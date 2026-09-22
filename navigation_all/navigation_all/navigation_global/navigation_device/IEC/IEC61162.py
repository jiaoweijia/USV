from . import DecodeVDM1 as DecodeVDM1
from . import DecodeVDM2 as DecodeVDM2
from    collect_global.common.logManager import output, outputMode,enum_Error
IS_WELCOME = True
#枚举定义
from enum import unique, Enum, auto
@unique#枚举类修饰符，唯一检查
class enum_dataType(Enum):
    AIM = (0,'')
    AIO = (1,'')
    DPT = (2,'')
    GGA = (3,'')
    HDT = (4,'')
    HPA = (5,'')
    HPB = (6,'')
    HPC = (7,'')
    MWV = (8,'')
    RMC = (9,'')
    ROT = (10,'')
    TTM = (11,'')
    VDO = (12,'')
    VDM = (13,'')
    VLW = (14,'')
    ZDA = (15,'')
# 取得语句数据类型
def get_data_type(data):
    re_type = None
    mark = data[3:6]
    if mark == "AIM":
        re_type = mark
    elif mark == "AIO":
        re_type = mark
    elif mark == "DPT":
        re_type = mark
    elif mark == "GGA":
        re_type = mark
    elif mark == "HDT":
        re_type = mark
    elif mark == "HPA":
        re_type = mark
    elif mark == "HPB":
        re_type = mark
    elif mark == "HPC":
        re_type = mark
    elif mark == "MWV":
        re_type = mark
    elif mark == "RMC":
        re_type = mark
    elif mark == "ROT":
        re_type = mark
    elif mark == "TTM":
        re_type = mark
    elif mark == "VBW":
        re_type = mark
    elif mark == "VDO":
        re_type = mark
    elif mark == "VDM":
        re_type = mark
    elif mark == "VLW":
        re_type = mark
    elif mark == "ZDA":
        re_type = mark
    return re_type


