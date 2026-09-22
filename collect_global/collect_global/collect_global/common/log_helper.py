#!/usr/bin/evn python
# coding=utf-8

import os
import datetime
try:
    import threading
except ModuleNotFoundError:
    print('install threading...')
    os.system('pip install threading')

try:
    import time
except ModuleNotFoundError:
    print('install time...')
    os.system('pip install time')

try:
    import queue
except ModuleNotFoundError:
    print('install queue...')
    os.system('pip install queue')
from queue import Queue

from .file_helper import FileHelper

class logHelper:

    def __init__(self, name, path):
        # filePath = os.path.abspath('.') + path
        # print(filePath)
        if name is not None and path is not None:
            self._name = name
            self.__log_file = FileHelper(name, os.path.abspath('.') + path)
        self.__log_mutex = threading.Lock()
        self.__log_net_queue = Queue()
        self.__log_thread = None
        self.__log_is_run = False

    #def log_run(self,is_writer):
    #    if not self.__log_is_run:
    #        self.__log_is_run = True
    #        self.__log_mutex.acquire()
    #        if is_writer is None or is_writer:
    #            info = time.strftime("%H:%M:%S", time.localtime()) + " <" + self._name + "> [Enable]"
    #        else:
    #            info = time.strftime("%H:%M:%S", time.localtime()) + " <" + self._name + "> [Disable]"
    #        self.__log_net_queue.put(info)
    #        self.__log_mutex.release()
    #        self.__log_thread = threading.Thread(target=self.log_process)
    #        self.__log_thread.setDaemon(True)  # 设置成守护线程
    #        self.__log_thread.start()

    def log_run(self, name, path,is_writer):
        if not self.__log_is_run:
            if name is not None and path is not None:
                self._name = name
                self.__log_file = FileHelper(name, os.path.abspath('.') + path)
            self.__log_is_run = True
            #self.__log_mutex.acquire()
            #if is_writer is None or is_writer:
            #    info = time.strftime("%H:%M:%S", time.localtime()) + " <" + self._name + "> [Enable]"
            #else:
            #    info = time.strftime("%H:%M:%S", time.localtime()) + " <" + self._name + "> [Disable]"
            #self.__log_net_queue.put(info)
            #self.__log_mutex.release()
            self.__log_thread = threading.Thread(target=self.log_process)
            self.__log_thread.setDaemon(True)  # 设置成守护线程
            self.__log_thread.start()

    def log_stop(self):
        if self.__log_is_run:
            #self.__log_mutex.acquire()
            #info = time.strftime("%H:%M:%S", time.localtime()) + " <" + self._name + "> [Clean]"
            #self.__log_net_queue.put(info)
            #self.__log_mutex.release()
            #time.sleep(2)
            self.__log_is_run = False

            self.__log_thread.join()
            self.__log_thread = None

            self.__log_net_queue.queue.clear()  # 清空队列
            self.__log_file.close_file()

    def log_save(self, info):
        if not self.__log_is_run:
            return
        #输出带毫秒
        now = datetime.datetime.now()
        info = now.strftime("%H:%M:%S.") + f"{now.microsecond:06.0f}"[:3] + " " + info
        #输出秒
        #info = time.strftime("%H:%M:%S", time.localtime()) + " " + info
        self.__log_mutex.acquire()
        self.__log_net_queue.put(info)
        self.__log_mutex.release()

    def log_save_1(self, info):
        self.log_save(info)

    def log_save_2(self, info):
        self.log_save(info)

    def log_process(self):
        counter = 0
        while self.__log_is_run:
            counter = counter + 1
            if counter > 60 * 60:
                self.__log_file.clean_file()
                counter = 0
            time.sleep(1)
            mark = False
            self.__log_mutex.acquire()
            while not self.__log_net_queue.empty():
                try:
                    info = self.__log_net_queue.get_nowait()
                    # path = time.strftime("/%Y_%m_%d_%H", time.localtime()) + ".txt"
                    path = time.strftime("/%Y_%m_%d", time.localtime()) + ".txt"
                    self.__log_file.write_file(info, path, True)
                    mark = True
                except Exception as e:
                    print(str(e.args))
            self.__log_mutex.release()
            if mark:
                self.__log_file.flush_file()  # 缓冲区内容写入文件