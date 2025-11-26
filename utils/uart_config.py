import configparser
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum

class UartInputIgnoreMode(Enum):
    """Uart 输入忽略模式"""
    KEEP_ALL = "KEEP_ALL"
    INCLUDE_UART_INPUT_LIST = "INCLUDE_UART_INPUT_LIST"
    EXCLUDE_UART_INPUT_LIST = "EXCLUDE_UART_INPUT_LIST"

class UartOutputIgnoreMode(Enum):
    """Uart 输出忽略模式"""
    KEEP_ALL = "KEEP_ALL"
    IGNORE_ALL = "IGNORE_ALL"
    INCLUDE_OUTPUT_LIST = "INCLUDE_OUTPUT_LIST"
    EXCLUDE_OUTPUT_LIST = "EXCLUDE_OUTPUT_LIST"

class UartConfig:
    """Uart 配置管理器"""
    
    def __init__(self, config_path: str = "uart.config"):
        self.config_path = Path(config_path)
        self.input_ignore_mode = UartInputIgnoreMode.KEEP_ALL
        self.output_ignore_mode = UartOutputIgnoreMode.KEEP_ALL
        self.uart_input_list: List[str] = []
        self.uart_output_list: List[str] = []
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"配置文件不存在: {self.config_path}")
            return
        
        # 允许无值键，便于解析不含 key 的条目；保留大小写避免将裸值键转为小写
        config = configparser.ConfigParser(allow_no_value=True)
        config.optionxform = str
        config.read(self.config_path, encoding='utf-8')
        
        # 加载 Uart 输入配置
        if 'UART_INPUT_IGNORE_MODE' in config:
            # 支持两种格式：1) mode = KEEP_ALL 2) 直接一行 KEEP_ALL
            section = config['UART_INPUT_IGNORE_MODE']
            mode_str = section.get('mode')
            if mode_str is None and len(section.keys()) > 0:
                # 取第一个 key 作为值（allow_no_value=True 时 key 无值）
                mode_str = next(iter(section.keys()))
            if mode_str is None:
                mode_str = 'KEEP_ALL'
            else:
                mode_str = str(mode_str).strip().upper()
            try:
                self.input_ignore_mode = UartInputIgnoreMode(mode_str)
            except ValueError:
                print(f"无效的 Uart 输入忽略模式: {mode_str}")
                self.input_ignore_mode = UartInputIgnoreMode.KEEP_ALL
        
        if 'UART_INPUT_LIST' in config:
            section = config['UART_INPUT_LIST']
            # 同时支持 item_i = value 与裸值条目
            items = []
            # 先收集 values（对于 item_i = value 的情况）
            items.extend(v.strip() for v in section.values() if v is not None and str(v).strip())
            # 再收集 keys（对于裸值的情况，allow_no_value 会把值设为 None）
            items.extend(k.strip() for k, v in section.items() if (v is None) and str(k).strip())
            self.uart_input_list = [s for s in items if s]
        
        # 加载输出配置
        if 'OUTPUT_IGNORE_MODE' in config:
            section = config['OUTPUT_IGNORE_MODE']
            mode_str = section.get('mode')
            if mode_str is None and len(section.keys()) > 0:
                mode_str = next(iter(section.keys()))
            if mode_str is None:
                mode_str = 'KEEP_ALL'
            else:
                mode_str = str(mode_str).strip().upper()
            try:
                self.output_ignore_mode = UartOutputIgnoreMode(mode_str)
            except ValueError:
                print(f"无效的输出忽略模式: {mode_str}")
                self.output_ignore_mode = UartOutputIgnoreMode.KEEP_ALL
        
        if 'UART_OUTPUT_LIST' in config:
            section = config['UART_OUTPUT_LIST']
            items = []
            items.extend(v.strip() for v in section.values() if v is not None and str(v).strip())
            items.extend(k.strip() for k, v in section.items() if (v is None) and str(k).strip())
            self.uart_output_list = [s for s in items if s]
    
    def is_uart_input_allowed(self, input_name: str) -> bool:
        """检查 Uart 输入是否被允许"""
        if self.input_ignore_mode == UartInputIgnoreMode.KEEP_ALL:
            return True
        
        is_in_list = self._is_in_uart_input_list(input_name)
        
        if self.input_ignore_mode == UartInputIgnoreMode.INCLUDE_UART_INPUT_LIST:
            return is_in_list
        elif self.input_ignore_mode == UartInputIgnoreMode.EXCLUDE_UART_INPUT_LIST:
            return not is_in_list
        
        return True
    
    def is_output_allowed(self, output_name: str) -> bool:
        """检查输出是否被允许"""
        if self.output_ignore_mode == UartOutputIgnoreMode.KEEP_ALL:
            return True
        elif self.output_ignore_mode == UartOutputIgnoreMode.IGNORE_ALL:
            return False
        
        is_in_list = self._is_in_uart_output_list(output_name)
        
        if self.output_ignore_mode == UartOutputIgnoreMode.INCLUDE_OUTPUT_LIST:
            return is_in_list
        elif self.output_ignore_mode == UartOutputIgnoreMode.EXCLUDE_OUTPUT_LIST:
            return not is_in_list
        
        return True
    
    def _is_in_uart_input_list(self, input_name: str) -> bool:
        """检查输入是否在 Uart 输入列表中"""
        for pattern in self.uart_input_list:
            if self._match_input_pattern(input_name, pattern):
                return True
        return False
    
    def _is_in_uart_output_list(self, output_name: str) -> bool:
        """检查输出是否在输出列表中"""
        for pattern in self.uart_output_list:
            if self._match_output_pattern(output_name, pattern):
                return True
        return False
    
    def _match_input_pattern(self, input_name: str, pattern: str) -> bool:
        """匹配输入模式"""
        # 转换为正则表达式
        regex_pattern = self._convert_to_regex(pattern)
        
        try:
            return bool(re.match(regex_pattern, input_name, re.IGNORECASE))
        except re.error:
            # 如果正则表达式无效，使用简单字符串匹配
            return input_name.lower() == pattern.lower()
    
    def _match_output_pattern(self, output_name: str, pattern: str) -> bool:
        """匹配输出模式"""
        regex_pattern = self._convert_to_regex(pattern)
        
        try:
            return bool(re.match(regex_pattern, output_name, re.IGNORECASE))
        except re.error:
            return output_name.lower() == pattern.lower()
    
    def _convert_to_regex(self, pattern: str) -> str:
        """将模式转换为正则表达式"""
        # 转义特殊字符
        pattern = re.escape(pattern)
        
        # 支持通配符
        pattern = pattern.replace(r'\*', '.*')
        pattern = pattern.replace(r'\?', '.')
        
        return f'^{pattern}$'
    
    def get_filtered_uart_inputs(self, all_inputs: List[str]) -> List[str]:
        """获取过滤后的 Uart 输入列表"""
        return [input_name for input_name in all_inputs if self.is_uart_input_allowed(input_name)]
    
    def get_filtered_outputs(self, all_outputs: List[str]) -> List[str]:
        """获取过滤后的输出列表"""
        return [output_name for output_name in all_outputs if self.is_output_allowed(output_name)]
    
    def save_config(self):
        """保存配置到文件"""
        lines = []
        # Uart 输入模式
        lines.append('[UART_INPUT_IGNORE_MODE]')
        lines.append('# 一共存在三种模式')
        lines.append('# KEEP_ALL  保留所有的Uart输出')
        lines.append('# INCLUDE_UART_INPUT_LIST在该模式下UART_INPUT_LIST下的Uart输入被保留，忽略其他输入')
        lines.append('# EXCLUDE_UART_INPUT_LIST在该模式下UART_INPUT_LIST下的Uart输入被排除')
        lines.append('# 注意，只有最后两种模式时UART_INPUT_LIST下的会起作用')
        lines.append('# 对于忽略的输入，驱动会直接放回负值，表示读取失败，模拟站点不在的情况')
        lines.append(self.input_ignore_mode.value)
        lines.append('')
        # Uart 输入列表
        lines.append('# 输入列表')
        lines.append('[UART_INPUT_LIST]')
        if self.uart_input_list:
            lines.extend(self.uart_input_list)
        lines.append('')
        # 输出模式
        lines.append('[OUTPUT_IGNORE_MODE]')
        lines.append('# 一共存在四种模式')
        lines.append('# KEEP_ALL  保留所有的Uart输出')
        lines.append('# IGNORE_ALL:忽略所有的Uart输出')
        lines.append('# INCLUDE_OUTPUT_LIST在该模式下OUTPUT_LIST下的Uart输出被保留，忽略除OUTPUT_LIST下的其余输出')
        lines.append('# EXCLUDE_OUTPUT_LIST在该模式下OUTPUT_LIST下的Uart输出被排除')
        lines.append('# 注意，只有最后两种模式时UART_OUTPUT_LIST下的会起作用')
        lines.append(self.output_ignore_mode.value)
        lines.append('')
        # 输出列表
        lines.append('[UART_OUTPUT_LIST]')
        if self.uart_output_list:
            lines.extend(self.uart_output_list)
        lines.append('')
        content = "\n".join(lines)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_default_config(self):
        """创建默认配置文件"""
        config_content = """# Uart 配置文件
# 配置 Uart 输入的忽略模式
# 一共存在三种模式
# KEEP_ALL  保留所有的Uart输出
# INCLUDE_UART_INPUT_LIST在该模式下UART_INPUT_LIST下的Uart输入被保留，忽略其他输入
# EXCLUDE_UART_INPUT_LIST在该模式下UART_INPUT_LIST下的Uart输入被排除
# 注意，只有最后两种模式时UART_INPUT_LIST下的会起作用
# 对于忽略的输入，驱动会直接放回负值，表示读取失败，模拟站点不在的情况

[UART_INPUT_IGNORE_MODE]
KEEP_ALL

# 输入列表
[UART_INPUT_LIST]
# 示例项目（每行一条，无 item_ 前缀）
# Uart_Period_recv_Com_ADD_0xb000a000

# 配置 Uart 输出的忽略模式
# 一共存在四种模式
# KEEP_ALL  保留所有的Uart输出
# IGNORE_ALL 忽略所有的Uart输出
# INCLUDE_OUTPUT_LIST在该模式下OUTPUT_LIST下的Uart输出被保留，忽略除OUTPUT_LIST下的其余输出
# EXCLUDE_OUTPUT_LIST在该模式下OUTPUT_LIST下的Uart输出被排除
# 注意，只有最后两种模式时UART_OUTPUT_LIST下的会起作用

[OUTPUT_IGNORE_MODE]
KEEP_ALL

# 输出列表（每行一条，无 item_ 前缀）
[UART_OUTPUT_LIST]
# 示例项目
# Uart_Send_Com_ADD_0xb000a000
"""
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"已创建默认配置文件: {self.config_path}")

def _get_default_uart_config_path():
    """获取 uart.config 文件的默认路径"""
    # 默认路径：当前项目目录下的uart.config
    from pathlib import Path
    # 获取当前文件所在目录（utils目录）
    current_file_dir = Path(__file__).parent
    # 项目根目录（config_demo0728）
    project_root = current_file_dir.parent
    # 默认配置文件路径
    default_path = project_root / "uart.config"
    return str(default_path)

def _get_uart_config_path():
    """获取 uart.config 文件的路径（使用默认路径）"""
    # 使用独立的默认路径
    return _get_default_uart_config_path()

# 全局实例（延迟初始化）
uart_config = None

def get_uart_config() -> UartConfig:
    """获取 Uart 配置实例"""
    global uart_config
    if uart_config is None:
        config_path = _get_uart_config_path()
        uart_config = UartConfig(config_path)
    return uart_config

def init_uart_config(config_path: str = None):
    """初始化 Uart 配置"""
    global uart_config
    if config_path is None:
        config_path = _get_uart_config_path()
    uart_config = UartConfig(config_path)
    return uart_config

def reload_uart_config():
    """重新加载 Uart 配置"""
    global uart_config
    config_path = _get_uart_config_path()
    uart_config = UartConfig(config_path)
    return uart_config

