#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试大文件周期GLINK处理后的XML展开功能
"""

import os
import sys
import json
import uuid
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from controllers.file_controller import FileController
from PyQt5.QtWidgets import QApplication


def test_large_file_xml_expansion():
    """测试大文件周期GLINK处理后的XML展开"""
    print("测试大文件周期GLINK处理后的XML展开功能...")
    
    # 创建测试用的大文件
    test_file_path = "test_large_file.txt"
    num_rows = 100  # 测试用的行数，实际文件有160000行
    num_cols = 16
    
    with open(test_file_path, 'w') as f:
        for i in range(num_rows):
            line = ' '.join(['1' for _ in range(num_cols)]) + '\n'
            f.write(line)
    
    print(f"创建测试文件 {test_file_path}，包含 {num_rows} 行，每行 {num_cols} 列")
    
    try:
        # 创建应用程序实例
        app = QApplication([])
        
        # 创建FileController实例
        file_controller = FileController(None)
        
        # 模拟一个包含大文件周期GLINK步骤的流程数据
        test_data = {
            "path_setting": {
                "project_path": os.getcwd(),
                "data_path": os.path.join(os.getcwd(), "data")
            },
            "global_params": {
                "simulation_time": 10000,
                "time_unit": "ms"
            },
            "steps": []
        }
        
        # 添加一个大文件周期GLINK步骤
        step = {
            "base": {
                "step_id": "test_step_001",
                "step_name": "测试大文件周期GLINK",
                "step_type": 1,  # GLINK周期类型
                "time": 100.0
            },
            "type": {
                "file_path": test_file_path,
                "period": 10.0,
                "start_time": 0
            },
            "expand": {
                "periodic_file_path": test_file_path
            },
            "protocol": {
                "protocol_type": -1
            }
        }
        
        test_data["steps"].append(step)
        
        # 保存到临时XML文件
        test_xml_path = "test_large_file_expansion.xml"
        file_controller.save_to_file(test_xml_path, test_data)
        
        print(f"已保存测试XML文件: {test_xml_path}")
        
        # 检查XML文件中的step数量
        tree = ET.parse(test_xml_path)
        root = tree.getroot()
        steps_elem = root.find("steps")
        
        if steps_elem is None:
            print("❌ 错误：XML文件中没有找到steps元素")
            return False
        
        steps = list(steps_elem.findall("step"))
        print(f"XML文件中包含 {len(steps)} 个step")
        
        if len(steps) > 1:
            print("✅ 成功：XML文件中包含多个step")
            
            # 打印前几个step的信息
            print("前5个step的time值：")
            for i, step_elem in enumerate(steps[:5]):
                base_elem = step_elem.find("base")
                if base_elem is not None:
                    time_field = base_elem.find("time")
                    if time_field is not None:
                        print(f"  Step {i+1}: time = {time_field.text}")
            
            return True
        else:
            print("❌ 失败：XML文件中只有一个或零个step")
            
            # 打印XML文件内容用于调试
            print("XML文件内容：")
            tree.write(sys.stdout, encoding="utf-8", xml_declaration=True)
            
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"已删除测试文件: {test_file_path}")
        if os.path.exists(test_xml_path):
            os.remove(test_xml_path)
            print(f"已删除测试XML文件: {test_xml_path}")


if __name__ == "__main__":
    success = test_large_file_xml_expansion()
    if success:
        print("\n🎉 测试通过！大数据XML展开多个step功能正常")
        sys.exit(0)
    else:
        print("\n💥 测试失败！大数据XML只输出一个step的问题未解决")
        sys.exit(1)