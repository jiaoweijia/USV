# 控制命令模块类，负责生成和发送控制命令给无人船
# 用于生成和发送控制命令 命令封装层：把"发PWM/OTA/重启/相机"翻译成文本，按船ID查IP后发
from PySide6.QtCore import QObject, Signal
from USVManager import USVManager
class CommandManager(QObject):
    """控制命令模块类，负责生成和发送控制命令给无人船"""
    
    # 定义信号，用于通知其他模块命令发送状态
    command_sent = Signal(str, str, bool)  # 参数：无人船ID, 命令内容, 是否成功
    
    def __init__(self, udp_comm, usv_manager: USVManager = None):#第一个传入UDPCOMN对象
        """初始化控制命令模块
        
        Args:
            udp_comm: UDP通讯模块实例
            usv_manager: 无人船管理模块实例
        """
        super().__init__()
        self.udp_comm = udp_comm
        self.usv_manager = usv_manager
    
    def send_control_command(self, usv_id, pwm1, pwm2):
        """发送控制命令给无人船
        
        Args:
            usv_id: 无人船ID
            pwm1: 第一个PWM值
            pwm2: 第二个PWM值
            
        Returns:
            bool: 发送是否成功
        """
        # 获取无人船信息
        usv_info = self.usv_manager.get_usv_info(usv_id) #查id
        if not usv_info:
            print(f"无人船 {usv_id} 未注册")
            self.command_sent.emit(usv_id, f"{pwm1},{pwm2}", False)
            return False
        
        # 生成控制命令
        command = f"{pwm1},{pwm2}"
        
        # 发送命令
        success = self.udp_comm.send_message(
            command, 
            usv_info['ip'], 
            usv_info['port']
        )
        
        # 发射命令发送状态信号
        self.command_sent.emit(usv_id, command, success)
        
        return success
    
    def send_ota_command(self, usv_id):
        """发送OTA命令给无人船
        
        Args:
            usv_id: 无人船ID
            
        Returns:
            bool: 发送是否成功
        """
        # 获取无人船信息
        usv_info = self.usv_manager.get_usv_info(usv_id)
        if not usv_info:
            print(f"无人船 {usv_id} 未注册")
            self.command_sent.emit(usv_id, "OTA", False)
            return False
        
        # 发送OTA命令
        success = self.udp_comm.send_message(
            "OTA", 
            usv_info['ip'], 
            usv_info['port']
        )
        
        # 发射命令发送状态信号
        self.command_sent.emit(usv_id, "OTA", success)
        
        return success
    
    def send_restart_command(self, usv_id):
        """发送Restart命令给无人船
        Args:
            usv_id: 无人船ID
        Returns:
            bool: 发送是否成功
        """
        # 获取无人船信息
        usv_info = self.usv_manager.get_usv_info(usv_id)
        if not usv_info:
            print(f"无人船 {usv_id} 未注册")
            self.command_sent.emit(usv_id, "Restart", False)
            return False
        
        # 发送Restart命令
        success = self.udp_comm.send_message(
            "Restart", 
            usv_info['ip'], 
            usv_info['port']
        )
        
        # 发射命令发送状态信号
        self.command_sent.emit(usv_id, "Restart", success)
        
        return success

    def send_camera_command(self, usv_id):
        """发送Camera命令给无人船
        
        Args:
            usv_id: 无人船ID
            
        Returns:
            bool: 发送是否成功
        """
        # 获取无人船信息
        usv_info = self.usv_manager.get_usv_info(usv_id)
        if not usv_info:
            print(f"无人船 {usv_id} 未注册")
            self.command_sent.emit(usv_id, "Camera_Toggle", False)
            return False  
        # 发送Camera命令
        success = self.udp_comm.send_message(
            "Camera_Toggle", 
            usv_info['ip'], 
            usv_info['port']
        )
        
        # 发射命令发送状态信号
        self.command_sent.emit(usv_id, "Camera_Toggle", success)
        
        return success

    def send_command_to_all(self, command):
        """发送命令给所有已连接的无人船
        
        Args:
            command: 要发送的命令内容
            
        Returns:
            dict: 发送结果，格式：{usv_id: 是否成功}
        """
        results = {}
        all_usvs = self.usv_manager.get_all_usvs()
        
        for usv_id, usv_info in all_usvs.items():
            success = self.udp_comm.send_message(
                command, 
                usv_info['ip'], 
                usv_info['port']
            )
            results[usv_id] = success
            self.command_sent.emit(usv_id, command, success)
        
        return results
