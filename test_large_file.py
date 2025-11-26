import xml.etree.ElementTree as ET
import json
import os
import uuid

# 模拟大文件处理流程，测试是否能正确生成多个step元素
def test_large_file_save():
    # 创建XML根元素
    root = ET.Element("root")
    steps_elem = ET.SubElement(root, "steps")
    
    # 1. 模拟大文件处理场景
    print("=== 测试1: 大文件处理逻辑 ===")
    
    # 模拟大文件处理后的processed_data（5行数据）
    processed_data = [
        ["0x0102", "0x0304"],
        ["0x0506", "0x0708"],
        ["0x090A", "0x0B0C"],
        ["0x0D0E", "0x0F10"],
        ["0x1112", "0x1314"]
    ]
    
    # 模拟step数据
    base_data = {"time": 100.0, "name": "周期GLINK大文件"}
    type_data = {"protocol_type": 0, "file_path": "large_file.txt", "period": 5.0}
    expand_data = {"periodic_group_id": f"periodic_{uuid.uuid4().hex}", "periodic_file_path": "large_file.txt"}
    protocol_data = {"protocol_type": 0}
    
    # 模拟大文件处理逻辑
    step_type = 1  # 周期GLINK类型
    periodic_file_path = "large_file.txt"
    
    print(f"检测到大文件: {periodic_file_path}")
    print(f"大文件包含 {len(processed_data)} 行数据，开始处理...")
    
    # 设置第一行数据作为预览，并标记为大文件处理过
    if processed_data:
        type_data["data_region"] = processed_data[0]
        expand_data["periodic_file_data"] = processed_data
        expand_data["periodic_file_line_count"] = len(processed_data)  # 关键修复：标记为大文件处理过
        
    print(f"大文件处理完成，共 {len(processed_data)} 行")
    
    # 立即展开步骤
    print(f"立即展开步骤: {len(processed_data)} 行数据...")
    file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
    period_value = type_data.get("period")
    group_id = expand_data.get("periodic_group_id")
    
    # 第一行的time来自base_step_data中的time
    first_time = float(base_data.get("time", 0.0))
    period = float(period_value if period_value not in (None, "") else 0.0)
    
    print(f"展开参数: first_time={first_time}, period={period}")
    
    # 限制展开的行数
    max_rows = min(1000, len(processed_data))
    print(f"展开前 {max_rows} 行数据")
    
    # 循环创建step元素
    for row_idx, row_data in enumerate(processed_data[:max_rows]):
        step_elem = ET.SubElement(steps_elem, "step")
        print(f"创建第 {row_idx+1} 个step元素，时间: {first_time + row_idx * period}")
        
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
        
        # 设置当前行的数据
        type_data_copy["data_region"] = row_data
        
        for k, v in type_data_copy.items():
            field = ET.SubElement(type_elem, k)
            if k == "data_region":
                field.text = json.dumps(v, ensure_ascii=False)
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
    
    print(f"步骤展开完成，共生成 {max_rows} 个步骤")
    print("=" * 50)
    
    # 2. 模拟常规周期GLINK处理逻辑（验证不会重复处理）
    print("=== 测试2: 常规周期GLINK处理逻辑（应跳过已处理的大文件） ===")
    
    # 模拟常规周期GLINK步骤（应该被跳过，因为已经处理过）
    periodic_file_data = processed_data
    
    # 检查是否已被大文件处理过
    if step_type == 1 and periodic_file_data and not expand_data.get("periodic_file_line_count"):
        print("开始处理常规周期GLINK步骤...")
        # 这里的代码应该不会执行，因为我们已经设置了periodic_file_line_count
    else:
        if expand_data.get("periodic_file_line_count"):
            print("检测到该步骤已被大文件处理逻辑处理过，跳过常规处理")
        else:
            print("不满足常规周期GLINK处理条件，跳过")
    
    print("=" * 50)
    
    # 3. 模拟普通步骤处理逻辑（验证不会覆盖）
    print("=== 测试3: 普通步骤处理逻辑（应跳过周期GLINK步骤） ===")
    
    if step_type != 1:
        print("开始处理普通步骤...")
        # 这里的代码应该不会执行，因为step_type == 1
    else:
        print("检测到该步骤是周期GLINK步骤，跳过普通步骤处理")
    
    print("=" * 50)
    
    # 4. 检查结果
    steps = root.findall(".//step")
    print(f"\n=== 测试结果 ===")
    print(f"生成的step元素总数: {len(steps)}")
    print(f"期望的step元素总数: {len(processed_data)}")
    
    # 验证结果
    if len(steps) == len(processed_data):
        print("✓ 测试通过：生成了正确数量的step元素")
    else:
        print("✗ 测试失败：生成的step元素数量不正确")
    
    # 将XML保存到文件
    xml_str = ET.tostring(root, encoding="utf-8", method="xml")
    with open("test_large_file_output.xml", "wb") as f:
        f.write(xml_str)
    
    print(f"\nXML文件已保存到 test_large_file_output.xml")
    
    # 打印每个step的关键信息
    print("\n每个step的关键信息：")
    for i, step in enumerate(steps):
        time = step.find(".//base/time").text
        data_region = step.find(".//type/data_region").text
        print(f"Step {i+1}: time={time}, data_region={data_region}")
    
    return len(steps)

if __name__ == "__main__":
    test_large_file_save()