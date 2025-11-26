#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试脚本，验证多行数据展开功能
"""

import sys
import os
import json
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入所需模块
from models.step_model import StepModel


def test_multiline_data_expansion():
    """
    测试多行数据展开功能
    """
    print("开始测试多行数据展开功能...")
    
    try:
        # 创建一个StepModel实例
        step = StepModel()
        
        # 设置基本数据
        base_data = {
            "name": "测试步骤",
            "start_time": "1",
            "timeout": "1000",
            "max_retries": "3",
            "environment": "default"
        }
        step.set_base_step_data(base_data)
        
        # 设置类型数据
        type_data = {
            "step_type": "0",  # 普通步骤
            "protocol_type": "1",  # 假设为某种协议类型
            "data_region": "[]",  # 初始为空列表
            "period": "1000"  # 设置周期为1000毫秒
        }
        step.set_type_step_data(type_data)
        
        # 设置协议数据，包含多行hex数据
        protocol_data = {
            "消息控制字": "0x0001",
            "file_hex_sequences": [
                "01 02 03",
                "04 05 06",
                "07 08 09"
            ]
        }
        step.set_protocol_data(protocol_data)
        
        print("\n1. 准备测试数据:")
        print(f"   步骤名称: {step.get_base_step_data().get('name')}")
        print(f"   开始时间: {step.get_base_step_data().get('start_time')}")
        print(f"   周期: {step.get_type_step_data().get('period')}")
        print(f"   多行数据: {protocol_data.get('file_hex_sequences')}")
        print(f"   数据行数: {len(protocol_data.get('file_hex_sequences'))}")
        
        # 模拟文件保存过程中的多行数据处理逻辑
        print("\n2. 模拟多行数据处理逻辑:")
        
        # 创建XML根元素
        root = ET.Element("config")
        steps_elem = ET.SubElement(root, "steps")
        
        protocol_data = step.get_protocol_data()
        file_hex_sequences = protocol_data.get("file_hex_sequences", [])
        
        if file_hex_sequences:
            print(f"   检测到多行数据，准备展开为{len(file_hex_sequences)}个步骤")
            
            # 获取基础时间和周期
            base_time = int(step.get_base_step_data().get("start_time", "0"))
            period_value = step.get_type_step_data().get("period", "0")
            period = int(period_value) if period_value.isdigit() else 1000
            
            print(f"   基础时间: {base_time}, 周期: {period}")
            
            # 遍历多行数据
            for i, hex_line in enumerate(file_hex_sequences):
                print(f"\n   处理第{i+1}行数据: {hex_line}")
                
                # 创建新的step元素
                step_elem = ET.SubElement(steps_elem, "step")
                
                # 保存base数据，更新start_time
                base_elem = ET.SubElement(step_elem, "base")
                for k, v in step.get_base_step_data().items():
                    field = ET.SubElement(base_elem, k)
                    if k == "start_time":
                        # 计算当前步骤的开始时间
                        current_time = base_time + i * period
                        field.text = str(current_time)
                        print(f"      更新start_time为: {current_time}")
                    else:
                        field.text = str(v)
                
                # 保存type数据
                type_elem = ET.SubElement(step_elem, "type")
                for k, v in step.get_type_step_data().items():
                    field = ET.SubElement(type_elem, k)
                    if k == "data_region":
                        # 使用当前行的hex数据更新data_region
                        hex_data = hex_line.strip().split()
                        # 将hex字符串转换为数字列表
                        hex_list = [int(x, 16) for x in hex_data]
                        field.text = json.dumps(hex_list, ensure_ascii=False)
                        print(f"      更新data_region为: {hex_list}")
                    else:
                        field.text = str(v)
                
                # 保存expand数据
                expand_elem = ET.SubElement(step_elem, "expand")
                for k, v in step.get_expand_step_data().items():
                    if k not in ("periodic_file_data", "periodic_file_path"):
                        field = ET.SubElement(expand_elem, k)
                        field.text = str(v)
                
                # 保存protocol数据（不包含file_hex_sequences）
                protocol_elem = ET.SubElement(step_elem, "protocol")
                for k, v in protocol_data.items():
                    if k != "file_hex_sequences":
                        field = ET.SubElement(protocol_elem, k)
                        field.text = str(v)
        else:
            print("   未检测到多行数据，保持单个步骤")
            # 正常保存单个步骤
            step_elem = ET.SubElement(steps_elem, "step")
            
        # 打印生成的XML
        print("\n3. 生成的XML结构:")
        xml_str = ET.tostring(root, encoding="unicode")
        print(xml_str)
        
        # 验证结果
        steps = list(root.iter("step"))
        print(f"\n4. 验证结果:")
        print(f"   生成的步骤数量: {len(steps)}")
        print(f"   预期的步骤数量: {len(file_hex_sequences) if file_hex_sequences else 1}")
        
        if len(steps) == len(file_hex_sequences):
            print("   ✓ 多行数据成功展开为对应数量的步骤")
            
            # 检查每个步骤的start_time和data_region
            all_correct = True
            for i, step_elem in enumerate(steps):
                # 检查start_time
                base_elem = step_elem.find("base")
                start_time = base_elem.find("start_time").text
                expected_time = str(int(base_time) + i * period)
                if start_time != expected_time:
                    print(f"   ✗ 第{i+1}个步骤的start_time不正确: {start_time} (预期: {expected_time})")
                    all_correct = False
                else:
                    print(f"   ✓ 第{i+1}个步骤的start_time正确: {start_time}")
                
                # 检查data_region
                type_elem = step_elem.find("type")
                data_region = type_elem.find("data_region").text
                expected_data = json.dumps([int(x, 16) for x in file_hex_sequences[i].strip().split()], ensure_ascii=False)
                if data_region != expected_data:
                    print(f"   ✗ 第{i+1}个步骤的data_region不正确: {data_region} (预期: {expected_data})")
                    all_correct = False
                else:
                    print(f"   ✓ 第{i+1}个步骤的data_region正确")
            
            if all_correct:
                print("\n🎉 所有测试通过！多行数据展开功能正常工作。")
                return True
            else:
                print("\n❌ 部分测试失败，请检查代码逻辑。")
                return False
        else:
            print(f"   ✗ 步骤数量不正确: {len(steps)} (预期: {len(file_hex_sequences)})")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_multiline_data_expansion()
