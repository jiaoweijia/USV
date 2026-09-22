#系统模块
import json
from datetime import datetime
from typing import Dict, List, Union
#导入日志管理器
from .logManager import output, outputMode,enum_Error
from .commonTools import *
#这个类只用json转换操作，没有具体业务功能
#字符串转成dict数据
def load_json(json_str):
    try:
        #如果不是str返回None,其它则转换成dict或者array
        json_data = json.loads(json_str) if isinstance(json_str, str) else None
        return json_data
    except json.JSONDecodeError as e:
        output(f"[load_json]:JSON解析错误:{e}\n数据:{json_str}",outputMode.saveLog,enum_Error.formatErr)
    return None
#判断json中指定路径的节点是否是数组
def josnNode_is_array(json_data, path):
    """检查 JSON 中指定路径的节点是否为数组"""
    current = json_data
    for key in path.split('.'):
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return False
    return isinstance(current, list)

#这个类在构造时，传入json解析后的对象，这样获取节点时，参数可以少传入一个参数
class loadJsonNode:
    def __init__(self,obj):
        self.obj = obj
    #析构函数
    def __del__(self):
        pass
    @staticmethod
    def toJsonString(obj,en_ascii=False,ind=None):
        try:
            #return json.dumps(obj,ensure_ascii=en_ascii,indent=ind) if obj else "{{}}"
            #去掉json字符串的的错误转义
            return json.dumps(obj,ensure_ascii=en_ascii,indent=ind)#.replace('\\', "").replace('"[', "[").replace(']"', "]").replace("'", '"') if obj else "{{}}"
        except Exception as e:
            output(f"[toJsonString]:错误:{e}\n数据:{obj}",outputMode.saveLog,enum_Error.warning)
        return "{{}}"
    @staticmethod
    def parse_items(objArray,target_class):
        """解析 rwxx 中的 rw 字段，生成扁平化的成员列表"""
        items = []
        for _ in range(1):
            if objArray is None or target_class is None:
                break
            try:
                for member in objArray:
                    if isinstance(member, dict):
                        items.append(target_class(member))
            except Exception as e:
                output(f"[parse_items]错误:{e}",outputMode.saveLog,enum_Error.warning)
        return items
    @staticmethod
    def parse_dict(objArray,target_class, key_attr='id'):
        """解析 rwxx 中的 rw 字段，生成扁平化的成员列表"""
        dicts: Dict[str, target_class]={}
        try:
            for member in objArray:
                if isinstance(member, dict) is False:
                    continue    
                nodeVal = target_class(member)
                if nodeVal is None:
                    continue
                # 动态获取指定属性
                key = getattr(nodeVal, key_attr, None)
                if key is not None:
                    dicts[key] = nodeVal
        except Exception as e:
            output(f"[parse_dict]复制错误:{e}",outputMode.saveLog,enum_Error.warning)
        return dicts

    #加上接口方式是保证返回类型
    @staticmethod
    def _stringNode(obj, key,default=''):
        try:
            return dataConvertManager.data2str(obj.get(key,default),default) if obj else default
        except Exception as e:
            output(f"[stringNode]:节点类型错误，错误:{e}",outputMode.saveLog,enum_Error.warning)
            pass
        return default
    def stringNode(self, key,default=''):
        return loadJsonNode._stringNode(self.obj, key,default)

    def _intNode(obj, key,default=0):
        try:
             return dataConvertManager.data2int(obj.get(key,default),default) if obj else default
        except Exception as e:
            output(f"[intNode]:节点类型错误，错误:{e}",outputMode.saveLog,enum_Error.warning)
            pass
        return default
    def intNode(self, key,default=0):
        return loadJsonNode._intNode(self.obj, key,default)

    def _floatNode(obj, key,default=0.0):
        try:
            return dataConvertManager.data2float(obj.get(key,default),default) if obj else default
        except Exception as e:
            output(f"[floatNode]:节点类型错误，错误:{e}",outputMode.saveLog,enum_Error.warning)
            pass
        return default
    def floatNode(self, key,default=0.0):
        return loadJsonNode._floatNode(self.obj, key,default)

    def _boolNode(obj, key,default=False):
        try:
            return dataConvertManager.data2bool(obj.get(key,default),default) if obj else default
        except Exception as e:
            output(f"[boolNode]:节点类型错误，错误:{e}",outputMode.saveLog,enum_Error.warning)
            pass
        return default
    def boolNode(self, key,default=False):
        return loadJsonNode._boolNode(self.obj, key,default)

    def _listNode(obj, key,default=[]):
        try:
            listInfo = obj.get(key,default) if obj else default
            if isinstance(listInfo, list):
                return listInfo
            if isinstance(listInfo, dict):
                output(f"[listNode]:节点类型错误，{key}是dict",outputMode.saveLog,enum_Error.warning)
                return [listInfo]
            output(f"[listNode]:节点类型错误，错误:{key}",outputMode.saveLog,enum_Error.localErr)
            return default
        except Exception as e:
            output(f"[listNode]:节点转换错误:{e}",outputMode.saveLog,enum_Error.localErr)
            pass
        return default
    def listNode(self, key,default=[]):
        return loadJsonNode._listNode(self.obj, key,default)

    def _dictNode(obj, key,default={}):
        try:
            dictInfo = obj.get(key,default) if obj else default
            if isinstance(dictInfo, dict):
                return dictInfo
            output(f"[dictNode]节点类型错误，错误:{key}",outputMode.saveLog,enum_Error.warning)
            return default
        except Exception as e:
            output(f"[dictNode]节点转换错误:{e}",outputMode.saveLog,enum_Error.warning)
            pass
        return default
    def dictNode(self, key,default={}):
        return loadJsonNode._dictNode(self.obj, key,default)

    def _timeNode(obj, key,format="%Y-%m-%d %H:%M:%S",default=None):
        try:
            if obj is None:
                return default
            return datetime.strptime(loadJsonNode._stringNode(obj,key), format)
        except Exception as e:
            output(f"[timeNode]节点类型错误，错误:{e}",outputMode.saveLog,enum_Error.warning)
            pass
        return default
    def timeNode(self, key,format="%Y-%m-%d %H:%M:%S",default=None):
         return loadJsonNode._timeNode(self.obj, key,format,default)
#使用自定义编码器（可选但更优雅）
class customEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()  # 调用对象的 to_dict() 方法
        return super().default(obj)
#json读取基类,基类目的在于设置dict的obj，这样在使用self.JsonNode的时候函数时不用传递obj,简化参数
class jsonBase:
    def __init__(self,obj):
        self.JsonNode = loadJsonNode(obj)

    def delJsonNode(self,delNode=False):#删除jsonNode节点，防止内存过大，用于使用完成后释放，一般用于派生类加载数据后
        if delNode is not None and delNode is True:
            if hasattr(self, 'JsonNode'):
                has_subclasses = bool(jsonBase.__subclasses__())
                del self.JsonNode
    def to_dict(self):#数据到dict，基类没有实现，主要保证接口存在，需要在派生类中实现功能
        return {}