class IEC:
    m_surplus_buf = bytearray()   # 上次剩余数据
    m_data_list = []  # 有效的数据列表

    # VDO/VDM语句列表
    m_vdo_list = {}
    m_vdo_total = 0
    m_vdo_bits = 0
    m_vdm_list = {}
    m_vdm_total = 0
    m_vdm_bits = 0

    #
    def __init__(self):
        global IS_WELCOME
        if IS_WELCOME:
            IS_WELCOME = False
            print('****************************************\r\nWelcome to use the IEC61162 software library\r\n'
                  'Copyright hui.mail@qq.com\r\nVersion 1.0.0 2021.12\r\n****************************************')
        # license_obj.get_license_status()

    # 添加语句数据列表
    def add_data_list(self, data, data_type, bits):
        if data_type == "AIO" or data_type == "AIM":
            self.m_data_list.append({'data': data, 'type': data_type, 'bits': bits})
        else:
            self.m_data_list.append({'data': data, 'type': data_type})
        if data_type == "VDO":
            self.add_vdm_list(data, False)
        if data_type == "VDM":
            self.add_vdm_list(data, True)

    # 清除语句数据列表
    def clean_data_list(self):
        self.m_data_list = []

    # 设置数据
    def set_data(self, buf):  # 传入数据
        sign = False
        if buf is None:
            return 0
        buf_len = len(buf)
        if buf_len < 1 or buf_len > DecodeVDM1.ID_SIZE_BUF:
            return 0
        # 清除上次数据
        self.clean_data_list()
        # if not license_obj.get_license_status():
        #     # 许可过期
        #     return 0
        try:
            data_buf = bytearray()  # 数据缓存
            # 取得上次剩余数据
            if len(self.m_surplus_buf) > 0:
                if len(self.m_surplus_buf) < DecodeVDM1.ID_SIZE_SIGN_BUF:
                    # 检查上次剩余数据
                    for f in range(len(self.m_surplus_buf)):
                        # 取得开始标识符
                        if self.m_surplus_buf[f] == b'$'[0] or self.m_surplus_buf[f] == b'!'[0]:
                            data_buf = bytearray()
                            sign = True
                        if self.m_surplus_buf[f] == 0:
                            break
                        # 取得有效数据
                        if sign:
                            data_buf.append(self.m_surplus_buf[f])
                self.m_surplus_buf = bytearray()  # 清除上次剩余数据

            # 重新校验数据长度
            if len(data_buf) + buf_len >= DecodeVDM1.ID_SIZE_CHECK_BUF:
                # 丢弃上次剩余数据，只取新数据
                data_buf = bytearray()

            # 重组数据
            for f in range(buf_len):
                data_buf.append(buf[f])

            data_buf_len = len(data_buf)
            sign = False
            point = 0  # 保留最后一个语句首位置
            counter = 0  # data_buf数组下标
            check_buf = bytearray()  # 语句缓存

            while counter < data_buf_len:
                if data_buf[counter] == 0:
                    counter += 1
                    continue
                if len(check_buf) >= DecodeVDM1.ID_SIZE_SIGN_BUF - 5:  # 防止错误句语超限，-5是为了校验'*'后字符长度
                    # 等待重新获取语句
                    check_buf = bytearray()
                    sign = False
                    point = counter  # 保留位置

                if data_buf[counter] == b'$'[0] or data_buf[counter] == b'!'[0]:  # 开始标识符
                    # 重新获取语句
                    check_buf = bytearray()
                    sign = True
                    point = counter  # 保留位置

                if data_buf[counter] == b'*'[0]:  # 结束符
                    if counter + 2 >= data_buf_len:
                        # 长度不够，结束循环校验
                        break
                    check_buf.append(data_buf[counter])  # '*'
                    counter += 1
                    if DecodeVDM1.is_hex(data_buf[counter]) and DecodeVDM1.is_hex(data_buf[counter + 1]):  # 校验为十六进制字符
                        check_buf.append(data_buf[counter])  # 'h'
                        counter += 1
                        check_buf.append(data_buf[counter])  # 'h'
                        if DecodeVDM1.is_check_sum(check_buf):
                            str_check_buf = check_buf.decode()
                            data_type = get_data_type(str_check_buf)
                            if data_type is not None:
                                self.add_data_list(str_check_buf, data_type, 0)
                    else:
                        counter += 1  # 跳过1位校验码位置
                    point = counter + 1  # 保留下一位置(当前长度)
                    sign = False
                # 获得数据
                if sign:
                    check_buf.append(data_buf[counter])
                counter += 1

            if data_buf_len - point > 0:  # 有剩余数据
                self.m_surplus_buf = bytearray()
                # 保存剩余数据
                surplus_len = DecodeVDM1.ID_SIZE_SIGN_BUF - 5  # 强制最大剩余长度,保留最后的1条语句长度的数据
                if data_buf_len - point >= surplus_len:
                    # 保存剩余数据
                    for f in range(surplus_len):
                        self.m_surplus_buf.append(data_buf[data_buf_len-surplus_len+f])
                else:
                    surplus_len = (data_buf_len-point)  # 剩余长度
                    # 保存剩余数据
                    for f in range(surplus_len):
                        self.m_surplus_buf.append(data_buf[point+f])

            return len(self.m_data_list)
        except Exception as e:
            output("[IEC] DATA Exception: " + str(e.args))
            output("[IEC] DATA: " + str(buf.decode('gb2312')))
        return 0

    # 取得语句数据
    def get_data(self, index):
        if index < 0 or index > len(self.m_data_list):
            return None, None
        return self.m_data_list[index]['type'], self.m_data_list[index]['data']

    # 取得结构数据
    def get_data_struct(self, index):
        if index < 0 or index > len(self.m_data_list):
            return None, None
        data_type = get_data_type(self.m_data_list[index]['data'])

        try:
            if data_type == "AIM":  # VDM完整信息
                return self.get_struct_VDM(self.m_data_list[index]['data'], self.m_data_list[index]['bits'], True)
            elif data_type == "AIO":  # VDO完整信息
                return self.get_struct_VDM(self.m_data_list[index]['data'], self.m_data_list[index]['bits'], False)
            elif data_type == "DPT":
                return data_type, self.get_struct_DPT(self.m_data_list[index]['data'])
            elif data_type == "GGA":
                return data_type, self.get_struct_GGA(self.m_data_list[index]['data'])
            elif data_type == "HDT":
                return data_type, self.get_struct_HDT(self.m_data_list[index]['data'])
            elif data_type == "HPA":
                return data_type, self.get_struct_HPA(self.m_data_list[index]['data'])
            elif data_type == "HPB":
                return data_type, self.get_struct_HPB(self.m_data_list[index]['data'])
            elif data_type == "HPC":
                return data_type, self.get_struct_HPC(self.m_data_list[index]['data'])
            elif data_type == "MWV":
                return data_type, self.get_struct_MWV(self.m_data_list[index]['data'])
            elif data_type == "RMC":
                return data_type, self.get_struct_RMC(self.m_data_list[index]['data'])
            elif data_type == "ROT":
                return data_type, self.get_struct_ROT(self.m_data_list[index]['data'])
            elif data_type == "TTM":
                return data_type, self.get_struct_TTM(self.m_data_list[index]['data'])
            elif data_type == "VBW":
                return data_type, self.get_struct_VBW(self.m_data_list[index]['data'])
            elif data_type == "VDO":
                return None, None
            elif data_type == "VDM":
                return None, None
            elif data_type == "VLW":
                return data_type, self.get_struct_VLW(self.m_data_list[index]['data'])
            elif data_type == "ZDA":
                return data_type, self.get_struct_ZDA(self.m_data_list[index]['data'])

        except Exception as e:
            output("[IEC] Get struct: " + str(e.args))
        return None, None

    def get_struct_DPT(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--DPT, x.x, x.x, x.x*hh<CR><LF>
            # $SDDPT,,5.2,10*53  $SDDPT,0010.6,0005.4*51
            # 初始化数据
            dpt_wdr = 0.0  # 水深 单位为米
            dpt_oft = 0.0  # 偏移量
            dpt_mrs = 0.0  # 最大比例尺

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                dpt_wdr = round(float(sInfo), 1)  #

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                dpt_oft = round(float(sInfo), 1)  #

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                dpt_mrs = round(float(sInfo), 1)  #

            # 构造返回结构
            result_dict = {}
            result_dict['wdr'] = dpt_wdr
            result_dict['oft'] = dpt_oft
            result_dict['mrs'] = dpt_mrs
            return result_dict
        except Exception as e:
            output("[IEC] DPT Exception: " + str(e.args))
            output("[IEC] DPT: " + data)
        return None

    def get_struct_GGA(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != 0 and data[point] != '*':
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--GGA, hhmmss.ss, llll.ll, a, yyyyy.yy, a, x, xx, x.x, x.x, M, x.x, M, x.x, xxxx*hh<CR><LF>
            # $GPGGA,044426,3852.161,N,12131.927,E,1,03,8.1,27.5,M,6.6,M,,*4E
            # $GPGGA, 045922.00, 3858.4189, N, 12142.4519, E, 1, 17, 0.7, 22.0, M,, M,, *44
            # 初始化数据
            gga_utc_hour = 0
            gga_utc_minute = 0
            gga_utc_sec = 0
            gga_lat = 0.0  # Latitude
            gga_lon = 0.0  # Longitude
            gga_indicator = 0  # GPS quality indicator
            gga_number = 0  # Number of satellites in use, 00 - 12, may be different from the number in view
            gga_dilution = 0.0  # Horizontal dilution of precision
            gga_altitude = 0.0  # Antenna altitude above / below mean sea level(geoid)
            gga_altitude_units = ''  # Units of antenna altitude, m
            gga_separation = 0.0  # Geoidal separation
            gga_separation_units = ''  # Units of geoidal separation, m
            gga_age = 0.0  # Age of differential GPS data
            gga_id = 0  # Differential reference station ID, 0000 - 1023

            # 解析数据
            point += 1
            utc_mark = 0  # 标志
            sInfo = ""
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
                utc_mark += 1
                if utc_mark == 2:
                    gga_utc_hour = int(sInfo)  # UTC时间
                    if gga_utc_hour < 0 or gga_utc_hour > 23:
                        gga_utc_hour = 24
                    sInfo = ""
                if utc_mark == 4:
                    gga_utc_minute = int(sInfo)
                    if gga_utc_minute < 0 or gga_utc_minute > 59:
                        gga_utc_minute = 60
                    sInfo = ""
            if len(sInfo) > 0:
                gga_utc_sec = float(sInfo)
                if gga_utc_sec < 0 or gga_utc_sec >= 60:
                    gga_utc_sec = 0

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_lat = float(sInfo)
                d_lat = int(gga_lat / 100)
                m_lat = (gga_lat - d_lat * 100) * 0.0166667
                gga_lat = round(d_lat + m_lat, 6)  # 纬度
            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                if data[point] == 'S':  # 纬度半球S或N
                    gga_lat = gga_lat * -1
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_lon = float(sInfo)
                d_lon = int(gga_lon / 100)
                m_lon = (gga_lon - d_lon * 100) * 0.0166667
                gga_lon = round(d_lon + m_lon, 6)  # 经度
            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                if data[point] == 'W':  # 经度半球E(东经)或W(西经)
                    gga_lon = gga_lon * -1
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_indicator = round(float(sInfo), 1)  # GPS quality indicator

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_number = int(sInfo)  # Number of satellites in use, 00-12, may be different from the number in view

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_dilution = round(float(sInfo), 1)  # Horizontal dilution of precision

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_altitude = round(float(sInfo), 1)  # Antenna altitude above/below mean sea level (geoid)

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                gga_altitude_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_separation = round(float(sInfo), 1)  # Geoidal separation

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                gga_separation_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_age = round(float(sInfo), 1)  # Age of differential GPS data

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                gga_id = int(sInfo)  # Differential reference station ID, 0000-1023

            # 构造返回结构
            result_dict = {}
            result_dict['utc_hour'          ] = gga_utc_hour
            result_dict['utc_minute'        ] = gga_utc_minute
            result_dict['utc_sec'           ] = gga_utc_sec
            result_dict['lat'               ] = gga_lat
            result_dict['lon'               ] = gga_lon
            result_dict['indicator'         ] = gga_indicator
            result_dict['number'            ] = gga_number
            result_dict['dilution'          ] = gga_dilution
            result_dict['altitude'          ] = gga_altitude
            result_dict['altitude_units'    ] = gga_altitude_units
            result_dict['separation'        ] = gga_separation
            result_dict['separation_units'  ] = gga_separation_units
            result_dict['age'               ] = gga_age
            result_dict['id'                ] = gga_id
            return result_dict
        except Exception as e:
            output("[IEC] GGA Exception: " + str(e.args))
            output("[IEC] GGA: " + data)
        return None

    def get_struct_HDT(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != 0 and data[point] != '*':
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--HDT, x.x, T*hh<CR><LF>
            # $HEHDT,114.2,T*29
            # 初始化数据
            hdt_angle = 0.0
            hdt_stat = ''

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hdt_angle = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hdt_stat = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['angle' ] = hdt_angle
            result_dict['stat'  ] = hdt_stat
            return result_dict
        except Exception as e:
            output("[IEC] HDT Exception: " + str(e.args))
            output("[IEC] HDT: " + data)
        return None

    def get_struct_HPA(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            #
            # $--HPA,1,A,100,A,0,V,101,A,R,455,A,0,V,407,A,K*32<CR><LF>
            # 初始化数据
            hpa_driving_mode = 0  # 驾驶模式，0:未知 1:人工 2:自主航行 3:远程
            hpa_driving_mode_stat = 'V'  # 标识
            hpa_engine_spd_l = 0  # 左侧主机转数
            hpa_engine_spd_l_stat = 'V'  # 标识
            hpa_engine_spd_m = 0  # 中间主机转数
            hpa_engine_spd_m_stat = 'V'  # 标识
            hpa_engine_spd_r = 0  # 右侧主机转数
            hpa_engine_spd_r_stat = 'V'  # 标识
            hpa_engine_spd_units = ''  # 主机转数单位 R:rmp P:百分数%
            hpa_engine_power_l = 0  # 左侧主机功率
            hpa_engine_power_l_stat = 'V'  # 标识
            hpa_engine_power_m = 0  # 中间主机功率
            hpa_engine_power_m_stat = 'V'  # 标识
            hpa_engine_power_r = 0  # 右侧主机功率
            hpa_engine_power_r_stat = 'V'  # 标识
            hpa_engine_power_units = ''  # 主机功率单位 K:kW P:百分数%

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_driving_mode = int(sInfo)

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_driving_mode_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_engine_spd_l = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_spd_l_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_engine_spd_m = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_spd_m_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_engine_spd_r = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_spd_r_stat = data[point]
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_spd_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_engine_power_l = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_power_l_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_engine_power_m = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_power_m_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpa_engine_power_r = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_power_r_stat = data[point]
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpa_engine_power_units = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['mode'          ] = hpa_driving_mode
            result_dict['mode_stat'     ] = hpa_driving_mode_stat
            result_dict['spd_l'         ] = hpa_engine_spd_l
            result_dict['spd_l_stat'    ] = hpa_engine_spd_l_stat
            result_dict['spd_m'         ] = hpa_engine_spd_m
            result_dict['spd_m_stat'    ] = hpa_engine_spd_m_stat
            result_dict['spd_r'         ] = hpa_engine_spd_r
            result_dict['spd_r_stat'    ] = hpa_engine_spd_r_stat
            result_dict['spd_units'     ] = hpa_engine_spd_units
            result_dict['power_l'       ] = hpa_engine_power_l
            result_dict['power_l_stat'  ] = hpa_engine_power_l_stat
            result_dict['power_m'       ] = hpa_engine_power_m
            result_dict['power_m_stat'  ] = hpa_engine_power_m_stat
            result_dict['power_r'       ] = hpa_engine_power_r
            result_dict['power_r_stat'  ] = hpa_engine_power_r_stat
            result_dict['power_units'   ] = hpa_engine_power_units

            return result_dict
        except Exception as e:
            output("[IEC] HPA Exception: " + str(e.args))
            output("[IEC] HPA: " + data)
        return None

    def get_struct_HPB(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            #
            # $--HPB,1,A,10.5,A,0,V,10.3,A,D*26<CR><LF>
            # 初始化数据
            hpb_driving_mode = 0  # 驾驶模式，0:未知 1:人工 2:自主航行 3:远程
            hpb_driving_mode_stat = 'V'  # 标识
            hpb_rudder_l = 0  # 左侧舵角
            hpb_rudder_l_stat = 'V'  # 标识
            hpb_rudder_m = 0  # 中间舵角
            hpb_rudder_m_stat = 'V'  # 标识
            hpb_rudder_r = 0  # 右侧舵角
            hpb_rudder_r_stat = 'V'  # 标识
            hpb_rudder_units = ''  # 舵角单位  D:角度 P:百分数%

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpb_driving_mode = int(sInfo)

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpb_driving_mode_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpb_rudder_l = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpb_rudder_l_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpb_rudder_m = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpb_rudder_m_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpb_rudder_r = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpb_rudder_r_stat = data[point]
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpb_rudder_units = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['mode'          ] = hpb_driving_mode
            result_dict['mode_stat'     ] = hpb_driving_mode_stat
            result_dict['rudder_l'      ] = hpb_rudder_l
            result_dict['rudder_l_stat' ] = hpb_rudder_l_stat
            result_dict['rudder_m'      ] = hpb_rudder_m
            result_dict['rudder_m_stat' ] = hpb_rudder_m_stat
            result_dict['rudder_r'      ] = hpb_rudder_r
            result_dict['rudder_r_stat' ] = hpb_rudder_r_stat
            result_dict['rudder_units'  ] = hpb_rudder_units
            return result_dict
        except Exception as e:
            output("[IEC] HPB Exception: " + str(e.args))
            output("[IEC] HPB: " + data)
        return None

    def get_struct_HPC(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            #
            # $--HPC,1,A,0,A,0,V,0,A,P,0,A,0,V,0,A,K*34<CR><LF>
            # 初始化数据
            hpc_driving_mode = 0  # 驾驶模式，0:未知 1:人工 2:自主航行 3:远程
            hpc_driving_mode_stat = 'V'  # 标识
            hpc_spd_b = 0  # 船艏侧推转数
            hpc_spd_b_stat = 'V'  # 标识
            hpc_spd_m = 0  # 中间侧推转数
            hpc_spd_m_stat = 'V'  # 标识
            hpc_spd_s = 0  # 船艉侧推转数
            hpc_spd_s_stat = 'V'  # 标识
            hpc_spd_units = ''  # 侧推转数单位  R:rmp P:百分数%
            hpc_power_b = 0  # 船艏侧推功率
            hpc_power_b_stat = 'V'  # 标识
            hpc_power_m = 0  # 中间侧推功率
            hpc_power_m_stat = 'V'  # 标识
            hpc_power_s = 0  # 船艉侧推功率
            hpc_power_s_stat = 'V'  # 标识
            hpc_power_units = ''  # 侧推功率单位 K:kW P:百分数%

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_driving_mode = int(sInfo)

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_driving_mode_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_spd_b = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_spd_b_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_spd_m = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_spd_m_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_spd_s = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_spd_s_stat = data[point]
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_spd_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_power_b = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_power_b_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_power_m = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_power_m_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                hpc_power_s = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_power_s_stat = data[point]
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                hpc_power_units = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['mode'          ] = hpc_driving_mode
            result_dict['mode_stat'     ] = hpc_driving_mode_stat
            result_dict['spd_b'         ] = hpc_spd_b
            result_dict['spd_b_stat'    ] = hpc_spd_b_stat
            result_dict['spd_m'         ] = hpc_spd_m
            result_dict['spd_m_stat'    ] = hpc_spd_m_stat
            result_dict['spd_s'         ] = hpc_spd_s
            result_dict['spd_s_stat'    ] = hpc_spd_s_stat
            result_dict['spd_units'     ] = hpc_spd_units
            result_dict['power_b'       ] = hpc_power_b
            result_dict['power_b_stat'  ] = hpc_power_b_stat
            result_dict['power_m'       ] = hpc_power_m
            result_dict['power_m_stat'  ] = hpc_power_m_stat
            result_dict['power_s'       ] = hpc_power_s
            result_dict['power_s_stat'  ] = hpc_power_s_stat
            result_dict['power_units'   ] = hpc_power_units

            return result_dict
        except Exception as e:
            output("[IEC] HPC Exception: " + str(e.args))
            output("[IEC] HPC: " + data)
        return None

    def get_struct_MWV(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--MWV, x.x, a, x.x, a, A *hh<CR><LF>
            # $IIMWV,152.5,R,3.5,N,A*38
            # 初始化数据
            mwv_angle = 0.0  # 风向
            mwv_stat = ''  # 标识
            mwv_speed = 0.0  # 风速
            mwv_units = ''  # 单位

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                mwv_angle = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                mwv_stat = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                mwv_speed = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                mwv_units = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['angle' ] = mwv_angle
            result_dict['stat'  ] = mwv_stat
            result_dict['speed' ] = mwv_speed
            result_dict['units' ] = mwv_units
            return result_dict
        except Exception as e:
            output("[IEC] MWV Exception: " + str(e.args))
            output("[IEC] MWV: " + data)
        return None

    def get_struct_RMC(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != 0 and data[point] != '*':
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--RMC, hhmmss.ss, A, llll.ll,a, yyyyy.yy, a, x.x, x.x, xxxxxx, x.x,a, a*hh<CR><LF>
            # $GPRMC,092350.00,A,2230.240,N,11350.242,E,00.0,090.,180908,03.,W,A*2F
            # 初始化数据
            rmc_utc_hour = 0
            rmc_utc_minute = 0
            rmc_utc_sec = 0
            rmc_stat = 'V'  # 定状态，A = 有效定位，V = 无效定位
            rmc_lat = 0.0  # 纬度(度),正数为北纬，负数为南纬
            rmc_lon = 0.0  # 经度(度),正数为东经，负数为西经
            rmc_speed = 0.0  # 地面速率(000.0~999.9节)
            rmc_course = 0.0  # 地面航向(000.0~359.9度，以真北为参考基准，前面的0也将被传输)
            rmc_utc_day = 0  # Day, 01 to 31(UTC)
            rmc_utc_month = 0  # Month, 01 to 12(UTC)
            rmc_utc_year = 0  # Year(UTC)
            rmc_angle = 0.0  # 磁偏角(000.0~180.0度),正数为东，负数为西
            rmc_mode = 'A'  # 模式指示(仅NMEA01833.00版本输出，A = 自主定位，D = 差分，E = 估算，N = 数据无效)

            # 解析数据
            point += 1
            utc_mark = 0  # 标志
            sInfo = ""
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
                utc_mark += 1
                if utc_mark == 2:
                    rmc_utc_hour = int(sInfo)  # UTC时间
                    if rmc_utc_hour < 0 or rmc_utc_hour > 23:
                        rmc_utc_hour = 24
                    sInfo = ""
                if utc_mark == 4:
                    rmc_utc_minute = int(sInfo)
                    if rmc_utc_minute < 0 or rmc_utc_minute > 59:
                        rmc_utc_minute = 60
                    sInfo = ""
            if len(sInfo) > 0:
                rmc_utc_sec = float(sInfo)
                if rmc_utc_sec < 0 or rmc_utc_sec >= 60:
                    rmc_utc_sec = 0

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                rmc_stat = data[point]  # 定位状态
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                rmc_lat = float(sInfo)
                d_lat = int(rmc_lat/100)
                m_lat = (rmc_lat - d_lat*100) * 0.0166667
                rmc_lat = round(d_lat + m_lat, 6)  # 纬度
            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                if data[point] == 'S':  # 纬度半球S或N
                    rmc_lat = rmc_lat * -1
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                rmc_lon = float(sInfo)
                d_lon = int(rmc_lon / 100)
                m_lon = (rmc_lon - d_lon * 100) * 0.0166667
                rmc_lon = round(d_lon + m_lon, 6)  # 经度
            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                if data[point] == 'W':  # 经度半球E(东经)或W(西经)
                    rmc_lon = rmc_lon * -1
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                rmc_speed = round(float(sInfo), 1)  # 地面速度

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                rmc_course = round(float(sInfo), 1)  # 地面航向

            sInfo = ""
            point += 1
            utc_mark = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
                utc_mark += 1
                if utc_mark == 2:
                    rmc_utc_day = int(sInfo)  # UTC日期
                    if rmc_utc_day < 1 or rmc_utc_day > 31:
                         rmc_utc_day = 0
                    sInfo = ""
                if utc_mark == 4:
                    rmc_utc_month = int(sInfo)
                    if rmc_utc_month< 1 or rmc_utc_month > 12:
                        rmc_utc_month = 0
                    sInfo = ""
            if len(sInfo) > 0:
                rmc_utc_year = int(sInfo) + 2000

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                rmc_angle = round(float(sInfo), 1)  # 磁偏角
            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                if data[point] == 'W':  # 磁偏角方向，E(东)或W(西)
                    rmc_angle = rmc_angle * -1
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                rmc_mode = data[point]  # 模式指示(仅NMEA0183 3.00版本输出，A=自主定位，D=差分，E=估算，N=数据无效)

            # 构造返回结构
            result_dict = {}
            result_dict['utc_hour'  ] = rmc_utc_hour
            result_dict['utc_minute'] = rmc_utc_minute
            result_dict['utc_sec'   ] = rmc_utc_sec
            result_dict['stat'      ] = rmc_stat
            result_dict['lat'       ] = rmc_lat
            result_dict['lon'       ] = rmc_lon
            result_dict['speed'     ] = rmc_speed
            result_dict['course'    ] = rmc_course
            result_dict['utc_day'   ] = rmc_utc_day
            result_dict['utc_month' ] = rmc_utc_month
            result_dict['utc_year'  ] = rmc_utc_year
            result_dict['angle'     ] = rmc_angle
            result_dict['mode'      ] = rmc_mode
            return result_dict
        except Exception as e:
            output("[IEC] RMC Exception: " + str(e.args))
            output("[IEC] RMC: " + data)
        return None

    def get_struct_ROT(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != 0 and data[point] != '*':
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--ROT, x.x, A*hh<CR><LF>
            # $HEROT,001.8,A*22
            # 初始化数据
            rot_rate = 0.0
            rot_stat = ''

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                rot_rate = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                rot_stat = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['rot'   ] = rot_rate
            result_dict['stat'  ] = rot_stat
            return result_dict
        except Exception as e:
            output("[IEC] ROT Exception: " + str(e.args))
            output("[IEC] ROT: " + data)
        return None

    def get_struct_TTM(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != 0 and data[point] != '*':
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--TTM, xx, x.x, x.x, a, x.x, x.x, a, x.x, x.x, a, c - -c, a, a, hhmmss.ss, a * hh < CR > < LF >
            # $RATTM, 101, 0.25, 256.15, T, 0.1, 68.7, T, 0.25, 0.00, N, XIANGYA, T,, 222350.00, R * 7C
            # $RATTM,05,15.23,14.2,T,31.41,359.1,R,3.96,-28.1,N,,T,,,A*3B
            # $AHTTM,1,4.1,124.7,T,0,0,T,,,N,,L,,045926.26,M*35
            # 初始化数据
            ttm_number = 0  # Target number, 00 to 99
            ttm_distance_own = 0.00  # Target distance from own ship
            ttm_bearing = 0.00  # Bearing from own ship, degrees true/relative (T/R)
            ttm_bearing_tr = ''  # (T/R)
            ttm_speed = 0.00  # Target speed
            ttm_course = 0.00  # Target course, degrees true/relative (T/R)
            ttm_course_tr = ''  # (T/R)
            ttm_distance = 0.00  # Distance of closest-point-of-approach
            ttm_cpa = 0.00  # Time to CPA, min., "-" increasing
            ttm_units = ''  # Speed/distance units, K/N/S
            ttm_name = ''  # Target name
            ttm_status = ''  # Target status L = Lost; Q = Query; T = Tracking
            ttm_reference = ''  # Reference target (see Note 2)= R,null otherwise
            ttm_utc_hour = 0
            ttm_utc_minute = 0
            ttm_utc_sec = 0
            ttm_type = ''  # Type of acquisition,A = Automatic,M = manual,R = reported

            # 解析数据
            point += 1
            utc_mark = 0  # 标志
            sInfo = ""
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_number = int(sInfo)  # Target number, 00 to 99

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_distance_own = round(float(sInfo), 2)  # Target distance from own ship

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_bearing = round(float(sInfo), 2)  # Bearing from own ship, degrees true/relative (T/R)

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ttm_bearing_tr = data[point]  # (T/R)
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_speed = round(float(sInfo), 2)  # arget speed

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_course = round(float(sInfo), 2)  # Target course, degrees true/relative (T/R)

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ttm_course_tr = data[point]  # (T/R)
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_distance = round(float(sInfo), 2)  # Distance of closest-point-of-approach

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                ttm_cpa = round(float(sInfo), 2)  # Time to CPA, min., "-" increasing

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ttm_units = data[point]  # Speed/distance units, K/N/S
                point += 1

            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                ttm_name += str(data[point])
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ttm_status = data[point]  # arget status
                point += 1

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ttm_reference = data[point]  # Reference target (see Note 2)= R,null otherwise
                point += 1

            sInfo = ""
            point += 1
            utc_mark = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
                utc_mark += 1
                if utc_mark == 3:
                    ttm_utc_hour = int(sInfo)  #
                    if ttm_utc_hour < 0 or ttm_utc_hour > 23:
                         ttm_utc_hour = 0
                    sInfo = ""
                if utc_mark == 5:
                    ttm_utc_minute = int(sInfo)
                    if ttm_utc_minute < 0 or ttm_utc_minute > 59:
                        ttm_utc_minute = 0
                    sInfo = ""
            if len(sInfo) > 0:
                ttm_utc_sec = float(sInfo)
                if ttm_utc_sec < 0 or ttm_utc_sec >= 60:
                    ttm_utc_sec = 0
            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ttm_type = data[point]  # Type of acquisition,A = Automatic,M = manual,R = reported
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['number'        ] = ttm_number  # Target number, 00 to 99
            result_dict['distance_own'  ] = ttm_distance_own  # Target distance from own ship
            result_dict['bearing'       ] = ttm_bearing  # Bearing from own ship, degrees true/relative (T/R)
            result_dict['bearing_tr'    ] = ttm_bearing_tr  # (T/R)
            result_dict['speed'         ] = ttm_speed  # Target speed
            result_dict['course'        ] = ttm_course  # Target course, degrees true/relative (T/R)
            result_dict['course_tr'     ] = ttm_course_tr  # (T/R)
            result_dict['distance'      ] = ttm_distance  # Distance of closest-point-of-approach
            result_dict['cpa'           ] = ttm_cpa  # Time to CPA, min., "-" increasing
            result_dict['units'         ] = ttm_units  # Speed/distance units, K/N/S
            result_dict['name'          ] = ttm_name  # Target name
            result_dict['status'        ] = ttm_status   # Target status
            result_dict['reference'     ] = ttm_reference  # Reference target (see Note 2)= R,null otherwise
            result_dict['utc_hour'      ] = ttm_utc_hour
            result_dict['utc_minute'    ] = ttm_utc_minute
            result_dict['utc_sec'       ] = ttm_utc_sec
            result_dict['type'          ] = ttm_type  # Type of acquisition,A = Automatic,M = manual,R = reported
            return result_dict
        except Exception as e:
            output("[IEC] TTM Exception: " + str(e.args))
            output("[IEC] TTM: " + data)
        return None

    def get_struct_VDM(self, data, bits, is_vdm):  # 取得结构体
        code_buf = DecodeVDM1.get_DecodeX4(data[7:], bits)
        if code_buf is None:
            return None, None
        try:
            # 解析数据头
            message_id, repeat_indicator, mmsi = DecodeVDM1.decode_vdm_head(code_buf)
            if message_id is None:
                return None, None
            result_dict = {'id': message_id, 'repeat': repeat_indicator, 'mmsi': mmsi}  # 构造返回结构
            if is_vdm:
                result_dict['sign_type'] = 'VDM'
                data_type = "AIM_" + str(message_id)
            else:
                result_dict['sign_type'] = 'VDO'
                data_type = "AIO_" + str(message_id)

            info_dict = None
            # 解析数据体
            if message_id == 1 or message_id == 2:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_1(code_buf)
            elif message_id == 3:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_3(code_buf)
            elif message_id == 4 or message_id == 11:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_4(code_buf)
            elif message_id == 5:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_5(code_buf)
            elif message_id == 6:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_6(code_buf)
            elif message_id == 7 or message_id == 13:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_7(code_buf)
            elif message_id == 8:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_8(code_buf)
            elif message_id == 9:
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_9(code_buf)
            elif message_id == 10:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_10(code_buf)
            elif message_id == 12:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_12(code_buf)
            elif message_id == 14:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_14(code_buf)
            elif message_id == 15:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_15(code_buf)
            elif message_id == 16:  # pass
                # 解析
                info_dict = DecodeVDM1.decode_vdm_message_16(code_buf)
            elif message_id == 17:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_17(code_buf)
            elif message_id == 18:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_18(code_buf)
            elif message_id == 19:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_19(code_buf)
            elif message_id == 20:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_20(code_buf)
            elif message_id == 21:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_21(code_buf)
            elif message_id == 22:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_22(code_buf)
            elif message_id == 23:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_23(code_buf)
            elif message_id == 24:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_24(code_buf)
            elif message_id == 25:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_25(code_buf)
            elif message_id == 26:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_26(code_buf)
            elif message_id == 27:  # pass
                # 解析
                info_dict = DecodeVDM2.decode_vdm_message_27(code_buf)

            if info_dict is None:
                return None, None
            result_dict['info'] = info_dict  # 构造返回结构
            return data_type, result_dict
        except Exception as e:
            output("[IEC] VDM[" + str(message_id) + "] Exception: " + str(e.args))
            output("[IEC] VDM[" + str(message_id) + "] : " + data)
            return "EXCEPT", None
        return None, None

    # 将ADO/ADM数据重组（包括组合多语句），将完整数据[AIO/AIM]加入m_data_list
    def add_vdm_list(self, data, is_vdm):
        if data is None:
            return
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return
        data_len -= 3  # 取掉未尾“*hh”的长度
        sign = False
        point = 0
        while point < data_len and data[point] != '*' and data[point] != 0:
            if data[point] == ',':
                sign = True
                break
            point += 1
        if not sign:
            return

        # !--VDM,x,x,x,a,s—s,x*hh<CR><LF>
        # !AIVDM,1,1,,B,169AB6U02;8fnLlA7m>SPRk608Dj,0*5D
        # 初始化数据
        vdm_total = 0
        vdm_number = 0
        vdm_serial_number = 0
        vdm_channel = ''
        vdm_data = ''
        vdm_bits = 0

        # 解析数据
        sInfo = ""
        point += 1
        while point < data_len and data[point] != '*' and data[point] != 0:
            if data[point] == ',':
                break
            sInfo += data[point]
            point += 1
        if len(sInfo) > 0:
            vdm_total = int(sInfo)  #

        sInfo = ""
        point += 1
        while point < data_len and data[point] != '*' and data[point] != 0:
            if data[point] == ',':
                break
            sInfo += data[point]
            point += 1
        if len(sInfo) > 0:
            vdm_number = int(sInfo)  #

        sInfo = ""
        point += 1
        while point < data_len and data[point] != '*' and data[point] != 0:
            if data[point] == ',':
                break
            sInfo += data[point]
            point += 1
        if len(sInfo) > 0:
            vdm_serial_number = int(sInfo)  #

        point += 1
        if point < data_len and data[point] != ',' and data[point] != '*':
            vdm_channel = data[point]
            point += 1

        sInfo = ""
        point += 1
        while point < data_len and data[point] != '*' and data[point] != 0:
            if data[point] == ',':
                break
            sInfo += data[point]
            point += 1
        if len(sInfo) > 0:
            vdm_data = sInfo  #

        sInfo = ""
        point += 1
        while point < data_len and data[point] != '*' and data[point] != 0:
            if data[point] == ',':
                break
            sInfo += data[point]
            point += 1
        if len(sInfo) > 0:
            vdm_bits = int(sInfo)  #

        if vdm_total < 1 or vdm_total > 9:
            return
        if vdm_number < 1 or vdm_number > 9:
            return
        if vdm_serial_number < 0 or vdm_serial_number > 9:
            return
        if vdm_bits < 0 or vdm_bits > 5:
            return
        if len(vdm_data) < 1 or len(vdm_data) > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return
        if vdm_total == 1:  # 单语句
            if is_vdm:
                self.add_data_list("!HHAIM," + vdm_data, "AIM", vdm_bits)  # 加入列表数据
            else:
                self.add_data_list("!HHAIO," + vdm_data, "AIO", vdm_bits)  # 加入列表数据
            if self.m_vdm_total != 0:
                # 清除多语句缓存
                self.m_vdm_list = {}
                self.m_vdm_total = 0
                self.m_vdm_bits = 0
            if self.m_vdo_total != 0:
                # 清除多语句缓存
                self.m_vdo_list = {}
                self.m_vdo_total = 0
                self.m_vdo_bits = 0
        else:  # 多语句
            if is_vdm:
                if vdm_number == 1:
                    # 重新缓存多语句
                    self.m_vdm_list = {}
                    self.m_vdm_total = vdm_total
                    self.m_vdm_bits = vdm_bits
                self.m_vdm_list['data' + str(vdm_number)] = vdm_data
                if len(self.m_vdm_list) == self.m_vdm_total:  # 语句数量已满，重组数据
                    code_data = ''
                    try:
                        for f in range(0, self.m_vdm_total):
                            code_data += self.m_vdm_list['data' + str(f+1)]
                    except Exception as e:
                        output("[IEC] VDM(make up) Exception: " + str(e.args))
                        # 清除多语句缓存
                        self.m_vdm_list = {}
                        self.m_vdm_total = 0
                        self.m_vdm_bits = 0
                        code_data = ''
                    if len(code_data) > 1:
                        self.add_data_list("!HHAIM," + code_data, "AIM", self.m_vdm_bits)  # 加入列表数据
                        # 清除多语句缓存
                        self.m_vdm_list = {}
                        self.m_vdm_total = 0
                        self.m_vdm_bits = 0
            else:
                if vdm_number == 1:
                    # 重新缓存多语句
                    self.m_vdo_list = {}
                    self.m_vdo_total = vdm_total
                    self.m_vdo_bits = vdm_bits
                self.m_vdo_list['data' + str(vdm_number)] = vdm_data
                if len(self.m_vdo_list) == self.m_vdo_total:  # 语句数量已满，重组数据
                    code_data = ''
                    try:
                        for f in range(0, self.m_vdo_total):
                            code_data += self.m_vdo_list['data' + str(f+1)]
                    except Exception as e:
                        output("[IEC] VDO(make up) Exception: " + str(e.args))
                        # 清除多语句缓存
                        self.m_vdo_list = {}
                        self.m_vdo_total = 0
                        self.m_vdo_bits = 0
                        code_data = ''
                    if len(code_data) > 1:
                        self.add_data_list("!HHAIO," + code_data, "AIO", self.m_vdo_bits)  # 加入列表数据
                        # 清除多语句缓存
                        self.m_vdo_list = {}
                        self.m_vdo_total = 0
                        self.m_vdo_bits = 0
        return

    def get_struct_VLW(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--VLW, x.x, N, x.x, N*hh<CR><LF>
            # $VDVLW,691752.25,N,8379.37,N*57
            # 初始化数据
            vlw_water = 0.0  # 累积对水距离
            vlw_water_units = ''  # 单位
            vlw_water_reset = 0.0  # 重置后的对水距离
            vlw_water_reset_units = ''  # 单位
            vlw_ground = 0.0  # 累积对地距离
            vlw_ground_units = ''  # 单位
            vlw_ground_reset = 0.0  # 重置后的对地距离
            vlw_ground_reset_units = ''  # 单位

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vlw_water = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vlw_water_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vlw_water_reset = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vlw_water_reset_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vlw_ground = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vlw_ground_units = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vlw_ground_reset = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vlw_ground_reset_units = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['water'] = vlw_water
            result_dict['water_units'] = vlw_water_units
            result_dict['water_reset'] = vlw_water_reset
            result_dict['water_reset_units'] = vlw_water_reset_units
            result_dict['ground'] = vlw_ground
            result_dict['ground_units'] = vlw_ground_units
            result_dict['ground_reset'] = vlw_ground_reset
            result_dict['ground_reset_units'] = vlw_ground_reset_units
            return result_dict
        except Exception as e:
            output("[IEC] VLW Exception: " + str(e.args))
            output("[IEC] VLW: " + data)
        return None

    def get_struct_VBW(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while data[point] != 0 and data[point] != '*' and point < data_len:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None

            # $--VBW, x.x, x.x, A, x.x, x.x, A, x.x, A, x.x, A*hh<CR><LF>
            # $VDVBW,-0.2,,A,,,V*47
            # 初始化数据
            vbw_lws = 0.0  # 纵向水速度
            vbw_tws = 0.0  # 横向水速度
            vbw_sws = ''  # 有效位
            vbw_lgs = 0.0  # 纵向地面速度
            vbw_tgs = 0.0  # 横向地面速度
            vbw_sgs = ''  # 有效位
            vbw_stws = 0.0  # 船尾横向水速度
            vbw_ssws = ''  # 有效位
            vbw_stgs = 0.0  # 船尾横向地面速度
            vbw_ssgs = ''  # 有效位

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vbw_lws = round(float(sInfo), 1)  #

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vbw_tws = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vbw_sws = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vbw_lgs = round(float(sInfo), 1)  #

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vbw_tgs = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vbw_sgs = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vbw_stws = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vbw_ssws = data[point]
                point += 1

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                vbw_stgs = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                vbw_ssgs = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['lws'] = vbw_lws
            result_dict['tws'] = vbw_tws
            result_dict['sws'] = vbw_sws
            result_dict['lgs'] = vbw_lgs
            result_dict['tgs'] = vbw_tgs
            result_dict['sgs'] = vbw_sgs
            result_dict['stws'] = vbw_stws
            result_dict['ssws'] = vbw_ssws
            result_dict['stgs'] = vbw_stgs
            result_dict['sgs'] = vbw_ssgs
            return result_dict
        except Exception as e:
            output("[IEC] VBW Exception: " + str(e.args))
            output("[IEC] VBW: " + data)
        return None

    def get_struct_ZDA(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != 0 and data[point] != '*':
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None
            # $--ZDA, hhmmss.ss, xx, xx, xxxx, xx, xx*hh<CR><LF>

            # 初始化数据
            zda_utc_hour = 0
            zda_utc_minute = 0
            zda_utc_sec = 0
            zda_utc_day = 0  # Day, 01 to 31 (UTC)
            zda_utc_month = 0  # Month, 01 to 12 (UTC
            zda_utc_year = 0  # Year (UTC)
            zda_local_zone_hour = 0  # Local zone hours(see Note), 00 h to ±13 h
            zda_local_zone_minute = 0  # Local zone minutes (see Note), 00 to +59
            # 解析数据
            point += 1
            utc_mark = 0  # 标志
            sInfo = ""
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
                utc_mark += 1
                if utc_mark == 2:
                    zda_utc_hour = int(sInfo)  # UTC时间
                    if zda_utc_hour < 0 or zda_utc_hour > 23:
                        zda_utc_hour = 24
                    sInfo = ""
                if utc_mark == 4:
                    zda_utc_minute = int(sInfo)
                    if zda_utc_minute < 0 or zda_utc_minute > 59:
                        zda_utc_minute = 60
                    sInfo = ""
            if len(sInfo) > 0:
                zda_utc_sec = float(sInfo)
                if zda_utc_sec < 0 or zda_utc_sec >= 60:
                    zda_utc_sec = 0

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                zda_utc_day = int(sInfo)
                if zda_utc_day < 1 or zda_utc_day > 31:
                    zda_utc_day = 0

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                zda_utc_month = int(sInfo)
                if zda_utc_month < 1 or zda_utc_month > 12:
                    zda_utc_month = 0

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                zda_utc_year = int(sInfo)

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                zda_local_zone_hour = int(sInfo)
                if zda_local_zone_hour < -13 or zda_local_zone_hour > 13:
                    zda_local_zone_hour = 0

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                zda_local_zone_minute = int(sInfo)
                if zda_local_zone_minute < 0 or zda_local_zone_minute > 59:
                    zda_local_zone_minute = 0

            # 构造返回结构
            result_dict = {}
            result_dict['utc_hour'] = zda_utc_hour
            result_dict['utc_minute'] = zda_utc_minute
            result_dict['utc_sec'] = zda_utc_sec
            result_dict['utc_year'] = zda_utc_year
            result_dict['utc_month'] = zda_utc_month
            result_dict['utc_day'] = zda_utc_day
            result_dict['local_zone_hour'] = zda_local_zone_hour
            result_dict['local_zone_minute'] = zda_local_zone_minute
            return result_dict
        except Exception as e:
            output("[IEC] ZDA Exception: " + str(e.args))
            output("[IEC] ZDA: " + data)
        return None

    def get_struct_test(self, data):  # 取得结构体
        if data is None:
            return None
        data_len = len(data)
        if data_len < 6 or data_len > DecodeVDM1.ID_SIZE_SIGN_BUF:
            return None
        try:
            data_len -= 3  # 取掉未尾“*hh”的长度
            sign = False
            point = 0
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    sign = True
                    break
                point += 1
            if not sign:
                return None
            #
            # 初始化数据

            # 解析数据
            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                int_value = int(sInfo)  #

            sInfo = ""
            point += 1
            while point < data_len and data[point] != '*' and data[point] != 0:
                if data[point] == ',':
                    break
                sInfo += data[point]
                point += 1
            if len(sInfo) > 0:
                float_value = round(float(sInfo), 1)  #

            point += 1
            if point < data_len and data[point] != ',' and data[point] != '*':
                ch_value = data[point]
                point += 1

            # 构造返回结构
            result_dict = {}
            result_dict['test'] = 0
            return result_dict
        except Exception as e:
            output("[IEC] TEST Exception: " + str(e.args))
            output("[IEC] TEST: " + data)
        return None

    def get_ABM_6(self, mmsi, str_data, is_Cn):
        if is_Cn:
            return DecodeVDM2.get_ABM_message_6(mmsi, str_data.encode('mbcs'), is_Cn)
        return DecodeVDM2.get_ABM_message_6(mmsi, str_data.encode(), is_Cn)

    def get_BBM_8(self, str_data, is_Cn):
        if is_Cn:
            return DecodeVDM2.get_BBM_message_8(str_data.encode('mbcs'), is_Cn)
        return DecodeVDM2.get_BBM_message_8(str_data.encode(), is_Cn)

    def get_ABM_12(self, mmsi, str_data, is_Cn):
        return DecodeVDM2.get_ABM_message_12(mmsi, str_data.encode(), is_Cn)

    def get_BBM_14(self, str_data, is_Cn):
        return DecodeVDM2.get_BBM_message_14(str_data.encode(), is_Cn)
