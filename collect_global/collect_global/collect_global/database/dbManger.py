'''
    维护线程,用于定时查询维护列表,根据维护列表配置
    定时删除超时数据
    maintainTable配置在,ect/cofnig.json的数据库配置中设置
'''

import queue
#维护列表
#日志输出接口
from ..common.logManager import output, outputMode,enum_Error
from ..common.baseClass import deviceThread
from .mysql import mysqlMgr
from .sqlite import sqliteMgr
from .sqlserver import sqlserverMgr
from .databaseBase import database_type
from ..common.jsonFunc import jsonBase
from ..common.baseClass import paraBase
from ..common import commonTools as tools
class maintain_member(jsonBase):
    def __init__(self,obj= None,uuid='',vch_name='',vch_table_name='',vch_child_table='',vch_child_table_key='',vch_time_field='',n_saveTime=10):
        self.uuid                = uuid                 #UUID
        self.vch_name            = vch_name             #名称
        self.vch_table_name      = vch_table_name       #主表
        self.vch_child_table     = vch_child_table      #子表名称
        self.vch_child_table_key = vch_child_table_key  #子表关键字
        self.vch_time_field      = vch_time_field       #时间字段
        self.n_saveTime          = n_saveTime           #单位秒
        self.parseData(obj)

        self.childTable=[]
    def parseData(self,obj):
        if obj is None:
            return 
        super().__init__(obj)
        self.uuid                   = self.JsonNode.stringNode( "uuid"                  , "")
        self.vch_name               = self.JsonNode.stringNode( "vch_name"              , "")
        self.vch_table_name         = self.JsonNode.stringNode( "vch_table_name"        , "")
        self.vch_child_table        = self.JsonNode.stringNode( "vch_child_table"       , "")
        self.vch_child_table_key    = self.JsonNode.stringNode( "vch_child_table_key"   , "")
        self.vch_time_field         = self.JsonNode.stringNode( "vch_time_field"        , "")
        self.n_saveTime             = self.JsonNode.intNode(    "n_saveTime"            , 10)

class maintain_table(deviceThread):
    def __init__(self, name, dev):
        super().__init__(name, dev)
    
    def run(self,mainMgr):
        output(f"[{tools.cmn(self)}]:{self.name}-线程启动",outputMode.saveLog,enum_Error.localInfo)
        collectInterval = mainMgr.configInfo.databaseInfo.checkInterval/1000
        strMaintainTable = mainMgr.configInfo.databaseInfo.maintainTable
        connect = None
        sqlClass = None
        while self.runFlag:
            try:
                if mainMgr is None:
                    output(f"[{tools.cmn(self)}]:mainMgr参数错误",outputMode.saveLog,enum_Error.localErr)
                    break
                if tools.is_empty(strMaintainTable):
                    output(f"[{tools.cmn(self)}]:没有配置维护表名称,请在/etc/config.json中的数据库配置中配置",outputMode.saveLog,enum_Error.warning)
                    break
                self.threadWaitEvent.wait(collectInterval)
                self.threadWaitEvent.clear()
                if self.runFlag is False:   break
                sqlClass = mainMgr.configInfo.databaseInfo.dbInterface.getClass()#add by lhl 20251209
                if sqlClass is None:        continue
                connect = mainMgr.configInfo.databaseInfo.dbInterface.getConnectInterface()
                if connect is None:         continue
                strSql = f"select * from {strMaintainTable} where n_isenable = 1"
                dataList = []
                dataList = sqlClass.executeSql(connect,strSql)
                dataMgr = paraBase(dataList,maintain_member)
                for data in dataMgr.memberList:
                    if tools.is_empty(data.vch_child_table) or tools.is_empty(data.vch_child_table_key):
                        continue
                    if mainMgr.configInfo.databaseInfo.dbtype == database_type.sqlite.value:
                        strSql = f"select {data.vch_child_table_key} from {data.vch_child_table} where n_isenable = 1 and n_db_copy_table =1"
                    else:
                        strSql = f"select {data.vch_child_table_key} from {data.vch_child_table} where n_isenable = 1"#服务器端都是复制
                    dataList = sqlClass.executeSql(connect,strSql)
                    if dataList is None:
                        continue
                    for childData in dataList:
                        data.childTable.append(childData[f"{data.vch_child_table_key}"])
                for data in dataMgr.memberList:
                    strTime = ""
                    if mainMgr.configInfo.databaseInfo.dbtype == database_type.sqlite.value:
                        div =tools.timeManager.get_time_minus_ms(data.n_saveTime*1000)
                        strTime = f'{div}'
                    elif mainMgr.configInfo.databaseInfo.dbtype == database_type.mysql.value:
                        div = tools.timeManager.get_current_time_day_local_str_s(data.n_saveTime)
                        strTime = f"'{div}'"
                    elif mainMgr.configInfo.databaseInfo.dbtype == database_type.mysql.value:
                        div = tools.timeManager.get_current_time_day_local_str_s(data.n_saveTime)
                        strTime = f"'{div}'"

                    strSql = f"""delete from {data.vch_table_name} where {data.vch_time_field} < {strTime}"""
                    mainMgr.addSql(strSql)              #增加到执行列表
                    if not data.childTable: continue    #没有子表,不执行下面操作
                    for childData in data.childTable:   #删除子表超时数据
                        strSql = f"""delete from {data.vch_table_name}_{childData} where {data.vch_time_field} < {strTime}"""
                        mainMgr.addSql(strSql)          #增加到执行列表
                connect = sqlClass.closeConnect(connect)#关闭连接,检测线程数据库使用短连接
            except Exception as e:
                output(f'[异常]:[{tools.cmn(self)}]:{e}',outputMode.saveLog,enum_Error.localErr)
            connect = sqlClass.closeConnect(connect)    #防止跳转到异常时没有关闭连接
        #正常退出线程时,做一个关闭连接操作,一般不会跳转到此处
        if connect is not None and sqlClass is not  None:   connect = sqlClass.closeConnect(connect)
        output(f"[{tools.cmn(self)}][{self.name}线程退出]",outputMode.saveLog,enum_Error.localInfo)
class maintainMgr:
    def __init__(self,configInfo,mainMgr):
        self.configInfo = configInfo
        self.mainMgr = mainMgr
        self.maintainThread = maintain_table("维护线程",self)
        
    def run(self):
        self.maintainThread._run()
    def stop(self):
        self.maintainThread._stop()
    def addSql(self,sql):
        if self.mainMgr:
            self.mainMgr.addSql(sql)