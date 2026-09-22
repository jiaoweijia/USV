import os
for _ in range(2):
    try:
        import  zmq
        break #导入成功跳出,
    except ModuleNotFoundError as e:
        print(f"[导入zmq包]:[错误]:{e}")
        #if sys.version.find('3.7.') != -1:
        os.system('pip install zmq')
        #else:
        #    os.system('pip install zmq')

import threading
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import zmq
import threading
import json
import time
from typing import List, Dict, Any
import signal
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ZMQForwarder")

class ZMQForwarderServer:
    """
    ZMQ 订阅转发服务器
    从多个发布者接收消息，并转发给多个订阅者
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化转发服务器
        
        Args:
            config: 配置字典，包含：
                - subscribe_endpoints: 订阅端口列表（监听发布者）
                - publish_endpoint: 发布端口（供订阅者连接）
                - context: ZMQ上下文（可选）
                - topics: 要订阅的主题列表，None表示订阅所有主题
        """
        self.config = config
        self.subscribe_endpoints = config.get('subscribe_endpoints', ['tcp://*:5555'])
        self.publish_endpoint = config.get('publish_endpoint', 'tcp://*:5556')
        self.topics = config.get('topics', [])  # 空列表表示订阅所有主题
        self.running = False
        
        # 创建ZMQ上下文
        self.context = config.get('context', zmq.Context())
        
        # 创建socket
        self.sub_socket = None
        self.pub_socket = None
        
        # 统计信息
        self.stats = {
            'messages_received': 0,
            'messages_forwarded': 0,
            'errors': 0,
            'start_time': None
        }
    
    def setup_sockets(self):
        """设置ZMQ sockets"""
        try:
            # 创建订阅socket（XPUB模式，用于接收发布者的消息）
            self.sub_socket = self.context.socket(zmq.XSUB)
            self.sub_socket.setsockopt(zmq.LINGER, 0)
            
            # 绑定到所有订阅端点
            for endpoint in self.subscribe_endpoints:
                self.sub_socket.bind(endpoint)
                logger.info(f"订阅端点绑定: {endpoint}")
            
            # 创建发布socket（XSUB模式，用于向订阅者发送消息）
            self.pub_socket = self.context.socket(zmq.XPUB)
            self.pub_socket.setsockopt(zmq.LINGER, 0)
            self.pub_socket.bind(self.publish_endpoint)
            logger.info(f"发布端点绑定: {self.publish_endpoint}")
            
            # 如果需要订阅特定主题，发送订阅请求
            if self.topics:
                for topic in self.topics:
                    if isinstance(topic, str):
                        # 添加消息前缀（ZMQ约定）
                        topic_bytes = topic.encode('utf-8')
                        subscription = b'\x01' + topic_bytes
                        self.sub_socket.send(subscription)
                        logger.info(f"订阅主题: {topic}")
            
            logger.info("ZMQ sockets 设置完成")
            
        except Exception as e:
            logger.error(f"设置sockets时出错: {e}")
            self.cleanup()
            raise
    
    def forward_messages(self):
        """转发消息的主循环"""
        logger.info("开始转发消息...")
        
        # 使用poll进行非阻塞I/O
        poller = zmq.Poller()
        poller.register(self.sub_socket, zmq.POLLIN)
        poller.register(self.pub_socket, zmq.POLLIN)
        
        while self.running:
            try:
                events = dict(poller.poll(timeout=1000))  # 1秒超时
                
                # 处理来自发布者的消息
                if self.sub_socket in events:
                    message = self.sub_socket.recv_multipart()
                    if message:
                        self.stats['messages_received'] += 1
                        
                        # 转发消息给订阅者
                        self.pub_socket.send_multipart(message)
                        self.stats['messages_forwarded'] += 1
                        
                        # 调试：打印消息内容（前100字符）
                        if logger.isEnabledFor(logging.DEBUG):
                            try:
                                msg_str = ' | '.join([part[:100].decode('utf-8', errors='ignore') 
                                                    for part in message])
                                logger.debug(f"转发消息: {msg_str}")
                            except:
                                pass
                
                # 处理来自订阅者的订阅/取消订阅请求
                if self.pub_socket in events:
                    message = self.pub_socket.recv()
                    if message:
                        # 第一个字节是订阅/取消订阅标志
                        if message[0] == 1:
                            topic = message[1:].decode('utf-8', errors='ignore')
                            logger.info(f"新的订阅: {topic}")
                        elif message[0] == 0:
                            topic = message[1:].decode('utf-8', errors='ignore')
                            logger.info(f"取消订阅: {topic}")
                        # 将订阅请求转发给发布者
                        self.sub_socket.send(message)
                
                # 定期打印统计信息
                if self.stats['messages_received'] % 1000 == 0 and self.stats['messages_received'] > 0:
                    self.print_stats()
                    
            except zmq.ZMQError as e:
                if self.running:  # 只有运行时才记录错误
                    logger.error(f"ZMQ错误: {e}")
                    self.stats['errors'] += 1
            except Exception as e:
                if self.running:  # 只有运行时才记录错误
                    logger.error(f"转发消息时出错: {e}")
                    self.stats['errors'] += 1
    
    def print_stats(self):
        """打印统计信息"""
        if self.stats['start_time']:
            elapsed = time.time() - self.stats['start_time']
            rate = self.stats['messages_received'] / elapsed if elapsed > 0 else 0
            logger.info(
                f"统计: 接收={self.stats['messages_received']}, "
                f"转发={self.stats['messages_forwarded']}, "
                f"错误={self.stats['errors']}, "
                f"速率={rate:.2f} msg/sec"
            )
    
    def start(self):
        """启动转发服务器"""
        if self.running:
            logger.warning("服务器已经在运行")
            return
        
        logger.info("启动ZMQ转发服务器...")
        self.running = True
        self.stats['start_time'] = time.time()
        
        try:
            self.setup_sockets()
            
            # 在主线程中运行转发循环
            self.forward_messages()
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"服务器运行时出错: {e}")
        finally:
            self.stop()
    
    def start_in_background(self):
        """在后台线程中启动服务器"""
        if self.running:
            logger.warning("服务器已经在运行")
            return
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        try:
            self.setup_sockets()
            
            # 在新线程中运行转发循环
            self.thread = threading.Thread(target=self.forward_messages, daemon=True)
            self.thread.start()
            
            logger.info("ZMQ转发服务器在后台线程中启动")
            
        except Exception as e:
            logger.error(f"启动后台服务器时出错: {e}")
            self.stop()
    
    def stop(self):
        """停止服务器"""
        if not self.running:
            return
        
        logger.info("正在停止ZMQ转发服务器...")
        self.running = False
        
        # 等待线程结束（如果是后台运行）
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        self.cleanup()
        
        # 打印最终统计
        self.print_stats()
        logger.info("ZMQ转发服务器已停止")
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.sub_socket:
                self.sub_socket.close()
            if self.pub_socket:
                self.pub_socket.close()
            # 注意：我们不关闭context，因为它可能被共享
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")


