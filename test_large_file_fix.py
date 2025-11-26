#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试大文件周期GLINK处理修复
"""

import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.file_controller import FileController
from main_model import DataModel

# 创建一个模拟的大文件用于测试
test_file_path = "test_large_file.txt"

# 生成测试文件（16列x100行的"1"）
with open(test_file_path, "w", encoding="utf-8") as f:
    for _ in range(100):
        f.write("1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1\n")

try:
    # 创建模型和控制器
    model = DataModel()
    controller = FileController(model, None, None, None, None, None)
    
    # 模拟没有数据类型配置的情况
    periodic_file_path = test_file_path
    start_time = 100.0
    period = 1.0
    type_data = {}
    
    # 从type_data中提取数据类型（应该为空）
    data_types = []
    for i in range(1, 13):
        dtype_key = f"data_type_{i}"
        dtype_val = type_data.get(dtype_key)
        if dtype_val is not None:
            data_types.append(int(dtype_val))
    
    print(f"提取的数据类型列表: {data_types}")
    
    # 如果没有找到数据类型，尝试根据文件内容自动检测列数并生成默认数据类型
    if not data_types:
        print("未找到数据类型配置，尝试自动检测文件格式...")
        # 读取文件的第一行来确定列数
        with open(periodic_file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line:
                columns = first_line.split()
                num_columns = len(columns)
                print(f"检测到文件有 {num_columns} 列数据")
                # 为每一列生成默认数据类型（假设为类型1）
                data_types = [1] * num_columns
            else:
                # 文件为空，使用默认的1个通道
                data_types = [1]
    
    print(f"最终使用的数据类型列表: {data_types}")
    
    # 调用批量处理函数
    processed_data = controller.process_large_periodic_file(periodic_file_path, start_time, period, data_types)
    
    print(f"\n处理完成！共处理 {len(processed_data)} 行数据")
    print(f"每行数据包含 {len(processed_data[0])} 个数据项")
    print(f"第一行数据示例: {json.dumps(processed_data[0], indent=2, ensure_ascii=False)}")
    
    print("\n修复测试成功！")
    
except Exception as e:
    print(f"\n测试失败: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    # 清理测试文件
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"\n已删除测试文件: {test_file_path}")
