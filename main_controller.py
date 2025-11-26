from main_model import DataModel
from main_window import MainWindow
import sys
from pathlib import Path
from controllers.step_detail_controller import StepDetailController
from controllers.global_config_controller import GlobalConfigController
from controllers.step_list_controller import StepListController
from controllers.file_controller import FileController
from controllers.window_controller import WindowController
from controllers.glink_config_controller import GLinkConfigController
from controllers.uart_config_controller import UartConfigController
from controllers.bc_config_controller import BcConfigController
from utils import conf

class MainController:
    def __init__(self, app_manager, parent=None):
        """主控制器，协调模型和视图"""
        self.app_manager = app_manager
        self.parent = parent
        
        self.model = DataModel()
        self.main_window = MainWindow(self, parent)
        
        # 当窗口关闭时通知应用管理器
        self.main_window.destroyed.connect(lambda: app_manager.close_window(self))
        
        self.STRINGS = conf.get_config_strings()
        
        # 视图引用
        self.global_view = self.main_window.global_view
        self.step_list_view = self.main_window.step_list_view
        self.step_detail_view = self.main_window.step_detail_view

        # 子控制器
        self.window_controller = WindowController(self.model, self.main_window)
        self.step_detail_controller = StepDetailController(self.model, self.step_detail_view)
        
        # 创建全局配置控制器（先不传递step_list_controller）
        self.global_config_controller = GlobalConfigController(
            self.model, self.global_view, self.window_controller
        )
        
        self.glink_config_controller = GLinkConfigController()
        self.uart_config_controller = UartConfigController()
        self.bc_config_controller = BcConfigController()
        
        # 创建步骤列表控制器（传递global_config_controller）
        self.step_list_controller = StepListController(
            self.model, self.step_list_view, 
            self.step_detail_controller, self.global_config_controller, self.STRINGS
        )
        
        # 现在设置循环引用：将step_list_controller传递给global_config_controller
        self.global_config_controller.step_list_controller = self.step_list_controller
        self.file_controller = FileController(
            self.model, self.main_window, 
            global_controller=self.global_config_controller, 
            window_controller=self.window_controller,
            step_list_controller=self.step_list_controller, 
            step_detail_controller=self.step_detail_controller
        )
        
        # 初始化数据
        # self.global_config_controller.update_global_view()
        
        # 连接信号
        self.connect_signals()
        
        # 启动时恢复所有协议的默认设置（GLink、串口、1553-BC、中断）
        try:
            self.global_view.reset_all_to_default_silent()
        except Exception as e:
            print(f"启动时恢复默认设置失败: {e}")
    
    def connect_signals(self):
        """连接所有信号"""
        # 连接 GLink 配置菜单
        self.main_window.glink_config_action.triggered.connect(
            self.glink_config_controller.show_config_dialog
        )
        # 连接串口配置菜单
        self.main_window.serial_config_action.triggered.connect(
            self.uart_config_controller.show_config_dialog
        )
        # 连接1553-BC配置菜单
        self.main_window.bc_config_action.triggered.connect(
            self.bc_config_controller.show_config_dialog
        )
        # 连接"保存流程并生成数据"
        self.main_window.save_and_export_action.triggered.connect(
            self.file_controller.save_and_export
        )
        
        # 连接全局设置菜单
        self.main_window.global_settings_action.triggered.connect(
            self.main_window.show_settings_dialog
        )
        
        # 连接新建窗口信号
        self.main_window.new_window_action.triggered.connect(self.create_new_window)
        
        # 连接其他控制器的信号
        self.step_detail_controller.connect_signals()
        self.global_config_controller.connect_signals()
        self.step_list_controller.connect_signals()
        self.file_controller.connect_signals()
        self.window_controller.connect_signals()
        
        # 连接 GLink 配置变更信号
        self.glink_config_controller.config_changed.connect(self.on_glink_config_changed)
    
    def on_glink_config_changed(self):
        """GLink 配置变更时的回调"""
        print("GLink 配置已更新")
        # 这里可以添加配置变更后的处理逻辑
        # 例如：重新加载数据、更新界面等

    def create_new_window(self):
        """创建新窗口"""
        self.app_manager.create_window()

    def update_global_model(self):
        self.global_config_controller.update_global_model()

    def update_window_title(self):
        """更新窗口标题"""
        title = "流程配置工具"
        if self.model.file_path:
            file_name = Path(self.model.file_path).name
            title += f" - {file_name}"
        
        if self.model.is_dirty():
            title += " *"
        
        
        if self.model.is_dirty():
            title += " *"
        
        self.main_window.setWindowTitle(title)


