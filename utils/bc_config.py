import configparser
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum

class BcInputIgnoreMode(Enum):
    """BC 输入忽略模式"""
    KEEP_ALL = "KEEP_ALL"
    INCLUDE_BC_INPUT_LIST = "INCLUDE_BC_INPUT_LIST"
    EXCLUDE_BC_INPUT_LIST = "EXCLUDE_BC_INPUT_LIST"

class BcOutputIgnoreMode(Enum):
    """BC 输出忽略模式"""
    KEEP_ALL = "KEEP_ALL"
    IGNORE_ALL = "IGNORE_ALL"
    INCLUDE_BC_OUTPUT_LIST = "INCLUDE_BC_OUTPUT_LIST"
    EXCLUDE_BC_OUTPUT_LIST = "EXCLUDE_BC_OUTPUT_LIST"

class BcConfig:
    """BC 配置管理器"""
    
    def __init__(self, config_path: str = "bc.config"):
        self.config_path = Path(config_path)
        self.input_ignore_mode = BcInputIgnoreMode.KEEP_ALL
        self.output_ignore_mode = BcOutputIgnoreMode.KEEP_ALL
        self.bc_input_list: List[str] = []
        self.bc_output_list: List[str] = []
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
        
        # 加载 BC 输入配置
        if 'BC_INPUT_IGNORE_MODE' in config:
            # 支持两种格式：1) mode = KEEP_ALL 2) 直接一行 KEEP_ALL
            section = config['BC_INPUT_IGNORE_MODE']
            mode_str = section.get('mode')
            if mode_str is None and len(section.keys()) > 0:
                # 取第一个 key 作为值（allow_no_value=True 时 key 无值）
                mode_str = next(iter(section.keys()))
            if mode_str is None:
                mode_str = 'KEEP_ALL'
            else:
                mode_str = str(mode_str).strip().upper()
            try:
                self.input_ignore_mode = BcInputIgnoreMode(mode_str)
            except ValueError:
                print(f"无效的 BC 输入忽略模式: {mode_str}")
                self.input_ignore_mode = BcInputIgnoreMode.KEEP_ALL
        
        if 'BC_INPUT_LIST' in config:
            section = config['BC_INPUT_LIST']
            # 同时支持 item_i = value 与裸值条目
            items = []
            # 先收集 values（对于 item_i = value 的情况）
            items.extend(v.strip() for v in section.values() if v is not None and str(v).strip())
            # 再收集 keys（对于裸值的情况，allow_no_value 会把值设为 None）
            items.extend(k.strip() for k, v in section.items() if (v is None) and str(k).strip())
            self.bc_input_list = [s for s in items if s]
        
        # 加载输出配置
        if 'BC_OUTPUT_IGNORE_MODE' in config:
            section = config['BC_OUTPUT_IGNORE_MODE']
            mode_str = section.get('mode')
            if mode_str is None and len(section.keys()) > 0:
                mode_str = next(iter(section.keys()))
            if mode_str is None:
                mode_str = 'KEEP_ALL'
            else:
                mode_str = str(mode_str).strip().upper()
            try:
                self.output_ignore_mode = BcOutputIgnoreMode(mode_str)
            except ValueError:
                print(f"无效的输出忽略模式: {mode_str}")
                self.output_ignore_mode = BcOutputIgnoreMode.KEEP_ALL
        
        if 'BC_OUTPUT_LIST' in config:
            section = config['BC_OUTPUT_LIST']
            items = []
            items.extend(v.strip() for v in section.values() if v is not None and str(v).strip())
            items.extend(k.strip() for k, v in section.items() if (v is None) and str(k).strip())
            self.bc_output_list = [s for s in items if s]
    
    def is_bc_input_allowed(self, input_name: str) -> bool:
        """检查 BC 输入是否被允许"""
        if self.input_ignore_mode == BcInputIgnoreMode.KEEP_ALL:
            return True
        
        is_in_list = self._is_in_bc_input_list(input_name)
        
        if self.input_ignore_mode == BcInputIgnoreMode.INCLUDE_BC_INPUT_LIST:
            return is_in_list
        elif self.input_ignore_mode == BcInputIgnoreMode.EXCLUDE_BC_INPUT_LIST:
            return not is_in_list
        
        return True
    
    def is_output_allowed(self, output_name: str) -> bool:
        """检查输出是否被允许"""
        if self.output_ignore_mode == BcOutputIgnoreMode.KEEP_ALL:
            return True
        elif self.output_ignore_mode == BcOutputIgnoreMode.IGNORE_ALL:
            return False
        
        is_in_list = self._is_in_bc_output_list(output_name)
        
        if self.output_ignore_mode == BcOutputIgnoreMode.INCLUDE_BC_OUTPUT_LIST:
            return is_in_list
        elif self.output_ignore_mode == BcOutputIgnoreMode.EXCLUDE_BC_OUTPUT_LIST:
            return not is_in_list
        
        return True
    
    def _is_in_bc_input_list(self, input_name: str) -> bool:
        """检查输入是否在 BC 输入列表中"""
        for pattern in self.bc_input_list:
            if self._match_input_pattern(input_name, pattern):
                return True
        return False
    
    def _is_in_bc_output_list(self, output_name: str) -> bool:
        """检查输出是否在输出列表中"""
        for pattern in self.bc_output_list:
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
    
    def get_filtered_bc_inputs(self, all_inputs: List[str]) -> List[str]:
        """获取过滤后的 BC 输入列表"""
        return [input_name for input_name in all_inputs if self.is_bc_input_allowed(input_name)]
    
    def get_filtered_outputs(self, all_outputs: List[str]) -> List[str]:
        """获取过滤后的输出列表"""
        return [output_name for output_name in all_outputs if self.is_output_allowed(output_name)]
    
    def save_config(self):
        """保存配置到文件"""
        lines = []
        # BC 输入模式
        lines.append('[BC_INPUT_IGNORE_MODE]')
        lines.append('# 一共存在三种模式')
        lines.append('# KEEP_ALL  保留所有的Bc输出')
        lines.append('# INCLUDE_BC_INPUT_LIST在该模式下BC_INPUT_LIST下的Bc输入被保留，忽略其他输入')
        lines.append('# EXCLUDE_BC_INPUT_LIST在该模式下BC_INPUT_LIST下的Bc输入被排除')
        lines.append('# 注意，只有最后两种模式时BC_INPUT_LIST下的会起作用')
        lines.append('# 对于忽略的输入，驱动会直接放回负值，表示读取失败，模拟站点不在的情况')
        lines.append(self.input_ignore_mode.value)
        lines.append('')
        # BC 输入列表
        lines.append('# 输入列表')
        lines.append('[BC_INPUT_LIST]')
        if self.bc_input_list:
            lines.extend(self.bc_input_list)
        lines.append('')
        # 输出模式
        lines.append('[BC_OUTPUT_IGNORE_MODE]')
        lines.append('# 一共存在四种模式')
        lines.append('# KEEP_ALL  保留所有的BC输出')
        lines.append('# IGNORE_ALL:忽略所有的BC输出')
        lines.append('# INCLUDE_BC_OUTPUT_LIST在该模式下BC_OUTPUT_LIST下BC输出被保留，忽略除BC_OUTPUT_LIST下的其余输出')
        lines.append('# EXCLUDE_BC_OUTPUT_LIST在该模式下BC_OUTPUT_LIST下的BC输出被排除')
        lines.append('# 注意，只有最后两种模式时BC_OUTPUT_LIST下的会起作用')
        lines.append(self.output_ignore_mode.value)
        lines.append('')
        # 输出列表
        lines.append('[BC_OUTPUT_LIST]')
        if self.bc_output_list:
            lines.extend(self.bc_output_list)
        lines.append('')
        content = "\n".join(lines)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_default_config(self):
        """创建默认配置文件"""
        config_content = """# BC 配置文件
# 配置 BC 输入的忽略模式
# 一共存在三种模式
# KEEP_ALL  保留所有的Bc输出
# INCLUDE_BC_INPUT_LIST在该模式下BC_INPUT_LIST下的Bc输入被保留，忽略其他输入
# EXCLUDE_BC_INPUT_LIST在该模式下BC_INPUT_LIST下的Bc输入被排除
# 注意，只有最后两种模式时BC_INPUT_LIST下的会起作用
# 对于忽略的输入，驱动会直接放回负值，表示读取失败，模拟站点不在的情况

[BC_INPUT_IGNORE_MODE]
KEEP_ALL

# 输入列表
[BC_INPUT_LIST]
# 示例项目（每行一条，无 item_ 前缀）
# BcRecv_ID0XD_SA_0x15_Len44

# 配置 BC 输出的忽略模式
# 一共存在四种模式
# KEEP_ALL  保留所有的BC输出
# IGNORE_ALL 忽略所有的BC输出
# INCLUDE_BC_OUTPUT_LIST在该模式下BC_OUTPUT_LIST下BC输出被保留，忽略除BC_OUTPUT_LIST下的其余输出
# EXCLUDE_BC_OUTPUT_LIST在该模式下BC_OUTPUT_LIST下的BC输出被排除
# 注意，只有最后两种模式时BC_OUTPUT_LIST下的会起作用

[BC_OUTPUT_IGNORE_MODE]
KEEP_ALL

# 输出列表（每行一条，无 item_ 前缀）
[BC_OUTPUT_LIST]
# 示例项目
# BcSend_ID0XD_SA_0x15_Len44
"""
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"已创建默认配置文件: {self.config_path}")

def _get_default_bc_config_path():
    """获取 bc.config 文件的默认路径"""
    # 默认路径：当前项目目录下的bc.config
    from pathlib import Path
    # 获取当前文件所在目录（utils目录）
    current_file_dir = Path(__file__).parent
    # 项目根目录（config_demo0728）
    project_root = current_file_dir.parent
    # 默认配置文件路径
    default_path = project_root / "bc.config"
    return str(default_path)

def _get_bc_config_path():
    """获取 bc.config 文件的路径（使用默认路径）"""
    # 使用独立的默认路径
    return _get_default_bc_config_path()

# 全局实例（延迟初始化）
bc_config = None

def get_bc_config() -> BcConfig:
    """获取 BC 配置实例"""
    global bc_config
    if bc_config is None:
        config_path = _get_bc_config_path()
        bc_config = BcConfig(config_path)
    return bc_config

def init_bc_config(config_path: str = None):
    """初始化 BC 配置"""
    global bc_config
    if config_path is None:
        config_path = _get_bc_config_path()
    bc_config = BcConfig(config_path)
    return bc_config

def reload_bc_config():
    """重新加载 BC 配置"""
    global bc_config
    config_path = _get_bc_config_path()
    bc_config = BcConfig(config_path)
    return bc_config

