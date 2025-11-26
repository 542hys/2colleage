import configparser
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum

class InputIgnoreMode(Enum):
    """NC 输入忽略模式"""
    KEEP_ALL = "KEEP_ALL"
    INCLUDE_NC_INPUT_LIST = "INCLUDE_NC_INPUT_LIST"
    EXCLUDE_NC_INPUT_LIST = "EXCLUDE_NC_INPUT_LIST"

class OutputIgnoreMode(Enum):
    """GLink 输出忽略模式"""
    KEEP_ALL = "KEEP_ALL"
    IGNORE_ALL = "IGNORE_ALL"
    INCLUDE_OUTPUT_LIST = "INCLUDE_OUTPUT_LIST"
    EXCLUDE_OUTPUT_LIST = "EXCLUDE_OUTPUT_LIST"

class GLinkConfig:
    """GLink 配置管理器"""
    
    def __init__(self, config_path: str = "glink.config"):
        self.config_path = Path(config_path)
        self.input_ignore_mode = InputIgnoreMode.KEEP_ALL
        self.output_ignore_mode = OutputIgnoreMode.KEEP_ALL
        self.nc_input_list: List[str] = []
        self.output_list: List[str] = []
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
        
        # 加载 NC 输入配置
        if 'NC_INPUT_IGNORE_MODE' in config:
            # 支持两种格式：1) mode = KEEP_ALL 2) 直接一行 KEEP_ALL
            section = config['NC_INPUT_IGNORE_MODE']
            mode_str = section.get('mode')
            if mode_str is None and len(section.keys()) > 0:
                # 取第一个 key 作为值（allow_no_value=True 时 key 无值）
                mode_str = next(iter(section.keys()))
            if mode_str is None:
                mode_str = 'KEEP_ALL'
            else:
                mode_str = str(mode_str).strip().upper()
            try:
                self.input_ignore_mode = InputIgnoreMode(mode_str)
            except ValueError:
                print(f"无效的 NC 输入忽略模式: {mode_str}")
                self.input_ignore_mode = InputIgnoreMode.KEEP_ALL
        
        if 'NC_INPUT_LIST' in config:
            section = config['NC_INPUT_LIST']
            # 同时支持 item_i = value 与裸值条目
            items = []
            # 先收集 values（对于 item_i = value 的情况）
            items.extend(v.strip() for v in section.values() if v is not None and str(v).strip())
            # 再收集 keys（对于裸值的情况，allow_no_value 会把值设为 None）
            items.extend(k.strip() for k, v in section.items() if (v is None) and str(k).strip())
            self.nc_input_list = [s for s in items if s]
        
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
                self.output_ignore_mode = OutputIgnoreMode(mode_str)
            except ValueError:
                print(f"无效的输出忽略模式: {mode_str}")
                self.output_ignore_mode = OutputIgnoreMode.KEEP_ALL
        
        if 'OUTPUT_LIST' in config:
            section = config['OUTPUT_LIST']
            items = []
            items.extend(v.strip() for v in section.values() if v is not None and str(v).strip())
            items.extend(k.strip() for k, v in section.items() if (v is None) and str(k).strip())
            self.output_list = [s for s in items if s]
    
    def is_nc_input_allowed(self, input_name: str) -> bool:
        """检查 NC 输入是否被允许"""
        if self.input_ignore_mode == InputIgnoreMode.KEEP_ALL:
            return True
        
        is_in_list = self._is_in_nc_input_list(input_name)
        
        if self.input_ignore_mode == InputIgnoreMode.INCLUDE_NC_INPUT_LIST:
            return is_in_list
        elif self.input_ignore_mode == InputIgnoreMode.EXCLUDE_NC_INPUT_LIST:
            return not is_in_list
        
        return True
    
    def is_output_allowed(self, output_name: str) -> bool:
        """检查输出是否被允许"""
        if self.output_ignore_mode == OutputIgnoreMode.KEEP_ALL:
            return True
        elif self.output_ignore_mode == OutputIgnoreMode.IGNORE_ALL:
            return False
        
        is_in_list = self._is_in_output_list(output_name)
        
        if self.output_ignore_mode == OutputIgnoreMode.INCLUDE_OUTPUT_LIST:
            return is_in_list
        elif self.output_ignore_mode == OutputIgnoreMode.EXCLUDE_OUTPUT_LIST:
            return not is_in_list
        
        return True
    
    def _is_in_nc_input_list(self, input_name: str) -> bool:
        """检查输入是否在 NC 输入列表中"""
        for pattern in self.nc_input_list:
            if self._match_input_pattern(input_name, pattern):
                return True
        return False
    
    def _is_in_output_list(self, output_name: str) -> bool:
        """检查输出是否在输出列表中"""
        for pattern in self.output_list:
            if self._match_output_pattern(output_name, pattern):
                return True
        return False
    
    def _match_input_pattern(self, input_name: str, pattern: str) -> bool:
        """匹配输入模式"""
        # 解析模式：NcRecv_ID0x40A_SA0x8_Len46 或 NCRecv_ID41-0x401 SA0x120_Len32
        # 支持通配符和范围匹配
        
        # 转换为正则表达式
        regex_pattern = self._convert_to_regex(pattern)
        
        try:
            return bool(re.match(regex_pattern, input_name, re.IGNORECASE))
        except re.error:
            # 如果正则表达式无效，使用简单字符串匹配
            return input_name.lower() == pattern.lower()
    
    def _match_output_pattern(self, output_name: str, pattern: str) -> bool:
        """匹配输出模式"""
        # 支持对 ID 号子地址所有消息的屏蔽和保留
        # 也支持对 ID 号子地址长度单条消息的屏蔽和保留
        
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
        
        # 支持十六进制范围
        pattern = re.sub(r'0x([0-9A-Fa-f]+)-0x([0-9A-Fa-f]+)', 
                        lambda m: f'0x[0-9A-Fa-f]{{{len(m.group(1))},{len(m.group(2))}}}', 
                        pattern)
        
        return f'^{pattern}$'
    
    def get_filtered_nc_inputs(self, all_inputs: List[str]) -> List[str]:
        """获取过滤后的 NC 输入列表"""
        return [input_name for input_name in all_inputs if self.is_nc_input_allowed(input_name)]
    
    def get_filtered_outputs(self, all_outputs: List[str]) -> List[str]:
        """获取过滤后的输出列表"""
        return [output_name for output_name in all_outputs if self.is_output_allowed(output_name)]
    
    def save_config(self):
        """保存配置到文件（不带 mode = 与 item_i = 前缀）"""
        lines = []
        # NC 输入模式
        lines.append('[NC_INPUT_IGNORE_MODE]')
        lines.append(self.input_ignore_mode.value)
        lines.append('')
        # NC 输入列表
        lines.append('# 支持的格式：')
        lines.append('# • 1对1 NC输入: NcRecv_ID0x40A_SA0x8_Len46')
        lines.append('# • 1对4 NC输入: NCRecv_ID41-0x401_SA0x120_Len32')
        lines.append('')
        lines.append('[NC_INPUT_LIST]')
        if self.nc_input_list:
            lines.extend(self.nc_input_list)
        lines.append('')
        # 输出模式
        lines.append('[OUTPUT_IGNORE_MODE]')
        lines.append(self.output_ignore_mode.value)
        lines.append('')
        # 输出列表
        lines.append('# 支持的格式：')
        lines.append('# • 支持对ID号子地址所有消息的屏蔽和保留')
        lines.append('# • 支持对ID号子地址长度单条消息的屏蔽和保留')
        lines.append('')
        lines.append('[OUTPUT_LIST]')
        if self.output_list:
            lines.extend(self.output_list)
        lines.append('')
        content = "\n".join(lines)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_default_config(self):
        """创建默认配置文件"""
        config_content = """# GLink 配置文件
# 配置 NC 输入的忽略模式
# KEEP_ALL  保留所有 GLink 输入
# INCLUDE_NC_INPUT_LIST 在该模式下 NC_INPUT_LIST 下的 GLink 输入被保留，忽略其他输入
# EXCLUDE_NC_INPUT_LIST 在该模式下 NC_INPUT_LIST 下的 GLink 输入被排除

[NC_INPUT_IGNORE_MODE]
KEEP_ALL

# 输入列表格式：
# • 1对1 NC输入: NcRecv_ID0x40A_SA0x8_Len46
# • 1对4 NC输入: NCRecv_ID41-0x401 SA0x120_Len32

[NC_INPUT_LIST]
# 示例项目（每行一条，无 item_ 前缀）
# NcRecv_ID0x40A_SA0x15_Len78

# 配置 GLink 输出的忽略模式
# KEEP_ALL  保留所有的 GLink 输出
# IGNORE_ALL 忽略所有的 GLink 输出
# INCLUDE_OUTPUT_LIST 在该模式下 OUTPUT_LIST 下的 GLink 输出被保留，忽略除 OUTPUT_LIST 下的其余输出
# EXCLUDE_OUTPUT_LIST 在该模式下 OUTPUT_LIST 下的 GLink 输出被排除

[OUTPUT_IGNORE_MODE]
KEEP_ALL

# 输出列表（每行一条，无 item_ 前缀）
[OUTPUT_LIST]
# 示例项目
"""
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"已创建默认配置文件: {self.config_path}")

