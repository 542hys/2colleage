from main_model import DataModel
from main_window import MainWindow
import sys
from pathlib import Path
from controllers.step_detail_controller import StepDetailController
from controllers.global_config_controller import GlobalConfigController
from controllers.step_list_controller import StepListController
from controllers.file_controller import FileController
from controllers.window_controller import WindowController
from utils import conf
from PyQt5.QtCore import QObject, pyqtSignal
import weakref
from main_controller import MainController

class ApplicationManager(QObject):
    """管理整个应用程序和所有窗口"""
    window_closed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.windows = []
        self.app = None
        
    def create_window(self, controller=None, file_path=None):
        """创建新窗口"""
        if not controller:
            controller = MainController(self)
        window = controller.main_window
        
        # 设置窗口位置（避免完全重叠）
        # if self.windows:
        #     last_window = self.windows[-1].main_window
        #     pos = last_window.pos()
        #     window.move(pos.x() + 40, pos.y() + 40)

        if self.windows:
            last_ref = self.windows[-1]
            last_controller = last_ref()  # 解引用
            if last_controller and last_controller.main_window:
                last_pos = last_controller.main_window.pos()
                window.move(last_pos.x() + 40, last_pos.y() + 40)
        
        window.show()
        self.windows.append(weakref.ref(controller))
        
        # 如果提供了文件路径，打开它
        if file_path:
            controller.file_controller.open_file(file_path)
        
        return controller
    
    def close_window(self, controller):
        """关闭窗口"""
        # 从窗口中移除引用
        self.windows = [ref for ref in self.windows if ref() != controller]
        
        # 如果没有窗口了，退出应用
        if not self.windows:
            self.app.quit()
    
    def get_all_windows(self):
        """获取所有活动窗口"""
        return [ref() for ref in self.windows if ref() is not None]
    
    def bring_all_to_front(self):
        """将所有窗口前置"""
        for controller in self.get_all_windows():
            controller.main_window.raise_()
            controller.main_window.activateWindow()


