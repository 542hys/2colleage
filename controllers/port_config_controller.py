from PyQt5.QtCore import QObject, pyqtSignal
from views.port_config_view import PortConfigDialog
from utils.port_config import PortConfig, get_port_config

class PortConfigController(QObject):
    """中断配置控制器"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.port_config = None  # 延迟加载，不在初始化时加载
    
    def show_config_dialog(self):
        """显示配置对话框"""
        # 在打开对话框时才加载配置
        if self.port_config is None:
            self.port_config = get_port_config()
        dialog = PortConfigDialog()
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec_()
    
    def on_config_saved(self):
        """配置保存后的回调"""
        # 重新加载配置
        self.port_config = PortConfig()
        self.config_changed.emit()
        print("中断配置已更新")
    
    def get_int_period(self, int_num: int):
        """获取中断号的周期值（毫秒）"""
        return self.port_config.get_int_period(int_num)
    
    def is_int_ignored(self, int_num: int) -> bool:
        """检查中断号是否被忽略"""
        return self.port_config.is_int_ignored(int_num)
    
    def get_single_trigger_times(self, int_num: int):
        """获取中断号的单次触发时间列表（毫秒）"""
        return self.port_config.get_single_trigger_times(int_num)
    
    def get_config_summary(self) -> dict:
        """获取配置摘要"""
        return {
            "period_count": len(self.port_config.int_period),
            "ignore_count": len(self.port_config.ignore_int),
            "trigger_count": len(self.port_config.single_trigger_int)
        }

