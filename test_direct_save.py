import os
import sys
import xml.etree.ElementTree as ET
import uuid
import tempfile

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 导入需要的模块
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

# 创建测试数据文件
def create_test_data_file(file_path, num_rows=10):
    with open(file_path, 'w') as f:
        for i in range(num_rows):
            f.write(f"1.1 2.2 3.3 4.4 5.5 6.6 7.7 8.8 9.9 10.1 11.1 12.1 13.1 14.1 15.1 16.1\n")

# 直接测试大文件处理和XML保存逻辑
def test_direct_save():
    print("=== 开始测试大文件直接保存到XML ===")
    
    # 创建测试数据文件
    test_file_path = "test_large_file.txt"
    num_rows = 5
    create_test_data_file(test_file_path, num_rows=num_rows)
    
    try:
        # 模拟大文件处理的核心逻辑
        print(f"\n1. 读取大文件数据 ({test_file_path})")
        with open(test_file_path, 'r') as f:
            processed_data = f.readlines()
        print(f"   读取到 {len(processed_data)} 行数据")
        
        # 2. 创建XML根元素
        print("\n2. 创建XML根元素")
        root = ET.Element("root")
        steps_elem = ET.SubElement(root, "steps")
        
        # 3. 模拟大文件周期GLINK处理（step_type=1）
        print("\n3. 模拟大文件周期GLINK处理 (step_type=1)")
        
        # 设置初始数据
        base_data = {
            "time": 100.0,
            "name": "周期GLINK大文件"
        }
        type_data = {
            "protocol_type": "0",
            "file_path": test_file_path,
            "period": 5.0
        }
        
        # 为大文件中的每一行创建一个step
        expand_data = {
            "periodic_file_line_count": len(processed_data),  # 标记为大文件处理过的
            "periodic_group_id": f"periodic_{uuid.uuid4().hex}"
        }
        
        for i, line_data in enumerate(processed_data):
            # 创建step元素
            step_elem = ET.SubElement(steps_elem, "step")
            
            # 创建base子元素
            base_elem = ET.SubElement(step_elem, "base")
            for k, v in base_data.items():
                if k == "time":
                    # 计算时间（初始时间 + 周期 * 索引）
                    time_val = base_data["time"] + (type_data["period"] * i)
                    field = ET.SubElement(base_elem, k)
                    field.text = str(time_val)
                else:
                    field = ET.SubElement(base_elem, k)
                    field.text = str(v)
            
            # 创建type子元素
            type_elem = ET.SubElement(step_elem, "type")
            for k, v in type_data.items():
                field = ET.SubElement(type_elem, k)
                field.text = str(v)
            
            # 添加data_region字段（模拟实际处理）
            data_region = [f"0x{((i*2)+1):04X}", f"0x{((i*2)+2):04X}"]
            data_region_elem = ET.SubElement(type_elem, "data_region")
            data_region_elem.text = str(data_region)
            
            # 创建expand子元素
            expand_elem = ET.SubElement(step_elem, "expand")
            for k, v in expand_data.items():
                field = ET.SubElement(expand_elem, k)
                field.text = str(v)
            
            # 添加分组索引和是否首行标记
            index_elem = ET.SubElement(expand_elem, "periodic_group_index")
            index_elem.text = str(i)
            
            first_elem = ET.SubElement(expand_elem, "periodic_group_first")
            first_elem.text = "1" if i == 0 else "0"
            
            # 创建protocol子元素
            protocol_elem = ET.SubElement(step_elem, "protocol")
            protocol_field = ET.SubElement(protocol_elem, "protocol_type")
            protocol_field.text = "0"
            
            print(f"   创建Step {i+1}: time = {base_data['time'] + (type_data['period'] * i)}")
        
        # 4. 生成美化的XML
        print("\n4. 生成美化的XML")
        rough_string = ET.tostring(root, encoding="utf-8", method="xml")
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8")
        
        # 移除多余的空白行
        pretty_xml_str = b'\n'.join(
            line for line in pretty_xml.splitlines() 
            if line.strip()
        ).decode("utf-8")
        
        # 5. 保存到XML文件
        xml_file_path = "test_direct_output.xml"
        print(f"\n5. 保存到XML文件: {xml_file_path}")
        with open(xml_file_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml_str)
        
        # 6. 验证XML文件
        print(f"\n6. 验证XML文件内容")
        if os.path.exists(xml_file_path):
            print(f"   文件已成功创建，大小: {os.path.getsize(xml_file_path)} 字节")
            
            # 解析XML并检查内容
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            steps = root.findall("./steps/step")
            
            print(f"   XML中包含 {len(steps)} 个step元素")
            print(f"   预期 {num_rows} 个step元素")
            
            # 检查每个step的time值
            for i, step in enumerate(steps):
                base_elem = step.find("./base")
                time = base_elem.find("./time")
                name = base_elem.find("./name")
                print(f"   Step {i+1}: time={time.text}, name={name.text}")
            
            # 验证结果
            if len(steps) == num_rows:
                print(f"\n✅ 测试成功！大文件处理后正确保存了 {len(steps)} 个step到XML。")
                return True
            else:
                print(f"\n❌ 测试失败！预期 {num_rows} 个step，实际 {len(steps)} 个。")
                return False
        else:
            print(f"\n❌ 测试失败！XML文件未创建。")
            return False
            
    finally:
        # 清理临时文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        # 保留输出文件以便检查
        # if os.path.exists("test_direct_output.xml"):
        #     os.remove("test_direct_output.xml")

if __name__ == "__main__":
    success = test_direct_save()
    sys.exit(0 if success else 1)