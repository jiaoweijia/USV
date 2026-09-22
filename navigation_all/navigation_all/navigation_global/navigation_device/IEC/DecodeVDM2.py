import binascii
import struct

from .DecodeVDM1 import (get_ASCII_6To8Bit, get_EnCodeX4, get_EnCode_Chinese14,
                                          get_check_sum, Get_SequentialMessageIdentifier, get_ASCII_8To6Bit,
                                          )

# 解析VDM数据,message17 [pass]
def decode_vdm_message_17(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais17_spare1 = ch  # Not use
    #
    flag = False
    ch = code_buf[6]
    if (ch & 2) > 0:
        flag = True
    ch = code_buf[6] & 3
    ais17_lon = int(ch * pow(2, 16))
    ch = code_buf[7]
    ais17_lon += int(ch * pow(2, 10))
    ch = code_buf[8]
    ais17_lon += int(ch * pow(2, 4))
    ch = code_buf[9] >> 2
    ais17_lon += int(ch)
    if flag:
        bys = ais17_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFC)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais17_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais17_lon /= 600
    ais17_lon = round(ais17_lon, 6)
    if ais17_lon < -180 or ais17_lon > 180:
        ais17_lon = 181
    #
    flag = False
    ch = code_buf[9]
    if (ch & 2) > 0:
        flag = True
    ch = code_buf[9] & 3
    ais17_lat = int(ch * pow(2, 15))
    ch = code_buf[10]
    ais17_lat += int(ch * pow(2, 9))
    ch = code_buf[11]
    ais17_lat += int(ch * pow(2, 3))
    ch = code_buf[12] >> 3
    ais17_lat += int(ch)
    if flag:
        bys = ais17_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFE)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais17_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais17_lat /= 600
    ais17_lat = round(ais17_lat, 6)
    if ais17_lat < -90 or ais17_lat > 90:
        ais17_lat = 91
    #
    ch = code_buf[12] & 7
    ais17_spare2 = int(ch * pow(2, 2))
    ch = code_buf[13] >> 4
    ais17_spare2 += int(ch)  # Not use
    #
    ch = code_buf[13] & 15
    ais17_data_type = int(ch * pow(2, 2))
    ch = code_buf[14] >> 4
    ais17_data_type += int(ch)
    #
    ch = code_buf[14] & 15
    ais17_data_id = int(ch * pow(2, 6))
    ch = code_buf[15]
    ais17_data_id += int(ch)
    #
    ch = code_buf[16]
    ais17_data_zcount = int(ch * pow(2, 7))
    ch = code_buf[17]
    ais17_data_zcount += int(ch * pow(2, 1))
    ch = code_buf[18] >> 5
    ais17_data_zcount += int(ch)
    #
    ch = (code_buf[18] >> 2) & 7
    ais17_data_sequence = int(ch)
    #
    ch = code_buf[18] & 3
    ais17_data_n = int(ch * pow(2, 3))
    ch = code_buf[19] >> 3
    ais17_data_n += int(ch)
    #
    ch = code_buf[19] & 7
    ais17_data_health = int(ch)
    #
    ais17_data_data = bytearray()
    if 0 < ais17_data_n <= 29:
        N = int(ais17_data_n * (24 / 6))
        for i in range(N):
            if i + 20 >= len(code_buf):
                break
            ais17_data_data.append(code_buf[20 + i])

    # 构造结构体
    info_dict = {}
    info_dict['spare1'  ] = ais17_spare1  # Spare (Not used. Should be set to zero)
    info_dict['lon'     ] = ais17_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict['lat'     ] = ais17_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['spare2'  ] = ais17_spare2  #
    
    data_json = {}
    data_json['type'    ] = ais17_data_type  # Recommendation ITU-R M.823 
    data_json['id'      ] = ais17_data_id  # Recommendation ITU-R M.823 station identifier
    data_json['zcount'  ] = ais17_data_zcount  # Time value in 0.6 s (0-3 599.4)
    data_json['sequence'] = ais17_data_sequence  # Sequence number Message sequence number (cyclic 0-7)
    data_json['n'       ] = ais17_data_n  # Number of DGNSS data words following the two word header, up to a maximum of 29
    data_json['health'  ] = ais17_data_health  # Reference station health
    data_json['data'    ] = str(binascii.b2a_hex(ais17_data_data))[2:-1]  # DGNSS message data words excluding parity(n×24)
    info_dict['data'    ] = data_json

    return info_dict


# 解析VDM数据,message18 [pass]
def decode_vdm_message_18(code_buf):
    #
    ch = code_buf[6] & 15
    ais18_spare1 = int(ch * pow(2, 4))
    ch = code_buf[7] >> 2
    ais18_spare1 += int(ch)  # Not use
    #
    ch = code_buf[7] & 3
    ais18_sog = int(ch * pow(2, 8))
    ch = code_buf[8]
    ais18_sog += int(ch * pow(2, 2))
    ch = code_buf[9] >> 4
    ais18_sog += int(ch)
    if ais18_sog < 0 or ais18_sog > 1022:
        ais18_sog = 1023
    ais18_sog = round(ais18_sog * 0.1, 1)
    #
    ais18_position = code_buf[9] & 8
    #
    flag = False
    ch = code_buf[9]
    if (ch & 4) > 0:
        flag = True
    ch = code_buf[9] & 7
    ais18_lon = int(ch * pow(2, 25))
    ch = code_buf[10]
    ais18_lon += int(ch * pow(2, 19))
    ch = code_buf[11]
    ais18_lon += int(ch * pow(2, 13))
    ch = code_buf[12]
    ais18_lon += int(ch * pow(2, 7))
    ch = code_buf[13]
    ais18_lon += int(ch * pow(2, 1))
    ch = code_buf[14] >> 5
    ais18_lon += int(ch)
    if flag:
        bys = ais18_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais18_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais18_lon /= 600000
    ais18_lon = round(ais18_lon, 6)
    if ais18_lon < -180 or ais18_lon > 180:
        ais18_lon = 181
    #
    flag = False
    ch = code_buf[14]
    if (ch & 16) > 0:
        flag = True
    ch = code_buf[14] & 31
    ais18_lat = int(ch * pow(2, 22))
    ch = code_buf[15]
    ais18_lat += int(ch * pow(2, 16))
    ch = code_buf[16]
    ais18_lat += int(ch * pow(2, 10))
    ch = code_buf[17]
    ais18_lat += int(ch * pow(2, 4))
    ch = code_buf[18] >> 2
    ais18_lat += int(ch)
    if flag:
        bys = ais18_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais18_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais18_lat /= 600000
    ais18_lat = round(ais18_lat, 6)
    if ais18_lat < -90 or ais18_lat > 90:
        ais18_lat = 91
    #
    ch = code_buf[18] & 3
    ais18_cog = int(ch * pow(2, 10))
    ch = code_buf[19]
    ais18_cog += int(ch * pow(2, 4))
    ch = code_buf[20] >> 2
    ais18_cog += int(ch)
    if ais18_cog < 0 or ais18_cog > 3599:
        ais18_cog = 3600
    ais18_cog = round(ais18_cog * 0.1, 1)
    #
    ch = code_buf[20] & 3
    ais18_heading = int(ch * pow(2, 7))
    ch = code_buf[21]
    ais18_heading += int(ch * pow(2, 1))
    ch = code_buf[22] >> 5
    ais18_heading += int(ch)
    if ais18_heading < 0 or ais18_heading > 359:
        ais18_heading = 511
    #
    ch = code_buf[22] & 31
    ais18_stamp = int(ch * pow(2, 1))
    ch = code_buf[23] >> 5
    ais18_stamp += int(ch)
    #
    ch = (code_buf[23] >> 3) & 3
    ais18_spare2 = ch  # Not use
    #
    if code_buf[23] & 4 == 0:
        ais18_unit_flag = 0
    else:
        ais18_unit_flag = 1
    #
    if code_buf[23] & 2 == 0:
        ais18_display_flag = 0
    else:
        ais18_display_flag = 1
    #
    ais18_dsc_flag = code_buf[23] & 1
    #
    if code_buf[24] & 32 == 0:
        ais18_band_flag = 0
    else:
        ais18_band_flag = 1
    #
    if code_buf[24] & 16 == 0:
        ais18_message22_flag = 0
    else:
        ais18_message22_flag = 1
    #
    if code_buf[24] & 8 == 0:
        ais18_mode_flag = 0
    else:
        ais18_mode_flag = 1
    #
    if code_buf[24] & 4 == 0:
        ais18_flag = 0
    else:
        ais18_flag = 1
    #
    if code_buf[24] & 2 == 0:
        ais18_comm_state_flag = 0
    else:
        ais18_comm_state_flag = 1
    #
    if ais18_comm_state_flag == 0:
        ch = code_buf[24] & 1
        ais18_comm_state0_sync_state = int(ch * pow(2, 1))
        ch = code_buf[25] >> 5
        ais18_comm_state0_sync_state += int(ch)
        #
        ch = (code_buf[25] >> 3) & 7
        ais18_comm_state0_slot_timeout = int(ch)
        #
        ch = code_buf[25] & 3
        ais18_comm_state0_sub_message = int(ch * pow(2, 12))
        ch = code_buf[26]
        ais18_comm_state0_sub_message += int(ch * pow(2, 6))
        ch = code_buf[27]
        ais18_comm_state0_sub_message += int(ch)
    else:
        ch = code_buf[24] & 1
        ais18_comm_state1_sync_state = int(ch * pow(2, 1))
        ch = code_buf[25] >> 5
        ais18_comm_state1_sync_state += int(ch)
        #
        ch = code_buf[25] & 31
        ais18_comm_state1_slot_increment = int(ch * pow(2, 8))
        ch = code_buf[26]
        ais18_comm_state1_slot_increment += int(ch * pow(2, 2))
        ch = code_buf[27] >> 4
        ais18_comm_state1_slot_increment += int(ch)
        #
        ch = (code_buf[27] >> 1) & 7
        ais18_comm_state1_number_slots = ch
        #
        ais18_comm_state1_flag = code_buf[27] & 1

    # 构造结构体
    info_dict = {}
    info_dict['spare1'          ] = ais18_spare1  #
    info_dict['sog'             ] = ais18_sog  # 对地速度 0-102.2节 102.3=没有，102.2=02.2节或更高(1/10)
    info_dict['position'        ] = ais18_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict['lon'             ] = ais18_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict['lat'             ] = ais18_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['cog'             ] = ais18_cog  # 对地航向 (1/10)
    info_dict['heading'         ] = ais18_heading  # True heading
    info_dict['stamp'           ] = ais18_stamp  # UTC second when the report was generated 0-59 or 60 if time stamp is not available, which should also be the default value or 62 if electronic position fixing system operates in estimated (dead reckoning) mode or 61 if positioning system is in manual input mode or 63 if the positioning system is inoperative
    info_dict['spare2'          ] = ais18_spare2  #
    info_dict['unit_flag'       ] = ais18_unit_flag  # 0 = Class B SOTDMA unit, 1 = Class B “CS” unit
    info_dict['display_flag'    ] = ais18_display_flag  # 0 = No display available;, 1 = Equipped with integrated display
    info_dict['dsc_flag'        ] = ais18_dsc_flag  # 0 = Not equipped with DSC function, 1 = Equipped with DSC function
    info_dict['band_flag'       ] = ais18_band_flag  # 0 = Capable of operating over the upper 525 kHz band of the marine band, 1 = Capable of operating over the whole marine band
    info_dict['message22_flag'  ] = ais18_message22_flag  # 0 = No frequency management via Message 22, 1 = Frequency management via Message 22
    info_dict['mode_flag'       ] = ais18_mode_flag  # 0 = Station operating in autonomous and continuous mode = default, 1 = Station operating in assigned mode
    info_dict['flag'            ] = ais18_flag  # RAIM-flag
    info_dict['comm_flag'       ] = ais18_comm_state_flag  # 0 = SOTDMA 1 = ITDMA communication state follows
    sotdma_dict = {}
    itdma_dict = {}
    if ais18_comm_state_flag == 0:
        sotdma_dict['sync_state'] = ais18_comm_state0_sync_state
        sotdma_dict['slot_timeout'] = ais18_comm_state0_slot_timeout
        sotdma_dict['sub_message'] = ais18_comm_state0_sub_message

    else:
        itdma_dict['sync_state'] = ais18_comm_state1_sync_state
        itdma_dict['slot_increment'] = ais18_comm_state1_slot_increment
        itdma_dict['state_number_slots'] = ais18_comm_state1_number_slots
        itdma_dict['state_flag'] = ais18_comm_state1_flag
    info_dict['sotdma'] = sotdma_dict
    info_dict['itdma'] = itdma_dict
    return info_dict


