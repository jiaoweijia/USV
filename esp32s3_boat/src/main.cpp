// main.cpp
// ============================================================================
//  ESP32-S3 多船编队无人艇（USV）下位机主程序
//  功能概述：
//    1. 连接 WiFi，通过 UDP 与多台上位机（电脑/树莓派/飞腾派）通信
//    2. 接收控制指令（"左桨µs,右桨µs"），转换为 PWM 占空比驱动电调
//    3. 每 2s 上报状态（电池电压/温度/灯态/PWM值），每 200s 重发注册包
//    4. 低电压（≤7.2V）自动停桨保护，双转向灯常亮警示
//    5. 按需开启摄像头，JPEG 帧分包经 UDP 图传（约 10fps）
//    6. 支持 HTTP 网页 OTA 固件升级
//    7. 转向灯自动指示（按桨差/舵角），也可手动控制
//  编队身份：取 WiFi MAC 地址后两字节转十进制（>9999 取模）作为船 ID
// ============================================================================
#include "main.hpp" // 包含头文件，定义全局变量和函数头文件
#define version "2026.6.4"  // 固件版本号（随状态包上报给上位机）
// ========== 性能调优参数 ==========
#define CHUNK_SIZE 1400   // 图传每包数据长度（字节）。MTU 上限 1500，取 1400 留余量给包头，减少包数量提速
#define PACKET_DELAY_US 0 // 图传分包之间的延迟（微秒）。设 0 最大限度提速，网络拥堵时可调为 2~5
#define FRAME_DELAY_MS 100  // 图传帧间延迟（毫秒）。100ms/帧 ≈ 10fps 帧率上限
// ============================================================================
// 摄像头引脚配置（DVP 并口摄像头，根据 ESP32-S3-USB-CAM 模块调整）
// 工作原理：ESP32 输出 XCLK 时钟给摄像头 → 摄像头按 PCLK 节拍从 Y2~Y9
//          并行吐出像素字节 → VSYNC/HREF 标记帧/行边界 → SCCB(I2C) 配置寄存器
// 注意：这些 GPIO 与模组硬件绑定，不能随意更改，必须与实际接线一一对应
// ============================================================================
#define PWDN_GPIO_NUM (-1) // 摄像头断电控制脚。-1 表示模组未引出该脚，不使用（无法软件断电）
#define RESET_GPIO_NUM (-1) // 摄像头硬件复位脚。-1 表示未接，只能靠 esp_camera_deinit() 软件复位
#define XCLK_GPIO_NUM 10 // 主时钟输出脚：ESP32 输出 20MHz 方波，是摄像头的工作心跳
#define SIOD_GPIO_NUM 40  // SCCB 数据线（即 I2C SDA）：读写摄像头内部寄存器（分辨率/画质/帧率）
#define SIOC_GPIO_NUM 39  // SCCB 时钟线（即 I2C SCL）
#define Y9_GPIO_NUM 48 // 8位像素数据总线最高位（bit7）
#define Y8_GPIO_NUM 11 // 像素数据 bit6
#define Y7_GPIO_NUM 12 // 像素数据 bit5
#define Y6_GPIO_NUM 14 // 像素数据 bit4
#define Y5_GPIO_NUM 16 // 像素数据 bit3
#define Y4_GPIO_NUM 18 // 像素数据 bit2
#define Y3_GPIO_NUM 17 // 像素数据 bit1
#define Y2_GPIO_NUM 15 // 像素数据最低位（bit0）

#define VSYNC_GPIO_NUM 38 // 帧同步脚：脉冲表示"新的一帧开始"，用于帧边界对齐
#define HREF_GPIO_NUM 47 // 行同步脚：表示当前正在输出一行有效像素
#define PCLK_GPIO_NUM 13 // 像素时钟脚：每输出 1 字节像素打 1 个脉冲，ESP32 按此采样数据总线

Ticker timer_control; // Arduino Ticker 定时器对象：每 100ms 周期调用 control() 做 PWM 保活+状态上报

// ============================================================================
// WiFi 配置
// ============================================================================
// const char *ssid = "test305";      // 历史 WiFi 配置（备用，按需切换）
// const char *password = "DMU305307";
// const char *ssid = "LSH_24G";
// const char *password = "LSH_2025";
const char *ssid = "ISSEC";       // 当前使用的 WiFi 热点名称
const char *password = "issec8888"; // 当前使用的 WiFi 密码

// ============================================================================
// UDP 配置
// ============================================================================
WiFiUDP udp; // UDP 对象，用于收发数据包（本地监听 localPort）

// 多台上位机的 IP 地址（编队系统的岸基/机载计算节点），报文会同时发给所有节点
// IPAddress serverIP(192, 168, 0, 102);   // 历史配置
// IPAddress serverIP(192, 168, 170, 144); // 历史配置
// IPAddress piServerIP(192, 168, 170, 191); // 历史配置
// IPAddress serverIP(192, 168, 6, 10);    // 历史配置
IPAddress rkserverIP(192, 168, 6, 10);  // rk 电脑服务器 IP 地址（瑞芯微上位机）
IPAddress serverIP(192, 168, 6, 11);    // 刘鹏电脑服务器 IP 地址（主上位机）
IPAddress dfgserverIP(192, 168, 6, 12); // 段富高电脑服务器 IP地址
IPAddress piServerIP(192, 168, 6, 13);  // 飞腾派服务器 IP 地址
unsigned int serverPort = 7020;         // 电脑服务器端监听端口
unsigned int piServerPort = 7020;       // 树莓派/飞腾派服务器端监听端口
unsigned int localPort = 7021;          // 本船 UDP 监听端口（接收控制指令）
unsigned int cameraPort = 7022;         // 摄像头图传专用端口（与控制端口分离，互不阻塞）

unsigned long lastHeartbeatTime = 0;     // 上次发送状态心跳的时间戳（millis()）
unsigned long lastreconnectTime = 0;     // 上次重发注册包的时间戳（millis()）
const unsigned long heartbeatInterval = 2000; // 状态心跳间隔：2 秒
unsigned long currentTime = 0; // 当前时间缓存（millis()，control() 内使用）
String macLastFourDecimalStr = ""; // 本船 ID 字符串：MAC 后两字节转十进制（编队唯一标识）

