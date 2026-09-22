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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from    collect_global.common.logManager import output, outputMode,enum_Error
class CustomHandler(logging.StreamHandler):
    """自定义处理器，重载写入方法"""
    
    def emit(self, record):
        """
        重载 emit 方法，这是实际写入日志的方法
        """
        try:
            msg = self.format(record)
            output(msg)
            # 自定义写入逻辑
            #self.custom_write(msg)
            
            # 或者调用父类的写入方法（写入到流）
            # self.stream.write(msg + self.terminator)
            
            #self.flush()
        except Exception:
            self.handleError(record)
    
    def custom_write(self, msg):
        """完全自定义的写入函数"""
        # 这里可以写入到任何地方
        print(f"[自定义写入] {msg}")
        
        # 示例：同时写入到文件和控制台
        with open('custom.log', 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
        
        # 或者发送到远程服务器、数据库等
        # send_to_remote(msg)
custom_handler = CustomHandler()
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
custom_handler.setFormatter(formatter)
logger.addHandler(custom_handler)

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
        #配制信息
        self.config = config
        #得到订阅端口
        self.subscribe_endpoints = config.get('subscribe_endpoints', ['tcp://*:5555'])
        #得到发布端口
        self.publish_endpoint = config.get('publish_endpoint', 'tcp://*:5556')
        #订阅主题
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
                        logger.debug(f"转发消息: {message}")
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
    #同步启动,会阻塞在此函数,正常不会使用,只有在调试时使用,以便跟踪代码
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
    #异步运行,这样可以处理其它数据,正常使用此功能   
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
                self.sub_socket = None
            if self.pub_socket:
                self.pub_socket.close()
                self.pub_socket = None
            # 注意：我们不关闭context，因为它可能被共享
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
#这个是zmq服务,用于单一程序中使用,他可以订阅,并处理订阅消息,也可以定时发布,还可以处理控制
class ZMQService:
    def __init__(self, publish_port=None, subscribe_port=None, control_port=None):
        """
        ZMQ转发服务
        :param publish_port: 发布端口
        :param subscribe_port: 订阅端口  
        :param control_port: 控制端口
        """
        self.context        = zmq.Context()
        
        # 端口配置
        self.publish_port   = publish_port
        #发布的回调函数
        self.pub_list       = []
        #发布数据锁
        self.pub_lock       = threading.Lock()
        #发布信号
        self.pub_event      = threading.Event()

        self.subscribe_port = subscribe_port
        self.sub_callback   = None
        # 主题到订阅者的映射
        self.topic_subscribers: Dict[str, List[str]] = {}
        
        self.control_port   = control_port
        self.control_callback = None
        # 运行标志
        self.running = False
        
        logger.info(f"转发服务初始化 - 发布端口: {publish_port}, 订阅端口: {subscribe_port}, 控制端口: {control_port}")
    def copyPubList(self,maxnum):
        pass
        
    def start_publisher(self):
        """启动发布者服务"""
        publisher = self.context.socket(zmq.PUB)
        publisher.bind(f"tcp://*:{self.publish_port}")
        
        logger.info(f"发布者已启动，监听端口: {self.publish_port}")
        
        try:
            while self.running:
                if self.pub_event.wait(100) is False:
                    continue
                self.pub_event.clear()#关闭事件,否则会一直有信号
                while self.running:
                    pubList = self.copyPubList(None)
                    if not pubList:
                        break
                    for mem in pubList:
                        publisher.send

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
    
    
    def start_control_service(self):
        """启动控制服务"""
        control = self.context.socket(zmq.REP)
        control.bind(f"tcp://*:{self.control_port}")
        
        logger.info(f"控制服务已启动，监听端口: {self.control_port}")
        
        try:
            poller = zmq.Poller()
            poller.register(control, zmq.POLLIN)
            
            while self.running:
                try:
                    events = dict(poller.poll(timeout=1000))  # 1秒超时

                    message = control.recv_multipart(flags=zmq.NOBLOCK)
                    
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
    
    def stop(self):
        """停止服务"""
        self.running = False
        logger.info("服务已停止")



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

