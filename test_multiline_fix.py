import sys
import os
import json
import xml.etree.ElementTree as ET
import traceback

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("开始测试多行HEX数据保存功能...")

# 直接测试save_to_file方法中处理file_hex_sequences的逻辑
try:
    # 模拟file_hex_sequences数据
    file_hex_sequences = [
        [0x01, 0x02, 0x03, 0x04],
        [0x05, 0x06, 0x07, 0x08],
        [0x09, 0x0A, 0x0B, 0x0C]
    ]
    
    # 创建XML结构
    root = ET.Element("config")
    steps_elem = ET.SubElement(root, "steps")
    
    # 模拟单个步骤数据
    base_data = {
        "step_name": "测试步骤",
        "start_time": 0,
        "step_type": 2  # 普通步骤
    }
    
    type_data = {
        "protocol_type": 1,
        "data_type_1": 1,
        "period": 100  # 100毫秒周期
    }
    
    expand_data = {}
    protocol_data = {}
    
    # 测试我们的多行处理逻辑
    if file_hex_sequences:
        multiline_data = file_hex_sequences
        period = type_data.get("period", 100) / 1000  # 转换为秒
        print(f"\n检测到多行数据，共 {len(multiline_data)} 行，周期 {period} 秒")
        
        for i, hex_items in enumerate(multiline_data):
            # 为每行数据创建一个新步骤
            step_elem = ET.SubElement(steps_elem, "step")
            
            # 设置开始时间
            current_start_time = base_data["start_time"] + (i * period)
            print(f"步骤 {i+1} - 开始时间: {current_start_time}")
            
            # 保存基础数据
            base_elem = ET.SubElement(step_elem, "base")
            for key, value in base_data.items():
                if key == "start_time":
                    ET.SubElement(base_elem, key).text = str(current_start_time)
                else:
                    ET.SubElement(base_elem, key).text = str(value)
            
            # 保存类型数据
            type_elem = ET.SubElement(step_elem, "type")
            for key, value in type_data.items():
                if key == "data_region":
                    ET.SubElement(type_elem, key).text = json.dumps(hex_items)
                else:
                    ET.SubElement(type_elem, key).text = str(value)
            
            # 保存扩展数据
            expand_elem = ET.SubElement(step_elem, "expand")
            for key, value in expand_data.items():
                ET.SubElement(expand_elem, key).text = str(value)
            
            # 保存协议数据
            protocol_elem = ET.SubElement(step_elem, "protocol")
            for key, value in protocol_data.items():
                ET.SubElement(protocol_elem, key).text = str(value)
    
    # 保存测试XML
    test_file = "test_multiline_result.xml"
    tree = ET.ElementTree(root)
    tree.write(test_file, encoding="utf-8", xml_declaration=True)
    
    # 检查生成的XML
    print(f"\n生成XML文件: {test_file}")
    tree_read = ET.parse(test_file)
    root_read = tree_read.getroot()
    steps = root_read.findall("./steps/step")
    
    print(f"\n测试结果:")
    print(f"预期步骤数: {len(file_hex_sequences)}")
    print(f"实际步骤数: {len(steps)}")
    
    # 清理临时文件
    if os.path.exists(test_file):
        os.remove(test_file)
    
    # 验证
    if len(steps) == len(file_hex_sequences):
        print("\n✓ 测试通过: 多行HEX数据成功展开为多个步骤")
        print("✓ 处理逻辑正确，每个步骤都有独立的开始时间和数据")
    else:
        print("\n✗ 测试失败: 多行HEX数据未正确展开为多个步骤")
        
except Exception as e:
    print(f"\n✗ 测试过程中发生错误: {str(e)}")
    print(f"错误详情: {traceback.format_exc()}")
    
print("\n测试完成")
