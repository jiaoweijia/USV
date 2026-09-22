from __future__ import annotations  # 放在文件顶部

from    pathlib import Path
import  os
import  sys
import  glob
import  time
import  datetime
for _ in range(2):
    try:
        import  psutil
        break
    except ModuleNotFoundError:
        os.system('pip install psutil')
from    datetime import timedelta
from    enum import unique, Enum, auto
import  threading
import  uuid
import  math
import  bisect
from    typing import List, Tuple, Optional
from    decimal import Decimal
import  pathlib
import  struct
import  shutil
#日志输出接口
from    .logManager import output, outputMode,enum_Error
#crcmod  = try_import("crcmod",'pip install crcmod==1.7',2)
for _ in range(2):
    try:
        import  crcmod
        break #导入成功跳出,
    except ModuleNotFoundError as e:
        output(f"[导入crcmod包]:[错误]:{e}",outputMode.saveLog,enum_Error.localErr)
        #if sys.version.find('3.7.') != -1:
        os.system('pip install crcmod==1.7')
        #else:
        #    os.system('pip install crcmod')

for _ in range(2):
    try:
        import  numpy as np
        break #导入成功跳出,
    except ModuleNotFoundError as e:
        output(f"[导入numpy包]:[错误]:{e}",outputMode.saveLog,enum_Error.localErr)
        #if sys.version.find('3.7.') != -1:
        os.system('pip install numpy')
        #else:
        #    os.system('pip install crcmod')


#生成新的uuid
def getUUIDString():
    random_uuid = uuid.uuid4()
    return random_uuid.hex

#判断是否在调试模式
def is_debugging():
    return sys.gettrace() is not None

## 网络断开相关的关键词（根据实际错误信息补充）
network_keywords = [
    "timeout",              #超时
    "network",              #网络相关
    "connection",           #连接问题
    "refused",              #连接被拒绝
    "broken pipe",          #管道破裂（连接中断）
    "unreachable",          #不可达
    "failed to connect",    #连接失败
    'winerror 10061',       #windows socket异常
    'winerror 10053'        #windows socket异常
]
def checkNetConnect(error_msg):
    bRes = True
    error_msg = error_msg.lower()  # 转为小写，方便关键词匹配

    # 判断错误信息是否包含网络相关关键词
    if any(keyword in error_msg for keyword in network_keywords):
        bRes = False
    return bRes
#得到类加函数名称
def cmn(self=None):
    """一行代码获取当前方法名"""
    import sys
    frame = sys._getframe(1)
    func_name = frame.f_code.co_name
    return f"{self.__class__.__name__}.{func_name}" if self else func_name
