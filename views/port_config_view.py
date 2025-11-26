import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTabWidget, QWidget, QMessageBox, QSplitter, QTextEdit, QCheckBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from utils.port_config import PortConfig

class PortConfigDialog(QDialog):
    """中断配置对话框"""
    
    config_saved = pyqtSignal()  # 配置保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("中断配置")
        self.setModal(True)
        self.resize(900, 700)
        # 禁用窗口标题栏的帮助按钮（问号）
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 从全局设置获取配置文件路径
        from views.global_config_view import ConfigManager
        config_manager = ConfigManager()
        protocol_config = config_manager.get_protocol_config("interrupt")
        config_path = protocol_config.get("config_path", "")
        
        # 初始化配置管理器
        from utils.port_config import PortConfig
        if config_path:
            self.port_config = PortConfig(config_path)
        else:
            from utils.port_config import get_port_config, reload_port_config, _get_default_port_config_path
            self.default_config_path = _get_default_port_config_path()
            self.port_config = reload_port_config()
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 移除配置路径区域，路径在全局设置中配置
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 中断周期配置选项卡
        period_tab = self.create_period_tab()
        tab_widget.addTab(period_tab, "中断周期配置")
        
        # 忽略中断配置选项卡
        ignore_tab = self.create_ignore_tab()
        tab_widget.addTab(ignore_tab, "忽略中断配置")
        
        # 单次触发中断配置选项卡
        trigger_tab = self.create_trigger_tab()
        tab_widget.addTab(trigger_tab, "单次触发中断配置")
        
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
    
    def create_period_tab(self):
        """创建中断周期配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 说明文本
        note_text = QTextEdit()
        note_text.setMaximumHeight(80)
        note_text.setReadOnly(True)
        note_text.setPlainText(
            "对中断周期的配置，注意此处只需要配周期性中断，其余均认为是非周期中断\n"
            "格式：中断号=周期值(ms)"
        )
        layout.addWidget(note_text)
        
        # 表格
        table_group = QGroupBox("中断周期列表")
        table_layout = QVBoxLayout()
        
        self.period_table = QTableWidget()
        self.period_table.setColumnCount(2)
        self.period_table.setHorizontalHeaderLabels(["中断号", "周期值(ms)"])
        self.period_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.period_table.setMaximumHeight(300)
        table_layout.addWidget(self.period_table)
        
        # 按钮
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_period_item)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_period_item)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_period_item)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        table_layout.addLayout(button_layout)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # 格式说明
        format_group = QGroupBox("格式说明")
        format_layout = QVBoxLayout()
        format_text = QTextEdit()
        format_text.setMaximumHeight(60)
        format_text.setReadOnly(True)
        format_text.setPlainText("示例：4=5 表示4号中断周期为5ms")
        format_layout.addWidget(format_text)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_ignore_tab(self):
        """创建忽略中断配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 说明文本
        note_text = QTextEdit()
        note_text.setMaximumHeight(60)
        note_text.setReadOnly(True)
        note_text.setPlainText("忽略的中断号列表")
        layout.addWidget(note_text)
        
        # 列表
        list_group = QGroupBox("忽略的中断号")
        list_layout = QVBoxLayout()
        
        self.ignore_list = QListWidget()
        self.ignore_list.setMaximumHeight(300)
        list_layout.addWidget(self.ignore_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_ignore_item)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_ignore_item)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_ignore_item)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_trigger_tab(self):
        """创建单次触发中断配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 说明文本
        note_text = QTextEdit()
        note_text.setMaximumHeight(100)
        note_text.setReadOnly(True)
        note_text.setPlainText(
            "单次触发中断配置\n"
            "对于数据触发的中断可在底层驱动中通过读文件控制数据何时到来，不在此处配置\n"
            "格式：中断号=触发时间(ms)，多个时间用逗号分隔"
        )
        layout.addWidget(note_text)
        
        # 表格
        table_group = QGroupBox("单次触发中断列表")
        table_layout = QVBoxLayout()
        
        self.trigger_table = QTableWidget()
        self.trigger_table.setColumnCount(2)
        self.trigger_table.setHorizontalHeaderLabels(["中断号", "触发时间(ms)，多个用逗号分隔"])
        self.trigger_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trigger_table.setMaximumHeight(300)
        table_layout.addWidget(self.trigger_table)
        
        # 按钮
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_trigger_item)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_trigger_item)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_trigger_item)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        
        table_layout.addLayout(button_layout)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # 格式说明
        format_group = QGroupBox("格式说明")
        format_layout = QVBoxLayout()
        format_text = QTextEdit()
        format_text.setMaximumHeight(60)
        format_text.setReadOnly(True)
        format_text.setPlainText("示例：90=10000,10005,10010,70000 表示90号中断在仿真时间10s、10.005s、10.01s、70s时触发")
        format_layout.addWidget(format_text)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        widget.setLayout(layout)
        return widget
    
    def load_config(self):
        """加载配置"""
        # 加载中断周期配置
        self.period_table.setRowCount(0)
        for int_num, period in sorted(self.port_config.int_period.items()):
            row = self.period_table.rowCount()
            self.period_table.insertRow(row)
            self.period_table.setItem(row, 0, QTableWidgetItem(str(int_num)))
            self.period_table.setItem(row, 1, QTableWidgetItem(str(period)))
        
        # 加载忽略的中断号
        self.ignore_list.clear()
        for int_num in sorted(self.port_config.ignore_int):
            self.ignore_list.addItem(str(int_num))
        
        # 加载单次触发中断配置
        self.trigger_table.setRowCount(0)
        for int_num, times in sorted(self.port_config.single_trigger_int.items()):
            row = self.trigger_table.rowCount()
            self.trigger_table.insertRow(row)
            self.trigger_table.setItem(row, 0, QTableWidgetItem(str(int_num)))
            times_str = ','.join(str(t) for t in times)
            self.trigger_table.setItem(row, 1, QTableWidgetItem(times_str))
    
    def save_config(self):
        """保存配置"""
        try:
            # 从全局设置获取配置文件路径
            from views.global_config_view import ConfigManager
            config_manager = ConfigManager()
            protocol_config = config_manager.get_protocol_config("interrupt")
            config_path = protocol_config.get("config_path", "")
            
            if not config_path:
                QMessageBox.warning(self, "错误", "请在全局设置中配置中断的配置文件路径")
                return
            
            self.port_config.config_path = Path(config_path)
            
            # 保存中断周期配置
            self.port_config.int_period = {}
            for row in range(self.period_table.rowCount()):
                int_item = self.period_table.item(row, 0)
                period_item = self.period_table.item(row, 1)
                if int_item and period_item:
                    try:
                        int_num = int(int_item.text().strip())
                        period = int(period_item.text().strip())
                        if period > 0:
                            self.port_config.int_period[int_num] = period
                    except ValueError:
                        continue
            
            # 保存忽略的中断号
            self.port_config.ignore_int = []
            for i in range(self.ignore_list.count()):
                item = self.ignore_list.item(i)
                if item:
                    try:
                        int_num = int(item.text().strip())
                        self.port_config.ignore_int.append(int_num)
                    except ValueError:
                        continue
            
            # 保存单次触发中断配置
            self.port_config.single_trigger_int = {}
            for row in range(self.trigger_table.rowCount()):
                int_item = self.trigger_table.item(row, 0)
                times_item = self.trigger_table.item(row, 1)
                if int_item and times_item:
                    try:
                        int_num = int(int_item.text().strip())
                        times_str = times_item.text().strip()
                        if times_str:
                            times = [int(t.strip()) for t in times_str.split(',') if t.strip()]
                            if times:
                                self.port_config.single_trigger_int[int_num] = times
                    except ValueError:
                        continue
            
            self.port_config.save_config()
            config_path = str(self.port_config.config_path) if hasattr(self.port_config, 'config_path') else '未知路径'
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
            self.port_config.int_period = {}
            self.port_config.ignore_int = []
            self.port_config.single_trigger_int = {}
            self.load_config()
    
    def add_period_item(self):
        """添加中断周期项"""
        from PyQt5.QtWidgets import QInputDialog
        int_num, ok1 = QInputDialog.getInt(self, "添加中断周期", "中断号:", 0, 0, 65535, 1)
        if ok1:
            period, ok2 = QInputDialog.getInt(self, "添加中断周期", "周期值(ms):", 1, 1, 1000000, 1)
            if ok2:
                row = self.period_table.rowCount()
                self.period_table.insertRow(row)
                self.period_table.setItem(row, 0, QTableWidgetItem(str(int_num)))
                self.period_table.setItem(row, 1, QTableWidgetItem(str(period)))
    
    def edit_period_item(self):
        """编辑中断周期项"""
        current_row = self.period_table.currentRow()
        if current_row >= 0:
            int_item = self.period_table.item(current_row, 0)
            period_item = self.period_table.item(current_row, 1)
            if int_item and period_item:
                from PyQt5.QtWidgets import QInputDialog
                int_num, ok1 = QInputDialog.getInt(self, "编辑中断周期", "中断号:", int(int_item.text()), 0, 65535, 1)
                if ok1:
                    period, ok2 = QInputDialog.getInt(self, "编辑中断周期", "周期值(ms):", int(period_item.text()), 1, 1000000, 1)
                    if ok2:
                        int_item.setText(str(int_num))
                        period_item.setText(str(period))
    
    def delete_period_item(self):
        """删除中断周期项"""
        current_row = self.period_table.currentRow()
        if current_row >= 0:
            self.period_table.removeRow(current_row)
    
    def add_ignore_item(self):
        """添加忽略的中断号"""
        from PyQt5.QtWidgets import QInputDialog
        int_num, ok = QInputDialog.getInt(self, "添加忽略中断", "中断号:", 0, 0, 65535, 1)
        if ok:
            self.ignore_list.addItem(str(int_num))
    
    def edit_ignore_item(self):
        """编辑忽略的中断号"""
        current_item = self.ignore_list.currentItem()
        if current_item:
            from PyQt5.QtWidgets import QInputDialog
            int_num, ok = QInputDialog.getInt(self, "编辑忽略中断", "中断号:", int(current_item.text()), 0, 65535, 1)
            if ok:
                current_item.setText(str(int_num))
    
    def delete_ignore_item(self):
        """删除忽略的中断号"""
        current_row = self.ignore_list.currentRow()
        if current_row >= 0:
            self.ignore_list.takeItem(current_row)
    
    def add_trigger_item(self):
        """添加单次触发中断项"""
        from PyQt5.QtWidgets import QInputDialog
        int_num, ok1 = QInputDialog.getInt(self, "添加单次触发中断", "中断号:", 0, 0, 65535, 1)
        if ok1:
            times_str, ok2 = QInputDialog.getText(self, "添加单次触发中断", "触发时间(ms)，多个用逗号分隔:\n示例: 10000,10005,10010,70000")
            if ok2 and times_str:
                row = self.trigger_table.rowCount()
                self.trigger_table.insertRow(row)
                self.trigger_table.setItem(row, 0, QTableWidgetItem(str(int_num)))
                self.trigger_table.setItem(row, 1, QTableWidgetItem(times_str))
    
    def edit_trigger_item(self):
        """编辑单次触发中断项"""
        current_row = self.trigger_table.currentRow()
        if current_row >= 0:
            int_item = self.trigger_table.item(current_row, 0)
            times_item = self.trigger_table.item(current_row, 1)
            if int_item and times_item:
                from PyQt5.QtWidgets import QInputDialog
                int_num, ok1 = QInputDialog.getInt(self, "编辑单次触发中断", "中断号:", int(int_item.text()), 0, 65535, 1)
                if ok1:
                    times_str, ok2 = QInputDialog.getText(self, "编辑单次触发中断", "触发时间(ms)，多个用逗号分隔:", text=times_item.text())
                    if ok2 and times_str:
                        int_item.setText(str(int_num))
                        times_item.setText(times_str)
    
    def delete_trigger_item(self):
        """删除单次触发中断项"""
        current_row = self.trigger_table.currentRow()
        if current_row >= 0:
            self.trigger_table.removeRow(current_row)





