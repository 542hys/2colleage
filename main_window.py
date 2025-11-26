from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QAction, QSplitter, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from views.global_config_view import GlobalConfigView
from views.step_list_view import StepListView
from views.step_detail_view import StepDetailView


class MainWindow(QMainWindow):
    """主窗口视图"""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("流程配置工具")
        self.setGeometry(100, 100, 1200, 800)

        self.create_menu()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.param_tab = QWidget()
        self.tab_widget.addTab(self.param_tab, "步骤配置")

        self.global_view = GlobalConfigView()
        self.step_list_view = StepListView()
        self.step_detail_view = StepDetailView()

        self.init_param_tab()
        self.apply_styles()

    def create_menu(self):
        menubar = self.menuBar()

        window_menu = menubar.addMenu("窗口")
        self.new_window_action = QAction("新建窗口", self)
        self.new_window_action.setShortcut("Ctrl+Shift+N")
        window_menu.addAction(self.new_window_action)

        config_menu = menubar.addMenu("流程配置")
        self.new_action = QAction(QIcon.fromTheme("document-new"), "新建", self)
        self.open_action = QAction(QIcon.fromTheme("document-open"), "打开", self)
        self.save_action = QAction(QIcon.fromTheme("document-save"), "保存", self)
        self.save_as_action = QAction("另存为", self)

        config_menu.addAction(self.new_action)
        config_menu.addAction(self.open_action)
        config_menu.addAction(self.save_action)
        config_menu.addAction(self.save_as_action)

        self.save_and_export_action = QAction("保存流程并生成数据", self)
        config_menu.addAction(self.save_and_export_action)

        driver_menu = menubar.addMenu("驱动配置")
        self.glink_config_action = QAction("GLink 配置", self)
        self.glink_config_action.setShortcut("Ctrl+G")
        driver_menu.addAction(self.glink_config_action)

        self.serial_config_action = QAction("串口配置", self)
        driver_menu.addAction(self.serial_config_action)

        self.bc_config_action = QAction("1553-BC配置", self)
        driver_menu.addAction(self.bc_config_action)

        settings_menu = menubar.addMenu("设置")
        self.global_settings_action = QAction("路径设置", self)
        self.global_settings_action.setShortcut("Ctrl+S")
        settings_menu.addAction(self.global_settings_action)

    def init_param_tab(self):
        splitter = QSplitter(Qt.Horizontal)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.addWidget(QLabel("步骤列表"))
        left_layout.addWidget(self.step_list_view)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.addWidget(QLabel("步骤详情"))
        right_layout.addWidget(self.step_detail_view)

        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setSizes([200, 600])

        layout = QVBoxLayout(self.param_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter)

    def show_settings_dialog(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        from views.global_config_view import ConfigManager

        dialog = QDialog(self)
        dialog.setWindowTitle("路径设置")
        dialog.setModal(True)
        dialog.resize(600, 300)

        layout = QVBoxLayout(dialog)
        dialog_global_view = GlobalConfigView(dialog)

        try:
            config_manager = ConfigManager()
            config_data = config_manager.get_config()
            dialog_global_view.set_data(config_data)
        except Exception as e:
            print(f"同步配置到对话框视图时出错: {e}")

        layout.addWidget(dialog_global_view)

        # tip_label = QLabel("提示: 输出目录将保存生成的配置文件")
        # tip_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        #layout.addWidget(tip_label)

        dialog.exec_()

        try:
            dialog_config = dialog_global_view.get_data()

            try:
                if hasattr(self, 'global_view') and self.global_view:
                    try:
                        _ = self.global_view.objectName()
                        self.global_view.set_data(dialog_config)
                    except RuntimeError:
                        print("主窗口global_view已失效，重新创建")
                        self.global_view = GlobalConfigView()
                        self.global_view.set_data(dialog_config)
                else:
                    self.global_view = GlobalConfigView()
                    self.global_view.set_data(dialog_config)
            except Exception as e:
                print(f"更新主窗口global_view时出错: {e}")

            if hasattr(self, 'controller') and self.controller:
                try:
                    if hasattr(self.controller, 'global_config_controller'):
                        self.controller.global_config_controller.update_global_model()
                except Exception as e:
                    print(f"更新全局配置控制器时出错: {e}")
        except Exception as e:
            print(f"同步配置时出错: {e}")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
            }
            QTabWidget::pane {
                border: none;
                margin-top: 5px;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #c0c0c0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-color: #a0a0a0;
            }
            QTabBar::tab:hover {
                background: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 10px;
            }
            QPushButton {
                padding: 5px 12px;
                background-color: #e8e8e8;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #d8d8d8;
            }
            QPushButton:pressed {
                background-color: #c8c8c8;
            }
            QLabel {
                font-weight: 500;
            }
        """)

    def closeEvent(self, event):
        try:
            model_dirty = False
            if hasattr(self, 'controller') and hasattr(self.controller, 'model'):
                model_dirty = bool(getattr(self.controller.model, 'is_dirty', lambda: False)())
            if model_dirty:
                reply = QMessageBox.question(
                    self,
                    "未保存的更改",
                    "当前配置尚未保存，确定要关闭吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
        except Exception:
            event.accept()