class fileManager:
    def query_file(path,exName="csv",childDir = False):
        files = []
        # 判断是否为目录
        if os.path.isdir(path):
            # 匹配目录下所有 .csv 文件（包括子目录的话用 recursive=True）
            # 只匹配当前目录
            paths=[]
            if childDir:# 若需递归匹配子目录：
                paths = glob.glob(os.path.join(path, "**", f'*.{exName}'), recursive=True)
            else:
                paths = glob.glob(os.path.join(path, f'*.{exName}'))
            
            for path in paths:
                # 确保是文件（排除可能名为 "xxx.csv" 的目录）
                if os.path.isfile(path):
                    files.append(path)
            print(f"从目录加载了 {len(files)} 个{exName}文件")
    
        # 判断是否为文件
        elif os.path.isfile(path):
            # 检查文件是否为 .csv 格式
            if path.endswith(f'.{exName}'):
                files.append(path)
                print("加载了单个{exName}文件")
            else:
                print(f"指定路径是文件，但不是 .{exName} 格式")
        return files
    #写文件,以utf-8-sig编码保存
    def writeFile(file_name,content):
        res= False
        errInfo = ''
        try:
            with open(file_name, 'w', encoding='utf-8-sig') as file:  # 'r' 表示只读模式，encoding根据文件实际编码调整，常见utf-8、gbk等
                file.write(content)
            res = True
        except FileNotFoundError:
            errInfo = f"文件 {file_name} 未找到"
        except Exception as e:
            errInfo = f"写文件时发生错误: {e}"

        return res,errInfo
    #先以utf-8读取,如果失败在以gbk读取,如果二种都读取失败则返回失败,也可以在函数里扩展其它编码的读写
    def readTextFile(filename):
        res         = False
        errInfo     = ''
        lines_list  = []
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines_list = [line.rstrip('\n') for line in file]   # 直接迭代文件对象，每次返回一行
            res = True
        except UnicodeDecodeError:
            # 尝试其他编码（如GBK）
            lines_list.clear()
            try:
                with open(filename, 'r', encoding='gbk') as file:
                    lines_list = [line.rstrip('\n') for line in file]
                res = True
            except Exception as e:
                errInfo =f"[readTextFile]:读取文件失败:[{e}]"
        except Exception as e:
            errInfo =f"[readTextFile]:读取文件失败:[{e}]"
        return res,errInfo, lines_list

    def readFile(file_name):
        content = ''
        res = False
        errInfo = ''
        try:
            with open(file_name, 'r', encoding='utf-8-sig') as file:  # 'r' 表示只读模式，encoding根据文件实际编码调整，常见utf-8、gbk等
                content = file.read()  # 一次性读取整个文件内容到字符串
            res = True
        except FileNotFoundError:
            errInfo = f"文件[{file_name}]未找到"
        except Exception as e:
            errInfo = f"读取文件时发生错误:[{e}]"

        return res,errInfo,content    
    def exePath():
        # 获取可执行文件所在目录（打包后）或脚本所在目录（开发环境）
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            base_path = os.path.dirname(sys.executable)
            return base_path
        else:
            # 开发环境
            #base_path = os.path.dirname(os.path.abspath(__file__))
            #return base_path
            try:
                main_file = sys.modules['__main__'].__file__
                main_dir = os.path.dirname(os.path.abspath(main_file))
                return  main_dir
            except AttributeError as e:
                output(f"exePath:无法获取主程序路径（可能作为模块被导入）错误:{e}",outputMode.saveLog, enum_Error.localErr)
            except Exception as e:
                output(f"exePath:无法获取主程序路径,错误:{e}",outputMode.saveLog, enum_Error.localErr)
        return ''
    def exePath1():
         main_file = sys.modules['__main__'].__file__
         return Path(main_file).resolve()
    def removeDir(dir_path):
        # 检查目录是否存在
        if not os.path.exists(dir_path):
            print(f"目录[{dir_path}]不存在")
            return
        # 检查是否为目录（避免误删文件）
        if not os.path.isdir(dir_path):
            print(f"[{dir_path}]不是目录，无法删除")
            return
        try:
            # 递归删除目录及所有内容（包括子目录、文件）
            shutil.rmtree(dir_path)
            print(f"目录[{dir_path}]及其所有内容已成功删除")
        except PermissionError:
            print(f"权限不足，无法删除 [{dir_path}]")
        except OSError as e:
            print(f"删除[{dir_path}]失败：{e}")  # 如文件被占用、只读等情况
    def copyDir(src_dir,dst_dir):
        try:
            # 检查源目录是否存在
            if not os.path.isdir(src_dir):
                print(f"错误：源目录 '{src_dir}' 不存在或不是目录")
            else:
                # 检查目标目录是否已存在（存在则会报错，需手动处理）
                if os.path.exists(dst_dir):
                    print(f"错误：目标目录 '{dst_dir}' 已存在，请先删除或更换名称")
                else:
                    # 复制目录（递归复制所有内容）
                    shutil.copytree(src_dir, dst_dir)
                    print(f"目录 '{src_dir}' 已成功复制到 '{dst_dir}'")

        except PermissionError:
            print(f"权限不足，无法复制目录：{src_dir}")
        except Exception as e:
            print(f"复制目录失败：{e}")


    def delete_old_files(directory, days=10):
        """删除指定目录中超过指定天数的文件"""
        cutoff_time = datetime.datetime.now() - timedelta(days=days)
    
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
        
            # 跳过子目录（只处理文件）
            if os.path.isfile(file_path):
                # 获取文件的最后修改时间
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            
                # 如果文件修改时间早于截止时间，则删除
                if mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        print(f"已删除: {file_path}")
                    except Exception as e:
                        print(f"无法删除 {file_path}: {e}")
    def delete_old_txt_files(directory, days=10, dry_run=True):
        """删除指定目录中超过指定天数的 .txt 文件"""
        cutoff_time = datetime.datetime.now() - timedelta(days=days)
        deleted_count = 0
    
        with os.scandir(directory) as entries:
            for entry in entries:
                # 检查是否为 .txt 文件
                if entry.is_file() and entry.name.endswith('.txt'):
                    # 获取文件修改时间
                    mtime = datetime.datetime.fromtimestamp(entry.stat().st_mtime)
                
                    # 判断是否超过指定天数
                    if mtime < cutoff_time:
                        try:
                            if dry_run:
                                print(f"[模拟] 删除: {entry.path}")
                            else:
                                os.remove(entry.path)
                                print(f"已删除: {entry.path}")
                            deleted_count += 1
                        except Exception as e:
                            print(f"无法删除 {entry.path}: {e}")
    
        print(f"操作完成: 共删除 {deleted_count} 个文件")
    def createDir(dir_path)->bool:
        bRes = False
        try:
            if dir_path and not os.path.exists(dir_path):  # 判断一个目录是否存在
               os.makedirs(dir_path)  # 多层创建目录
            bRes = True
        except Exception as e:
            print(f"创建[{dir_path}]失败:[{e}]")
        return bRes
    def removeFile(file_path):
        try:
            # 检查文件是否存在
            if os.path.exists(file_path):
                # 删除文件
                os.remove(file_path)
                print(f"文件 '{file_path}' 已成功删除")
            else:
                print(f"文件 '{file_path}' 不存在")
        except PermissionError:
            print(f"权限不足，无法删除 '{file_path}'")
        except OSError as e:
            print(f"删除文件失败: {e}")

