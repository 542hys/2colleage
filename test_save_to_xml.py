import os
import sys
import xml.etree.ElementTree as ET
import tempfile

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from controllers.file_controller import FileController
from main_model import DataModel

# 创建一个简单的测试模型
def create_test_model():
    model = DataModel()
    
    # 添加一个周期GLINK步骤
    step = model.add_step()
    step.set_base_step_data({
        "step_type": 1,  # 周期GLINK
        "time": 100.0,
        "name": "测试周期步骤"
    })
    step.set_type_step_data({
        "file_path": "test_large_file.txt",
        "period": 10.0,
        "data_type_1": 1
    })
    expand_data = step.get_expand_step_data()
    expand_data["periodic_file_path"] = "test_large_file.txt"
    
    return model

# 创建测试数据文件
def create_test_data_file(file_path, num_rows=10):
    with open(file_path, 'w') as f:
        for i in range(num_rows):
            f.write(f"1.1 2.2 3.3 4.4 5.5 6.6 7.7 8.8 9.9 10.1 11.1 12.1 13.1 14.1 15.1 16.1\n")

# 测试save_to_xml方法
def test_save_to_xml():
    # 创建测试数据文件
    test_file_path = "test_large_file.txt"
    create_test_data_file(test_file_path, num_rows=5)
    
    try:
        # 创建模型
        model = create_test_model()
        
        # 创建控制器（使用Mock对象避免依赖问题）
        print("创建FileController控制器...")
        
        # 模拟所需的依赖对象
        class MockMainWindow:
            def __init__(self):
                self.new_action = None
                self.open_action = None
                self.save_action = None
                self.save_as_action = None
                
        mock_main_window = MockMainWindow()
        
        # 初始化控制器（只提供必要的参数）
        controller = FileController(
            model=model,
            main_window=mock_main_window,
            global_controller=None,
            window_controller=None,
            step_list_controller=None,
            step_detail_controller=None
        )
        
        # 创建一个临时XML文件路径
        xml_file_path = "test_output.xml"
        
        # 保存到XML文件
        print("开始保存到XML文件...")
        controller.save_to_file(xml_file_path)
        
        # 检查生成的XML文件
        print("检查生成的XML文件...")
        if os.path.exists(xml_file_path):
            print(f"XML文件已成功创建: {xml_file_path}")
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            steps = root.findall("./steps/step")
            
            print(f"生成的step数量: {len(steps)}")
            
            # 检查每个step的time值
            for i, step in enumerate(steps):
                base_elem = step.find("./base")
                time = base_elem.find("./time")
                name = base_elem.find("./name")
                print(f"  Step {i+1}: time = {time.text}, name = {name.text}")
            
            # 验证结果
            assert len(steps) == 5, f"预期生成5个step，实际生成了{len(steps)}个"
            print("✅ 测试通过！大文件周期GLINK正确生成了多个step。")
            return True
        else:
            print("❌ 测试失败！XML文件未创建。")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败！发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        # 保留输出文件以便检查
        # if os.path.exists("test_output.xml"):
        #     os.remove("test_output.xml")

if __name__ == "__main__":
    test_save_to_xml()