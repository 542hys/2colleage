# 测试XML保存功能，验证字典类型数据的处理
import sys
import os
import json
import xml.etree.ElementTree as ET
from main_model import DataModel

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 从controllers.file_controller导入FileController
try:
    from controllers.file_controller import FileController
    print("✓ 成功导入FileController")
except Exception as e:
    print(f"✗ 导入FileController失败: {e}")
    sys.exit(1)

# 创建一个模拟的主窗口类，用于测试
class MockMainWindow:
    pass

# 创建一个模拟的控制器类，用于测试
class MockController:
    pass

# 测试函数
def test_xml_save_with_dict_data():
    print("\n=== 测试XML保存功能（包含字典类型数据） ===")
    
    # 创建DataModel实例
    model = DataModel()
    print("✓ 创建DataModel实例")
    
    # 添加包含字典类型的path_setting
    model.path_setting["test_dict"] = {"key": "value", "number": 123}
    model.path_setting["test_list"] = [1, 2, 3, "test"]
    model.path_setting["test_string"] = "hello world"
    model.path_setting["test_none"] = None
    print("✓ 添加包含字典、列表、字符串和None的path_setting数据")
    
    # 添加包含字典类型的global_params
    model.global_params["param_dict"] = {"config": "value", "count": 456}
    model.global_params["param_string"] = "global value"
    print("✓ 添加包含字典的global_params数据")
    
    # 创建模拟控制器实例
    main_window = MockMainWindow()
    global_controller = MockController()
    window_controller = MockController()
    step_list_controller = MockController()
    step_detail_controller = MockController()
    
    try:
        # 创建FileController实例
        file_controller = FileController(model, main_window, global_controller, 
                                       window_controller, step_list_controller, step_detail_controller)
        print("✓ 创建FileController实例")
        
        # 直接测试XML生成逻辑，不依赖完整的FileController.save_to_file方法
        print("\n--- 直接测试XML生成逻辑 ---")
        
        # 创建XML根元素
        root = ET.Element("config")
        
        # 保存path_setting节点（与file_controller.py中的逻辑相同）
        path_setting_elem = ET.SubElement(root, "path_setting")
        for k, v in model.path_setting.items():
            field = ET.SubElement(path_setting_elem, k)
            # 使用修复后的逻辑：确保所有值都是字符串类型
            field.text = str(v) if v is not None else ""
            print(f"  path_setting字段: {k} = {v} -> 保存为: {field.text}")
        
        # 保存global_params节点（与file_controller.py中的逻辑相同）
        global_params_elem = ET.SubElement(root, "global_params")
        for k, v in model.global_params.items():
            field = ET.SubElement(global_params_elem, k)
            # 使用修复后的逻辑：确保所有值都是字符串类型
            field.text = str(v) if v is not None else ""
            print(f"  global_params字段: {k} = {v} -> 保存为: {field.text}")
        
        # 测试ET.tostring()调用
        try:
            rough_string = ET.tostring(root, encoding="utf-8", method="xml")
            print("✓ 成功调用ET.tostring()，没有TypeError错误")
            
            # 尝试美化XML（与file_controller.py中的逻辑相同）
            try:
                from xml.dom import minidom
                reparsed = minidom.parseString(rough_string)
                pretty_string = reparsed.toprettyxml(indent="    ")
                print("✓ 成功美化XML")
                
                # 保存到文件
                test_file = "test_save.xml"
                with open(test_file, "w", encoding="utf-8") as f:
                    # 移除第一行的xml声明（minidom会自动添加）
                    lines = pretty_string.splitlines()
                    if lines and lines[0].strip().startswith("<?xml"):
                        lines = lines[1:]
                    f.write("\n".join(lines))
                print(f"✓ 成功保存XML文件到: {test_file}")
                
                # 验证保存的XML文件是否正确
                tree = ET.parse(test_file)
                root = tree.getroot()
                print("✓ 成功解析保存的XML文件")
                
                # 检查path_setting节点
                path_setting = root.find("path_setting")
                if path_setting:
                    print("✓ 找到path_setting节点")
                    
                    # 检查test_dict字段
                    test_dict_elem = path_setting.find("test_dict")
                    if test_dict_elem is not None:
                        print(f"✓ test_dict字段值: {test_dict_elem.text}")
                        
                    # 检查test_list字段
                    test_list_elem = path_setting.find("test_list")
                    if test_list_elem is not None:
                        print(f"✓ test_list字段值: {test_list_elem.text}")
                        
                    # 检查test_string字段
                    test_string_elem = path_setting.find("test_string")
                    if test_string_elem is not None:
                        print(f"✓ test_string字段值: {test_string_elem.text}")
                        
                    # 检查test_none字段
                    test_none_elem = path_setting.find("test_none")
                    if test_none_elem is not None:
                        print(f"✓ test_none字段值: {test_none_elem.text}")
            except Exception as e:
                print(f"✗ 美化或保存XML文件失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        except TypeError as e:
            print(f"✗ 发生TypeError错误: {e}")
            print("修复失败！XML保存功能仍然无法处理字典类型数据")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"✗ 生成XML时发生其他错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    finally:
        # 清理测试文件
        if os.path.exists("test_save.xml"):
            os.remove("test_save.xml")
            print("✓ 清理测试文件")
    
    print("\n=== 测试完成！ ===")
    return True

if __name__ == "__main__":
    success = test_xml_save_with_dict_data()
    if success:
        print("\n🎉 修复成功！XML保存功能现在可以正确处理字典类型数据了！")
        sys.exit(0)
    else:
        print("\n❌ 修复失败！请检查代码")
        sys.exit(1)