class dataConvertManager:
    def check_data(val,describ="")->bool:
        if val is None or (isinstance(val,str) and is_empty(val)):
            if val: output(f"{describ}:没有val:({val})",outputMode.saveLog,enum_Error.warning)
            return False
        return True
    def bytes2hexstring(bytesContent):
        try:
            if bytesContent is None or not isinstance(bytesContent, bytes):
                return ''
            return ''.join(['%02X' % b for b in bytesContent])
        except Exception as e:
            output(f'bytes2hexstring错误:{e}',outputMode.saveLog, enum_Error.localErr)
        return ''
    def convert_types(obj):
        """递归转换 Decimal 和 datetime 为 JSON 兼容类型"""
        if isinstance(obj, Decimal):
            return float(obj)  # 转换为浮点数
        elif isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")  # 转换为字符串
        elif isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        elif hasattr(obj, '__dict__'):  # 处理对象类型
            return convert_types(obj.__dict__)
        else:
            return obj
    def data2float(val, default=0.0):
        """将'bs'字段转换为整数，如果转换失败则返回默认值"""
        try:
            return float(val) if dataConvertManager.check_data(val,"data2float") else default
        except Exception as e:
            if isinstance(val,str):
                if val.lower() == 'true':
                    return 1.0
                if val.lower() == 'false':
                    return 0.0
            output(f"[data2float]:无法将({val})转换为浮点:{e}",outputMode.saveLog,enum_Error.warning)
        return default
    #安全转换成int，如果失败返回默认值
    def data2int(val, default=0):
        """将'bs'字段转换为整数，如果转换失败则返回默认值"""
        try:
            return int(val) if dataConvertManager.check_data(val,"data2int") else default
        except Exception as e:
            output(f"[data2int]:无法将val:({val})转换为整数:[错误]:{e}",outputMode.saveLog,enum_Error.warning)
        return default

    def data2str(val, default=''):
        """将'bs'字段转换为整数，如果转换失败则返回默认值"""
        try:
            if val is None: return default
            return str(val)
        except (ValueError, TypeError):
            output(f"data2str无法将val:({val})转换为字符串",outputMode.saveLog,enum_Error.warning)
        return default

    def data2bool(val, default=False):
        """将'bs'字段转换为整数，如果转换失败则返回默认值"""
        if val is None:
            output(f"data2bool 节点类型错误{val}",outputMode.saveLog,enum_Error.warning)
            return default
        try:
            return bool(val)
        except (ValueError, TypeError):
            output(f"data2bool无法将val({val})转换为布尔类型",outputMode.saveLog,enum_Error.warning)

        return default
    #格式化浮点数，保留两位小数，precision为保留小数位数
    def format_floats(obj, precision=2):
        if isinstance(obj, float):
            return round(obj, precision)  # 保留两位小数（仍为浮点数）
            # 或使用:return f"{obj:.{precision}f}" # 转为字符串
        if isinstance(obj, list):
            return [format_floats(item, precision) for item in obj]
        if isinstance(obj, dict):
            return {k: format_floats(v, precision) for k, v in obj.items()}
        return obj
def is_empty(s: str) -> bool:
    """判断字符串是否为空、None 或仅包含空白字符"""
    if s is None:           return True
    if isinstance(s,str):   return not s.strip()
    return True

#判断是dos运行，还是后台运行
def is_running_in_background():
    try:
        if sys.stdin.isatty():              return False    # 检查标准输入是否连接到终端
        if os.isatty(sys.stdout.fileno()):  return False    # 检查标准输出是否被重定向
    except Exception:
        pass
    # 检查父进程是否为服务宿主
    try:
        parent = psutil.Process(os.getppid())
        if parent.name() == "services.exe": return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
    return True

