#ifndef MAIN_HPP // 主头文件
#define MAIN_HPP // 主头文件，包含所有必要的库和定义

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>// 包含WiFiUdp库，用于UDP通信
#include <Ticker.h>// 包含Ticker库，用于定时器中断
#include <WebServer.h>// 包含WebServer库，用于HTTP服务器
#include <Update.h>// 包含Update库，用于OTA更新
#include "esp_camera.h" // 添加摄像头支持头文件
#include "soc/soc.h" // Disable brownout problems
#include "soc/rtc_cntl_reg.h" // Disable brownout problems
enum USV_type {Single_paddle,double_paddle }; // USV类型
enum USV_type USV  = double_paddle; // USV类型，默认双桨模式

// 无刷电机电调和舵机引脚定义，单桨模式
#define ESC_PWM_PIN 3    // 无刷电机电调控制引脚
#define SERVO_PWM_PIN 4  // 舵机控制引脚
// LEDC通道定义
#define ESC_CHANNEL 0    // 电调LED通道，一共0-7个通道pwm
#define SERVO_CHANNEL 1  // 舵机LED通道
#define PWM_FREQs 50      // PWM频率  硬件电路硬性约束50Hz
#define PWM_RESOLUTIONs 12 // PWM分辨率

// 双桨机控制引脚定义
#define ESC_PWM_L 4    // 无刷电机电调左
#define ESC_PWM_R 3    // 无刷电机电调右
// LEDC通道定义
#define PWM_L_CHANNEL 0    // 电调LED通道
#define PWM_R_CHANNEL 1  // 舵机LED通道
#define PWM1_FREQs 50      // PWM频率  硬性约束50Hz
#define PWM1_RESOLUTIONs 12 // PWM分辨率

#define LED_pin 0
#define LED_LEFT_PIN 5     // 左侧转向灯
#define LED_RIGHT_PIN 6    // 右侧转向灯
#define TURN_DEADBAND 50   // 转向灯死区，避免轻微偏差误触发


#define interrupt_time_control 100 // 定时器中断时间

// WiFi配置 extern 声明，只声明，不定义,实际变量在main.cpp中定义
extern const char* ssid;
extern const char* password;

// UDP配置
extern WiFiUDP udp; // UDP对象
extern IPAddress serverIP; // 服务器IP地址
extern IPAddress piServerIP; // 服务器IP地址
extern IPAddress rkserverIP;     // 服务器IP地址
extern IPAddress dfgServerIP;    // 服务器IP地址
extern unsigned int serverPort; // 服务器端口
extern unsigned int piServerPort; // 服务器端口
extern unsigned int localPort; // 本地端口
extern unsigned int cameraPort; // 相机端口

// 相机配置
extern bool cameraEnabled; // 相机是否启用
extern TaskHandle_t cameraTaskHandle; // 相机任务句柄 FreeRTOS任务句柄(任务的身份证)

// 全局变量
extern int throttle; // 无刷电机电调PWM值
extern int steering; // 舵机PWM值
extern int pwm_left; // 无刷电机电调左PWM值
extern int pwm_right; // 无刷电机电调右PWM值
extern bool otaMode; // OTA模式

// 全局变量
extern int adcValue; // ADC值单片机只能处理数字信号，现实世界模拟信号，分辨率12位，范围0-4095，每个单位0.8mV，输入电压 = adcValue × 3.3 / 4095
extern float temperature; // 温度

// 函数声明
int convertPWM_single(int pwmValue); // 单桨模式PWM值转换
int convertPWM_double(int pwmValue); // 双桨模式PWM值转换
void Set_Single_paddle_Pwm(int throttle_pwm, int steering_pwm); // 单桨模式设置PWM值
void Set_Double_paddle_Pwm(int throttle_pwm, int steering_pwm); // 双桨模式设置PWM值
void resetControls(); // 重置控制变量
void restartSystem(); // 重启系统
void startCamera(); // 启动相机
void stopCamera(); // 停止相机
bool initCamera(); // 初始化相机
void deinitCamera(); // 反初始化相机
void sendImageUDP(camera_fb_t * fb); // 发送相机图像到UDP服务器 ，参数为相机图像指针    
void cameraTask(void *pvParameters); // 相机任务函数，用于处理相机数据
void startOTA(); // 启动OTA更新
void commend_parse(String incomingPacket); // 解析收到的命令
void setTurnLEDState(int left, int right); // 设置转向灯状态
void updateTurnLEDs(); // 更新转向灯状态
bool handleLedCommand(String incomingPacket); // 处理LED灯命令
void control(); // 控制函数
void calibrateESC(); // 单桨校准电调
void calibratePWM(); // 校准PWM值
bool sendUdpMessageTo(IPAddress ip, unsigned int port, String message); // 发送UDP消息到指定IP和端口
bool sendUdpMessage(String message);     // 发送UDP消息到4个服务器
void readUdpData(void *parameter); // 读取UDP数据，参数为任务指针
String buildRegisterMessage(); // 构建船的注册消息
String buildStatusMessage(int adcValue, float temperature); // 构建状态消息
String buildHeartbeatMessage(); // 构建心跳消息
String buildcommandMessage(String message); // 构建命令消息
#endif // MAIN_HPP
