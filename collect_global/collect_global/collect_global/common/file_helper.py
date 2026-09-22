# 文件操作

import time
import os

try:
    import configparser
except ModuleNotFoundError:
    print('install configparser...')
    os.system('pip install configparser')

try:
    import datetime
except ModuleNotFoundError:
    print('install datetime...')
    os.system('pip install datetime')
from datetime import datetime


# 文件操作类
class FileHelper:

    def __init__(self, name, file_path):
        self._file_fo = None
        self._file_name = ""
        self._file_save_days = 0
        self._is_write = False

        self._name = name
        self._file_path = file_path
        self._init()

    def _init(self,is_write=True):
        self._is_write = is_write
        try:
            if self._is_write:
                if not os.path.exists(self._file_path):  # 判断一个目录是否存在
                    os.makedirs(self._file_path)  # 多层创建目录
        except:
            pass

    # 把时间戳转化为时间: 1479264792 to 2016-11-16 10:53:12
    def TimeStampToTime(self, timestamp):
        timeStruct = time.localtime(timestamp)
        return time.strftime('%Y-%m-%d %H:%M:%S', timeStruct)

    # 获取文件的大小,结果保留两位小数，单位为MB
    def get_FileSize(self, filePath):
        fsize = os.path.getsize(filePath)
        fsize = fsize / float(1024 * 1024)
        return round(fsize, 2)

    # 获取文件的访问时间
    def get_FileAccessTime(self, filePath):
        t = os.path.getatime(filePath)
        return self.TimeStampToTime(t)

    # 获取文件的创建时间
    def get_FileCreateTime(self, filePath):
        t = os.path.getctime(filePath)
        return self.TimeStampToTime(t)

    # 获取文件的修改时间
    def get_FileModifyTime(self, filePath):
        t = os.path.getmtime(filePath)
        return self.TimeStampToTime(t)

    # 打开文件
    def open_file(self, file_name):
        if not self._is_write:
            return
        self.close_file()
        self._file_name = file_name
        path = self._file_path + self._file_name
        try:
            self._file_fo = open(path, "a+b")
        except Exception as e:
            print('Open log [' + path + '] [Error]: ' + str(e.args))

    # 关闭文件
    def close_file(self):
        if not self._is_write:
            return
        try:
            if self._file_fo is not None:
                self._file_fo.close()
        except Exception as e:
            print('Close log file [Error]: ' + str(e.args))
        self._file_fo = None
        self._file_name = ""

    # 写入文件
    def write_file(self, info, file_name, is_line):
        print(info)
        if not self._is_write:
            return
        try:
            if file_name != self._file_name:
                self.open_file(file_name)
            if self._file_fo is None:
                self.open_file(file_name)
            if self._file_fo is not None:
                if is_line:
                    self._file_fo.write((info + "\n").encode())
                else:
                    self._file_fo.write(info.encode())
        except Exception as e:
            print('Write log file [Error]: ' + str(e.args))
            self.close_file()

    # 缓冲区内容写入文件
    def flush_file(self):
        if not self._is_write:
            return
        try:
            if self._file_fo is not None:
                self._file_fo.flush()  # 缓冲区内容写入文件
        except Exception as e:
            print('Flush log file [Error]: ' + str(e.args))

    # 检查文件创建时间，清除过期文件
    def clean_file(self):
        path = self._file_path
        self._clean_file(path)

    def _clean_file(self, path):
        if self._file_save_days <= 0:
            return
        cur_datetime = datetime.now()  # 获得当前时间
        try:
            ls_dir = os.listdir(path)
            dirs = [i for i in ls_dir if os.path.isdir(os.path.join(path, i))]
            if dirs:
                for i in dirs:
                    self._clean_file(os.path.join(path, i))
            files = [i for i in ls_dir if os.path.isfile(os.path.join(path, i))]
            for file in files:
                file_datetime = datetime.fromtimestamp(os.path.getctime(path + "/" + file))
                _days = (cur_datetime - file_datetime).days
                # _seconds = (cur_datetime - file_datetime).seconds
                if _days > self._file_save_days:
                    try:
                        os.remove(path + "/" + file)
                    except Exception as e2:
                        print('Del log [''' + path + "/" + file + '] [Error]: ' + str(e2.args))

        except Exception as e:
            print('Del log file [Error]: ' + str(e.args))