#安全得到dict中的值
def safe_DictValue(dictObj,key,default=None,outMsg = True):
    try:
        if dictObj and isinstance(dictObj,dict) and isinstance(key,str) and key in dictObj:
            return dictObj[key] if dictObj[key] is not None else default
        if outMsg:
            output(f"getDictValue:无法从dict:({dictObj})中获取key:({key})的值",outputMode.saveLog,enum_Error.warning)
        #if dictObj and isinstance(dictObj,dict) and isinstance(key,str):
        #    val = dictObj.get(key,default)
        #    if val: return val
    except Exception as e:
        output(f"getDictValue:无法从dict:({dictObj})中获取key:({key})的值,[错误]:{e}",outputMode.saveLog,enum_Error.warning)
    return default
#检测sql存储的字段值
def checksqlValue(val):
    try:
        if val is None:
            return 'null'
        if isinstance(val,str):
            return f"'{val}'"
        return val
    except Exception as e:
        output(f"checksqlValue:无法将val:({val})转换为字符串:{e}",outputMode.saveLog,enum_Error.warning)
    return 'null'

def checkName(name,nId,default):
    try:
        strName = name
        if is_empty(strName):   strName = default + str(nId)
    except:
        pass
    return strName
#crc计算类
class crc_calute:
    # 计算crc函数
    def calculate_crc16(data):
        crc = 0xFFFF
        polynomial = 0x8005
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFFFF  # 确保结果为16位
        return crc

    def calcrc16(data:bytes):
        crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
        return crc16(data)
    def calcrc32(data:bytes):
        crc32 = crcmod.mkCrcFun(0x104C11DB7, rev=True, initCrc=0xFFFFFFFF, xorOut=0xFFFFFFFF)
        return crc32(data)
class timeManager:
    def __init__(self):
        pass
    def get_time_minus_ms(ms):
        current_time = datetime.datetime.now()
        # 减去n秒
        result_time = current_time - datetime.timedelta(milliseconds=ms)
        return int(result_time.timestamp() * 1000)
    def get_time_minus_s(s):
        current_time = datetime.datetime.now()
        # 减去n秒
        result_time = current_time - datetime.timedelta(seconds=s)
        return int(result_time.timestamp())
    def get_cur_day_local_datetime():
        timestamp = time.time()
        local_time = time.localtime(timestamp)
        year = local_time.tm_year
        month = local_time.tm_mon
        day = local_time.tm_mday
        return datetime.datetime(year, month, day)
    #得到当前小时
    def get_cur_hour_local_datetime():
        timestamp = time.time()
        local_time = time.localtime(timestamp)
        year    = local_time.tm_year
        month   = local_time.tm_mon
        day     = local_time.tm_mday
        houre   = local_time.tm_hour
        #minute = local_time.tm_min     # 分钟
        #second = local_time.tm_sec     # 秒
        return datetime.datetime(year, month, day,houre)
    #得到当天的年月日的毫秒
    def get_cur_day_local_ms():
        return int(get_cur_day_local_datetime().timestamp() * 1000)
    #得到当天的年月日的秒
    def get_cur_day_local_s():
        return int(get_cur_day_local_datetime().timestamp())
    #得到本地时间字符中,如果s参数设置,则是当前时间减去s时间
    def get_current_time_day_local_str_s(s=None):
        if s is None:   return timeManager.format_time_s(timeManager.get_current_time_day_local_s())
        return timeManager.format_time_s(timeManager.get_time_minus_s(s))
    def get_current_time_day_local_str_ms(ms=None):
        if ms is None:  return timeManager.format_time_ms(timeManager.get_current_time_day_local_s())
        return timeManager.format_time_ms(timeManager.get_time_minus_ms(ms))
    
    # 获取时间戳(秒)
    def get_timestamp_s():
        return int(time.time())
    # 获取时间戳(毫秒)
    def get_timestamp_ms():
        return int(round(time.time() * 1000))
        #return time.time_ns() // 1000000 #//表示整数除法 /是真除法float除法

    #格式化时间戳到秒，参数都是浮点秒
    def format_time_s(timestamp) -> str:
        res = ''
        try:
            res = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(e)
        return res

    #格式化utc时间戳到秒，参数都是浮点秒，北京时间减8小时，根据系统设置来得到时区
    def format_time_utc_s(timestamp) -> str:
        res = ''
        try:
            res = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(e)
        return res
    #格式化时间戳到毫秒，参数是秒
    def format_time_utc_ms(timestamp) -> str:
        res = ''
        try:
            res = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except Exception as e:
            print(e)
        return res
    #格式化时间戳到毫秒，参数是秒
    def format_time_ms(timestamp) -> str:
        res = ''
        try:
            res = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except Exception as e:
            print(e)
        return res

# 判断类是否有父类（除 object 外）
def has_parent(cls):
    parents = cls.__bases__
    return len(parents) > 0 and (parents != (object,) or len(parents) > 1)
