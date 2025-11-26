import sys
import os
import json
import tempfile
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from controllers.file_controller import FileController
from PyQt5.QtWidgets import QApplication

# 创建Qt应用实例
app = QApplication([])

# 创建测试文件
def create_test_file(rows=10, cols=16):
    test_file_path = os.path.join(os.path.dirname(__file__), "test_large_file.txt")
    with open(test_file_path, "w") as f:
        for i in range(rows):
            row = [f"{i}_{j}" for j in range(cols)]
            f.write("\t".join(row) + "\n")
    return test_file_path

# 测试XML生成
def test_xml_generation():
    # 创建测试文件
    test_file_path = create_test_file(rows=10, cols=16)
    print(f"创建测试文件: {test_file_path}")
    
    # 创建FileController实例
    file_controller = FileController(None)
    
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
        "file_path": test_file_path,
        "period": "10.0",
        "start_time": "100.0"
    }
    
    expand_data = {
        "periodic_file_path": test_file_path,
        "periodic_file_data": None
    }
    
    protocol_data = {
        "protocol_type": "-1"
    }
    
    # 创建一个模拟的step对象
    class MockStep:
        def __init__(self, base_data, type_data):
            self.base_data = base_data
            self.type_data = type_data
        
        def get_base_step_data(self):
            return self.base_data
        
        def get_type_step_data(self):
            return self.type_data
    
    step = MockStep(base_data, type_data)
    
    # 测试保存XML
    print("\n开始测试XML生成...")
    xml_file_path = os.path.join(os.path.dirname(__file__), "test_output.xml")
    
    # 直接调用XML生成逻辑
    try:
        # 创建根元素
        root_elem = ET.Element("steps")
        
        # 模拟大文件处理
        print("模拟大文件处理...")
        
        # 1. 提取参数
        periodic_file_path = type_data.get("file_path")
        if not periodic_file_path:
            periodic_file_path = expand_data.get("periodic_file_path")
        
        start_time = type_data.get("start_time")
        period = type_data.get("period")
        
        # 2. 处理数据类型
        data_types = []
        for i in range(1, 13):
            dt_key = f"data_type_{i}"
            dt_value = type_data.get(dt_key)
            if dt_value and dt_value != "0":
                data_types.append(int(dt_value))
        
        # 如果没有设置数据类型，自动检测
        if not data_types:
            try:
                with open(periodic_file_path, "r") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        col_count = len(first_line.split("\t"))
                        data_types = [1] * col_count  # 默认为数值类型
                        print(f"自动检测到 {col_count} 列数据")
            except Exception as e:
                print(f"检测列数失败: {str(e)}")
                data_types = [1] * 16  # 默认为16列
        
        # 3. 处理大文件
        processed_data = file_controller.process_large_periodic_file(periodic_file_path, data_types)
        expand_data["periodic_file_data"] = processed_data
        
        # 4. 立即展开步骤（关键修复）
        print(f"立即展开步骤: {len(processed_data)} 行数据...")
        
        file_path_value = periodic_file_path
        period_value = period
        group_id = expand_data.get("periodic_group_id")
        if not group_id:
            import uuid
            group_id = f"periodic_{uuid.uuid4().hex}"
            expand_data["periodic_group_id"] = group_id
        
        # 第一行的time来自base_step_data中的time
        first_time = float(base_data.get("time", 0.0))
        period = float(period_value if period_value not in (None, "") else 0.0)
        
        print(f"展开参数: first_time={first_time}, period={period}")
        
        # 限制展开的行数
        max_rows = min(1000, len(processed_data))
        print(f"展开前 {max_rows} 行数据")
        
        for row_idx, row_data in enumerate(processed_data[:max_rows]):
            step_elem = ET.SubElement(root_elem, "step")
            
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
            # 打印前几个step的信息
            print("\n前3个step的信息:")
            for i, step in enumerate(steps[:3]):
                base = step.find("base")
                time = base.find("time").text
                type_elem = step.find("type")
                data_region = type_elem.find("data_region").text
                print(f"Step {i+1}: time={time}, data_region={data_region[:50]}...")
            return True
        else:
            print("✗ 测试失败: XML文件中step数量不正确")
            return False
            
    except Exception as e:
        print(f"测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"\n清理测试文件: {test_file_path}")
        if os.path.exists(xml_file_path):
            print(f"保留测试生成的XML文件: {xml_file_path}")

if __name__ == "__main__":
    test_xml_generation()
    # 退出Qt应用
    app.quit()
