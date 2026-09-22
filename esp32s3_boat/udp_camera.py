import socket
import cv2
import numpy as np
import struct

UDP_IP = "0.0.0.0"
UDP_PORT = 7022

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"UDP receiver listening on {UDP_IP}:{UDP_PORT}")

    frame_buffer = {}
    expected_frame_id = None
    packet_count = 0

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            packet_count += 1
            
            # 检查数据长度是否足够解析头部
            if len(data) < 10:
                print(f"数据包太短: {len(data)} 字节，跳过...")
                continue

            # 解析头部信息
            try:
                frame_id = struct.unpack('<I', data[0:4])[0]
                total_packets = struct.unpack('<H', data[4:6])[0]
                packet_idx = struct.unpack('<H', data[6:8])[0]
                packet_len = struct.unpack('<H', data[8:10])[0]
            except struct.error as e:
                print(f"解包错误: {e}，跳过此数据包...")
                continue

            # 验证解析的数据是否合理
            if total_packets <= 0 or total_packets > 1000:
                print(f"无效的总包数: {total_packets}，跳过...")
                continue
                
            if packet_idx >= total_packets:
                print(f"包索引({packet_idx})超出范围({total_packets})，跳过...")
                continue
                
            if packet_len <= 0 or packet_len > 1472:
                print(f"无效的包长度: {packet_len}，跳过...")
                continue

            # 检查数据长度是否与声明的包长度一致
            if len(data) < 10 + packet_len:
                print(f"数据长度不足: 实际{len(data)}, 需要{10 + packet_len}, 跳过...")
                continue

            packet_data = data[10:10+packet_len]

            # 如果这是新帧的第一包，清空之前的缓冲区
            if frame_id != expected_frame_id:
                expected_frame_id = frame_id
                frame_buffer.clear()
                print(f"开始新帧: ID={frame_id}, 总包数={total_packets}")
                # 添加一个简单的帧ID验证（可选）
                if frame_id == 0:
                    print("警告: 接收到帧ID为0，可能有同步问题")
                    
            frame_buffer[packet_idx] = packet_data

            # 检查是否收集齐了所有包
            if len(frame_buffer) == total_packets:
                print(f"帧完成: ID={frame_id}, 已收集{len(frame_buffer)}个包")
                jpeg_data = b''.join(frame_buffer[i] for i in sorted(frame_buffer.keys()))
                img = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                # 水平镜像（左右翻转）
                # img = cv2.flip(img, 1)
                # 垂直镜像（上下翻转）- 使图像从倒立变正立
                img = cv2.flip(img, 0)
                if img is not None:
                    # 显示图像前检查尺寸
                    if img.shape[0] > 0 and img.shape[1] > 0:
                        cv2.imshow("XIAO ESP32S3 Sense High-FPS Stream", img)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    else:
                        print("解码成功但图像尺寸异常")
                else:
                    print("解码失败")
                frame_buffer.clear()
                expected_frame_id = None  # 重置期望的帧ID
        except Exception as e:
            print(f"其他错误: {e}")
            # 重置缓冲区以避免累积错误
            frame_buffer.clear()
            expected_frame_id = None

    sock.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()