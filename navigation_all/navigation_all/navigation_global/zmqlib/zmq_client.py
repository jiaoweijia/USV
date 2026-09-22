import zmq
import threading
import json
import time
from typing import List, Dict, Any
import signal
import sys
import logging
from collect_global.common.baseClass import deviceThread
from collect_global.common import commonTools as tools
from    enum import unique, Enum, auto
from .zmq_define import *
from collect_global.pynet.redisMgr import dualDataBase
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ZMQForwarder")

class e_zmq_client(Enum):
    none    = (-1,  "未定义")
    pub     = (0,   "发布")
    sub     = (1,   "订阅")
   
class ZMQClient(deviceThread):
    """
    简单的ZMQ客户端示例，用于测试
    """
    def __init__(self,name,dev = None,sub:zmqMember=None,subTopics=[],pub:zmqMember=None):
        deviceThread.__init__(self,name,dev)
        self.callback = None
        self.zmqSubContext = None
        self.zmqSubSocket = None
        self.zmqPubContext = None
        self.zmqPubSocket = None
        self.dualThread = None
        if sub:
            self.dualThread = dualDataBase("",self)#内部启动
            self.zmqSubContext,self.zmqSubSocket = ZMQClient.create_subscriber(sub.to_string())
            for topic in subTopics:
                self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE,topic)
            time.sleep(1)  # 给SUB端时间连接
        if pub:
           self.zmqPubContext,self.zmqPubSocket = ZMQClient.create_publisher(pub.to_string())
    def pubInfo(self,topic,message):
        self.pubInfoByte(topic.encode(), message.encode())
    def pubInfoByte(self,topic,message):
        if self.zmqPubSocket :self.zmqPubSocket.send_multipart([topic, message])
    def dual_data(self,data):
        print(data)
    def run(self,dev):    
        nWaitTime = self.threadWait/1000 #等待转换成秒
        while self.runFlag:
            self.threadEvent.wait(nWaitTime)
            self.threadEvent.clear()
            if self.runFlag is False:
                break
            try:
                while self.runFlag:
                    if self.zmqSubSocket:
                        message = self.zmqSubSocket.recv_multipart()
                        if message and self.dualThread:
                            self.dualThread.addData(message)
            except Exception as e:
                pass
    
    @staticmethod
    def create_publisher(endpoint: str, topic: str = ""):
        """创建发布者"""
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.connect(endpoint)
        logger.info(f"发布者已创建，端点: {endpoint}")

        time.sleep(1)
        return context, socket
    
    @staticmethod
    def create_subscriber(endpoint: str, topic: str = ""):
        """创建订阅者"""
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(endpoint)
        
        if topic:
            socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        else:
            socket.setsockopt_string(zmq.SUBSCRIBE, "")  # 订阅所有消息
        time.sleep(1)
        logger.info(f"订阅者已创建，端点: {endpoint}, 主题: {topic or '所有'}")
        return context, socket