# 解析VDM数据,message19 [pass]
def decode_vdm_message_19(code_buf):
    #
    ch = code_buf[6] & 15
    ais19_reserved1 = int(ch * pow(2, 4))
    ch = code_buf[7] >> 2
    ais19_reserved1 += int(ch)

    ch = code_buf[7] & 3
    ais19_sog = int(ch * pow(2, 8))
    ch = code_buf[8]
    ais19_sog += int(ch * pow(2, 2))
    ch = code_buf[9] >> 4
    ais19_sog += int(ch)
    if ais19_sog < 0 or ais19_sog > 1022:
        ais19_sog = 1023
    ais19_sog = round(ais19_sog * 0.1, 1)
    #
    if code_buf[9] & 8 == 0:
        ais19_position = 0
    else:
        ais19_position = 1
    #
    flag = False
    ch = code_buf[9]
    if (ch & 4) > 0:
        flag = True
    ch = code_buf[9] & 7
    ais19_lon = int(ch * pow(2, 25))
    ch = code_buf[10]
    ais19_lon += int(ch * pow(2, 19))
    ch = code_buf[11]
    ais19_lon += int(ch * pow(2, 13))
    ch = code_buf[12]
    ais19_lon += int(ch * pow(2, 7))
    ch = code_buf[13]
    ais19_lon += int(ch * pow(2, 1))
    ch = code_buf[14] >> 5
    ais19_lon += int(ch)
    if flag:
        bys = ais19_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais19_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais19_lon /= 600000
    ais19_lon = round(ais19_lon, 6)
    if ais19_lon < -180 or ais19_lon > 180:
        ais19_lon = 181
    #
    flag = False
    ch = code_buf[14]
    if (ch & 16) > 0:
        flag = True
    ch = code_buf[14] & 31
    ais19_lat = int(ch * pow(2, 22))
    ch = code_buf[15]
    ais19_lat += int(ch * pow(2, 16))
    ch = code_buf[16]
    ais19_lat += int(ch * pow(2, 10))
    ch = code_buf[17]
    ais19_lat += int(ch * pow(2, 4))
    ch = code_buf[18] >> 2
    ais19_lat += int(ch)
    if flag:
        bys = ais19_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais19_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais19_lat /= 600000
    ais19_lat = round(ais19_lat, 6)
    if ais19_lat < -90 or ais19_lat > 90:
        ais19_lat = 91
    #
    ch = code_buf[18] & 3
    ais19_cog = int(ch * pow(2, 10))
    ch = code_buf[19]
    ais19_cog += int(ch * pow(2, 4))
    ch = code_buf[20] >> 2
    ais19_cog += int(ch)
    if ais19_cog < 0 or ais19_cog > 3599:
        ais19_cog = 3600
    ais19_cog = round(ais19_cog * 0.1, 1)
    #
    ch = code_buf[20] & 3
    ais19_heading = int(ch * pow(2, 7))
    ch = code_buf[21]
    ais19_heading += int(ch * pow(2, 1))
    ch = code_buf[22] >> 5
    ais19_heading += int(ch)
    if ais19_heading < 0 or ais19_heading > 359:
        ais19_heading = 511
    #
    ch = code_buf[22] & 31
    ais19_stamp = int(ch * pow(2, 1))
    ch = code_buf[23] >> 5
    ais19_stamp += int(ch)
    #
    ch = (code_buf[23] >> 1) & 15
    ais19_reserved2 = ch
    #
    ais19_name = ""
    for i in range(20):  # 20 = 120 / 6
        _name = int((code_buf[23 + i] & 1) * pow(2, 5))
        _name += int(code_buf[24 + i] >> 1)
        if _name > 0:
            ais19_name += str(get_ASCII_6To8Bit(_name))
    ais19_name = ais19_name.strip()
    #
    ch = code_buf[43] & 1
    ais19_cargo_type = int(ch * pow(2, 7))
    ch = code_buf[44]
    ais19_cargo_type += int(ch * pow(2, 1))
    ch = code_buf[45] >> 5
    ais19_cargo_type += int(ch)
    if ais19_cargo_type < 1 or ais19_cargo_type > 255:
        ais19_cargo_type = 0
    #
    ch = code_buf[45] & 31
    ais19_reference_a = int(ch * pow(2, 4))
    ch = code_buf[46] >> 2
    ais19_reference_a += int(ch)
    #
    ch = code_buf[46] & 3
    ais19_reference_b = int(ch * pow(2, 7))
    ch = code_buf[47]
    ais19_reference_b += int(ch * pow(2, 1))
    ch = code_buf[48] >> 5
    ais19_reference_b += int(ch)
    #
    ch = code_buf[48] & 31
    ais19_reference_c = int(ch * pow(2, 1))
    ch = code_buf[49] >> 5
    ais19_reference_c += ch
    #
    ch = code_buf[49] & 31
    ais19_reference_d = int(ch * pow(2, 1))
    ch = code_buf[50] >> 5
    ais19_reference_d += ch
    #
    ch = (code_buf[50] >> 1) & 15
    ais19_device_type = ch
    #
    ais19_flag = code_buf[50] & 1
    #
    if code_buf[51] & 32 == 0:
        ais19_dte = 0
    else:
        ais19_dte = 1
    #
    if code_buf[51] & 16 == 0:
        ais19_mode_flag = 0
    else:
        ais19_mode_flag = 1
    #
    ch = code_buf[51] & 15
    ais19_spare = ch  # Not use

    # 构造结构体
    info_dict = {}
    info_dict['reserved1'] = ais19_reserved1  # Reserved for regional or local applications
    info_dict['sog'] = ais19_sog  # 对地速度 0-102.2节 102.3=没有，102.2=02.2节或更高(1/10)
    info_dict[
        'position'] = ais19_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict[
        'lon'] = ais19_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict[
        'lat'] = ais19_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['cog'] = ais19_cog  # 对地航向 (1/10)
    info_dict['heading'] = ais19_heading  # True heading
    info_dict[
        'stamp'] = ais19_stamp  # UTC second when the report was generated 0-59 or 60 if time stamp is not available, which should also be the default value or 62 if electronic position fixing system operates in estimated (dead reckoning) mode or 61 if positioning system is in manual input mode or 63 if the positioning system is inoperative
    info_dict['reserved2'] = ais19_reserved2  # Reserved for regional applications
    info_dict['name'] = ais19_name  #
    info_dict[
        'cargo_type'] = ais19_cargo_type  # 0 = not available or no ship = default 1-99 = as defined in § 3.3.8.2.3.2 100-199 = preserved, for regional use 200-255 = preserved, for future use
    reference_dict = {}
    reference_dict['a'] = ais19_reference_a
    reference_dict['b'] = ais19_reference_b
    reference_dict['c'] = ais19_reference_c
    reference_dict['d'] = ais19_reference_d
    info_dict['reference'] = reference_dict  #
    info_dict[
        'device_type'] = ais19_device_type  # 0 = Undefined (default); 1 = GPS, 2 = GLONASS, 3 = combined GPS/GLONASS, 4 = Loran-C, 5 = Chayka, 6 = integrated navigation system, 7 = surveyed; 8-15 = not used
    info_dict['flag'] = ais19_flag  # RAIM-flag
    info_dict['dte'] = ais19_dte  # Data terminal ready (0 = available 1 = not available = default)
    info_dict['mode_flag'] = ais19_mode_flag  # Assigned mode flag
    info_dict['spare'] = ais19_spare  # (Not used. Should be set to zero)
    return info_dict


