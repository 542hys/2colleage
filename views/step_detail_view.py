import sys
import json
import struct
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QFormLayout, QLineEdit, QComboBox, QPushButton, QListWidget,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QAction, QFileDialog,
    QDialog, QLabel, QTextEdit, QDialogButtonBox, QListWidgetItem, QSplitter,
    QMessageBox, QInputDialog, QTableWidget, QHeaderView, QTableWidgetItem, QAbstractScrollArea, QSizePolicy
)
import json
from PyQt5.QtWidgets import QLineEdit, QComboBox, QLabel, QScrollArea, QWidget, QVBoxLayout, QFormLayout
from models import template_manager
from models.step_model import (COMBO,
                              BASIC_TYPE_FIELDS, STYPE, DTYPE)
from PyQt5.QtCore import Qt, QRectF, QPointF, QStandardPaths, pyqtSignal, QEvent
from PyQt5.QtGui import QBrush, QColor, QPen, QPainter, QFont, QIcon
from models.step_model import GLINK_REQUIRED_FIELDS, FIELD_LABELS, FIELD_TYPES
#注意读取数据详情不要硬编码
#注意错误处理
import models.step_model as step_model
from models.step_model import StepModel,DETAIL_STRINGS
from utils import conf
from utils.protocol_template_utils import (
    calc_crc_tail_metrics,
    calc_serial_extended_metrics,
    calc_serial_standard_metrics,
    normalize_data_region_value,
)


class NoWheelComboBox(QComboBox):
    """禁用滚轮的QComboBox"""
    def wheelEvent(self, event):
        # 忽略滚轮事件，禁用滚轮改变选项
        event.ignore()


