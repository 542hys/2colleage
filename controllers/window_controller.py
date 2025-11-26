from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMessageBox, QWidget, QFormLayout, QLabel, QLineEdit, QComboBox, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class WindowController:
    def __init__(self, model, main_window):
        '''初始化窗口控制器，负责窗口信息的统一管理'''
        self.model = model
        self.main_window = main_window

    def connect_signals(self):
        # 檢查 exit_action 是否存在，如果存在則連接信號
        if hasattr(self.main_window, 'exit_action'):
            self.main_window.exit_action.triggered.connect(self.exit_app)

    def update_window_title(self):
        """更新窗口标题"""
        title = "流程配置工具"
        if self.model.file_path:
            file_name = Path(self.model.file_path).name
            title += f" - {file_name}"
        
        if self.model.is_dirty():
            title += " *"
        
        self.main_window.setWindowTitle(title)
    
    def exit_app(self):
        """退出应用程序"""
        if self.model.is_dirty():
            reply = QMessageBox.question(
                self.main_window, "未保存的更改",
                "当前配置有未保存的更改，是否保存?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_config()
            elif reply == QMessageBox.Cancel:
                return
        
        QApplication.quit()

    def is_form_layout_valid(self):
        """检查form_layout是否仍然有效"""
        try:
            # 尝试访问form_layout的属性
            _ = self.form_layout.rowCount()
            return True
        except RuntimeError:
            return False
    
    def recreate_form_layout(self):
        """重新创建form_layout"""
        try:
            # 重新创建form_container和form_layout
            self.form_container = QWidget()
            self.form_layout = QFormLayout(self.form_container)
            self.form_container.setLayout(self.form_layout)
            self.scroll_area.setWidget(self.form_container)
            print("重新创建了form_layout")
        except Exception as e:
            print(f"重新创建form_layout失败: {e}")

    def clear(self):
        """清除详情显示"""
        self.field_widgets.clear()
        self.step_type_widgets.clear()
        
        if self.is_form_layout_valid():
            while self.form_layout.rowCount():
                self.form_layout.removeRow(0)
        else:
            print("form_layout无效，跳过清除操作")

    def refresh_fields(self, smodel=None, init=False):
        if smodel:
            self.smodel = smodel
        
        # 检查form_layout是否有效
        if not self.is_form_layout_valid():
            print("form_layout无效，重新创建")
            self.recreate_form_layout()
        
        #清空原有的widgets
        try:
            while self.form_layout.rowCount():
                self.form_layout.removeRow(0)
        except RuntimeError:
            print("清除form_layout时出错，重新创建")
            self.recreate_form_layout()
            
        self.field_widgets.clear()
        #基础字段widgets
        basic_list = step_model.BASIC_TYPE_FIELDS
        self.get_field_wigets(basic_list)
        # 当前行
        self.upper_row_count = self.form_layout.rowCount()
        # 进行下半部分对应流程步类型字段的刷新
        self.refresh_lower_fields(init)

    def get_field_wigets(self, FIELD_LIST, step_type=None):
        # 检查form_layout是否有效
        if not self.is_form_layout_valid():
            print("get_field_wigets: form_layout无效，重新创建")
            self.recreate_form_layout()
            
        for field in FIELD_LIST:
            try:
                # 获取字段标签
                label = step_model.get_field_label(field)
                # 获取字段数据类型与默认值
                dtype = step_model.get_field_type(field)
                default = step_model.get_field_default(field)
                # 从step_data中获取当前值，若无则置为默认值
                value = self.smodel.get_value(field, default)
                if dtype == COMBO:#组合选项
                    widget = self.get_combo_widget(field=field, value=value)
                elif dtype == "union":
                    widget = self.get_union_widgets()
                    widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
                else:
                    widget = QLineEdit(str(value))
                    widget.editingFinished.connect(lambda:self.on_edit_finished(widget, dtype))
                
                self.form_layout.addRow(QLabel(label), widget)
                self.field_widgets[field] = widget
                #在step_type的widget绑定改变信号以刷新下半部分字段
                if field == STYPE:
                    widget.currentIndexChanged.connect(self.on_step_type_changed)
                elif field == "protocol_type":
                    # 这里可以添加协议类型的改变信号
                    widget.currentIndexChanged.connect(self.on_protocol_type_changed)
            except RuntimeError as e:
                print(f"添加字段 {field} 时出错: {e}")
                # 尝试重新创建form_layout
                if not self.is_form_layout_valid():
                    self.recreate_form_layout()
                    # 重新尝试添加这个字段
                    try:
                        self.form_layout.addRow(QLabel(label), widget)
                        self.field_widgets[field] = widget
                    except RuntimeError:
                        print(f"重新添加字段 {field} 仍然失败")

    def refresh_lower_fields(self, init=False):
        # 检查form_layout是否有效
        if not self.is_form_layout_valid():
            print("refresh_lower_fields: form_layout无效，重新创建")
            self.recreate_form_layout()
            return
            
        # 1. 移除下半部分所有行
        try:
            while self.form_layout.rowCount() > self.upper_row_count:
                self.form_layout.removeRow(self.upper_row_count)
        except RuntimeError:
            print("移除下半部分行时出错，重新创建form_layout")
            self.recreate_form_layout()
            return

        # 2. 获取当前step_type
        step_type = self.smodel.get_base_step_data().get(STYPE, 0)
        
        # 非初始化时从widget获取
        if not init:
            step_type_widget = self.field_widgets.get(STYPE)
            if isinstance(step_type_widget, QComboBox):
                step_type = step_type_widget.currentData()
        else:
            step_type = self.smodel.get_step_type()
            
        if self.step_type != step_type:
            self.type_step_data.clear()
            self.step_type = step_type

        # 3. 添加字段widgets
        try:
            # 如果有缓存，直接用
            if step_type in self.step_type_widgets:
                widgets_dict = self.step_type_widgets[step_type]
                #添加到表单
                for field, widget in widgets_dict.items():
                    label = step_model.get_field_label(field)
                    self.form_layout.addRow(QLabel(label), widget)
                    self.field_widgets[field] = widget
            else:
                # 获取字段列表
                print(f"dialog refresh_lower_fields step_type: {step_type}")
                step_type_fields = step_model.get_step_type_field_list(n=step_type)
                # 获取对应widget
                self.get_field_wigets(step_type_fields)
        except RuntimeError as e:
            print(f"添加字段widgets时出错: {e}")
            return

        # 4. 处理协议模板
        try:
            if self.template_manager.is_step_type_template_valid(step_type):
                self.on_protocol_type_changed(init=init)
            else:
                self.reomove_protocol_template_area()
        except RuntimeError as e:
            print(f"处理协议模板时出错: {e}")