// ============================================================================
// 相机相关全局变量
// ============================================================================
bool cameraEnabled = false; // 相机是否已启用（图传任务运行标志）
bool low_power = false;  // 低功耗（低电压）模式标志：true 时电机强制停转
TaskHandle_t cameraTaskHandle = NULL; // 相机图传 FreeRTOS 任务句柄（用于停止任务）

// ============================================================================
// 电机控制全局变量
// ============================================================================
// 单桨模式
int throttle = 1000; // 油门值 (1000-2000us)：1000=停转，2000=全速
int steering = 1500; // 舵机转向值 (1000-2000us)：1500=居中
// 双桨模式
int pwm_left = 1500; // 无刷电机电调左 PWM 值 (1000-2000us)：1500=停（注意写入时会镜像翻转）
int pwm_right = 1500; // 无刷电机电调右 PWM 值 (1000-2000us)：1500=停
int led_left_state = 0;  // 左侧转向灯状态（1=亮，0=灭）
int led_right_state = 0; // 右侧转向灯状态（1=亮，0=灭）
bool manual_led_mode = false; // 手动转向灯模式标志：true 时冻结自动转向灯逻辑

bool otaMode = false; // OTA 模式标志：true 时 loop() 专职处理网页升级，心跳/PWM 保活停止

// ============================================================================
// OTA 网页服务器
// ============================================================================
// WebServer实例（端口 80），仅在 otaMode=true 时通过 loop() 里的 handleClient() 服务
WebServer server(80);

// 美化后的 OTA HTML 页面（原始字符串字面量，无需转义），包含进度条和状态显示。
// 页面流程：选择 .bin 固件 → XMLHttpRequest POST 上传到 /update → 实时显示进度百分比
//          → 成功后显示"重启中"提示（设备端收到完整固件后自动重启）
const char *upload_html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>OTA更新</title>
  <meta charset="UTF-8">
  <style>
    /* ===== 页面整体布局样式 ===== */
    body {
      font-family: Arial, sans-serif;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f5f5f5;
    }
    .container {
      background-color: white;
      border-radius: 10px;
      padding: 30px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    h1 {
      color: #333;
      text-align: center;
      margin-bottom: 30px;
    }
    /* ===== 上传表单样式 ===== */
    .upload-form {
      text-align: center;
      margin: 30px 0;
    }
    input[type="file"] {
      margin-bottom: 20px;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 5px;
    }
    input[type="submit"] {
      background-color: #4CAF50;
      color: white;
      padding: 12px 24px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 16px;
    }
    input[type="submit"]:hover {
      background-color: #45a049;
    }
    /* ===== 进度条样式 ===== */
    .progress-container {
      display: none;
      margin-top: 20px;
    }
    .progress-bar {
      width: 100%;
      height: 25px;
      background-color: #f0f0f0;
      border-radius: 5px;
      overflow: hidden;
    }
    .progress-bar-inner {
      height: 100%;
      background-color: #4CAF50;
      width: 0%;
      transition: width 0.3s ease;
    }
    /* ===== 状态提示框样式（uploading/success/error 三种配色） ===== */
    .status {
      margin-top: 15px;
      padding: 10px;
      border-radius: 5px;
      text-align: center;
      display: none;
    }
    .status.uploading {
      display: block;
      background-color: #e3f2fd;
      color: #1976d2;
    }
    .status.success {
      display: block;
      background-color: #e8f5e9;
      color: #388e3c;
    }
    .status.error {
      display: block;
      background-color: #ffebee;
      color: #d32f2f;
    }
    /* ===== 重启提示样式 ===== */
    .reboot-message {
      display: none;
      margin-top: 20px;
      text-align: center;
      padding: 15px;
      background-color: #e8f5e9;
      border-radius: 5px;
      color: #388e3c;
    }
    .button-container {
      text-align: center;
      margin-top: 20px;
    }
    .home-button {
      background-color: #2196F3;
      color: white;
      padding: 10px 20px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
    }
    .home-button:hover {
      background-color: #0b7dda;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>鹏鹏的EPS32S3多船编队控制下位机 OTA Update</h1>
    <!-- 上传表单：multipart/form-data 方式 POST 到 /update，由 ESP32 端 Update 库接收 -->
    <form class="upload-form" method='POST' action='/update' enctype='multipart/form-data' id='uploadForm'>
      <input type='file' name='update' id='fileInput' required>
      <br>
      <input type='submit' value='更新固件'>
    </form>

    <!-- 上传进度条容器（默认隐藏，开始上传后显示） -->
    <div class="progress-container" id="progressContainer">
      <div class="progress-bar">
        <div class="progress-bar-inner" id="progressBar"></div>
      </div>
      <div id="progressText">0%</div>
    </div>

    <!-- 状态提示框（uploading/success/error 动态切换样式类） -->
    <div class="status" id="status"></div>

    <!-- 更新成功后的重启提示 -->
    <div class="reboot-message" id="rebootMessage">
      <h3>更新成功！设备重启中...</h3>
      <p>设备将自动重启，请稍候...</p>
    </div>

    <div class="button-container">
      <a href="/" class="home-button">返回首页</a>
    </div>
  </div>

  <script>
    // 拦截表单默认提交，改用 XMLHttpRequest 上传以获得进度回调
    document.getElementById('uploadForm').addEventListener('submit', function(e) {
      e.preventDefault();

      const fileInput = document.getElementById('fileInput');
      const file = fileInput.files[0];
      if (!file) {
        alert('请先选择一个文件!');
        return;
      }

      const formData = new FormData();
      formData.append('update', file);

      // 显示进度元素
      document.getElementById('progressContainer').style.display = 'block';
      document.getElementById('status').className = 'status uploading';
      document.getElementById('status').textContent = '正在上传...';
      document.getElementById('status').style.display = 'block';

      // 创建XMLHttpRequest来上传文件
      const xhr = new XMLHttpRequest();

      // 更新进度（loaded/total 计算百分比，驱动进度条宽度）
      xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          document.getElementById('progressBar').style.width = percent + '%';
          document.getElementById('progressText').textContent = percent + '%';
        }
      });

      // 处理完成事件（根据 HTTP 状态码区分成功/失败）
      xhr.addEventListener('load', function() {
        const response = xhr.responseText;
        if (xhr.status === 200) {
          // 更新成功
          document.getElementById('status').className = 'status success';
          document.getElementById('status').textContent = '更新完成!';

          // 显示重启消息
          setTimeout(function() {
            document.getElementById('rebootMessage').style.display = 'block';

            // 一段时间后可以重新加载页面或重定向
            setTimeout(function() {
              // 可选：重启后重定向或重新加载页面
              // window.location.href = "/";
            }, 5000);
          }, 1000);
        } else {
          // 更新失败
          document.getElementById('status').className = 'status error';
          document.getElementById('status').textContent = '更新失败! 状态码: ' + xhr.status;
        }
      });

      // 处理错误（网络断开等）
      xhr.addEventListener('error', function() {
        document.getElementById('status').className = 'status error';
        document.getElementById('status').textContent = '上传错误!';
      });

      // 发送请求
      xhr.open('POST', '/update');
      xhr.send(formData);
    });
  </script>