#安全得到dict的值，如果没有key返回
def checkDictNode(dictNode:dict, key:str):
    resInfo = None 
    try:
        resInfo = dictNode[key] if dictNode and key and key in dictNode else None
    except:
        pass
    return resInfo



class TimeSeriesDataManager:
    def __init__(self,nTotalTime: int=7200 ,bucket_size: int=60):
        """
        初始化时间序列数据管理器
        
        参数:
            bucket_size: 每个桶的秒数，默认为60秒
        """
        self.nTotalTime = nTotalTime
        self.bucket_size = bucket_size
        self.num_buckets = self.nTotalTime // bucket_size + 1  # 总桶数
        self.buckets = [[] for _ in range(self.num_buckets)]  # 初始化桶列表
        
    def _get_bucket_index(self, timestamp: int) -> int:
        """计算时间戳对应的桶索引"""
        return timestamp // self.bucket_size
    
    def insert(self, timestamp: int, value: any) -> None:
        """
        插入时间戳和对应值
        
        参数:
            timestamp: 时间戳（0-7200秒）
            value: 对应的值
        """
        if not (0 <= timestamp <= self.nTotalTime):
            raise ValueError(f"时间戳必须在0-{self.nTotalTime}秒之间")
            
        bucket_idx = self._get_bucket_index(timestamp)
        bucket = self.buckets[bucket_idx]
        
        # 使用二分查找找到插入位置
        idx = bisect.bisect_left(bucket, (timestamp,))
        
        # 如果时间戳已存在则更新，否则插入
        if idx < len(bucket) and bucket[idx][0] == timestamp:
            bucket[idx][1].updateInfo(value)
            #bucket[idx] = (timestamp,bucket[idx][1].updateInfo(value))
        else:
            bucket.insert(idx, (timestamp, value))
    def removeRemainMember(self, timestamp: int) -> None:
        #初始位置不能删除
        if timestamp == 0:
            timestamp = 1

        # 先检查当前桶
        bucket_idx = self._get_bucket_index(timestamp)
        bucket = self.buckets[bucket_idx]
        # 使用二分查找找到第一个大于timestamp的位置
        idx = bisect.bisect_right(bucket, (timestamp,))
        
        if idx < len(bucket) and bucket[idx][0] == timestamp:
            self.buckets[bucket_idx] = bucket[:idx + 1]#去掉后面数据
        elif idx >= 0 :# 如果找到相等的时间戳
            self.buckets[bucket_idx] = bucket[:idx]#去掉后面数据
        for i in range(bucket_idx + 1,len(self.buckets)):
            self.buckets[i] = []

    def query(self, timestamp: int) -> Optional[any]:
        """
        查询时间戳对应的值，不存在时返回前一个时间戳的值
        
        参数:
            timestamp: 时间戳（0-7200秒）
            
        返回:
            存在时返回对应值，不存在时返回前一个时间戳的值，无数据时返回None
        """
        if not (0 <= timestamp <= self.nTotalTime):
            raise ValueError("时间戳必须在0-7200秒之间")
            
        # 先检查当前桶
        bucket_idx = self._get_bucket_index(timestamp)
        bucket = self.buckets[bucket_idx]
        
        # 使用二分查找找到第一个大于timestamp的位置
        idx = bisect.bisect_right(bucket, (timestamp,))
        if idx < len(bucket) and bucket[idx][0] == timestamp:
            return bucket[idx][1]
        # 如果找到相等的时间戳
        if idx > 0 and bucket[idx - 1][0] == timestamp:
            return bucket[idx - 1][1]
            
        # 如果当前桶有更小的时间戳
        if idx > 0:
            return bucket[idx - 1][1]
            
        # 当前桶没有更小的时间戳，检查前一个桶
        for prev_bucket_idx in range(bucket_idx - 1, -1, -1):
            prev_bucket = self.buckets[prev_bucket_idx]
            if prev_bucket:
                return prev_bucket[-1][1]  # 返回前一个桶的最后一个元素
                
        # 没有找到任何数据
        return None
    
    def get_all_data(self) -> List[Tuple[int, any]]:
        """获取所有数据（按时间戳排序）"""
        all_data = []
        for bucket in self.buckets:
            all_data.extend(bucket)
        return sorted(all_data, key=lambda x: x[0])


def bytes_to_string(byte_data, encode='ascii'):
    try:
        byteLen = len(byte_data)
        if byteLen == 1 and byte_data[0] == 0:
            return ''
        if byteLen == 2 and byte_data[0] == 0 and byte_data[1] == 0:
            return ''

        return byte_data.decode(encoding=encode,errors='ignore')
        
    except Exception as e:
        return ""

