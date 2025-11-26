#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLink 配置测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.glink_config import GLinkConfig, InputIgnoreMode, OutputIgnoreMode

def test_glink_config():
    """测试 GLink 配置功能"""
    print("=== GLink 配置测试 ===")
    
    # 创建配置实例
    config = GLinkConfig("test_glink.config")
    
    # 创建默认配置
    config.create_default_config()
    print("✓ 已创建默认配置文件")
    
    # 测试 NC 输入过滤
    print("\n--- 测试 NC 输入过滤 ---")
    
    # 设置为排除模式
    config.input_ignore_mode = InputIgnoreMode.EXCLUDE_NC_INPUT_LIST
    config.nc_input_list = [
        "NcRecv_ID0x40A_SA0x15_Len78",
        "NcRecv_ID0x100_SA0x20_Len32"
    ]
    
    test_inputs = [
        "NcRecv_ID0x40A_SA0x15_Len78",  # 应该被排除
        "NcRecv_ID0x200_SA0x30_Len64",  # 应该被保留
        "NcRecv_ID0x100_SA0x20_Len32"   # 应该被排除
    ]
    
    for input_name in test_inputs:
        allowed = config.is_nc_input_allowed(input_name)
        status = "允许" if allowed else "排除"
        print(f"  {input_name}: {status}")
    
    # 测试输出过滤
    print("\n--- 测试输出过滤 ---")
    
    # 设置为包含模式
    config.output_ignore_mode = OutputIgnoreMode.INCLUDE_OUTPUT_LIST
    config.output_list = [
        "Output_ID0x500_SA0x10",
        "Output_ID0x600_SA0x20"
    ]
    
    test_outputs = [
        "Output_ID0x500_SA0x10",  # 应该被保留
        "Output_ID0x700_SA0x30",  # 应该被排除
        "Output_ID0x600_SA0x20"   # 应该被保留
    ]
    
    for output_name in test_outputs:
        allowed = config.is_output_allowed(output_name)
        status = "允许" if allowed else "排除"
        print(f"  {output_name}: {status}")
    
    # 测试模式匹配
    print("\n--- 测试模式匹配 ---")
    
    # 测试通配符匹配
    config.nc_input_list = ["NcRecv_ID0x*_SA0x10_Len*"]
    test_patterns = [
        "NcRecv_ID0x100_SA0x10_Len32",
        "NcRecv_ID0x200_SA0x10_Len64",
        "NcRecv_ID0x300_SA0x20_Len32"  # 不匹配
    ]
    
    for pattern in test_patterns:
        allowed = config.is_nc_input_allowed(pattern)
        status = "匹配" if allowed else "不匹配"
        print(f"  {pattern}: {status}")
    
    # 保存配置
    config.save_config()
    print("\n✓ 配置已保存到文件")
    
    # 显示配置摘要
    summary = {
        "input_mode": config.input_ignore_mode.value,
        "output_mode": config.output_ignore_mode.value,
        "nc_input_count": len(config.nc_input_list),
        "output_count": len(config.output_list)
    }
    print(f"\n配置摘要: {summary}")

if __name__ == "__main__":
    test_glink_config() 