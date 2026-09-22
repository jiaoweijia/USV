import datetime
import  time
from    enum import unique, Enum, auto
import  threading
from    typing import Tuple
from    .log_helper import logHelper

#输出日志类型，按位与，默认为255
g_logType=255
#定义日志帮助类，默认为空
g_logHelper:logHelper = None

@unique#枚举类修饰符，唯一检查
class outputMode(Enum):
    '''
    管理器类型枚举类
    '''
    none    = 0 #默认值
    srceen  = 1 #屏幕输出
    saveLog = 2 #保存日志,并在屏幕输出
#输出日志锁，防止并发
ouputLock = threading.Lock()
##############增加下面枚举时要注意对应的errorArray也要增加
@unique#枚举类修饰符，唯一检查
class enum_Error(Enum):#第一个会根据配制信息按位与得到是否显示,第二个是对应类型文字转换数组
    default     = (0    ,"默认类型") #"默认类型"
    localErr    = (1    ,"本地错误") #"本地错误"
    localInfo   = (2    ,"本地信息") #"本地信息"
    protocolErr = (4    ,"协议错误") #"协议错误"
    formatErr   = (8    ,"格式错误") #"格式错误"
    netError    = (16   ,"网络错误") #"网络错误"
    warning     = (32   ,"警告信息") #"警告信息"
    debug       = (64   ,"调试信息") #"调试信息"
    otherErr    = (128  ,"其他错误") #"其他错误"
    @classmethod
    def from_code(cls, code):
        for member in cls:
            if member.value[0] == code:
                return member.value
        return enum_Error.default.value

#class enum_Error(Enum):#第一个会根据配制信息按位与得到是否显示,第二个是对应类型文字转换数组
#    default     = (0    ,0) #"默认类型"
#    localErr    = (1    ,1) #"本地错误"
#    localInfo   = (2    ,2) #"本地信息"
#    protocolErr = (4    ,3) #"协议错误"
#    formatErr   = (8    ,4) #"格式错误"
#    netError    = (16   ,5) #"网络错误"
#    warning     = (32   ,6) #"警告信息"
#    debug       = (64   ,7) #"调试信息"
#    otherErr    = (128  ,8) #"其他错误"
#错误类型对应的文本描述数组,如果增加枚举,要同时增加错误类型数组
#logArray = [
#    "默认类型",
#    "本地错误",
#    "本地信息",
#    "协议错误",
#    "格式错误",
#    "网络错误",
#    "警告信息",
#    "调试信息",
#    "其他错误"
#]
#logArray = {
#    enum_Error.default    .value:"默认类型",
#    enum_Error.localErr   .value:"本地错误",
#    enum_Error.localInfo  .value:"本地信息",
#    enum_Error.protocolErr.value:"协议错误",
#    enum_Error.formatErr  .value:"格式错误",
#    enum_Error.netError   .value:"网络错误",
#    enum_Error.warning    .value:"警告信息",
#    enum_Error.debug      .value:"调试信息",
#    enum_Error.otherErr   .value:"其他错误"
#}
#########
def buildLogHelper(name:str,path:str,level:int,run=False)->Tuple[bool,str]:
    bRes    = False
    strRes  = ''
    try:
        global g_logType,g_logHelper
        g_logType   = level
        g_logHelper = logHelper(name,path)
        if run :    runLog(name,path)
        bRes = True
    except Exception as e:
        strRes = f'{e}'
    return bRes,strRes
def runLog(name,path):
    global g_logHelper
    if g_logHelper is not None:
        g_logHelper.log_run(name,path,True)
def stopLog():
    global g_logHelper
    if g_logHelper is not None:
        g_logHelper.log_stop()

def output(info,nmode:outputMode=outputMode.saveLog,logType=enum_Error.localInfo):
    try:
        global g_logType,g_logHelper
        if g_logType &logType.value[0] == 0:
            return
        #if logType.value[1] >= 0 or logType.value[1] < len(logArray):   
        #    info = f'[{logArray[logType.value[1]]}]:{info}'
        #info = f'[{logArray.get(logType.value,"未知")}]:{info}'
        info = f'[{logType.value[1]}]:{info}'
        now = datetime.datetime.now()
        with ouputLock:
            if   nmode.value == 0:    return
            elif nmode.value == 1:    print(now.strftime("%H:%M:%S.") + f"{now.microsecond:06.0f}"[:3] + " " +info)
            elif nmode.value == 2:
                if g_logHelper is not None:
                    g_logHelper.log_save_1(info)
                else:
                    print(now.strftime("%H:%M:%S.") + f"{now.microsecond:06.0f}"[:3] + " " +info)
            else:
                print(now.strftime("%H:%M:%S.") + f"{now.microsecond:06.0f}"[:3] + " " +info)
    except Exception as e:
        print(now.strftime("%H:%M:%S.") + f"{now.microsecond:06.0f}"[:3] + " " + f'输出日志错误:错误信息:{e}-输出信息:{info}')