</body>
</html>
)rawliteral";

// ============================================================================
// PWM 换算与电机输出
// ============================================================================

// 将PWM微秒值转换为LEDC占空比值（单桨模式）
// 输入：pwmValue 期望的脉宽（1000~2000us，舵机/电调标准协议）
// 输出：12 位分辨率下的占空比计数（约 204~409）
// 换算依据：50Hz PWM 周期 = 20ms = 20000us；满量程占空比 = 2^12 - 1 = 4095
// 公式：duty = 脉宽 × 4095 / 20000（整数除法，误差 < 1µs，可忽略）
int convertPWM_single(int pwmValue)
{
  return (pwmValue * 4095) / 20000;
}
// 将PWM微秒值转换为LEDC占空比值（双桨模式，换算公式与单桨相同）
int convertPWM_double(int pwmValue)
{
  return (pwmValue * 4095) / 20000;
}

// 单桨模式 PWM 输出：油门→电调（通道0/GPIO3），转向→舵机（通道1/GPIO4）
void Set_Single_paddle_Pwm(int throttle_pwm, int steering_pwm)
{
  int esc_duty = convertPWM_single(throttle_pwm); // 油门µs → 占空比
  ledcWrite(ESC_CHANNEL, esc_duty);               // 写入电调 LEDC 通道

  int servo_duty = convertPWM_single(steering_pwm); // 转向µs → 占空比
  ledcWrite(SERVO_CHANNEL, servo_duty);             // 写入舵机 LEDC 通道
}

// 双桨模式 PWM 输出：左桨（通道0/GPIO4），右桨（通道1/GPIO3）
void Set_Double_paddle_Pwm(int pwm_left, int pwm_right)
{
  // 左桨方向镜像变换：-(x-1500)+1500 = 3000-x
  // 原因：左电机与右电机对装（螺旋桨转向相反以抵消反扭），或上位机协议方向约定
  // 效果：1500 不变；>1500 的值变小，<1500 的值变大（绕中位翻转）
  pwm_left = -(pwm_left - 1500) + 1500;
  int PWM_L_duty = convertPWM_double(pwm_left); // 左桨µs → 占空比
  ledcWrite(PWM_L_CHANNEL, PWM_L_duty);         // 写入左电调 LEDC 通道

  int PWM_R_duty = convertPWM_double(pwm_right); // 右桨µs → 占空比
  ledcWrite(PWM_R_CHANNEL, PWM_R_duty);          // 写入右电调 LEDC 通道
}

// ============================================================================
// 转向灯控制
// ============================================================================

// 直接设置左右转向灯亮灭（1=亮，0=灭），并同步到全局状态变量（随状态包上报）
void setTurnLEDState(int left, int right)
{
  led_left_state = left ? 1 : 0; //if left is 1, then led_left_state is 1, else 0
  led_right_state = right ? 1 : 0; //if right is 1, then led_right_state is 1, else 0

  digitalWrite(LED_LEFT_PIN, led_left_state ? HIGH : LOW);  // 左灯5  if led_left_state is 1, then left LED is on, else off
  digitalWrite(LED_RIGHT_PIN, led_right_state ? HIGH : LOW); // 右灯6  if led_right_state is 1, then right LED is on, else off
}

// 根据当前控制量自动判断转向方向并点亮对应转向灯（带死区防抖）
// 单桨：按舵机值偏离 1500 的方向；双桨：按左右桨差值方向
// TURN_DEADBAND=50：死区，避免直行附近的微小偏差导致灯频繁闪烁
void updateTurnLEDs()
{
  if (USV == Single_paddle)
  {
    if (steering < 1500 - TURN_DEADBAND)      // 舵量偏左超过死区
    {
      setTurnLEDState(1, 0);                  // 点亮左转灯
    }
    else if (steering > 1500 + TURN_DEADBAND) // 舵量偏右超过死区
    {
      setTurnLEDState(0, 1);                  // 点亮右转灯
    }
    else
    {
      setTurnLEDState(0, 0);                  // 死区内（视为直行），双灯灭
    }
  }
  else if (USV == double_paddle)
  {
    int diff = pwm_left - pwm_right;          // 左右桨差：>0 左桨快 → 船右转；<0 → 左转

    if (diff < -TURN_DEADBAND)                // 差值超死区且右桨快
    {
      setTurnLEDState(1, 0);                  // 点亮左转灯
    }
    else if (diff > TURN_DEADBAND)            // 差值超死区且左桨快
    {
      setTurnLEDState(0, 1);                  // 点亮右转灯
    }
    else
    {
      setTurnLEDState(0, 0);                  // 双桨速接近（直行），双灯灭
    }
  }
}

// 处理转向灯手动测试指令（LED_LEFT/LED_RIGHT/LED_OFF/LED_BOTH）
// 命中任一指令则进入 manual_led_mode 并返回 true（commend_parse 据此短路后续解析）
bool handleLedCommand(String incomingPacket)
{
  if (incomingPacket.equalsIgnoreCase("LED_LEFT"))  // udp发送LED_LEFT  点亮左灯（测试用）
  {
    manual_led_mode = true;                         // 进入手动模式，冻结自动转向灯
    setTurnLEDState(1, 0);
    Serial.println("LED test command: left");
    return true;
  }

  if (incomingPacket.equalsIgnoreCase("LED_RIGHT")) // 点亮右灯（测试用）
  {
    manual_led_mode = true;
    setTurnLEDState(0, 1);
    Serial.println("LED test command: right");
    return true;
  }

  if (incomingPacket.equalsIgnoreCase("LED_OFF"))   // 双灯全灭（测试用）
  {
    manual_led_mode = true;
    setTurnLEDState(0, 0);
    Serial.println("LED test command: off");
    return true;
  }

  if (incomingPacket.equalsIgnoreCase("LED_BOTH"))  // 双灯全亮（测试/警示用）
  {
    manual_led_mode = true;
    setTurnLEDState(1, 1);
    Serial.println("LED test command: both");
    return true;
  }

  return false; // 不是灯控指令，交由后续指令解析
}

