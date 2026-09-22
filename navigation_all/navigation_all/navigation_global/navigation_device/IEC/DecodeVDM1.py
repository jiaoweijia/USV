import binascii
import struct

'''
1:计划中的位置报告（A类船载移动设备）
2:指配的计划中的位置报告（A类船载移动设备）
3:特定位置报告，对询问的响应（A类船载移动设备）
4:基站的位置
5:计划中的静态和航行相关船只数据报告；（A类船载移动设备）
6:二进制寻址消息
7:确认收到寻址的二进制数据
8:二进制广播消息
9:标准的SAR航空器位置报告
10:UTC/日期询问
11:UTC/日期响应
12:寻址安全相关消息
13:确认收到寻址安全相关消息
14:安全相关广播消息
15:请求特定的消息类型（可导致一个或几个台站发出多个响应）
16:由主管部门通过基站指配特定的报告性能
17:DGNSS广播二进制消息,由基站提供的DGNSS校正 
18:标准的B类设备位置报告,替代消息1、2、3使用的标准的B类船载移动设备位置报告
19:扩展的B类设备位置报告;不再需要;扩展的B类船载移动设备位置报告；包含附加的静态信息
20:数据链路管理消息,为基站保留的时隙
21:助航设备报告,助航设备的位置和状态报告
22:信道管理,基站所用的信道和收发信机模式管理
23:群组指配命令,由主管部门通过基站为移动台特定指配特定的报告性能
24:静态数据报告,为MMSI指配的附加数据(A部分：名称;B部分：静态数据)
25:单时隙二进制消息,非计划中的短二进制数据发送（广播或寻址)
26:带有通信状态的多时隙二进制消息,计划的二进制数据发送（广播或寻址）
27:远距离应用的位置报告,基站覆盖以外的A类和B类“SO”船载移动设备
'''
ID_SIZE_BUF = 1024 * 2  #
ID_SIZE_SIGN_BUF = 100  #
ID_SIZE_CHECK_BUF = ID_SIZE_BUF + ID_SIZE_SIGN_BUF


# 校验16进制字符
def is_hex(ch):
    if b'0'[0] <= ch <= b'9'[0]:
        return True
    if b'A'[0] <= ch <= b'F'[0]:
        return True
    if b'a'[0] <= ch <= b'f'[0]:
        return True
    return False


# 校验数据和
def is_check_sum(buf):
    if buf is None:
        return False
    buf_len = len(buf)
    if buf is None or buf_len < 6 or buf_len > ID_SIZE_SIGN_BUF:
        return False
    if not is_hex(buf[buf_len - 2]) or not is_hex(buf[buf_len - 1]):
        return False
    _sum = buf[1]
    for i in range(2, buf_len - 3):
        _sum = _sum ^ buf[i]

    data_sum = '0X' + chr(buf[buf_len - 2]) + chr(buf[buf_len - 1])
    data_sum = int(data_sum, 16)
    if data_sum != _sum:
        return False
    return True


# 校验数据和
def get_check_sum(buf):
    if buf is None:
        return False
    buf_len = len(buf)
    _sum = buf[0]
    for i in range(1, buf_len):
        _sum = _sum ^ buf[i]
    return (hex(_sum))[2:].zfill(2).upper()


def get_ASCII_6To8Bit(ch):
    re_chr = ch
    if 0 < re_chr < 0x20:
        re_chr += 0x40
    else:
        if re_chr == 0:  # 过滤@符号
            re_chr = 0x20
    return chr(re_chr)


def get_ASCII_8To6Bit(ch):
    re_chr = ch
    if 0x61 <= re_chr <= 0x7A:
        re_chr -= 0x20
    if re_chr >= 0x40:
        re_chr -= 0x40
    return re_chr


# 编码X4
def get_EnCodeX4(data_buf):
    N = len(data_buf)
    code_buf = bytearray()
    for i in range(N):
        if data_buf[i] > (data_buf[i] & 63):
            data_buf[i] = (data_buf[i] & 63)
        ch = data_buf[i] + 0x30
        if ch > 0x57:  # 6bit转8bit字符
            ch += 0x08
        if ch < 0x30:
            return None
        code_buf.append(ch)
    return code_buf


# 解码X4
def get_DecodeX4(data, bits):
    if data is None or len(data) < 1:
        return None
    '''
    fill bits field: this field represents the number of fill bits added to
    complete the last six-bit coded character. This field is required and
    shall immediately follow the encapsulated data field. To
    encapsulate, the number of binary bits shall be a multiple of six. If it
    is not, one to five fill bits are added. This field shall be set to zero
    when no fill bits have been added. The fill bits field shall always be
    the last data field in the sentence. This shall not be a null field.
    '''
    data_buf = data.encode()
    code_buf = bytearray()
    # 解码
    N = len(data_buf)
    for i in range(N):
        if data_buf[i] - 0x30 < 0:
            return None
        ch = data_buf[i] - 0x30
        if data_buf[i] > 0x57:  # 6bit转8bit字符
            ch -= 0x08
        code_buf.append(ch)
    '''
    if bits != 0:
        ch = 0
        code_buf.append(ch)
    '''
    return code_buf


# 转中文内码
def get_EnCode_Chinese14(data_buf, ch_tmp, begin_bits):
    bits_point = begin_bits  # 设置开始位
    is_complete = True
    code_buf = bytearray()
    N = len(data_buf)
    point = 0
    for f in range(N):
        if f + point >= N:
            break
        if (data_buf[f + point] & 128) > 0 and (f + 1 + point < N) and (data_buf[f + 1 + point] & 128):
            # 汉字转码
            A = data_buf[f + point] & 127
            B = data_buf[f + 1 + point] & 127
            a1 = A - 0x40  # 7位有效
            b1 = B  # 7位有效
            if A < 0x40:
                a1 = (A - 0x30) * 4 + int(B / 0x20)
                b1 = B % 0x20
            a1 = a1 | 64
            if bits_point == 0:
                ch_tmp = (a1 >> 1) & 63
                code_buf.append(ch_tmp)
                ch_tmp = ((a1 << 5) & 32) | (b1 >> 2) & 31
                code_buf.append(ch_tmp)
                ch_tmp = ((b1 << 4) & 48)

                bits_point = 2
                point += 1
                is_complete = False
            elif bits_point == 1:
                ch_tmp = ch_tmp | ((a1 >> 2) & 31)
                code_buf.append(ch_tmp)
                ch_tmp = ((a1 << 4) & 48) | ((b1 >> 3) & 15)
                code_buf.append(ch_tmp)
                ch_tmp = (b1 << 3) & 56
                bits_point = 3
                point += 1
                is_complete = False
            elif bits_point == 2:
                ch_tmp = ch_tmp | ((a1 >> 3) & 15)
                code_buf.append(ch_tmp)
                ch_tmp = ((a1 << 3) & 56) | ((b1 >> 4) & 7)
                code_buf.append(ch_tmp)
                ch_tmp = (b1 << 2) & 60
                bits_point = 4
                point += 1
                is_complete = False
            elif bits_point == 3:
                ch_tmp = ch_tmp | ((a1 >> 4) & 7)
                code_buf.append(ch_tmp)
                ch_tmp = ((a1 << 2) & 60) | ((b1 >> 5) & 3)
                code_buf.append(ch_tmp)
                ch_tmp = (b1 << 1) & 62
                bits_point = 5
                point += 1
                is_complete = False
            elif bits_point == 4:
                ch_tmp = ch_tmp | (a1 >> 5) & 3
                code_buf.append(ch_tmp)
                ch_tmp = ((a1 << 1) & 62) | ((b1 >> 6) & 1)
                code_buf.append(ch_tmp)
                ch_tmp = b1 & 63
                code_buf.append(ch_tmp)
                bits_point = 0
                point += 1
                is_complete = True
            elif bits_point == 5:
                ch_tmp = ch_tmp | (a1 >> 6) & 1
                code_buf.append(ch_tmp)
                ch_tmp = a1 & 63
                code_buf.append(ch_tmp)
                ch_tmp = (b1 >> 1) & 63
                code_buf.append(ch_tmp)
                ch_tmp = (b1 << 5) & 32
                bits_point = 1
                point += 1
                is_complete = True
        else:
            if (data_buf[f + point] & 128) > 0:
                continue
            ch = get_ASCII_8To6Bit(data_buf[f + point])

            if bits_point == 0:
                ch_tmp = (ch >> 1) & 63
                code_buf.append(ch_tmp)
                ch_tmp = (ch << 5) & 32
                bits_point = 1
                is_complete = False
            elif bits_point == 1:
                ch_tmp = ch_tmp | ((ch >> 2) & 31)
                code_buf.append(ch_tmp)
                ch_tmp = (ch << 4) & 48
                bits_point = 2
                is_complete = False
            elif bits_point == 2:
                ch_tmp = ch_tmp | ((ch >> 3) & 15)
                code_buf.append(ch_tmp)
                ch_tmp = (ch << 3) & 56
                bits_point = 3
                is_complete = False
            elif bits_point == 3:
                ch_tmp = ch_tmp | ((ch >> 4) & 7)
                code_buf.append(ch_tmp)
                ch_tmp = (ch << 2) & 60
                bits_point = 4
                is_complete = False
            elif bits_point == 4:
                ch_tmp = ch_tmp | ((ch >> 5) & 3)
                code_buf.append(ch_tmp)
                ch_tmp = (ch << 1) & 62
                bits_point = 5
                is_complete = False
            elif bits_point == 5:
                ch_tmp = ch_tmp | ((ch >> 6) & 1)
                code_buf.append(ch_tmp)
                ch_tmp = ch & 63
                code_buf.append(ch_tmp)
                bits_point = 0
                is_complete = True

    if not is_complete:
        code_buf.append(ch_tmp)

    if bits_point == 0:
        fill_bits = 0
    else:
        fill_bits = 6 - bits_point

    return code_buf, fill_bits


