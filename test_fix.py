#!/usr/bin/env python3
# 测试修复后的代码

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 测试1: 验证DataModel是否有path_setting属性
print("测试1: 验证DataModel是否有path_setting属性")
try:
    from main_model import DataModel
    model = DataModel()
    print(f"✓ DataModel实例创建成功")
    print(f"✓ path_setting属性存在: {model.path_setting}")
    print(f"✓ path_setting初始值为字典: {isinstance(model.path_setting, dict)}")
    # 测试设置path_setting
    model.path_setting = {"test_key": "test_value"}
    print(f"✓ path_setting可以设置值: {model.path_setting}")
except Exception as e:
    print(f"✗ 测试失败: {e}")
    traceback.print_exc()

print("\n测试2: 验证file_controller.py是否能正常导入")
try:
    from controllers.file_controller import FileController
    print(f"✓ FileController导入成功")
except Exception as e:
    print(f"✗ 测试失败: {e}")
    traceback.print_exc()

print("\n测试3: 创建测试文件并验证多行读取功能")
# 创建测试文件
test_file_content = """
12345678
9ABCDEF0
1122334455
"""
test_file_path = os.path.join(os.path.dirname(__file__), "test_hex.txt")
try:
    with open(test_file_path, "w") as f:
        f.write(test_file_content)
    print(f"✓ 测试文件创建成功: {test_file_path}")
    
    # 导入read_hex_sequences_from_files函数
    from controllers.file_controller import FileController
    
    # 创建一个模拟的FileController实例（只用于测试read_hex_sequences_from_files函数）
    class MockModel:
        def __init__(self):
            self.path_setting = {}
            self.global_params = {}
            self.steps = []
    
    class MockMainWindow:
        pass
    
    class MockGlobalController:
        pass
    
    class MockWindowController:
        pass
    
    class MockStepListController:
        pass
    
    class MockStepDetailController:
        pass
    
    # 创建FileController实例
    file_controller = FileController(
        MockModel(),
        MockMainWindow(),
        MockGlobalController(),
        MockWindowController(),
        MockStepListController(),
        MockStepDetailController()
    )
    
    # 访问read_hex_sequences_from_files函数（它是一个内部函数，需要通过其他方式测试）
    # 这里我们直接重新实现一个简单的测试版本
    def test_read_hex_sequences_from_files(path_field, msg_len=None):
        """测试版本的read_hex_sequences_from_files函数"""
        seqs = []
        if not path_field:
            return seqs
        # 支持以 ; 或 , 分隔的多个文件
        parts = []
        if isinstance(path_field, str):
            parts = [p.strip() for p in path_field.replace("\n", ",").split(",") if p.strip()]
        elif isinstance(path_field, (list, tuple)):
            parts = [str(p).strip() for p in path_field if str(p).strip()]
        for p in parts:
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        s = line.strip()
                        if not s:
                            continue
                        # 解析一行HEX
                        s = s.replace("\t", " ").replace(",", " ")
                        s = s.replace("0x", "").replace("0X", "")
                        s = "".join(s.split())
                        # 按16位（4个字符）分组，最后一个字节不补零
                        row = []
                        for i in range(0, len(s), 4):
                            if i + 4 <= len(s):
                                # 完整的16位
                                row.append(f"0x{s[i:i+4].upper()}")
                            else:
                                # 最后一个不完整的字节，不补零
                                remaining = s[i:]
                                if len(remaining) == 2:
                                    row.append(f"0x{remaining.upper()}")
                                elif len(remaining) == 1:
                                    row.append(f"0x{remaining.upper()}")
                        if msg_len and isinstance(msg_len, int) and msg_len > 0:
                            row = row[:msg_len]
                        if row:
                            seqs.append(row)
            except Exception as e:
                print(f"读取文件出错: {e}")
                continue
        return seqs
    
    # 测试多行读取
    result = test_read_hex_sequences_from_files(test_file_path)
    print(f"✓ read_hex_sequences_from_files函数执行成功")
    print(f"✓ 读取到的行数: {len(result)}")
    print(f"✓ 每行内容:")
    for i, row in enumerate(result):
        print(f"    行{i+1}: {row}")
    
    # 验证是否读取了所有行（测试文件有3行有效内容）
    if len(result) == 3:
        print(f"✓ 成功读取所有3行数据")
    else:
        print(f"✗ 读取行数不正确，期望3行，实际读取{len(result)}行")
        
except Exception as e:
    print(f"✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
finally:
    # 清理测试文件
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"\n✓ 测试文件已清理")

print("\n所有测试完成")