// 重置控制状态：电机停转（1000/1500µs），非手动灯模式下转向灯恢复自动逻辑
// 触发场景：收到 "reset" 指令（通常是控制失联或测试完毕后调用）
void resetControls()
{
  if (USV == Single_paddle)
  {
    throttle = 1000;  // 油门回最低（电机停）
    steering = 1500;  // 舵机回中
    Set_Single_paddle_Pwm(throttle, steering); // 立即输出
    if (!manual_led_mode)
    {
      updateTurnLEDs(); // 自动模式下灯也回直行状态
    }
    Serial.println("已重置控制参数 - 电机停止，舵机居中");
  }
  else if (USV == double_paddle)
  {
    pwm_left = 1500;  // 双桨回中位（停转）
    pwm_right = 1500;
    Set_Double_paddle_Pwm(pwm_left, pwm_right); // 立即输出
    if (!manual_led_mode)
    {
      updateTurnLEDs();
    }
    Serial.println("已重置控制参数 - 电机停止");
  }
}

// 系统软重启（收到 "restart" 指令或 OTA 完成后调用）
void restartSystem()
{
  Serial.println("系统重启中...");
  delay(100);        // 等待串口打印完成
  ESP.restart();     // ESP32 软复位
}

// ============================================================================
// 摄像头初始化与图传
// ============================================================================

// 初始化摄像头：配置 DVP 引脚映射、时钟、格式，并注册到 esp_camera 驱动
// 返回：true=初始化成功，false=失败（引脚错误/排线松动/驱动异常等）
bool initCamera()
{
  camera_config_t config;                       // 摄像头配置结构体
  config.ledc_channel = LEDC_CHANNEL_0;         // XCLK 使用 LEDC 通道 0输出（注意：与双桨左电调的 PWM_L_CHANNEL=0 编号重叠）
  config.ledc_timer = LEDC_TIMER_0;             // XCLK 使用 LEDC 定时器 0
  config.pin_d0 = Y2_GPIO_NUM;                  // 数据总线 D0~D7（对应 Y2~Y9 引脚宏）
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;              // 主时钟脚（20MHz 输出）
  config.pin_pclk = PCLK_GPIO_NUM;              // 像素时钟脚
  config.pin_vsync = VSYNC_GPIO_NUM;            // 帧同步脚
  config.pin_href = HREF_GPIO_NUM;              // 行同步脚
  config.pin_sscb_sda = SIOD_GPIO_NUM;          // SCCB(I2C) 数据脚
  config.pin_sscb_scl = SIOC_GPIO_NUM;          // SCCB(I2C) 时钟脚
  config.pin_pwdn = PWDN_GPIO_NUM;              // 断电脚（未接，-1）
  config.pin_reset = RESET_GPIO_NUM;            // 复位脚（未接，-1）
  config.xclk_freq_hz = 20000000;               // XCLK 频率 20MHz（DVP 摄像头常用值）
  config.pixel_format = PIXFORMAT_JPEG;         // 输出 JPEG（硬件压缩，便于 UDP 分包传输）
  config.frame_size = FRAMESIZE_UXGA; // 初始申请 UXGA(1600x1200) 大小的帧缓冲
  config.jpeg_quality = 12;                     // 初始 JPEG 质量（0-63，数值越小质量越高）
  config.fb_count = 2;                          // 帧缓冲数量：2 个实现采集/发送流水线

  // 初始化摄像头（驱动探测传感器型号、配置寄存器、启动 DMA）
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK)
  {
    Serial.printf("摄像头初始化失败: %s\n", esp_err_to_name(err));
    return false;
  }

  // 初始化成功后，实际降规格以减轻传输带宽压力：
  sensor_t *s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_VGA); // 强制 VGA(640x480)，JPEG 体积小，UDP 分包少
  s->set_quality(s, 30);               // 质量 30（中等，平衡画质与压缩率）

  Serial.println("摄像头初始化成功");
  return true;
}

// 关闭摄像头：释放驱动占用的硬件资源（LEDC/DMAC/帧缓冲）
void deinitCamera()
{
  esp_camera_deinit();
  Serial.println("摄像头已关闭");
}

// 发送单个图传分包（自定义协议：12字节头 + 数据载荷）
// 包头布局：帧ID(4B) + 总包数(2B) + 当前包序号(2B) + 本包数据长(2B) + payload
// 接收端按 frame_id 聚包、按 packet_idx 排序重组；缺包则丢弃整帧（等下一帧）
void sendCameraPacketTo(IPAddress ip, uint32_t frame_id, uint16_t total_packets, uint16_t packet_idx, uint16_t packet_len, uint8_t *payload)
{
  udp.beginPacket(ip, cameraPort);        // 目标：指定上位机 IP + 图传端口 7022
  udp.write((uint8_t *)&frame_id, 4);     // 帧唯一 ID（取 micros()，区分不同帧）
  udp.write((uint8_t *)&total_packets, 2);// 本帧共分成几个包
  udp.write((uint8_t *)&packet_idx, 2);   // 当前包的序号（从 0 开始）
  udp.write((uint8_t *)&packet_len, 2);   // 当前包载荷长度（最后一包可能小于 CHUNK_SIZE）
  udp.write(payload, packet_len);         // JPEG 数据分片
  udp.endPacket();                        // 发出
}