# 解析VDM数据,message20 [pass]
def decode_vdm_message_20(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais20_spare1 = ch  # Not use
    #
    ch = code_buf[6] & 3
    ais20_offset1 = int(ch * pow(2, 10))
    ch = code_buf[7]
    ais20_offset1 += int(ch * pow(2, 4))
    ch = code_buf[8] >> 2
    ais20_offset1 += int(ch)
    #
    ch = code_buf[8] & 3
    ais20_slots1 = int(ch * pow(2, 2))
    ch = code_buf[9] >> 4
    ais20_slots1 += int(ch)
    #
    ch = (code_buf[9] >> 1) & 7
    ais20_timeout1 = ch
    #
    ch = code_buf[9] & 1
    ais20_increment1 = int(ch * pow(2, 10))
    ch = code_buf[10]
    ais20_increment1 += int(ch * pow(2, 4))
    ch = code_buf[11] >> 2
    ais20_increment1 += int(ch)
    #
    ais20_offset2 = 0
    ais20_slots2 = 0
    ais20_timeout2 = 0
    ais20_increment2 = 0
    ais20_offset3 = 0
    ais20_slots3 = 0
    ais20_timeout3 = 0
    ais20_increment3 = 0
    ais20_offset4 = 0
    ais20_slots4 = 0
    ais20_timeout4 = 0
    ais20_increment4 = 0
    ais20_spare2 = 0
    #
    if len(code_buf) > 16:
        ch = code_buf[11] & 3
        ais20_offset2 = int(ch * pow(2, 10))
        ch = code_buf[12]
        ais20_offset2 += int(ch * pow(2, 4))
        ch = code_buf[13] >> 2
        ais20_offset2 += int(ch)
        #
        ch = code_buf[13] & 3
        ais20_slots2 = int(ch * pow(2, 2))
        ch = code_buf[14] >> 4
        ais20_slots2 += int(ch)
        #
        ch = (code_buf[14] >> 1) & 7
        ais20_timeout2 = ch
        #
        ch = code_buf[14] & 1
        ais20_increment2 = int(ch * pow(2, 10))
        ch = code_buf[15]
        ais20_increment2 += int(ch * pow(2, 4))
        ch = code_buf[16] >> 2
        ais20_increment2 += int(ch)
    #
    if len(code_buf) > 21:
        ch = code_buf[16] & 3
        ais20_offset3 = int(ch * pow(2, 10))
        ch = code_buf[17]
        ais20_offset3 += int(ch * pow(2, 4))
        ch = code_buf[18] >> 2
        ais20_offset3 += int(ch)
        #
        ch = code_buf[18] & 3
        ais20_slots3 = int(ch * pow(2, 2))
        ch = code_buf[19] >> 4
        ais20_slots3 += int(ch)
        #
        ch = (code_buf[19] >> 1) & 7
        ais20_timeout3 = ch
        #
        ch = code_buf[19] & 1
        ais20_increment3 = int(ch * pow(2, 10))
        ch = code_buf[20]
        ais20_increment3 += int(ch * pow(2, 4))
        ch = code_buf[21] >> 2
        ais20_increment3 += int(ch)
    #
    if len(code_buf) > 26:
        ch = code_buf[21] & 3
        ais20_offset4 = int(ch * pow(2, 10))
        ch = code_buf[22]
        ais20_offset4 += int(ch * pow(2, 4))
        ch = code_buf[23] >> 2
        ais20_offset4 += int(ch)
        #
        ch = code_buf[23] & 3
        ais20_slots4 = int(ch * pow(2, 2))
        ch = code_buf[24] >> 4
        ais20_slots4 += int(ch)
        #
        ch = (code_buf[24] >> 1) & 7
        ais20_timeout4 = ch
        #
        ch = code_buf[24] & 1
        ais20_increment4 = int(ch * pow(2, 10))
        ch = code_buf[25]
        ais20_increment4 += int(ch * pow(2, 4))
        ch = code_buf[26] >> 2
        ais20_increment4 += int(ch)
        #
        ch = code_buf[26] & 3
        ais20_spare2 = ch

    # 构造结构体
    info_dict = {}
    info_dict['spare1'] = ais20_spare1  # (Not used. Should be set to zero)
    info_dict['offset1'] = ais20_offset1  # Reserved offset number; 0 = not available
    info_dict['slots1'] = ais20_slots1  # Number of reserved consecutive slots: 1-15; 0 = not available
    info_dict['timeout1'] = ais20_timeout1  # Time-out value in minutes; 0 = not available
    info_dict['increment1'] = ais20_increment1  # Increment to repeat reservation block 1; 0 = not available
    info_dict['offset2'] = ais20_offset2  # Reserved offset number; 0 = not available
    info_dict['slots2'] = ais20_slots2  # Number of reserved consecutive slots: 1-15; 0 = not available
    info_dict['timeout2'] = ais20_timeout2  # Time-out value in minutes; 0 = not available
    info_dict['increment2'] = ais20_increment2  # Increment to repeat reservation block 1; 0 = not available
    info_dict['offset3'] = ais20_offset3  # Reserved offset number; 0 = not available
    info_dict['slots3'] = ais20_slots3  # Number of reserved consecutive slots: 1-15; 0 = not available
    info_dict['timeout3'] = ais20_timeout3  # Time-out value in minutes; 0 = not available
    info_dict['increment3'] = ais20_increment3  # Increment to repeat reservation block 1; 0 = not available
    info_dict['offset4'] = ais20_offset4  # Reserved offset number; 0 = not available
    info_dict['slots4'] = ais20_slots4  # Number of reserved consecutive slots: 1-15; 0 = not available
    info_dict['timeout4'] = ais20_timeout4  # Time-out value in minutes; 0 = not available
    info_dict['increment4'] = ais20_increment4  # Increment to repeat reservation block 1; 0 = not available
    info_dict['spare2'] = ais20_spare2
    return info_dict


# 解析VDM数据,message21 [pass]
def decode_vdm_message_21(code_buf):
    #
    ch = code_buf[6] & 15
    ais21_navigation = int(ch * pow(2, 1))
    ch = code_buf[7] >> 5
    ais21_navigation += int(ch)
    #
    ais21_name = ''
    for i in range(20):  # 20 = 120 / 6
        _name = int((code_buf[7 + i] & 31) * pow(2, 1))
        _name += int(code_buf[8 + i] >> 5)
        if _name > 0:
            ais21_name += str(get_ASCII_6To8Bit(_name))
    ais21_name = ais21_name.strip()
    #
    if code_buf[27] & 16 == 0:
        ais21_position = 0
    else:
        ais21_position = 1
    #
    flag = False
    ch = code_buf[27]
    if (ch & 8) > 0:
        flag = True
    ch = code_buf[27] & 15
    ais21_lon = int(ch * pow(2, 24))
    ch = code_buf[28]
    ais21_lon += int(ch * pow(2, 18))
    ch = code_buf[29]
    ais21_lon += int(ch * pow(2, 12))
    ch = code_buf[30]
    ais21_lon += int(ch * pow(2, 6))
    ch = code_buf[31]
    ais21_lon += int(ch)
    if flag:
        bys = ais21_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF0)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais21_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais21_lon /= 600000
    ais21_lon = round(ais21_lon, 6)
    if ais21_lon < -180 or ais21_lon > 180:
        ais21_lon = 181
    #
    flag = False
    ch = code_buf[32]
    if (ch & 32) > 0:
        flag = True
    ch = code_buf[32]
    ais21_lat = int(ch * pow(2, 21))
    ch = code_buf[33]
    ais21_lat += int(ch * pow(2, 15))
    ch = code_buf[34]
    ais21_lat += int(ch * pow(2, 9))
    ch = code_buf[35]
    ais21_lat += int(ch * pow(2, 3))
    ch = code_buf[36] >> 3
    ais21_lat += int(ch)
    if flag:
        bys = ais21_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(bys[0] | 0xF8)
        new_bys.append(bys[1])
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais21_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais21_lat /= 600000
    ais21_lat = round(ais21_lat, 6)
    if ais21_lat < -90 or ais21_lat > 90:
        ais21_lat = 91
    #
    ch = code_buf[36] & 7
    ais21_reference_a = int(ch * pow(2, 6))
    ch = code_buf[37]
    ais21_reference_a += int(ch)
    #
    ch = code_buf[38]
    ais21_reference_b = int(ch * pow(2, 3))
    ch = code_buf[39] >> 3
    ais21_reference_b += int(ch)
    #
    ch = code_buf[39] & 7
    ais21_reference_c = int(ch * pow(2, 3))
    ch = code_buf[40] >> 3
    ais21_reference_c += int(ch)
    #
    ch = code_buf[40] & 7
    ais21_reference_d = int(ch * pow(2, 3))
    ch = code_buf[41] >> 3
    ais21_reference_d += int(ch)
    #
    ch = code_buf[41] & 7
    ais21_device_type = int(ch * pow(2, 1))
    ch = code_buf[42] >> 5
    ais21_device_type += int(ch)
    #
    ch = code_buf[42] & 31
    ais21_stamp = int(ch * pow(2, 1))
    ch = code_buf[43] >> 5
    ais21_stamp += int(ch)
    #
    if code_buf[43] & 16 == 0:
        ais21_off_position = 0
    else:
        ais21_off_position = 1
    #
    ch = code_buf[43] & 15
    ais21_aton_status = int(ch * pow(2, 4))
    ch = code_buf[44] >> 2
    ais21_aton_status += int(ch)
    #
    if code_buf[44] & 2 == 0:
        ais21_flag = 0
    else:
        ais21_flag = 1
    #
    ais21_virtual_aton_flag = code_buf[44] & 1
    #
    if code_buf[45] & 32 == 0:
        ais21_mode_flag = 0
    else:
        ais21_mode_flag = 1
    #
    ais21_spare1 = code_buf[45] & 15
    #
    ais21_name_ext = ''
    _point = len(code_buf) - 46 - 1  # -1为了减去首部占用字节(2位)，首部和尾部可补齐1个字节

    if 0 < _point <= 60:  # 60 = 360/6
        for i in range(_point):
            _name_ext = int((code_buf[45 + i] & 15) * pow(2, 2))
            _name_ext += int(code_buf[46 + i] >> 4)
            if _name_ext > 0:
                ais21_name_ext += str(get_ASCII_6To8Bit(_name_ext))
        ais21_name_ext = ais21_name_ext.strip()
    #
    ais21_spare2 = 0  # Not use

    # 构造结构体
    info_dict = {}
    info_dict[
        'navigation'] = ais21_navigation  # 0 = not available = default; 1-15 = fixed aid-to-navigation; 16-31 =floating aid-to-navigation; refer to appropriate definition set up by IALA
    info_dict['name'] = ais21_name  # Name of Aids-to-Navigation
    info_dict[
        'position'] = ais21_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict[
        'lon'] = ais21_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict[
        'lat'] = ais21_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    reference_dict = {}
    reference_dict['a'] = ais21_reference_a
    reference_dict['b'] = ais21_reference_b
    reference_dict['c'] = ais21_reference_c
    reference_dict['d'] = ais21_reference_d
    info_dict['reference'] = reference_dict  #
    info_dict[
        'device_type'] = ais21_device_type  # 0 = Undefined (default);1 = GPS 2 = GLONASS 3 = Combined GPS/GLONASS 4 = Loran-C 5 = Chayka 6 = Integrated Navigation System 7 = surveyed 8-15 = not used
    info_dict[
        'stamp'] = ais21_stamp  # UTC second when the report was generated 0-59 or 60 if time stamp is not available, which should also be the default value or 62 if electronic position fixing system operates in estimated (dead reckoning) mode or 61 if positioning system is in manual input mode or 63 if the positioning system is inoperative
    info_dict[
        'off_position'] = ais21_off_position  # For floating aids-to-navigation, only: 0 = on position; 1 = off position;
    info_dict['aton_status'] = ais21_aton_status  # Reserved for the indication of the AtoN status
    info_dict['flag'] = ais21_flag  # RAIM-flag
    info_dict[
        'virtual_aton_flag'] = ais21_virtual_aton_flag  # 0 = default = real AtoN at indicated position; 1 = virtual AtoN
    info_dict['mode_flag'] = ais21_mode_flag  # Assigned mode flag
    info_dict['spare1'] = ais21_spare1  # Spare (Not used. Should be set to zero)
    info_dict['name_ext'] = ais21_name_ext  #
    info_dict['spare2'] = ais21_spare2  #
    return info_dict


