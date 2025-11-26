from PyQt5.QtCore import QObject, pyqtSignal
from views.uart_config_view import UartConfigDialog
from utils.uart_config import UartConfig, get_uart_config

class UartConfigController(QObject):
    """Uart 配置控制器"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.uart_config = None  # 延迟加载，不在初始化时加载
    
    def show_config_dialog(self):
        """显示配置对话框"""
        # 在打开对话框时才加载配置
        if self.uart_config is None:
            self.uart_config = get_uart_config()
        dialog = UartConfigDialog()
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec_()
    
    def on_config_saved(self):
        """配置保存后的回调"""
        # 重新加载配置
        self.uart_config = UartConfig()
        self.config_changed.emit()
        print("Uart 配置已更新")
    
    def is_uart_input_allowed(self, input_name: str) -> bool:
        """检查 Uart 输入是否被允许"""
        return self.uart_config.is_uart_input_allowed(input_name)
    
    def is_output_allowed(self, output_name: str) -> bool:
        """检查输出是否被允许"""
        return self.uart_config.is_output_allowed(output_name)
    
    def get_filtered_uart_inputs(self, all_inputs: list) -> list:
        """获取过滤后的 Uart 输入列表"""
        return self.uart_config.get_filtered_uart_inputs(all_inputs)
    
    def get_filtered_outputs(self, all_outputs: list) -> list:
        """获取过滤后的输出列表"""
        return self.uart_config.get_filtered_outputs(all_outputs)
    
    def get_config_summary(self) -> dict:
        """获取配置摘要"""
        return {
            "input_mode": self.uart_config.input_ignore_mode.value,
            "output_mode": self.uart_config.output_ignore_mode.value,
            "uart_input_count": len(self.uart_config.uart_input_list),
            "output_count": len(self.uart_config.uart_output_list)
        }

