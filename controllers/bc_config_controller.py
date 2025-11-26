from PyQt5.QtCore import QObject, pyqtSignal
from views.bc_config_view import BcConfigDialog
from utils.bc_config import BcConfig, get_bc_config

class BcConfigController(QObject):
    """BC 配置控制器"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bc_config = None  # 延迟加载，不在初始化时加载
    
    def show_config_dialog(self):
        """显示配置对话框"""
        # 在打开对话框时才加载配置
        if self.bc_config is None:
            self.bc_config = get_bc_config()
        dialog = BcConfigDialog()
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec_()
    
    def on_config_saved(self):
        """配置保存后的回调"""
        # 重新加载配置
        self.bc_config = BcConfig()
        self.config_changed.emit()
        print("BC 配置已更新")
    
    def is_bc_input_allowed(self, input_name: str) -> bool:
        """检查 BC 输入是否被允许"""
        return self.bc_config.is_bc_input_allowed(input_name)
    
    def is_output_allowed(self, output_name: str) -> bool:
        """检查输出是否被允许"""
        return self.bc_config.is_output_allowed(output_name)
    
    def get_filtered_bc_inputs(self, all_inputs: list) -> list:
        """获取过滤后的 BC 输入列表"""
        return self.bc_config.get_filtered_bc_inputs(all_inputs)
    
    def get_filtered_outputs(self, all_outputs: list) -> list:
        """获取过滤后的输出列表"""
        return self.bc_config.get_filtered_outputs(all_outputs)
    
    def get_config_summary(self) -> dict:
        """获取配置摘要"""
        return {
            "input_mode": self.bc_config.input_ignore_mode.value,
            "output_mode": self.bc_config.output_ignore_mode.value,
            "bc_input_count": len(self.bc_config.bc_input_list),
            "output_count": len(self.bc_config.bc_output_list)
        }