# 解析VDM数据,message22 [pass]
def decode_vdm_message_22(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais22_spare1 = ch  # Not use
    #
    ch = code_buf[6] & 3
    ais22_channel_a = int(ch * pow(2, 10))
    ch = code_buf[7]
    ais22_channel_a += int(ch * pow(2, 4))
    ch = code_buf[8] >> 2
    ais22_channel_a += int(ch)
    #
    ch = code_buf[8] & 3
    ais22_channel_b = int(ch * pow(2, 10))
    ch = code_buf[9]
    ais22_channel_b += int(ch * pow(2, 4))
    ch = code_buf[10] >> 2
    ais22_channel_b += int(ch)
    #
    ch = code_buf[10] & 3
    ais22_mode = int(ch * pow(2, 2))
    ch = code_buf[11] >> 4
    ais22_mode += int(ch)
    #
    if code_buf[11] & 8 == 0:
        ais22_power = 0
    else:
        ais22_power = 1
    #
    ch = code_buf[11]
    flag = False
    if (code_buf[11] & 4) > 0:
        flag = True  # 负数
    ch = code_buf[11] & 7
    ais22_lon1 = int(ch * pow(2, 15))
    ch = code_buf[12]
    ais22_lon1 += int(ch * pow(2, 9))
    ch = code_buf[13]
    ais22_lon1 += int(ch * pow(2, 3))
    ch = code_buf[14] >> 3
    ais22_lon1 += int(ch)
    if flag:
        bys = ais22_lon1.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFC)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais22_lon1 = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais22_lon1 /= 600
    ais22_lon1 = round(ais22_lon1, 6)
    if ais22_lon1 < -180 or ais22_lon1 > 180:
        ais22_lon1 = 181
    #
    flag = False
    if (code_buf[14] & 4) > 0:
        flag = True  # 负数
    ch = code_buf[14] & 7
    ais22_lat1 = int(ch * pow(2, 14))
    ch = code_buf[15]
    ais22_lat1 += int(ch * pow(2, 8))
    ch = code_buf[16]
    ais22_lat1 += int(ch * pow(2, 2))
    ch = code_buf[17] >> 4
    ais22_lat1 += int(ch)
    if flag:
        bys = ais22_lat1.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFE)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais22_lat1 = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais22_lat1 /= 600
    ais22_lat1 = round(ais22_lat1, 6)
    if ais22_lat1 < -180 or ais22_lat1 > 180:
        ais22_lat1 = 181
    #
    flag = False
    if (code_buf[17] & 8) > 0:
        flag = True  # 负数
    ch = code_buf[17] & 15
    ais22_lon2 = int(ch * pow(2, 14))
    ch = code_buf[18]
    ais22_lon2 += int(ch * pow(2, 8))
    ch = code_buf[19]
    ais22_lon2 += int(ch * pow(2, 2))
    ch = code_buf[20] >> 3
    ais22_lon2 += int(ch)
    if flag:
        bys = ais22_lon2.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFC)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais22_lon2 = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais22_lon2 /= 600
    ais22_lon2 = round(ais22_lon2, 6)
    if ais22_lon2 < -180 or ais22_lon2 > 180:
        ais22_lon2 = 181
    #
    flag = False
    if (code_buf[20] & 8) > 0:
        flag = True  # 负数
    ch = code_buf[20] & 15
    ais22_lat2 = int(ch * pow(2, 13))
    ch = code_buf[21]
    ais22_lat2 += int(ch * pow(2, 7))
    ch = code_buf[22]
    ais22_lat2 += int(ch * pow(2, 1))
    ch = code_buf[23] >> 5
    ais22_lat2 += int(ch)
    if flag:
        bys = ais22_lat2.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFE)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais22_lat2 = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais22_lat2 /= 600
    ais22_lat2 = round(ais22_lat2, 6)
    if ais22_lat2 < -180 or ais22_lat2 > 180:
        ais22_lat2 = 181
    #
    if code_buf[23] & 16 == 0:
        ais22_broadcast = 0
    else:
        ais22_broadcast = 1
    #
    if code_buf[23] & 8 == 0:
        ais22_bandwidth_a = 0
    else:
        ais22_bandwidth_a = 1
    #
    if code_buf[23] & 4 == 0:
        ais22_bandwidth_b = 0
    else:
        ais22_bandwidth_b = 1
    #
    ch = code_buf[23] & 3
    ais22_size = int(ch * pow(2, 1))
    ch = code_buf[24] >> 5
    ais22_size += int(ch)
    #
    ch = code_buf[24] & 31
    ais22_spare2 = int(ch * pow(2, 18))
    ch = code_buf[25]
    ais22_spare2 += int(ch * pow(2, 12))
    ch = code_buf[26]
    ais22_spare2 += int(ch * pow(2, 6))
    ch = code_buf[27]
    ais22_spare2 += int(ch)  # Not use

    # 构造结构体
    info_dict = {}
    info_dict['spare1'] = ais22_spare1  # Spare (Not used. Should be set to zero)
    info_dict['channel_a'] = ais22_channel_a  # Channel number according to Recommendation ITU-R M.1084,Annex 4
    info_dict['channel_b'] = ais22_channel_b  #
    info_dict[
        'mode'] = ais22_mode  # 0 = Tx A/Tx B, Rx A/Rx B (default) 1 = Tx A, Rx A/Rx B 2 = Tx B, Rx A/Rx B 3-15: not used
    info_dict['power'] = ais22_power  # 0 = high (default), 1 = low
    info_dict['lon1'] = ais22_lon1  #
    info_dict['lat1'] = ais22_lat1  #
    info_dict['lon2'] = ais22_lon2  #
    info_dict['lat2'] = ais22_lat2  #
    info_dict[
        'broadcast'] = ais22_broadcast  # 0 = broadcast geographical area message = default; 1 = addressed message (to individual station(s))
    info_dict['bandwidth_a'] = ais22_bandwidth_a  # 0 = default (as specified by channel number);1 = 12.5 kHz bandwidth
    info_dict['bandwidth_b'] = ais22_bandwidth_b  #
    info_dict['size'] = ais22_size  # Transitional zone size
    info_dict['spare2'] = ais22_spare2
    return info_dict