def _get_default_glink_config_path():
    """获取 glink.config 文件的默认路径"""
    # 默认路径：当前项目目录下的glink.config
    from pathlib import Path
    # 获取当前文件所在目录（utils目录）
    current_file_dir = Path(__file__).parent
    # 项目根目录（config_demo0728）
    project_root = current_file_dir.parent
    # 默认配置文件路径
    default_path = project_root / "glink.config"
    return str(default_path)

def _get_glink_config_path():
    """获取 glink.config 文件的路径（使用默认路径）"""
    # 使用独立的默认路径，不再依赖全局设置的输出路径
    return _get_default_glink_config_path()

# 全局实例（延迟初始化，以便从输出目录读取配置）
glink_config = None

def get_glink_config() -> GLinkConfig:
    """获取 GLink 配置实例（从输出目录读取）"""
    global glink_config
    if glink_config is None:
        config_path = _get_glink_config_path()
        glink_config = GLinkConfig(config_path)
    return glink_config

def init_glink_config(config_path: str = None):
    """初始化 GLink 配置"""
    global glink_config
    if config_path is None:
        config_path = _get_glink_config_path()
    glink_config = GLinkConfig(config_path)
    return glink_config

def reload_glink_config():
    """重新加载 GLink 配置（当输出路径改变时调用）"""
    global glink_config
    config_path = _get_glink_config_path()
    glink_config = GLinkConfig(config_path)
    return glink_config 