SequentialMessageIdentifier = 0  # 0~3


def Get_SequentialMessageIdentifier():
    global SequentialMessageIdentifier
    if SequentialMessageIdentifier > 3:
        SequentialMessageIdentifier = 0

    return SequentialMessageIdentifier


# 解析VDM数据头
def decode_vdm_head(code_buf):
    message_id = int(code_buf[0])
    if message_id < 1 or message_id > 27:
        return None, None, None

    ch = code_buf[1]
    repeat_indicator = int(ch >> 4)
    # mmsi
    ch = code_buf[1] & 15
    mmsi = (ch * pow(2, 26) +
            code_buf[2] * pow(2, 20) +
            code_buf[3] * pow(2, 14) +
            code_buf[4] * pow(2, 8) +
            code_buf[5] * pow(2, 2))
    ch = code_buf[6] >> 4
    mmsi += int(ch)
    return message_id, repeat_indicator, mmsi


# 解析VDM数据,message1/2 [pass]
def decode_vdm_message_1(code_buf):
    #
    ch = code_buf[6] & 15
    ais1_status = int(ch)
    #
    flag = False
    ch = code_buf[7]
    if (ch & 32) > 0:
        flag = True
    ch = code_buf[7]
    ais1_rot = int(ch * pow(2, 2))
    ch = code_buf[8] >> 4
    ais1_rot += int(ch)
    if flag:
        bys = ais1_rot.to_bytes(2, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1])
        ais1_rot = int.from_bytes(new_bys, byteorder='big', signed=True)
    #
    ch = code_buf[8]
    ais1_sog = int((ch & 15) * pow(2, 6))
    ch = code_buf[9]
    ais1_sog += int(ch)
    if ais1_sog < 0 or ais1_sog > 1022:
        ais1_sog = 1023
    ais1_sog = round(ais1_sog * 0.1, 1)
    #
    ch = code_buf[10]
    if ch & 32 == 0:
        ais1_position = 0
    else:
        ais1_position = 1
    #
    flag = False
    if (ch & 16) > 0:
        flag = True  # 负数
    ais1_lon = (ch & 31) * pow(2, 23)
    ch = code_buf[11]
    ais1_lon += ch * pow(2, 17)
    ch = code_buf[12]
    ais1_lon += ch * pow(2, 11)
    ch = code_buf[13]
    ais1_lon += ch * pow(2, 5)
    ch = code_buf[14] >> 1
    ais1_lon += ch
    if flag:
        bys = ais1_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais1_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais1_lon /= 600000
    ais1_lon = round(ais1_lon, 6)
    if ais1_lon < -180 or ais1_lon > 180:
        ais1_lon = 181
    #
    ch = code_buf[14]
    flag = False
    if (ch & 1) > 0:
        flag = True  # 负数
    ch = code_buf[14] & 1
    ais1_lat = ch * pow(2, 26)
    ch = code_buf[15]
    ais1_lat += ch * pow(2, 20)
    ch = code_buf[16]
    ais1_lat += ch * pow(2, 14)
    ch = code_buf[17]
    ais1_lat += ch * pow(2, 8)
    ch = code_buf[18]
    ais1_lat += ch * pow(2, 2)
    ch = code_buf[19] >> 4
    ais1_lat += ch
    if flag:
        bys = ais1_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais1_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais1_lat /= 600000
    ais1_lat = round(ais1_lat, 6)
    if ais1_lat < -90 or ais1_lat > 90:
        ais1_lat = 91
    #
    ch = code_buf[19] & 15
    ais1_cog = ch * pow(2, 8)
    ch = code_buf[20]
    ais1_cog += ch * pow(2, 2)
    ch = code_buf[21] >> 4
    ais1_cog += ch
    if ais1_cog < 0 or ais1_cog > 3599:
        ais1_cog = 3600
    ais1_cog = round(ais1_cog * 0.1, 1)
    #
    ch = code_buf[21] & 15
    ais1_heading = ch * pow(2, 5)
    ch = code_buf[22] >> 1
    ais1_heading += ch
    if ais1_heading < 0 or ais1_heading > 359:
        ais1_heading = 511
    #
    ch = code_buf[22] & 1
    ais1_stamp = int(ch * pow(2, 5))
    ch = code_buf[23] >> 1
    ais1_stamp += ch
    if ais1_stamp < 0 or ais1_stamp > 63:
        ais1_stamp = 60
    #
    ch = code_buf[23] & 1
    ais1_special = int(ch * pow(2, 1))
    ch = code_buf[24] >> 5
    ais1_special += ch
    #
    ais1_spare = (code_buf[24] >> 2) & 7  # Not use
    #
    if code_buf[24] & 2 == 0:
        ais1_flag = 0
    else:
        ais1_flag = 1
    #
    ch = code_buf[24] & 1
    ais1_comm_state_sync_state = int(ch * pow(2, 1))
    ch = code_buf[25] >> 5
    ais1_comm_state_sync_state += int(ch)
    #
    ch = (code_buf[25] >> 3) & 7
    ais1_comm_state_slot_timeout = int(ch)
    #
    ch = code_buf[25] & 3
    ais1_comm_state_sub_message = int(ch * pow(2, 12))
    ch = code_buf[26]
    ais1_comm_state_sub_message += int(ch * pow(2, 6))
    ch = code_buf[27]
    ais1_comm_state_sub_message += int(ch)
    # 构造结构体
    info_dict = {}
    info_dict[
        'status'] = ais1_status  # 0=正在使用的引擎；1=在锚；2=没有下命令；3=限制可操作性；4=吃水受限；5=停泊；6=搁浅；7=从事捕鱼；8=帆船；9=预留；10=预留；11-14 =预留，15=没有定义默认
    info_dict['rot'] = ais1_rot  # Rate of turn ±127
    info_dict['sog'] = ais1_sog  # 对地速度 0-102.2节 102.3=没有，102.2=02.2节或更高(1/10)
    info_dict[
        'position'] = ais1_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict['lon'] = ais1_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict['lat'] = ais1_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['cog'] = ais1_cog  # 对地航向 (1/10)
    info_dict['heading'] = ais1_heading  # True heading
    info_dict[
        'stamp'] = ais1_stamp  # UTC second when the report was generated 0-59 or 60 if time stamp is not available, which should also be the default value or 62 if electronic position fixing system operates in estimated (dead reckoning) mode or 61 if positioning system is in manual input mode or 63 if the positioning system is inoperative
    info_dict['special'] = ais1_special  # special manoeuvre indicator
    info_dict['spare'] = ais1_spare  # Spare (Not used. Should be set to zero)
    info_dict['flag'] = ais1_flag  # RAIM-flag
    sotdma_dict = {}
    sotdma_dict['sync_state'] = ais1_comm_state_sync_state  # 0-3
    sotdma_dict['slot_timeout'] = ais1_comm_state_slot_timeout  # 0-7
    sotdma_dict['sub_message'] = ais1_comm_state_sub_message
    info_dict['sotdma'] = sotdma_dict
    return info_dict