# 解析VDM数据,message23 [pass]
def decode_vdm_message_23(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais23_spare1 = ch  # Not use
    #
    ais23_lon1 = 181
    ais23_lat1 = 91
    if len(code_buf) > 12:
        #
        ch = code_buf[6]
        flag = False
        if (ch & 2) > 0:
            flag = True  # 负数
        ais23_lon1 = (ch & 3) * pow(2, 16)
        ch = code_buf[7]
        ais23_lon1 += ch * pow(2, 10)
        ch = code_buf[8]
        ais23_lon1 += ch * pow(2, 4)
        ch = code_buf[9] >> 2
        ais23_lon1 += ch
        if flag:
            bys = ais23_lon1.to_bytes(4, byteorder='big', signed=True)
            new_bys = bytearray()
            new_bys.append(0xFF)
            new_bys.append(bys[1] | 0xFC)
            new_bys.append(bys[2])
            new_bys.append(bys[3])
            ais23_lon1 = int.from_bytes(new_bys, byteorder='big', signed=True)
        ais23_lon1 /= 600
        ais23_lon1 = round(ais23_lon1, 6)
        if ais23_lon1 < -180 or ais23_lon1 > 180:
            ais23_lon1 = 181
        #
        ch = code_buf[9]
        flag = False
        if (ch & 2) > 0:
            flag = True  # 负数
        ais23_lat1 = (ch & 3) * pow(2, 15)
        ch = code_buf[10]
        ais23_lat1 += ch * pow(2, 9)
        ch = code_buf[11]
        ais23_lat1 += ch * pow(2, 3)
        ch = code_buf[12] >> 3
        ais23_lat1 += ch
        if flag:
            bys = ais23_lat1.to_bytes(4, byteorder='big', signed=True)
            new_bys = bytearray()
            new_bys.append(0xFF)
            new_bys.append(bys[1] | 0xFE)
            new_bys.append(bys[2])
            new_bys.append(bys[3])
            ais23_lat1 = int.from_bytes(new_bys, byteorder='big', signed=True)
        ais23_lat1 /= 600
        ais23_lat1 = round(ais23_lat1, 6)
        if ais23_lat1 < -90 or ais23_lat1 > 90:
            ais23_lat1 = 91
    #
    ais23_lon2 = 181
    ais23_lat2 = 91
    ais23_station_type = 0
    ais23_cargo_type = 0
    ais23_spare2 = 0
    ais23_tr_mode = 0
    ais23_reporting_interval = 0
    ais23_quiet_time = 0
    ais23_spare3 = 0
    if len(code_buf) > 26:
        ch = code_buf[12]
        flag = False
        if (ch & 4) > 0:
            flag = True  # 负数
        ais23_lon2 = (ch & 3) * pow(2, 15)
        ch = code_buf[13]
        ais23_lon2 += ch * pow(2, 9)
        ch = code_buf[14]
        ais23_lon2 += ch * pow(2, 3)
        ch = code_buf[15] >> 3
        ais23_lon2 += ch
        if flag:
            bys = ais23_lon2.to_bytes(4, byteorder='big', signed=True)
            new_bys = bytearray()
            new_bys.append(0xFF)
            new_bys.append(bys[1] | 0xFC)
            new_bys.append(bys[2])
            new_bys.append(bys[3])
            ais23_lon2 = int.from_bytes(new_bys, byteorder='big', signed=True)
        ais23_lon2 /= 600
        ais23_lon2 = round(ais23_lon2, 6)
        if ais23_lon2 < -180 or ais23_lon2 > 180:
            ais23_lon2 = 181
        #
        ch = code_buf[15]
        flag = False
        if (ch & 4) > 0:
            flag = True  # 负数
        ais23_lat2 = (ch & 3) * pow(2, 14)
        ch = code_buf[16]
        ais23_lat2 += ch * pow(2, 8)
        ch = code_buf[17]
        ais23_lat2 += ch * pow(2, 2)
        ch = code_buf[18] >> 4
        ais23_lat2 += ch
        if flag:
            bys = ais23_lat2.to_bytes(4, byteorder='big', signed=True)
            new_bys = bytearray()
            new_bys.append(0xFF)
            new_bys.append(bys[1] | 0xFE)
            new_bys.append(bys[2])
            new_bys.append(bys[3])
            ais23_lat2 = int.from_bytes(new_bys, byteorder='big', signed=True)
        ais23_lat2 /= 600
        ais23_lat2 = round(ais23_lat2, 6)
        if ais23_lat2 < -90 or ais23_lat2 > 90:
            ais23_lat2 = 91
        #
        ch = code_buf[18] & 15
        ais23_station_type = ch
        #
        ch = code_buf[19]
        ais23_cargo_type = int(ch * pow(2, 2))
        ch = code_buf[20] >> 4
        ais23_cargo_type += int(ch)
        #
        ch = code_buf[20] & 15
        ais23_spare2 = (ch & 3) * pow(2, 18)
        ch = code_buf[21]
        ais23_spare2 += ch * pow(2, 12)
        ch = code_buf[22]
        ais23_spare2 += ch * pow(2, 6)
        ch = code_buf[23]
        ais23_spare2 += ch
        #
        ch = code_buf[24] >> 4
        ais23_tr_mode = int(ch)
        #
        ch = code_buf[24] & 15
        ais23_reporting_interval = int(ch)
        #
        ch = code_buf[25] >> 2
        ais23_quiet_time = int(ch)
        #
        ch = code_buf[25] & 3
        ais23_spare3 = int(ch * pow(2, 4))
        ch = code_buf[26] >> 2
        ais23_spare3 += ch
        ais23_spare3 = 0

    # 构造结构体
    info_dict = {}
    info_dict['spare1'] = ais23_spare1  # (Not used. Should be set to zero)
    info_dict['lon1'] = ais23_lon1  # 右上角（东北）；以1/10 min为单位（±180º，东=正，西=负）
    info_dict['lat1'] = ais23_lat1  # 右上角（东北）；以1/10 min为单位（±90º，北=正，南=负）
    info_dict['lon2'] = ais23_lon2  # 左下角（西南）；以1/10 min为单位（±180º，东=正，西=负）
    info_dict['lat2'] = ais23_lat2  # 左下角（西南）；以1/10 min为单位（±90º，北=正，南=负）
    info_dict['station_type'] = ais23_station_type  #
    info_dict['cargo_type'] = ais23_cargo_type  #
    info_dict['spare2'] = ais23_spare2  # (Not used. Should be set to zero)
    info_dict['tr_mode'] = ais23_tr_mode  #
    info_dict['reporting_interval'] = ais23_reporting_interval  #
    info_dict['quiet_time'] = ais23_quiet_time  #
    info_dict['spare3'] = ais23_spare3  #
    return info_dict


# 解析VDM数据,message24 [pass]
def decode_vdm_message_24(code_buf):
    #
    ch = (code_buf[6] >> 2) & 3
    ais24_part_number = ch
    #
    ais24_name = ""
    ais24_cargo_type = 0
    ais24_vendor_id = ""
    ais24_call_sign = ""
    ais24_reference_a = 0
    ais24_reference_b = 0
    ais24_reference_c = 0
    ais24_reference_d = 0
    ais24_spare = 0
    #
    if ais24_part_number == 0:
        # part A
        for i in range(20):
            if i + 7 >= len(code_buf):
                break
            ch = code_buf[6 + i] & 3
            _name = (ch * pow(2, 4))
            ch = code_buf[7 + i] >> 2
            _name += ch
            if _name > 0:
                ais24_name += str(get_ASCII_6To8Bit(_name))
        ais24_name = ais24_name.strip()
    else:
        # part B
        ch = code_buf[6] & 3
        ais24_cargo_type = int(ch * pow(2, 6))
        ch = code_buf[7]
        ais24_cargo_type += int(ch)
        #
        for i in range(7):
            ch = code_buf[8 + i]
            _vendor_id = ch
            if _vendor_id > 0:
                ais24_vendor_id += str(get_ASCII_6To8Bit(_vendor_id))
        ais24_vendor_id = ais24_vendor_id.strip()
        #
        for i in range(7):
            ch = code_buf[15 + i]
            _call_sign = ch
            if _call_sign > 0:
                ais24_call_sign += str(get_ASCII_6To8Bit(_call_sign))
        ais24_call_sign = ais24_call_sign.strip()
        #
        ch = code_buf[22]
        ais24_reference_a = int(ch * pow(2, 3))
        ch = code_buf[23] >> 3
        ais24_reference_a += int(ch)
        #
        ch = code_buf[23] & 7
        ais24_reference_b = int(ch * pow(2, 6))
        ch = code_buf[24]
        ais24_reference_b += int(ch)
        #
        ch = code_buf[25]
        ais24_reference_c = int(ch)
        #
        ch = code_buf[26]
        ais24_reference_d = int(ch)
        #
        ais24_spare = code_buf[27]

    # 构造结构体
    info_dict = {}
    info_dict['part_number'] = ais24_part_number  # 0:A ,1:B
    info_dict['name'] = ais24_name  #
    info_dict[
        'cargo_type'] = ais24_cargo_type  # Type of ship and cargo type 0 = not available or no ship = default 1-99 = as defined in § 3.3.8.2.3.2 100-199 = preserved, for regional use 200-255 = preserved, for future use
    info_dict['vendor_id'] = ais24_vendor_id  #
    info_dict['call_sign'] = ais24_call_sign  #
    reference_dict = {}
    reference_dict['a'] = ais24_reference_a
    reference_dict['b'] = ais24_reference_b
    reference_dict['c'] = ais24_reference_c
    reference_dict['d'] = ais24_reference_d
    info_dict['reference'] = reference_dict  #
    info_dict['spare'] = ais24_spare
    return info_dict


# 解析VDM数据,message25 [pass]
def decode_vdm_message_25(code_buf):
    #
    if code_buf[6] & 8 == 0:
        ais25_destination_indicator = 0
    else:
        ais25_destination_indicator = 1
    #
    if code_buf[6] & 4 == 0:
        ais25_binary_data_flag = 0
    else:
        ais25_binary_data_flag = 1
    #
    ais25_point = 0
    #
    ais25_destination_mmsi = 0
    if ais25_destination_indicator != 0:
        # 寻址
        ch = code_buf[6] & 3
        ais25_destination_mmsi = int(ch * pow(2, 28))
        ch = code_buf[7]
        ais25_destination_mmsi += int(ch * pow(2, 22))
        ch = code_buf[8]
        ais25_destination_mmsi += int(ch * pow(2, 16))
        ch = code_buf[9]
        ais25_destination_mmsi += int(ch * pow(2, 10))
        ch = code_buf[10]
        ais25_destination_mmsi += int(ch * pow(2, 4))
        ch = code_buf[11] >> 2
        ais25_destination_mmsi += int(ch)
        ais25_point = 5
    #
    _point = len(code_buf) - 6 - ais25_point
    ais25_binary_data = bytearray()

    if 0 < _point <= 21:  # 广播：21=(128-2)/6； 8bit字节数16=128/8;  寻址：8bit字节数12=(98-2)/8 # 每8位组成一个字节，包括16bit应用标识符
        for i in range(0, _point, 4):
            ch = code_buf[6 + ais25_point + i] & 3
            _binarydata = int(ch * pow(2, 6))

            if 6 + ais25_point + i + 1 >= len(code_buf):
                break
            ch = code_buf[6 + ais25_point + i + 1]
            _binarydata += int(ch)
            ais25_binary_data.append(_binarydata)

            if 6 + ais25_point + i + 2 >= len(code_buf):
                break
            ch = code_buf[6 + ais25_point + i + 2]
            _binarydata = int(ch * pow(2, 2))
            if 6 + ais25_point + i + 3 >= len(code_buf):
                break
            ch = code_buf[6 + ais25_point + i + 3] >> 4
            _binarydata += int(ch)
            ais25_binary_data.append(_binarydata)

            ch = code_buf[6 + ais25_point + i + 3] & 15
            _binarydata = int(ch * pow(2, 4))
            if 6 + ais25_point + i + 4 >= len(code_buf):
                break
            ch = code_buf[6 + ais25_point + i + 4] >> 2
            _binarydata += int(ch)
            ais25_binary_data.append(_binarydata)
    # 构造结构体
    info_dict = {}
    info_dict['destination_indicator'] = ais25_destination_indicator  # 0 = Broadcast, 1 = Addressed
    info_dict[
        'binary_data_flag'] = ais25_binary_data_flag  # 0 = unstructured binary data, 1 = binary data coded as defined by using the 16-bit Application identifier
    info_dict['destination_mmsi'] = ais25_destination_mmsi  #
    info_dict['binary_data'] = str(binascii.b2a_hex(ais25_binary_data))[
                               2:-1]  # binary_data[0]&3有效(2bit)，binary_data[1+n]&63有效(6bit)
    return info_dict


# 解析VDM数据,message26 [pass]
def decode_vdm_message_26(code_buf):
    #
    if code_buf[6] & 8 == 0:
        ais26_destination_indicator = 0  # 广播
    else:
        ais26_destination_indicator = 1  # 寻址
    #
    if code_buf[6] & 4 == 0:
        ais26_binary_data_flag = 0
    else:
        ais26_binary_data_flag = 1
    #
    ais26_point = 0
    ais26_destination_mmsi = 0
    if ais26_destination_indicator != 0:
        # 寻址
        ch = code_buf[6] & 3
        ais26_destination_mmsi = int(ch * pow(2, 28))
        ch = code_buf[7]
        ais26_destination_mmsi += int(ch * pow(2, 22))
        ch = code_buf[8]
        ais26_destination_mmsi += int(ch * pow(2, 16))
        ch = code_buf[9]
        ais26_destination_mmsi += int(ch * pow(2, 10))
        ch = code_buf[10]
        ais26_destination_mmsi += int(ch * pow(2, 4))
        ch = code_buf[11] >> 2
        ais26_destination_mmsi += int(ch)
        ais26_point = 5
    #
    ais26_binary_data = bytearray()
    _point = len(code_buf) - 6 - ais26_point

    if 0 < _point <= 170:  # 170=(1004+20-2)/6; 8bit字节数128=(1004+20)/8; 每8位组成一个字节，包括16bit应用标识符和结尾20bit的通信状态内容
        for i in range(0, _point, 4):
            ch = code_buf[6 + ais26_point + i] & 3
            _binarydata = int(ch * pow(2, 6))

            if 6 + ais26_point + i + 1 >= len(code_buf):
                break
            ch = code_buf[6 + ais26_point + i + 1]
            _binarydata += int(ch)
            ais26_binary_data.append(_binarydata)

            if 6 + ais26_point + i + 2 >= len(code_buf):
                break
            ch = code_buf[6 + ais26_point + i + 2]
            _binarydata = int(ch * pow(2, 2))
            if 6 + ais26_point + i + 3 >= len(code_buf):
                break
            ch = code_buf[6 + ais26_point + i + 3] >> 4
            _binarydata += int(ch)
            ais26_binary_data.append(_binarydata)

            ch = code_buf[6 + ais26_point + i + 3] & 15
            _binarydata = int(ch * pow(2, 4))
            if 6 + ais26_point + i + 4 >= len(code_buf):
                break
            ch = code_buf[6 + ais26_point + i + 4] >> 2
            _binarydata += int(ch)
            ais26_binary_data.append(_binarydata)

    # 构造结构体
    info_dict = {}
    info_dict['destination_indicator'] = ais26_destination_indicator  # 0 = Broadcast, 1 = Addressed
    info_dict[
        'binary_data_flag'] = ais26_binary_data_flag  # 0 = unstructured binary data, 1 = binary data coded as defined by using the 16-bit Application identifier
    info_dict['destination_mmsi'] = ais26_destination_mmsi  #
    info_dict['binary_data'] = str(binascii.b2a_hex(ais26_binary_data))[2:-1]
    '''
    sotdma_dict = {}
    itdma_dict = {}
    if ais26_comm_state_flag == 0:
        sotdma_dict['sync_state'] = ais26_comm_state0_sync_state
        sotdma_dict['slot_timeout'] = ais26_comm_state0_slot_timeout
        sotdma_dict['sub_message'] = ais26_comm_state0_sub_message
    else:
        itdma_dict['sync_state'] = ais26_comm_state1_sync_state
        itdma_dict['slot_increment'] = ais26_comm_state1_slot_increment
        itdma_dict['state_number_slots'] = ais26_comm_state1_number_slots
        itdma_dict['state_flag'] = ais26_comm_state1_flag
    info_dict['sotdma'] = sotdma_dict
    info_dict['itdma'] = itdma_dict
    '''
    return info_dict


# 解析VDM数据,message27 [pass]
def decode_vdm_message_27(code_buf):
    #
    if code_buf[6] & 8 == 0:
        ais27_position = 0
    else:
        ais27_position = 1
    #
    if code_buf[6] & 4 == 0:
        ais27_flag = 0
    else:
        ais27_flag = 1
    #
    ch = code_buf[6] & 3
    ais27_status = int(ch * pow(2, 2))
    ch = code_buf[7] >> 4
    ais27_status += int(ch)
    #
    ch = code_buf[7]
    flag = False
    if (ch & 8) > 0:
        flag = True  # 负数
    ais27_lon = (ch & 15) * pow(2, 14)
    ch = code_buf[8]
    ais27_lon += ch * pow(2, 8)
    ch = code_buf[9]
    ais27_lon += ch * pow(2, 2)
    ch = code_buf[10] >> 4
    ais27_lon += ch
    if flag:
        bys = ais27_lon.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFC)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais27_lon = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais27_lon /= 600
    ais27_lon = round(ais27_lon, 6)
    if ais27_lon < -180 or ais27_lon > 180:
        ais27_lon = 181
    #
    ch = code_buf[10]
    flag = False
    if (ch & 8) > 0:
        flag = True  # 负数
    ais27_lat = (ch & 15) * pow(2, 13)
    ch = code_buf[11]
    ais27_lat += ch * pow(2, 7)
    ch = code_buf[12]
    ais27_lat += ch * pow(2, 1)
    ch = code_buf[13] >> 5
    ais27_lat += ch
    if flag:
        bys = ais27_lat.to_bytes(4, byteorder='big', signed=True)
        new_bys = bytearray()
        new_bys.append(0xFF)
        new_bys.append(bys[1] | 0xFE)
        new_bys.append(bys[2])
        new_bys.append(bys[3])
        ais27_lat = int.from_bytes(new_bys, byteorder='big', signed=True)
    ais27_lat /= 600
    ais27_lat = round(ais27_lat, 6)
    if ais27_lat < -90 or ais27_lat > 90:
        ais27_lat = 91
    #
    ch = code_buf[13] & 31
    ais27_sog = int(ch * pow(2, 1))
    ch = code_buf[14] >> 5
    ais27_sog += int(ch)
    if ais27_sog < 0 or ais27_sog > 62:
        ais27_sog = 102.3  # 63
    #
    ch = code_buf[14] & 31
    ais27_cog = int(ch * pow(2, 4))
    ch = code_buf[15] >> 2
    ais27_cog += int(ch)
    if ais27_cog < 0 or ais27_cog > 359:
        ais27_cog = 360  # 511
    #
    if code_buf[15] & 2 == 0:
        ais27_gnss_position = 0
    else:
        ais27_gnss_position = 1
    #
    ais27_spare = code_buf[15] & 1

    # 构造结构体
    info_dict = {}
    info_dict[
        'position'] = ais27_position  # Position accuracy 1 = high (< 10 m; differential mode of e.g. DGNSS receiver) 0 = low (> 10 m; autonomous mode of e.g. global navigation satellite system(GNSS) receiver or of other electronic position fixing device); 0 = default
    info_dict[
        'flag'] = ais27_flag  # RAIM flag of electronic position fixing device; 0 = RAIM not in use = default; 1 = RAIM in use)
    info_dict['status'] = ais27_status  #
    info_dict[
        'lon'] = ais27_lon  # 经度(±180°, East = positive, West = negative.181° (6791AC0h) = not available = default)
    info_dict[
        'lat'] = ais27_lat  # 纬度(±90°, North = positive, South = negative.91° (3412140h) = not available = default)
    info_dict['sog'] = ais27_sog  # 对地速度 0-102.2节 102.3=没有，102.2=02.2节或更高(1/10)
    info_dict['cog'] = ais27_cog  # 对地航向 (1/10)
    info_dict[
        'gnss_position'] = ais27_gnss_position  # 0 = Position is the current GNSS position; 1 = Reported position is not the current GNSS position = default
    info_dict['spare'] = ais27_spare
    return info_dict