def bytes_to_uint(byte_data, byte_order='big'):
    """
    将bytes转换为float浮点数
    :param byte_data: 字节数据（bytes类型，长度应为4或8）
    :param byte_order: 字节序，'little'（小端）或'big'（大端），默认小端
    :return: 转换后的无符号值
    """
    # 检查字节长度
    if len(byte_data) == 1:
        format_char = 'B'  # 8位signd char
    elif len(byte_data) == 2:
        format_char = 'H'  # 16位short
    elif len(byte_data) == 4:
        format_char = 'I'  # 32位int
    elif len(byte_data) == 8:
        format_char = 'Q'  # 64位long long
    else:
        raise ValueError("字节长度必须是2（16位int）或4（8位int）")
    
    # 根据字节序选择格式符
    if byte_order == 'little':
        format_str = '<' + format_char  # 小端序
    else:
        format_str = '>' + format_char  # 大端序
    
    # 解析字节数据
    return struct.unpack(format_str, byte_data)[0]

def bytes_to_int(byte_data, byte_order='big'):
    """
    将bytes转换为int
    :param byte_order: 字节序，'little'（小端）或'big'（大端），默认小端
    :return: 转换后的int值
    """
    # 检查字节长度
    if len(byte_data) == 1:
        format_char = 'b'  # 8位signd char
    elif len(byte_data) == 2:
        format_char = 'h'  # 16位short
    elif len(byte_data) == 4:
        format_char = 'i'  # 32位int
    elif len(byte_data) == 8:
        format_char = 'q'  # 64位long long
    else:
        raise ValueError("字节长度必须是2（16位int）或4（8位int）")
    
    # 根据字节序选择格式符
    if byte_order == 'little':
        format_str = '<' + format_char  # 小端序
    else:
        format_str = '>' + format_char  # 大端序
    
    # 解析字节数据
    return struct.unpack(format_str, byte_data)[0]
def bytes_to_float(byte_data, byte_order='little'):
    """
    将bytes转换为float浮点数
    :param byte_data: 字节数据（bytes类型，长度应为4或8）
    :param byte_order: 字节序，'little'（小端）或'big'（大端），默认小端
    :return: 转换后的float值
    """
    # 检查字节长度（4字节对应32位浮点数，8字节对应64位浮点数）
    if len(byte_data) == 4:
        format_char = 'f'  # 32位浮点数
    elif len(byte_data) == 8:
        format_char = 'd'  # 64位浮点数
    else:
        raise ValueError("字节长度必须是4（32位float）或8（64位double）")
    
    # 根据字节序选择格式符
    if byte_order == 'little':
        format_str = '<' + format_char  # 小端序
    else:
        format_str = '>' + format_char  # 大端序
    
    # 解析字节数据
    return struct.unpack(format_str, byte_data)[0]


def float_to_bytes(float_data, byte_order='little'):
    """
    将bytes转换为float浮点数
    :param byte_data: 字节数据（bytes类型，长度应为4或8）
    :param byte_order: 字节序，'little'（小端）或'big'（大端），默认小端
    :return: 转换后的float值
    """
    # 检查字节长度（4字节对应32位浮点数，8字节对应64位浮点数）
    if type(float_data) == np.float32:
        format_char = 'f'  # 32位浮点数
    elif type(float_data) == float:
        format_char = 'd'  # 64位浮点数
    else:
        raise ValueError("字节长度必须是4（32位float）或8（64位double）")
    
    # 根据字节序选择格式符
    if byte_order == 'little':
        format_str = '<' + format_char  # 小端序
    else:
        format_str = '>' + format_char  # 大端序
    
    # 解析字节数据
    return struct.pack(format_str, float_data)
def data_to_bytes(int_data, byte_order='little'):
    """
    将bytes转换为float浮点数
    :param byte_data: 字节数据（bytes类型，长度应为4或8） int8, int16, int32, int64
    :param byte_order: 字节序，'little'（小端）或'big'（大端），默认小端
    :return: 转换后的float值
    """
    # 检查字节长度（4字节对应32位浮点数，8字节对应64位浮点数）
    if type(int_data) == np.int8:
        format_char = 'b'  # 32位浮点数
    elif type(int_data) == np.uint8:
        format_char = 'B'  # 32位浮点数
    elif type(int_data) == np.int16:
        format_char = 'h'  # 64位浮点数
    elif type(int_data) == np.uint16:
        format_char = 'H'  # 64位浮点数
    elif type(int_data) == np.int32:
        format_char = 'i'  # 64位浮点数
    elif type(int_data) == np.uint32:
        format_char = 'I'  # 64位浮点数
    elif type(int_data) == np.int64:
        format_char = 'q'  # 64位浮点数
    elif type(int_data) == np.uint64:
        format_char = 'Q'  # 64位浮点数
    elif type(int_data) == np.float32:
        format_char = 'f'  # 64位浮点数
    elif type(int_data) == float:
        format_char = 'd'  # 64位浮点数
    elif type(int_data) == str:
        format_char = f'{len(int_data)}s'  #字符串
    else:
        raise ValueError("字节长度必须是4（32位float）或8（64位double）")
    
    # 根据字节序选择格式符
    if byte_order == 'little':
        format_str = '<' + format_char  # 小端序
    else:
        format_str = '>' + format_char  # 大端序
    
    # 解析字节数据
    return struct.pack(format_str, float_data)
