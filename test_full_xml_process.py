import os
import json
import xml.etree.ElementTree as ET
import uuid

# 创建一个完整的测试，模拟FileController中的save_to_xml方法的核心逻辑
def test_full_xml_process():
    # 模拟大文件处理后的数据
    processed_data = []
    for i in range(5):  # 创建5行测试数据
        row = [f"{i}_{j}" for j in range(4)]
        processed_data.append(row)
    
    # 模拟步骤数据
    class MockStep:
        def __init__(self, base_data, type_data):
            self.base_data = base_data
            self.type_data = type_data
        
        def get_base_step_data(self):
            return self.base_data
        
        def get_type_step_data(self):
            return self.type_data
    
    # 创建模拟步骤
    base_data = {
        "step_index": "1",
        "time": "100.0",
        "step_name": "测试步骤",
        "step_comment": "测试周期GLINK",
        "step_type": "1"
    }
    
    type_data = {
        "step_type": "1",
        "file_path": "test_file.txt",
        "period": "10.0",
        "start_time": "100.0"
    }
    
    expand_data = {
        "periodic_file_path": "test_file.txt",
        "periodic_file_data": processed_data,
        "periodic_file_line_count": len(processed_data)  # 标记为大文件处理结果
    }
    
    protocol_data = {
        "protocol_type": "-1"
    }
    
    step = MockStep(base_data, type_data)
    
    # 模拟save_to_xml中的核心逻辑
    print("开始模拟完整的XML保存流程...")
    
    # 创建根元素
    root_elem = ET.Element("steps")
    steps_elem = root_elem
    
    # 模拟大文件处理后的立即展开
    print("\n=== 模拟大文件处理后的立即展开 ===")
    
    # 提取参数
    step_type = int(base_data.get("step_type", 0))
    periodic_file_path = expand_data.get("periodic_file_path")
    periodic_file_data = expand_data.get("periodic_file_data")
    periodic_file_line_count = expand_data.get("periodic_file_line_count")
    
    print(f"step_type={step_type}, periodic_file_path={periodic_file_path}")
    print(f"periodic_file_data存在: {periodic_file_data is not None}")
    print(f"periodic_file_line_count={periodic_file_line_count}")
    
    # 检查是否需要立即展开（大文件处理后）
    if step_type == 1 and periodic_file_data and periodic_file_line_count:
        print("检测到大文件处理结果，立即展开步骤...")
        
        file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
        period_value = type_data.get("period")
        group_id = expand_data.get("periodic_group_id")
        
        if not group_id:
            group_id = f"periodic_{uuid.uuid4().hex}"
            expand_data["periodic_group_id"] = group_id
        
        if file_path_value:
            expand_data["periodic_file_path"] = file_path_value
            type_data["file_path"] = file_path_value
        
        # 第一行的time来自base_step_data中的time
        first_time = float(base_data.get("time", 0.0))
        period = float(period_value if period_value not in (None, "") else 0.0)
        
        print(f"展开参数: first_time={first_time}, period={period}, 数据行数={len(processed_data)}")
        
        # 限制展开的行数
        max_rows = min(1000, len(processed_data))
        
        # 循环展开步骤
        for row_idx, row_data in enumerate(processed_data[:max_rows]):
            step_elem = ET.SubElement(steps_elem, "step")
            
            # 保存base字典（更新time字段）
            base_elem = ET.SubElement(step_elem, "base")
            base_data_copy = base_data.copy()
            base_data_copy["time"] = first_time + row_idx * period
            for k, v in base_data_copy.items():
                field = ET.SubElement(base_elem, k)
                field.text = str(v)
            
            # 保存type字典（更新data_region）
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
            
            print(f"生成Step {row_idx + 1}: time={first_time + row_idx * period}, data_region={row_data}")
        
        print(f"\n大文件立即展开完成，共生成 {max_rows} 个步骤")
        
        # 模拟跳过常规保存
        print("\n=== 跳过常规保存步骤 ===")
        
    # 模拟常规保存步骤
    print("\n=== 模拟常规保存步骤 ===")
    
    # 检查常规保存条件（非大文件情况）
    if step_type == 1 and periodic_file_data and not expand_data.get("periodic_file_line_count"):
        print("检测到常规周期GLINK，开始展开...")
        # 这里的逻辑不会执行，因为我们已经设置了periodic_file_line_count
    else:
        print("常规保存条件不满足，跳过")
    
    # 保存XML文件
    xml_file_path = os.path.join(os.path.dirname(__file__), "full_test_output.xml")
    tree = ET.ElementTree(root_elem)
    ET.indent(tree, space="  ", level=0)
    tree.write(xml_file_path, encoding="utf-8", xml_declaration=True)
    
    print(f"\nXML文件生成成功: {xml_file_path}")
    
    # 验证XML文件
    print("\n验证XML文件内容...")
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    steps = root.findall("step")
    print(f"XML文件中包含 {len(steps)} 个step元素")
    
    if len(steps) == len(processed_data):
        print("✓ 测试通过: XML文件中保存了正确数量的step")
        # 打印每个step的信息
        print("\n所有step的信息:")
        for i, step in enumerate(steps):
            base = step.find("base")
            time = base.find("time").text
            type_elem = step.find("type")
            data_region = type_elem.find("data_region").text
            print(f"Step {i+1}: time={time}, data_region={data_region}")
        return True
    else:
        print("✗ 测试失败: XML文件中step数量不正确")
        return False

if __name__ == "__main__":
    test_full_xml_process()
