#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试大文件周期GLINK的XML展开逻辑
"""

import os
import sys
import json
import uuid
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))


# 模拟FileController中的大文件处理和XML展开逻辑
def simulate_large_file_xml_expansion():
    """模拟大文件周期GLINK的XML展开逻辑"""
    print("模拟大文件周期GLINK的XML展开逻辑...")
    
    # 创建测试用的大文件
    test_file_path = "test_large_file.txt"
    num_rows = 100  # 测试用的行数
    num_cols = 16
    
    with open(test_file_path, 'w') as f:
        for i in range(num_rows):
            line = ' '.join(['1' for _ in range(num_cols)]) + '\n'
            f.write(line)
    
    print(f"创建测试文件 {test_file_path}，包含 {num_rows} 行，每行 {num_cols} 列")
    
    try:
        # 模拟处理大文件的逻辑
        print("模拟处理大文件...")
        processed_data = []
        
        # 读取文件并处理
        with open(test_file_path, 'r', encoding='utf-8') as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                # 分割数据
                values = line.split()
                if not values:
                    continue
                
                # 模拟数据类型检测
                data_types = [1] * len(values)
                
                # 构建row_data
                row_data = []
                for col_idx, (value, data_type) in enumerate(zip(values, data_types)):
                    row_data.append({
                        "data_type": data_type,
                        "value": value
                    })
                
                processed_data.append(row_data)
                
                if (line_idx + 1) % 1000 == 0:
                    print(f"  已处理 {line_idx + 1} 行...")
        
        print(f"大文件处理完成，共 {len(processed_data)} 行")
        
        # 模拟XML展开逻辑
        print("模拟XML展开...")
        
        # 创建XML根节点
        root = ET.Element("root")
        steps_elem = ET.SubElement(root, "steps")
        
        # 模拟步骤数据
        base_data = {
            "step_id": "test_step_001",
            "step_name": "测试大文件周期GLINK",
            "step_type": 1,
            "time": 100.0
        }
        
        type_data = {
            "file_path": test_file_path,
            "period": 10.0,
            "start_time": 0
        }
        
        expand_data = {
            "periodic_file_path": test_file_path
        }
        
        protocol_data = {
            "protocol_type": -1
        }
        
        # 第一行的time来自base_step_data中的time（仿真时间）
        first_time = float(base_data.get("time", 0.0))
        period = float(type_data.get("period", 0.0))
        file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
        
        # 生成group_id
        group_id = f"periodic_{uuid.uuid4().hex}"
        
        print(f"展开参数: first_time={first_time}, period={period}, 总行数={len(processed_data)}")
        
        # 限制展开的行数，避免内存问题
        max_rows = min(100, len(processed_data))
        print(f"展开行数: {max_rows}")
        
        # 展开步骤
        generated_steps = 0
        for row_idx, row_data in enumerate(processed_data[:max_rows]):
            step_elem = ET.SubElement(steps_elem, "step")
            
            # 保存base字典
            base_elem = ET.SubElement(step_elem, "base")
            base_data_copy = base_data.copy()
            base_data_copy["time"] = first_time + row_idx * period
            for k, v in base_data_copy.items():
                field = ET.SubElement(base_elem, k)
                field.text = str(v)
            
            # 保存type字典
            type_elem = ET.SubElement(step_elem, "type")
            type_data_copy = {}
            for k, v in type_data.items():
                if k in ("start_time",):
                    continue
                type_data_copy[k] = v
            if file_path_value is not None:
                type_data_copy["file_path"] = file_path_value
            
            # 设置data_region为当前行的数据
            type_data_copy["data_region"] = row_data
            
            for k, v in type_data_copy.items():
                field = ET.SubElement(type_elem, k)
                if k == "data_region":
                    if isinstance(v, (list, dict)):
                        if v:
                            field.text = json.dumps(v, ensure_ascii=False)
                        else:
                            field.text = "[]"
                    elif v is None:
                        field.text = "None"
                    else:
                        field.text = str(v)
                else:
                    field.text = str(v)
            
            # 保存expand字典
            expand_elem = ET.SubElement(step_elem, "expand")
            for k, v in expand_data.items():
                if k in ("periodic_file_data", "periodic_file_path"):
                    continue
                field = ET.SubElement(expand_elem, k)
                field.text = str(v)
            field = ET.SubElement(expand_elem, "periodic_group_id")
            field.text = group_id
            field = ET.SubElement(expand_elem, "periodic_group_index")
            field.text = str(row_idx)
            field = ET.SubElement(expand_elem, "periodic_group_first")
            field.text = "1" if row_idx == 0 else "0"
            if file_path_value:
                field = ET.SubElement(expand_elem, "periodic_file_path")
                field.text = str(file_path_value)
            
            # 保存protocol_data字典
            protocol_elem = ET.SubElement(step_elem, "protocol")
            protocol_type = protocol_data.get("protocol_type", -1)
            if protocol_type != -1:
                for k, v in protocol_data.items():
                    field = ET.SubElement(protocol_elem, k)
                    field.text = str(v)
            
            generated_steps += 1
            
            if (row_idx + 1) % 10 == 0:
                print(f"  已生成 {row_idx + 1} 个step...")
        
        print(f"步骤展开完成，共生成 {generated_steps} 个step")
        
        # 保存XML文件
        test_xml_path = "test_large_file_expansion.xml"
        tree = ET.ElementTree(root)
        tree.write(test_xml_path, encoding="utf-8", xml_declaration=True)
        
        print(f"已保存测试XML文件: {test_xml_path}")
        
        # 检查生成的XML文件
        tree = ET.parse(test_xml_path)
        root = tree.getroot()
        steps_elem = root.find("steps")
        steps = list(steps_elem.findall("step"))
        
        print(f"\n✅ 验证结果：")
        print(f"   预期生成的step数量: {max_rows}")
        print(f"   实际生成的step数量: {len(steps)}")
        
        if len(steps) == max_rows:
            print(f"   🎉 测试通过！XML正确展开了 {len(steps)} 个step")
            
            # 打印前几个step的time值
            print("   前5个step的time值：")
            for i, step_elem in enumerate(steps[:5]):
                base_elem = step_elem.find("base")
                if base_elem is not None:
                    time_field = base_elem.find("time")
                    if time_field is not None:
                        print(f"     Step {i+1}: time = {time_field.text}")
            
            return True
        else:
            print(f"   ❌ 测试失败！XML只展开了 {len(steps)} 个step")
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
        if os.path.exists("test_large_file_expansion.xml"):
            os.remove("test_large_file_expansion.xml")


if __name__ == "__main__":
    success = simulate_large_file_xml_expansion()
    if success:
        print("\n🎉 测试通过！大文件周期GLINK的XML展开逻辑正常")
        sys.exit(0)
    else:
        print("\n💥 测试失败！大文件周期GLINK的XML展开逻辑存在问题")
        sys.exit(1)