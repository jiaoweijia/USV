#枚举定义
from    enum import unique, Enum, auto
#结构体定义
from    dataclasses import dataclass
#日志输出接口
from    .logManager import output, outputMode,enum_Error
#通用工具
from    .import commonTools as tools
#json管理
from    .jsonFunc  import*
#基类定义
import  numpy as np
from    .baseClass import*
from    ..protocol.protocol_socket import *
from    ..database.databaseBase import *
from    ..database.mysql import mysqlMgr
from    ..database.sqlite import sqliteMgr
from    ..database.sqlserver import sqlserverMgr
from    ..common.jsonFunc import *
from    ..pynet.redisMgr import redisInfo
from    ..common.watchThread import watchManager
#数据类型参考《SIMATIC STEP 7 Basic_Professional V16 和 SIMATIC WinCC V16.pdf》
@unique#枚举类修饰符，唯一检查,也可以扩展给其它协议使用,这里类型基本全了,不全进行补充,其它协议使用类型也从这里面抽取
class Enum_Data_type(Enum):
    none            =-1 #没有配置
    root            =0  #根节点
    bool            =1  #1字节，bool类型是按照位进行与的，比较特殊在连续的8个bool为一个byte,为了解决特殊，需要在参数表里增加偏移量和位二个字段
    byte            =2  #1字节 有符号整数：-128 到 +127 无符号整数：0 到 255
    word            =3  #2字节 有符号整数：-32,768 到 +32,767 无符号整数：0 到 65,
    dword           =4  #4字节 有符号整数：-2,147,483,648 到 +2,147,483,647 无符号整数：0 到 4,294,967,295
    lword           =5  #8字节 有符号整数：-9,223,372,036,854,775,808 到 +9,223,372,036,854,775,807 无符号整数：0 到 18_446_744_073_709_551_615
    sint            =6  #1字节 有符号整数：-128 到 +127
    usint           =7  #1字节 无符号整数：0 到 255
    int             =8  #2字节 有符号整数：-32,768 到 +32,767 
    uint            =9  #2字节 无符号整数：0 到 65,535
    dint            =10 #4字节 有符号整数：-2,147,483,648 到 +2,147,483,647
    udint           =11 #4字节 无符号整数：0 到 4,294,967,295
    lint            =12 #8字节 有符号整数：-9,223,372,036,854,775,808 到 +9,223,372,036,854,775,807
    ulint           =13 #8字节 无符号整数：0 到 18_446_744_073_709_551_615
    real            =14 #4字节 单精度浮点数
    lreal           =15 #8字节 双精度浮点数
    s5time          =16 #2字节 时间 0-999
    time            =17 #4字节 时间 有符号
    ltime           =18 #8字节 时间 有符号
    date            =19 #2字节 日期，无符号
    time_of_day     =20 #4字节 时间，无符号
    ltod            =21 #8字节 时间，无符号
    date_and_time   =22 #8字节 日期和时间
    ldt             =23 #8字节 日期和时间
    dtl             =24 #12字节 日期和时间
    char            =25 #1字节 字符
    wchar           =26 #2字节 字符
    string          =27 #256字节 字符串
    wstring         =28 #512字节 字符串
    arrayType       =29 #数组,采集不使用,但是配置和计算时会使用
    structType      =30 #结构体，采集不使用,但是配置和计算时会使用
    owntype         =31 #自定义类型，采集不使用,但是配置和计算时会使用
    TON_TIME        =32 #16字节定时器，采集不使用,但是配置和计算时会使用
    HW_IO           =33 #2字节硬件IO，采集不使用,但是配置和计算时会使用
    IEC_TIMER       =34 #16字节IEC定时器，采集不使用,但是配置和计算时会使用
    int_BCD         =35 #2字节BCD码
    dint_BCD        =36 #4字节BCD码

byte_order = ['big','little','big_swap','little_swap']
@unique#枚举类修饰符，唯一检查,也可以扩展给其它协议使用,这里类型基本全了
class enum_byte_order(Enum):
    big         = 0
    little      = 1
    big_swap    = 2
    little_swap = 3

