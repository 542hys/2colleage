"""
配置加载工具模块
根据流程步类型按需加载对应的配置文件
"""
from typing import Optional, Union
from models.step_model import SUPPORTED_TYPES

def get_config_by_step_type(step_type: int):
    """
    根据流程步类型获取对应的配置对象
    
    Args:
        step_type: 流程步类型索引
            - 0, 1: GLINK -> GLinkConfig
            - 2, 3: 串口 -> UartConfig
            - 4, 5: 1553-BC -> BcConfig
            - 7: 中断 -> PortConfig
            - 其他: None
    
    Returns:
        对应的配置对象，如果step_type不匹配则返回None
    """
    if not (0 <= step_type < len(SUPPORTED_TYPES)):
        return None
    
    step_type_name = SUPPORTED_TYPES[step_type]
    
    # GLINK相关 (0, 1)
    if step_type_name in ("glink_fileds_non_periodic", "glink_fileds_periodic"):
        from utils.glink_config import get_glink_config
        return get_glink_config()
    
    # 串口相关 (2, 3)
    elif step_type_name in ("serial_fileds_non_periodic", "serial_fileds_periodic"):
        from utils.uart_config import get_uart_config
        return get_uart_config()
    
    # 1553-BC相关 (4, 5)
    elif step_type_name in ("bus1553_fileds_non_periodic", "bus1553_fileds_periodic"):
        from utils.bc_config import get_bc_config
        return get_bc_config()
    
    # 中断相关 (7)
    elif step_type_name == "interrupt_fileds":
        from utils.port_config import get_port_config
        return get_port_config()
    
    # 其他类型不需要配置
    return None

def reload_config_by_step_type(step_type: int):
    """
    根据流程步类型重新加载对应的配置
    
    Args:
        step_type: 流程步类型索引
    
    Returns:
        重新加载后的配置对象，如果step_type不匹配则返回None
    """
    if not (0 <= step_type < len(SUPPORTED_TYPES)):
        return None
    
    step_type_name = SUPPORTED_TYPES[step_type]
    
    # GLINK相关 (0, 1)
    if step_type_name in ("glink_fileds_non_periodic", "glink_fileds_periodic"):
        from utils.glink_config import reload_glink_config
        return reload_glink_config()
    
    # 串口相关 (2, 3)
    elif step_type_name in ("serial_fileds_non_periodic", "serial_fileds_periodic"):
        from utils.uart_config import reload_uart_config
        return reload_uart_config()
    
    # 1553-BC相关 (4, 5)
    elif step_type_name in ("bus1553_fileds_non_periodic", "bus1553_fileds_periodic"):
        from utils.bc_config import reload_bc_config
        return reload_bc_config()
    
    # 中断相关 (7)
    elif step_type_name == "interrupt_fileds":
        from utils.port_config import reload_port_config
        return reload_port_config()
    
    # 其他类型不需要配置
    return None

