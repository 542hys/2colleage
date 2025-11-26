import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入CRC计算函数
from utils.protocol_template_utils import calc_crc_tail_metrics

def test_time_timestamp_conversion():
    """测试时间到时间戳的转换"""
    print("\n测试时间到时间戳的转换:")
    
    # 测试案例：时间值 -> 时间戳（毫秒）
    test_cases = [
        (1.000, 0x000003E8),  # 1.000秒 -> 1000毫秒
        (2.000, 0x000007D0),  # 2.000秒 -> 2000毫秒
        (3.500, 0x00000DAC),  # 3.500秒 -> 3500毫秒
    ]
    
    for time_val, expected_ms in test_cases:
        timestamp_ms = int(round(time_val * 1000))
        time_low = timestamp_ms & 0xFFFF
        time_high = (timestamp_ms >> 16) & 0xFFFF
        
        print(f"时间: {time_val:.3f}秒 -> 毫秒: {timestamp_ms} (0x{timestamp_ms:08X})")
        print(f"  拆分后 - 高16位: 0x{time_high:04X}, 低16位: 0x{time_low:04X}")

def test_frame_count_calculation():
    """测试帧计数计算"""
    print("\n测试帧计数计算:")
    
    # 测试行索引到帧计数的转换
    for line_idx in range(5):
        frame_count = (line_idx + 1) & 0xFFFF
        print(f"行索引: {line_idx} -> 帧计数: 0x{frame_count:04X}")

def test_crc_calculation():
    """测试CRC计算"""
    print("\n测试CRC计算:")
    
    # 测试数据区CRC计算
    test_data_regions = [
        "0x0102",
        "0x0304", 
        "0x0506",
    ]
    
    for data_region in test_data_regions:
        metrics = calc_crc_tail_metrics(data_region)
        crc_value = metrics.get("overrides", {}).get("数据区crc校验和", "0x0000")
        print(f"数据区: {data_region} -> CRC: {crc_value}")

def simulate_glink_export():
    """模拟GLINK导出过程"""
    print("\n模拟GLINK导出过程:")
    
    # 模拟周期GLINK数据
    base_time = 1.0
    period = 1.0
    sequences = [
        ["0x0000", "0x03E8", "0x0000", "0x0001", "0x0000", "0x0001", "0x0102", "0x0000"],
        ["0x0000", "0x03E8", "0x0000", "0x0001", "0x0000", "0x0001", "0x0304", "0x0000"],
        ["0x0000", "0x03E8", "0x0000", "0x0001", "0x0000", "0x0001", "0x0506", "0x0000"]
    ]
    
    print("\n导出的GLINK数据:")
    print("时间(秒)\t时间高\t时间低\t控制字\t消息ID\t帧计数\t数据\tCRC")
    
    for line_idx, seq in enumerate(sequences):
        time_val = base_time + period * line_idx
        
        # 1. 计算时间戳
        timestamp_ms = int(round(time_val * 1000))
        time_low = timestamp_ms & 0xFFFF
        time_high = (timestamp_ms >> 16) & 0xFFFF
        
        # 2. 计算帧计数
        frame_count = (line_idx + 1) & 0xFFFF
        
        # 3. 计算CRC
        data_region = seq[6]  # 数据区在索引6
        metrics = calc_crc_tail_metrics(data_region)
        crc_value = metrics.get("overrides", {}).get("数据区crc校验和", "0x0000")
        
        # 创建输出行
        output_seq = seq.copy()
        output_seq[0] = f"0x{time_high:04X}"  # 更新时间高16位
        output_seq[1] = f"0x{time_low:04X}"   # 更新时间低16位
        output_seq[4] = f"0x{frame_count:04X}" # 更新帧计数
        output_seq[-1] = crc_value            # 更新CRC
        
        # 格式化输出
        time_str = f"{time_val:.3f}"
        data_str = "\t".join(output_seq)
        print(f"{time_str}\t{data_str}")

def test_glink_export():
    """测试GLINK导出功能"""
    print("开始测试GLINK导出功能...")
    
    # 运行各项测试
    test_time_timestamp_conversion()
    test_frame_count_calculation()
    test_crc_calculation()
    simulate_glink_export()
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_glink_export()