#snap7协议数据转换
def snap7data2Str(data, type,bit,byte_order,reserved=None):
    ''' 参数说明
        data byte数组
        type 数据类型
        bit 偏移量，bool使用
        byte_order 字节序,如果是字符串则是编码方式(ascii,utf-16be)
                          如果是数据，使用编码字节序(big,little)
    '''
    try:
        if data is None or len(data) == 0:
            return ''
        if type == Enum_Data_type.bool.value:
            return str((data[0] & (1 << bit)) != 0)
        elif type == Enum_Data_type.byte.value:
            return str(data[0])
        elif type == Enum_Data_type.word.value:
            return str(tools.bytes_to_int(data[0:2] ,byte_order))
        elif type == Enum_Data_type.dword.value:
            return str(tools.bytes_to_int(data[0:4] ,byte_order))
        elif type == Enum_Data_type.lword.value:
            return str(tools.bytes_to_int(data[0:8] ,byte_order))
        elif type == Enum_Data_type.sint.value:
            return str(tools.bytes_to_int(data[0:1] ,byte_order))
        elif type == Enum_Data_type.usint.value:
            return str(tools.bytes_to_uint(data[0:1],byte_order))
        elif type == Enum_Data_type.int.value:
            return str(tools.bytes_to_int(data[0:2] ,byte_order))
        elif type == Enum_Data_type.uint.value:
            return str(tools.bytes_to_uint(data[0:2],byte_order))
        elif type == Enum_Data_type.dint.value:
            return str(tools.bytes_to_int(data[0:4] ,byte_order))
        elif type == Enum_Data_type.udint.value:
            return str(tools.bytes_to_uint(data[0:4],byte_order))
        elif type == Enum_Data_type.lint.value:
            return str(tools.bytes_to_int(data[0:8] ,byte_order))
        elif type == Enum_Data_type.ulint.value:
            return str(tools.bytes_to_uint(data[0:8],byte_order))
        elif type == Enum_Data_type.real.value:
            if reserved is not None and isinstance(reserved, int):
                return f"{tools.bytes_to_float(data[0:4], byte_order):.{reserved}f}"
            #return tools.bytes_to_float(data[0:4], byte_order)
            return str(tools.bytes_to_float(data[0:4], byte_order))#add by lhl 20251110 将值转换成字符串
        elif type == Enum_Data_type.lreal.value:
            if reserved is not None and isinstance(reserved, int):
                return f"{tools.bytes_to_float(data[0:8], byte_order):.{reserved}f}"
            return str(tools.bytes_to_float(data[0:8], byte_order))#add by lhl 20251110 将值转换成字符串
            #return tools.bytes_to_float(data[0:8], byte_order)
        elif type == Enum_Data_type.s5time.value:
            return str(tools.bytes_to_int(data[0:2], byte_order))
        elif type == Enum_Data_type.time.value:
            return str(tools.bytes_to_int(data[0:4], byte_order))
        elif type == Enum_Data_type.ltime.value:
            return str(tools.bytes_to_int(data[0:8], byte_order))
        elif type == Enum_Data_type.date.value:
            return str(tools.bytes_to_int(data[0:2], byte_order))
        elif type == Enum_Data_type.time_of_day.value:
            hour = tools.bytes_to_uint(data[0:1], byte_order)
            minute = tools.bytes_to_uint(data[1:2], byte_order)
            second = tools.bytes_to_uint(data[2:3], byte_order)
            mic = tools.bytes_to_uint(data[3:4], byte_order)
            strInfo = f'{hour}:{minute}:{second}.{mic}'
            return strInfo
            #return str(tools.bytes_to_int(data[0:4], byte_order))
        elif type == Enum_Data_type.ltod.value:
            return str(tools.bytes_to_int(data[0:8], byte_order))
        elif type == Enum_Data_type.date_and_time.value:
            year = 1990+tools.bytes_to_uint(data[0:1], byte_order)
            month = tools.bytes_to_uint(data[1:2], byte_order)+1
            day = tools.bytes_to_uint(data[2:3], byte_order)+1
            hour = tools.bytes_to_uint(data[3:4], byte_order)
            minute = tools.bytes_to_uint(data[4:5], byte_order)
            second = tools.bytes_to_uint(data[5:6], byte_order)
            strInfo = f'{year}-{month}-{day} {hour}:{minute}:{second}'
            return strInfo
            #return str(tools.bytes_to_int(data[0:8], byte_order))
        elif type == Enum_Data_type.ldt.value:
            return str(tools.bytes_to_int(data[0:8], byte_order))
        elif type == Enum_Data_type.dtl.value:
            year = tools.bytes_to_uint(data[0:2], byte_order)
            month = tools.bytes_to_uint(data[2:3], byte_order)
            day = tools.bytes_to_uint(data[3:4], byte_order)
            week = tools.bytes_to_uint(data[4:5], byte_order)
            hour = tools.bytes_to_uint(data[5:6], byte_order)
            minute = tools.bytes_to_uint(data[6:7], byte_order)
            second = tools.bytes_to_uint(data[7:8], byte_order) 
            mic= tools.bytes_to_uint(data[8:], byte_order)
            strInfo = f'{year}-{month}-{day} {hour}:{minute}:{second}.{mic}'
            return strInfo
        elif type == Enum_Data_type.char.value:
            return tools.bytes_to_string(data[0:1],byte_order)
        elif type == Enum_Data_type.wchar.value:
            return tools.bytes_to_string(data[0:2],byte_order)
        elif type == Enum_Data_type.string.value:
            totalLen = tools.bytes_to_uint(data[0:1], 'big')
            if totalLen == 0:
                return ''
            dataLen = tools.bytes_to_uint(data[1:2],  'big')
            if dataLen == 0:
                return ''
            return tools.bytes_to_string(data[2:2+dataLen],byte_order)
        elif type == Enum_Data_type.wstring.value:
            totalLen = tools.bytes_to_uint(data[0:2], 'big')
            if totalLen == 0:
                return ''
            dataLen = tools.bytes_to_uint(data[2:4],  'big')*2
            if dataLen == 0:
                return ''
            return tools.bytes_to_string(data[4:4+dataLen],byte_order)
        elif type == Enum_Data_type.arrayType.value:
            return ""
        elif type == Enum_Data_type.structType.value:
            return ""
        elif type == Enum_Data_type.owntype.value:
            return ''
        else:
            return ""
    except Exception as e:
        output(f'数据转换成字符串失败，错误信息：{e}',outputMode.saveLog, enum_Error.localErr)
        return ""

