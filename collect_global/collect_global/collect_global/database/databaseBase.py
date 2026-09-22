#枚举定义
from enum import unique, Enum, auto
import threading
#日志接口
from ..common.logManager import output, outputMode,enum_Error
#工具接口
from ..common import commonTools as tools
from ..common.baseClass import commonBase
@unique#枚举类修饰符，唯一检查
class database_type(Enum):
    defaule     = -1    #没有设置库
    sqlite      = 0     #sqlite
    mysql       = 1
    sqlserver   = 2

class databaseBase(commonBase):
    def __init__(self,serverName,index,name,db_host, db_port,db_user,db_password,db_name,type,databaseMgr):
        commonBase.__init__(self)
        #生成一个名称
        self._name = f"{tools.checkName(serverName,index,'databaseBase')}-{db_host}-{db_port}-{db_name}"
        self.db_host                = db_host           #数据库地址
        self.db_port                = db_port           #数据库端口
        self.db_user                = db_user           #数据库登录用户名
        self.db_password            = db_password       #数据库登录密码
        self.db_name                = db_name           #数据库名称,如果是sqlite
        self.db_type                = type              #数据库类型
        self.hWriteThread           = None              #写线程控制句柄
        self.is_run                 = False             #运行标志 - 未运行
        self.write_Event_timeout_ms = 1000              #单位毫秒
        self.writeEvent             = threading.Event() #写信号
        self.nGroupNum              = 100;              #100条提交一次
        self.databaseMgr            = databaseMgr       #数据库管理实例
    def singleQuery(db_host,db_port,db_user,db_password,db_db,sql,bCommit = True,bGetRes = True):
        return []
    def getConnect(db_host,db_port,db_user,db_password,db_db):
        return None
    def getTable_field(conn,tableName):
        return {}
    def getClass(self):
        return databaseBase
    def closeConnect(connection):
        return None
    def clearTable(connection,tableName):
        pass
    def copyTable(connection,tableName,new_tableName):
        pass
    def getConnectInterface(self):
        return None
    def executeSql(connection,sql,bCommit = True,bGetRes = True):
        return []
    def run(self):
        try:
            self.stop()
            self.is_run = True  # 运行标志 - 已运行
            self.writeEvent.clear()
            self.hWriteThread = threading.Thread(target=self.dualThread,daemon=True)  # 设置为守护线程，主程序退出时自动终止 定义线程
            self.hWriteThread.start()  # 启动线程
        except Exception as e:
            output(f'[databaseBase.run]:[{self._name}] 开始失败，错误:{e}',outputMode.saveLog,enum_Error.localInfo)  # 写日志
    def stop(self):
        if self.hWriteThread:
            self.is_run = False
            self.writeEvent.set()
            self.hWriteThread.join()
            self.writeEvent.clear()
        self.hWriteThread = None
    def flush(self):
        self.writeEvent.set()
    def check_connection(conn):
        raise NotImplementedError("[databaseBase.check_connection]:子类必须实现 check_connection 方法")
        return True
    def dualThread(self):
        raise NotImplementedError("[databaseBase.dualThread]:子类必须实现 check_connection 方法")
        pass
class databaseMgr:
    def __init__(self,name,db_host,db_port,db_user,db_password,db_name,threadNum):
        #参数信息
        self._name          = name
        self.db_host        = db_host
        self.db_port        = db_port
        self.db_user        = db_user
        self.db_password    = db_password
        self.db_name        = db_name
        #使用参数
        self.writeList      = []
        self.writeLock      = threading.Lock()
        self.threadNum      = threadNum
        self.databaseList   = []
    def copyWriteData(self,num=None):
        bList=[]
        with self.writeLock:
            size = len(self.writeList)
            if num is None or num >= size:
                bList=self.writeList[0:]
                self.writeList.clear()
            else:
                bList=self.writeList[0:num]
                self.writeList=self.writeList[num:]
        return bList
    def addSql(self,sql):
        self.writeSql(sql)
    def writeSql(self,sql):
        if not self.databaseList:   return#没有启动写线程,直接退出
        if tools.is_empty(sql):     return#sql是空,不执行
        #增加到入库列表中
        with self.writeLock:
            self.writeList.append(sql)
        for db in self.databaseList:    db.flush()  #让所有入库线程去执行插入,现在如果多线程,入为没有顺序
    def run(self,target_class):
        for i in range(self.threadNum):
            try:
                db = target_class(self._name,i,self.db_host,self.db_port,
                                  self.db_user,self.db_password,self.db_name,self)
                if db is None:    continue  #如果是None继续后面的启动
                db.run()                    #运行线程
                self.databaseList.append(db)#增加到线程列表,用于刷新和关闭时调用
            except Exception as e:
                output(f'[异常]:[databaseMgr.run]:[{i}]:{e}',outputMode.saveLog,enum_Error.localErr)  # 写日志
    def stop(self):
        for database in self.databaseList:  database.stop()#停止所有数据库入库线程