# class ZMQClient:
#     """
#     简单的ZMQ客户端示例，用于测试
#     """
    
#     @staticmethod
#     def create_publisher(endpoint: str, topic: str = ""):
#         """创建发布者"""
#         context = zmq.Context()
#         socket = context.socket(zmq.PUB)
#         socket.bind(endpoint)
#         logger.info(f"发布者已创建，端点: {endpoint}")
#         return context, socket
    
#     @staticmethod
#     def create_subscriber(endpoint: str, topic: str = ""):
#         """创建订阅者"""
#         context = zmq.Context()
#         socket = context.socket(zmq.SUB)
#         socket.connect(endpoint)
        
#         if topic:
#             socket.setsockopt_string(zmq.SUBSCRIBE, topic)
#         else:
#             socket.setsockopt_string(zmq.SUBSCRIBE, "")  # 订阅所有消息
        
#         logger.info(f"订阅者已创建，端点: {endpoint}, 主题: {topic or '所有'}")
#         return context, socket


# def signal_handler(signum, frame):
#     """处理信号"""
#     logger.info(f"收到信号 {signum}")
#     sys.exit(0)


# def main():
#     """主函数"""
#     # 注册信号处理
#     signal.signal(signal.SIGINT, signal_handler)
#     signal.signal(signal.SIGTERM, signal_handler)
    
