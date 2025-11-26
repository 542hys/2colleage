import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTabWidget, QWidget, QMessageBox, QSplitter, QTextEdit, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from utils.bc_config import BcConfig, BcInputIgnoreMode, BcOutputIgnoreMode

class BcConfigDialog(QDialog):
    """BC 配置对话框"""
    
    config_saved = pyqtSignal()  # 配置保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("1553-BC配置")
        self.setModal(True)
        self.resize(800, 600)
        # 禁用窗口标题栏的帮助按钮（问号）
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 从全局设置获取配置文件路径
        from views.global_config_view import ConfigManager
        config_manager = ConfigManager()
        protocol_config = config_manager.get_protocol_config("bc")
        config_path = protocol_config.get("config_path", "")
        
        # 初始化配置管理器
        from utils.bc_config import BcConfig
        if config_path:
            self.bc_config = BcConfig(config_path)
        else:
            from utils.bc_config import get_bc_config, reload_bc_config, _get_default_bc_config_path
            self.default_config_path = _get_default_bc_config_path()
            self.bc_config = reload_bc_config()
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 移除配置路径区域，路径在全局设置中配置
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # BC 输入配置选项卡
        bc_input_tab = self.create_bc_input_tab()
        tab_widget.addTab(bc_input_tab, "输入配置")
        
        # 输出配置选项卡
        output_tab = self.create_output_tab()
        tab_widget.addTab(output_tab, "输出配置")
        
        layout.addWidget(tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self.reset_to_default)
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_bc_input_tab(self):
        """创建 BC 输入配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 忽略模式配置
        mode_group = QGroupBox("BC 输入忽略模式")
        mode_layout = QFormLayout()
        
        self.bc_input_mode_combo = QComboBox()
        self.bc_input_mode_combo.addItems([
            "KEEP_ALL - 保留所有的Bc输出",
            "INCLUDE_BC_INPUT_LIST - 在该模式下BC_INPUT_LIST下的Bc输入被保留，忽略其他输入",
            "EXCLUDE_BC_INPUT_LIST - 在该模式下BC_INPUT_LIST下的Bc输入被排除"
        ])
        self.bc_input_mode_combo.currentIndexChanged.connect(self.on_bc_input_mode_changed)
        
        mode_layout.addRow("忽略模式:", self.bc_input_mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 说明文本
        note_text = QTextEdit()
        note_text.setMaximumHeight(80)
        note_text.setReadOnly(True)
        note_text.setPlainText(
            "注意：只有最后两种模式时BC_INPUT_LIST下的会起作用\n"
            "对于忽略的输入，驱动会直接放回负值，表示读取失败，模拟站点不在的情况"
        )
        layout.addWidget(note_text)
        
        # 输入列表配置
        list_group = QGroupBox("BC 输入列表")
        list_layout = QVBoxLayout()
        
        # 列表控件
        self.bc_input_list = QListWidget()
        self.bc_input_list.setMaximumHeight(200)
        list_layout.addWidget(self.bc_input_list)
        
        # 添加/删除按钮
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加输入")
        add_btn.clicked.connect(self.add_bc_input)
        
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_bc_input)
        
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_bc_input)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # 格式说明
        format_group = QGroupBox("格式说明")
        format_layout = QVBoxLayout()
        
        format_text = QTextEdit()
        format_text.setMaximumHeight(100)
        format_text.setReadOnly(True)
        format_text.setPlainText(
            "支持的格式：\n"
            "• BC输入示例: BcRecv_ID0XD_SA_0x15_Len44\n"
            "• 支持通配符匹配模式"
        )
        format_layout.addWidget(format_text)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_output_tab(self):
        """创建输出配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 忽略模式配置
        mode_group = QGroupBox("输出忽略模式")
        mode_layout = QFormLayout()
        
        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItems([
            "KEEP_ALL - 保留所有的BC输出",
            "IGNORE_ALL - 忽略所有的BC输出",
            "INCLUDE_BC_OUTPUT_LIST - 在该模式下BC_OUTPUT_LIST下BC输出被保留，忽略除BC_OUTPUT_LIST下的其余输出",
            "EXCLUDE_BC_OUTPUT_LIST - 在该模式下BC_OUTPUT_LIST下的BC输出被排除"
        ])
        self.output_mode_combo.currentIndexChanged.connect(self.on_output_mode_changed)
        
        mode_layout.addRow("忽略模式:", self.output_mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 说明文本
        note_text = QTextEdit()
        note_text.setMaximumHeight(60)
        note_text.setReadOnly(True)
        note_text.setPlainText("注意：只有最后两种模式时BC_OUTPUT_LIST下的会起作用")
        layout.addWidget(note_text)
        
        # 输出列表配置
        list_group = QGroupBox("BC 输出列表")
        list_layout = QVBoxLayout()
        
        # 列表控件
        self.bc_output_list = QListWidget()
        self.bc_output_list.setMaximumHeight(200)
        list_layout.addWidget(self.bc_output_list)
        
        # 添加/删除按钮
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加输出")
        add_btn.clicked.connect(self.add_output)
        
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_output)
        
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_output)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # 格式说明
        format_group = QGroupBox("格式说明")
        format_layout = QVBoxLayout()
        
        format_text = QTextEdit()
        format_text.setMaximumHeight(100)
        format_text.setReadOnly(True)
        format_text.setPlainText(
            "支持的格式：\n"
            "• BC输出示例: BcSend_ID0XD_SA_0x15_Len44\n"
            "• 支持通配符匹配模式"
        )
        format_layout.addWidget(format_text)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        widget.setLayout(layout)
        return widget
    
    def load_config(self):
        """加载配置"""
        # 加载 BC 输入模式
        mode_index = 0
        if self.bc_config.input_ignore_mode == BcInputIgnoreMode.INCLUDE_BC_INPUT_LIST:
            mode_index = 1
        elif self.bc_config.input_ignore_mode == BcInputIgnoreMode.EXCLUDE_BC_INPUT_LIST:
            mode_index = 2
        self.bc_input_mode_combo.setCurrentIndex(mode_index)
        
        # 加载 BC 输入列表
        self.bc_input_list.clear()
        for item in self.bc_config.bc_input_list:
            self.bc_input_list.addItem(item)
        
        # 加载输出模式
        output_mode_index = 0
        if self.bc_config.output_ignore_mode == BcOutputIgnoreMode.IGNORE_ALL:
            output_mode_index = 1
        elif self.bc_config.output_ignore_mode == BcOutputIgnoreMode.INCLUDE_BC_OUTPUT_LIST:
            output_mode_index = 2
        elif self.bc_config.output_ignore_mode == BcOutputIgnoreMode.EXCLUDE_BC_OUTPUT_LIST:
            output_mode_index = 3
        self.output_mode_combo.setCurrentIndex(output_mode_index)
        
        # 加载输出列表
        self.bc_output_list.clear()
        for item in self.bc_config.bc_output_list:
            self.bc_output_list.addItem(item)
    
    def save_config(self):
        """保存配置"""
        try:
            # 从全局设置获取配置文件路径
            from views.global_config_view import ConfigManager
            config_manager = ConfigManager()
            protocol_config = config_manager.get_protocol_config("bc")
            config_path = protocol_config.get("config_path", "")
            
            if not config_path:
                QMessageBox.warning(self, "错误", "请在全局设置中配置1553-BC的配置文件路径")
                return
            
            # 更新配置对象的路径
            self.bc_config.config_path = Path(config_path)
            
            # 保存 BC 输入模式
            mode_index = self.bc_input_mode_combo.currentIndex()
            if mode_index == 0:
                self.bc_config.input_ignore_mode = BcInputIgnoreMode.KEEP_ALL
            elif mode_index == 1:
                self.bc_config.input_ignore_mode = BcInputIgnoreMode.INCLUDE_BC_INPUT_LIST
            elif mode_index == 2:
                self.bc_config.input_ignore_mode = BcInputIgnoreMode.EXCLUDE_BC_INPUT_LIST
            
            # 保存 BC 输入列表
            self.bc_config.bc_input_list = []
            for i in range(self.bc_input_list.count()):
                self.bc_config.bc_input_list.append(self.bc_input_list.item(i).text())
            
            # 保存输出模式
            output_mode_index = self.output_mode_combo.currentIndex()
            if output_mode_index == 0:
                self.bc_config.output_ignore_mode = BcOutputIgnoreMode.KEEP_ALL
            elif output_mode_index == 1:
                self.bc_config.output_ignore_mode = BcOutputIgnoreMode.IGNORE_ALL
            elif output_mode_index == 2:
                self.bc_config.output_ignore_mode = BcOutputIgnoreMode.INCLUDE_BC_OUTPUT_LIST
            elif output_mode_index == 3:
                self.bc_config.output_ignore_mode = BcOutputIgnoreMode.EXCLUDE_BC_OUTPUT_LIST
            
            # 保存输出列表
            self.bc_config.bc_output_list = []
            for i in range(self.bc_output_list.count()):
                self.bc_config.bc_output_list.append(self.bc_output_list.item(i).text())
            
            # 保存到文件
            self.bc_config.save_config()
            
            # 显示保存位置
            config_path = str(self.bc_config.config_path) if hasattr(self.bc_config, 'config_path') else '未知路径'
            QMessageBox.information(self, "成功", f"配置已保存到:\n{config_path}")
            self.config_saved.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self, "确认", "确定要重置为默认配置吗？这将清除所有自定义设置。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.bc_config.input_ignore_mode = BcInputIgnoreMode.KEEP_ALL
            self.bc_config.output_ignore_mode = BcOutputIgnoreMode.KEEP_ALL
            self.bc_config.bc_input_list = []
            self.bc_config.bc_output_list = []
            self.load_config()
    
    def on_bc_input_mode_changed(self):
        """BC 输入模式改变"""
        pass  # 可以在这里添加实时预览功能
    
    def on_output_mode_changed(self):
        """输出模式改变"""
        pass  # 可以在这里添加实时预览功能
    
    def add_bc_input(self):
        """添加 BC 输入"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "添加 BC 输入", "输入名称:")
        if ok and text:
            self.bc_input_list.addItem(text)
    
    def edit_bc_input(self):
        """编辑 BC 输入"""
        current_item = self.bc_input_list.currentItem()
        if current_item:
            from PyQt5.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "编辑 BC 输入", "输入名称:", text=current_item.text())
            if ok and text:
                current_item.setText(text)
    
    def delete_bc_input(self):
        """删除 BC 输入"""
        current_row = self.bc_input_list.currentRow()
        if current_row >= 0:
            self.bc_input_list.takeItem(current_row)
    
    def add_output(self):
        """添加输出"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "添加输出", "输出名称:")
        if ok and text:
            self.bc_output_list.addItem(text)
    
    def edit_output(self):
        """编辑输出"""
        current_item = self.bc_output_list.currentItem()
        if current_item:
            from PyQt5.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "编辑输出", "输出名称:", text=current_item.text())
            if ok and text:
                current_item.setText(text)
    
    def delete_output(self):
        """删除输出"""
        current_row = self.bc_output_list.currentRow()
        if current_row >= 0:
            self.bc_output_list.takeItem(current_row)








