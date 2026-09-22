#RKLLM 大模型接口测试（连 192.168.6.20:8080 的对话 API）
import sys
import requests
import json

# ================== 配置区 ==================
# 修改这里的 IP 地址为你的板子 IP
SERVER_IP = '192.168.6.20' 
SERVER_PORT = '8080'

# 修复点：RKLLM 服务通常挂载在根路径，而不是 /generate
# 请确保这个地址和你服务端运行的地址一致
API_ENDPOINT = f'http://{SERVER_IP}:{SERVER_PORT}/rkllm_chat'

# ==========================================
# 创建会话对象
session = requests.Session()
session.keep_alive = False
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount('https://', adapter)
session.mount('http://', adapter)

def get_current_temperature(location: str, unit: str = "celsius"):
    """模拟获取当前温度"""
    print(f" -> [函数调用模拟] 正在查询 {location} 的当前温度...")
    return {
        "temperature": 26.1,
        "location": location,
        "unit": unit,
        "description": "sunny"
    }

def get_temperature_date(location: str, date: str, unit: str = "celsius"):
    """模拟获取指定日期温度"""
    print(f" -> [函数调用模拟] 正在查询 {location} 在 {date} 的温度...")
    return {
        "temperature": 25.9,
        "location": location,
        "date": date,
        "unit": unit
    }

def get_function_by_name(name):
    """根据名称返回函数对象"""
    functions = {
        "get_current_temperature": get_current_temperature,
        "get_temperature_date": get_temperature_date
    }
    return functions.get(name)

def main():
    print(f"尝试连接到服务器: {API_ENDPOINT}")
    print("============================")
    print("🚀 RKLLM 客户端已启动 (输入 'exit' 退出, 'clear' 清空历史)")
    print("============================")

    # 初始化消息历史
    messages = [
        {"role": "system", "content": f"You are a helpful assistant. Current Date: 2026-06-02"}
    ]

    while True:
        try:
            user_input = input("\n👤 你: ")
            
            if user_input.lower() == 'exit':
                break
            if user_input.lower() == 'clear':
                messages = messages[:1] # 保留 system 消息
                print("🧹 已清空对话历史。")
                continue

            # 添加用户输入到历史
            messages.append({"role": "user", "content": user_input})

            # 定义工具（函数）列表
            TOOLS = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_current_temperature",
                        "description": "Get current temperature at a location.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "The location to get the temperature for."},
                                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "The unit to return the temperature in."},
                            },
                            "required": ["location"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_temperature_date",
                        "description": "Get temperature at a location and date.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "The location to get the temperature for."},
                                "date": {"type": "string", "description": "The date to get the temperature for (YYYY-MM-DD)."},
                                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "The unit to return the temperature in."},
                            },
                            "required": ["location", "date"],
                        },
                    },
                },
            ]

            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'not_required'
            }

            # 构建请求数据
            data = {
                "model": 'qwen-1.8b-chat',
                "messages": messages,
                "stream": False,
                "enable_thinking": False,
                "tools": TOOLS
            }

            # 发送请求
            response = session.post(API_ENDPOINT, json=data, headers=headers, stream=False, verify=False)

            if response.status_code == 200:
                response_data = response.json()
                assistant_message = response_data["choices"][0]["message"]
                content = assistant_message.get("content", "")
                
                # 检查是否是函数调用请求
                if "function_call" in assistant_message:
                    fn_call = assistant_message["function_call"]
                    fn_name = fn_call["name"]
                    fn_args = json.loads(fn_call["arguments"])
                    
                    print(f" -> 模型请求调用函数: {fn_name} with {fn_args}")
                    
                    # 把模型的回复（包含函数调用指令）加到历史
                    messages.append(assistant_message)
                    
                    # 执行函数
                    func = get_function_by_name(fn_name)
                    if func:
                        try:
                            fn_result = func(**fn_args)
                            # 把函数执行结果加到历史
                            messages.append({
                                "role": "tool",
                                "name": fn_name,
                                "content": json.dumps(fn_result, ensure_ascii=False)
                            })
                            
                            # 再次发送请求，让模型生成最终的人类可读回复
                            second_response = session.post(API_ENDPOINT, json={
                                "model": 'qwen-1.8b-chat',
                                "messages": messages,
                                "stream": False,
                                "enable_thinking": False,
                                "tools": TOOLS
                            }, headers=headers, verify=False)
                            
                            if second_response.status_code == 200:
                                final_content = second_response.json()["choices"][0]["message"]["content"]
                                print(f"\n🤖 助手: {final_content}")
                                # 把最终回复存入历史
                                messages.append({"role": "assistant", "content": final_content})
                            else:
                                print(" -> 第二次请求失败:", second_response.text)
                        except Exception as e:
                            print(" -> 函数执行出错:", e)
                    else:
                        print(" -> 未找到对应函数")
                else:
                    # 普通对话回复
                    print(f"\n🤖 助手: {content}")
                    messages.append({"role": "assistant", "content": content})
                    
            else:
                print(" -> 请求失败:", response.status_code, response.text)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(" -> 发生异常:", e)

if __name__ == '__main__':
    main()