#     # 配置转发服务器
#     config = {
#         'subscribe_endpoints': [
#             'tcp://*:5555',  # 接收来自发布者1的消息
#             'tcp://*:5557',  # 接收来自发布者2的消息
#         ],
#         'publish_endpoint': 'tcp://*:5556',  # 向订阅者发布消息
#         'topics': ['news', 'sports', 'weather'],  # 可选：只转发这些主题
#         # 'topics': []  # 空列表表示转发所有主题
#     }
    
#     # 创建并启动服务器
#     server = ZMQForwarderServer(config)
    
#     try:
#         # 直接运行（阻塞）
#         server.start()
        
#         # 或者在后台运行（非阻塞）
#         # server.start_in_background()
#         # while True:
#         #     time.sleep(1)
        
#     except KeyboardInterrupt:
#         logger.info("正在关闭服务器...")
#         server.stop()
#     except Exception as e:
#         logger.error(f"服务器运行出错: {e}")
#         server.stop()


class ZMQForwardService:
    def __init__(self, publish_port=5555, subscribe_port=5556, control_port=5557):
        """
        ZMQ转发服务
        :param publish_port: 发布端口
        :param subscribe_port: 订阅端口  
        :param control_port: 控制端口
        """
        self.context = zmq.Context()
        
        # 端口配置
        self.publish_port = publish_port
        self.subscribe_port = subscribe_port
        self.control_port = control_port
        
        # 主题到订阅者的映射
        self.topic_subscribers: Dict[str, List[str]] = {}
        
        # 运行标志
        self.running = False
        
        logger.info(f"转发服务初始化 - 发布端口: {publish_port}, 订阅端口: {subscribe_port}, 控制端口: {control_port}")
    
    def start_publisher(self):
        """启动发布者服务"""
        publisher = self.context.socket(zmq.PUB)
        publisher.bind(f"tcp://*:{self.publish_port}")
        
        logger.info(f"发布者已启动，监听端口: {self.publish_port}")
        
        try:
            while self.running:
                # 等待消息并转发
                time.sleep(0.1)  # 避免CPU占用过高
                
                # 这里可以添加其他处理逻辑
                # 在实际应用中，这里可能会从数据库或其他源获取数据
                
        except KeyboardInterrupt:
            logger.info("发布者服务被中断")
        finally:
            publisher.close()
    
    def start_subscriber(self):
        """启动订阅者服务（接收订阅请求）"""
        subscriber = self.context.socket(zmq.REP)
        subscriber.bind(f"tcp://*:{self.subscribe_port}")
        
        logger.info(f"订阅服务已启动，监听端口: {self.subscribe_port}")
        
        try:
            while self.running:
                # 接收订阅请求
                try:
                    message = subscriber.recv_json(flags=zmq.NOBLOCK)
                    
                    if message:
                        action = message.get("action")
                        topic = message.get("topic")
                        client_id = message.get("client_id")
                        
                        if action == "subscribe":
                            # 添加订阅
                            if topic not in self.topic_subscribers:
                                self.topic_subscribers[topic] = []
                            
                            if client_id not in self.topic_subscribers[topic]:
                                self.topic_subscribers[topic].append(client_id)
                                logger.info(f"客户端 {client_id} 订阅了主题: {topic}")
                                subscriber.send_json({"status": "success", "message": f"已订阅主题: {topic}"})
                            else:
                                subscriber.send_json({"status": "info", "message": f"已订阅主题: {topic}"})
                        
                        elif action == "unsubscribe":
                            # 取消订阅
                            if topic in self.topic_subscribers and client_id in self.topic_subscribers[topic]:
                                self.topic_subscribers[topic].remove(client_id)
                                logger.info(f"客户端 {client_id} 取消订阅主题: {topic}")
                                subscriber.send_json({"status": "success", "message": f"已取消订阅主题: {topic}"})
                            else:
                                subscriber.send_json({"status": "error", "message": "未找到订阅记录"})
                        
                        elif action == "list_topics":
                            # 列出所有主题
                            topics = list(self.topic_subscribers.keys())
                            subscriber.send_json({"status": "success", "topics": topics})
                        
                        elif action == "list_subscribers":
                            # 列出主题的订阅者
                            if topic in self.topic_subscribers:
                                subscribers = self.topic_subscribers[topic]
                                subscriber.send_json({"status": "success", "subscribers": subscribers})
                            else:
                                subscriber.send_json({"status": "error", "message": "主题不存在"})
                        
                        else:
                            subscriber.send_json({"status": "error", "message": "未知操作"})
                
                except zmq.Again:
                    # 没有消息，继续循环
                    time.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("订阅服务被中断")
        finally:
            subscriber.close()
    
    def forward_message(self, topic: str, message: Any, metadata: Dict = None):
        """转发消息给所有订阅者"""
        if topic not in self.topic_subscribers or not self.topic_subscribers[topic]:
            logger.warning(f"主题 {topic} 没有订阅者")
            return
        
        try:
            # 创建转发socket
            forward_socket = self.context.socket(zmq.PUB)
            forward_socket.connect(f"tcp://localhost:{self.publish_port}")
            time.sleep(0.1)  # 给连接时间
            
            # 构建消息
            msg_data = {
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
                "data": message,
                "subscriber_count": len(self.topic_subscribers[topic])
            }
            
            if metadata:
                msg_data["metadata"] = metadata
            
            # 发布消息
            forward_socket.send_string(f"{topic} {json.dumps(msg_data)}")
            logger.info(f"已转发消息到主题: {topic}, 订阅者数: {len(self.topic_subscribers[topic])}")
            
            forward_socket.close()
            
        except Exception as e:
            logger.error(f"转发消息时出错: {e}")
    
    def start_control_service(self):
        """启动控制服务"""
        control = self.context.socket(zmq.REP)
        control.bind(f"tcp://*:{self.control_port}")
        
        logger.info(f"控制服务已启动，监听端口: {self.control_port}")
        
        try:
            while self.running:
                try:
                    message = control.recv_json(flags=zmq.NOBLOCK)
                    
                    if message:
                        command = message.get("command")
                        
                        if command == "status":
                            # 获取服务状态
                            status = {
                                "topics_count": len(self.topic_subscribers),
                                "total_subscribers": sum(len(subs) for subs in self.topic_subscribers.values()),
                                "topics": {topic: len(subs) for topic, subs in self.topic_subscribers.items()}
                            }
                            control.send_json({"status": "success", "data": status})
                        
                        elif command == "forward":
                            # 手动转发消息
                            topic = message.get("topic")
                            data = message.get("data")
                            metadata = message.get("metadata", {})
                            
                            self.forward_message(topic, data, metadata)
                            control.send_json({"status": "success", "message": "消息已转发"})
                        
                        elif command == "stats":
                            # 获取统计信息
                            stats = {
                                "service_start_time": datetime.now().isoformat(),
                                "topics": self.topic_subscribers
                            }
                            control.send_json({"status": "success", "data": stats})
                        
                        else:
                            control.send_json({"status": "error", "message": "未知命令"})
                
                except zmq.Again:
                    time.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("控制服务被中断")
        finally:
            control.close()
    
    def run(self):
        """启动转发服务"""
        self.running = True
        
        # 启动各个服务线程
        publisher_thread = threading.Thread(target=self.start_publisher, daemon=True)
        subscriber_thread = threading.Thread(target=self.start_subscriber, daemon=True)
        control_thread = threading.Thread(target=self.start_control_service, daemon=True)
        
        publisher_thread.start()
        subscriber_thread.start()
        control_thread.start()
        
        logger.info("ZMQ转发服务已启动")
        
        try:
            # 主线程保持运行
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("正在停止服务...")
            self.stop()
    
    def stop(self):
        """停止服务"""
        self.running = False
        logger.info("服务已停止")