// 摄像头图传 FreeRTOS 任务（固定在核心 0 运行，与核心 1 的 UDP 收包互不干扰）
// 循环：抓帧 → 按 CHUNK_SIZE 分包 → 逐包发给 serverIP 和 piServerIP → 延时控帧率
void cameraTask(void *pvParameters)
{
  Serial.println("相机传输任务开始");
  while (cameraEnabled) // cameraEnabled 置 false 时退出循环（stopCamera 也会强删任务）
  {
    camera_fb_t *fb = esp_camera_fb_get(); // 从驱动抓取一帧 JPEG（阻塞直到拍完）
    if (!fb)
    {
      Serial.println("Frame capture failed");
      delay(10);
      return; // 注意：此处 return 会直接结束任务（未删除句柄，属潜在小缺陷）
    }

    // 分包发送
    uint32_t frame_id = micros(); // 微秒级时间戳作为帧 ID，唯一性好
    uint16_t total_packets = (fb->len + CHUNK_SIZE - 1) / CHUNK_SIZE; // 向上取整求总包数

    for (uint16_t i = 0; i < total_packets; i++)
    {
      uint16_t packet_len = (i == total_packets - 1) ? (fb->len - i * CHUNK_SIZE) : CHUNK_SIZE; // 最后一包取剩余长度

      sendCameraPacketTo(serverIP, frame_id, total_packets, i, packet_len, fb->buf + i * CHUNK_SIZE);  // 发给主上位机
      sendCameraPacketTo(piServerIP, frame_id, total_packets, i, packet_len, fb->buf + i * CHUNK_SIZE); // 发给飞腾派
      // sendCameraPacketTo(dfgserverIP, frame_id, total_packets, i, packet_len, fb->buf + i * CHUNK_SIZE); // 备用：段富高
      // sendCameraPacketTo(rkserverIP, frame_id, total_packets, i, packet_len, fb->buf + i * CHUNK_SIZE);  // 备用：RK

      // 包间延迟设为0，但如果网络拥堵可以微调为2~5微秒
      if (PACKET_DELAY_US > 0)
        delayMicroseconds(PACKET_DELAY_US);
    }

    esp_camera_fb_return(fb); // 归还帧缓冲给驱动（必须调用，否则缓冲耗尽后无法再拍）

    // 帧率控制：根据期望的帧率调整 delay（100ms → 最高约 10fps）
    delay(FRAME_DELAY_MS);
  }

  Serial.println("相机传输任务结束");
  vTaskDelete(NULL); // 删除自身任务（cameraEnabled 变 false 后走到这里）
}

// 启动摄像头图传：初始化硬件 + 在核心 0 创建高优先级(5)图传任务
// 已开启则忽略；初始化失败则保持关闭状态
void startCamera()
{
  if (cameraEnabled)
  {
    Serial.println("相机已经开启");
    return;
  }

  if (!initCamera())
  {
    Serial.println("相机初始化失败");
    return;
  }

  cameraEnabled = true;
  // 将相机任务分配到核心 0（与主循环不同的核心），避免图传挤占控制/通信的 CPU
  xTaskCreatePinnedToCore(cameraTask, "CameraTask", 4096, NULL, 5, &cameraTaskHandle, 0);
  Serial.println("相机已开启并开始传输（核心 0）");
}

// 停止摄像头图传：置停止标志 → 强制删除任务 → 反初始化硬件
void stopCamera()
{
  if (!cameraEnabled)
  {
    Serial.println("相机已经关闭");
    return;
  }

  cameraEnabled = false;
  if (cameraTaskHandle != NULL)
  {
    vTaskDelete(cameraTaskHandle); // 强制删除任务（不管它当前执行到哪）
    cameraTaskHandle = NULL;
  }
  deinitCamera();
  Serial.println("摄像头已关闭");
}

// ============================================================================
// OTA 网页固件升级
// ============================================================================

// 启动 OTA：注册 HTTP 路由并启动 WebServer（端口 80）
// 收到 "OTA" 指令后调用；此后 loop() 专职跑 server.handleClient()，
// control() 中的 PWM 保活和心跳全部暂停（升级期间电机绝不动，安全设计）
void startOTA()
{
  if (otaMode)
    return; // 已处于 OTA 模式则不重复进入

  otaMode = true;

  // 配置HTTP服务器用于网页上传
  // 路由 1：GET / → 返回上传页面（浏览器打开 http://船IP/ 看到的界面）
  server.on("/", HTTP_GET, []()                
            { server.send(200, "text/html", upload_html); });

  // 路由 2：POST /update → 处理固件上传（三个回调阶段）
  server.on("/update", HTTP_POST, []()
            {
        server.send(200, "text/html", upload_html); // 上传结束，返回页面
        delay(1000);                                 // 等待 HTTP 响应发送完毕
        restartSystem(); }, []()                     // 重启进入新固件
            {
        // 上传过程回调：按文件分片状态机处理
        HTTPUpload& upload = server.upload();
        if (upload.status == UPLOAD_FILE_START) {
            Serial.printf("HTTP更新: %s\n", upload.filename.c_str());
            if (!Update.begin()) {           // 阶段1：开始，向 Flash 申请 OTA 分区
                Update.printError(Serial);
            }
        } else if (upload.status == UPLOAD_FILE_WRITE) {
            if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
                Update.printError(Serial);   // 阶段2：逐片写入 Flash
            }
        } else if (upload.status == UPLOAD_FILE_END) {
            if (Update.end(true)) {          // 阶段3：结束并校验（true=设置启动分区标志）
                Serial.println("HTTP更新完成");
            } else {
                Update.printError(Serial);
            }
        } });

  server.begin();
  Serial.println("HTTP OTA服务器已启动");

  // 发送OTA准备完成消息给上位机（含本机 IP，方便上位机引导用户打开升级页面）
  // 注意：此处 buildcommandMessage() 的返回值未发送，疑似遗漏 sendUdpMessage() 调用
  String otaInfo = "OTA_READY:" + WiFi.localIP().toString() + "\r\n" + "上传固件项目的.pio/build/<board_name>/firmware.bin";
  buildcommandMessage(otaInfo);
}

// ============================================================================
// 指令解析（UDP/串口共用入口）
// ============================================================================

