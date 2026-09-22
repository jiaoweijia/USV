import collect_global.common.define as defineInterface
from .zmq_server import ZMQForwarderServer
class zmqMember():
    def __init__(self,host,port):
        self.host = host
        self.port = port
    def to_string(self):
        return f'tcp://{self.host}:{self.port}'
class zmqInfo():
    def __init__(self,obj):
        self.pubProxy = None
        self.subProxy = []
        self.server = None
        if obj is None:
            return
        self.pubProxy = zmqMember(obj.get("host","localhost"),obj.get("port",5555))
        zmqVal = obj.get("sub_setting",[])
        for sub in zmqVal:
            self.subProxy.append(zmqMember(sub.get("host","localhost"),sub.get("port",5556)))
    def to_config(self):
        dictRes = {}
        dictRes['subscribe_endpoints'] = [m.to_string() for m in self.subProxy]
        dictRes['publish_endpoint']     = self.pubProxy.to_string()
        return dictRes
    def run(self):
        config = defineInterface.loadJsonNode.toJsonString(self.to_config())
        try:
            self.server = ZMQForwarderServer(self.to_config())
            if self.server is None:
                raise Exception("生成实例失败")
            self.server.start_in_background()
        except Exception as e:
            if self.server is not None:self.server.stop()
            self.server = None
    def stop(self):
        if self.server is not None: self.server.stop()
        self.server = None
class zmqProxyMgr():
    def __init__(self,zmqProxyList):
        self.proxyList =[]
        for zmq in zmqProxyList:
            self.proxyList.append(zmqInfo(zmq))

    def run(self):
        for zmq in self.proxyList:
            zmq.run()

        # context = zmq.Context()
    
        # # 前端接收订阅者连接
        # frontend = context.socket(zmq.XSUB)
        # frontend.bind("tcp://*:5556")
    
        # # 后端接收发布者连接
        # backend = context.socket(zmq.XPUB)
        # backend.bind("tcp://*:5555")
    
        # zmq.proxy(frontend, backend)
        #zmq.proxy()
    def stop(self):
        for zmq in self.proxyList:
            zmq.stop()




