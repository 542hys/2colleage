#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试read_hex_sequences_from_files函数
"""

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 直接从file_controller.py导入函数
import file_controller

# 创建测试文件
test_file = "test_hex.txt"
with open(test_file, 'w') as f:
    f.write("0x1234 0x5678\n0x9ABC 0xDEF0")

print(f"创建测试文件 {test_file}")
print("内容：")
with open(test_file, 'r') as f:
    print(f.read())

# 调用函数测试
print("\n调用read_hex_sequences_from_files函数...")
try:
    sequences = file_controller.read_hex_sequences_from_files(test_file, 2)
    print(f"返回结果：{sequences}")
    print(f"共 {len(sequences)} 行")
    for i, seq in enumerate(sequences):
        print(f"第 {i+1} 行: {seq}")
except Exception as e:
    print(f"出错：{e}")
    import traceback
    traceback.print_exc()

# 清理
os.remove(test_file)
print(f"\n清理测试文件 {test_file}")