// 解析收到的文本指令并执行。支持格式：
//   "左值,右值"      → 控制指令（单桨=油门,舵机；双桨=左桨,右桨）
//   "LED_LEFT/RIGHT/OFF/BOTH" → 手动转向灯测试
//   "reset"          → 停机复位
//   "restart"        → 系统重启
//   "OTA"            → 进入网页固件升级模式
//   "Camera_Toggle"  → 开/关摄像头图传
void commend_parse(String incomingPacket)
{
  incomingPacket.trim(); // 去除首尾空白（含 UDP 报文尾部换行）

  // 1) 优先尝试转向灯测试指令
  if (handleLedCommand(incomingPacket))
  {
    return;
  }

  // 2) 系统级指令
  if (incomingPacket.equalsIgnoreCase("reset")) // 复位：电机停、舵机回中、退出手动灯模式
  {
    manual_led_mode = false;
    resetControls();
    return;
  }

  if (incomingPacket.equalsIgnoreCase("restart")) // 软重启整块板子
  {
    restartSystem();
    return;
  }

  if (incomingPacket.equalsIgnoreCase("OTA")) // 进入 OTA 升级模式
  {
    startOTA();
    return;
  }

  // 3) 相机开关指令
  if (incomingPacket.equalsIgnoreCase("Camera_Toggle")) // 切换相机状态并回报
  {
    if (cameraEnabled)
    {
      stopCamera();
      buildcommandMessage("Camera:Closed"); // 注意：返回值未发送，疑似遗漏 sendUdpMessage()
    }
    else
    {
      startCamera();
      buildcommandMessage("Camera:Opened");
    }
    return;
  }

  // 4) 控制指令：必须含逗号分隔的两个数值
  int commaIndex = incomingPacket.indexOf(','); // 查找逗号位置，返回第一个逗号的下标
  if (commaIndex > 0)
  {
    if (USV == Single_paddle)
    {
      throttle = incomingPacket.substring(0, commaIndex).toInt();     // 逗号前 = 油门 
      steering = incomingPacket.substring(commaIndex + 1).toInt();    // 逗号后 = 舵机
      if (!low_power) // 低电压保护中则只更新数值不输出 PWM 电池低于7.2VV，low_power为true
      {
        throttle = constrain(throttle, 1000, 2000); // 限幅，防止非法值打坏电调 无论发多少，都夹回1000-2000之间
        steering = constrain(steering, 1000, 2000);
        Set_Single_paddle_Pwm(throttle, steering);  // 立即输出（不等 100ms 周期，保证响应） 写入通道
      }
      manual_led_mode = false; // 收到控制指令即退出手动灯模式，恢复自动转向灯
      Serial.println("解析到控制指令 - 油门: " + String(throttle) + ", 舵机: " + String(steering));
    }
    else if (USV == double_paddle)
    {
      pwm_left = incomingPacket.substring(0, commaIndex).toInt();   // 逗号前 = 左桨
      pwm_right = incomingPacket.substring(commaIndex + 1).toInt(); // 逗号后 = 右桨
      if (!low_power)
      {
        pwm_left = constrain(pwm_left, 1000, 2000);   // 限幅
        pwm_right = constrain(pwm_right, 1000, 2000);
        Set_Double_paddle_Pwm(pwm_left, pwm_right);   // 立即输出
      }

      manual_led_mode = false;

      Serial.println("解析到控制指令 - 左电机: " + String(pwm_left) + ", 右电机: " + String(pwm_right));
    }
  }
  else
  {
    Serial.println("错误：无效的指令格式"); // 无逗号且非任何已知指令
  }
}

// ============================================================================
// 心脏循环：由 Ticker 每 100ms 调用一次
// ============================================================================

// 周期任务（100ms）：①PWM保活 ②自动转向灯 ③电池电压监测 ④状态心跳/重注册
// 注意：运行在 Ticker 回调上下文（esp_timer 任务），因此内部不做网络重活，
//      仅发送小体积状态包（当前实现如此，若加打印/大逻辑需谨慎）
void control()
{
  if (!otaMode) // OTA 模式下暂停一切控制，专心升级
  {
    if (!low_power) // 正常电压：维持电机输出与转向灯
    {
      // ① PWM 保活：把当前控制量再写一遍。
      // 原因：航模电调普遍有 failsafe——收不到 PWM 信号约 0.5s 就自动熄火，
      //       即使控制值没变也必须周期性刷新信号
      if (USV == Single_paddle)
      {
        Set_Single_paddle_Pwm(throttle, steering);
      }
      else if (USV == double_paddle)
      {
        Set_Double_paddle_Pwm(pwm_left, pwm_right);
      }
      // ② 自动转向灯（手动测试模式下冻结）
      if (!manual_led_mode)
      {
        updateTurnLEDs();
      }
    }
    else{
      setTurnLEDState(1,1); // 低电压：双转向灯常亮警示（电机已强制停转）
    }

    // ③④ 状态上报节拍控制
    currentTime = millis();
    if (currentTime - lastreconnectTime >= 100 * heartbeatInterval) // 每 200s 重发注册包
    {
      // "防丢重连"机制：上位机若重启/丢包，最多 200s 内能重新发现本船
      sendUdpMessage(buildRegisterMessage());
      sendUdpMessage(macLastFourDecimalStr); // 附带纯 ID 字符串（兼容旧上位机协议）
      lastreconnectTime = currentTime;
    }
    else
    {
      if (currentTime - lastHeartbeatTime >= heartbeatInterval) // 每 2s 发一次状态心跳
      {
        // 获取ADC0数据（电池电压分压采样）
        int adcValue = analogRead(A0);
        float voltage = adcValue * 3.3 / 4095.0 * 3+0.5; // 还原实际电压：ADC量程3.3V×分压比3 + 二极管压降补偿0.5V
        if (voltage>7.2)   // 3S锂电池：>7.2V 视为正常（约2.4V/节）
        {
          low_power = false;
        }
        else              // ≤7.2V 触发低压保护
        {
          low_power = true;
        }

        // 获取板载温度（使用ESP32内置温度传感器）
        float temperature = temperatureRead();

        // 发送状态上报数据（type:1，含电压/温度/灯态/PWM/相机/版本）
        sendUdpMessage(buildStatusMessage(adcValue, temperature));
        lastHeartbeatTime = currentTime;
      }
    }
  }
}

// ============================================================================
// 电调校准（上电时执行一次）
// ============================================================================

// 单桨模式校准：输出标准油门序列让电调学习行程范围
// 序列：1000(最低) → 1300 → 1000，随后舵机输出两遍中位 1500
void calibrateESC()
{
  Serial.println("开始电调校准...");  //ledcWrite 往某个特定通道输送一个占空比数值
  ledcWrite(ESC_CHANNEL, convertPWM_single(1000)); // 最低油门 航模PWM协议电调识别1000-2000us
  delay(1000);
  ledcWrite(ESC_CHANNEL, convertPWM_single(1300)); // 中高油门（校准行程）
  delay(2000);
  ledcWrite(ESC_CHANNEL, convertPWM_single(1000)); // 回最低
  delay(1000);

  ledcWrite(SERVO_CHANNEL, convertPWM_single(1500)); // 舵机中位
  delay(1000);
  ledcWrite(SERVO_CHANNEL, convertPWM_single(1500)); // 保持中位
  delay(1000);

  Serial.println("单桨校准完成");
}

