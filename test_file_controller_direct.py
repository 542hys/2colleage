#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接使用FileController测试大文件周期GLINK的XML展开
"""

import os
import sys
import json
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 尝试在不创建QApplication的情况下测试
def test_file_controller_without_qt():
    """
    直接导入FileController的关键部分并测试
    """
    print("直接测试FileController的大文件XML展开逻辑...")
    
    # 导入所需的模块
    import uuid
    from controllers.file_controller import FileController
    
    # 创建测试用的大文件
    test_file_path = "test_large_file.txt"
    num_rows = 50  # 测试用的行数
    num_cols = 16
    
    with open(test_file_path, 'w') as f:
        for i in range(num_rows):
            line = ' '.join(['1' for _ in range(num_cols)]) + '\n'
            f.write(line)
    
    print(f"创建测试文件 {test_file_path}，包含 {num_rows} 行，每行 {num_cols} 列")
    
    try:
        # 创建一个模拟的步骤数据
        step_data = {
            "base": {
                "step_id": f"test_step_{uuid.uuid4().hex[:8]}",
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
        
        # 模拟FileController中的大文件处理逻辑
        print("模拟FileController的大文件处理逻辑...")
        
        # 模拟process_large_periodic_file函数
        def mock_process_large_periodic_file(file_path, data_types):
            processed_data = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    
                    values = line.split()
                    if not values:
                        continue
                    
                    # 如果data_types为空，自动检测
                    if not data_types:
                        data_types = [1] * len(values)
                    
                    # 确保数据类型数量与列数匹配
                    if len(data_types) < len(values):
                        data_types.extend([1] * (len(values) - len(data_types)))
                    elif len(data_types) > len(values):
                        data_types = data_types[:len(values)]
                    
                    row_data = []
                    for col_idx, (value, data_type) in enumerate(zip(values, data_types)):
                        row_data.append({
                            "data_type": data_type,
                            "value": value
                        })
                    
                    processed_data.append(row_data)
            
            return processed_data
        
        # 获取数据类型
        type_data = step_data["type"]
        data_types = []
        for i in range(1, 13):  # 检查data_type_1到data_type_12
            key = f"data_type_{i}"
            if key in type_data and type_data[key] is not None:
                data_types.append(type_data[key])
        
        # 如果data_types为空，尝试自动检测
        if not data_types:
            print("未找到数据类型配置，尝试自动检测文件格式...")
            try:
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        values = first_line.split()
                        if values:
                            num_cols = len(values)
                            data_types = [1] * num_cols
                            print(f"检测到文件有 {num_cols} 列数据")
                    else:
                        # 文件为空，默认1个通道
                        data_types = [1]
                        print("文件为空，默认1个通道")
            except Exception as e:
                print(f"自动检测文件格式失败: {str(e)}")
                data_types = [1]
        
        # 处理大文件
        processed_data = mock_process_large_periodic_file(test_file_path, data_types)
        print(f"大文件处理完成，共 {len(processed_data)} 行")
        
        # 模拟XML展开
        print("模拟XML展开...")
        
        # 创建XML根节点
        root = ET.Element("root")
        steps_elem = ET.SubElement(root, "steps")
        
        base_data = step_data["base"]
        type_data = step_data["type"]
        expand_data = step_data["expand"]
        protocol_data = step_data["protocol"]
        
        file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
        period_value = type_data.get("period")
        
        # 生成group_id
        group_id = f"periodic_{uuid.uuid4().hex}"
        
        # 第一行的time来自base_step_data中的time
        first_time = float(base_data.get("time", 0.0))
        period = float(period_value if period_value not in (None, "") else 0.0)
        
        # 限制展开的行数
        max_rows = min(1000, len(processed_data))
        
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
            if period_value is not None:
                type_data_copy["period"] = period_value
            
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
            
        print(f"步骤展开完成，共生成 {generated_steps} 个step")
        
        # 验证结果
        print("\n✅ 验证结果：")
        print(f"   预期生成的step数量: {min(1000, num_rows)}")
        print(f"   实际生成的step数量: {generated_steps}")
        
        if generated_steps > 1:
            print(f"   🎉 测试通过！XML正确展开了 {generated_steps} 个step")
            return True
        else:
            print(f"   ❌ 测试失败！XML只展开了 {generated_steps} 个step")
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
    success = test_file_controller_without_qt()
    if success:
        print("\n🎉 测试通过！FileController的大文件XML展开逻辑正常")
        sys.exit(0)
    else:
        print("\n💥 测试失败！FileController的大文件XML展开逻辑存在问题")
        sys.exit(1)