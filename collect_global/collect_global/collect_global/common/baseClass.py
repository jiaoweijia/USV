#基类，不包含其它包
import threading
from typing import Optional
#日志接口
from ..common.logManager import output, outputMode,enum_Error
from . import commonTools as tools
class ADict(dict):
    """
    Accessing dict keys like an attribute.
    """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__  # type: ignore

#普通基类，包含常用锁,可以扩展其它通用的成员或者函数
class commonBase:
    def __init__(self):
        self.dataLock       = threading.Lock()      #数据锁,只有做锁数据，里面没有任务其它锁
        self.interfaceLock  = threading.Lock()      #功能锁，外部调用接口锁，防止多线程并发
        self.threadLock     = threading.Lock()      #线程锁，如果有多线程，防止并发，里面可以锁数据
#线程基类,用于开启线程,dev为具体的线程实例
class deviceThread:
    def __init__(self, name, dev):
        self.name               = name              #线程名称
        self.dev                = dev               #设备，不同的操作，dev对应参数类型
        self.runFlag            = True              #线程运行标志
        self.handle             = None              #线程句柄
        self.threadEvent        = threading.Event() #处理信号
        self.threadWaitEvent    = threading.Event() #等待信号,用于重新连接使用
        self.threadWait         = 1000              #默认1000毫秒
    #运行线程
    def _run(self):
        self._stop()
        try:
            self.runFlag = True         #设置运行标识为True
            self.threadEvent.clear()    #清理事件信号
            self.threadWaitEvent.set()  #启动时直接连接
            #生成线程实例  target指定线程运行函数,args,指定参数信息,daemon表示主线程退出此线程退出
            self.handle  = threading.Thread(target=self.run, args=(self.dev,),daemon=True)  
            #启动线程
            self.handle.start()
        except Exception as e:
            output(f'[异常]:[deviceThread._run]:运行线程失败{e}',outputMode.saveLog,enum_Error.localErr)
    def _stop(self):
        self.runFlag = False
        self.threadEvent.set()
        self.threadWaitEvent.set()
        if self.handle != None:
            self.handle.join()
            self.handle = None
        self.threadEvent.clear()
        self.threadWaitEvent.clear()
    def _flush(self):
        self.threadEvent.set()
    #默认运行函数,会输出需要重载日志
    def run(self,dev):
        nWaitTime = self.threadWait/1000 #等待转换成秒
        while self.runFlag:
            self.threadEvent.wait(nWaitTime)
            self.threadEvent.clear()
            if self.runFlag is False:
                break
            output(f'[deviceThread]:没有重载,请重载使用',outputMode.saveLog,enum_Error.warning)
#参数基类,参数中可以使用目标类,方便于扩展性,不方便的是可读性差一些
class paraBase(commonBase):
    def __init__(self,data,target_class):
        super().__init__()
        self.memberList = []
        if data is None or target_class is None:
            return
        for val in data:
            try:
                self.memberList.append(target_class(val))
            except Exception as e:
                output(f'[异常]:[paraBase.__init__]:异常:{e}',outputMode.saveLog,enum_Error.localErr)
    def parseData(self,data = None,clearData = True,target_class =None):
        if clearData is True:
            self.memberList.clear()
        if data is None or target_class is None:
            return
        for val in data:
            try:
                self.memberList.append(target_class(val))
            except Exception as e:
                output(f'[异常]:[paraBase.parseData]:异常:{e}',outputMode.saveLog,enum_Error.localErr)
#设备基类,为了保证其它调用接口不报错
class deviceBase(commonBase):
    def __init__(self):
        super().__init__()
    def dual_data(self,data):
        pass

class dualDataBase(deviceThread,commonBase):
    def __init__(self,name='default',dev:Optional[deviceBase] = None):
        deviceThread.__init__(self,name,dev)
        commonBase.__init__(self)
        self.dev = dev
        self.dataList = []
        self._run()
        
    #处理数据线程
    def run(self,dev):
        nWaitTime = self.threadWait/1000 #等待转换成秒
        while self.runFlag:
            self.threadEvent.wait(nWaitTime)
            self.threadEvent.clear()
            if self.runFlag is False:
                break
            while self.runFlag:
                dataList = self.copyData(None)
                if not dataList: break
                for data in dataList:
                    if self.dev: self.dev.dual_data(data)
    #增加数据,通知线程
    def addData(self,data):
        with self.dataLock:
            #增加数据过大后,删除处理不过来的数据
            # if len(self.dataList) > 1000:
            #     self.dataList = self.dataList[300:]
            self.dataList.append(data)
        self.threadEvent.set()
    #复制列表
    def copyData(self,num=None):
        bList=[]
        with self.dataLock:
            size = len(self.dataList)
            if num is None or num >= size:
                bList=self.dataList[0:]
                self.dataList.clear()
            else:
                bList=self.dataList[0:num]
                self.dataList=self.dataList[num:]
        return bList


#add by lhl 20251224
#增加采集设备基类
class PLC_Device_Base():
    def __init__(self):
        pass
    #基类设置值接口,需要在子类中实现
    def setVals(self,nodeInfo,val):
        output(f'[异常]:[PLC_Device_Base.setVals]:需要重载',outputMode.saveLog,enum_Error.localErr)
        pass
#写操作维护,用于设备定时读取指定数据,以检测tcp是否通信正常线程
class PLC_Device_WriteBase(deviceThread,commonBase):
    def __init__(self,dev,name):
        #继承二个基类,分别初始化基类
        deviceThread.__init__(self,name,dev)     #包含运行的信号和run接口
        commonBase  .__init__(self)     #包含三个基本的数据锁
        ###
        self.dev        = dev           #设备信息
        self.writePlc   = None          #写设备的实例
        self.lastTime   = None          #读取信息时间来判断是否超时
    #析构函数
    def __del__(self):
        self._stop()#停止线程
    def setReadTime(self,readTime):
        with self.dataLock:
            self.lastTime = readTime
    def readTime(self):
        nReadTime = 0
        with self.dataLock:
            nReadTime = self.lastTime
        return nReadTime

    def run(self,devInfo):
        output(f"[PLC_Device_WriteBase]:{self.name}-定期读取线程启动",outputMode.saveLog,enum_Error.localInfo)
        checkInterval = 1#秒
        readTimeDiv   = 1000#毫秒
        while self.runFlag:
            try:
                self.threadWaitEvent.wait(checkInterval)
                self.threadWaitEvent.clear()
                if self.runFlag is False:
                    break
                nTime = self.readTime()
                if nTime is None or (tools.timeManager.get_timestamp_ms() - nTime) >readTimeDiv:
                    if self.readVal() is True:
                        self.setReadTime(tools.timeManager.get_timestamp_ms())
            except Exception as e:
                output(f"[异常]:[{tools.cmn(self)}]:错误:{e}",outputMode.saveLog,enum_Error.localErr)
        output(f"[PLC_Device_WriteBase.run]:[退出]",outputMode.saveLog,enum_Error.localErr)