# 编码VDM数据,message6/8，二进制8bit
def encode_message_6_8bit(data_buf):
    code_buf = bytearray()
    N = len(data_buf)

    # 构造屏显解析协议；如不构造，对方可以输出语句，但屏幕中不显示
    code_buf.append(0)
    code_buf.append(0x04)  # 英文短信
    code_buf.append(0x00 | 0x02)  # 需要应答 | 0x02
    code_buf.append(0)
    ch_tmp = 0  # 递增序列号不使用

    for f in range(0, N, 3):
        ch_tmp = ch_tmp | (((data_buf[f]) >> 6) & 3)
        code_buf.append(ch_tmp)
        ch_tmp = data_buf[f] & 63
        code_buf.append(ch_tmp)
        if f + 1 >= N:
            fill_bits = 0
            break

        ch_tmp = (data_buf[f + 1] >> 2) & 63
        code_buf.append(ch_tmp)
        ch_tmp = ((data_buf[f + 1] << 4) & 48)
        if f + 2 >= N:
            code_buf.append(ch_tmp)
            fill_bits = 4
            break

        ch_tmp = ch_tmp | ((data_buf[f + 2] >> 4) & 15)
        code_buf.append(ch_tmp)
        ch_tmp = ((data_buf[f + 2] << 2) & 60)
        if f + 3 >= N:
            code_buf.append(ch_tmp)
            fill_bits = 2
            break

    encode_buf = get_EnCodeX4(code_buf)  # X4计算

    return encode_buf, fill_bits


