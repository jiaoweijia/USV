from __future__ import annotations  # 放在文件顶部
#枚举定义
from enum import unique, Enum, auto
from collect_global.common import commonTools as tools
class topic_Head():
    def __init__(self):
        self.deviceId=''
        self.taskId=''
        self.type = 0
        self.timestamp = 0
        self.content = None
    def to_dict(self):
        dictRes = {}
        dictRes['deviceId'] = self.deviceId
        dictRes['taskId']   = self.taskId
        dictRes['type']     = self.type
        dictRes['timestamp']= self.timestamp
        if self.content is not None:
            dictRes['content'] = self.content
       
        # if isinstance(self.content,dict):
        #     dictRes['content'] = self.content
        # elif isinstance(self.content,list):
        #     dictRes['content'] = [val.to_dict() for val in self.content ]

        return dictRes
#不同主题对应的类
#Ais成员定义
ais_Member_define={
    #成员名称       #别名     #描述          #类型     #初值
    "source"      : (""     ,"数据源"         ,int   ,-1  ),  #用于扩展,0.ais,1.雷达
    "sign_type"   : (""     ,"信号类型"       ,str   ,''  ),  #信号类型
    "type"        : (""     ,"信号类型"       ,str   ,''  ),  #信号类型
    "name"        : (""     ,"名称"           ,str   ,''  ),
	"callsg"      : (""     ,"呼号"           ,str   ,''  ),
	"mmsi"        : ("id"   ,"船舶识别码"     ,int   ,0  ),
    "lon"         : (""     ,"经度"           ,float ,90  ),
    "lat"         : (""     ,"纬度"           ,float ,180  ),
    "sog"         : (""     ,"航速"           ,float ,102  ),
    "cog"         : (""     ,"航向"           ,float ,90  ),
    "hdg"         : (""     ,"船艏向"         ,float ,512  ),
    "rot"         : (""     ,"转向率"         ,float ,0  ),
    "length"      : (""     ,"船长"           ,float ,0  ),
    "width"       : (""     ,"船宽"           ,float ,0  ),
    "DemensionA"  : (""     ,"gps距离船艏"    ,int   ,0  ),
    "DemensionB"  : (""     ,"gps距离船艉"    ,int   ,0  ),
    "DemensionC"  : (""     ,"gps距离左舷"    ,int   ,0  ),
    "DemensionD"  : (""     ,"gps距离右舷"    ,int   ,0  ),
    "timestamp"   : (""     ,"接收时间"       ,int   ,0  ),
}

class topic_define (Enum):
    #通导信息                           #别名                     #类信息    #描述
    navigation_gps                =("navigation/gps"             ,None      ,"GPS信息")
    navigation_beidou             =("navigation/beidou"          ,None      ,"北斗信息")
    navigation_depth_finder       =("navigation/depth_finder"    ,None      ,"测深仪")
    navigation_wind_speed_angle   =("navigation/wind_speed_angle",None      ,"风速风向仪")
    navigation_compass            =("navigation/compass"         ,None      ,"电罗经")
    navigation_inertial           =("navigation/inertial"        ,None      ,"惯导信息")
    navigation_simulated          =("navigation/simulated"       ,None      ,"模拟信息")
    #环境感知                                                    
    senson_ais                    =("senson/ais"                 ,ais_Member_define  ,"ais信息") # pyright: ignore[reportUndefinedVariable]
    senson_radar                  =("senson/radar"               ,None  ,"雷达信息")
    senson_visual                 =("senson/visual"              ,None  ,"视觉信息")
    senson_result                 =("senson/result"              ,None  ,"融合信息")
    #海图信息                                                   
    charts_obs                    =("charts/obs"                 ,None  ,"碍航物信息")
    charts_route                  =("charts/route"               ,None  ,"航线信息")

class dynamicMembersCls:
    def __init__(self,dictInfo,dictVal=None):
        self.dictInfo= dictInfo
        self.from_dict(dictVal)
    def to_dict(self):
        dictRes = {}
        for k,v in self.dictInfo.items():
            if hasattr(self, k) and (val := getattr(self, k)) is not None:  dictRes[k] = val
        return dictRes
    def from_dict(self,dictVal):
        if dictVal is None: return
        for k,v in self.dictInfo.items():
            key = k if tools.is_empty(v[0]) else v[0]
            if key in dictVal:    setattr(self,k, dictVal[key])
    #从接收里读取
    def loadFrom_Recv(self,dictVal):
        pass
'''
    正常使用dynamicMembersCls可以减少代码量,
    但是为了让vs工具能显示成员,所以每个类都实例了一下,
    或者有需要特殊处理的在重载即可
'''
class aisInfo(dynamicMembersCls):
    source      :int   #数据源"     
    sign_type   :str   #信号类型"
    type        :int   #设备类型
    name        :str   #名称"       
    callsg      :str   #呼号"       
    mmsi        :int   #船舶识别码" 
    lon         :float #经度"       
    lat         :float #纬度"       
    sog         :float #航速"       
    cog         :float #航向"       
    heading     :float #船艏向"     
    rot         :float #转向率"     
    length      :float #船长"       
    width       :float #船宽"       
    DemensionA  :int   #gps距离船艏"
    DemensionB  :int   #gps距离船艉"
    DemensionC  :int   #gps距离左舷"
    DemensionD  :int   #gps距离右舷"
    timestamp   :int   #接收时间"   
    def __init__(self,dictInfo,dictVal=None):
        #这种是通过使用定义文件定义成员变量,但是在vs里实例不能使用.显示成员内容,在pycharm可以
        dynamicMembersCls.__init__(self,dictInfo,dictVal)
    # #从接收里读取
    # def loadFrom_Recv(self,dictVal):
    #     self.mmsi       = dictVal.get('mmsi',-1)
    #     self.sign_type  = dictVal.get('sign_type','')
    #     info = dictVal.get('info',{})
    #     self.from_dict(info)
    #     for k,v in ais_Member_define.items():
    #         if k == 'mmsi' or k == 'sign_type': continue
    #         if k in info:
    #             setattr(self,k,info[k])