#判断是否是debug模式
def is_debugging():
    # 获取当前进程 ID
    current_pid = os.getpid()
    # 获取当前进程信息
    current_process = psutil.Process(current_pid)
    # 获取命令行参数（如调试器的命令）
    cmdline = current_process.cmdline()
    # 常见调试器关键词（根据实际情况补充）
    debug_keywords = ["debugpy", "pdb", "pydevd", "pycharm"]
    # 检查命令行中是否包含调试相关关键词
    return any(keyword in ' '.join(cmdline).lower() for keyword in debug_keywords)

#设置控制台模式,只对windows操作系统有效,如果是release运行,则设置不可以编辑模式
def setConsoleMode():
    if sys.platform == "win32":
        import ctypes

        def disable_quick_edit_mode():
            # 获取控制台模式
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            hStdin = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE = -10
    
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(hStdin, ctypes.byref(mode)):
                return False
    
            # 清除快速编辑模式位
            mode.value &= ~(0x0040 | 0x0080)  # 禁用快速编辑和插入模式
    
            if not kernel32.SetConsoleMode(hStdin, mode):
                return False
            return True

        # 在程序开始时调用
        if is_debugging() is False:
            disable_quick_edit_mode()#禁用快速编辑模式,解决dos界面不动情况 
def safe_enum(value,target_class):
    try:
        return target_class(value)
    except Exception as e:
        output(f"[safe_enum]:[{target_class.__name__}]转换错误错误:{e}",outputMode.saveLog, enum_Error.localErr)
    return None


def find_in_package(strDarwin,strWin32,strLinux) -> Optional[str]:
    """Find the `snap7.dll` file according to the os used.
    Returns:
        Full path to the `snap7.dll` file.
    """
    basedir = pathlib.Path(__file__).parent.absolute()
    if sys.platform == "darwin":
        lib = strDarwin #'libsnap7.dylib'
    elif sys.platform == "win32":
        lib = strWin32 #'snap7.dll'
    else:
        lib = strLinux#'libsnap7.so'
    full_path = basedir.joinpath('lib', lib)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return str(full_path)
    return None

import ipaddress
import re

class IPValidator:
    """IP地址验证器"""
    
    @staticmethod
    def is_ipv4(ip_str):
        """检查是否为有效的IPv4地址"""
        try:
            ipaddress.IPv4Address(ip_str)
            return True
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def is_ipv6(ip_str):
        """检查是否为有效的IPv6地址"""
        try:
            ipaddress.IPv6Address(ip_str)
            return True
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def is_ip(ip_str):
        """检查是否为有效的IP地址（IPv4或IPv6）"""
        return IPValidator.is_ipv4(ip_str) or IPValidator.is_ipv6(ip_str)
    
    @staticmethod
    def get_ip_version(ip_str):
        """获取IP地址版本"""
        if IPValidator.is_ipv4(ip_str):
            return 4
        elif IPValidator.is_ipv6(ip_str):
            return 6
        else:
            return None
def is_in_f1_to_f360(s):
    # 匹配模式：f开头，后跟数字
    pattern = r'^f(\d+)$'
    match = re.match(pattern, s, re.IGNORECASE)  # 忽略大小写
    
    if not match:
        return False  # 格式不符，肯定不在 f1-f360
    
    num = int(match.group(1))
    return  (1 <= num <= 360)