# 解析VDM数据,message3 [pass]
def decode_vdm_message_3(code_buf):
    #
    ch = code_buf[6] & 15
    ais3_status = int(ch)
    #
    flag = False
    ch = code_buf[7]
    if (ch & 32) > 0:
        flag = True
    ch = code_buf[7]
    ais3_rot = int(ch * pow(2, 2))
    ch = code_buf[8] >> 4
    ais3_rot += int(ch)
    if flag:
        bys = ais3_rot.to_bytes(2, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1])
        ais3_rot = int.from_bytes(new_bys, byteorder='big', signed=True)
    #
    ch = code_buf[8]
    ais3_sog = int((ch & 15) * pow(2, 6))
    ch = code_buf[9]
    ais3_sog += int(ch)
    if ais3_sog < 0 or ais3_sog > 1022:
        ais3_sog = 1023
    ais3_sog = round(ais3_sog * 0.1, 1)
    #
    ch = code_buf[10]
    if ch & 32 == 0:
        ais3_position = 0
    else:
        ais3_position = 1
    #
    flag = False
    if (ch & 16) > 0:
        flag = True  # 负数
    ais3_lon = (ch & 31) * pow(2, 23)
    ch = code_buf[11]
    ais3_lon += ch * pow(2, 17)
    ch = code_buf[12]
    ais3_lon += ch * pow(2, 11)
    ch = code_buf[13]
    ais3_lon += ch * pow(2, 5)
    ch = code_buf[14] >> 1
    ais3_lon += ch
    if flag:
        bys = ais3_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais3_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais3_lon /= 600000
    ais3_lon = round(ais3_lon, 6)
    if ais3_lon < -180 or ais3_lon > 180:
        ais3_lon = 181
    #
    flag = False
    ch = code_buf[14]
    if (ch & 1) > 0:
        flag = True  # 负数
    ch = code_buf[14] & 1
    ais3_lat = ch * pow(2, 26)
    ch = code_buf[15]
    ais3_lat += ch * pow(2, 20)
    ch = code_buf[16]
    ais3_lat += ch * pow(2, 14)
    ch = code_buf[17]
    ais3_lat += ch * pow(2, 8)
    ch = code_buf[18]
    ais3_lat += ch * pow(2, 2)
    ch = code_buf[19] >> 4
    ais3_lat += ch
    if flag:
        bys = ais3_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais3_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais3_lat /= 600000
    ais3_lat = round(ais3_lat, 6)
    if ais3_lat < -90 or ais3_lat > 90:
        ais3_lat = 91
    #
    ch = code_buf[19] & 15
    ais3_cog = ch * pow(2, 8)
    ch = code_buf[20]
    ais3_cog += ch * pow(2, 2)
    ch = code_buf[21] >> 4
    ais3_cog += ch
    if ais3_cog < 0 or ais3_cog > 3599:
        ais3_cog = 3600
    ais3_cog = round(ais3_cog * 0.1, 1)
    #
    ch = code_buf[21] & 15
    ais3_heading = ch * pow(2, 5)
    ch = code_buf[22] >> 1
    ais3_heading += ch
    if ais3_heading < 0 or ais3_heading > 359:
        ais3_heading = 511
    #
    ch = code_buf[22] & 1
    ais3_stamp = int(ch * pow(2, 5))
    ch = code_buf[23] >> 1
    ais3_stamp += ch
    #
    ch = code_buf[23] & 1
    ais3_special = int(ch * pow(2, 1))
    ch = code_buf[24] >> 5
    ais3_special += ch
    #
    ais3_spare = (code_buf[24] >> 2) & 7  # Not use
    #
    if code_buf[24] & 2 == 0:
        ais3_flag = 0
    else:
        ais3_flag = 1
    #
    ch = code_buf[24] & 1
    ais3_comm_state_sync_state = int(ch * pow(2, 1))
    ch = code_buf[25] >> 5
    ais3_comm_state_sync_state += int(ch)
    #
    ch = code_buf[25] & 31
    ais3_comm_state_slot_increment = int(ch * pow(2, 8))
    ch = code_buf[26]
    ais3_comm_state_slot_increment += int(ch * pow(2, 2))
    ch = code_buf[27] >> 4
    ais3_comm_state_slot_increment += int(ch)
    #
    ch = (code_buf[27] >> 1) & 7
    ais3_comm_state_number_slots = ch
    #
    if code_buf[27] & 1 == 0:
        ais3_comm_state_flag = 0
    else:
        ais3_comm_state_flag = 1

    # 构造结构体
    info_dict = {}
    info_dict[
        'status'] = ais3_status  # 0=正在使用的引擎；1=在锚；2=没有下命令；3=限制可操作性；4=吃水受限；5=停泊；6=搁浅；7=从事捕鱼；8=帆船；9=预留；10=预留；11-14 =预留，15=没有定义默认
    info_dict['rot'] = ais3_rot  # Rate of turn ±127
    info_dict['sog'] = ais3_sog  # 对地速度 0-102.2节 102.3=没有，102.2=02.2节或更高(1/10)
    info_dict[
        'position'] = ais3_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict['lon'] = ais3_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict['lat'] = ais3_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['cog'] = ais3_cog  # 对地航向 (1/10)
    info_dict['heading'] = ais3_heading  # True heading
    info_dict[
        'stamp'] = ais3_stamp  # UTC second when the report was generated 0-59 or 60 if time stamp is not available, which should also be the default value or 62 if electronic position fixing system operates in estimated (dead reckoning) mode or 61 if positioning system is in manual input mode or 63 if the positioning system is inoperative
    info_dict['special'] = ais3_special  # special manoeuvre indicator
    info_dict['spare'] = ais3_spare  # Spare (Not used. Should be set to zero)
    info_dict['flag'] = ais3_flag  # RAIM-flag
    itdma_dict = {}
    itdma_dict['sync_state'] = ais3_comm_state_sync_state  # 0-3
    itdma_dict['slot_increment'] = ais3_comm_state_slot_increment
    itdma_dict['state_number_slots'] = ais3_comm_state_number_slots
    itdma_dict['state_flag'] = ais3_comm_state_flag
    info_dict['itdma'] = itdma_dict
    return info_dict


