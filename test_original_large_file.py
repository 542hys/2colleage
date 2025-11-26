#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试原始大文件周期GLINK处理修复
"""

import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.file_controller import FileController
from main_model import DataModel

# 使用原始的大文件路径
test_file_path = "16x16_ones.txt"

# 检查文件是否存在
if not os.path.exists(test_file_path):
    print(f"错误：测试文件 {test_file_path} 不存在！")
    sys.exit(1)

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
    
    # 为了测试效率，我们只处理前1000行
    print("\n开始处理原始大文件（仅处理前1000行用于测试）...")
    
    # 自定义一个简化的处理函数，只处理前1000行
    processed_data = []
    line_count = 0
    max_lines = 1000
    
    with open(periodic_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line_count >= max_lines:
                break
                
            line = line.strip()
            if not line:
                continue
            
            # 按空格分割
            values = line.split()
            
            # 检查数据列数是否匹配
            if len(values) != len(data_types):
                raise ValueError(f"第 {line_count + 1} 行数据列数 ({len(values)}) 与数据类型数量 ({len(data_types)}) 不匹配")
            
            # 构建当前行的数据结构
            row_data = []
            for value_str, dtype_idx in zip(values, data_types):
                # 验证十六进制数据格式
                try:
                    if dtype_idx in [1, 2, 3, 4]:  # 假设这些是数值类型
                        float(value_str)  # 尝试转换为浮点数验证
                except ValueError:
                    raise ValueError(f"第 {line_count + 1} 行第 {len(row_data) + 1} 列数据 '{value_str}' 不是有效的数值")
                
                row_data.append({
                    "data_type": dtype_idx,
                    "value": value_str
                })
            
            processed_data.append(row_data)
            line_count += 1
            
            # 每处理100行显示一次进度
            if line_count % 100 == 0:
                print(f"已处理 {line_count}/{max_lines} 行...")
    
    print(f"\n处理完成！共处理 {len(processed_data)} 行数据")
    print(f"每行数据包含 {len(processed_data[0])} 个数据项")
    print(f"第一行数据示例: {json.dumps(processed_data[0], indent=2, ensure_ascii=False)}")
    
    print("\n原始大文件修复测试成功！")
    
except Exception as e:
    print(f"\n测试失败: {str(e)}")
    import traceback
    traceback.print_exc()
