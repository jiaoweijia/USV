#枚举定义
from enum import unique, Enum, auto

from collect_global.common.baseClass import commonBase
@unique#枚举类修饰符，唯一检查
class enum_device_data_type(Enum):
    vdo = 0
    vdm = 1
    radar = 2

@unique#枚举类修饰符，唯一检查
class enum_device_type(Enum):
    none                = (0,"没有定义")
    auto                = (1,"自适应")
    gps                 = (2,"GPS")
    beidou              = (3,"北斗")
    depth_finder        = (4,"测深仪")
    wind_Speed_Angle    = (5,"风速风向仪")
    compass             = (6,"电罗经")
    ais                 = (7,"ais信息")
    #如果不全,后续补全
    integrate_target    =(8,"融合目标信息") #雷达-视频 Ais 最后结果输出
    guandao             =(9,"惯导信息")     #刘鹏确认\
    haitushuju          =(10,"查询海图数据")
    navigation_route    =(11,"航线设计")
    task_info           =(12,"任务信息")
    control_info        =(13,"控制信息")
    order_info          =(14,"指令信息")

    
#设备基本信息
class deviceBase(commonBase):
    def __init__(self,deviceType):
        commonBase.__init__(self)
        self.deviceType = deviceType
#gps信息
class gpsDevice(deviceBase):
    def __init__(self,argv ,**argm):
        super().__init__(enum_device_type.gps)
        self.longitude = -180   #经度
        self.latitude  = -90    #纬度
        self.cosg      = 0      #航速
        self.sosg       = 0     #航向
        #不够补全
#北斗信息
class beidouDevice(gpsDevice):
    def __init__(self, deviceType):
        super().__init__(enum_device_type.Beidou)
#测深仪