# 解码VDM数据,message6/8，二进制8bit
def decode_message_6_8bit(data_buf):
    # 英文字符确码
    code_buf = bytearray()
    N = len(data_buf)

    for f in range(4, N, 4):
        ch_tmp = ((data_buf[f] << 6) & 192) | (data_buf[f + 1] & 63)
        code_buf.append(ch_tmp)
        ch_tmp = ((data_buf[f + 2] << 2) & 252) | ((data_buf[f + 3] >> 4) & 3)
        code_buf.append(ch_tmp)
        ch_tmp = ((data_buf[f + 3] << 4) & 240) | ((data_buf[f + 4] >> 2) & 15)
        code_buf.append(ch_tmp)

    return code_buf


# 编码VDM数据,message6/8，英文字符
def encode_message_6_en(data_buf):
    code_buf = bytearray()
    N = len(data_buf)

    data_6bit = bytearray()
    for f in range(N):
        ch = get_ASCII_8To6Bit(data_buf[f])
        data_6bit.append(ch)

    # 构造屏显解析协议；如不构造，对方可以输出语句，但屏幕中不显示
    code_buf.append(0)
    code_buf.append(0x04)  # 英文短信
    code_buf.append(0x00 | 0x02)  # 需要应答 | 0x02
    code_buf.append(0)
    ch_tmp = 0  # 递增序列号不使用

    for f in range(N):
        ch_tmp = ch_tmp | (((data_6bit[f]) >> 4) & 3)
        code_buf.append(ch_tmp)
        ch_tmp = (data_6bit[f] << 2) & 60

    code_buf.append(ch_tmp)
    fill_bits = 2

    encode_buf = get_EnCodeX4(code_buf)  # X4计算

    return encode_buf, fill_bits


# 解码VDM数据,message6/8，英文字符
def decode_message_6_en(data_buf):
    # 英文字符确码
    code_buf = bytearray()
    N = len(data_buf)

    for f in range(4, N):
        ch_tmp = ((data_buf[f] << 4) & 48) | ((data_buf[f + 1] >> 2) & 15)
        code_buf.append(ch_tmp)

    return code_buf


