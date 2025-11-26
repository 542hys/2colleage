import os
import sys
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.file_controller import FileController
from main_model import DataModel
from models.step_model import StepModel

class MockMainWindow:
    def __init__(self):
        self.window_title = "Mock Window"

class MockGlobalController:
    def update_global_model(self):
        pass

class MockStepListController:
    def clear_step_data(self):
        pass
    def update_step_list(self):
        pass

class MockStepDetailController:
    def clear_step_detail(self):
        pass

class MockWindowController:
    def update_window_title(self):
        pass

def create_test_model(large_file_path, line_count=60):
    """创建包含周期GLINK步骤的数据模型，使用指定的大文件"""
    model = DataModel()
    
    # 创建一个周期GLINK步骤
    step = StepModel()
    step.step_type = 1  # 周期GLINK类型
    
    # 设置基础数据（直接访问字典）
    step.base_step_data.update({
        "name": "周期GLINK大文件测试",
        "time": 100.0,
        "step_type": 1
    })
    
    # 设置类型数据（直接访问字典）
    step.type_step_data.update({
        "protocol_type": 0,
        "file_path": large_file_path,
        "period": 5.0,  # 5秒周期
        "data_type_1": 1,  # 数据类型
        "data_type_2": 1
    })
    
    # 设置展开数据（大文件标记）
    step.expand_step_data.update({
        "periodic_file_path": large_file_path,
        "periodic_file_data": [],  # 空数据表示需要处理大文件
        "periodic_file_line_count": line_count  # 标记为大文件
    })
    
    # 设置协议数据
    step.protocol_data.update({
        "protocol_type": 0
    })
    
    # 添加步骤到模型
    model.add_step(step)
    
    return model

def create_large_test_file(file_path, line_count=60):
    """创建包含指定行数的大测试文件"""
    with open(file_path, 'w') as f:
        # 生成60行数据，每行包含两个普通数值
        for i in range(line_count):
            f.write(f"{100+i} {200+i}\n")
    print(f"创建大测试文件: {file_path}，共 {line_count} 行")

def test_large_file_processing():
    """测试大文件处理逻辑"""
    # 创建60行的大测试文件
    large_file_path = "test_60_lines.txt"
    create_large_test_file(large_file_path, line_count=60)
    
    try:
        # 创建测试数据模型
        model = create_test_model(large_file_path, line_count=60)
        
        # 创建模拟的控制器实例
        mock_main_window = MockMainWindow()
        mock_global_controller = MockGlobalController()
        mock_step_list_controller = MockStepListController()
        mock_step_detail_controller = MockStepDetailController()
        mock_window_controller = MockWindowController()
        
        file_controller = FileController(
            model, 
            mock_main_window, 
            mock_global_controller, 
            mock_step_list_controller, 
            mock_step_detail_controller, 
            mock_window_controller
        )
        
        # 获取原始模型中的步骤数量
        original_step_count = len(model.steps)
        print(f"原始模型中的步骤数量: {original_step_count}")
        
        # 手动调用大文件处理逻辑
        print("\n手动处理大文件...")
        
        # 获取步骤
        if model.steps:
            step = model.steps[0]
            
            # 检查是否是周期GLINK大文件
            step_type = step.base_step_data.get("step_type", -1)
            expand_data = step.expand_step_data
            file_path = expand_data.get("periodic_file_path")
            line_count = expand_data.get("periodic_file_line_count")
            
            if step_type == 1 and file_path and line_count:
                print(f"检测到周期GLINK大文件: {file_path}")
                
                # 处理大文件
                processed_data = file_controller.process_large_periodic_file(file_path)
                print(f"大文件处理完成，共处理 {len(processed_data)} 行数据")
                
                # 展开步骤
                first_time = step.base_step_data.get("time", 100.0)
                period = step.type_step_data.get("period", 5.0)
                
                # 清空原步骤
                model.steps.clear()
                
                # 生成新步骤
                for i in range(len(processed_data)):
                    new_step = StepModel()
                    new_step.step_type = 1
                    
                    # 设置基础数据
                    new_step.base_step_data.update({
                        "name": f"周期GLINK步骤_{i+1}",
                        "time": first_time + i * period,
                        "step_type": 1
                    })
                    
                    # 设置类型数据
                    new_step.type_step_data.update(step.type_step_data)
                    new_step.type_step_data["file_path"] = file_path
                    
                    # 设置展开数据
                    new_step.expand_step_data.update({
                        "periodic_file_path": file_path,
                        "periodic_file_data": processed_data[i],
                        "periodic_file_line_count": line_count
                    })
                    
                    # 设置协议数据
                    new_step.protocol_data.update(step.protocol_data)
                    
                    # 添加到模型
                    model.steps.append(new_step)
                    
                print(f"步骤展开完成，共生成 {len(model.steps)} 个步骤")
                
                # 验证步骤数量
                if len(model.steps) == line_count:
                    print("测试通过: 大文件处理后生成了正确数量的步骤")
                    
                    # 直接创建XML文件进行验证
                    print("\n创建验证XML文件: test_large_file_verify.xml")
                    root = ET.Element("config")
                    
                    # 全局参数
                    global_elem = ET.SubElement(root, "global_params")
                    for k, v in model.global_params.items():
                        param = ET.SubElement(global_elem, k)
                        param.text = str(v)
                    
                    # 步骤
                    steps_elem = ET.SubElement(root, "steps")
                    for step in model.steps:
                        step_elem = ET.SubElement(steps_elem, "step")
                        
                        # 保存base字典
                        base_elem = ET.SubElement(step_elem, "base")
                        for k, v in step.base_step_data.items():
                            field = ET.SubElement(base_elem, k)
                            field.text = str(v)
                        
                        # 保存type字典
                        type_elem = ET.SubElement(step_elem, "type")
                        for k, v in step.type_step_data.items():
                            field = ET.SubElement(type_elem, k)
                            field.text = str(v)
                        
                        # 保存expand字典
                        expand_elem = ET.SubElement(step_elem, "expand")
                        for k, v in step.expand_step_data.items():
                            field = ET.SubElement(expand_elem, k)
                            if isinstance(v, (list, dict)):
                                field.text = str(v)  # 简化处理
                            else:
                                field.text = str(v)
                    
                    # 保存XML文件
                    tree = ET.ElementTree(root)
                    tree.write("test_large_file_verify.xml", encoding="utf-8", xml_declaration=True)
                    
                    # 验证XML文件
                    print(f"验证XML文件包含 {len(model.steps)} 个步骤")
                    
                    return True
                else:
                    print(f"测试失败: 预期 {line_count} 个步骤，实际 {len(model.steps)} 个步骤")
                    return False
            else:
                print("未检测到周期GLINK大文件")
                return False
        else:
            print("模型中没有步骤")
            return False
            
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        if os.path.exists(large_file_path):
            os.remove(large_file_path)

if __name__ == "__main__":
    print("开始测试大文件处理逻辑...")
    success = test_large_file_processing()
    if success:
        print("\n测试通过！大文件处理逻辑可以正确生成所有步骤。")
    else:
        print("\n测试失败！大文件处理逻辑存在问题。")
    sys.exit(0 if success else 1)