def str2snap7data(data,type,bit,byte_order,dataLen=0):
    ''' 参数说明
        data 是字符串
        type 数据类型
        bit 偏移量，bool使用
        byte_order 字节序,如果是字符串则是编码方式(ascii,utf-16be)
                          如果是数据，使用编码字节序(big,little)
    '''
    try:
        if data is None or len(data) == 0:
            return None
        if type == Enum_Data_type.bool.value:
            return 0 if data =="False" or tools.dataConvertManager.data2int(data) !=1 else 1
        elif type == Enum_Data_type.byte.value:
            return tools.data_to_bytes(np.int8(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.word.value:
            return tools.data_to_bytes(np.int16(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.dword.value:
            return tools.data_to_bytes(np.int32(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.lword.value:
            return tools.data_to_bytes(np.int64(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.sint.value:
            return tools.data_to_bytes(np.int8(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.usint.value:
            return tools.data_to_bytes(np.uint8(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.int.value:
            return tools.data_to_bytes(np.int16(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.uint.value:
            return tools.data_to_bytes(np.uint16(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.dint.value:
            return tools.data_to_bytes(np.int32(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.udint.value:
            return tools.data_to_bytes(np.uint32(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.lint.value:
            return tools.data_to_bytes(np.int64(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.ulint.value:
            return tools.data_to_bytes(np.uint64(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.real.value:
            float64_num =tools.dataConvertManager.data2float(data)
            float32_num = np.float32(float64_num)
            return tools.float_to_bytes(float32_num, byte_order)
        elif type == Enum_Data_type.lreal.value:
            float64_num =tools.dataConvertManager.data2float(data)
            return tools.float_to_bytes(float64_num, byte_order)
        elif type == Enum_Data_type.s5time.value:
            return tools.data_to_bytes(np.int16(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.time.value:
            return tools.data_to_bytes(np.int32(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.ltime.value:
            return tools.data_to_bytes(np.int64(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.date.value:
            return tools.data_to_bytes(np.int16(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.time_of_day.value:
            #strInfo = f'{hour}:{minute}:{second}.{mic}'
            strArray = data.split(":")
            bRes = bytearray(4)
            index =0
            for strInfo in strArray:
                if index ==2:
                    strMic = strInfo.split(".")
                    for mic in strMic:
                        if index >3:
                            break
                        bRes[index] = tools.data2int(mic)
                        index = index +1
                    break
                bRes[index] = tools.data2int(strInfo)
                index = index +1
            return bRes
            #return str(tools.bytes_to_int(data[0:4], byte_order))
        elif type == Enum_Data_type.ltod.value:
            return tools.data_to_bytes(np.int64(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.date_and_time.value:
            year    = 1990+tools.bytes_to_uint(data[0:1], byte_order)
            month   = tools.bytes_to_uint(data[1:2], byte_order)+1
            day     = tools.bytes_to_uint(data[2:3], byte_order)+1
            hour    = tools.bytes_to_uint(data[3:4], byte_order)
            minute  = tools.bytes_to_uint(data[4:5], byte_order)
            second  = tools.bytes_to_uint(data[5:6], byte_order)
            strInfo = f'{year}-{month}-{day} {hour}:{minute}:{second}'
            return strInfo
            #return str(tools.bytes_to_int(data[0:8], byte_order))
        elif type == Enum_Data_type.ldt.value:
            return tools.data_to_bytes(np.int64(tools.dataConvertManager.data2int(data)),byte_order = byte_order)
        elif type == Enum_Data_type.dtl.value:
            year    = tools.bytes_to_uint(data[0:2], byte_order)
            month   = tools.bytes_to_uint(data[2:3], byte_order)
            day     = tools.bytes_to_uint(data[3:4], byte_order)
            week    = tools.bytes_to_uint(data[4:5], byte_order)
            hour    = tools.bytes_to_uint(data[5:6], byte_order)
            minute  = tools.bytes_to_uint(data[6:7], byte_order)
            second  = tools.bytes_to_uint(data[7:8], byte_order) 
            mic     = tools.bytes_to_uint(data[8:], byte_order)
            strInfo = f'{year}-{month}-{day} {hour}:{minute}:{second}.{mic}'
            return strInfo
        elif type == Enum_Data_type.char.value:
            return tools.bytes_to_string(data[0:1],byte_order)
        elif type == Enum_Data_type.wchar.value:
            return tools.bytes_to_string(data[0:2],byte_order)
        elif type == Enum_Data_type.string.value:
            byteStr = tools.data_to_bytes(data,byte_order = byte_order)
            dataSize=len(byteStr)
            return struct.pack(f'>BB{dataSize}s',dataLen,dataSize,byteStr)
        elif type == Enum_Data_type.wstring.value:
            byteStr = tools.data_to_bytes(data,byte_order = byte_order)
            dataSize=len(byteStr)
            return struct.pack(f'>HH{dataSize}s',dataLen,dataSize,byteStr)
        elif type == Enum_Data_type.arrayType.value:
            return bytes()
        elif type == Enum_Data_type.structType.value:
            return bytes()
        elif type == Enum_Data_type.owntype.value:
            return bytes()
        else:
            return bytes()
    except Exception as e:
        output(f'数据转换成字符串失败，错误信息：{e}',outputMode.saveLog, enum_Error.localErr)
        return bytes()
def dataTypeLen(type,len):
    if type == Enum_Data_type.bool.value:
        return 1
    elif type == Enum_Data_type.byte.value:
        return 1
    elif type == Enum_Data_type.word.value:
        return 2
    elif type == Enum_Data_type.dword.value:
        return 4
    elif type == Enum_Data_type.lword.value:
        return 8
    elif type == Enum_Data_type.sint.value:
        return 1
    elif type == Enum_Data_type.usint.value:
        return 1
    elif type == Enum_Data_type.int.value:
        return 2
    elif type == Enum_Data_type.uint.value:
        return 2
    elif type == Enum_Data_type.dint.value:
        return 4
    elif type == Enum_Data_type.udint.value:
        return 4
    elif type == Enum_Data_type.lint.value:
        return 8
    elif type == Enum_Data_type.ulint.value:
        return 8
    elif type == Enum_Data_type.real.value:
        return 4
    elif type == Enum_Data_type.lreal.value:
        return 8
    elif type == Enum_Data_type.s5time.value:
        return 2
    elif type == Enum_Data_type.time.value:
        return 4
    elif type == Enum_Data_type.ltime.value:
        return 8
    elif type == Enum_Data_type.date.value:
        return 2
    elif type == Enum_Data_type.time_of_day.value:
        return 4
    elif type == Enum_Data_type.ltod.value:
        return 8
    elif type == Enum_Data_type.date_and_time.value:
        return 8
    elif type == Enum_Data_type.ldt.value:
        return 8
    elif type == Enum_Data_type.dtl.value:
        return 12
    elif type == Enum_Data_type.char.value:
        return 1
    elif type == Enum_Data_type.wchar.value:
        return 2
    elif type == Enum_Data_type.string.value:
        return len
    elif type == Enum_Data_type.wstring.value:
        return len
    elif type == Enum_Data_type.arrayType.value:
        return 0
    elif type == Enum_Data_type.structType.value:
        return 0
    elif type == Enum_Data_type.owntype.value:
        return 0
    elif type == Enum_Data_type.TON_TIME.value:
        return 16
    elif type == Enum_Data_type.HW_IO.value:
        return 2
    elif type == Enum_Data_type.IEC_TIMER.value:
        return 16
    elif type == Enum_Data_type.int_BCD.value:
        return 2
    elif type == Enum_Data_type.dint_BCD.value:
        return 4
    else:
        return 0

@dataclass
class valueInfo:
    def __init__(self,obj = None,serveruuid='',nodeuuid='',name='',value='',dataTime=0,flag=''):
        self.nodeuuid   = nodeuuid
        self.serveruuid = serveruuid
        self.name       =name
        self.value      =value
        self.dataTime   = dataTime
        self.flag       = flag
        if obj is not None:
            self.paras_dict(obj)

    def to_dict(self):
        resDic = {}
        resDic['nodeuuid']      = self.nodeuuid
        resDic['serveruuid']    = self.serveruuid
        resDic['name']          = self.name
        resDic['value']         = self.value
        resDic['dataTime']      = self.dataTime
        resDic['flag']          = self.flag
        return resDic
    def paras_dict(self,dict):
        if dict is None:
            return
        try:
            self.nodeuuid   = dict['nodeuuid']
            self.serveruuid = dict['serveruuid']
            self.name       = dict['name']
            self.value      = dict['value']
            self.dataTime   = dict['dataTime']
            self.flag       = dict['flag']
        except Exception as e:
            output(f'[valueInfo.paras_dict]:转换错误:{e}',outputMode.saveLog, enum_Error.localErr)
    def to_sql(self,tableName,dbType,bUpdate,listUUid=None):
        strSql = ''
        if bUpdate is False:
            strUUID = tools.getUUIDString()
            if listUUid and isinstance(listUUid, str): #add by lhl 20251201 增加历史分组表
                strSql = f"""insert into {tableName} (uuid,node_uuid,vch_value,n_collect_time,list_uuid) 
                values ('{strUUID}','{self.nodeuuid}','{self.value}',{self.dataTime},'{listUUid}')
                """
            else:
                strSql = f"""insert into {tableName} (uuid,node_uuid,vch_value,n_collect_time) 
                values ('{strUUID}','{self.nodeuuid}','{self.value}',{self.dataTime})
                """
            return strSql

        if dbType == database_type.sqlite.value:
            if bUpdate:
                if listUUid and isinstance(listUUid, str):
                    strSql = f"""
                    insert or replace into {tableName} (node_uuid,vch_value,n_collect_time,list_uuid)
                    values ('{self.nodeuuid}','{self.value}','{self.dataTime}','{listUUid}')
                   """
                else:
                    strSql = f"""
                    insert or replace into {tableName} (node_uuid,vch_value,n_collect_time)
                    values ('{self.nodeuuid}','{self.value}','{self.dataTime}')
                   """
        elif dbType == database_type.mysql.value:
            if bUpdate:
                if listUUid and isinstance(listUUid, str):
                    strSql = f"""
                    insert or replace into {tableName} (node_uuid,vch_value,n_collect_time,list_uuid)
                    values ('{uuid}','{self.nodeuuid}','{self.value}','{self.dataTime}','{listUUid}')
               
                """
                else:
                    strSql = f"""
                    insert or replace into {tableName} (node_uuid,vch_value,n_collect_time)
                    values ('{uuid}','{self.nodeuuid}','{self.value}','{self.dataTime}')
               
                """
        return strSql

class valueInfoMgr:
    def __init__(self):
        self.valueList      = []    
        self.nCollectTime   = 0
        self.strDeviceId    = ''
    def addValue(self,valueInfo):
        self.valueList.append(valueInfo)
    def to_dict(self,type):
        dictRes = {}
        dictRes['type'] = type
        dictRes['data'] = [valueInfo.to_dict() for valueInfo in self.valueList]
        return dictRes
    def paras_dict(self,dict):
        nType               = dict['type']


    def to_DB(self,mainMgr):
        if not mainMgr.databaseMgr:
            return
        strHistory      = mainMgr.getTable("t_val_history")         #历史数据表
        strHistoryList  = mainMgr.getTable("t_val_history_list")    #历史分组表 add by lhl 20251201
        strLast         = mainMgr.getTable("t_val_last")            #最新数据表

        strHistoryUUID  = tools.getUUIDString()                     #历史数据的UUID用于插入t_val_history_list使用,t_val_history中用于分组
        if mainMgr.dbSaveHistoryInfo == 1:                          #保存历史数据,写入t_val_history_list表
            mainMgr.databaseMgr.writeSql(f"insert into {strHistoryList} (uuid,device_uuid,n_collectTime) values('{strHistoryUUID}','{self.strDeviceId}',{self.nCollectTime})")
        for val in self.valueList:
            if mainMgr.dbSaveHistoryInfo == 1:                      #保存历史数据到t_val_history表
                mainMgr.databaseMgr.writeSql(val.to_sql(strHistory,mainMgr.configInfo.databaseInfo.dbtype,False,strHistoryUUID))
            if mainMgr.dbsaveLast == 1:                             #保存最后数据数据到t_val_last表
                mainMgr.databaseMgr.writeSql(val.to_sql(strLast,mainMgr.configInfo.databaseInfo.dbtype,True,strHistoryUUID))

class dataInfo:
    def __init__(self,obj,serveruuid="",uuid="",name="",dbnum=0,type=0,datalen=0,offset=0,reserved=0,
                      bit=0,format="",parentuuid="",isenable=0,order=0,flag="",slave=1,transName=0,isEnableSet=0,minVal='',maxVal=''):
        self.serveruuid     = serveruuid
        self.uuid           = uuid
        self.name           = name
        self.dbnum          = dbnum
        self.type           = type
        self.datalen        = datalen   if datalen != None else 0
        self.offset         = offset    if offset != None else 0
        self.reserved       = reserved
        self.bit            = bit
        self.format         = format
        self.parentuuid     = parentuuid
        self.isenable       = isenable
        self.order          = order if order != None else 0
        self.flag           = flag  if flag != None else ''
        self.slaveId        = slave
        #为了下控增加的参数
        self.transName      = transName

        self.isEnableSet    = isEnableSet
        self.minVal         = minVal
        self.maxVal         = maxVal

        #增加传输名称的代码
        if tools.is_empty(self.flag) is False and self.flag[-1] != ';':
            self.flag = f'{self.flag};'

        if self.transName ==1:
            if self.flag.find(self.name+';') <0:
                self.flag =self.flag + self.name +";"
        ######
        #用于采集的,扩展信息
        self.collectVal     = ''
        self.preCollectVal  = ''
        self.collectTime    = 0
        self.paras_dict(obj)

    def copyInfo(self):
        res = dataInfo(None)
        res.serveruuid    = self.serveruuid
        res.uuid          = self.uuid
        res.name          = self.name
        res.dbnum         = self.dbnum
        res.type          = self.type
        res.datalen       = self.datalen
        res.offset        = self.offset
        res.reserved      = self.reserved
        res.bit           = self.bit
        res.format        = self.format
        res.parentuuid    = self.parentuuid
        res.isenable      = self.isenable
        res.order         = self.order
        res.flag          = self.flag
        res.slaveId       = self.slaveId #add by lhl 20251128 增加发送子站ID,在服务器中也要增加对应的字段
        ##为了下控增加
        res.transName     = self.transName
        res.isEnableSet   = self.isEnableSet
        res.minVal        = self.minVal
        res.maxVal        = self.maxVal
        ##
        return res
    def to_dict(self):
        resDic = {}
        resDic['serveruuid']    = self.serveruuid
        resDic['uuid']          = self.uuid
        resDic['name']          = self.name
        resDic['dbnum']         = self.dbnum
        resDic['type']          = self.type
        resDic['datalen']       = self.datalen
        resDic['offset']        = self.offset
        resDic['reserved']      = self.reserved
        resDic['bit']           = self.bit
        resDic['format']        = self.format
        resDic['parentuuid']    = self.parentuuid
        resDic['isenable']      = self.isenable
        resDic['order']         = self.order
        resDic['flag']          = self.flag
        resDic['slaveId']       = self.slaveId #add by lhl 20251128 增加发送子站ID,在服务器中也要增加对应的字段

        ##下控上传下数据给
        resDic['transName']     = self.transName
        resDic['isEnableSet']   = self.isEnableSet
        resDic['minVal']        = self.minVal
        resDic['maxVal']        = self.maxVal

        return resDic
    def paras_dict(self,dict)->bool:
        if dict is None:
            return False
        try:
            self.serveruuid = dict['serveruuid']
            self.uuid       = dict['uuid']
            self.name       = dict['name']
            self.dbnum      = dict['dbnum']
            self.type       = dict['type']
            self.datalen    = dict['datalen']
            self.offset     = dict['offset']
            self.reserved   = dict['reserved']
            self.bit        = dict['bit']
            self.format     = dict['format']
            self.parentuuid = dict['parentuuid']
            self.isenable   = dict['isenable']
            self.order      = tools.dataConvertManager.data2int(dict['order'],None)
            self.flag       = dict['flag']
            self.slaveId    = tools.safe_DictValue(dict,'slaveId',self.slaveId)
            #为了下控
            self.transName  = tools.safe_DictValue(dict,'transName',self.transName)
            self.isEnableSet= tools.safe_DictValue(dict,'isEnableSet',self.isEnableSet)
            self.minVal     = tools.safe_DictValue(dict,'minVal',self.minVal)
            self.maxVal     = tools.safe_DictValue(dict,'maxVal',self.maxVal)
        except Exception as e:
            output(f'[dataInfo.paras_dict]:转换错误:[{e}]',outputMode.saveLog, enum_Error.localErr)
            return False
        return True
    def to_sql(self,dbType =0):
        strRes = ""
        if dbType == 0: #sqlite
            pass
        elif dbType == 1: #mysql  增加IGNORE 可以忽略冲突
            strRes = f"""insert IGNORE into t_collect_node_info_{self.serveruuid} (uuid,serveruuid,`name`,dbnum,`type`,reserved,datalen,`offset`,`bit`,`format`,
                            isenable,parentuuid,`order`,`flag`,`n_slave_id`,n_transName,n_isenable_set,vch_minVal,vch_maxVal) values(
                                {tools.checksqlValue(self.uuid)},{tools.checksqlValue(self.serveruuid)},
                                {tools.checksqlValue(self.name)},{tools.checksqlValue(self.dbnum)},
                                {tools.checksqlValue(self.type)},{tools.checksqlValue(self.reserved)},
                                {tools.checksqlValue(self.datalen)},{tools.checksqlValue(self.offset)},
                                {tools.checksqlValue(self.bit)},{tools.checksqlValue(self.format)},
                                {tools.checksqlValue(self.isenable)},{tools.checksqlValue(self.parentuuid)},
                                {tools.checksqlValue(self.order)},{tools.checksqlValue(self.flag)},
                                {tools.checksqlValue(self.slaveId)},{tools.checksqlValue(self.transName)},
                                {tools.checksqlValue(self.isEnableSet)},{tools.checksqlValue(self.minVal)},
                                {tools.checksqlValue(self.maxVal)}
                            )
            """
        elif dbType == 2: #sqlserver
            #strRes = f"""insert into t_collect_node_info_{self.serveruuid} (uuid,serveruuid,"name",dbnum,"type",reserved,datalen,"offset","bit","format",
            #isenable,parentuuid,"order","flag","n_slave_id") values(
            #{tools.checksqlValue(self.uuid)},{tools.checksqlValue(self.serveruuid)},
            #{tools.checksqlValue(self.name)},{tools.checksqlValue(self.dbnum)},
            #{tools.checksqlValue(self.type)},{tools.checksqlValue(self.reserved)},
            #{tools.checksqlValue(self.datalen)},{tools.checksqlValue(self.offset)},
            #{tools.checksqlValue(self.bit)},{tools.checksqlValue(self.format)},
            #{tools.checksqlValue(self.isenable)},{tools.checksqlValue(self.parentuuid)},
            #{tools.checksqlValue(self.order)},{tools.checksqlValue(self.flag)},
            #{tools.checksqlValue(self.slaveId)}
            #)
            #"""
            #增加如果主键冲突的处理
            strRes = f"""insert into t_collect_node_info_{self.serveruuid} (uuid,serveruuid,"name",dbnum,"type",reserved,datalen,"offset","bit","format",
                isenable,parentuuid,"order","flag","n_slave_id",n_transName,n_isenable_set,vch_minVal,vch_maxVal)
               select
                {tools.checksqlValue(self.uuid)},{tools.checksqlValue(self.serveruuid)},
                {tools.checksqlValue(self.name)},{tools.checksqlValue(self.dbnum)},
                {tools.checksqlValue(self.type)},{tools.checksqlValue(self.reserved)},
                {tools.checksqlValue(self.datalen)},{tools.checksqlValue(self.offset)},
                {tools.checksqlValue(self.bit)},{tools.checksqlValue(self.format)},
                {tools.checksqlValue(self.isenable)},{tools.checksqlValue(self.parentuuid)},
                {tools.checksqlValue(self.order)},{tools.checksqlValue(self.flag)},
                {tools.checksqlValue(self.slaveId)},{tools.checksqlValue(self.transName)},
                {tools.checksqlValue(self.isEnableSet)},{tools.checksqlValue(self.minVal)},
                {tools.checksqlValue(self.maxVal)} 
                where NOT EXISTS (
                SELECT 1 FROM t_collect_node_info_{self.serveruuid}
                WHERE uuid = {tools.checksqlValue(self.uuid)}
            );
            """
        return strRes
#记录同一dbnum下的采集点
class dbinfo:
    def __init__(self,dbnum,deviceId,slaveId=0):
        self.dbnum              = dbnum     #西门子是db号,modbus是1-4寄存器类型
        self.deviceId           = deviceId  #采集设备id
        self.slaveId            = slaveId   #西门子不会用到,modbus从站id 
        self.maxbuffer          = 0         #db块中最大的偏移量
        self.collectNodeList    = []        #db里的成员列表
        
    #增加节点信息,然后计算最大buffer
    def addNodeInfo(self,node):
        self.collectNodeList.append(node)
        self.countMax(node.offset,node.datalen)
    #用于根据uuid查找数据
    #def nodeInfo(self,nodeUUID):
    #    nodeInfo = None
    #    nodeInfo = self.collectNodeDict.get(nodeUUID)
    #    return nodeInfo
    def countMax(self,offset, len):
        self.maxbuffer = max(self.maxbuffer, offset + len)

@unique#枚举类修饰符，唯一检查
#采集协议
class Enum_server_type(Enum):
    opc     =   0  #OPC 扩展
    snap7   =   1  #西门子snap7(第一阶段只完成此采集)
    iec104  =   2  #IEC104 扩展
    modbus  =   3  #modbus 扩展
    kafka   =   4  #kafka 扩展
    mqtt    =   5  #mqtt 扩展

#日志信息管理
class logInfo(jsonBase):
    def __init__(self,obj=None,bDelNode=False):
        self.level      = 255 #默认全部输出
        self.path       = '/var/logs/'
        self.filename   = 'log'
        self.savetime   = 7 #保存天数
        self.describe   = ''
        if obj is None:
           return
        super().__init__(obj)
        self.level = self.JsonNode.intNode("level",255)
        self.path = self.JsonNode.stringNode("path","/var/logs/")
        #修正目录,主要是第一个不是"/"增加"/"
        if self.path[0] != '/':
            self.path = '/' + self.path

        self.filename = self.JsonNode.stringNode("filename","log")
        self.savetime = self.JsonNode.intNode("savetime",7)
        self.describe = self.JsonNode.stringNode("describe","")

        self.delJsonNode(bDelNode)
class databaseInfo(jsonBase):
    def __init__(self,obj=None,bDelNode=False):
        self.host           = "127.0.0.1" #默认全部输出
        self.port           = 3306
        self.user           = "root"
        self.password       = "123456"
        self.dbname         = "collect_data"
        self.dbtype         = 0
        self.checkInterval  = 10000 #检查周期,定时检查数据库
        self.maintainTable  = "t_maintain_table"
        self.describe       = ''
        self.dbInterface    = None
        if obj is None:
           return
        super().__init__(obj)
        self.host           = self.JsonNode.stringNode("host","127.0.0.1")
        self.port           = self.JsonNode.intNode("port",3306)
        self.user           = self.JsonNode.stringNode("user","root")
        self.password       = self.JsonNode.stringNode("password","123456")
        self.dbname         = self.JsonNode.stringNode("dbname","collect_data")
        self.dbtype         = self.JsonNode.intNode("dbtype",0)
        self.checkInterval  = self.JsonNode.intNode("checkInterval",10000)
        self.maintainTable  = self.JsonNode.stringNode("maintainTable","t_maintain_table")
        self.describe       = self.JsonNode.stringNode("describe","")

        #数据库接口
        if self.dbtype == database_type.sqlite.value:
            self.dbInterface = sqliteMgr(self.describe,0,self.host,self.port,self.user,self.password,self.dbname,None)
        elif self.dbtype == database_type.mysql.value:
            self.dbInterface = mysqlMgr(self.describe,0,self.host,self.port,self.user,self.password,self.dbname,None)
        elif self.dbtype == database_type.sqlserver.value:
            self.dbInterface = sqlserverMgr(self.describe,0,self.host,self.port,self.user,self.password,self.dbname,None)
        else:#没有对应配置,使用默认接口
            self.dbInterface = databaseBase(self.describe,0,"databaseBase",self.host,self.port,self.user,self.password,self.dbname,database_type.defaule,None)
        self.delJsonNode(bDelNode)
    def setDbName(self,dbName):
        self.dbname = dbName
        self.dbInterface.db_name= dbName
class collectPowerStationCfg(jsonBase):
    def __init__(self,obj=None,bDelNode=False):
        self.time_tick  = 1000 #默认全部输出
        self.des_host   = "http://218.60.117.218:8086/system/user/selectEnergyStationData"
        self.user       = "hhrdtest"
        self.pwd        = "hhrdtest@123"
        if obj is None:
           return
        super().__init__(obj)
        self.time_tick  = self.JsonNode.intNode("time_tick",self.time_tick)
        self.des_host   = self.JsonNode.stringNode("des_host",self.des_host).strip()
        self.user       = self.JsonNode.stringNode("user",self.user).strip()
        self.pwd        = self.JsonNode.stringNode("pwd",self.pwd).strip()
        self.delJsonNode(bDelNode)
#配置信息管理
class configMgr:
    def __init__(self,strInfo:str):
        #默认值
        self.databaseInfo   = databaseInfo()
        self.logInfo        = logInfo()
        self.redisInfo      = redisInfo()
        self.modbusTemp     = modbusTemperature()
        self.collectCfg     = collectPowerStationCfg()
        self.dlrd = False

        self.jsonMgr = None
        if tools.is_empty(strInfo):
            return
        self.dictJson = load_json(strInfo)
        if self.dictJson is None:
           return
        self.jsonMgr        = loadJsonNode(self.dictJson)
        self.databaseInfo   = databaseInfo(self.jsonMgr.dictNode("database"))
        self.logInfo        = logInfo(self.jsonMgr.dictNode("log"))
        self.redisInfo      = redisInfo(self.jsonMgr.dictNode("redis_info"))
        self.modbusTemp     = modbusTemperature(self.jsonMgr.dictNode("modbusTemp"))
        self.collectCfg     = collectPowerStationCfg(self.jsonMgr.dictNode("collectAddress"))
        self.dlrd           = self.jsonMgr.boolNode("dlrd",self.dlrd)
    def getDbInterface(self,defInterface=databaseBase):
        dbInterface = defInterface
        if self.databaseInfo:
            dbInterface = self.databaseInfo.dbInterface.getClass()
        return dbInterface

class writeNode(jsonBase):
    def __init__(self,obj= None):
        self.host       = ""
        self.port       = 102
        self.db         = 0
        self.offset     = 0
        self.plcConnect = None
        if obj is None:
            return
        super().__init__(obj)
        
        self.host       = self.JsonNode.stringNode("host",self.host)
        self.port       = self.JsonNode.intNode("port",self.port)
        self.db         = self.JsonNode.intNode("db",self.db)
        self.offset     = self.JsonNode.intNode("offset",self.offset)

class collectNode(jsonBase):
    def __init__(self,obj = None):
        self.offset     = 0,
        self.dataLen    = 0,
        self.unit       = 1
        self.writeNode  = []
        if obj is None:
            return
        super().__init__(obj)
        self.offset     = self.JsonNode.intNode("offset",self.offset)
        self.dataLen    = self.JsonNode.intNode("dataLen",self.dataLen)
        self.unit       = self.JsonNode.intNode("unit",self.unit)
        writeList       = self.JsonNode.listNode("writeNode")
        for write in writeList:
            self.writeNode.append(writeNode(write))
#温度采集
class collectTempInfo(jsonBase):
    def __init__(self,obj=None):
        self.deviceId       = tools.getUUIDString() #设备id,如果不设置使用动态uuid
        self.host           = ''                    #地址
        self.port           = 502                   #端口
        self.collectTick    = 1                     #采集间隔
        self.collectNode    = []                    #采集单元点列表
        self.modbusTcp      = None                  #modbus连接Tcp
        if obj is None:
            return
        super().__init__(obj)
        self.deviceId       = self.JsonNode.stringNode( "deviceId"      ,self.deviceId)
        self.host           = self.JsonNode.stringNode( "host"          ,self.host)
        self.port           = self.JsonNode.intNode(    "port"          ,self.port)
        self.collectTick    = self.JsonNode.intNode(    "collectTick"   ,self.collectTick)
        collectList         = self.JsonNode.listNode(   "collectNode"   ,[])
        for collect in collectList:
            self.collectNode.append(collectNode(collect))
class modbusTemperature(jsonBase):
    def __init__(self,obj=None):
        if obj is None:obj = {}
        super().__init__(obj)
        self.collectTick = self.JsonNode.intNode("collectTick",60)
        self.bCopyTable  = self.JsonNode.intNode("copyTable",0)               #从配置文件中得到
        self.collectInfo = []
        collectList = self.JsonNode.listNode("collectInfo",[])
        for collect in collectList: self.collectInfo.append(collectTempInfo(collect))

class mainMangerBase():
    def __init__(self,configInfo):
        from ..database.dbManger import maintainMgr
        self.configInfo   = configInfo                    #保存配置信息
        self.maintainMgr  = maintainMgr(configInfo,self)  #定义管理类实例
        self.watchMgr     = watchManager()                #定义监视类实例
        pass
    def run(obj):
        #其它管理类重载run后,如果不需要启动,可以给变量设置为None
        if obj and hasattr(obj,"maintainMgr")   and obj.maintainMgr:  obj.maintainMgr.run() #运行管理类,用于维护基本数据,包含删除超期数据
        if obj and hasattr(obj,"watchMgr")      and obj.watchMgr:     obj.watchMgr._run()   #运行监视线程,可以增加监视点,如果超时会调用reset,用于超时后续处理
    def stop(obj):
        if obj and hasattr(obj,"maintainMgr")   and obj.maintainMgr:  obj.maintainMgr.stop()#停止管理类
        if obj and hasattr(obj,"watchMgr")      and obj.watchMgr:     obj.watchMgr._stop()  #停止监视类
    def addSql(strsql):
        pass
    #需要重载此函数
    def init(self)->Tuple[bool,str]:
        self.maintainMgr = None #没有重载不启动管理类
        self.watchMgr    = None #没有重载不启动监视管理线程
        output("mainMangerBase.init 需要重载",outputMode.saveLog,enum_Error.localInfo)
        return True,'mainMangerBase.init 需要重载'

######控制json定义
@unique#枚举类修饰符，唯一检查
class enum_Ctrl_code(Enum):
    NONE_CTRL       = 0 #没有控制
    SET_CTRL        = 1 #下控设置值
    REBOOT_CTRL     = 2 #重启采集终端
    RELOGIN_CTRL    = 3 #采集终端重新登
    REREGITER_CTRL  = 4 #采集终端重新注册 
class result_info:
    def __init__(self,obj= None):
        self.nResult    = 1
        self.strMsg     = ""
        self.paras_dict(obj)
    def to_dict(self):
        resDict = {}
        resDict['result'] = self.nResult
        resDict['message']= self.strMsg
        return resDict
    def paras_dict(self,dict):
        if dict is None:return
        self.nResult    = tools.safe_DictValue(dict,"result",1)
        self.strMsg     = tools.safe_DictValue(dict,"message",'')
#下控节点信息类
class control_Node:
    def __init__(self,obj=None,deviceId="",nodeuuid="",nodeVal=""):
        self.deviceId   = deviceId  #设备ID
        self.nodeuuid   = nodeuuid  #节点ID
        self.nodeVal    = nodeVal   #节点设置值
        self.exeRes     = None      #执行结果
        self.nodePreVal = None      #设置节点前的值
        self.paras_dict(obj)        #从obj里得到设置值,主要用于对json的反解
    def to_dict(self):              #转换到dict
        resDict ={}
        resDict["deviceId"] = self.deviceId
        resDict["nodeuuid"] = self.nodeuuid
        resDict["nodeVal"]  = self.nodeVal
        if self.exeRes      is not None: resDict["exeRes"] = self.exeRes.to_dict()   #如果不是None,则不出现在json字段里
        if self.nodePreVal  is not None: resDict["preVal"] = self.nodePreVal         #如果不是None,则出现在json字段里
        return resDict
    def paras_dict(self,dict):
        if dict is None:return
        try:
            self.deviceId   = tools.safe_DictValue(dict,"deviceId","")
            self.nodeuuid   = tools.safe_DictValue(dict,'nodeuuid',"")
            self.nodeVal    = tools.safe_DictValue(dict,'nodeVal',"")
            #得到exeRes,如果不空则给成员赋值
            #self.exeRes = define.result_info(excRes) if (excRes := tools.safe_DictValue(dict,'exeRes',None,False)) is not None else None
            #第二种方法
            excRes          = tools.safe_DictValue(dict,'exeRes',None,False)
            if excRes is not None:  self.exeRes = define.result_info(excRes)
            self.nodePreVal = tools.safe_DictValue(dict,'preVal',None,False)
        except Exception as e:
            output(f'[valueInfo.paras_dict]:转换错误:{e}',outputMode.saveLog, enum_Error.localErr)
class control_Json(jsonBase):
    def __init__(self,strContent=None,bDelNode=False):
        self.ctrlHead   = control_Head()
        if tools.is_empty(strContent):  return      #没有json文本
        json_data       = load_json(strContent)     #json文本转换成json实例
        if json_data    is None:   return           #转换json实例错误
        self.ctrlHead   = control_Head(json_data)
        self.delJsonNode(bDelNode)
       
class control_Head():
    def __init__(self,obj=None,ctluuid="",ctlType =enum_Ctrl_code.NONE_CTRL.value,userId='',userName='',setTime=0,result = enum_State_code.fail.value):
        self.ctluuid    = ctluuid
        self.ctlType    = ctlType
        self.userId     = userId
        self.userName   = userName
        self.setTime    = setTime
        self.result     = result
        self.ctlNode    ={}
        self.parase_dict(obj)
    def copyHeadInfo(self):
        return control_Head(None,self.ctluuid,self.ctlType,self.userId,self.userName,self.setTime,self.result)
    def to_dict(self):
        resDict ={}
        try:
            resDict["ctluuid" ] = self.ctluuid
            resDict["ctlType" ] = self.ctlType
            resDict["userId"  ] = self.userId
            resDict["userName"] = self.userName
            resDict['setTime' ] = self.setTime
            resDict['result' ]  = self.result

            resDict["ctlNode" ] = [{k:[v.to_dict() for v in m]}for k,m in self.ctlNode.items()]
        except Exception as e:
            resDict={}
            output(f'[valueInfo.to_dict]:转换错误:{e}',outputMode.saveLog, enum_Error.localErr)
        return resDict
    def parase_dict(self,dict):
        try:
            if not dict: return
            self.ctluuid    = tools.safe_DictValue(dict,"ctluuid"  ,"")
            self.ctlType    = tools.safe_DictValue(dict,"ctlType"  ,enum_Ctrl_code.NONE_CTRL.value)
            self.userId     = tools.safe_DictValue(dict,"userId"   ,"")
            self.userName   = tools.safe_DictValue(dict,"userName" ,"")
            self.setTime    = tools.safe_DictValue(dict,"setTime"  ,0)
            self.result     = tools.safe_DictValue(dict,"result"  ,enum_State_code.fail.value)
            ctlNode         = tools.safe_DictValue(dict,"ctlNode"  ,[])
            self.ctlNode    = {k: [control_Node(v)  for v in m]for d in ctlNode for k, m in d.items() }
        except Exception as e:
            output(f'[valueInfo.paras_dict]:转换错误:{e}',outputMode.saveLog, enum_Error.localErr)
    def to_json_string(self):
        return loadJsonNode.toJsonString(self.to_dict())