# 编码VDM数据,message6/8，中文内码
def encode_message_6_cn(data_buf):
    code_buf = bytearray()
    N = len(data_buf)

    # 构造屏显解析协议；如不构造，对方可以输出语句，但屏幕中不显示
    code_buf.append(25)
    code_buf.append(52)  # 中文短信
    ch_tmp = 4
    bits_point = 4  # 已占用位数
    encode_buf, fill_bits = get_EnCode_Chinese14(data_buf, ch_tmp, bits_point)  # 中文编码
    if encode_buf is None:
        return None, None
    for i in range(len(encode_buf)):
        code_buf.append(encode_buf[i])

    encode_buf = get_EnCodeX4(code_buf)  # X4计算

    return encode_buf, fill_bits


# 编码VDM数据,message12/14，英文字符
def encode_message_12_en(data_buf):
    code_buf = bytearray()
    N = len(data_buf)

    for f in range(N):
        ch = get_ASCII_8To6Bit(data_buf[f])
        code_buf.append(ch)

    encode_buf = get_EnCodeX4(code_buf)  # X4计算

    return encode_buf


# 编码VDM数据,message12/14，中文内码(通知规定不支持中文，在NSR AIS[NSI-1000 UAIS]设备中测试，中英文都显示乱码)
def encode_message_12_cn(data_buf):
    code_buf = bytearray()
    N = len(data_buf)

    # 构造屏显解析协议；如不构造，对方可以输出语句，但屏幕中不显示
    code_buf.append(38)
    code_buf.append(38)
    code_buf.append(38)

    bits_point = 0  # 已占用位数
    encode_buf1, fill_bits = get_EnCode_Chinese14(data_buf, bits_point)
    if encode_buf1 is None:
        return None, None
    for f in range(len(encode_buf1)):
        code_buf.append(encode_buf1[f])

    encode_buf = get_EnCodeX4(code_buf)  # X4计算

    return encode_buf, fill_bits


# 取得ABM语句，二进制寻址
def get_ABM_message_6(mmsi, data_buf, is_Cn):
    sequentialMessageIdentifier = 0
    if is_Cn:
        encode_buf, fill_bits = encode_message_6_cn(data_buf)
    else:
        encode_buf, fill_bits = encode_message_6_en(data_buf)

    if encode_buf is None:
        return None
    Des_len = len(encode_buf)
    if Des_len > 85:
        Des_len = 85  # 长度极限
    cutoff = 60  # (NSR AIS 60成功) # 语句分割长度 60->(8bit)45
    total_number = 1  # 语句统计
    if Des_len > cutoff:
        total_number = int(Des_len / cutoff)
        if Des_len % cutoff > 0:
            total_number += 1

    if total_number > 9:
        return None
    if total_number > 0:
        sequentialMessageIdentifier = Get_SequentialMessageIdentifier()

    result = ''
    point = 0
    number = 1  # 当前语句序号
    for f in range(total_number):
        abm_buf = bytearray()
        abm_buf_len = 0
        for f2 in range(cutoff):
            abm_buf.append(encode_buf[point])
            point += 1
            abm_buf_len += 1
            if abm_buf_len >= cutoff or point >= Des_len:
                break

        if f == total_number - 1:
            str_abm = "AIABM," + str(total_number) + "," + str(number) + ",0," + mmsi + ",0,6," + abm_buf.decode(
                'utf-8') + "," + str(fill_bits)
        else:
            str_abm = "AIABM," + str(total_number) + "," + str(number) + ",0," + mmsi + ",0,6," + abm_buf.decode(
                'utf-8') + ",0"

        result += '!' + str_abm + '*' + get_check_sum(str_abm.encode()) + '\r\n'
        number += 1

    return result


# 取得ABM语句，二进制广播
def get_BBM_message_8(data_buf, is_Cn):
    sequentialMessageIdentifier = 0
    if is_Cn:
        encode_buf, fill_bits = encode_message_6_cn(data_buf)
    else:
        encode_buf, fill_bits = encode_message_6_en(data_buf)

    if encode_buf is None:
        return None
    Des_len = len(encode_buf)
    if Des_len > 85:
        Des_len = 85  # 长度极限
    cutoff = 60  # (NSR AIS 60成功) # 语句分割长度 60->(8bit)45
    total_number = 1  # 语句统计
    if Des_len > cutoff:
        total_number = int(Des_len / cutoff)
        if Des_len % cutoff > 0:
            total_number += 1

    if total_number > 9:
        return None
    if total_number > 0:
        sequentialMessageIdentifier = Get_SequentialMessageIdentifier()

    result = ''
    point = 0
    number = 1  # 当前语句序号
    for f in range(total_number):
        abm_buf = bytearray()
        abm_buf_len = 0
        for f2 in range(cutoff):
            abm_buf.append(encode_buf[point])
            point += 1
            abm_buf_len += 1
            if abm_buf_len >= cutoff or point >= Des_len:
                break

        if f == total_number - 1:
            str_abm = "AIBBM," + str(total_number) + "," + str(number) + "," + str(
                sequentialMessageIdentifier) + ",0,8," + abm_buf.decode(
                'utf-8') + "," + str(fill_bits)
        else:
            str_abm = "AIBBM," + str(total_number) + "," + str(number) + "," + str(
                sequentialMessageIdentifier) + ",0,8," + abm_buf.decode(
                'utf-8') + ",0"

        result += '!' + str_abm + '*' + get_check_sum(str_abm.encode()) + '\r\n'
        number += 1

    return result


# 取得ABM语句，安全寻址
def get_ABM_message_12(mmsi, data_buf, is_Cn):
    sequentialMessageIdentifier = 0
    fill_bits = 0
    if is_Cn:
        encode_buf, fill_bits = encode_message_12_cn(data_buf)
    else:
        encode_buf = encode_message_12_en(data_buf)

    if encode_buf is None:
        return None
    Des_len = len(encode_buf)
    if Des_len > 85:
        Des_len = 85  # 长度极限
    cutoff = 60  # (NSR AIS 60成功) # 语句分割长度 60->(8bit)45
    total_number = 1  # 语句统计
    if Des_len > cutoff:
        total_number = int(Des_len / cutoff)
        if Des_len % cutoff > 0:
            total_number += 1

    if total_number > 9:
        return None
    if total_number > 0:
        sequentialMessageIdentifier = Get_SequentialMessageIdentifier()

    result = ''
    point = 0
    number = 1  # 当前语句序号
    for f in range(total_number):
        abm_buf = bytearray()
        abm_buf_len = 0
        for f2 in range(cutoff):
            abm_buf.append(encode_buf[point])
            point += 1
            abm_buf_len += 1
            if abm_buf_len >= cutoff or point >= Des_len:
                break

        if f == total_number - 1:
            str_abm = "AIABM," + str(total_number) + "," + str(number) + ",0," + mmsi + ",0,12," + abm_buf.decode(
                'utf-8') + "," + str(fill_bits)
        else:
            str_abm = "AIABM," + str(total_number) + "," + str(number) + ",0," + mmsi + ",0,12," + abm_buf.decode(
                'utf-8') + ",0"

        result += '!' + str_abm + '*' + get_check_sum(str_abm.encode()) + '\r\n'
        number += 1

    return result


# 取得ABM语句，安全广播
def get_BBM_message_14(data_buf, is_Cn):
    sequentialMessageIdentifier = 0
    fill_bits = 0
    if is_Cn:
        encode_buf, fill_bits = encode_message_12_cn(data_buf)
    else:
        encode_buf = encode_message_12_en(data_buf)

    if encode_buf is None:
        return None
    Des_len = len(encode_buf)
    if Des_len > 85:
        Des_len = 85  # 长度极限
    cutoff = 60  # (NSR AIS 60成功) # 语句分割长度 60->(8bit)45
    total_number = 1  # 语句统计
    if Des_len > cutoff:
        total_number = int(Des_len / cutoff)
        if Des_len % cutoff > 0:
            total_number += 1

    if total_number > 9:
        return None
    if total_number > 0:
        sequentialMessageIdentifier = Get_SequentialMessageIdentifier()

    result = ''
    point = 0
    number = 1  # 当前语句序号
    for f in range(total_number):
        abm_buf = bytearray()
        abm_buf_len = 0
        for f2 in range(cutoff):
            abm_buf.append(encode_buf[point])
            point += 1
            abm_buf_len += 1
            if abm_buf_len >= cutoff or point >= Des_len:
                break

        if f == total_number - 1:
            str_abm = "AIBBM," + str(total_number) + "," + str(number) + "," + str(
                sequentialMessageIdentifier) + ",0,14," + abm_buf.decode(
                'utf-8') + "," + str(fill_bits)
        else:
            str_abm = "AIBBM," + str(total_number) + "," + str(number) + "," + str(
                sequentialMessageIdentifier) + ",0,14," + abm_buf.decode(
                'utf-8') + ",0"

        result += '!' + str_abm + '*' + get_check_sum(str_abm.encode()) + '\r\n'
        number += 1

    return result
