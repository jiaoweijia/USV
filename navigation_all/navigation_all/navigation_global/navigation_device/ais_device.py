import  json
from os import name
import  threading
from    .IEC.IEC61162 import IEC
from    collect_global.common import commonTools as tools, jsonFunc
from    collect_global.common.baseClass import commonBase
#默认协议参数，如果不设置参数时，使用默认参数
from    collect_global.protocol.data_protocol import defProtocol
from    collect_global.protocol.data_protocol import *
from    collect_global.common.logManager import output, outputMode,enum_Error
from    collect_global.pynet.socket_define import *
from    collect_global.common import commonTools as tools
from    collect_global.pynet import redisMgr as redisMgr
from    ..common.topic_define import topic_define,topic_Head
g_mutex_own = threading.Lock()
g_mutex_target = threading.Lock()

g_ais_a_live_max = 120  # AIS A类数据有效时长
g_ais_b_live_max = 300  # AIS B类数据有效时长
g_arpa_live_max = 60  # ARPA数据有效时长

# 全局计算参数
g_engine_full_spd = 412
g_engine_full_power = 2000
g_rudder_full = 30
g_thruster_full_spd = 412
g_thruster_full_power = 2000

# #Ais成员定义
# ais_Member_define={
#     "none"        : (-1     ,"未定义"         ,None    ),
#     "source"      : (1      ,"数据源"         ,int     ),  #用于扩展,0.ais,1.雷达
#     "sign_type"   : (1      ,"信号类型"       ,str     ),  #用于扩展,0.ais,1.雷达
#     "name"        : (0      ,"名称"           ,str     ),
# 	"callsg"      : (1      ,"呼号"           ,str     ),
# 	"mmsi"        : (2      ,"船舶识别码"     ,int     ),
#     "lon"         : (3      ,"经度"           ,float   ),
#     "lat"         : (4      ,"纬度"           ,float   ),
#     "sog"         : (5      ,"航速"           ,float   ),
#     "cog"         : (6      ,"航向"           ,float   ),
#     "heading"     : (7      ,"船艏向"         ,float   ),
#     "roturn"      : (8      ,"转向率"         ,float   ),
#     "length"      : (9      ,"船长"           ,float   ),
#     "width"       : (10     ,"船宽"           ,float   ),
#     "DemensionA"  : (11     ,"gps距离船艏"    ,int     ),
#     "DemensionB"  : (12     ,"gps距离船艉"    ,int     ),
#     "DemensionC"  : (13     ,"gps距离左舷"    ,int     ),
#     "DemensionD"  : (14     ,"gps距离右舷"    ,int     ),
#     "localtime"   : (15     ,"接收时间"       ,int     ),
# }


g_sn =0
# 拼装完整的JSON信息
def get_general_json_to_bytes(item_type, item_data, item_timestamp):
    global g_sn
    g_sn = g_sn + 1
    if g_sn > 9999:
        g_sn = 1
    _obj = {}
    if item_timestamp is None:
        _obj['time'] = tools.timeManager.get_timestamp_ms()
    else:
        _obj['time'] = item_timestamp
    _obj['cbid'] = "cfg_db.LOCAL_SBID"
    _obj['sn'] = str(g_sn)
    _obj['item'] = []
    _obj2 = {}
    _obj2['type'] = item_type
    _obj2['data'] = item_data
    _obj['item'].append(_obj2)

    dictionary_str = json.dumps(_obj)
    # 字符串转换为字节数组
    byte_array = bytes(dictionary_str, 'utf-8')
    return byte_array
def output_json(item_flag, item_type, item_data, item_timestamp):
    byte_array = get_general_json_to_bytes(item_type, item_data, item_timestamp)

class shipInfo():
    def __init__(self):
        self.info = {}
