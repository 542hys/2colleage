import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from utils.protocol_template_utils import calculate_total_bytes

def test_calculate_total_bytes():
    """测试calculate_total_bytes函数"""
    print("测试calculate_total_bytes函数...")
    
    # 测试用例1: 基本数据类型
    test_data1 = [
        {"data_type": "UINT8", "value": 10},
        {"data_type": "UINT16", "value": 200},
        {"data_type": "UINT32", "value": 1000},
        {"data_type": "FLOAT32", "value": 3.14},
        {"data_type": "STRING", "value": "test"}
    ]
    
    expected1 = 1 + 2 + 4 + 4 + 4  # UINT8(1) + UINT16(2) + UINT32(4) + FLOAT32(4) + STRING(4)
    result1 = calculate_total_bytes(test_data1)
    print(f"测试用例1 - 期望: {expected1}, 实际: {result1}")
    assert result1 == expected1, f"测试用例1失败"
    
    # 测试用例2: 空数据
    test_data2 = []
    result2 = calculate_total_bytes(test_data2)
    print(f"测试用例2 - 期望: 0, 实际: {result2}")
    assert result2 == 0, f"测试用例2失败"
    
    # 测试用例3: 包含未知数据类型
    test_data3 = [
        {"data_type": "UINT8", "value": 10},
        {"data_type": "UNKNOWN", "value": 20}
    ]
    
    expected3 = 1 + 2  # UINT8(1) + UNKNOWN(默认2)
    result3 = calculate_total_bytes(test_data3)
    print(f"测试用例3 - 期望: {expected3}, 实际: {result3}")
    assert result3 == expected3, f"测试用例3失败"
    
    print("所有测试用例通过!")

if __name__ == "__main__":
    try:
        test_calculate_total_bytes()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
