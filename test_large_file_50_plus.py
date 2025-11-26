import os
import sys
import xml.etree.ElementTree as ET
import uuid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 从file_controller导入处理大文件的函数
from controllers.file_controller import FileController
from main_model import DataModel
from models.step_model import StepModel

class MockMainWindow:
    def __init__(self):
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
    
    # 设置展开数据（大文件标记，直接访问字典）
    step.expand_step_data.update({
        "periodic_file_path": large_file_path,
        "periodic_file_data": [],  # 空数据表示需要处理大文件
        "periodic_file_line_count": line_count  # 标记为大文件
    })
    
    # 设置协议数据（直接访问字典）
    step.protocol_data.update({
        "protocol_type": 0
    })
    
    # 添加步骤到模型
    model.add_step(step)
    
    return model

def create_large_test_file(file_path, line_count=60):
    """创建指定行数的大测试文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(line_count):
            # 生成两列数据
            col1 = f"{100+i}"
            col2 = f"{200+i}"
            f.write(f"{col1} {col2}\n")
    print(f"创建大测试文件: {file_path}，共 {line_count} 行")

def test_large_file_save():
    """测试大文件（超过50行）的保存功能"""
    # 创建60行的大测试文件
    large_file_path = "test_60_lines.txt"
    create_large_test_file(large_file_path, line_count=60)
    
    try:
        # 创建测试数据模型
        model = create_test_model(large_file_path, line_count=60)
        
        # 创建模拟的控制器实例
        mock_main_window = MockMainWindow()
        file_controller = FileController(model, mock_main_window, None, None, None, None)
        
            # 保存到XML文件（使用绝对路径）
        output_xml_path = os.path.abspath("test_60_lines_output.xml")
        print(f"保存到XML文件: {output_xml_path}")
        
        try:
            file_controller.save_to_file(output_xml_path)
            print("调用save_to_file完成")
        except Exception as e:
            print(f"调用save_to_file时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 验证XML文件是否存在
        print(f"检查XML文件是否存在: {output_xml_path}")
        if not os.path.exists(output_xml_path):
            print(f"测试失败: 无法找到保存的XML文件 '{output_xml_path}'")
            print("当前目录文件列表:")
            for f in os.listdir("."):
                if f.endswith(".xml"):
                    print(f"  - {f}")
            return False
        
        # 验证XML文件
        tree = ET.parse(output_xml_path)
        root = tree.getroot()
        steps = root.findall("./steps/step")
        
        print(f"XML文件中包含 {len(steps)} 个step元素")
        
        # 检查是否保存了所有行
        if len(steps) == 60:
            print("✓ 成功：保存了所有60行数据")
        else:
            print(f"✗ 失败：只保存了 {len(steps)} 行数据，应该保存60行")
        
        # 检查前几行和最后几行的时间值
        for i in range(min(5, len(steps))):
            step = steps[i]
            time = float(step.find("./base/time").text)
            print(f"Step {i+1}: time={time}")
        
        if len(steps) > 5:
            for i in range(max(0, len(steps)-5), len(steps)):
                step = steps[i]
                time = float(step.find("./base/time").text)
                print(f"Step {i+1}: time={time}")
        
        return len(steps) == 60
        
    except Exception as e:
        print(f"测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        if os.path.exists(large_file_path):
            os.remove(large_file_path)
        # 保留XML文件以便检查
        # if os.path.exists(output_xml_path):
        #     os.remove(output_xml_path)

if __name__ == "__main__":
    print("开始测试超过50行的大文件保存功能...")
    success = test_large_file_save()
    if success:
        print("\n测试通过！超过50行的大文件可以正确保存。")
    else:
        print("\n测试失败！超过50行的大文件保存有问题。")
    sys.exit(0 if success else 1)