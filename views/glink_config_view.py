import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTabWidget, QWidget, QMessageBox, QSplitter, QTextEdit, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import re

from utils.glink_config import GLinkConfig, InputIgnoreMode, OutputIgnoreMode


class NCInputDialog(QDialog):
    """NC/NT 输入配置对话框"""
    
    def __init__(self, parent=None, initial_text=None):
        super().__init__(parent)
        self.setWindowTitle("添加 NC/NT 输入")
        self.setModal(True)
        self.resize(400, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.setup_ui()
        
        # 如果提供了初始文本，尝试解析并填充
        if initial_text:
            self.parse_and_fill(initial_text)
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # 第一步：选择nc或nt
        self.type_combo = QComboBox()
        self.type_combo.addItems(["nc", "nt"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form_layout.addRow("类型:", self.type_combo)
        
        # 第一个下拉框：NcRecv或NtRecv
        self.recv_combo = QComboBox()
        self.recv_combo.addItems(["NcRecv"])
        form_layout.addRow("接收类型:", self.recv_combo)
        
        # 第二个输入框：ID字段
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("例如: 0x40A")
        form_layout.addRow("ID:", self.id_edit)
        
        # 第三个输入框：SA字段
        self.sa_edit = QLineEdit()
        self.sa_edit.setPlaceholderText("例如: 0x8")
        form_layout.addRow("SA:", self.sa_edit)
        
        # 第四个输入框：Len字段
        self.len_edit = QLineEdit()
        self.len_edit.setPlaceholderText("例如: 46")
        form_layout.addRow("Len:", self.len_edit)
        
        layout.addLayout(form_layout)
        
        # 预览标签
        self.preview_label = QLabel("预览: ")
        self.preview_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.preview_label)
        
        # 连接输入变化信号以更新预览
        self.type_combo.currentTextChanged.connect(self.update_preview)
        self.recv_combo.currentTextChanged.connect(self.update_preview)
        self.id_edit.textChanged.connect(self.update_preview)
        self.sa_edit.textChanged.connect(self.update_preview)
        self.len_edit.textChanged.connect(self.update_preview)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 初始化预览
        self.update_preview()
    
    def validate_inputs(self):
        """校验 ID/SA/Len 输入格式"""
        id_val = self.id_edit.text().strip()
        sa_val = self.sa_edit.text().strip()
        len_val = self.len_edit.text().strip()

        def _validate_hex(value, label):
            if not value:
                QMessageBox.warning(self, "格式错误", f"{label} 不能为空")
                return False
            if value.lower().startswith("0x"):
                body = value[2:]
            else:
                body = value
            if not body or not re.fullmatch(r"[0-9A-Fa-f]+", body):
                QMessageBox.warning(self, "格式错误", f"{label} 需要是十六进制（例如 0x40A）")
                return False
            return True

        if not _validate_hex(id_val, "ID"):
            return False
        if not _validate_hex(sa_val, "SA"):
            return False
        if not len_val or not len_val.isdigit():
            QMessageBox.warning(self, "格式错误", "Len 需要是十进制数字")
            return False
        return True

    def accept(self):
        """带校验的确认"""
        if not self.validate_inputs():
            return
        super().accept()

    def on_type_changed(self, text):
        """类型改变时更新接收类型下拉框"""
        self.recv_combo.clear()
        if text == "nc":
            self.recv_combo.addItems(["NcRecv"])
        elif text == "nt":
            self.recv_combo.addItems(["NtRecv"])
        self.update_preview()
    
    def update_preview(self):
        """更新预览文本"""
        recv = self.recv_combo.currentText()
        id_val = self.id_edit.text().strip()
        sa_val = self.sa_edit.text().strip()
        len_val = self.len_edit.text().strip()
        
        parts = [recv]
        if id_val:
            # 确保ID格式正确（添加ID前缀，处理0x）
            if id_val.startswith("0x") or id_val.startswith("0X"):
                parts.append(f"ID{id_val}")
            else:
                parts.append(f"ID0x{id_val}")
        if sa_val:
            # 确保SA格式正确
            if sa_val.startswith("0x") or sa_val.startswith("0X"):
                parts.append(f"SA{sa_val}")
            else:
                parts.append(f"SA0x{sa_val}")
        if len_val:
            parts.append(f"Len{len_val}")
        
        preview = "_".join(parts)
        self.preview_label.setText(f"预览: {preview}")
    
    def parse_and_fill(self, text):
        """解析现有文本并填充到表单"""
        # 解析格式：NcRecv_ID0x40A_SA0x8_Len46 或 NtRecv_ID0x40A_SA0x8_Len46
        text = text.strip()
        
        # 判断类型
        if text.upper().startswith("NCRECV"):
            self.type_combo.setCurrentText("nc")
            recv_type = "NcRecv"
        elif text.upper().startswith("NTRECV"):
            self.type_combo.setCurrentText("nt")
            recv_type = "NtRecv"
        else:
            return  # 无法解析
        
        # 设置接收类型
        if self.recv_combo.findText(recv_type) >= 0:
            self.recv_combo.setCurrentText(recv_type)
        
        # 解析ID
        id_match = re.search(r'ID(0x[0-9A-Fa-f]+)', text, re.IGNORECASE)
        if id_match:
            self.id_edit.setText(id_match.group(1))
        
        # 解析SA
        sa_match = re.search(r'SA(0x[0-9A-Fa-f]+)', text, re.IGNORECASE)
        if sa_match:
            self.sa_edit.setText(sa_match.group(1))
        
        # 解析Len
        len_match = re.search(r'Len(\d+)', text, re.IGNORECASE)
        if len_match:
            self.len_edit.setText(len_match.group(1))
    
    def get_result(self):
        """获取生成的名称"""
        recv = self.recv_combo.currentText()
        id_val = self.id_edit.text().strip()
        sa_val = self.sa_edit.text().strip()
        len_val = self.len_edit.text().strip()
        
        if not id_val or not sa_val or not len_val:
            return None
        
        # 格式化ID
        if id_val.startswith("0x") or id_val.startswith("0X"):
            id_str = f"ID{id_val}"
        else:
            id_str = f"ID0x{id_val}"
        
        # 格式化SA
        if sa_val.startswith("0x") or sa_val.startswith("0X"):
            sa_str = f"SA{sa_val}"
        else:
            sa_str = f"SA0x{sa_val}"
        
        # 格式化Len
        len_str = f"Len{len_val}"
        
        return f"{recv}_{id_str}_{sa_str}_{len_str}"


class GLinkConfigDialog(QDialog):
    """GLink 配置对话框"""
    
    config_saved = pyqtSignal()  # 配置保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GLink 配置")
        self.setModal(True)
        self.resize(800, 600)
        # 禁用窗口标题栏的帮助按钮（问号）
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 从全局设置读取配置文件路径
        from views.global_config_view import ConfigManager
        self.config_manager = ConfigManager()
        protocol_config = self.config_manager.get_protocol_config("glink")
        config_path = protocol_config.get("config_path", "..//..//Platform//ExDrivers//GLINK//glink.config")
        
        # 初始化配置管理器（使用全局设置中的路径）
        from utils.glink_config import GLinkConfig
        self.glink_config = GLinkConfig(config_path)
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 移除配置路径区域，路径在全局设置中配置
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # NC 输入配置选项卡
        nc_input_tab = self.create_nc_input_tab()
        tab_widget.addTab(nc_input_tab, "输入配置")
        
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
    
    def create_nc_input_tab(self):
        """创建 NC 输入配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 忽略模式配置
        mode_group = QGroupBox("NC 输入忽略模式")
        mode_layout = QFormLayout()
        
        self.nc_input_mode_combo = QComboBox()
        self.nc_input_mode_combo.addItems([
            "KEEP_ALL - 保留所有 GLink 输入",
            "INCLUDE_NC_INPUT_LIST - 只保留列表中的输入",
            "EXCLUDE_NC_INPUT_LIST - 排除列表中的输入"
        ])
        self.nc_input_mode_combo.currentIndexChanged.connect(self.on_nc_input_mode_changed)
        
        mode_layout.addRow("忽略模式:", self.nc_input_mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 输入列表配置
        list_group = QGroupBox("NC 输入列表")
        list_layout = QVBoxLayout()
        
        # 列表控件
        self.nc_input_list = QListWidget()
        self.nc_input_list.setMaximumHeight(200)
        list_layout.addWidget(self.nc_input_list)
        
        # 添加/删除按钮
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加输入")
        add_btn.clicked.connect(self.add_nc_input)
        
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_nc_input)
        
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_nc_input)
        
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
            "• 1对1 NC输入: NcRecv_ID0x40A_SA0x8_Len46\n"
            "• 1对4 NC输入: NCRecv_ID41-0x401_SA0x120_Len32"
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
            "KEEP_ALL - 保留所有的 GLink 输出",
            "IGNORE_ALL - 忽略所有的 GLink 输出",
            "INCLUDE_OUTPUT_LIST - 只保留列表中的输出",
            "EXCLUDE_OUTPUT_LIST - 排除列表中的输出"
        ])
        self.output_mode_combo.currentIndexChanged.connect(self.on_output_mode_changed)
        
        mode_layout.addRow("忽略模式:", self.output_mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 输出列表配置
        list_group = QGroupBox("输出列表")
        list_layout = QVBoxLayout()
        
        # 列表控件
        self.output_list = QListWidget()
        self.output_list.setMaximumHeight(200)
        list_layout.addWidget(self.output_list)
        
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
            "• 对ID号子地址所有消息: NcSend_ID0x40A_SA0x8\n"
            "• 对ID号子地址长度单条消息: NcSend_ID0x40A_SA0x8_Len46\n"
            "• 1对4输出: NcSend_ID41-0x401_SA0x120_Len32"
        )
        format_layout.addWidget(format_text)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        widget.setLayout(layout)
        return widget
    
    def load_config(self):
        """加载配置"""
        # 配置文件路径从全局设置读取，不需要在界面显示
        
        # 加载 NC 输入模式
        mode_index = 0
        if self.glink_config.input_ignore_mode == InputIgnoreMode.INCLUDE_NC_INPUT_LIST:
            mode_index = 1
        elif self.glink_config.input_ignore_mode == InputIgnoreMode.EXCLUDE_NC_INPUT_LIST:
            mode_index = 2
        self.nc_input_mode_combo.setCurrentIndex(mode_index)
        
        # 加载 NC 输入列表
        self.nc_input_list.clear()
        for item in self.glink_config.nc_input_list:
            self.nc_input_list.addItem(item)
        
        # 加载输出模式
        output_mode_index = 0
        if self.glink_config.output_ignore_mode == OutputIgnoreMode.IGNORE_ALL:
            output_mode_index = 1
        elif self.glink_config.output_ignore_mode == OutputIgnoreMode.INCLUDE_OUTPUT_LIST:
            output_mode_index = 2
        elif self.glink_config.output_ignore_mode == OutputIgnoreMode.EXCLUDE_OUTPUT_LIST:
            output_mode_index = 3
        self.output_mode_combo.setCurrentIndex(output_mode_index)
        
        # 加载输出列表
        self.output_list.clear()
        for item in self.glink_config.output_list:
            self.output_list.addItem(item)
    
    def save_config(self):
        """保存配置"""
        try:
            # 从全局设置获取配置文件路径
            protocol_config = self.config_manager.get_protocol_config("glink")
            config_path = protocol_config.get("config_path", "..//..//Platform//ExDrivers//GLINK//glink.config")
            
            # 更新配置对象的路径
            self.glink_config.config_path = Path(config_path)
            
            # 保存 NC 输入模式
            mode_index = self.nc_input_mode_combo.currentIndex()
            if mode_index == 0:
                self.glink_config.input_ignore_mode = InputIgnoreMode.KEEP_ALL
            elif mode_index == 1:
                self.glink_config.input_ignore_mode = InputIgnoreMode.INCLUDE_NC_INPUT_LIST
            elif mode_index == 2:
                self.glink_config.input_ignore_mode = InputIgnoreMode.EXCLUDE_NC_INPUT_LIST
            
            # 保存 NC 输入列表
            self.glink_config.nc_input_list = []
            for i in range(self.nc_input_list.count()):
                self.glink_config.nc_input_list.append(self.nc_input_list.item(i).text())
            
            # 保存输出模式
            output_mode_index = self.output_mode_combo.currentIndex()
            if output_mode_index == 0:
                self.glink_config.output_ignore_mode = OutputIgnoreMode.KEEP_ALL
            elif output_mode_index == 1:
                self.glink_config.output_ignore_mode = OutputIgnoreMode.IGNORE_ALL
            elif output_mode_index == 2:
                self.glink_config.output_ignore_mode = OutputIgnoreMode.INCLUDE_OUTPUT_LIST
            elif output_mode_index == 3:
                self.glink_config.output_ignore_mode = OutputIgnoreMode.EXCLUDE_OUTPUT_LIST
            
            # 保存输出列表
            self.glink_config.output_list = []
            for i in range(self.output_list.count()):
                self.glink_config.output_list.append(self.output_list.item(i).text())
            
            # 保存到文件
            self.glink_config.save_config()
            
            # 显示保存位置
            config_path = str(self.glink_config.config_path) if hasattr(self.glink_config, 'config_path') else '未知路径'
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
            self.glink_config.input_ignore_mode = InputIgnoreMode.KEEP_ALL
            self.glink_config.output_ignore_mode = OutputIgnoreMode.KEEP_ALL
            self.glink_config.nc_input_list = []
            self.glink_config.output_list = []
            self.load_config()
    
    def on_nc_input_mode_changed(self):
        """NC 输入模式改变"""
        pass  # 可以在这里添加实时预览功能
    
    def on_output_mode_changed(self):
        """输出模式改变"""
        pass  # 可以在这里添加实时预览功能
    
    def add_nc_input(self):
        """添加 NC 输入"""
        dialog = NCInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self.nc_input_list.addItem(result)
            else:
                QMessageBox.warning(self, "警告", "请填写所有字段（ID、SA、Len）")
    
    def edit_nc_input(self):
        """编辑 NC 输入"""
        current_item = self.nc_input_list.currentItem()
        if current_item:
            dialog = NCInputDialog(self, initial_text=current_item.text())
            if dialog.exec_() == QDialog.Accepted:
                result = dialog.get_result()
                if result:
                    current_item.setText(result)
                else:
                    QMessageBox.warning(self, "警告", "请填写所有字段（ID、SA、Len）")
        else:
            QMessageBox.information(self, "提示", "请先选择要编辑的项")
    
    def delete_nc_input(self):
        """删除 NC 输入"""
        current_row = self.nc_input_list.currentRow()
        if current_row >= 0:
            self.nc_input_list.takeItem(current_row)
    
    def add_output(self):
        """添加输出"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "添加输出", "输出名称:")
        if ok and text:
            self.output_list.addItem(text)
    
    def edit_output(self):
        """编辑输出"""
        current_item = self.output_list.currentItem()
        if current_item:
            from PyQt5.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "编辑输出", "输出名称:", text=current_item.text())
            if ok and text:
                current_item.setText(text)
    
    def delete_output(self):
        """删除输出"""
        current_row = self.output_list.currentRow()
        if current_row >= 0:
            self.output_list.takeItem(current_row) 