# # 客户端示例
class ZMQClient:
    def __init__(self, client_id: str, forward_service_host="localhost"):
        self.client_id = client_id
        self.context = zmq.Context()
        self.forward_service_host = forward_service_host
        
        # 订阅服务地址
        self.subscribe_service = f"tcp://{forward_service_host}:5556"
        self.publish_service = f"tcp://{forward_service_host}:5555"
        
        logger.info(f"客户端 {client_id} 初始化完成")
    
    def subscribe(self, topic: str):
        """订阅主题"""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.connect(self.subscribe_service)
            
            request = {
                "action": "subscribe",
                "topic": topic,
                "client_id": self.client_id
            }
            
            socket.send_json(request)
            response = socket.recv_json()
            socket.close()
            
            logger.info(f"订阅响应: {response}")
            return response
            
        except Exception as e:
            logger.error(f"订阅失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def unsubscribe(self, topic: str):
        """取消订阅"""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.connect(self.subscribe_service)
            
            request = {
                "action": "unsubscribe",
                "topic": topic,
                "client_id": self.client_id
            }
            
            socket.send_json(request)
            response = socket.recv_json()
            socket.close()
            
            logger.info(f"取消订阅响应: {response}")
            return response
            
        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def start_receiver(self, topics: List[str]):
        """启动消息接收器"""
        def receiver():
            socket = self.context.socket(zmq.SUB)
            socket.connect(self.publish_service)
            
            # 订阅所有指定主题
            for topic in topics:
                socket.setsockopt_string(zmq.SUBSCRIBE, topic)
                logger.info(f"客户端 {self.client_id} 开始监听主题: {topic}")
            
            try:
                while True:
                    try:
                        message = socket.recv_string(flags=zmq.NOBLOCK)
                        if message:
                            topic, data = message.split(' ', 1)
                            message_data = json.loads(data)
                            logger.info(f"客户端 {self.client_id} 收到消息: {message_data}")
                    except zmq.Again:
                        time.sleep(0.1)
                    except Exception as e:
                        logger.error(f"接收消息时出错: {e}")
            except KeyboardInterrupt:
                logger.info(f"客户端 {self.client_id} 接收器已停止")
            finally:
                socket.close()
        
        # 在后台线程中运行接收器
        thread = threading.Thread(target=receiver, daemon=True)
        thread.start()
        return thread


# # 测试和演示
# if __name__ == "__main__":
#     import sys
    
#     if len(sys.argv) > 1 and sys.argv[1] == "server":
#         # 启动服务器
#         print("启动ZMQ转发服务器...")
#         service = ZMQForwardService()
#         service.run()
    
#     elif len(sys.argv) > 1 and sys.argv[1] == "client1":
#         # 客户端1
#         client = ZMQClient("client1")
        
#         # 订阅主题
#         client.subscribe("news")
#         client.subscribe("weather")
        
#         # 启动接收器
#         client.start_receiver(["news", "weather"])
        
#         # 保持运行
#         try:
#             while True:
#                 time.sleep(1)
#         except KeyboardInterrupt:
#             print("客户端1已退出")
    
#     elif len(sys.argv) > 1 and sys.argv[1] == "client2":
#         # 客户端2
#         client = ZMQClient("client2")
        
#         # 订阅主题
#         client.subscribe("news")
#         client.subscribe("sports")
        
#         # 启动接收器
#         client.start_receiver(["news", "sports"])
        
#         # 保持运行
#         try:
#             while True:
#                 time.sleep(1)
#         except KeyboardInterrupt:
#             print("客户端2已退出")
    
#     elif len(sys.argv) > 1 and sys.argv[1] == "producer":
#         # 消息生产者
#         print("启动消息生产者...")
        
#         # 连接到控制端口
#         context = zmq.Context()
#         control = context.socket(zmq.REQ)
#         control.connect("tcp://localhost:5557")
        
#         topics = ["news", "weather", "sports", "stocks"]
        
#         try:
#             message_id = 1
#             while True:
#                 import random
                
#                 topic = random.choice(topics)
#                 message = {
#                     "id": message_id,
#                     "content": f"消息内容 {message_id}",
#                     "source": "producer"
#                 }
                
#                 request = {
#                     "command": "forward",
#                     "topic": topic,
#                     "data": message,
#                     "metadata": {"priority": random.randint(1, 5)}
#                 }
                
#                 control.send_json(request)
#                 response = control.recv_json()
#                 print(f"发送消息: {message_id} 到主题: {topic}, 响应: {response}")
                
#                 message_id += 1
#                 time.sleep(2)
                
#         except KeyboardInterrupt:
#             print("生产者已停止")
#         finally:
#             control.close()
    
#     else:
#         print("请指定运行模式:")
#         print("  python forward_service.py server    - 启动转发服务器")
#         print("  python forward_service.py client1   - 启动客户端1")
#         print("  python forward_service.py client2   - 启动客户端2")
#         print("  python forward_service.py producer  - 启动消息生产者")
