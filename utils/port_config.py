import configparser
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class PortConfig:
    """中断配置管理器"""
    
    def __init__(self, config_path: str = "port.config"):
        self.config_path = Path(config_path)
        # 中断周期配置：中断号 -> 周期值(ms)
        self.int_period: Dict[int, int] = {}
        # 忽略的中断号列表
        self.ignore_int: List[int] = []
        # 单次触发中断配置：中断号 -> 触发时间列表(ms)
        self.single_trigger_int: Dict[int, List[int]] = {}
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
        
        # 加载中断周期配置
        if 'INT_PERIOD' in config:
            section = config['INT_PERIOD']
            self.int_period = {}
            for key, value in section.items():
                try:
                    int_num = int(key.strip())
                    period = int(value.strip()) if value else 0
                    if period > 0:
                        self.int_period[int_num] = period
                except (ValueError, TypeError):
                    # 跳过无效的条目
                    continue
        
        # 加载忽略的中断号
        if 'IGNORE_INT' in config:
            section = config['IGNORE_INT']
            self.ignore_int = []
            for key, value in section.items():
                try:
                    # 忽略注释行（以分号或中文分号开头的）
                    key_stripped = key.strip()
                    if key_stripped.startswith('；') or key_stripped.startswith(';') or not key_stripped:
                        continue
                    int_num = int(key_stripped)
                    self.ignore_int.append(int_num)
                except (ValueError, TypeError):
                    # 跳过无效的条目和注释
                    continue
        
        # 加载单次触发中断配置
        if 'ISINGLE_TRIGGER_INTJ' in config:
            section = config['ISINGLE_TRIGGER_INTJ']
            self.single_trigger_int = {}
            for key, value in section.items():
                try:
                    # 忽略注释行（以分号或中文分号开头的）
                    key_stripped = key.strip()
                    if key_stripped.startswith('；') or key_stripped.startswith(';') or not key_stripped:
                        continue
                    int_num = int(key_stripped)
                    if value:
                        # 解析多个触发时间，用逗号分隔
                        times = [int(t.strip()) for t in value.split(',') if t.strip()]
                        if times:
                            self.single_trigger_int[int_num] = times
                except (ValueError, TypeError):
                    # 跳过无效的条目
                    continue
    
    def get_int_period(self, int_num: int) -> Optional[int]:
        """获取中断号的周期值（毫秒），如果不存在返回None"""
        return self.int_period.get(int_num)
    
    def is_int_ignored(self, int_num: int) -> bool:
        """检查中断号是否被忽略"""
        return int_num in self.ignore_int
    
    def get_single_trigger_times(self, int_num: int) -> List[int]:
        """获取中断号的单次触发时间列表（毫秒）"""
        return self.single_trigger_int.get(int_num, [])
    
    def save_config(self):
        """保存配置到文件"""
        lines = []
        
        # 中断周期配置
        lines.append('# 对中断周期的配置,注意此处只需要配周期性中断，其余均认为是非周期中断')
        lines.append('# 中断号=周期值(ms)')
        lines.append('[INT_PERIOD]')
        if self.int_period:
            # 按中断号排序
            for int_num in sorted(self.int_period.keys()):
                period = self.int_period[int_num]
                lines.append(f'{int_num}={period}')
        lines.append('')
        
        # 忽略的中断号
        lines.append('# 忽略的中断号')
        lines.append('[IGNORE_INT]')
        if self.ignore_int:
            # 按中断号排序
            for int_num in sorted(self.ignore_int):
                lines.append(str(int_num))
        lines.append('')
        
        # 单次触发中断配置
        lines.append('# 单次触发中断配置')
        lines.append('# 对于数据触发的中断可在底层驱动中通过读文件控制数据何时到来，不在此处配置')
        lines.append('# 中断号=触发时间(ms)')
        lines.append('[ISINGLE_TRIGGER_INTJ]')
        if self.single_trigger_int:
            # 按中断号排序
            for int_num in sorted(self.single_trigger_int.keys()):
                times = self.single_trigger_int[int_num]
                times_str = ','.join(str(t) for t in times)
                lines.append(f'{int_num}={times_str}')
        lines.append('')
        
        content = "\n".join(lines)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_default_config(self):
        """创建默认配置文件"""
        config_content = """# 中断配置文件
# 对中断周期的配置,注意此处只需要配周期性中断，其余均认为是非周期中断
# 中断号=周期值(ms)

[INT_PERIOD]
# 示例：4号中断周期为5ms
# 4=5

# 忽略的中断号
[IGNORE_INT]
# 示例：忽略某个中断号
# ；核间通信中断

# 单次触发中断配置
# 对于数据触发的中断可在底层驱动中通过读文件控制数据何时到来，不在此处配置
# 中断号=触发时间(ms)

[ISINGLE_TRIGGER_INTJ]
# 示例：仿真时间10s时触发90号中断
# 90=10000,10005,10010,70000
"""
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"已创建默认配置文件: {self.config_path}")

def _get_default_port_config_path():
    """获取 port.config 文件的默认路径"""
    # 默认路径：当前项目目录下的port.config
    from pathlib import Path
    # 获取当前文件所在目录（utils目录）
    current_file_dir = Path(__file__).parent
    # 项目根目录（config_demo0728）
    project_root = current_file_dir.parent
    # 默认配置文件路径
    default_path = project_root / "port.config"
    return str(default_path)

def _get_port_config_path():
    """获取 port.config 文件的路径（使用默认路径）"""
    # 使用独立的默认路径
    return _get_default_port_config_path()

# 全局实例（延迟初始化）
port_config = None

def get_port_config() -> PortConfig:
    """获取中断配置实例"""
    global port_config
    if port_config is None:
        config_path = _get_port_config_path()
        port_config = PortConfig(config_path)
    return port_config

def init_port_config(config_path: str = None):
    """初始化中断配置"""
    global port_config
    if config_path is None:
        config_path = _get_port_config_path()
    port_config = PortConfig(config_path)
    return port_config

def reload_port_config():
    """重新加载中断配置"""
    global port_config
    config_path = _get_port_config_path()
    port_config = PortConfig(config_path)
    return port_config