# 解析VDM数据,message4/11 [pass]
def decode_vdm_message_4(code_buf):
    #
    ch = code_buf[6] & 15
    ais4_utc_year = int(ch * pow(2, 10))
    ch = code_buf[7]
    ais4_utc_year += int(ch * pow(2, 4))
    ch = code_buf[8] >> 2
    ais4_utc_year += int(ch)
    if ais4_utc_year < 1 or ais4_utc_year > 9999:
        ais4_utc_year = 0
    #
    ch = code_buf[8] & 3
    ais4_utc_month = int(ch * pow(2, 2))
    ch = code_buf[9] >> 4
    ais4_utc_month += int(ch)
    if ais4_utc_month < 1 or ais4_utc_month > 12:
        ais4_utc_month = 0
    #
    ch = code_buf[9] & 15
    ais4_utc_day = int(ch * pow(2, 1))
    ch = code_buf[10] >> 5
    ais4_utc_day += int(ch)
    if ais4_utc_day < 1 or ais4_utc_day > 31:
        ais4_utc_day = 0
    #
    ch = code_buf[10] & 31
    ais4_utc_hour = int(ch)
    if ais4_utc_hour < 0 or ais4_utc_hour > 23:
        ais4_utc_hour = 24
    #
    ch = code_buf[11]
    ais4_utc_minute = int(ch)
    if ais4_utc_minute < 0 or ais4_utc_minute > 59:
        ais4_utc_minute = 60
    #
    ch = code_buf[12]
    ais4_utc_second = int(ch)
    if ais4_utc_second < 0 or ais4_utc_second > 59:
        ais4_utc_second = 60
    #
    if code_buf[13] >> 5 == 0:
        ais4_position = 0
    else:
        ais4_position = 1
    #
    flag = False
    ch = code_buf[13]
    if (ch & 16) > 0:
        flag = True
    ch = code_buf[13] & 31
    ais4_lon = ch * pow(2, 23)
    ch = code_buf[14]
    ais4_lon += ch * pow(2, 17)
    ch = code_buf[15]
    ais4_lon += ch * pow(2, 11)
    ch = code_buf[16]
    ais4_lon += ch * pow(2, 5)
    ch = code_buf[17] >> 1
    ais4_lon += ch
    if flag:
        bys = ais4_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais4_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais4_lon /= 600000
    ais4_lon = round(ais4_lon, 6)
    if ais4_lon < -180 or ais4_lon > 180:
        ais4_lon = 181
    #
    flag = False
    ch = code_buf[17]
    if (ch & 1) > 0:
        flag = True
    ch = code_buf[17] & 1
    ais4_lat = ch * pow(2, 26)
    ch = code_buf[18]
    ais4_lat += ch * pow(2, 20)
    ch = code_buf[19]
    ais4_lat += ch * pow(2, 14)
    ch = code_buf[20]
    ais4_lat += ch * pow(2, 8)
    ch = code_buf[21]
    ais4_lat += ch * pow(2, 2)
    ch = code_buf[22] >> 4
    ais4_lat += ch
    if flag:
        bys = ais4_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais4_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais4_lat /= 600000
    ais4_lat = round(ais4_lat, 6)
    if ais4_lat < -90 or ais4_lat > 90:
        ais4_lat = 91
    #
    ch = code_buf[22] & 15
    ais4_device_type = ch
    #
    ais4_control = code_buf[23] >> 5
    #
    ch = code_buf[23] & 31
    ais4_spare = int(ch * pow(2, 4))
    ch = code_buf[24] >> 2
    ais4_spare += ch  # Not use
    #
    if code_buf[24] & 2 == 0:
        ais4_flag = 0
    else:
        ais4_flag = 1
    #
    ch = code_buf[24] & 1
    ais4_comm_state_sync_state = int(ch * pow(2, 1))
    ch = code_buf[25] >> 5
    ais4_comm_state_sync_state += int(ch)
    #
    ch = (code_buf[25] >> 3) & 7
    ais4_comm_state_slot_timeout = int(ch)
    #
    ch = code_buf[25] & 3
    ais4_comm_state_sub_message = int(ch * pow(2, 12))
    ch = code_buf[26]
    ais4_comm_state_sub_message += int(ch * pow(2, 6))
    ch = code_buf[27]
    ais4_comm_state_sub_message += int(ch)
    # 构造结构体
    info_dict = {}
    info_dict['utc_year'] = ais4_utc_year
    info_dict['utc_month'] = ais4_utc_month
    info_dict['utc_day'] = ais4_utc_day
    info_dict['utc_hour'] = ais4_utc_hour
    info_dict['utc_minute'] = ais4_utc_minute
    info_dict['utc_second'] = ais4_utc_second
    info_dict[
        'position'] = ais4_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict['lon'] = ais4_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict['lat'] = ais4_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict[
        'device_type'] = ais4_device_type  # Use of differential corrections is defined by field position accuracy above: 0 = undefined (default) 1 = global positioning system (GPS) 2 = GNSS (GLONASS) 3 = combined GPS/GLONASS 4 = Loran-C 5 = Chayka 6 = integrated navigation system 7 = surveyed 8-15 = not used
    info_dict['control'] = ais4_control  # Transmission control for longrange broadcast message
    info_dict['spare'] = ais4_spare  # Spare (Not used. Should be set to zero)
    info_dict['flag'] = ais4_flag  # RAIM-flag
    sotdma_dict = {}
    sotdma_dict['sync_state'] = ais4_comm_state_sync_state  # 0-3
    sotdma_dict['slot_timeout'] = ais4_comm_state_slot_timeout  # 0-7
    sotdma_dict['sub_message'] = ais4_comm_state_sub_message
    info_dict['sotdma'] = sotdma_dict
    return info_dict


