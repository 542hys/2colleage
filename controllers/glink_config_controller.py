from PyQt5.QtCore import QObject, pyqtSignal
from views.glink_config_view import GLinkConfigDialog
from utils.glink_config import GLinkConfig, get_glink_config

class GLinkConfigController(QObject):
    """GLink 配置控制器"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.glink_config = None  # 延迟加载，不在初始化时加载
    
    def show_config_dialog(self):
        """显示配置对话框"""
        # 在打开对话框时才加载配置
        if self.glink_config is None:
            self.glink_config = get_glink_config()
        dialog = GLinkConfigDialog()
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec_()
    
    def on_config_saved(self):
        """配置保存后的回调"""
        # 重新加载配置
        self.glink_config = GLinkConfig()
        self.config_changed.emit()
        print("GLink 配置已更新")
    
    def is_nc_input_allowed(self, input_name: str) -> bool:
        """检查 NC 输入是否被允许"""
        if self.glink_config is None:
            self.glink_config = get_glink_config()
        return self.glink_config.is_nc_input_allowed(input_name)
    
    def is_output_allowed(self, output_name: str) -> bool:
        """检查输出是否被允许"""
        if self.glink_config is None:
            self.glink_config = get_glink_config()
        return self.glink_config.is_output_allowed(output_name)
    
    def get_filtered_nc_inputs(self, all_inputs: list) -> list:
        """获取过滤后的 NC 输入列表"""
        if self.glink_config is None:
            self.glink_config = get_glink_config()
        return self.glink_config.get_filtered_nc_inputs(all_inputs)
    
    def get_filtered_outputs(self, all_outputs: list) -> list:
        """获取过滤后的输出列表"""
        if self.glink_config is None:
            self.glink_config = get_glink_config()
        return self.glink_config.get_filtered_outputs(all_outputs)
    
    def get_config_summary(self) -> dict:
        """获取配置摘要"""
        if self.glink_config is None:
            self.glink_config = get_glink_config()
        return {
            "input_mode": self.glink_config.input_ignore_mode.value,
            "output_mode": self.glink_config.output_ignore_mode.value,
            "nc_input_count": len(self.glink_config.nc_input_list),
            "output_count": len(self.glink_config.output_list)
        } 