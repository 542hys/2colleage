import os
import sys
import xml.etree.ElementTree as ET
import uuid

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 模拟模型和步骤类
class MockStep:
    def __init__(self):
        self.base_data = {
            "step_type": 1,  # 周期GLINK
            "time": 100.0,
            "name": "测试周期步骤"
        }
        self.type_data = {
            "file_path": "test_file.txt",
            "period": 10.0,
            "data_type_1": 1
        }
        self.expand_data = {
            "periodic_file_path": "test_file.txt"
        }
        self.protocol_data = {
            "protocol_type": 0,
            "消息控制字": "0x0003",
            "数据区": ""
        }
    
    def get_base_step_data(self):
        return self.base_data
    
    def get_type_step_data(self):
        return self.type_data
    
    def get_expand_step_data(self):
        return self.expand_data
    
    def get_protocol_data(self):
        return self.protocol_data
    
    def set_protocol_data(self, data):
        self.protocol_data = data

class MockModel:
    def __init__(self):
        self.path_setting = {}
        self.global_params = {}
        self.steps = []
    
    def reset_dirty(self):
        pass

# 模拟FileController的核心逻辑
def test_save_logic():
    # 创建测试模型和步骤
    model = MockModel()
    step = MockStep()
    model.steps.append(step)
    
    # 模拟大文件处理
    print("模拟大文件处理...")
    processed_data = []
    for i in range(5):
        row_data = [
            {"data_type": 1, "value": f"1.1 + {i}"},
            {"data_type": 2, "value": f"2.2 + {i}"},
            {"data_type": 3, "value": f"3.3 + {i}"}
        ]
        processed_data.append(row_data)
    
    # 设置处理后的数据
    expand_data = step.get_expand_step_data()
    expand_data["periodic_file_data"] = processed_data
    expand_data["periodic_file_line_count"] = len(processed_data)
    
    # 模拟XML生成逻辑
    print("生成XML...")
    root = ET.Element("config")
    
    # 保存path_setting节点
    path_setting_elem = ET.SubElement(root, "path_setting")
    
    # 保存global_params节点
    global_params_elem = ET.SubElement(root, "global_params")
    
    # 保存steps节点
    steps_elem = ET.SubElement(root, "steps")
    
    for step in model.steps:
        # 检查是否是周期GLINK且包含文件数据或文件路径
        step_type = step.get_base_step_data().get("step_type", -1)
        expand_data = step.get_expand_step_data()
        periodic_file_data = expand_data.get("periodic_file_data")
        periodic_file_path = expand_data.get("periodic_file_path")
        
        print(f"处理步骤: step_type={step_type}, periodic_file_data={periodic_file_data is not None}, periodic_file_path={periodic_file_path}")
        
        # 处理大文件情况
        if step_type == 1 and periodic_file_path and periodic_file_data:
            print(f"检测到大文件周期GLINK，包含 {len(periodic_file_data)} 行数据，开始展开...")
            
            # 立即展开步骤
            base_data = step.get_base_step_data()
            type_data = step.get_type_step_data()
            file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
            period_value = type_data.get("period")
            group_id = expand_data.get("periodic_group_id")
            if not group_id:
                group_id = f"periodic_{uuid.uuid4().hex}"
                expand_data["periodic_group_id"] = group_id
            
            # 第一行的time来自base_step_data中的time（仿真时间）
            first_time = float(base_data.get("time", 0.0))
            period = float(period_value if period_value not in (None, "") else 0.0)
            
            print(f"展开参数: first_time={first_time}, period={period}")
            
            # 限制展开的行数
            max_rows = min(1000, len(periodic_file_data))
            print(f"展开前 {max_rows} 行数据")
            
            for row_idx, row_data in enumerate(periodic_file_data[:max_rows]):
                step_elem = ET.SubElement(steps_elem, "step")
                print(f"  创建step {row_idx+1}")
                
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
                
                # 设置data_region为当前行的数据
                type_data_copy["data_region"] = row_data
                
                for k, v in type_data_copy.items():
                    field = ET.SubElement(type_elem, k)
                    if k == "data_region":
                        import json
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
                
                # 保存protocol字典
                protocol_elem = ET.SubElement(step_elem, "protocol")
                protocol_data = step.get_protocol_data()
                for k, v in protocol_data.items():
                    field = ET.SubElement(protocol_elem, k)
                    field.text = str(v)
            
            print(f"步骤展开完成，共生成 {max_rows} 个步骤")
            
            # 跳过当前步骤的常规保存
            continue
        
        # 普通步骤处理
        print("处理普通步骤...")
        if step_type != 1:
            step_elem = ET.SubElement(steps_elem, "step")
            print(f"  创建普通step")
    
    # 保存XML文件
    xml_file = "test_output.xml"
    tree = ET.ElementTree(root)
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
    
    # 检查生成的XML文件
    print(f"\n检查生成的XML文件: {xml_file}")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    steps = root.findall("./steps/step")
    
    print(f"生成的step数量: {len(steps)}")
    
    for i, step in enumerate(steps):
        base_elem = step.find("./base")
        time = base_elem.find("./time")
        print(f"  Step {i+1}: time = {time.text}")
        
        type_elem = step.find("./type")
        data_region = type_elem.find("./data_region")
        print(f"    data_region = {data_region.text}")
    
    # 清理
    if os.path.exists(xml_file):
        os.remove(xml_file)
    
    print("\n测试完成！")

if __name__ == "__main__":
    test_save_logic()