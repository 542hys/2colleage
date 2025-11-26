import os
import json
import xml.etree.ElementTree as ET
import uuid

# 创建一个简单的测试，直接模拟大文件处理和XML生成
def test_simple_xml_generation():
    # 模拟大文件处理后的数据
    processed_data = [
        [1.0, 2.0, 3.0, 4.0],
        [5.0, 6.0, 7.0, 8.0],
        [9.0, 10.0, 11.0, 12.0],
        [13.0, 14.0, 15.0, 16.0],
        [17.0, 18.0, 19.0, 20.0]
    ]
    
    # 准备测试数据
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
        "periodic_file_data": processed_data
    }
    
    protocol_data = {
        "protocol_type": "-1"
    }
    
    # 开始生成XML
    print("开始生成XML...")
    
    # 创建根元素
    root_elem = ET.Element("steps")
    
    # 提取参数
    file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
    period_value = type_data.get("period")
    group_id = expand_data.get("periodic_group_id")
    if not group_id:
        group_id = f"periodic_{uuid.uuid4().hex}"
        expand_data["periodic_group_id"] = group_id
    
    # 第一行的time来自base_step_data中的time
    first_time = float(base_data.get("time", 0.0))
    period = float(period_value if period_value not in (None, "") else 0.0)
    
    print(f"展开参数: first_time={first_time}, period={period}, 数据行数={len(processed_data)}")
    
    # 限制展开的行数
    max_rows = min(1000, len(processed_data))
    
    # 循环展开步骤
    for row_idx, row_data in enumerate(processed_data[:max_rows]):
        step_elem = ET.SubElement(root_elem, "step")
        
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
    
    # 保存XML文件
    xml_file_path = os.path.join(os.path.dirname(__file__), "simple_test_output.xml")
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
    
    if len(steps) == len(processed_data[:max_rows]):
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
    test_simple_xml_generation()