// 双桨模式校准：双桨同时输出中位 1500µs 使电调解锁待机
// （高低油门行程校准代码已注释，当前仅做中位解锁）
void calibratePWM()
{
  Serial.println("开始PWM校准...");
  ledcWrite(PWM_L_CHANNEL, convertPWM_double(1500)); // 左桨中位
  ledcWrite(PWM_R_CHANNEL, convertPWM_double(1500)); // 右桨中位
  delay(1000);
  // ledcWrite(PWM_L_CHANNEL, convertPWM_double(1100)); // 备用：全行程校准序列（如需重新校准电调行程可放开）
  // ledcWrite(PWM_R_CHANNEL, convertPWM_double(1100));
  // delay(2000);
  // ledcWrite(PWM_L_CHANNEL, convertPWM_double(1900));
  // ledcWrite(PWM_R_CHANNEL, convertPWM_double(1900));
  // delay(2000);
  // ledcWrite(PWM_L_CHANNEL, convertPWM_double(1500));
  // ledcWrite(PWM_R_CHANNEL, convertPWM_double(1500));
  // delay(1000);

  Serial.println("双桨校准完成");
}

// ============================================================================
// 上行报文构造（JSON 格式，发给所有上位机）
// ============================================================================

// 注册报文（type:0）：告知上位机"本船上线"，携带船只 ID（MAC 后四位十进制）
String buildRegisterMessage()
{
  return "{\"type\":0,\"content\":{\"id\":\"" + macLastFourDecimalStr + "\"}}";
}

// 状态报文（type:1）：周期心跳，携带全部运行状态
// 字段：adc0原始值 / 温度 / 左右灯态 / 船ID / 左右PWM / 相机开关 / 固件版本
String buildStatusMessage(int adcValue, float temperature)
{
  String jsonData = "{\"type\":1,\"content\":{";
  jsonData += "\"adc0\":\"" + String(adcValue);          // 电池电压 ADC 原始值
  jsonData += "\",\"temperature\":\"" + String(temperature, 1); // 芯片温度（1位小数）
  jsonData += "\",\"led_left\":\"" + String(led_left_state);    // 左转向灯状态
  jsonData += "\",\"led_right\":\"" + String(led_right_state);  // 右转向灯状态
  jsonData += "\",\"id\":\"" + macLastFourDecimalStr;           // 船只 ID
  jsonData += "\",\"pwml\":\"" + String(pwm_left);              // 左桨当前 PWM 值
  jsonData += "\",\"pwmr\":\"" + String(pwm_right);             // 右桨当前 PWM 值
  jsonData += "\",\"camera\":\"" + String(cameraEnabled);       // 相机开关状态
  jsonData += "\",\"version\":\"" + String(version);            // 固件版本号
  jsonData += "\"}}";
  return jsonData;
}

// 心跳报文（type:2）：携带运行时间戳（当前定义了但未实际调用，心跳由 type:1 兼任）
String buildHeartbeatMessage()
{
  String jsonData = "{\"type\":2,\"content\":{";
  jsonData += "\"timestamp\":\"";
  jsonData += String(millis());
  jsonData += "\"}}";
  return jsonData;
}

// 命令回应报文（type:3）：向上位机回报指令执行结果（如 Camera:Opened）
String buildcommandMessage(String message)
{
  String jsonData = "{\"type\":3,\"content\":{";
  jsonData += "\"command\":\"";
  jsonData += message;
  jsonData += "\"}}";
  return jsonData;
}

// ============================================================================
// UDP 发送
// ============================================================================

// 向指定 IP:端口 发送一条 UDP 消息（带串口日志），返回是否成功
bool sendUdpMessageTo(IPAddress ip, unsigned int port, String message)
{
  if (udp.beginPacket(ip, port)) // 组装包 成功构造目标地址数据包 返回0.1
  {
    udp.print(message); //装填数据
    bool result = udp.endPacket(); // 真正发出
    Serial.print("发送消息到 ");
    Serial.print(ip);// 目标IP
    Serial.print(":");
    Serial.print(port);
    Serial.print(" ");
    Serial.print(message);
    if (result)
    {
      Serial.println(" [成功]");
    }
    else
    {
      Serial.println(" [失败]");
    }
    return result;
  }
  else
  {
    Serial.print("发送消息到 ");
    Serial.print(ip);
    Serial.print(":");
    Serial.print(port);
    Serial.print(" ");
    Serial.print(message);
    Serial.println(" [失败 - 无法开始数据包]");
    return false;
  }
}

// 广播式发送：把一条消息同时发给全部 4 台上位机（任一成功即视为成功）
// 这是"多船编队"的简化设计——船只不维护会话，所有节点都能收到所有报文
bool sendUdpMessage(String message)
{
  message += "\n"; // 追加换行作为报文结束符（方便上位机按行解析）
  bool pcResult = sendUdpMessageTo(serverIP, serverPort, message);    // 刘鹏电脑
  bool piResult = sendUdpMessageTo(piServerIP, piServerPort, message);// 飞腾派
  bool dfgResult = sendUdpMessageTo(dfgserverIP, serverPort, message);// 段富高电脑
  bool rkResult = sendUdpMessageTo(rkserverIP, piServerPort, message);// RK电脑
  return pcResult || piResult || dfgResult || rkResult;
}

// ============================================================================
// UDP 接收任务（FreeRTOS，固定在核心 1 运行）
// ============================================================================

// 循环轮询 UDP 收包（100ms 间隔），收到即交给 commend_parse() 解析执行
// 与核心 0 的相机任务、Ticker 控制互不抢占，保证控制与图传隔离
void readUdpData(void *parameter)
{
  Serial.println("UDP数据读取任务已启动");

  while (true) // 永久任务
  {
    int packetSize = udp.parsePacket(); // 检查7021是否有到达的udp数据包
    if (packetSize)
    {
      char incomingPacket[255]; // 指令都很短，255 字节足够
      int len = udp.read(incomingPacket, 255);  //读取255字节到incomingPacket数组
      if (len > 0)
      {
        incomingPacket[len] = '\0'; // 手动补字符串结束符
        Serial.print("接收到UDP数据: ");
        Serial.println(incomingPacket);
        commend_parse(incomingPacket); // 解析并执行指令
      }
    }
    vTaskDelay(100 / portTICK_PERIOD_MS); // 让出 CPU 100ms（轮询节奏）每轮结束阻塞100ms
  }
}

