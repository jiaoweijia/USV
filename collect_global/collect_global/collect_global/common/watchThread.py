from    .baseClass import deviceThread,commonBase
#日志输出接口
from    .logManager import output, outputMode,enum_Error
from    . import commonTools as tools
class watchBase(commonBase):
    def __init__(self, uuid,*args, **kwargs):
        super().__init__()
        self.uuid = uuid
        self.lastTime = None
        self.timeOut = None
    def reset(self):
        output(f'[watchBase.reset]:[需要重载]',outputMode.saveLog,enum_Error.localErr)
    def setCurTime(self):
        with self.dataLock:
            self.lastTime = tools.timeManager.get_timestamp_ms()
    def curTime(self):
        nCurTime = None
        with self.dataLock:
            nCurTime = self.lastTime
        return nCurTime
    def setTimeout(self,timeout):
        with self.dataLock:
            self.timeOut = timeout
    def getTimeOut(self):
        nTimeout = None
        with self.dataLock:
            nTimeout = self.timeOut
        return nTimeout
    def isTimeout(self):
        bRes = False
        curTime = self.curTime()
        timeout = self.getTimeOut()
        if curTime is not None and timeout is not None:
            if (tools.timeManager.get_timestamp_ms() - curTime) > timeout:
                bRes = True
        return bRes

class watchManager(deviceThread,commonBase):
    def __init__(self, *args, **kwargs):
        #继承类里super继承第一个类,所以会调用deviceThread
        super().__init__(kwargs.get("name","watchManager"),kwargs.get("dev",None))
        commonBase.__init__(self)#调用基类构造
        self.watchDict={}
    def addWatch(self,val):
        with self.dataLock:
            self.watchDict[val.uuid] = val
    def removeWatch(self,uuid):
        popVal = None
        with self.dataLock:
            #try:
            #   if uuid in self.watchDict:  #增加这个判断,会
            #       del self.watchDict[uuid]   #这种情况,如果不存在则会弹出异常
            #   del self.watchDict[uuid]   #这种情况,如果不存在则会弹出异常
            #except Exception as e:
            #    pass
            popVal = self.pop(uuid,None)#安全弹出,如果没有则返回空,但是不会弹出异常
        return popVal

    def run(self,dev):
        nWaitTime = self.threadWait/1000 #等待转换成秒
        while self.runFlag:
            self.threadEvent.wait(nWaitTime)
            self.threadEvent.clear()
            if self.runFlag is False:
                break
            checkMem = {}
            with self.dataLock:
                checkMem = self.watchDict.copy()
            for k,m in checkMem.items():
                if m.isTimeout(): 
                    output(f"[{tools.cmn(self)}]:[出现超时连接,需要重置]",outputMode.saveLog,enum_Error.localErr)
                    m.reset()
        output(f"[{tools.cmn(self)}]:[检测线程退出]",outputMode.saveLog,enum_Error.localErr)
            
