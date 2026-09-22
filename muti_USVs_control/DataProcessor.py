# 数据处理模块类，负责处理无人船数据的采集和分析
# 用于接收、存储、分析和可视化无人船数据
#数据采集/导出，把实验数据存 CSV/Excel
import time
import csv
from openpyxl import Workbook
from openpyxl.styles import Font
from PySide6.QtCore import QObject, Signal

class DataProcessor(QObject):
    """数据处理模块类，负责处理无人船数据的采集和分析"""
    
    # 定义信号，用于通知其他模块数据采集状态
    data_collected = Signal(str, dict)  # 参数：无人船ID, 采集的数据
    experiment_started = Signal(str)  # 参数：实验类型
    experiment_stopped = Signal(str)  # 参数：实验类型
    
    def __init__(self):
        """初始化数据处理模块"""
        super().__init__()
        self.data_buffer = {}  # 存储采集的数据，格式：{usv_id: [{'timestamp': timestamp, 'data': data}, ...]}
        self.experiment_running = False
        self.current_experiment = None
        self.experiment_start_time = None
    
    def start_experiment(self, experiment_type):
        """开始实验数据采集
        
        Args:
            experiment_type: 实验类型
            
        Returns:
            bool: 是否成功开始
        """
        try:
            if self.experiment_running:
                return False
            
            self.current_experiment = experiment_type
            self.experiment_start_time = time.time()
            self.experiment_running = True
            
            # 清空数据缓冲区
            self.data_buffer = {}
            
            # 发射实验开始信号
            self.experiment_started.emit(experiment_type)
            
            return True
            
        except Exception as e:
            print(f"开始实验失败: {e}")
            return False
    
    def stop_experiment(self):
        """停止实验数据采集"""
        try:
            if not self.experiment_running:
                return False
            
            self.experiment_running = False
            
            # 发射实验停止信号
            self.experiment_stopped.emit(self.current_experiment)
            
            # 保存实验数据
            self.save_experiment_data()
            
            return True
            
        except Exception as e:
            print(f"停止实验失败: {e}")
            return False
    
    def collect_data(self, usv_id, data):
        """采集无人船数据
        
        Args:
            usv_id: 无人船ID
            data: 采集的数据，字典格式
        """
        try:
            if not self.experiment_running:
                return False
            
            # 获取当前时间戳
            timestamp = time.time() - self.experiment_start_time
            
            # 确保该无人船的数据缓冲区存在
            if usv_id not in self.data_buffer:
                self.data_buffer[usv_id] = []
            
            # 添加数据到缓冲区
            self.data_buffer[usv_id].append({
                'DateTime': timestamp,
                'data': data
            })
            
            # 发射数据采集信号
            self.data_collected.emit(usv_id, data)
            
            return True
            
        except Exception as e:
            print(f"采集数据失败: {e}")
            return False
    
    def save_experiment_data(self):
        """保存实验数据到CSV和XLSX文件"""
        try:
            if not self.data_buffer:
                return False
            
            # 创建文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            xlsx_filename = f"data/data_{timestamp}.xlsx"
            
            # 定义固定表头顺序（不含usv_id，因为每个sheet是独立USV）
            fixed_headers = ['DateTime', 'x', 'y', 'rx', 'ry', 'Heading', 'PWM_L', 'PWM_R', 'u', 'v']
            
            # 创建新的工作簿
            wb = Workbook()
            
            # 删除默认的sheet
            if wb.active:
                wb.remove(wb.active)
            
            # 为每个USV创建独立的sheet
            for usv_id, usv_data in self.data_buffer.items():
                # 创建sheet，使用合法的sheet名称
                sheet_name = f"USV{usv_id}" if str(usv_id).isdigit() else str(usv_id)
                # 确保sheet名称不超过31字符且不包含非法字符
                sheet_name = sheet_name[:31].replace(':', '').replace('\\', '').replace('/', '').replace('?', '').replace('*', '').replace('[', '').replace(']', '')
                
                ws = wb.create_sheet(title=sheet_name)
                
                # 写入表头
                ws.append(fixed_headers)
                
                # 设置表头样式
                for cell in ws[1]:
                    cell.font = Font(bold=True)
                
                # 处理并写入该USV的数据
                for entry in usv_data:
                    data = entry['data']
                    
                    # 处理数据转换
                    row_data = [
                        entry['DateTime'],  # DateTime（相对实验开始时间）
                        data.get('x', ''),
                        data.get('y', ''),
                        data.get('rx', ''),
                        data.get('ry', ''),
                        data.get('heading', '') * 180 / 3.1415926535 if data.get('heading', '') is not None else '',
                        data.get('pwml', '') + 1500 if data.get('pwml', '') is not None else '',
                        data.get('pwmr', '') + 1500 if data.get('pwmr', '') is not None else '',
                        data.get('u', ''),
                        data.get('v', '')
                    ]
                    
                    ws.append(row_data)
                
                # 调整列宽
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column_letter].width = adjusted_width
            
            # 保存XLSX文件
            wb.save(xlsx_filename)

            print(f"数据已保存到XLSX文件: {xlsx_filename}")
            print(f"已为 {len(self.data_buffer)} 个USV创建独立sheet")
            
            return True
            
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False
    
    def get_data_buffer(self):
        """获取数据缓冲区
        
        Returns:
            dict: 数据缓冲区
        """
        return self.data_buffer
    
    def get_experiment_status(self):
        """获取实验状态
        
        Returns:
            dict: 实验状态信息
        """
        return {
            'running': self.experiment_running,
            'type': self.current_experiment,
            'start_time': self.experiment_start_time,
            'duration': time.time() - self.experiment_start_time if self.experiment_running else None
        }