// ============================================================================
// 初始化
// ============================================================================

void setup()
{
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // 关闭欠压检测：防止电机堵转瞬间拉低电压导致芯片误复位
  
  Serial.begin(115200);
  Serial.println("ESP32S3 UDP 无刷电机+灯+摄像头控制启动中...");
  pinMode(LED_pin, OUTPUT);      // 状态灯 GPIO0
  pinMode(LED_LEFT_PIN, OUTPUT); // 左转向灯 GPIO5
  pinMode(LED_RIGHT_PIN, OUTPUT);// 右转向灯 GPIO6
  digitalWrite(LED_LEFT_PIN, LOW);  // 转向灯初始熄灭
  digitalWrite(LED_RIGHT_PIN, LOW);
  // digitalWrite(LED_pin, HIGH);
  analogWrite(LED_pin, 255); // 状态灯全亮（WiFi 连接过程中指示）

  // ---------- 连接 WiFi ----------
  WiFi.mode(WIFI_STA); // STA 模式（连别人热点，而非自建 AP 自己建热点）
  WiFi.begin(ssid, password);
  setTurnLEDState(1,1); // 连接期间双转向灯常亮作为"未就绪"指示
  while (WiFi.status() != WL_CONNECTED) // 死等 WiFi 连上（不连接不往下走）
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi连接成功！");
  Serial.print("IP地址: ");
  Serial.println(WiFi.localIP());  //返回当前 ESP32S3 的 IP 地址
  udp.begin(localPort); // 启动 UDP 监听（端口 7021，接收控制指令）可以发收UDP数据 例如船1:  192.168.6.47 : 7021 船2:  192.168.6.48 : 7021
  Serial.println("UDP客户端已启动");

  // ---------- 生成本船编队 ID ----------
  uint8_t mac[6];  //申请6字节空间，用于存储 MAC 地址
  WiFi.macAddress(mac);   // 获取当前 ESP32S3 的 MAC 地址
  char macStr[18];  //申请18字节空间，用于存储 MAC 地址字符串，符串
  sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  Serial.print("MAC地址: ");
  Serial.println(macStr);

  int macLastFourDecimal = (mac[4] << 8) | mac[5]; // 取 MAC 后两字节拼成 16 位数
  if (macLastFourDecimal > 9999)
    macLastFourDecimal %= 10000; // 压缩到 4 位以内，作为船 ID 极小概率冲突

  macLastFourDecimalStr = String(macLastFourDecimal);
  Serial.print("MAC地址的后四位（十进制）: ");
  Serial.println(macLastFourDecimal);
  sendUdpMessage(buildRegisterMessage()); // 首次上线：向所有上位机广播注册包
  // sendUdpMessage(macLastFourDecimalStr);

  // ---------- 按船型初始化 PWM 并校准电调 ----------
  if (USV == Single_paddle)
  {
    // 单桨：通道0→GPIO3(电调)，通道1→GPIO4(舵机)
    ledcSetup(ESC_CHANNEL, PWM_FREQs, PWM_RESOLUTIONs);   // 设置通道0：50Hz / 12位
    ledcAttachPin(ESC_PWM_PIN, ESC_CHANNEL);              // 把通道0波形输出到 GPIO3
    ledcSetup(SERVO_CHANNEL, PWM_FREQs, PWM_RESOLUTIONs); // 设置通道1：50Hz / 12位
    ledcAttachPin(SERVO_PWM_PIN, SERVO_CHANNEL);          // 把通道1波形输出到 GPIO4

    calibrateESC(); // 电调行程校准
    Serial.println("单桨校准完成");
  }
  else if (USV == double_paddle)
  {
    // 双桨：通道0→GPIO4(左电调)，通道1→GPIO3(右电调)
    ledcSetup(PWM_L_CHANNEL, PWM1_FREQs, PWM1_RESOLUTIONs); // 通道0：50Hz / 12位
    ledcAttachPin(ESC_PWM_L, PWM_L_CHANNEL);                // 把通道0波形输出到 GPIO4
    ledcSetup(PWM_R_CHANNEL, PWM1_FREQs, PWM1_RESOLUTIONs); // 通道1：50Hz / 12位
    ledcAttachPin(ESC_PWM_R, PWM_R_CHANNEL);                // 把通道1波形输出到 GPIO3

    calibratePWM(); // 双桨中位解锁
    Serial.println("双桨校准完成");
  }

  // ---------- 启动周期任务 ----------
  timer_control.attach_ms(interrupt_time_control, control); // Ticker：硬件定时器每 100ms 执行 control()
  // 将UDP读取任务分配到核心 1  （栈 4KB，优先级 1）
  xTaskCreatePinnedToCore(readUdpData, "ReadUdpData", 4096, NULL, 1, NULL, 1);
  //                       任务函数（一直运行） ， 任务名称   栈大小   参数   优先级   句柄   核心
  // sendUdpMessage(macLastFourDecimalStr);
  delay(2000);                       // 给上位机留出启动/响应时间
  sendUdpMessage(buildRegisterMessage()); // 二次注册，确保上位机收到
  // sendUdpMessage(macLastFourDecimalStr);
  // digitalWrite(LED_pin, LOW);
  analogWrite(LED_pin, 150); // 状态灯调暗：表示"初始化完成、正常运行"
  setTurnLEDState(0,0);      // 转向灯熄灭（就绪）
}

// ============================================================================
// 主循环
// ============================================================================

// loop() 主体很空：重活分别在 Ticker(control)、FreeRTOS 任务(收包/图传)中跑
void loop()
{
  // 处理HTTP服务器请求（仅 OTA 模式下，loop 专职服务网页升级）
  if (otaMode)
  {
    server.handleClient();
  }

  // 检查串口是否有数据传入（调试通道：USB 串口发指令等同 UDP 指令）
  if (Serial.available() > 0)
  {
    String receivedData = Serial.readStringUntil('\n');  //读到换行符为止
    commend_parse(receivedData);
  }
}