from ..zmqlib.zmq_client import *
from ..common.topic_define import aisInfo
from ..common.deviceInfo import enum_device_type,enum_device_data_type
class CAISControl(commonBase):
    def __init__(self):
        commonBase.__init__(self)               #基本类,包含数据锁
        self.decode = IEC()                     #IEC解析实例
        self.ownShip = shipInfo()               #本船信息
        self.vdmShip = {"ais": {}, "arpa": {}}  #它船信息
        self.pub    = ZMQClient("sub",None,None,None,zmqMember('127.0.0.1',5556))  #定义主管理类
    # 设置采集数据到字典
    def process_data(self,mark, ts_data):
        flag = False
        dataType = None
        dataInfo = None
        for _ in range(1):
            # 本船信息
            global  g_mutex_own
            with g_mutex_own:
                try:
                    if mark == "DPT":
                        self.ownShip.info['dpt_live'] = tools.timeManager.get_timestamp_ms()
                        self.ownShip.info['dpt'] = ts_data['wdr']
                        flag = True
                    elif mark == "GGA":
                        self.ownShip.info['gps1_live'] = tools.timeManager.get_timestamp_ms()
                        self.ownShip.info['gps1_lon'] = ts_data['lon']
                        self.ownShip.info['gps1_lat'] = ts_data['lat']
                        flag = True
                    elif mark == "HDT":
                        self.ownShip.info['compass_live'] = tools.timeManager.get_timestamp_ms()
                        self.ownShip.info['compass_hdg'] = ts_data['angle']
                        flag = True
                    elif mark == "MWV":
                        speed = ts_data['speed']
                        if ts_data['units'] == 'K':  # km/h to m/s
                            speed = round(ts_data['speed'] * (1000 / 3600), 1)
                        if ts_data['units'] == 'N':  # knots to m/s
                            speed = round(ts_data['speed'] * 0.514444, 1)
                        if ts_data['stat'] == 'T':
                            self.ownShip.info['wind_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['wind_din_t'] = ts_data['angle']
                            self.ownShip.info['wind_spd_t'] = speed
                        else:
                            self.ownShip.info['wind_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['wind_din_r'] = ts_data['angle']
                            self.ownShip.info['wind_spd_r'] = speed
                        flag = True
                    elif mark == "RMC":
                        if ts_data['stat'] == 'A':
                            self.ownShip.info['gps1_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['gps1_lon'] = ts_data['lon']
                            self.ownShip.info['gps1_lat'] = ts_data['lat']
                            self.ownShip.info['gps1_sog'] = ts_data['speed']
                            self.ownShip.info['gps1_cog'] = ts_data['course']
                        flag = True
                    elif mark == "ROT":
                        self.ownShip.info['compass_live'] = tools.timeManager.get_timestamp_ms()
                        self.ownShip.info['compass_rot'] = ts_data['rot']
                        flag = True
                    elif mark == "VBW":
                        if ts_data['sws'] == 'A':
                            self.ownShip.info['shiplog_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['shiplog_spd_l'] = ts_data['lws']
                            self.ownShip.info['shiplog_spd_t'] = ts_data['tws']
                        flag = True
                    elif mark == "VLW":
                        flag = True
                        pass
                    elif mark == "ZDA":
                        flag = True
                        pass
                    elif mark == "AIO_1" or mark == "AIO_2" or mark == "AIO_3":
                        self.ownShip.info['ais_live'] = tools.timeManager.get_timestamp_ms()
                        self.ownShip.info['ais_lon'] = ts_data['info']['lon']
                        self.ownShip.info['ais_lat'] = ts_data['info']['lat']
                        self.ownShip.info['ais_sog'] = ts_data['info']['sog']
                        self.ownShip.info['ais_cog'] = ts_data['info']['cog']
                        self.ownShip.info['ais_hdg'] = ts_data['info']['heading']
                        self.ownShip.info['ais_rot'] = ts_data['info']['rot']

                        # if cfg_db.LOCAL_MMSI < 1:
                        #     cfg_db.write_local_mmsi(ts_data['mmsi'])
                        flag = True

                    elif mark == "HPA":
                        if ts_data['mode_stat'] == 'A':
                            self.ownShip.info['mode_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['mode'] = ts_data['mode']
                        if ts_data['spd_l_stat'] == 'A':
                            if ts_data['spd_units'] == 'P':   # 百分比
                                self.ownShip.info['engine_spd_l'] = int(ts_data['spd_l'] * 0.01 * g_engine_full_spd)
                            else:
                                self.ownShip.info['engine_spd_l'] = ts_data['spd_l']
                            self.ownShip.info['engine_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['spd_m_stat'] == 'A':
                            if ts_data['spd_units'] == 'P':  # 百分比
                                self.ownShip.info['engine_spd_m'] = int(ts_data['spd_m'] * 0.01 * g_engine_full_spd)
                            else:
                                self.ownShip.info['engine_spd_m'] = ts_data['spd_m']
                            self.ownShip.info['engine_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['spd_r_stat'] == 'A':
                            if ts_data['spd_units'] == 'P':  # 百分比
                                self.ownShip.info['engine_spd_r'] = int(ts_data['spd_r'] * 0.01 * g_engine_full_spd)
                            else:
                                self.ownShip.info['engine_spd_r'] = ts_data['spd_r']
                            self.ownShip.info['engine_live'] = tools.timeManager.get_timestamp_ms()

                        if ts_data['power_l_stat'] == 'A':
                            if ts_data['power_units'] == 'P':  # 百分比
                                self.ownShip.info['engine_power_l'] = int(ts_data['power_l'] * 0.01 * g_engine_full_power)
                            else:
                                self.ownShip.info['engine_power_l'] = ts_data['power_l']
                            self.ownShip.info['engine_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['power_m_stat'] == 'A':
                            if ts_data['power_units'] == 'P':  # 百分比
                                self.ownShip.info['engine_power_m'] = int(ts_data['power_m'] * 0.01 * g_engine_full_power)
                            else:
                                self.ownShip.info['engine_power_m'] = ts_data['power_m']
                            self.ownShip.info['engine_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['power_r_stat'] == 'A':
                            if ts_data['power_units'] == 'P':  # 百分比
                                self.ownShip.info['engine_power_r'] = int(ts_data['power_r'] * 0.01 * g_engine_full_power)
                            else:
                                self.ownShip.info['engine_power_r'] = ts_data['power_r']
                            self.ownShip.info['engine_live'] = tools.timeManager.get_timestamp_ms()

                    elif mark == "HPB":
                        if ts_data['mode_stat'] == 'A':
                            self.ownShip.info['mode_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['mode'] = ts_data['mode']
                        if ts_data['rudder_l_stat'] == 'A':
                            if ts_data['rudder_units'] == 'P':   # 百分比
                                self.ownShip.info['rudder_ane_l'] = int(ts_data['rudder_l'] * 0.01 * g_rudder_full)
                            else:
                                self.ownShip.info['rudder_ane_l'] = ts_data['rudder_l']
                            self.ownShip.info['rudder_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['rudder_m_stat'] == 'A':
                            if ts_data['rudder_units'] == 'P':  # 百分比
                                self.ownShip.info['rudder_ane_m'] = int(ts_data['rudder_m'] * 0.01 * g_rudder_full)
                            else:
                                self.ownShip.info['rudder_ane_m'] = ts_data['rudder_m']
                            self.ownShip.info['rudder_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['rudder_r_stat'] == 'A':
                            if ts_data['rudder_units'] == 'P':  # 百分比
                                self.ownShip.info['rudder_ane_r'] = int(ts_data['rudder_r'] * 0.01 * g_rudder_full)
                            else:
                                self.ownShip.info['rudder_ane_r'] = ts_data['rudder_r']
                            self.ownShip.info['rudder_live'] = tools.timeManager.get_timestamp_ms()

                    elif mark == "HPC":
                        if ts_data['mode_stat'] == 'A':
                            self.ownShip.info['mode_live'] = tools.timeManager.get_timestamp_ms()
                            self.ownShip.info['mode'] = ts_data['mode']
                        if ts_data['spd_b_stat'] == 'A':
                            if ts_data['spd_units'] == 'P':   # 百分比
                                self.ownShip.info['thruster_spd_b'] = int(ts_data['spd_b'] * 0.01 * g_thruster_full_spd)
                            else:
                                self.ownShip.info['thruster_spd_b'] = ts_data['spd_b']
                            self.ownShip.info['thruster_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['spd_m_stat'] == 'A':
                            if ts_data['spd_units'] == 'P':  # 百分比
                                self.ownShip.info['thruster_spd_m'] = int(ts_data['spd_m'] * 0.01 * g_thruster_full_spd)
                            else:
                                self.ownShip.info['thruster_spd_m'] = ts_data['spd_m']
                            self.ownShip.info['thruster_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['spd_s_stat'] == 'A':
                            if ts_data['spd_units'] == 'P':  # 百分比
                                self.ownShip.info['thruster_spd_s'] = int(ts_data['spd_s'] * 0.01 * g_thruster_full_spd)
                            else:
                                self.ownShip.info['thruster_spd_s'] = ts_data['spd_s']
                            self.ownShip.info['thruster_live'] = tools.timeManager.get_timestamp_ms()

                        if ts_data['power_b_stat'] == 'A':
                            if ts_data['power_units'] == 'P':  # 百分比
                                self.ownShip.info['thruster_power_b'] = int(ts_data['power_b'] * 0.01 * g_thruster_full_power)
                            else:
                                self.ownShip.info['thruster_power_b'] = ts_data['power_b']
                            self.ownShip.info['thruster_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['power_m_stat'] == 'A':
                            if ts_data['power_units'] == 'P':  # 百分比
                                self.ownShip.info['thruster_power_m'] = int(ts_data['power_m'] * 0.01 * g_thruster_full_power)
                            else:
                                self.ownShip.info['thruster_power_m'] = ts_data['power_m']
                            self.ownShip.info['thruster_live'] = tools.timeManager.get_timestamp_ms()
                        if ts_data['power_s_stat'] == 'A':
                            if ts_data['power_units'] == 'P':  # 百分比
                                self.ownShip.info['thruster_power_s'] = int(ts_data['power_s'] * 0.01 * g_thruster_full_power)
                            else:
                                self.ownShip.info['thruster_power_s'] = ts_data['power_s']
                            self.ownShip.info['thruster_live'] = tools.timeManager.get_timestamp_ms()
                except Exception as e:
                    pass
                if flag is True:
                    dataType = enum_device_data_type.vdo.value
                    dataInfo = aisInfo(topic_define.senson_ais.value[1] ,self.ownShip.info)
                    dataInfo.sign_type= 'VDO'
                    dataInfo.localtime = tools.timeManager.get_timestamp_ms()

            if flag:    break

            target_id = ''
            is_dynamic = False
            # 他船AIS
            global g_mutex_target
            with g_mutex_target:
                try:
                    if mark == "AIM_1" or mark == "AIM_2":  # A类
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 1
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                            self.vdmShip['ais'][target_id]['name'] = ''
                        self.vdmShip['ais'][target_id]['live'] = g_ais_a_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                        self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['sog'] = ts_data['info']['sog']
                        self.vdmShip['ais'][target_id]['cog'] = ts_data['info']['cog']
                        self.vdmShip['ais'][target_id]['hdg'] = ts_data['info']['heading']
                        flag = True
                        is_dynamic = True
                    elif mark == "AIM_3":  # A类
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 1
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                            self.vdmShip['ais'][target_id]['name'] = ''
                        self.vdmShip['ais'][target_id]['live'] = g_ais_a_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                        self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['sog'] = ts_data['info']['sog']
                        self.vdmShip['ais'][target_id]['cog'] = ts_data['info']['cog']
                        self.vdmShip['ais'][target_id]['hdg'] = ts_data['info']['heading']

                        flag = True
                        is_dynamic = True
                    elif mark == "AIM_4":  # 基站
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 3
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                            self.vdmShip['ais'][target_id]['name'] = ''
                            self.vdmShip['ais'][target_id]['sog'] = 0
                            self.vdmShip['ais'][target_id]['cog'] = 0
                            self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                            self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['live'] = g_ais_b_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        flag = True
                        is_dynamic = True
                    elif mark == "AIM_5":  # A类
                        target_id = str(ts_data['mmsi'])
                        if target_id in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id]['live'] = g_ais_b_live_max
                            self.vdmShip['ais'][target_id]['read'] = False
                            self.vdmShip['ais'][target_id]['name'] = ts_data['info']['name']
                            l = ts_data['info']['reference']['a'] + ts_data['info']['reference']['b']
                            w = ts_data['info']['reference']['c'] + ts_data['info']['reference']['d']
                            if l > w:
                                self.vdmShip['ais'][target_id]['r'] = float(f"{l / 2:.1f}")
                            else:
                                self.vdmShip['ais'][target_id]['r'] = float(f"{w / 2:.1f}")
                            #add by lhl 20250122
                            self.vdmShip['ais'][target_id]['DemensionA']    = ts_data['info']['reference']['a']
                            self.vdmShip['ais'][target_id]['DemensionB']    = ts_data['info']['reference']['b']
                            self.vdmShip['ais'][target_id]['DemensionC']    = ts_data['info']['reference']['c']
                            self.vdmShip['ais'][target_id]['DemensionD']    = ts_data['info']['reference']['d']
                            self.vdmShip['ais'][target_id]['length']        = l
                            self.vdmShip['ais'][target_id]['width']         = w
                            #####
                        flag = True
                    elif mark == "AIM_18":  # B类
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 2
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                            self.vdmShip['ais'][target_id]['name'] = ''
                        self.vdmShip['ais'][target_id]['live'] = g_ais_b_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                        self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['sog'] = ts_data['info']['sog']
                        self.vdmShip['ais'][target_id]['cog'] = ts_data['info']['cog']
                        self.vdmShip['ais'][target_id]['hdg'] = ts_data['info']['heading']
                        flag = True
                        is_dynamic = True
                    elif mark == "AIM_19":  # B类
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 2
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                        self.vdmShip['ais'][target_id]['live'] = g_ais_b_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                        self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['sog'] = ts_data['info']['sog']
                        self.vdmShip['ais'][target_id]['cog'] = ts_data['info']['cog']
                        self.vdmShip['ais'][target_id]['hdg'] = ts_data['info']['heading']
                        self.vdmShip['ais'][target_id]['name'] = ts_data['info']['name']
                        l = ts_data['info']['reference']['a'] + ts_data['info']['reference']['b']
                        w = ts_data['info']['reference']['c'] + ts_data['info']['reference']['d']
                        if l > w:
                            self.vdmShip['ais'][target_id]['r'] = float(f"{l / 2:.1f}")
                        else:
                            self.vdmShip['ais'][target_id]['r'] = float(f"{w / 2:.1f}")
                        #add by lhl 20250122
                        self.vdmShip['ais'][target_id]['DemensionA']    = ts_data['info']['reference']['a']
                        self.vdmShip['ais'][target_id]['DemensionB']    = ts_data['info']['reference']['b']
                        self.vdmShip['ais'][target_id]['DemensionC']    = ts_data['info']['reference']['c']
                        self.vdmShip['ais'][target_id]['DemensionD']    = ts_data['info']['reference']['d']
                        self.vdmShip['ais'][target_id]['length']        = l
                        self.vdmShip['ais'][target_id]['width']         = w
                        #####
                        flag = True
                        is_dynamic = True
                    elif mark == "AIM_21":  # 助航设备
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 4
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                            self.vdmShip['ais'][target_id]['sog'] = 0
                            self.vdmShip['ais'][target_id]['cog'] = 0
                            self.vdmShip['ais'][target_id]['hdg'] = 0
                        self.vdmShip['ais'][target_id]['live'] = g_ais_b_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                        self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['name'] = ts_data['info']['name']
                        l = ts_data['info']['reference']['a'] + ts_data['info']['reference']['b']
                        w = ts_data['info']['reference']['c'] + ts_data['info']['reference']['d']
                        if l > w:
                            self.vdmShip['ais'][target_id]['r'] = float(f"{l / 2:.1f}")
                        else:
                            self.vdmShip['ais'][target_id]['r'] = float(f"{w / 2:.1f}")
                        #add by lhl 20250122
                        self.vdmShip['ais'][target_id]['DemensionA']    = ts_data['info']['reference']['a']
                        self.vdmShip['ais'][target_id]['DemensionB']    = ts_data['info']['reference']['b']
                        self.vdmShip['ais'][target_id]['DemensionC']    = ts_data['info']['reference']['c']
                        self.vdmShip['ais'][target_id]['DemensionD']    = ts_data['info']['reference']['d']
                        self.vdmShip['ais'][target_id]['length']        = l
                        self.vdmShip['ais'][target_id]['width']         = w
                        #####
                        flag = True
                        is_dynamic = True
                    elif mark == "AIM_24":  # 静态信息(A/B部分)
                        target_id = str(ts_data['mmsi'])
                        if target_id in self.vdmShip['ais']:
                            if ts_data['info']['part_number'] == 0:  # A
                                self.vdmShip['ais'][target_id]['name'] = ts_data['info']['name']
                            else:
                                l = ts_data['info']['reference']['a'] + ts_data['info']['reference']['b']
                                w = ts_data['info']['reference']['c'] + ts_data['info']['reference']['d']
                                if l > w:
                                    self.vdmShip['ais'][target_id]['r'] = float(f"{l / 2:.1f}")
                                else:
                                    self.vdmShip['ais'][target_id]['r'] = float(f"{w / 2:.1f}")

                                #add by lhl 20250122
                                self.vdmShip['ais'][target_id]['DemensionA']    = ts_data['info']['reference']['a']
                                self.vdmShip['ais'][target_id]['DemensionB']    = ts_data['info']['reference']['b']
                                self.vdmShip['ais'][target_id]['DemensionC']    = ts_data['info']['reference']['c']
                                self.vdmShip['ais'][target_id]['DemensionD']    = ts_data['info']['reference']['d']
                                self.vdmShip['ais'][target_id]['length']        = l
                                self.vdmShip['ais'][target_id]['width']         = w
                                #####
                        flag = True
                    elif mark == "AIM_27":  # 基站覆盖以外的A类和B类（远距离）
                        target_id = str(ts_data['mmsi'])
                        if target_id not in self.vdmShip['ais']:
                            self.vdmShip['ais'][target_id] = {}
                            self.vdmShip['ais'][target_id]['type'] = 2
                            self.vdmShip['ais'][target_id]['id'] = ts_data['mmsi']
                            self.vdmShip['ais'][target_id]['r'] = 0
                            self.vdmShip['ais'][target_id]['name'] = ''
                        self.vdmShip['ais'][target_id]['live'] = g_ais_b_live_max
                        self.vdmShip['ais'][target_id]['read'] = False
                        self.vdmShip['ais'][target_id]['lon'] = ts_data['info']['lon']
                        self.vdmShip['ais'][target_id]['lat'] = ts_data['info']['lat']
                        self.vdmShip['ais'][target_id]['sog'] = ts_data['info']['sog']
                        self.vdmShip['ais'][target_id]['cog'] = ts_data['info']['cog']
                        self.vdmShip['ais'][target_id]['hdg'] = ts_data['info']['cog']
                        flag = True
                        is_dynamic = True
                    if is_dynamic:  # 是动态信息
                        item_without = {key: value for key, value in self.vdmShip['ais'][target_id].items() if
                                        key != 'live' and key != 'read'}
                        '''
                        {"time": 1726211088, "cbid": "TEST0001", "sn": "1244", "item": 
                        [{"type": 1003, "data": 
                        {"type": 1, "id": 412207680, "r": 17.5, "name": "LIAN GANG 44", "lon": 121.964472, "lat": 38.860148, 
                        "sog": 8.7, "cog": 131.8}
                        }]
                        }
                        '''
                        # 发送JSON数据
                        output_json("VDM", 1003, item_without, None)
                    if not tools.is_empty(target_id) and target_id in self.vdmShip['ais']:
                        self.vdmShip['ais'][target_id]['localtime'] = tools.timeManager.get_timestamp_ms()
                        dataType = enum_device_data_type.vdm.value
                        dataInfo = aisInfo(topic_define.senson_ais.value[1],self.vdmShip['ais'][target_id])
                        dataInfo.sign_type= 'VDM'
                        dataInfo.localtime = tools.timeManager.get_timestamp_ms()
                except Exception as e:
                    pass
                
            if flag: break
       
            try:
                if mark == "TTM":
                    ts = get_ttm_to_true(ts_data)
                    if ts is not None:
                        target_id = str(ts_data['number'] + 900000000)
                        if target_id not in self.vdmShip['arpa']:
                            self.vdmShip['arpa'][target_id] = {}
                            self.vdmShip['arpa'][target_id]['type'] = 5
                            self.vdmShip['arpa'][target_id]['id'] = int(target_id)
                            self.vdmShip['arpa'][target_id]['r'] = 0
                        self.vdmShip['arpa'][target_id]['live'] = g_arpa_live_max
                        self.vdmShip['arpa'][target_id]['read'] = False
                        self.vdmShip['arpa'][target_id]['lon'] = ts.lon
                        self.vdmShip['arpa'][target_id]['lat'] = ts.lat
                        self.vdmShip['arpa'][target_id]['sog'] = ts.speed
                        self.vdmShip['arpa'][target_id]['cog'] = ts.course
                        self.vdmShip['arpa'][target_id]['status'] = ts_data['status']
                        self.vdmShip['arpa'][target_id]['name'] = ts_data['name']
                        flag = True

                        item_without = {key: value for key, value in self.vdmShip['arpa'][target_id].items() if
                                        key != 'live' and key != 'read'}

                        '''
                        b'{"time": 1726542661, "cbid": "TEST0001", "sn": "1", "item": 
                        [{"type": 1003, "data": 
                        {"type": 5, "id": 900000004, "r": 0, "lon": 121.668007, "lat": 39.010756,
                         "sog": 0.0, "cog": 180.0, "status": "Q", "name": "TGT 04"}
                         }]
                         }'
                        '''
                        '''
                        b'{"time": 1726542840, "cbid": "TEST0001", "sn": "2", "item": 
                         [{"type": 1003, "data": 
                         {"type": 5, "id": 900000001, "r": 0, "lon": 121.66929, "lat": 39.016154, 
                         "sog": 0.31, "cog": 251.0, "status": "T", "name": "TGT 01"}
                         }]
                         }'
                        '''
                        # 发送JSON数据
                        output_json("TTM", 1003, item_without, None)
                    pass
            except Exception as e:
                pass
            break
        return dataType,dataInfo

    def get_own_ship(self):
        global g_own_dict, g_mutex_own
        ts = ComputeShip()
        check_live = get_timestamp_ms_add(-30)
        flag = False
        g_mutex_own.acquire()

        try:
            if g_own_dict['gps1_live'] > check_live:
                if -180 <= g_own_dict['gps1_lon'] <= 180 and -90 <= g_own_dict['gps1_lat'] <= 90:
                    ts.lon = g_own_dict['gps1_lon']
                    ts.lat = g_own_dict['gps1_lat']
                    ts.speed = g_own_dict['gps1_sog']
                    ts.course = g_own_dict['gps1_cog']
                    flag = True
            elif g_own_dict['ais_live'] > check_live:
                if -180 <= g_own_dict['ais_lon'] <= 180 and -90 <= g_own_dict['ais_lat'] <= 90:
                    ts.lon = g_own_dict['ais_lon']
                    ts.lat = g_own_dict['ais_lat']
                    ts.speed = g_own_dict['ais_sog']
                    ts.course = g_own_dict['ais_cog']
                    flag = True
            if flag:
                flag = False
                if g_own_dict['compass_live'] > check_live:
                    if 0 <= g_own_dict['compass_hdg'] <= 360:
                        ts.heading = g_own_dict['compass_hdg']
                        flag = True
                elif g_own_dict['ais_live'] > check_live:
                    if 0 <= g_own_dict['ais_hdg'] <= 360:
                        ts.heading = g_own_dict['ais_hdg']
                        flag = True
                if not flag:
                    ts.heading = ts.course
                    flag = True
        except Exception as e:
            pass
        g_mutex_own.release()
        return flag, ts


    # 过滤数据类型
    def check_data_flag(int_type, str_flag):
        if int_type == 1:  # ALL 所有
            pass
        elif int_type == 2:  # Navigation 导航
            if (str_flag != "GGA" and str_flag != "RMC" and str_flag != "ZDA" and str_flag != "HDT" and str_flag != "ROT" and
                    str_flag != "DPT" and str_flag != "MWV" and str_flag != "VBW" and str_flag != "VLW" and
                    str_flag != "HPA" and str_flag != "HPB" and str_flag != "HPC"):
                return False
        elif int_type == 3:  # GPS
            if str_flag != "GGA" and str_flag != "RMC" and str_flag != "ZDA":
                return False
        elif int_type == 4:  # AIS
            if str_flag != "VDM" and str_flag != "VDO":
                return False
        elif int_type == 5:  # ARPA
            if str_flag != "TTM":
                return False
        elif int_type == 6:  # AIS+ARPA
            if str_flag != "VDM" and str_flag != "VDO" and str_flag != "TTM":
                return False
        elif int_type == 7:  # Propeller 推进器/舵角（螺旋桨）
            if str_flag != "HPA" and str_flag != "HPB" and str_flag != "HPC":
                return False
        return True

    # 取得TTM的坐标数据
    def get_ttm_to_true(self,ttm_dict):
        flag, own_ship = self.get_own_ship()
        if not flag:
            return None
        obj_ship = ComputeShip()
        bearing = compute_ttm_bearing(ttm_dict['bearing'], ttm_dict['bearing_tr'], own_ship.heading)
        distance = compute_ttm_distance(ttm_dict['distance_own'], ttm_dict['units'])
        obj_ship.lat, obj_ship.lon = compute_ttm_position(own_ship.lat, own_ship.lon, distance, bearing)
        obj_ship.speed = compute_ttm_speed(ttm_dict['speed'], ttm_dict['units'])
        obj_ship.course = ttm_dict['course']
        if ttm_dict['course_tr'] == 'R':
            obj_ship.speed, obj_ship.course = cal_abs_course_and_speed(own_ship, obj_ship)
        return obj_ship
    def setData(self,data):
        if self.decode is None: return#没有生成解析

        count = self.decode.set_data(data)
        listVdm = []
        for f in range(count):
            # 取得原始语句
            # re_type, re_data = self.decode.get_data(f)
            # if re_type is None:
            #     pass
            # else:
            #     #
            #     if re_type != 'AIO' and re_type != 'AIM':
            #         # 转发原始数据
            #         output_iec(re_type, re_data)
            #         counter_1 += 1
            # 取得解析数据
            re_type, re_struct = self.decode.get_data_struct(f)
            if re_type is None:
                pass
            else:
                # 处理数据
                dataType,dataInfo = self.process_data(re_type, re_struct)
                if dataType == enum_device_data_type.vdm.value:
                    listVdm.append(dataInfo.to_dict())
        if self.pub and listVdm:
            topHead = topic_Head()
            topHead.content = listVdm
            topHead.timestamp = tools.timeManager.get_timestamp_ms()
            dictInfo = topHead.to_dict()
            strRes = jsonFunc.loadJsonNode.toJsonString(dictInfo)

            self.pub.pubInfo(topic_define.senson_ais.value[0],strRes)
            print(strRes)


class aisDataMgr(socketDataInterface):
    def __init__(self,socket,address,socket_type,param,dualTargetClass,name='aisDataMgr',bLogin=True,aisDevice=None):
        #初始化父类,创建socket实例,并开始处理线程
        super().__init__(socket,address,socket_type,param,name)
        #如果是采集端,则是采集设备信息实例包含写redis及发送socket
        #如果是服务端,则是listeninfo
        self.aisDevice                  = aisDevice                     #采集设备信息实例
        self.loginFlag                  = enum_State_code.fail.value    #默认登录状态是失败
        self.deviceId                   = ''                            #登录uuid与终端设备Id一致,如果是空表示没登录
        self.rdCode                     = ''                            #是否有rdcode如果有rdcode则使用t_data[rdcode]写数据
        self.dualTaget                  = dualTargetClass               #处理类,主要是服务端或者客户端处理
        if socket is not None:
            self.socketClient.read_callback = self.callback             #读取数据的回调函数,主要是解析协议完成后的完整数据
            self.socketClient.run(True,True)                            #运行读写线程
        self.nSaveDbTime                = 60000                         #单位毫秒,设置保存数据库的时间,默认一分钟保存一次
        self.nPreSaveDbTime             = 0                             #当前保存时间,临时变量用于存储上一次的保存时间,当前时间和他对比,如果大于保存时间则保存一次,此次时间更新此时间
        self.isCopyTable                = 1                             #是否复制表,默认复制 add by lhl 20251205
        self.isInput_his                = 0                             #是否写入历史表,默认不写入 add by lhl 20251205

        #如果是边平台采集端,需要发送登录信息
        if self.transmit_type == enum_transmit_type.collect.value:
            serverInfo  = loginInfo.copyServerInfo(self.collectDevice)
            serverDict  = serverInfo.to_dict()
            strData     = loadJsonNode.toJsonString(serverDict)
            self.send_data(True,False,strData.encode('utf-8'),Enum_Protocol_Cmd.login,None,None,'',True)#发送登录信息
        #add by lhl 20251223  控制的客户端和服务器端不需要登录
        elif self.transmit_type == enum_transmit_type.control_client.value: self.loginFlag = enum_State_code.success.value #如果需要处理在此处完善代码
        elif self.transmit_type == enum_transmit_type.control_server.value: self.loginFlag = enum_State_code.success.value #如果需要处理在此处完善代码
        ###########
    #得到复制表名称
    def getTable(self,tablename):
        if self.isCopyTable == 1 and not tools.is_empty(self.deviceId):#复制表时返回tablename_登录uuid
            return f"{tablename}_{self.deviceId}"
        return tablename
    def close(self):
        socketDataInterface.close(self)
        self.loginFlag = enum_State_code.fail.value
        #清除回复消息记录 add by lhl 20251224
        with self.dataLock:
            for k,v in self.sendList:
                v.setRes(None,None)
            self.sendList.clear()
        ######
        if self.transmit_type == enum_transmit_type.server.value:
            g_manger =getManager()
            if g_manger is not None:
                dbInterface = g_manger.configInfo.databaseInfo.dbInterface.getClass()#add by lhl 20251210 使用数据库接收不用具体连接
                if not tools.is_empty(self.deviceId):
                    dbInterface.singleQuery(g_manger.configInfo.databaseInfo.host,
                                           g_manger.configInfo.databaseInfo.port,
                                           g_manger.configInfo.databaseInfo.user,
                                           g_manger.configInfo.databaseInfo.password,
                                           g_manger.configInfo.databaseInfo.dbname,
                        f"update t_terminal_list set online_flag = 0 where uuid = '{self.deviceId}'",True,False)
                    g_manger.writeRedisNode(redisMgr.redis_write_info(f"{self.deviceId}",{
                                    "login_status": self.loginFlag,
                                    "login_status_tm": tools.timeManager.get_timestamp_ms(),
                                    'login_describ': '断开连接'
                                    }))
            self.deviceId=''
        return

    #接收数据后使用回调,解析具体的数据
    def callback(self, data):
        self.add_dual_data(None,data)

    def dual_data(self,protocolHead,byteContent):
        #解析ais信息
        self.aisDevice.setData(byteContent)
        return
    

class aisSocket(socketInterface):
    def __init__(self,name='',nId =0,ipAddress='127.0.0.1',port=8080,tcpType=0,parameters=None,dualTargetClsss=None,bLogin=True,collectDevice=None):
       #调用父类的构造函数
       super().__init__(tools.checkName(name,nId,'aisSocket'),ipAddress,port,tcpType,parameters)  # 如果父类构造函数需要参数，需在这里传递
       self.bLogin          = bLogin
       self.collectDevice   = collectDevice
       self.dualTaget       = dualTargetClsss
    #析构函数
    def __del__(self):
        pass
    def callFunc(self,socket,address)->aisDataMgr:
        try:
            if self.collectDevice is not None:
                return aisDataMgr(socket,address,self.socket_type,self.parameters,self.dualTaget,self.name,self.bLogin,self.collectDevice)
            return None
        except Exception as e:
            output(f"[异常]:[aisSocket.callFunc]:{e}",outputMode.saveLog,enum_Error.localErr)
    def send_data(self,bEncode,bNeedCall,data,cmdCode:Enum_Protocol_Cmd=None,serialNum:int=None,proMgr:protocolMgr =None,uuid='',deviceId=''):
        resList = []
        if not self.m_tcp_mgr:
            output(f"[aisSocket.send_data]:没有实例,不能发送数据",outputMode.saveLog,enum_Error.localErr)
            return resList
        if self.m_tcp_mgr.socket_type == socket_type.tcp_client.value:
            if self.m_tcp_mgr.socketClient is None:
                output(f"[protocolSocket.send_data]:没有连接,不能发送数据",outputMode.saveLog,enum_Error.localErr)
                return resList
            callRes = self.m_tcp_mgr.socketClient.send_data(bEncode,bNeedCall,data,cmdCode,serialNum,proMgr,uuid)
            if callRes:resList.append(callRes)
            return resList
        #发送给服务器所有连接的客户端
        if self.m_tcp_mgr.socket_type == socket_type.tcp_server.value:
            resList = []
            with self.m_tcp_mgr.listLock:
                for client in self.m_tcp_mgr.clientList:
                   if not tools.is_empty(deviceId) :
                       if client.deviceId == deviceId:
                           callRes = client.send_data(bEncode,bNeedCall,data,cmdCode,serialNum,proMgr,uuid)
                           if callRes:resList.append(callRes)
                           break
                   else:
                       callRes = client.send_data(bEncode,bNeedCall,data,cmdCode,serialNum,proMgr,uuid)
                       if callRes:resList.append(callRes)
            return resList
        #没有socket类型
        return resList