class StepDetailView(QGroupBox):
    step_save_signal = pyqtSignal()
    def __init__(self, step_data=None, parent=None, smodel:StepModel=None):
        super().__init__("流程步详情", parent)
        self.STRINGS = conf.get_config_strings()["dialog"]# 获取配置字符串
        
        self.smodel = smodel
        # print(self.STRINGS["window_titles"]["step_config"])
        self.setWindowTitle("流程步详情")
        # self.setFixedSize(600, 500)
        self.step_data = step_data.copy() if step_data else {}
        self.union_table_header = ["数据类型","值"]
        self.step_type = 0

        self.base_step_data = {}
        self.type_step_data = {}
        self.expand_step_data = {}

        self.union_table_data = {}
        
        #滚动条区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        #基础字段所占行数,用来刷新对应step_type的下半部分
        self.upper_row_count = 0
        #表单容器
        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        self.layout = QVBoxLayout()
        # 用来管理表单中对应的字段widget
        self.field_widgets = {}
        self.step_type_widgets = {}  # key: step_type, value: {field: widget}
        # self.field_widgets_list = {}
        
        self.form_container.setLayout(self.form_layout)

        self.scroll_area.setWidget(self.form_container)
        self.layout.addWidget(self.scroll_area)
        # self.refresh_fields()
        # add_btn = QPushButton(self.STRINGS["button_text"]["add_field"])
        # add_btn = QPushButton("添加")
        # add_btn.clicked.connect(self.add_field_dialog)
        # 注意：self.form_layout 已經設為 form_container 的 layout，
        # 不能再次加入 self.layout，否則會導致 QObject 父子關係錯誤
        # self.layout.addWidget(add_btn)

        self.btn_row_confirm = QHBoxLayout()
        # 应该两个按钮都连接edit_finish信号？ save连接获取数据信号
        # controller接受到信号后，获取数据并刷新list和detail
        save_btn = QPushButton("更新全局数据") 
        cancel_btn = QPushButton("取消")

        # 如果连接函数里不用lambda直接加括号会先调用再返回，连接应当在controller里，这里方便快速实现
        save_btn.clicked.connect(self.on_step_save)
        cancel_btn.clicked.connect(self.on_step_cancel)

        self.btn_row_confirm.addWidget(save_btn)
        self.btn_row_confirm.addWidget(cancel_btn)
        self.layout.addLayout(self.btn_row_confirm)
        


        # button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        # button_box.accepted.connect(self.accept)
        # button_box.rejected.connect(self.reject)
        # self.layout.addWidget(button_box)
        self.template_manager = template_manager.template_manager    #单例模式
        self.model = None  # 用于访问所有流程步的model引用，由controller设置
        self.setLayout(self.layout)
        # self.add_protocol_template_area()
    
    def set_model(self, model):
        """设置model引用，用于访问所有流程步"""
        self.model = model
    
    # text2value应该放到step_model里，16进制和8进制转换成dtype也可以放进这里面
    # 默认的时间好像有问题
    # 类型错误没有处理
    #     
    def text2value(self, text, dtype):
        '''
        text: 要转化的字符串
        dtype: 要求的形式 如"double"
        '''
        if text == 'None':
            return text
        # 容错：将常见的误输入“×”、“Ｘ”替换为“x”，去除空白
        s = str(text).strip().replace('×', 'x').replace('Ｘ', 'x').replace('０x', '0x').replace('０X', '0x')
        try:
            # 若 dtype 为索引，转换为字符串类型名；否则用其字符串
            dtype_str = step_model.SUPPORTED_DTYPES[dtype] if isinstance(dtype, int) and 0 <= dtype < len(step_model.SUPPORTED_DTYPES) else str(dtype)
            dtype_str = dtype_str.upper().strip()

            # 数值类型：支持十六进制与十进制
            if dtype_str in ("UINT", "UINT8", "UINT16", "UINT32", "UINT64", "INT8", "INT16", "INT32", "INT64"):
                t = s
                # 支持全角0x写法纠正后统一处理
                if t.lower().startswith('0x'):
                    v = int(t, 16)
                else:
                    # 允许输入小数但按整数截断
                    v = int(float(t))
                return v

            # 浮点数类型
            if dtype_str in ("FLOAT", "DOUBLE", "REAL32", "REAL64"):
                return float(s)

            # 布尔类型
            if dtype_str in ("BOOL", "BOOLEAN"):
                low = s.lower()
                if low in ("true", "1", "yes", "t"):
                    return True
                if low in ("false", "0", "no", "f"):
                    return False
                return s  # 未知则原样返回

            # 其它类型按字符串返回
            return s
        except Exception:
            # 任意异常均不抛出，直接原样返回，避免界面崩溃
            return s
    
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
    
    def is_widget_valid(self, widget):
        """检查widget是否仍然有效"""
        if widget is None:
            return False
        try:
            # 尝试访问widget的属性来检查是否仍然有效
            if hasattr(widget, 'text'):
                _ = widget.text()  # 对于QLineEdit等有text方法的widget
            elif hasattr(widget, 'currentData'):
                _ = widget.currentData()  # 对于QComboBox等有currentData方法的widget
            return True
        except RuntimeError:
            return False
    
    def get_widget_value_safely(self, widget, dtype, field=None):
        """安全地获取widget的值
        field: 字段名（如"local_site"），用于特殊处理某些字段
        """
        if not self.is_widget_valid(widget):
            print(f"Widget已失效，使用默认值")
            return step_model.get_field_default(dtype) if dtype != "union" else []
        
        try:
            if dtype == COMBO:
                value = widget.currentData()
                if value is None:
                    value = widget.currentText()
                return value
            elif hasattr(widget, 'line_edit'):
                # file_path widget
                return widget.line_edit.text()
            elif dtype == "union":
                # 处理union类型
                table = widget.findChild(QTableWidget)
                if table is None:
                    return []
                union_data = []
                for row in range(table.rowCount()):
                    combo = table.cellWidget(row, 1)
                    edit = table.cellWidget(row, 2)
                    if combo is not None and edit is not None and self.is_widget_valid(combo) and self.is_widget_valid(edit):
                        raw = str(edit.text()).strip().replace('×', 'x').replace('Ｘ', 'x')
                        union_data.append({
                            "data_type": combo.currentData(),
                            "value": raw
                        })
                return union_data
            else:
                # 对于local_site、recip_site、sub_address字段，保留原始字符串格式
                if field in ("local_site", "recip_site", "sub_address", "base_address"):
                    text = widget.text().strip()
                    if not text:
                        return ""
                    # 如果显示格式是"数字 (0x数字)"，提取原始输入
                    if ' (' in text and text.endswith(')'):
                        # 可能是格式化后的显示，尝试保留原始格式
                        # 但这里我们只返回原始文本（去掉格式化后缀）
                        text = text.split(' (')[0]
                    # 直接返回用户输入的文本（保留0x前缀）
                    print(f"get_widget_value_safely {field}: 用户输入 '{text}'，返回字符串")
                    return text  # 保留原始字符串格式
                return self.text2value(widget.text(), dtype)
        except RuntimeError as e:
            print(f"获取widget值时出错: {e}")
            return step_model.get_field_default(dtype) if dtype != "union" else []
        
    def validate_numeric_input(self, text, field_name=""):
        """验证输入是否为有效的十进制或十六进制数字
        返回: (is_valid, error_message, parsed_value)
        is_valid: bool, 是否有效
        error_message: str, 错误信息（如果无效）
        parsed_value: int, 解析后的整数值（如果有效）
        """
        if not text or not text.strip():
            return True, "", None  # 空值视为有效（允许为空）
        
        text = text.strip()
        # 规范常见误输入（全角转半角）
        text = text.replace('×', 'x').replace('Ｘ', 'x').replace('Ｘ', 'x')
        
        try:
            # 检查是否为十六进制格式（0x或0X开头）
            if text.lower().startswith('0x'):
                # 验证十六进制格式
                hex_part = text[2:].strip()
                if not hex_part:
                    return False, f"请输入有效的十六进制数字（格式：0xXXXX）", None
                # 检查是否只包含十六进制字符
                if not all(c in '0123456789abcdefABCDEF' for c in hex_part):
                    return False, f"十六进制格式错误，只能包含0-9和A-F（格式：0xXXXX）", None
                try:
                    value = int(text, 16)
                    return True, "", value
                except ValueError:
                    return False, f"无法解析十六进制数字：{text}", None
            else:
                # 尝试作为十进制解析
                # 检查是否只包含数字和可能的负号
                if text.startswith('-'):
                    # 允许负数（虽然站点号等通常是无符号的，但这里先允许）
                    if not text[1:].strip().isdigit():
                        return False, f"请输入有效的十进制数字", None
                else:
                    if not text.replace('.', '').replace('-', '').isdigit():
                        return False, f"请输入有效的十进制或十六进制数字（十进制格式：123，十六进制格式：0x123）", None
                try:
                    # 尝试解析为整数（如果是浮点数，取整数部分）
                    value = int(float(text))
                    return True, "", value
                except ValueError:
                    return False, f"无法解析数字：{text}，请输入有效的十进制或十六进制数字", None
        except Exception as e:
            return False, f"输入格式错误：{str(e)}，请输入有效的十进制或十六进制数字", None
    
    def validate_float_input(self, text, field_name=""):
        """验证输入是否为有效的浮点数
        返回: (is_valid, error_message, parsed_value)
        is_valid: bool, 是否有效
        error_message: str, 错误信息（如果无效）
        parsed_value: float, 解析后的浮点数值（如果有效）
        """
        if not text or not text.strip():
            return True, "", None  # 空值视为有效（允许为空）
        
        text = text.strip()
        
        try:
            # 检查是否只包含数字、小数点、负号和科学计数法符号
            # 移除所有允许的字符后，应该为空或只包含空格
            allowed_chars = set('0123456789.-+eE')
            if not all(c in allowed_chars or c.isspace() for c in text):
                return False, f"{field_name}输入错误：只能包含数字、小数点、负号和科学计数法符号（如：123.45 或 1.23e-4）", None
            
            # 尝试解析为浮点数
            try:
                value = float(text)
                return True, "", value
            except ValueError:
                return False, f"{field_name}输入错误：无法解析为浮点数，请输入有效的数字（如：123.45 或 1.23）", None
        except Exception as e:
            return False, f"{field_name}输入格式错误：{str(e)}，请输入有效的浮点数（如：123.45）", None
    
    def validate_float_field_input(self, widget, dtype, element):
        """验证浮点数字段的输入（用于仿真时间和周期字段）"""
        if not isinstance(widget, QLineEdit):
            return
        
        text = widget.text().strip()
        field_label = step_model.get_field_label(element) if element else "该字段"
        
        # 如果为空，允许（使用默认值）
        if not text:
            widget.setProperty("last_valid_value", "")
            widget.setStyleSheet("")
            return
        
        # 验证输入格式
        is_valid, error_msg, parsed_value = self.validate_float_input(text, field_label)
        
        if not is_valid:
            # 显示错误提示
            QMessageBox.warning(
                self,
                "输入格式错误",
                f"{error_msg}\n\n"
                f"请输入有效的浮点数（如：123.45 或 1.23）"
            )
            # 恢复上次有效值
            last_valid = widget.property("last_valid_value")
            if last_valid is None:
                last_valid = ""
            widget.setText(str(last_valid))
            widget.setFocus()
            widget.setStyleSheet("color: red;")
            return
        
        # 输入有效，更新保存的值
        widget.setProperty("last_valid_value", text)
        widget.setStyleSheet("")
        # 保存到model
        try:
            if element == "time":
                self.smodel.set_value("time", parsed_value)
            elif element == "period":
                self.smodel.set_value("period", parsed_value)
        except Exception as e:
            print(f"保存{element}值失败: {e}")
        print(f"validate_float_field_input: {element} 输入有效: '{text}' -> {parsed_value}")
    
    def safe_hex_to_int(self, hex_str):
        """安全地将十六进制字符串转换为整数，处理0x前缀"""
        if not hex_str:
            return 0
        try:
            # 移除空格并转为小写
            hex_str = str(hex_str).strip().lower()
            # 规范常见误输入
            hex_str = hex_str.replace('×', 'x').replace('Ｘ', 'x')
            
            # 处理0x前缀
            if hex_str.startswith('0x'):
                return int(hex_str, 16)
            else:
                # 尝试作为十六进制解析
                try:
                    return int(hex_str, 16)
                except ValueError:
                    # 如果十六进制解析失败，尝试作为十进制
                    return int(float(hex_str))
        except (ValueError, TypeError) as e:
            print(f"无法转换十六进制字符串: {hex_str}, 错误: {e}")
            return 0

    def get_data_region_from_step(self):
        """从流程步详情中获取数据区字段的值"""
        raw_value = self.smodel.get_value("data_region", "")
        return normalize_data_region_value(raw_value)
    
    def clear(self):
        """清除详情显示"""
        self.field_widgets.clear()
        self.step_type_widgets.clear()
        
        if self.is_form_layout_valid():
            while self.form_layout.rowCount():
                self.form_layout.removeRow(0)
        else:
            print("form_layout无效，跳过清除操作")
    
    #生成union_widget
    def get_union_widgets(self):   
        """从smodel中取出数据生成union widget"""    
        table = QTableWidget()
        # 设置列数（增加序号列）
        table.setColumnCount(len(self.union_table_header) + 1)  # 增加序号列
        table.setHorizontalHeaderLabels(["序号"] + self.union_table_header)  # 添加序号列标题
        
        # 设置列宽策略
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 序号列自适应内容
        for i in range(1, table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)  # 其他列拉伸填充
        
        table.verticalHeader().setVisible(False)
        table.setRowCount(0)
        
        # 设置表格高度策略，确保所有行可见
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏垂直滚动条

        # 如果有已保存的数据，填充到表格
        union_table_data = self.smodel.get_union_data()
        if self.smodel.get_union_data():
            for item in union_table_data:
                data_type = item.get("data_type")
                
                value = item.get("value", "")
                print(f"data_type is {data_type}, value is {value}")
                self.add_union_row(table, data_type, value)

        vbox = QVBoxLayout()  
        vbox.addWidget(table)
        hbox = QHBoxLayout()
        # 上方插入
        insert_above_btn = QPushButton("上方插入")
        insert_above_btn.clicked.connect(lambda: self.add_union_row(table, insert_at=(table.currentRow() if table.currentRow() >= 0 else 0)))
        # 下方插入
        insert_below_btn = QPushButton("下方插入")
        insert_below_btn.clicked.connect(lambda: self.add_union_row(table, insert_at=(table.currentRow() + 1 if table.currentRow() >= 0 else table.rowCount())))
        # 删除
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(lambda: self.remove_union_row(table))
        hbox.addWidget(insert_above_btn)
        hbox.addWidget(insert_below_btn)
        hbox.addWidget(del_btn)
        hcontainer = QWidget()
        hcontainer.setLayout(hbox)
        vbox.addWidget(hcontainer)

        #用容器widget将垂直布局封起来以便添加到主布局
        container = QWidget()
        container.setLayout(vbox)
        
        # self.adjust_table_height(table, container)
    
        return container

    def adjust_table_height(self, table, container=None):
        """调整表格高度以适应所有行"""
        # 计算总高度
        height = 0
        
        # 添加行高
        for row in range(table.rowCount()):
            height += table.rowHeight(row)
        
        # 添加表头高度
        if table.horizontalHeader().isVisible():
            height += table.horizontalHeader().height()
        
        # 添加边框高度
        height += 5 * table.frameWidth()
        
        # 设置表格高度
        table.setFixedHeight(height)
        
        # 如果提供了容器，也调整容器高度
        if container:
            # 计算容器总高度 = 表格高度 + 按钮高度 + 布局间距
            container_height = height + 100  # 40 是按钮区域的大致高度
            
            # 设置容器的最小高度
            container.setMinimumHeight(container_height)
            container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # 设置滚动条策略

        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    
    def add_union_row(self, table, data_type=None, value=None, insert_at=None):
        """根据给定的数据添加union widget中的一行；若提供 insert_at，则在该位置插入，否则追加"""
        # 目标插入位置
        row = table.rowCount() if insert_at is None else max(0, min(insert_at, table.rowCount()))
        table.insertRow(row)

        # 添加序号列（只读）
        index_item = QTableWidgetItem(str(row + 1))
        index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)  # 设置为只读
        table.setItem(row, 0, index_item)  # 第一列为序号
        # 下拉框（使用禁用滚轮的自定义类）
        combo = NoWheelComboBox()
        # 从step_model中获取支持的数据结构类型
        options = step_model.get_combo_options("data_type")
       # 为下拉框添加选项和值
        for opt in options:
            opt_label, opt_value = step_model.get_combo_opt_label_value(opt)
            combo.addItem(opt_label, opt_value)
        # 设置选中项
        if data_type is not None:
            idx = combo.findData(data_type)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        table.setCellWidget(row, 1, combo)
        # 设置编辑框中的值
        if value is None:
            # 默认值
            value = step_model.get_field_default(step_model.SUPPORTED_DTYPES[0])
        # print(f"add_table_row\n data_type is {data_type}\n value is {value}")
        edit = QLineEdit(str(value))
        # 保留用户原始输入（支持十进制与0x十六进制），不做格式化
        # 保存初始值作为有效值
        edit.setProperty("last_valid_value", str(value))
        edit.editingFinished.connect(self.save_union_table_to_model)
        # 这里用lambda方便连接时传输参数
        combo.currentIndexChanged.connect(lambda: (self.on_combo_changed(combo, edit), self.save_union_table_to_model()))
        # 将当前新加的行加入到table中
        table.setCellWidget(row, 2, edit)  
        # 新增行后立即保存
        self.save_union_table_to_model()
        # 重新编号
        for i in range(table.rowCount()):
            index_item = table.item(i, 0)
            if index_item:
                index_item.setText(str(i + 1))

    def on_combo_changed(self, combo, edit):
        """union行combo改变时自动改变后面编辑框的内容为默认值"""
        if combo is not None:
            opt_value = combo.currentData()
        # 获取默认值
            value = step_model.get_field_default(step_model.SUPPORTED_DTYPES[opt_value])
            edit.setText(str(value))
        # 其实应该进行刷新
    
    def remove_union_row(self, table):
        """移除选中行并更新序号"""
        # 获取当前选中的行
        selected = table.currentRow()
        if selected >= 0:
            table.removeRow(selected)
            
            # 更新后续行的序号
            for row in range(selected, table.rowCount()):
                index_item = table.item(row, 0)
                if index_item:
                    index_item.setText(str(row + 1))
            
            # 调整表格高度
            # self.adjust_table_height(table)
            # 立即保存
            self.save_union_table_to_model()

    def get_union_field_name(self):
        """查找當前 step_type 中的 union 字段名稱"""
        try:
            step_type_fields = step_model.get_step_type_field_list(n=self.step_type)
            for field in step_type_fields:
                if step_model.get_field_type(field) == "union":
                    return field
        except Exception:
            pass
        return None

    def save_union_table_to_model_safe(self):
        """安全地保存union表格内容到StepModel（检查widget是否有效）"""
        try:
            union_field = self.get_union_field_name()
            if not union_field:
                return False
            container = self.field_widgets.get(union_field)
            if container is None:
                return False
            # 检查widget是否仍然有效（没有被删除）
            try:
                # 尝试访问widget的属性来检查是否有效
                if not container.isVisible() and container.parent() is None:
                    # Widget可能已被删除
                    return False
            except RuntimeError:
                # RuntimeError表示widget已被删除
                print("save_union_table_to_model_safe: container已被删除")
                return False
            
            table = container.findChild(QTableWidget)
            if table is None:
                return False
            
            # 再次检查table是否有效
            try:
                table.rowCount()
            except RuntimeError:
                print("save_union_table_to_model_safe: table已被删除")
                return False
            
            union_data = []
            for row in range(table.rowCount()):
                try:
                    combo = table.cellWidget(row, 1)
                    edit = table.cellWidget(row, 2)
                    if combo is None or edit is None:
                        continue
                    dtype_idx = combo.currentData()
                    raw = str(edit.text()).strip().replace('×', 'x').replace('Ｘ', 'x')
                    
                    # 验证输入格式（如果非空）
                    if raw:
                        is_valid, error_msg, parsed_value = self.validate_numeric_input(raw, "数据区")
                        if not is_valid:
                            # 显示错误提示
                            QMessageBox.warning(
                                self,
                                "输入格式错误",
                                f"数据区第{row+1}行输入错误：{error_msg}\n\n"
                                f"请输入有效的十进制数字（如：123）或十六进制数字（如：0x1111）"
                            )
                            # 恢复上次有效值
                            last_valid = edit.property("last_valid_value")
                            if last_valid is None:
                                last_valid = ""
                            edit.setText(str(last_valid))
                            edit.setFocus()
                            # 使用上次有效值或空值
                            raw = str(last_valid) if last_valid else ""
                    
                    value = raw
                    # 保存当前值作为下次的有效值
                    edit.setProperty("last_valid_value", raw)
                except (RuntimeError, AttributeError):
                    # Widget可能已被删除，跳过这一行
                    continue
                except Exception:
                    try:
                        dtype_idx = combo.currentData()
                        value = str(edit.text()).strip()
                    except (RuntimeError, AttributeError):
                        continue
                union_data.append({"data_type": dtype_idx, "value": value})
            
            # 只更新當前 union 字段
            self.smodel.update_type_data(self.step_type, {union_field: union_data})
            return True
        except RuntimeError as e:
            print(f"save_union_table_to_model_safe: RuntimeError - {e}")
            return False
        except Exception as e:
            print(f"save_union_table_to_model_safe: 其他错误 - {e}")
            return False
    
    def save_union_table_to_model(self):
        """將當前 union 表格內容即時保存到 StepModel"""
        self.save_union_table_to_model_safe()

    
    def get_step_data(self):
        """获取当前表单中的内容并更新到smodel中"""

        #获取基础字段到base_step_data中
        self.get_list_data(BASIC_TYPE_FIELDS, self.base_step_data)
        
        #获取当前step_type对应的字段列表
        type_field_list = step_model.get_step_type_field_list(n=self.step_type)
        #获取type_step_data
        self.get_list_data(type_field_list, self.type_step_data)
        
        #获取expand_step_data,未实现
        self.get_ext_data(self.expand_step_data)
        
        # 保留已有的periodic_file_data和periodic_file_path（如果存在）
        if hasattr(self.smodel, 'expand_step_data'):
            existing_periodic_data = self.smodel.expand_step_data.get("periodic_file_data")
            existing_periodic_path = self.smodel.expand_step_data.get("periodic_file_path")
            if existing_periodic_data is not None:
                self.expand_step_data["periodic_file_data"] = existing_periodic_data
            if existing_periodic_path is not None:
                self.expand_step_data["periodic_file_path"] = existing_periodic_path
        
        # 获取协议模板数据
        self.get_protocol_data()

        # print(f"dialog get_step_data before update: {self.smodel.get_type_step_data()}")
        # 将获取到的信息更新到smodel中，这里应该放到controller里，，但是写法会繁琐一点
        self.smodel.update_base_data(self.base_step_data)
        self.smodel.update_type_data(self.step_type, self.type_step_data)
        self.smodel.update_expand_data(self.expand_step_data)
        
        # 保存原始输入字符串到全局缓存（用于local_site、recip_site、sub_address）
        for field in ("local_site", "recip_site", "sub_address", "base_address"):
            if field in self.type_step_data:
                raw_value = self.type_step_data[field]
                if isinstance(raw_value, str):
                    self.smodel.set_raw_input_string(field, raw_value)
                    print(f"保存原始输入字符串: {field} = '{raw_value}'")
        
        # print(f"dialog get_step_data after update: {self.smodel.get_type_step_data()}")
        return self.smodel

    def get_ext_data(self, result):
        result = None

    def get_list_data(self, field_list, result):
        """
        从当前表单根据要获取的字段存入指定的字典中

        :param field_list: 要取出的字段
        :param result: 存放结果的字典
        :return: 无
        """
        #遍历字段列表从当前widget中取出值
        for field in field_list:
            if field not in self.field_widgets:
                print(f"字段 {field} 不在field_widgets中，跳过")
                continue
                
            widget = self.field_widgets[field]
            dtype = step_model.get_field_type(field)
            
            # 对于 time 和 period 字段，在保存前进行验证
            if field in ("time", "period"):
                if isinstance(widget, QLineEdit):
                    text = widget.text().strip()
                    if text:  # 如果非空，进行验证
                        field_label = step_model.get_field_label(field)
                        is_valid, error_msg, parsed_value = self.validate_float_input(text, field_label)
                        if not is_valid:
                            # 显示错误提示并阻止保存
                            QMessageBox.warning(
                                self,
                                "输入格式错误",
                                f"{field_label}输入错误：{error_msg}\n\n"
                                f"请输入有效的浮点数（如：123.45 或 1.23）"
                            )
                            widget.setFocus()
                            widget.setStyleSheet("color: red;")
                            # 恢复上次有效值
                            last_valid = widget.property("last_valid_value")
                            if last_valid is None:
                                last_valid = ""
                            widget.setText(str(last_valid))
                            # 抛出异常阻止保存
                            raise ValueError(f"{field_label}输入格式错误：{error_msg}")
            
            # 使用安全的方法获取值，传入field参数以便特殊处理
            value = self.get_widget_value_safely(widget, dtype, field=field)
            result[field] = value
            # 对于这三个字段，打印详细日志
            if field in ("local_site", "recip_site", "sub_address", "base_address"):
                print(f"get_list_data: {field} = '{value}' (type: {type(value).__name__})")

      
    
    def get_union_table_data(self, table):
        result = []
        for row in range(table.rowCount()):
            combo = table.cellWidget(row, 0)
            edit = table.cellWidget(row, 1)
            result.append({
                "data_type": combo.currentData(),
                "value": self.text2value(edit.text(), combo.currentData())
            })
        return result
    
    #self.field_widgets[field] = table

    #需要在json中给基本dtype设置默认值
    #需要有dtype的标签和值





    #可以再多增加一个字段，表示self.field_widgets[field] = widget添加的位置，可以用数组大小为8的一个widgetslist保存
    #如果step_data改变，可以存起来然后使用新的位置进行显示，后续改回去的时候就可以直接调用之前存储的数据
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
                default_str = "" if default is None else str(default)

                # 从step_data中获取当前值，若无则置为默认值
                # 对于local_site、recip_site、sub_address字段，使用get_display_value获取显示值（原始输入字符串）
                if field in ("local_site", "recip_site", "sub_address", "base_address", "time", "period"):
                    value = self.smodel.get_display_value(field, default)
                else:
                    value = self.smodel.get_value(field, default)

                placeholder_text = ""
                
                # 对于仿真时间、周期、站点号、地址相关字段，将注释放在placeholder中
                if field in ("time", "period", "local_site", "recip_site", "sub_address", "base_address"):
                    # 构建placeholder文本（包含注释信息）
                    if field == "time":
                        placeholder_text = "单位(秒)"
                    elif field == "period":
                        placeholder_text = "单位(秒)"
                    elif field == "local_site":
                        placeholder_text = "（支持十进制/十六进制输入）"
                    elif field == "recip_site":
                        placeholder_text = "（支持十进制/十六进制输入）"
                    elif field == "sub_address":
                        placeholder_text = "（支持十进制/十六进制输入）"
                    
                    # label只显示字段名（不含注释）
                    if field == "time":
                        label = "仿真时间"
                    elif field == "period":
                        label = "周期"
                    elif field == "local_site":
                        label = "自身站点号"
                    elif field == "recip_site":
                        label = "对方站点号"
                    elif field == "sub_address":
                        label = "子地址"
                    elif field == "base_address":
                        placeholder_text = "（支持十进制/十六进制输入）"
                        label = "基地址"

                if dtype == COMBO:  # 组合选项
                    if field == "protocol_type":
                        step_idx = self.step_type
                        current_val = value
                        widget = self._create_protocol_type_widget(step_idx, current_val)
                    else:
                        widget = self.get_combo_widget(field=field, value=value)
                elif dtype == "union":
                    widget = self.get_union_widgets()
                    widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
                elif field == "file_path":
                    # 文件路径使用带浏览按钮的widget
                    widget = self.get_file_path_widget(value)
                else:
                    # 文本输入类字段
                    if field in ("local_site", "recip_site", "sub_address", "base_address"):
                        # 确保显示的是字符串格式
                        if value is None:
                            display_value = ""
                        elif isinstance(value, str):
                            # 如果是字符串就直接显示（保留0x前缀）
                            display_value = value
                            print(f"显示字段 {field}: 字符串值 '{display_value}'")
                        else:
                            # 如果是数字，需要转换为字符串，但无法知道原始格式
                            # 这种情况下，如果用户之前输入的是0x11，但被转换成了17
                            # 我们无法还原。所以确保保存时就是字符串很重要
                            display_value = str(value)
                            print(f"显示字段 {field}: 数字值 {value} 转为 '{display_value}' (警告：可能丢失16进制格式)")

                        # 对于站点号/地址字段：仅在值真正为空时才显示 placeholder
                        if display_value is None:
                            display_value = ""
                        widget = QLineEdit(display_value)
                    elif field in ("time", "period"):
                        # 仿真时间 / 周期：仅在值真正为空时才依赖 placeholder
                        if value is None:
                            display_value = ""
                        else:
                            display_value = str(value)
                        widget = QLineEdit(display_value)
                    else:
                        # 其它字段保留原有行为：直接显示当前值/默认值
                        widget = QLineEdit(str(value))

                    # 对于local_site、recip_site、sub_address字段，添加输入验证
                    if field in ("local_site", "recip_site", "sub_address", "base_address"):
                        # 保存原始值用于验证失败时恢复
                        widget.setProperty("last_valid_value", display_value)
                        widget.editingFinished.connect(lambda w=widget, f=field: self.validate_site_address_input(w, f))
                    elif field in ("time", "period"):
                        # 对于仿真时间和周期字段，添加浮点数验证
                        widget.setProperty("last_valid_value", display_value)
                        widget.editingFinished.connect(lambda w=widget, dt=dtype, el=field: self.validate_float_field_input(w, dt, el))
                    else:
                        widget.editingFinished.connect(lambda w=widget, dt=dtype, el=field: self.on_edit_finished(w, dt, el))

                    # 设置占位符文本（灰色提示，在用户输入后自动消失）
                    if isinstance(widget, QLineEdit) and placeholder_text:
                        widget.setPlaceholderText(placeholder_text)

                widget_to_add = widget

                # 站点号 / 子地址：注释已经移到placeholder，不再需要额外的说明标签
                # 保留原有的容器结构，但移除说明标签
                if field in ("local_site", "recip_site", "sub_address", "base_address"):
                    # 注释已经在placeholder中，不需要额外的说明标签
                    widget_to_add = widget

                self.form_layout.addRow(QLabel(label), widget_to_add)
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


    def get_combo_widget(self, field, value=None):
        """通过字段名创建combo，若有指定的值则设置当前combo为指定的值"""
        # value = self.smodel.get_value(field, default)
            # if dtype == COMBO:#组合选项
        widget = QComboBox()
        # 获取组合选项列表
        # 这里的可以放到一个方法里
        options = step_model.get_combo_options(field)
        for opt in options:
        #获取选项的标签与值
            opt_label, opt_value = step_model.get_combo_opt_label_value(opt)
            # opt_label = step_model.get_combo_label(field, value)
            #设置选项
            widget.addItem(opt_label, opt_value)
        if value is not None:
            # 确保value的类型与combo的data类型匹配（通常是整数）
            try:
                # 如果是字符串，尝试转换为整数
                if isinstance(value, str):
                    if value.lower().startswith("0x"):
                        value_int = int(value, 16)
                    else:
                        value_int = int(value)
                else:
                    value_int = int(value)
                
                idx = widget.findData(value_int)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            except (ValueError, TypeError) as e:
                print(f"设置combo值失败: field={field}, value={value}, error={e}")

        return widget

    def _create_protocol_type_widget(self, step_type, current_value):
        """根据当前step_type创建协议类型下拉框"""
        combo = QComboBox()
        try:
            current_int = int(current_value)
        except (TypeError, ValueError):
            try:
                current_int = int(str(current_value), 16)
            except Exception:
                current_int = -1

        options = self.template_manager.get_protocol_options_for_step(step_type)
        has_value = False
        for opt in options:
            combo.addItem(opt["label"], opt["value"])
            if opt["value"] == current_int:
                has_value = True

        if not has_value and current_int is not None:
            combo.addItem(f"未识别({current_int})", current_int)
            combo.setCurrentIndex(combo.count() - 1)
        else:
            idx = combo.findData(current_int)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(self.on_protocol_type_changed)
        return combo
    
    def get_file_path_widget(self, value=None):
        """创建文件路径选择widget（包含输入框和浏览按钮）"""
        import os
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        line_edit = QLineEdit(str(value) if value else "")
        line_edit.setPlaceholderText("选择文件...")
        
        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(lambda: self.browse_file_path(line_edit))
        
        layout.addWidget(line_edit)
        layout.addWidget(browse_btn)
        widget.setLayout(layout)
        
        # 保存line_edit引用以便后续获取值
        widget.line_edit = line_edit
        
        return widget
    
    def browse_file_path(self, line_edit):
        """打开文件选择对话框"""
        import os
        from PyQt5.QtCore import QStandardPaths
        current_path = line_edit.text()
        if current_path and os.path.exists(current_path):
            default_dir = os.path.dirname(current_path)
        else:
            default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            default_dir,
            "所有文件 (*.*);;文本文件 (*.txt);;数据文件 (*.dat)"
        )
        
        if file_path:
            line_edit.setText(file_path)
            # 如果是在周期GLINK中，读取文件并解析数据
            step_type = self.smodel.get_base_step_data().get(STYPE, 0)
            if step_type in [0, 1]:  # glink_fileds_periodic
                self.load_periodic_data_from_file(file_path)
    
    def load_periodic_data_from_file(self, file_path):
        """读取周期GLINK数据文件，根据数据类型解析每行数据"""
        import os
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"文件不存在: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                QMessageBox.warning(self, "文件为空", "文件为空，无法读取数据")
                return
            
            # 获取数据区的数据类型列表
            data_region_widget = self.field_widgets.get("data_region")
            if not data_region_widget:
                QMessageBox.warning(self, "数据区未配置", "请先配置数据区的数据类型")
                return
            
            # 从union表格中获取数据类型
            table = data_region_widget.findChild(QTableWidget)
            if not table:
                QMessageBox.warning(self, "数据区未配置", "请先配置数据区的数据类型")
                return
            
            data_types = []
            for row in range(table.rowCount()):
                combo = table.cellWidget(row, 1)
                if combo:
                    dtype = combo.currentData()
                    if dtype is not None:
                        data_types.append(dtype)
            
            # 如果数据区未配置类型，尝试从第一行推断列数，并提示用户配置
            if not data_types:
                # 读取第一行来确定列数
                first_line = None
                for line in lines:
                    line = line.strip()
                    if line:
                        first_line = line
                        break
                
                if first_line:
                    col_count = len(first_line.split())
                    QMessageBox.information(
                        self,
                        "配置数据类型",
                        f"检测到文件第一行有 {col_count} 列数据。\n请先在数据区配置 {col_count} 个数据类型，然后重新选择文件。"
                    )
                else:
                    QMessageBox.warning(self, "数据类型未配置", "请先配置数据区的数据类型")
                return
            
            # 解析每行数据
            parsed_lines = []
            for line_idx, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 按空格分割
                values = line.split()
                
                # 检查数据列数是否匹配
                if len(values) != len(data_types):
                    QMessageBox.warning(
                        self, 
                        "数据格式错误", 
                        f"第 {line_idx + 1} 行数据列数 ({len(values)}) 与数据类型数量 ({len(data_types)}) 不匹配"
                    )
                    return
                
                # 解析每列数据
                parsed_row = []
                for col_idx, (value_str, dtype_idx) in enumerate(zip(values, data_types)):
                    try:
                        # 根据数据类型转换值（保留原始字符串）
                        parsed_row.append({
                            "data_type": dtype_idx,
                            "value": value_str  # 保存原始字符串
                        })
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "数据解析错误",
                            f"第 {line_idx + 1} 行第 {col_idx + 1} 列数据解析失败: {value_str}, 错误: {e}"
                        )
                        return
                
                parsed_lines.append(parsed_row)
            
            # 将解析后的第一行数据填充到数据区表格作为预览
            if parsed_lines:
                # 清空现有数据
                table.setRowCount(0)
                # 填充数据类型（使用第一行作为结构）
                first_row = parsed_lines[0]
                for item in first_row:
                    self.add_union_row(table, item["data_type"], item["value"])
                
                # 保存所有行数据到smodel的expand_step_data中（用于后续展开）
                self.smodel.expand_step_data["periodic_file_data"] = parsed_lines
                self.smodel.expand_step_data["periodic_file_path"] = file_path
                
                QMessageBox.information(
                    self,
                    "文件读取成功",
                    f"成功读取 {len(parsed_lines)} 行数据。保存时会根据周期展开为多个步骤。"
                )
            
        except Exception as e:
            QMessageBox.critical(self, "读取文件失败", f"读取文件时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_step_save(self):
        # 保存后应当发射刷新list的信号
        try:
            # 先计算当前流程步的自动字段值
            self.calculate_auto_fields()
            # 保存当前流程步数据
            self.step_save_signal.emit()
            
            # 更新所有流程步的数据
            self.update_all_steps_data()
        except Exception as e:
            print(f"保存过程中出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "保存错误", f"保存过程中出现错误: {str(e)}")
    
    def update_all_steps_data(self):
        """更新所有流程步的帧计数"""
        if not self.model or not hasattr(self.model, 'steps'):
            return
        
        print("开始更新所有流程步的帧计数...")
        
        # 首先按协议类型对流程步进行分组，并筛选出需要计算帧计数的流程步
        protocol_groups = {}
        
        for step in self.model.steps:
            step_type = step.get_step_type()
            protocol_type = step.get_base_step_data().get("protocol_type", 0)
            
            if protocol_type == -1:  # 无协议类型
                continue
                
            # 获取消息控制字，判断是否需要计算帧计数
            protocol_data = step.get_protocol_data() or {}
            ctrl_word_str = protocol_data.get("消息控制字", "0")
            ctrl_word = self.safe_hex_to_int(ctrl_word_str)
            
            # 只有帧计数位为1时才参与帧计数
            if (ctrl_word & 0x01) == 0x01:
                key = (step_type, protocol_type)
                if key not in protocol_groups:
                    protocol_groups[key] = []
                protocol_groups[key].append(step)
        
        # 对每个协议组按时间从大到小排序并计算帧计数
        for (step_type, protocol_type), steps in protocol_groups.items():
            # 按时间从大到小排序
            steps.sort(key=lambda x: x.get_value("time", 0), reverse=True)
            
            # 计算帧计数
            for idx, step in enumerate(steps):
                frame_count = (idx + 1) & 0xFFFF
                protocol_data = step.get_protocol_data() or {}
                protocol_data["帧计数"] = f"0x{frame_count:04X}"
                step.set_protocol_data(protocol_data)
                print(f"更新协议组({step_type}, {protocol_type})流程步: {step.get_name()}, 时间: {step.get_value('time', 0)}, 帧计数: {frame_count}")
        
        # 刷新当前流程步的显示，保持字体一致
        self.refresh_fields(self.smodel)
        
        print("所有流程步帧计数更新完成")
        
        # 保持当前视图字体一致性，仅刷新当前流程步的显示
        self.refresh_fields(self.smodel)
    
    def safe_hex_to_int(self, hex_str):
        """安全地将十六进制字符串转换为整数"""
        try:
            if isinstance(hex_str, str):
                if hex_str.lower().startswith("0x"):
                    return int(hex_str, 16)
                return int(hex_str)
            elif isinstance(hex_str, int):
                return hex_str
            return 0
        except (ValueError, TypeError):
            return 0

    def on_step_cancel(self):
        self.refresh_fields(init=True)
    
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
        
        # 获取当前流程步类型
        step_type = self.smodel.get_step_type()
        
        # 当流程步类型为中断类型（周期中断和非周期中断）时，移除字节序字段
        if step_type == 7 or step_type == 8:  # 7: 非周期中断, 8: 周期中断
            basic_list = [field for field in basic_list if field != "endian"]
        
        self.get_field_wigets(basic_list)
        # 当前行
        self.upper_row_count = self.form_layout.rowCount()
        # 进行下半部分对应流程步类型字段的刷新
        self.refresh_lower_fields(init)

    def on_step_type_changed(self):
        # 在切换step_type之前，先保存当前的data_region数据（如果存在）
        self.save_data_region_before_type_change()
        self.refresh_lower_fields()
    
    def save_data_region_before_type_change(self):
        """在切换step_type之前保存data_region的数据"""
        # 检查当前step_type是否有data_region字段
        current_fields = step_model.get_step_type_field_list(n=self.step_type)
        if "data_region" in current_fields:
            # 保存当前data_region的数据到model（使用安全版本）
            if self.save_union_table_to_model_safe():
                print(f"保存data_region数据（切换step_type前）")
            else:
                print(f"保存data_region数据失败（widget可能已删除）")
    
    def refresh_lower_fields(self, init=False):
        # 检查form_layout是否有效
        if not self.is_form_layout_valid():
            print("refresh_lower_fields: form_layout无效，重新创建")
            self.recreate_form_layout()
            return
        
        # 0. 在移除widget之前，先获取当前step_type并保存data_region数据（如果有）
        step_type = self.smodel.get_base_step_data().get(STYPE, 0)
        
        # 非初始化时从widget获取
        if not init:
            step_type_widget = self.field_widgets.get(STYPE)
            if isinstance(step_type_widget, QComboBox):
                step_type = step_type_widget.currentData()
        else:
            step_type = self.smodel.get_step_type()
        
        # 在移除widget之前保存data_region数据
        preserved_data_region = None
        if not init:
            old_fields = step_model.get_step_type_field_list(n=self.step_type)
            new_fields = step_model.get_step_type_field_list(n=step_type) if self.step_type != step_type else old_fields
            
            # 如果当前step_type有data_region，先保存数据
            if "data_region" in old_fields:
                # 在移除widget之前保存
                if self.save_union_table_to_model_safe():
                    print(f"保存data_region数据（refresh_lower_fields前，old step_type={self.step_type}）")
                    # 从smodel中获取保存的数据
                    preserved_data_region = self.smodel.get_value("data_region", None)
            
        # 1. 移除下半部分所有行（这会删除widget）
        try:
            while self.form_layout.rowCount() > self.upper_row_count:
                self.form_layout.removeRow(self.upper_row_count)
        except RuntimeError:
            print("移除下半部分行时出错，重新创建form_layout")
            self.recreate_form_layout()
            return
        
        # 2. 处理step_type切换
        if self.step_type != step_type:
            old_fields = step_model.get_step_type_field_list(n=self.step_type)
            new_fields = step_model.get_step_type_field_list(n=step_type)
            
            # 清除旧的type_step_data，但保留data_region（如果新旧step_type都支持）
            if "data_region" in old_fields and "data_region" in new_fields:
                # 如果新旧都支持data_region，保留之前保存的数据
                if preserved_data_region is None:
                    preserved_data_region = self.smodel.get_value("data_region", None)
                print(f"保留data_region数据用于新step_type")
            
            # 清除旧的type_step_data
            self.type_step_data.clear()
            
            # 如果新旧都支持data_region，恢复保存的值
            if preserved_data_region is not None and "data_region" in new_fields:
                self.type_step_data["data_region"] = preserved_data_region
                # 同时更新到smodel中，确保一致性
                self.smodel.update_type_data(step_type, {"data_region": preserved_data_region})
            
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
        
    def add_field_dialog(self):
        
        add_ft = self.STRINGS["costom_dialog"]["add_field_title"]
        ft_name = self.STRINGS["costom_dialog"]["add_field_label"]
        value_label = self.STRINGS["costom_dialog"]["add_field_value_label"]
        key, ok = QInputDialog.getText(self, add_ft, ft_name)
        if ok and key and key not in self.step_data and key not in [f[0] for f in GLINK_REQUIRED_FIELDS]:
            value, ok2 = QInputDialog.getText(self, add_ft, f"{key} "+value_label)
            if ok2:
                self.step_data[key] = value
                self.refresh_fields()

    def remove_field(self, key):
        if key in self.step_data:
            del self.step_data[key]
            self.refresh_fields()

    def reomove_protocol_template_area(self):
        """清除协议模板区域的所有控件"""
        # 确保协议表单布局存在
        if "protocol_template" in self.field_widgets:
            widget = self.field_widgets["protocol_template"]
            try:
                # 找到它在表单中的位置
                for i in range(self.form_layout.rowCount()):
                    layout_item = self.form_layout.itemAt(i, QFormLayout.FieldRole)
                    if layout_item and layout_item.widget() == widget:
                        self.form_layout.removeRow(i)
                        break
            except RuntimeError:
                # 如果form_layout已经被删除，忽略错误
                print("form_layout已被删除，跳过移除操作")
            
            # 从field_widgets中移除
            del self.field_widgets["protocol_template"]

    def on_protocol_type_changed(self, init=False):
        """协议类型改变时刷新协议模板字段"""
        # 这里可以添加协议类型的改变信号
        # print("protocol type changed")
        # 首先从current_value中获取协议类型
        # 然后获取协议模板字段
        # 再刷新协议表单

        #获取流程步类型与协议类型
        # 优先从widget获取（当前显示的值），如果widget不存在或未设置，从smodel获取
        step_type = self.smodel.get_base_step_data().get(STYPE, 0)
        protocol_type = self.smodel.get_value("protocol_type", -1)  # 默认-1（无）

        step_type_widget = self.field_widgets.get(STYPE)
        # print(f"step_type_widget {step_type_widget}")
        if isinstance(step_type_widget, QComboBox):
            step_type = step_type_widget.currentData()

        protocol_type_widget = self.field_widgets.get("protocol_type")
        # print(f"protcol type widget {protocol_type_widget}")
        if isinstance(protocol_type_widget, QComboBox):
            # 优先从widget获取当前选择的值
            protocol_type = protocol_type_widget.currentData()
            # 如果currentData返回None，从smodel获取并设置到下拉框
            if protocol_type is None:
                saved_protocol_type = self.smodel.get_value("protocol_type", -1)
                # 确保值是整数类型（combo的data是整数）
                try:
                    if isinstance(saved_protocol_type, str):
                        # 如果是字符串，尝试转换
                        if saved_protocol_type.lower().startswith("0x"):
                            saved_protocol_type = int(saved_protocol_type, 16)
                        else:
                            saved_protocol_type = int(saved_protocol_type)
                    elif saved_protocol_type is None:
                        saved_protocol_type = -1
                    else:
                        saved_protocol_type = int(saved_protocol_type)
                except (ValueError, TypeError):
                    saved_protocol_type = -1
                
                # 设置下拉框的值
                idx = protocol_type_widget.findData(saved_protocol_type)
                if idx >= 0:
                    protocol_type_widget.setCurrentIndex(idx)
                protocol_type = saved_protocol_type
        # print(f"step detail view protocol_type {protocol_type}")

        # 如果用下面这段会出现扩展帧出不来，暂时不知道是为什么
        # if not init:
        #     # 从widget表单处获取
        #     step_type_widget = self.field_widgets.get(STYPE)
        #     # print(f"step_type_widget {step_type_widget}")
        #     if isinstance(step_type_widget, QComboBox):
        #         step_type = step_type_widget.currentData()

        #     protocol_type_widget = self.field_widgets.get("protocol_type")
        #     # print(f"protcol type widget {protocol_type_widget}")
        #     if isinstance(protocol_type_widget, QComboBox):
        #         protocol_type = protocol_type_widget.currentData()
        #         # print(f"step detail view protocol_type {protocol_type}")
        # 如果协议类型为-1（无），则不显示协议模板
        if protocol_type == -1:
            protocol_template = None
            print(f"step detail view step_type:{step_type} protocol_type {protocol_type}  template :无")
        else:
            protocol_template = self.template_manager.get_template_by_step_and_protocol(step_type, protocol_type)
            ptname = protocol_template.get("name", "None") if protocol_template else "None"
            print(f"step detail view step_type:{step_type} protocol_type {protocol_type}  template :{ptname}")
        # 获取协议模板字段后通过内置函数刷新
        self.refresh_protocol_template(protocol_template)
        # for f in self.field_widgets:
        #     print(f"after {f}")


    def get_protocol_data(self):
        """从协议模板表格中获取数据"""
        # 检查协议类型，如果为-1（无），直接返回空字典并清空protocol_data
        protocol_type = self.smodel.get_value("protocol_type", -1)
        if protocol_type == -1:
            self.smodel.set_protocol_data({})
            print("协议类型为'无'，get_protocol_data返回空字典")
            return {}
        
        # 安全地检查protocol_table是否存在且有效
        if not hasattr(self, 'protocol_table'):
            self.smodel.set_protocol_data({})
            return {}
        
        # 尝试访问protocol_table来检查它是否仍然有效
        try:
            # 如果protocol_table已被删除，访问它的属性会抛出RuntimeError
            _ = self.protocol_table.rowCount()
        except (RuntimeError, AttributeError):
            # protocol_table已被删除或无效，清空protocol_data
            self.smodel.set_protocol_data({})
            print("protocol_table已被删除，get_protocol_data返回空字典")
            return {}
        
        if self.protocol_table is None:
            self.smodel.set_protocol_data({})
            return {}
            
        protocol_data = {}
        try:
            for row in range(self.protocol_table.rowCount()):
                element_item = self.protocol_table.item(row, 1)
                if element_item:
                    element = element_item.text()
                    widget = self.protocol_table.cellWidget(row, 3)
                    
                    if isinstance(widget, QLineEdit):
                        protocol_data[element] = widget.text()
                    elif isinstance(widget, QLabel):
                        protocol_data[element] = widget.text()
                    elif isinstance(widget, QComboBox):
                        # 对于下拉框，保存当前显示的文本
                        protocol_data[element] = widget.currentText()
                    # 处理子表格（ARRAY类型）
                    elif hasattr(widget, 'table') and isinstance(widget.table, QTableWidget):
                        # 从子表格中获取数据
                        array_data = []
                        for sub_row in range(widget.table.rowCount()):
                            edit = widget.table.cellWidget(sub_row, 1)
                            if edit and isinstance(edit, QLineEdit):
                                array_data.append(edit.text())
                        protocol_data[element] = " ".join(array_data) if array_data else ""
        except (RuntimeError, AttributeError) as e:
            # 在遍历过程中如果protocol_table被删除，捕获异常并返回空字典
            print(f"访问protocol_table时出错: {e}，get_protocol_data返回空字典")
            self.smodel.set_protocol_data({})
            return {}
        
        self.smodel.set_protocol_data(protocol_data)
        return protocol_data

    def calc_glink_fields(self, data):
        """计算GLINK模板的自动字段"""
        # 计算数据区长度（字节数）- 优先从union数据计算
        data_len = 0
        
        # 尝试从union数据计算精确字节数
        try:
            if hasattr(self.smodel, 'get_union_data'):
                union_data = self.smodel.get_union_data()
                if union_data:
                    from models.step_model import SUPPORTED_DTYPES
                    for item in union_data:
                        if not isinstance(item, dict):
                            continue
                        dtype_idx = item.get('data_type')
                        if isinstance(dtype_idx, int) and 0 <= dtype_idx < len(SUPPORTED_DTYPES):
                            dtype_str = SUPPORTED_DTYPES[dtype_idx].upper()
                        else:
                            dtype_str = str(dtype_idx).upper()
                        
                        # 根据数据类型计算字节数
                        if dtype_str in ("UINT8", "INT8", "BOOL", "BOOLEAN"):
                            data_len += 1
                        elif dtype_str in ("UINT16", "INT16"):
                            data_len += 2
                        elif dtype_str in ("UINT32", "INT32", "FLOAT32", "REAL32", "FLOAT", "REAL"):
                            data_len += 4
                        elif dtype_str in ("FLOAT64", "REAL64", "DOUBLE"):
                            data_len += 8
                        elif dtype_str in ("STR", "STRING"):
                            val = item.get('value', "")
                            data_len += len(str(val).encode('utf-8'))
                        else:
                            data_len += 2  # 默认16位
                    print(f"DEBUG: 从union数据计算字节数: {data_len}")
        except Exception as e:
            print(f"DEBUG: 从union数据计算失败: {e}")
            data_len = 0
        
        # 如果union数据计算失败，回退到数据区文本计算
        if data_len == 0:
            data_value = data.get("数据区", "")
            print(f"DEBUG: 回退到数据区文本计算: '{data_value}'")
            if data_value:
                tokens = [t for t in str(data_value).split() if t]
                for tok in tokens:
                    s = str(tok).strip()
                    if s.lower().startswith("0x"):
                        s = s[2:]
                    s = ''.join(ch for ch in s if ch.isalnum())
                    if not s:
                        continue
                    data_len += (len(s) + 1) // 2
                print(f"DEBUG: 从数据区文本计算字节数: {data_len}")
        
        print(f"DEBUG: 最终字节数: {data_len}")
        
        # 获取通信控制字 - 使用安全转换
        ctrl_word_str = data.get("消息控制字", "0")
        ctrl_word = self.safe_hex_to_int(ctrl_word_str)
        
        # 计算帧计数（仅当 ctrl_word 位0=1 时，即0x0001或0x0003）
        # 需要基于所有符合条件的流程步按时间排序后计算
        frame_count = 0
        if (ctrl_word & 0x01) == 0x01:
            # 获取所有符合条件的流程步（消息控制字为0x0001或0x0003）
            if self.model and hasattr(self.model, 'steps'):
                # 获取当前流程步的类型和协议类型
                current_step_type = self.smodel.get_step_type()
                current_protocol_type = self.smodel.get_base_step_data().get("protocol_type", 0)
                current_time = self.smodel.get_value("time", 0)
                
                # 筛选出所有同协议且消息控制字帧计数位为1的流程步
                eligible_steps = []
                for step in self.model.steps:
                    step_type = step.get_step_type()
                    protocol_type = step.get_base_step_data().get("protocol_type", 0)
                    
                    # 只处理同协议的流程步
                    if step_type == current_step_type and protocol_type == current_protocol_type:
                        step_protocol_data = step.get_protocol_data()
                        if step_protocol_data:
                            step_ctrl_word_str = step_protocol_data.get("消息控制字", "0")
                            step_ctrl_word = self.safe_hex_to_int(step_ctrl_word_str)
                            if (step_ctrl_word & 0x01) == 0x01:  # 位0=1，即0x0001或0x0003
                                step_time = step.get_value("time", 0)
                                eligible_steps.append((step_time, step))
                
                # 按时间从大到小排序
                eligible_steps.sort(key=lambda x: x[0], reverse=True)
                
                # 找到当前流程步在排序后的位置，帧计数为该位置+1
                current_found = False
                for idx, (step_time, step) in enumerate(eligible_steps):
                    # 通过比较step对象来判断是否是当前流程步
                    if step is self.smodel:
                        frame_count = (idx + 1) & 0xFFFF
                        print(f"帧计数计算: 当前流程步在排序后的位置为 {idx}，帧计数 = {frame_count}")
                        current_found = True
                        break
                
                if not current_found:
                    # 如果当前流程步不在列表中（可能还未保存），将其加入并重新排序
                    eligible_steps.append((current_time, self.smodel))
                    eligible_steps.sort(key=lambda x: x[0], reverse=True)
                    for idx, (step_time, step) in enumerate(eligible_steps):
                        if step is self.smodel:
                            frame_count = (idx + 1) & 0xFFFF
                            print(f"帧计数计算: 当前流程步（未保存）在排序后的位置为 {idx}，帧计数 = {frame_count}")
                            break
            else:
                # 如果没有model引用，回退到原有逻辑
                frame_count_str = data.get("帧计数", "0")
                frame_count = self.safe_hex_to_int(frame_count_str)
                print(f"帧计数计算: 无model引用，使用当前值，帧计数 = {frame_count}")
        
        # 计算CRC（仅当 ctrl_word 位1=1 时，即0x0002或0x0003）- 使用CRC-16/CCITT算法
        crc = None
        if (ctrl_word & 0x02) == 0x02:
            # CRC-16/CCITT查表法
            # CRC-16/CCITT查表法（CRC余式表，256个元素）
            crc_ta = [
                0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
                0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
                0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
                0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
                0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
                0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
                0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
                0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
                0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
                0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
                0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
                0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
                0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
                0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
                0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
                0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
                0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
                0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
                0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
                0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
                0x7367, 0x6346, 0x5325, 0x4304, 0x33e3, 0x23c2, 0x13a1, 0x0380,
                0xf26f, 0xe24e, 0xd22d, 0xc20c, 0xb2eb, 0xa2ca, 0x92a9, 0x8288,
                0x7156, 0x6177, 0x5114, 0x4135, 0x31d2, 0x21f3, 0x1190, 0x01b1,
                0xf05e, 0xe07f, 0xd01c, 0xc03d, 0xb0da, 0xa0fb, 0x9098, 0x80b9,
                0x47c5, 0x57e4, 0x6787, 0x77a6, 0x0741, 0x1760, 0x2703, 0x3722,
                0xc6cd, 0xd6ec, 0xe68f, 0xf6ae, 0x8649, 0x9668, 0xa60b, 0xb62a,
                0x45f4, 0x55d5, 0x65b6, 0x7597, 0x0570, 0x1551, 0x2532, 0x3513,
                0xc4fc, 0xd4dd, 0xe4be, 0xf49f, 0x8478, 0x9459, 0xa43a, 0xb41b,
                0x4b63, 0x5b42, 0x6b21, 0x7b00, 0x0be7, 0x1bc6, 0x2ba5, 0x3b84,
                0xca6b, 0xda4a, 0xea29, 0xfa08, 0x8aef, 0x9ace, 0xaaad, 0xba8c,
                0x4952, 0x5973, 0x6910, 0x7931, 0x09d6, 0x19f7, 0x2994, 0x39b5,
                0xc85a, 0xd87b, 0xe818, 0xf839, 0x88de, 0x98ff, 0xa89c, 0xb8bd,
                0x4f21, 0x5f00, 0x6f63, 0x7f42, 0x0fa5, 0x1f84, 0x2fe7, 0x3fc6,
                0xce29, 0xde08, 0xee6b, 0xfe4a, 0x8ead, 0x9e8c, 0xaeef, 0xbece,
                0x4d10, 0x5d31, 0x6d52, 0x7d73, 0x0d94, 0x1db5, 0x2dd6, 0x3df7,
                0xcc18, 0xdc39, 0xec5a, 0xfc7b, 0x8c9c, 0x9cbd, 0xacde, 0xbcff,
            ]
            
            def update_crc_with_value(crc_val, value, byte_count):
                """将值按字节加入CRC计算"""
                for i in range(byte_count):
                    byte_val = (value >> (8 * (byte_count - 1 - i))) & 0xFF
                    idx = ((crc_val >> 8) ^ byte_val) & 0xFF
                    if 0 <= idx < len(crc_ta):
                        crc_val = ((crc_val << 8) ^ crc_ta[idx]) & 0xFFFF
                return crc_val
            
            crc = 0xFFFF
            
            # 按顺序计算所有字段的CRC（注意：数据区crc校验和字段本身不参与计算，它只是用来存储计算结果）
            # 1. 仿真时间 (time) - UINT32, 4字节
            try:
                step_time = None
                time_widget = self.field_widgets.get("time")
                if isinstance(time_widget, QLineEdit):
                    time_text = time_widget.text().strip()
                    if time_text:
                        try:
                            step_time = float(time_text)
                        except ValueError:
                            step_time = time_text
                if step_time is None:
                    step_time = self.smodel.get_value("time", 0)
                if isinstance(step_time, (int, float)):
                    time_val = int(step_time) & 0xFFFFFFFF
                    crc = update_crc_with_value(crc, time_val, 4)
                    print(f"CRC计算: 仿真时间 = {time_val} (0x{time_val:08X})")
            except Exception as e:
                print(f"CRC计算: 获取仿真时间失败: {e}")
            
            # 2. 自身站点号 (local_site) - 通常为UINT8或UINT16
            try:
                local_site = self.smodel.get_value("local_site", 0)
                local_site_val = self.safe_hex_to_int(str(local_site)) & 0xFFFF
                crc = update_crc_with_value(crc, local_site_val, 2)
                print(f"CRC计算: 自身站点号 = {local_site_val} (0x{local_site_val:04X})")
            except Exception as e:
                print(f"CRC计算: 获取自身站点号失败: {e}")
            
            # 3. 对方站点号 (recip_site) - 通常为UINT8或UINT16
            try:
                recip_site = self.smodel.get_value("recip_site", 0)
                recip_site_val = self.safe_hex_to_int(str(recip_site)) & 0xFFFF
                crc = update_crc_with_value(crc, recip_site_val, 2)
                print(f"CRC计算: 对方站点号 = {recip_site_val} (0x{recip_site_val:04X})")
            except Exception as e:
                print(f"CRC计算: 获取对方站点号失败: {e}")
            
            # 4. 子地址 (sub_address) - 通常为UINT8或UINT16
            try:
                sub_address = self.smodel.get_value("sub_address", 0)
                sub_address_val = self.safe_hex_to_int(str(sub_address)) & 0xFFFF
                crc = update_crc_with_value(crc, sub_address_val, 2)
                print(f"CRC计算: 子地址 = {sub_address_val} (0x{sub_address_val:04X})")
            except Exception as e:
                print(f"CRC计算: 获取子地址失败: {e}")
            
            # 5. GLINK典型模板里的"时间" - UINT32, 4字节
            try:
                protocol_time_str = data.get("时间", "0")
                protocol_time_val = self.safe_hex_to_int(protocol_time_str) & 0xFFFFFFFF
                crc = update_crc_with_value(crc, protocol_time_val, 4)
                print(f"CRC计算: 协议时间 = {protocol_time_val} (0x{protocol_time_val:08X})")
            except Exception as e:
                print(f"CRC计算: 获取协议时间失败: {e}")
            
            # 6. 消息控制字 - UINT16, 2字节
            crc = update_crc_with_value(crc, ctrl_word, 2)
            print(f"CRC计算: 消息控制字 = {ctrl_word} (0x{ctrl_word:04X})")
            
            # 7. 消息ID - UINT16, 2字节
            try:
                msg_id_str = data.get("消息ID", "0")
                msg_id_val = self.safe_hex_to_int(msg_id_str) & 0xFFFF
                crc = update_crc_with_value(crc, msg_id_val, 2)
                print(f"CRC计算: 消息ID = {msg_id_val} (0x{msg_id_val:04X})")
            except Exception as e:
                print(f"CRC计算: 获取消息ID失败: {e}")
            
            # 8. 帧计数 - UINT16, 2字节（使用计算后的值）
            crc = update_crc_with_value(crc, frame_count, 2)
            print(f"CRC计算: 帧计数 = {frame_count} (0x{frame_count:04X})")
            
            # 9. 数据区 - 按原有逻辑处理
            data_value = data.get("数据区", "")
            if data_value:
                # 处理数据区：可能是空格分隔的16进制字符串，如 "0x0001 0x0002"
                for word in data_value.split():
                    try:
                        w = self.safe_hex_to_int(word)
                        # 按字节计算CRC（CRC-16/CCITT查表法）
                        # 高字节（高8位）
                        idx = ((crc >> 8) ^ (w >> 8)) & 0xFF
                        if 0 <= idx < len(crc_ta):
                            crc = ((crc << 8) ^ crc_ta[idx]) & 0xFFFF
                        # 低字节（低8位）
                        idx = ((crc >> 8) ^ (w & 0xFF)) & 0xFF
                        if 0 <= idx < len(crc_ta):
                            crc = ((crc << 8) ^ crc_ta[idx]) & 0xFFFF
                    except (ValueError, IndexError) as e:
                        print(f"CRC计算错误: {e}, word={word}, w={w if 'w' in locals() else 'N/A'}")
                        pass
                print(f"CRC计算: 数据区已处理")
            
            print(f"CRC计算完成: 最终CRC = 0x{crc:04X}")
        else:
            # 位1=0（0x0000或0x0001），CRC固定为0
            crc = 0
        
        # 时间使用用户输入的仿真时间（秒）×1000转换为毫秒
        try:
            step_time = self.smodel.get_value("time", 0)
            # 将秒转换为毫秒（×1000）
            time_ms = int(float(step_time) * 1000) & 0xFFFFFFFF
            self.update_protocol_field("时间", str(time_ms))
        except Exception:
            pass
        
        # 更新表格（消息长度字段已删除，不再更新）
        if (ctrl_word & 0x01) == 0x01:
            self.update_protocol_field("帧计数", str(frame_count))
        # 如果通信控制字要求计算CRC（位1），将计算结果更新到"数据区crc校验和"字段
        # 注意：该字段本身不参与CRC计算，只用于存储计算结果
        if crc is not None:
            data["数据区crc校验和"] = f"0x{crc:04X}"
            self.update_protocol_field("数据区crc校验和", f"0x{crc:04X}")

    def _apply_protocol_overrides(self, protocol_data, overrides):
        if not overrides:
            return
        for field_name, value in overrides.items():
            string_value = str(value)
            protocol_data[field_name] = string_value
            self.update_protocol_field(field_name, string_value)

    def calc_serial_std_fields(self, protocol_data):
        data_value = protocol_data.get("数据区") or self.get_data_region_from_step()
        metrics = calc_serial_standard_metrics(data_value)
        self._apply_protocol_overrides(protocol_data, metrics.get("overrides"))

    def calc_serial_ext_fields(self, protocol_data):
        data_value = protocol_data.get("数据区") or self.get_data_region_from_step()
        metrics = calc_serial_extended_metrics(data_value)
        self._apply_protocol_overrides(protocol_data, metrics.get("overrides"))

    def calc_crc_tail_fields(self, protocol_data):
        data_value = protocol_data.get("数据区") or self.get_data_region_from_step()
        metrics = calc_crc_tail_metrics(data_value)
        self._apply_protocol_overrides(protocol_data, metrics.get("overrides"))

    def update_protocol_time_from_step(self, protocol_data=None):
        """将当前仿真时间(秒)×1000写入协议“时间”字段"""
        try:
            step_time = self.smodel.get_value("time", 0)
            time_ms = int(float(step_time) * 1000) & 0xFFFFFFFF
            if protocol_data is not None:
                protocol_data["时间"] = str(time_ms)
            self.update_protocol_field("时间", str(time_ms))
            print(f"同步协议时间字段: {step_time}秒 -> {time_ms}毫秒")
            return time_ms
        except Exception as e:
            print(f"同步协议时间字段失败: {e}")
            return None

    def update_protocol_field(self, field_name, value):
        """更新协议模板中的字段值"""
        if not hasattr(self, 'protocol_table'):
            return
            
        for row in range(self.protocol_table.rowCount()):
            element_item = self.protocol_table.item(row, 1)
            if element_item and element_item.text() == field_name:
                widget = self.protocol_table.cellWidget(row, 3)
                
                if isinstance(widget, QLineEdit) and not widget.isReadOnly():
                    widget.setText(value)
                    # 确保字体不加粗，与其他字段保持一致
                    font = widget.font()
                    font.setBold(False)
                    widget.setFont(font)
                    # "时间"字段左对齐
                    if field_name == "时间":
                        widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif isinstance(widget, QLabel):
                    widget.setText(value)
                    # 确保字体不加粗，与其他字段保持一致
                    font = widget.font()
                    font.setBold(False)
                    widget.setFont(font)
                    # "时间"、"帧计数"和"数据区crc校验和"左对齐，与其他字段保持一致
                    if field_name in ["时间", "帧计数", "数据区crc校验和"]:
                        widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        widget.setAlignment(Qt.AlignCenter)
                print(f"更新字段 {field_name} = {value}")  # 添加调试信息
                return
        
        print(f"未找到字段: {field_name}")  # 添加调试信息
            

    def add_protocol_template_area(self):
        """添加协议模板区域到表单"""
        # 获取当前流程步类型和协议类型
        step_type = self.smodel.get_step_type()
        protocol_type = self.smodel.get_base_step_data().get("protocol_type", 0)
        
        # 检查是否需要协议模板（协议类型必须>=0，-1表示无）
        if step_type == step_model.STEP_TYPE_PROTOCOL and protocol_type >= 0:
            # 获取协议模板
            protocol_template = self.template_manager.get_template_by_step_and_protocol(step_type, protocol_type)
            
            if protocol_template:
                # 创建协议模板区域
                template_group = QGroupBox("协议模板")
                template_layout = QVBoxLayout()
                
                # 添加模板名称标签
                template_name_label = QLabel(f"模板: {protocol_template['name']}")
                template_layout.addWidget(template_name_label)
                
                # 添加协议模板表格
                #
                # widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
                # table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
                self.protocol_table = self.create_protocol_table(protocol_template)
                template_layout.addWidget(self.protocol_table)
                
                # 更新功能已整合到保存按钮中，移除单独的更新按钮
                
                template_group.setLayout(template_layout)
                
                # 添加到表单
                self.form_layout.addRow(template_group)
                self.field_widgets["protocol_template"] = template_group

    # def create_protocol_table(self, template):
    #     """创建协议模板表格"""
    #     table = QTableWidget()
    #     table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    #     table.verticalHeader().setVisible(False)
        
    #     # 设置表格列
    #     # headers = ["序号", "要素", "数据类型", "取值范围", "备注", "值"]
    #     headers = ["序号", "要素", "数据类型", "值"]
    #     table.setColumnCount(len(headers))
    #     table.setHorizontalHeaderLabels(headers)
        
    #     # 从模型获取已保存的数据
    #     saved_data = self.smodel.get_protocol_data()
        
    #     # 填充表格
    #     for idx, field in enumerate(template.get("fields", [])):
    #         table.insertRow(idx)
            
    #         # 序号
    #         table.setItem(idx, 0, QTableWidgetItem(str(field.get("seq", idx+1))))
            
    #         # 要素
    #         table.setItem(idx, 1, QTableWidgetItem(field.get("element", "")))
            
    #         # 数据类型
    #         table.setItem(idx, 2, QTableWidgetItem(field.get("dtype", "")))
            
    #         # 取值范围
    #         # table.setItem(idx, 3, QTableWidgetItem(field.get("range", "")))
            
    #         # 备注
    #         # remark = field.get("remark", "")
    #         # remark_item = QTableWidgetItem(remark)
    #         # remark_item.setToolTip(remark)
    #         # table.setItem(idx, 4, remark_item)
            
    #         # 值
    #         # 尝试从保存的数据中获取值，否则使用模板默认值
    #         value = saved_data.get(field.get("element"), field.get("value", ""))
    #         editable = field.get("editable", True)
            
    #         if editable:
    #             edit = QLineEdit(str(value))
    #             if field.get("auto_calc", False):
    #                 edit.setReadOnly(True)
    #                 edit.setStyleSheet("background-color: #f0f0f0;")
    #             table.setCellWidget(idx, 3, edit)
    #         else:
    #             label = QLabel(str(value))
    #             label.setAlignment(Qt.AlignCenter)
    #             table.setCellWidget(idx, 3, label)
        
    #     return table

    # 每个edit框都可以连这个
    # edit.editingFinished.connect(on_edit_finished)
    def validate_array_input(self, widget, element, dtype):
        """验证ARRAY类型输入（空格分隔的多个值）"""
        if not isinstance(widget, QLineEdit):
            return
        
        text = widget.text().strip()
        
        # 如果为空，允许
        if not text:
            widget.setProperty("last_valid_value", "")
            return
        
        # 分割输入（支持空格、逗号分隔）
        values = text.replace(',', ' ').split()
        invalid_values = []
        
        for i, val in enumerate(values):
            is_valid, error_msg, parsed_value = self.validate_numeric_input(val, f"{element}[{i}]")
            if not is_valid:
                invalid_values.append(f"第{i+1}个值 '{val}': {error_msg}")
        
        if invalid_values:
            # 显示错误提示
            QMessageBox.warning(
                self,
                "输入格式错误",
                f"{element}输入错误：\n" + "\n".join(invalid_values) + "\n\n"
                f"请输入有效的十进制数字（如：123）或十六进制数字（如：0x1111），多个值用空格或逗号分隔"
            )
            # 恢复上次有效值
            last_valid = widget.property("last_valid_value")
            if last_valid is None:
                last_valid = ""
            widget.setText(str(last_valid))
            widget.setFocus()
            return
        
        # 输入有效，更新保存的值
        widget.setProperty("last_valid_value", text)
        print(f"validate_array_input: {element} 输入有效: '{text}'")
    
    def validate_site_address_input(self, widget, field):
        """验证站点号或地址的输入"""
        if not isinstance(widget, QLineEdit):
            return
        
        text = widget.text().strip()
        field_label = step_model.get_field_label(field)
        
        # 如果为空，允许（使用默认值）
        if not text:
            widget.setProperty("last_valid_value", "")
            return
        
        # 验证输入格式
        is_valid, error_msg, parsed_value = self.validate_numeric_input(text, field)
        
        if not is_valid:
            # 显示错误提示
            QMessageBox.warning(
                self,
                "输入格式错误",
                f"{field_label}输入错误：{error_msg}\n\n"
                f"请输入有效的十进制数字（如：123）或十六进制数字（如：0x1111）"
            )
            # 恢复上次有效值
            last_valid = widget.property("last_valid_value")
            if last_valid is None:
                last_valid = ""
            widget.setText(str(last_valid))
            widget.setFocus()
            return
        
        # 输入有效，更新保存的值
        widget.setProperty("last_valid_value", text)
        # 保存原始输入字符串到model
        self.smodel.set_raw_input_string(field, text)
        print(f"validate_site_address_input: {field} 输入有效: '{text}'")
    
    def on_edit_finished(self, widget, dtype, element=None):
        """
        widget: QLineEdit或QLabel，表示当前编辑的单元格
        dtype: 数据类型，支持UINT8, UINT16, UINT32, INT8, INT16, INT32等，或输入int根据step_model中的supported dtypes进行转换
        """
        # widget = table.cellWidget(idx, 3)
        if isinstance(widget, QLineEdit):
            text = widget.text().strip()
            
            # 如果为空，允许（使用默认值）
            if not text:
                widget.setStyleSheet("")
                return
            
            # 对于数值类型，先验证输入格式
            if dtype in ("UINT8", "UINT16", "UINT32", "INT8", "INT16", "INT32", "uint", "uint8", "uint16", "uint32"):
                is_valid, error_msg, parsed_value = self.validate_numeric_input(text, element or "数值")
                if not is_valid:
                    # 显示错误提示
                    field_name = element if element else "该字段"
                    QMessageBox.warning(
                        self,
                        "输入格式错误",
                        f"{field_name}输入错误：{error_msg}\n\n"
                        f"请输入有效的十进制数字（如：123）或十六进制数字（如：0x1111）"
                    )
                    # 恢复上次有效值
                    last_valid = widget.property("last_valid_value")
                    if last_valid is None:
                        last_valid = ""
                    widget.setText(str(last_valid))
                    widget.setFocus()
                    widget.setStyleSheet("color: red;")
                    return
            
            # 验证通过，尝试转换
            try:
                result = step_model.convert_value_by_dtype(text, dtype)
                        
                # 如果是错误信息，显示为红色
                if isinstance(result, str) and result.startswith("错误"):
                    widget.setStyleSheet("color: red;")
                    widget.setText(result)
                else:
                    # 转换成功，更新显示格式
                    widget.setStyleSheet("")
                    # 保存当前值作为有效值
                    widget.setProperty("last_valid_value", text)
                            
                    # 根据类型格式化显示
                    if dtype in ("UINT8", "UINT16", "UINT32"):
                        if element == "时间":
                            widget.setText(str(result))
                        else:
                            widget.setText(f"{result} (0x{result:X})")
                    elif dtype in ("INT8", "INT16", "INT32"):
                        widget.setText(str(result))
                    else:
                        widget.setText(str(result))
            except Exception as e:
                # 转换失败，显示错误
                field_name = element if element else "该字段"
                QMessageBox.warning(
                    self,
                    "输入格式错误",
                    f"{field_name}输入错误：无法转换为{dtype}类型\n\n"
                    f"请输入有效的十进制数字（如：123）或十六进制数字（如：0x1111）"
                )
                # 恢复上次有效值
                last_valid = widget.property("last_valid_value")
                if last_valid is None:
                    last_valid = ""
                widget.setText(str(last_valid))
                widget.setFocus()
                widget.setStyleSheet("color: red;")

    def create_protocol_table(self, template):
        """创建协议模板表格（支持ARRAY类型子表格）"""
        table = QTableWidget()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        
        # 设置表格列（还原为4列）
        headers = ["序号", "要素", "数据类型", "值"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # 从模型获取已保存的数据
        saved_data = self.smodel.get_protocol_data()
        
        # 存储子表格的引用
        self.subtables = {}
        
        # 填充表格
        row_idx = 0
        for field in template.get("fields", []):
            element = field.get("element", "")
            table.insertRow(row_idx)
            
            # 序号
            table.setItem(row_idx, 0, QTableWidgetItem(str(field.get("seq", row_idx+1))))
            
            # 要素
            table.setItem(row_idx, 1, QTableWidgetItem(element))
            
            # 数据类型
            dtype = field.get("dtype", "")
            table.setItem(row_idx, 2, QTableWidgetItem(dtype))
            
            # 值单元格
            value = saved_data.get(element, field.get("value", ""))
            editable = field.get("editable", True)
            
            # 特殊处理："时间"字段即使模板中editable为false，也设置为可编辑
            if element == "时间":
                editable = True
            
            # ARRAY 简易实现：使用可编辑文本，输入空格分隔的0x..序列
            if isinstance(dtype, str) and dtype.upper().endswith("ARRAY"):
                edit = QLineEdit(str(value))
                edit.editingFinished.connect(lambda e=edit, el=element: None)
                table.setCellWidget(row_idx, 3, edit)
            else:
                if editable:
                    # 特例：消息控制字使用下拉框 0/1/2/3
                    if element == "消息控制字":
                        combo = QComboBox()
                        combo.addItem("0x0000", 0)
                        combo.addItem("0x0001", 1)
                        combo.addItem("0x0002", 2)
                        combo.addItem("0x0003", 3)
                        # 初始化选中
                        try:
                            cv = self.safe_hex_to_int(value)
                        except Exception:
                            cv = 0
                        idx = combo.findData(cv)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                        combo.currentIndexChanged.connect(self.calculate_auto_fields)
                        table.setCellWidget(row_idx, 3, combo)
                    else:
                        edit = QLineEdit(str(value))
                        # 确保字体不加粗，与其他字段保持一致
                        font = edit.font()
                        font.setBold(False)
                        edit.setFont(font)
                        # 保存初始值作为有效值
                        edit.setProperty("last_valid_value", str(value))
                        edit.editingFinished.connect(lambda e=edit, dt=dtype, el=element: self.on_edit_finished(e, dt, el))
                        # "时间"字段左对齐
                        if element == "时间":
                            edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        table.setCellWidget(row_idx, 3, edit)
                else:
                    label = QLabel(str(value))
                    # 确保字体不加粗，与其他字段保持一致
                    font = label.font()
                    font.setBold(False)
                    label.setFont(font)
                    # "时间"、"帧计数"和"数据区crc校验和"左对齐，与其他字段保持一致
                    if element in ["时间", "帧计数", "数据区crc校验和"]:
                        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        label.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row_idx, 3, label)
            
            row_idx += 1
        
        return table

    


    def refresh_protocol_template(self, template):
        """刷新协议模板显示"""
        
        # 如果已有协议模板区域，先移除
        if "protocol_template" in self.field_widgets:
            widget = self.field_widgets["protocol_template"]
            # 找到它在表单中的位置并安全移除
            try:
                for i in range(self.form_layout.rowCount()):
                    layout_item = self.form_layout.itemAt(i, QFormLayout.FieldRole)
                    if layout_item and layout_item.widget() == widget:
                        self.form_layout.removeRow(i)
                        break
            except RuntimeError:
                # 如果form_layout已经被删除，忽略错误
                print("form_layout已被删除，跳过移除操作")
            
            # 从field_widgets中移除
            del self.field_widgets["protocol_template"]
        
        # 如果没有模板（协议类型为"无"），清空protocol_data并删除protocol_table
        if not template:
            self.smodel.set_protocol_data({})
            
            # 安全地删除protocol_table属性
            if hasattr(self, 'protocol_table'):
                del self.protocol_table
                print("协议类型为'无'，已清空protocol_data并删除protocol_table")
            else:
                print("协议类型为'无'，已清空protocol_data")
            return
        
        # 添加新的协议模板区域
        if template:
            try:
                template_group = QGroupBox("协议模板")
                template_layout = QVBoxLayout()
                
                # 添加模板名称标签
                template_name_label = QLabel(f"模板: {template['name']}")
                template_layout.addWidget(template_name_label)
                
                # 添加协议模板表格
                self.protocol_table = self.create_protocol_table(template)
                self.protocol_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
                template_layout.addWidget(self.protocol_table)
                
                template_id = template.get("id")
                if template_id in ("glink_std", "glink_ext"):
                    self.update_protocol_time_from_step()
                
                # 更新功能已整合到保存按钮中，移除单独的更新按钮
                
                template_group.setLayout(template_layout)
                template_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
                
                # 添加到表单
                self.form_layout.addRow(template_group)
                self.field_widgets["protocol_template"] = template_group
            except RuntimeError as e:
                print(f"添加协议模板时出错: {e}")



    def calculate_auto_fields(self):
        """计算自动字段的值"""
        # 在计算前先同步当前表单中的值，确保无需保存也能参与计算
        try:
            self.get_step_data()
        except Exception as e:
            print(f"同步表单数据时出错: {e}")
        
        # 获取当前流程步类型和协议类型
        step_type = self.smodel.get_step_type()
        protocol_type = self.smodel.get_base_step_data().get("protocol_type", 0)
        
        print(f"计算自动字段 - step_type: {step_type}, protocol_type: {protocol_type}")
        
        # 获取协议模板（如果协议类型为-1，则不获取模板）
        if protocol_type == -1:
            protocol_template = None
            # 协议类型为"无"，清空protocol_data
            self.smodel.set_protocol_data({})
            print("协议类型为'无'，calculate_auto_fields已清空protocol_data")
            return
        else:
            protocol_template = self.template_manager.get_template_by_step_and_protocol(step_type, protocol_type)
        
        if not protocol_template:
            print("未找到协议模板")
            # 未找到模板时也清空protocol_data，避免保留旧数据
            self.smodel.set_protocol_data({})
            return
        
        print(f"使用协议模板: {protocol_template.get('name', 'Unknown')}")
        
        # 安全地检查protocol_table是否存在且有效
        if not hasattr(self, 'protocol_table'):
            print("protocol_table不存在，calculate_auto_fields跳过表格数据读取")
            return
        
        try:
            # 尝试访问protocol_table来检查它是否仍然有效
            _ = self.protocol_table.rowCount()
        except (RuntimeError, AttributeError):
            # protocol_table已被删除或无效
            print("protocol_table已被删除或无效，calculate_auto_fields跳过表格数据读取")
            return
        
        if self.protocol_table is None:
            print("protocol_table为None，calculate_auto_fields跳过表格数据读取")
            return
            
        try:
            # 从表格中获取数据
            protocol_data = {}
            for row in range(self.protocol_table.rowCount()):
                element_item = self.protocol_table.item(row, 1)
                if element_item:
                    element = element_item.text()
                    value_widget = self.protocol_table.cellWidget(row, 3)
                    
                    if isinstance(value_widget, QLineEdit) and not value_widget.isReadOnly():
                        protocol_data[element] = value_widget.text()
                    elif isinstance(value_widget, QComboBox):
                        dv = value_widget.currentData()
                        if element == "消息控制字" and isinstance(dv, int):
                            protocol_data[element] = f"0x{dv:04X}"
                        else:
                            protocol_data[element] = value_widget.currentText()
                    else:
                        # 对于只读字段，我们可能需要重新计算
                        protocol_data[element] = value_widget.text() if isinstance(value_widget, QLabel) else ""
        except (RuntimeError, AttributeError) as e:
            # 在遍历过程中如果protocol_table被删除或无效，捕获异常
            print(f"访问protocol_table时出错: {e}，calculate_auto_fields跳过表格数据读取")
            return
        
        print(f"从表格获取的数据: {protocol_data}")
        
        # 同步数据区字段 - 从流程步详情获取数据区
        try:
            data_region_from_step = self.get_data_region_from_step()
            print(f"从流程步获取的数据区: {data_region_from_step}")
            if data_region_from_step:
                protocol_data["数据区"] = data_region_from_step
        except Exception as e:
            print(f"获取数据区时出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 根据模板类型执行不同的计算
        template_id = protocol_template.get("id", "")
        print(f"模板ID: {template_id}")
        
        if template_id in ("glink_std", "glink_ext"):
            self.update_protocol_time_from_step(protocol_data)
        
        try:
            if template_id == "serial_std":
                self.calc_serial_std_fields(protocol_data)
            elif template_id == "serial_ext":
                self.calc_serial_ext_fields(protocol_data)
            elif template_id == "crc_tail":
                self.calc_crc_tail_fields(protocol_data)
            elif template_id == "glink_std":
                self.calc_glink_fields(protocol_data)
            elif template_id == "glink_ext":
                self.calc_glink_fields(protocol_data)
            elif template_id == "bus1553_std":
                self.calc_glink_fields(protocol_data)  # 使用相同的计算逻辑
            elif template_id == "bus1553_ext":
                self.calc_glink_fields(protocol_data)  # 使用相同的计算逻辑
            else:
                print(f"未知的模板ID: {template_id}")
        except Exception as e:
            print(f"计算自动字段时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.smodel.set_protocol_data(protocol_data)