# 解析VDM数据,message5 [pass]
def decode_vdm_message_5(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais5_version = int(ch)
    #
    ch = code_buf[6] & 3
    ais5_imo = int(ch * pow(2, 28))
    ch = code_buf[7]
    ais5_imo += int(ch * pow(2, 22))
    ch = code_buf[8]
    ais5_imo += int(ch * pow(2, 16))
    ch = code_buf[9]
    ais5_imo += int(ch * pow(2, 10))
    ch = code_buf[10]
    ais5_imo += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais5_imo += int(ch)
    if ais5_imo < 1 or ais5_imo > 999999999:
        ais5_imo = 0
    #
    ais5_call_sign = ''
    for i in range(7):
        ch = code_buf[11 + i] & 3
        _call_sign = (ch * pow(2, 4))
        ch = code_buf[12 + i] >> 2
        _call_sign += ch
        if _call_sign > 0:
            ais5_call_sign += str(get_ASCII_6To8Bit(_call_sign))
    ais5_call_sign = ais5_call_sign.strip()
    #
    ais5_name = ''
    for i in range(20):
        ch = code_buf[18 + i] & 3
        _name = (ch * pow(2, 4))
        ch = code_buf[19 + i] >> 2
        _name += ch
        if _name > 0:
            ais5_name += str(get_ASCII_6To8Bit(_name))
    ais5_name = ais5_name.strip()
    #
    ch = code_buf[38] & 3
    ais5_cargo_type = int(ch * pow(2, 6))
    ch = code_buf[39]
    ais5_cargo_type += int(ch)
    if ais5_cargo_type < 1 or ais5_cargo_type > 255:
        ais5_cargo_type = 0
    #
    ch = code_buf[40]
    ais5_reference_a = int(ch * pow(2, 3))
    ch = code_buf[41] >> 3
    ais5_reference_a += int(ch)
    #
    ch = code_buf[41] & 7
    ais5_reference_b = int(ch * pow(2, 6))
    ch = code_buf[42]
    ais5_reference_b += int(ch)
    #
    ch = code_buf[43]
    ais5_reference_c = int(ch)
    #
    ch = code_buf[44]
    ais5_reference_d = int(ch)
    #
    ch = code_buf[45] >> 2
    ais5_device_type = int(ch)
    #
    ch = code_buf[45] & 3
    ais5_utc_month = int(ch * pow(2, 2))
    ch = code_buf[46] >> 4
    ais5_utc_month += int(ch)
    if ais5_utc_month < 1 or ais5_utc_month > 12:
        ais5_utc_month = 0
    #
    ch = code_buf[46] & 15
    ais5_utc_day = int(ch * pow(2, 1))
    ch = code_buf[47] >> 5
    ais5_utc_day += int(ch)
    if ais5_utc_day < 1 or ais5_utc_day > 31:
        ais5_utc_day = 0
    #
    ch = code_buf[47] & 31
    ais5_utc_hour = int(ch)
    if ais5_utc_hour < 0 or ais5_utc_hour > 23:
        ais5_utc_hour = 24
    #
    ch = code_buf[48]
    ais5_utc_minute = int(ch)
    if ais5_utc_minute < 0 or ais5_utc_minute > 59:
        ais5_utc_minute = 60
    #
    ch = code_buf[49]
    ais5_draught = ch * pow(2, 2)
    ch = code_buf[50] >> 4
    ais5_draught += ch
    ais5_draught = round(ais5_draught * 0.1, 1)
    #
    ais5_destination = ''
    for i in range(20):
        ch = code_buf[50 + i] & 15
        _destination = (ch * pow(2, 2))
        ch = code_buf[51 + i] >> 4
        _destination += ch
        if _destination > 0:
            ais5_destination += str(get_ASCII_6To8Bit(_destination))
    ais5_destination = ais5_destination.strip()
    #
    ais5_dte = 0
    ais5_spare = 0  # Not use

    if code_buf[70] & 8 != 0:
        ais5_dte = 1
    #
    if code_buf[70] & 4 != 0:
        ais5_spare = 1  # Not use

    # 构造结构体
    info_dict = {}
    info_dict[
        'version'] = ais5_version  # AIS version indicator 0 = station compliant with AIS edition 0; 1-3 = station compliant with future AIS editions 1, 2, and 3
    info_dict['imo'] = ais5_imo  # 1-999999999; 0 = not available = default
    info_dict['call_sign'] = ais5_call_sign  # Call sign
    info_dict['name'] = ais5_name  #
    info_dict[
        'cargo_type'] = ais5_cargo_type  # Type of ship and cargo type 0 = not available or no ship = default 1-99 = as defined in § 3.3.8.2.3.2 100-199 = preserved, for regional use 200-255 = preserved, for future use
    reference_dict = {}
    reference_dict['a'] = ais5_reference_a
    reference_dict['b'] = ais5_reference_b
    reference_dict['c'] = ais5_reference_c
    reference_dict['d'] = ais5_reference_d
    info_dict['reference'] = reference_dict  #
    info_dict[
        'device_type'] = ais5_device_type  # Use of differential corrections is defined by field position accuracy above: 0 = undefined (default) 1 = global positioning system (GPS) 2 = GNSS (GLONASS) 3 = combined GPS/GLONASS 4 = Loran-C 5 = Chayka 6 = integrated navigation system 7 = surveyed 8-15 = not used
    info_dict['utc_month'] = ais5_utc_month  #
    info_dict['utc_day'] = ais5_utc_day  #
    info_dict['utc_hour'] = ais5_utc_hour  #
    info_dict['utc_minute'] = ais5_utc_minute  #
    info_dict[
        'draught'] = ais5_draught  # Maximum present static draught ; in 1/10 m, 255 = draught 25.5 m or greater, 0 = not available =default;
    info_dict['destination'] = ais5_destination  #
    info_dict['dte'] = ais5_dte  # Data terminal ready (0 = available, 1 = not available = default)
    info_dict['spare'] = ais5_spare  # Spare (Not used. Should be set to zero)
    return info_dict


# 解析VDM数据,message6 [pass]
def decode_vdm_message_6(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais6_sequence = ch
    #
    ch = code_buf[6] & 3
    ais6_d_mmsi = int(ch * pow(2, 28))
    ch = code_buf[7]
    ais6_d_mmsi += int(ch * pow(2, 22))
    ch = code_buf[8]
    ais6_d_mmsi += int(ch * pow(2, 16))
    ch = code_buf[9]
    ais6_d_mmsi += int(ch * pow(2, 10))
    ch = code_buf[10]
    ais6_d_mmsi += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais6_d_mmsi += int(ch)
    #
    if code_buf[11] & 2 == 0:
        ais6_flag = 0
    else:
        ais6_flag = 1
    #
    ais6_spare = code_buf[11] & 1  # Not use
    #
    ais6_binarydata = bytearray()
    _point = len(code_buf) - 12
    if 0 < _point < 156:  # 156=936/6; 8bit字节数117=936/8  # 每8位取组成一个字节，包括16bit应用标识符（注：实际数据长度不足920时，后面取得的数据为0x00）
        for i in range(0, _point, 4):
            ch = code_buf[12 + i]
            _binarydata = int(ch * pow(2, 2))
            if i + 12 + 1 >= len(code_buf):
                break
            ch = code_buf[12 + i + 1] >> 4
            _binarydata += int(ch)
            ais6_binarydata.append(_binarydata)

            ch = code_buf[12 + i + 1] & 15
            _binarydata = int(ch * pow(2, 4))
            if i + 12 + 2 >= len(code_buf):
                break
            ch = code_buf[12 + i + 2] >> 2
            _binarydata += int(ch)
            ais6_binarydata.append(_binarydata)

            ch = code_buf[12 + i + 2] & 3
            _binarydata = int(ch * pow(2, 6))
            if i + 12 + 3 >= len(code_buf):
                break
            ch = code_buf[12 + i + 3]
            _binarydata += int(ch)
            ais6_binarydata.append(_binarydata)
    # 构造结构体
    info_dict = {}
    info_dict['sequence'] = ais6_sequence  # Sequence number 0-3
    info_dict['d_mmsi'] = ais6_d_mmsi  # MMSI number of destination station
    info_dict[
        'flag'] = ais6_flag  # Retransmit flag should be set upon retransmission: 0 = no retransmission = default; 1 = retransmitted
    info_dict['spare'] = ais6_spare  # Spare (Not used. Should be set to zero)
    info_dict['binarydata'] = str(binascii.b2a_hex(ais6_binarydata))[2:-1]  # Maximum 117
    return info_dict


# 解析VDM数据,message7/13 [pass]
def decode_vdm_message_7(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais7_spare = int(ch)  # Not use
    #
    ch = (code_buf[6]) & 3
    ais7_d_mmsi_1 = int(ch * pow(2, 28))
    ch = (code_buf[7])
    ais7_d_mmsi_1 += int(ch * pow(2, 22))
    ch = (code_buf[8])
    ais7_d_mmsi_1 += int(ch * pow(2, 16))
    ch = (code_buf[9])
    ais7_d_mmsi_1 += int(ch * pow(2, 10))
    ch = (code_buf[10])
    ais7_d_mmsi_1 += int(ch * pow(2, 4))
    ch = (code_buf[11]) >> 2
    ais7_d_mmsi_1 += int(ch)
    #
    ch = (code_buf[11]) & 3
    ais7_sequence_1 = ch
    #
    ais7_d_mmsi_2 = 0
    ais7_sequence_2 = 0
    if len(code_buf) > 17:
        ch = (code_buf[12])
        ais7_d_mmsi_2 = int(ch * pow(2, 24))
        ch = (code_buf[13])
        ais7_d_mmsi_2 += int(ch * pow(2, 18))
        ch = (code_buf[14])
        ais7_d_mmsi_2 += int(ch * pow(2, 12))
        ch = (code_buf[15])
        ais7_d_mmsi_2 += int(ch * pow(2, 6))
        ch = (code_buf[16])
        ais7_d_mmsi_2 += int(ch)
        #
        ch = (code_buf[17]) >> 4
        ais7_sequence_2 = ch
    #
    ais7_d_mmsi_3 = 0
    ais7_sequence_3 = 0
    if len(code_buf) > 22:
        ch = (code_buf[17]) & 15
        ais7_d_mmsi_3 = int(ch * pow(2, 26))
        ch = (code_buf[18])
        ais7_d_mmsi_3 += int(ch * pow(2, 20))
        ch = (code_buf[19])
        ais7_d_mmsi_3 += int(ch * pow(2, 14))
        ch = (code_buf[20])
        ais7_d_mmsi_3 += int(ch * pow(2, 8))
        ch = (code_buf[21])
        ais7_d_mmsi_3 += int(ch * pow(2, 2))
        ch = (code_buf[22]) >> 4
        ais7_d_mmsi_3 += int(ch)
        #
        ch = (code_buf[22] >> 2) & 3
        ais7_sequence_3 = ch
    #
    ais7_d_mmsi_4 = 0
    ais7_sequence_4 = 0
    if len(code_buf) > 27:
        ch = (code_buf[22]) & 3
        ais7_d_mmsi_4 = int(ch * pow(2, 28))
        ch = (code_buf[23])
        ais7_d_mmsi_4 += int(ch * pow(2, 22))
        ch = (code_buf[24])
        ais7_d_mmsi_4 += int(ch * pow(2, 16))
        ch = (code_buf[25])
        ais7_d_mmsi_4 += int(ch * pow(2, 10))
        ch = (code_buf[26])
        ais7_d_mmsi_4 += int(ch * pow(2, 4))
        ch = (code_buf[27]) >> 2
        ais7_d_mmsi_4 += int(ch)
        #
        ch = (code_buf[27]) & 3
        ais7_sequence_4 = ch
    #
    # 构造结构体
    info_dict = {}
    info_dict['spare'] = ais7_spare  # Spare (Not used. Should be set to zero)
    info_dict['d_mmsi_1'] = ais7_d_mmsi_1  # MMSI number of destination station
    info_dict['sequence_1'] = ais7_sequence_1  # Sequence number 0-3
    info_dict['d_mmsi_2'] = ais7_d_mmsi_2  # MMSI number of destination station
    info_dict['sequence_2'] = ais7_sequence_2  # Sequence number 0-3
    info_dict['d_mmsi_3'] = ais7_d_mmsi_3  # MMSI number of destination station
    info_dict['sequence_3'] = ais7_sequence_3  # Sequence number 0-3
    info_dict['d_mmsi_4'] = ais7_d_mmsi_4  # MMSI number of destination station
    info_dict['sequence_4'] = ais7_sequence_4  # Sequence number 0-3
    return info_dict


# 解析VDM数据,message8 [pass]
def decode_vdm_message_8(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais8_spare = ch  # Not use
    #
    ais8_binarydata = bytearray()
    _point = len(code_buf) - 6
    if 0 < _point <= 161:  # 161 =(968-2)/6; 8bit字节数121=968)/8 每8位组成一个字节，包括16bit应用标识符（注：实际数据长度不足952时，后面取得的数据为0x00）
        for i in range(0, _point, 4):
            ch = code_buf[6 + i] & 3
            _binarydata = int(ch * pow(2, 6))

            if i + 6 + 1 >= len(code_buf):
                break
            ch = code_buf[6 + i + 1]
            _binarydata += int(ch)
            ais8_binarydata.append(_binarydata)

            if i + 6 + 2 >= len(code_buf):
                break
            ch = code_buf[6 + i + 2]
            _binarydata = int(ch * pow(2, 2))
            if i + 6 + 3 >= len(code_buf):
                break
            ch = code_buf[6 + i + 3] >> 4
            _binarydata += int(ch)
            ais8_binarydata.append(_binarydata)

            ch = code_buf[6 + i + 3] & 15
            _binarydata = int(ch * pow(2, 4))
            if i + 6 + 4 >= len(code_buf):
                break
            ch = code_buf[6 + i + 4] >> 2
            _binarydata += int(ch)
            ais8_binarydata.append(_binarydata)
    # 构造结构体
    info_dict = {}
    info_dict['spare'] = ais8_spare  # Spare (Not used. Should be set to zero)
    info_dict['binarydata'] = str(binascii.b2a_hex(ais8_binarydata))[2:-1]  # Maximum 968
    return info_dict


# 解析VDM数据,message9
def decode_vdm_message_9(code_buf):
    #
    ch = code_buf[6] & 15
    ais9_altitude = int(ch * pow(2, 8))
    ch = code_buf[7]
    ais9_altitude += int(ch * pow(2, 2))
    ch = code_buf[8] >> 4
    ais9_altitude += int(ch)
    if ais9_altitude < 0 or ais9_altitude > 4094:
        ais9_altitude = 4095
    #
    ch = code_buf[8] & 15
    ais9_sog = int(ch * pow(2, 6))
    ch = code_buf[9]
    ais9_sog += int(ch)
    if ais9_sog < 0 or ais9_sog > 1022:
        ais9_sog = 1023
    ais9_sog = round(ais9_sog * 0.1, 1)
    #
    if code_buf[10] >> 7 == 0:
        ais9_position = 0
    else:
        ais9_position = 1
    #
    flag = False
    ch = code_buf[10]
    if (ch & 16) > 0:
        flag = True
    ch = code_buf[10] & 31
    ais9_lon = int(ch * pow(2, 23))
    ch = code_buf[11] & 31
    ais9_lon += int(ch * pow(2, 17))
    ch = code_buf[12] & 31
    ais9_lon += int(ch * pow(2, 11))
    ch = code_buf[13] & 31
    ais9_lon += int(ch * pow(2, 5))
    ch = code_buf[14] >> 1
    ais9_lon += int(ch)
    if flag:
        bys = ais9_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais9_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais9_lon /= 600000
    ais9_lon = round(ais9_lon, 6)
    if ais9_lon < -180 or ais9_lon > 180:
        ais9_lon = 181
    #
    flag = False
    ch = code_buf[14]
    if (ch & 1) > 0:
        flag = True
    ch = code_buf[14] & 1
    ais9_lat = int(ch * pow(2, 26))
    ch = code_buf[15]
    ais9_lat += int(ch * pow(2, 20))
    ch = code_buf[16]
    ais9_lat += int(ch * pow(2, 14))
    ch = code_buf[17]
    ais9_lat += int(ch * pow(2, 8))
    ch = code_buf[18]
    ais9_lat += int(ch * pow(2, 2))
    ch = code_buf[19] >> 4
    ais9_lat += int(ch)
    if flag:
        bys = ais9_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais9_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais9_lat /= 600000
    ais9_lat = round(ais9_lat, 6)
    if ais9_lat < -90 or ais9_lat > 90:
        ais9_lat = 91
    #
    ch = code_buf[19] & 15
    ais9_cog = int(ch * pow(2, 8))
    ch = code_buf[20]
    ais9_cog += int(ch * pow(2, 2))
    ch = code_buf[21] >> 4
    ais9_cog += int(ch)
    if ais9_cog < 0 or ais9_cog > 3599:
        ais9_cog = 3600
    ais9_cog = round(ais9_cog * 0.1, 1)
    #
    ch = code_buf[21] & 15
    ais9_stamp = int(ch * pow(2, 2))
    ch = code_buf[22] >> 4
    ais9_stamp += int(ch)
    #
    if code_buf[22] & 8 == 0:
        ais9_sensor = 0
    else:
        ais9_sensor = 1
    #
    ch = code_buf[22] & 7
    ais9_spare1 = int(ch * pow(2, 4))
    ch = code_buf[23] >> 2
    ais9_spare1 += int(ch)  # Not use
    #
    if code_buf[23] & 2 == 0:
        ais9_dte = 0
    else:
        ais9_dte = 1
    #
    ch = (code_buf[23] & 1)
    ais9_spare2 = int(ch * pow(2, 2))
    ch = code_buf[24] >> 4
    ais9_spare2 += int(ch)  # Not use
    #
    if code_buf[24] & 8 == 0:
        ais9_mode = 0
    else:
        ais9_mode = 1
    #
    if code_buf[24] & 4 == 0:
        ais9_flag = 0
    else:
        ais9_flag = 1
    #
    if (code_buf[24] & 2) == 0:
        #
        ais9_comm_state_flag = 0
        #
        ch = code_buf[24] & 1
        ais9_comm_state0_sync_state = int(ch * pow(2, 1))
        ch = code_buf[25] >> 5
        ais9_comm_state0_sync_state += int(ch)
        #
        ch = (code_buf[25] >> 2) & 7
        ais9_comm_state0_slot_timeout = int(ch)
        #
        ch = (code_buf[25]) & 3
        ais9_comm_state0_sub_message = int(ch * pow(2, 12))
        ch = (code_buf[26])
        ais9_comm_state0_sub_message += int(ch * pow(2, 6))
        ch = (code_buf[27])
        ais9_comm_state0_sub_message += int(ch)
    else:
        #
        ais9_comm_state_flag = 1
        #
        ch = code_buf[24] & 1
        ais9_comm_state1_sync_state = int(ch * pow(2, 1))
        ch = code_buf[25] >> 5
        ais9_comm_state1_sync_state += int(ch)
        #
        ch = code_buf[25] & 31
        ais9_comm_state1_slot_increment = int(ch * pow(2, 8))
        ch = code_buf[26]
        ais9_comm_state1_slot_increment += int(ch * pow(2, 2))
        ch = code_buf[27] >> 4
        ais9_comm_state1_slot_increment += int(ch)
        #
        ch = (code_buf[27] >> 1) & 7
        ais9_comm_state1_number_slots = ch
        #
        ais9_comm_state1_flag = code_buf[27] & 1

    # 构造结构体
    info_dict = {}

    info_dict[
        'altitude'] = ais9_altitude  # Altitude (GNSS);(m) (0-4094 m) 4095 = not available, 4094 = 4094 m or higher
    info_dict['sog'] = ais9_sog  # 对地速度 0-102.2节 102.3=没有，102.2=02.2节或更高(1/10)
    info_dict[
        'position'] = ais9_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict['lon'] = ais9_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict['lat'] = ais9_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['cog'] = ais9_cog  # 对地航向 (1/10)
    info_dict[
        'stamp'] = ais9_stamp  # UTC second when the report was generated 0-59 or 60 if time stamp is not available, which should also be the default value or 62 if electronic position fixing system operates in estimated (dead reckoning) mode or 61 if positioning system is in manual input mode or 63 if the positioning system is inoperative
    info_dict['sensor'] = ais9_sensor  # Altitude sensor(0 = GNSS, 1 = barometric source)
    info_dict['spare1'] = ais9_spare1  # 
    info_dict['dte'] = ais9_dte  # Data terminal ready (0 = available 1 = not available = default)
    info_dict['spare2'] = ais9_spare2  # 
    info_dict['mode'] = ais9_mode  # Assigned mode flag
    info_dict[
        'flag'] = ais9_flag  # RAIM flag of electronic position fixing device; 0 = RAIM not in use = default; 1 = RAIM in use)
    info_dict['comm_state_flag'] = ais9_comm_state_flag  # Communication state selector flag (0 = SOTDMA, 1 = ITDMA)
    sotdma_dict = {}
    itdma_dict = {}
    if ais9_comm_state_flag == 0:
        sotdma_dict['sync_state'] = ais9_comm_state0_sync_state
        sotdma_dict['slot_timeout'] = ais9_comm_state0_slot_timeout
        sotdma_dict['sub_message'] = ais9_comm_state0_sub_message

    else:
        itdma_dict['sync_state'] = ais9_comm_state1_sync_state
        itdma_dict['slot_increment'] = ais9_comm_state1_slot_increment
        itdma_dict['state_number_slots'] = ais9_comm_state1_number_slots
        itdma_dict['state_flag'] = ais9_comm_state1_flag
    info_dict['sotdma'] = sotdma_dict
    info_dict['itdma'] = itdma_dict
    return info_dict


# 解析VDM数据,message10 [pass]
def decode_vdm_message_10(code_buf):
    ch = (code_buf[6] >> 2) & 3
    ais10_spare1 = ch  # Not use
    #
    ch = code_buf[6] & 3
    ais10_d_mmsi = int(ch * pow(2, 28))
    ch = code_buf[7]
    ais10_d_mmsi += int(ch * pow(2, 22))
    ch = code_buf[8]
    ais10_d_mmsi += int(ch * pow(2, 16))
    ch = code_buf[9]
    ais10_d_mmsi += int(ch * pow(2, 10))
    ch = code_buf[10]
    ais10_d_mmsi += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais10_d_mmsi += int(ch)
    #
    ch = code_buf[11] & 3
    ais10_spare2 = ch  # Not use
    # 构造结构体
    info_dict = {}
    info_dict['spare1'] = ais10_spare1
    info_dict['d_mmsi'] = ais10_d_mmsi  # MMSI number of destination station
    info_dict['spare2'] = ais10_spare2
    return info_dict


# 解析VDM数据,message12 [pass]
def decode_vdm_message_12(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais12_sequence = ch
    #
    ch = code_buf[6] & 3
    ais12_d_mmsi = int(ch * pow(2, 28))
    ch = code_buf[7]
    ais12_d_mmsi += int(ch * pow(2, 22))
    ch = code_buf[8]
    ais12_d_mmsi += int(ch * pow(2, 16))
    ch = code_buf[9]
    ais12_d_mmsi += int(ch * pow(2, 10))
    ch = code_buf[10]
    ais12_d_mmsi += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais12_d_mmsi += int(ch)
    #
    if code_buf[11] & 2 == 0:
        ais12_flag = 0
    else:
        ais12_flag = 1
    #
    ais12_spare = code_buf[11] & 1  # Not use
    #
    ais12_txt = ""
    _point = len(code_buf) - 12
    if 0 < _point <= 156:  # 156 = 936 / 6
        for i in range(0, _point):
            _txt = code_buf[12 + i]
            if _txt > 0:
                ais12_txt += str(get_ASCII_6To8Bit(_txt))
        ais12_txt = ais12_txt.strip()
    # 构造结构体
    info_dict = {}
    info_dict['sequence'] = ais12_sequence
    info_dict['d_mmsi'] = ais12_d_mmsi
    info_dict['flag'] = ais12_flag
    info_dict['spare'] = ais12_spare
    info_dict['txt'] = ais12_txt  # Maximum 936
    return info_dict


# 解析VDM数据,message14 [pass]
def decode_vdm_message_14(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais14_spare = ch  # Not use
    #
    ais14_txt = ""
    _point = len(code_buf) - 7 - 1  # -1为了减去首部占用字节(2位)，首部和尾部可补齐1个字节
    if 0 < _point <= 161:  # 161 = (968-2) / 6 # 968/6有余，所以最后一个字符可能会因为位移导致不正确（注：实际数据长度不足968时，后面取得的数据为0x00）
        for i in range(0, _point):
            if i + 7 >= len(code_buf):
                break
            _txt = ((code_buf[6 + i] & 3) * pow(2, 4))
            _txt += (code_buf[6 + i + 1] >> 2)
            if _txt > 0:
                ais14_txt += str(get_ASCII_6To8Bit(_txt))
        ais14_txt = ais14_txt.strip()
    # 构造结构体
    info_dict = {}
    info_dict['spare'] = ais14_spare
    info_dict['txt'] = ais14_txt  # Maximum 968
    return info_dict


# 解析VDM数据,message15 [pass]
def decode_vdm_message_15(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais15_spare1 = ch  # Not use
    #
    ch = code_buf[6] & 3
    ais15_d_mmsi_1 = int(ch * pow(2, 28))
    ch = code_buf[7]
    ais15_d_mmsi_1 += int(ch * pow(2, 22))
    ch = code_buf[8]
    ais15_d_mmsi_1 += int(ch * pow(2, 16))
    ch = code_buf[9]
    ais15_d_mmsi_1 += int(ch * pow(2, 10))
    ch = code_buf[10]
    ais15_d_mmsi_1 += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais15_d_mmsi_1 += int(ch)
    #
    ch = code_buf[11] & 3
    ais15_message_id1_1 = int(ch * pow(2, 4))
    ch = code_buf[12] >> 2
    ais15_message_id1_1 += int(ch)
    #
    ch = code_buf[12] & 3
    ais15_slot1_1 = int(ch * pow(2, 10))
    ch = code_buf[13]
    ais15_slot1_1 += int(ch * pow(2, 4))
    ch = code_buf[14] >> 2
    ais15_slot1_1 += int(ch)
    #
    ch = code_buf[14] & 3
    ais15_spare2 = ch  # Not use
    #
    ais15_message_id1_2 = 0
    ais15_slot1_2 = 0
    ais15_spare3 = 0
    ais15_d_mmsi_2 = 0
    ais15_message_id2_1 = 0
    ais15_slot2_1 = 0
    ais15_spare4 = 0
    #
    if len(code_buf) > 17:
        ais15_message_id1_2 = int(code_buf[15])
        #
        ais15_slot1_2 = int(code_buf[16] * pow(2, 6))
        ais15_slot1_2 += int(code_buf[17])
        #
    if len(code_buf) > 26:
        ch = code_buf[18] >> 4
        ais15_spare3 = ch  # Not use
        #
        ch = code_buf[18] & 15
        ais15_d_mmsi_2 = int(ch * pow(2, 26))
        ch = code_buf[19]
        ais15_d_mmsi_2 += int(ch * pow(2, 20))
        ch = code_buf[20]
        ais15_d_mmsi_2 += int(ch * pow(2, 14))
        ch = code_buf[21]
        ais15_d_mmsi_2 += int(ch * pow(2, 8))
        ch = code_buf[22]
        ais15_d_mmsi_2 += int(ch * pow(2, 2))
        ch = code_buf[23] >> 4
        ais15_d_mmsi_2 += int(ch)
        #
        ch = code_buf[23] & 15
        ais15_message_id2_1 = int(ch * pow(2, 2))
        ch = code_buf[24] >> 4
        ais15_message_id2_1 += int(ch)
        #
        ch = code_buf[24] & 15
        ais15_slot2_1 = int(ch * pow(2, 8))
        ch = code_buf[25]
        ais15_slot2_1 += int(ch * pow(2, 2))
        ch = code_buf[26] >> 4
        ais15_slot2_1 += int(ch)
        #
        ch = (code_buf[26] >> 2) & 3
        ais15_spare4 = ch  # Not use

    # 构造结构体
    info_dict = {}
    info_dict['spare1'] = ais15_spare1  # Spare (Not used. Should be set to zero)
    info_dict['d_mmsi_1'] = ais15_d_mmsi_1  # MMSI number of destination station
    info_dict['message_id1_1'] = ais15_message_id1_1  # First requested message type from first interrogated station
    info_dict[
        'slot1_1'] = ais15_slot1_1  # Response slot offset for first requested message from first interrogated station
    info_dict['spare2'] = ais15_spare2  # 
    info_dict['message_id1_2'] = ais15_message_id1_2  # 
    info_dict['slot1_2'] = ais15_slot1_2  # 
    info_dict['spare3'] = ais15_spare3  # 
    info_dict['d_mmsi_2'] = ais15_d_mmsi_2  # MMSI number of destination station
    info_dict['message_id2_1'] = ais15_message_id2_1  # 
    info_dict['slot2_1'] = ais15_slot2_1  # 
    info_dict['spare4'] = ais15_spare4  # 
    return info_dict


# 解析VDM数据,message16 [pass]
def decode_vdm_message_16(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais16_spare1 = ch  # Not use
    #
    ch = code_buf[6] & 3
    ais16_d_mmsi_1 = int(ch * pow(2, 28))
    ch = code_buf[7]
    ais16_d_mmsi_1 += int(ch * pow(2, 22))
    ch = code_buf[8]
    ais16_d_mmsi_1 += int(ch * pow(2, 16))
    ch = code_buf[9]
    ais16_d_mmsi_1 += int(ch * pow(2, 10))
    ch = code_buf[10]
    ais16_d_mmsi_1 += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais16_d_mmsi_1 += int(ch)
    #
    ch = code_buf[11] & 3
    ais16_offset1 = int(ch * pow(2, 10))
    ch = code_buf[12]
    ais16_offset1 += int(ch * pow(2, 4))
    ch = code_buf[13] >> 2
    ais16_offset1 += int(ch)
    #
    ch = code_buf[13] & 3
    ais16_increment1 = int(ch * pow(2, 8))
    ch = code_buf[14]
    ais16_increment1 += int(ch * pow(2, 2))
    ch = code_buf[15] >> 4
    ais16_increment1 += int(ch)
    #
    ais16_d_mmsi_2 = 0
    ais16_offset2 = 0
    ais16_increment2 = 0
    ais16_spare2 = 0
    if len(code_buf) > 24:
        ch = code_buf[15] & 15
        ais16_d_mmsi_2 = int(ch * pow(2, 26))
        ch = code_buf[16]
        ais16_d_mmsi_2 += int(ch * pow(2, 20))
        ch = code_buf[17]
        ais16_d_mmsi_2 += int(ch * pow(2, 14))
        ch = code_buf[18]
        ais16_d_mmsi_2 += int(ch * pow(2, 8))
        ch = code_buf[19]
        ais16_d_mmsi_2 += int(ch * pow(2, 2))
        ch = code_buf[20] >> 4
        ais16_d_mmsi_2 += int(ch)
        #
        ch = code_buf[20] & 15
        ais16_offset2 = int(ch * pow(2, 8))
        ch = code_buf[21]
        ais16_offset2 += int(ch * pow(2, 2))
        ch = code_buf[22] >> 4
        ais16_offset2 += int(ch)
        #
        ch = code_buf[22] & 15
        ais16_increment2 = int(ch * pow(2, 6))
        ch = code_buf[23]
        ais16_increment2 += int(ch)
        #
        ch = code_buf[24] >> 2
        ais16_spare2 = ch

    # 构造结构体
    info_dict = {}
    info_dict['spare1'] = ais16_spare1  # Spare (Not used. Should be set to zero)
    info_dict['d_mmsi_1'] = ais16_d_mmsi_1  # MMSI number of destination station
    info_dict['offset1'] = ais16_offset1  # Offset from current slot to first assigned slot(1)
    info_dict['increment1'] = ais16_increment1  # Increment to next assigned slot(1)
    info_dict['d_mmsi_2'] = ais16_d_mmsi_2  # MMSI number of destination station
    info_dict['offset2'] = ais16_offset2  # Offset from current slot to first assigned slot(1)
    info_dict['increment2'] = ais16_increment2  # Increment to next assigned slot(1)
    info_dict['spare2'] = ais16_spare2  # Spare. Not used.
    return info_dict