class BCD_Manager:
    def unpack_bcd(bcd_bytes, num_digits=None):
        """解压BCD字节序列，返回整数列表"""
        digits = []
    
        for bcd_byte in bcd_bytes:
            high = (bcd_byte >> 4) & 0x0F
            low = bcd_byte & 0x0F
        
            # 处理填充0（如0xF表示无数据）
            if high <= 9:
                digits.append(high)
            if low <= 9:
                digits.append(low)
    
        # 如果指定了数字位数，进行截断
        if num_digits and len(digits) > num_digits:
            digits = digits[-num_digits:]
    
        return digits

    def int_to_bcd(value: int, num_digits: int = 0) -> bytes:
        """
        将整数转换为BCD编码的字节
        :param value: 要转换的整数
        :param num_digits: 指定的BCD位数（每个字节存2位十进制数字）
        :return: BCD编码的字节
        """
        if value < 0:
            raise ValueError("BCD不支持负数")
    
        # 将整数转为字符串，确保偶数长度
        digits = str(value)
    
        # 如果需要补零
        if num_digits > 0:
            digits = digits.zfill(num_digits if num_digits % 2 == 0 else num_digits + 1)
    
        # 确保偶数长度
        if len(digits) % 2 != 0:
            digits = '0' + digits
    
        # 每两个数字转换成一个字节
        bcd_bytes = bytearray()
        for i in range(0, len(digits), 2):
            high = int(digits[i])        # 十位
            low = int(digits[i+1])       # 个位
            bcd_byte = (high << 4) | low  # 组合成一个字节
            bcd_bytes.append(bcd_byte)
    
        return bytes(bcd_bytes)
    def bcd_to_int_complete(bcd_bytes):
        """完整的BCD转整数，处理各种边界情况"""
        digits = []
    
        for bcd_byte in bcd_bytes:
            high = (bcd_byte >> 4) & 0x0F
            low = bcd_byte & 0x0F
        
            # 只添加有效的BCD数字
            if high <= 9:
                digits.append(str(high))
            if low <= 9:
                digits.append(str(low))
    
        if not digits:
            return 0
    
        return int(''.join(digits))
    def int_to_bcd_16bit(value: int) -> bytes:
        """
        将0-9999的整数转换为16位BCD（4位数字）
        :param value: 0-9999的整数
        :return: 2字节BCD
        """
        if not 0 <= value <= 9999:
            raise ValueError("值必须在0-9999范围内")
    
        # 格式化为4位数字，前面补零
        digits = f"{value:04d}"  # "0022"
    
        # 每两个数字转换为一个字节
        byte1 = (int(digits[0]) << 4) | int(digits[1])  # 千位和百位
        byte2 = (int(digits[2]) << 4) | int(digits[3])  # 十位和个位
    
        # 返回2字节，大端序
        return bytes([byte1, byte2])  # b'\x00\x22'
    def bcd_16bit_to_int(bcd_data: bytes, big_endian: bool = True) -> int:
        """
        16位BCD转整数
        :param bcd_data: 2字节BCD数据
        :param big_endian: True-大端序，False-小端序
        :return: 整数
        """
        if len(bcd_data) != 2:
            raise ValueError("需要2字节数据")
    
        if big_endian:
            byte1, byte2 = bcd_data[0], bcd_data[1]  # 大端序
        else:
            byte2, byte1 = bcd_data[0], bcd_data[1]  # 小端序
    
        # 解析BCD
        thousands = (byte1 >> 4) & 0x0F
        hundreds = byte1 & 0x0F
        tens = (byte2 >> 4) & 0x0F
        units = byte2 & 0x0F
    
        # 组合成整数
        return thousands * 1000 + hundreds * 100 + tens * 10 + units
    def int_to_bcd_32bit(value: int, big_endian: bool = True) -> bytes:
        """
        将整数转换为32位BCD（8位十进制数字）
        :param value: 0-99,999,999的整数
        :param big_endian: True-大端序，False-小端序
        :return: 4字节BCD数据
        """
        if not 0 <= value <= 99_999_999:
            raise ValueError("值必须在0-99,999,999范围内")
    
        # 格式化为8位数字
        digits = f"{value:08d}"  # 例如22 -> "00000022"
    
        # 每2位数字转换为1个字节
        bytes_list = []
        for i in range(0, 8, 2):
            high_digit = int(digits[i])
            low_digit = int(digits[i + 1])
            bcd_byte = (high_digit << 4) | low_digit
            bytes_list.append(bcd_byte)
    
        # 转换为字节并处理字节序
        result = bytes(bytes_list)
        if not big_endian:
            # 小端序：反转字节顺序
            result = result[::-1]
    
        return result
    def bcd_32bit_to_int(bcd_data: bytes, big_endian: bool = True) -> int:
        """
        32位BCD转整数
        :param bcd_data: 4字节BCD数据
        :param big_endian: True-大端序，False-小端序
        :return: 整数
        """
        if len(bcd_data) != 4:
            raise ValueError("需要4字节数据")
    
        # 处理字节序
        data = bcd_data if big_endian else bcd_data[::-1]
    
        # 解析BCD
        result = 0
        for byte in data:
            high_digit = (byte >> 4) & 0x0F
            low_digit = byte & 0x0F
        
            # 验证有效性
            if high_digit > 9 or low_digit > 9:
                raise ValueError(f"无效的BCD数据: {byte:02x}")
        
            result = result * 100 + high_digit * 10 + low_digit
    
        return result
