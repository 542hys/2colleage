from PyQt5.QtCore import Qt, QMimeData, QByteArray, pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QListWidget, QHeaderView, QLineEdit, QAbstractItemView,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem,QButtonGroup, 
)
from PyQt5.QtGui import QClipboard, QKeySequence, QColor, QBrush, QFont, QDrag,QPainter

from models.step_model import TABLE_COLUMNS
from models.step_model import STYPE
import models.step_model as step_model
from utils.conf import (TITEL_STRING, UP_STRING, DOWN_STRING, ADD_STRING,
                        EDIT_STRING, DELETE_STRING)




class StepTableWidget(QTableWidget):
    """自定义表格控件，支持拖放移动行并发射信号"""
    step_moved = pyqtSignal(int, int)  # 参数：原行，目标行
    # 新增：按 Delete/Backspace 删除请求信号
    delete_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.drag_start_row = -1

    def startDrag(self, supportedActions):
        """开始拖动时记录原始行"""
        print("start drag")
        self.drag_start_row = self.currentRow()
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        """处理拖放事件"""
        # 先调用基类方法，让表格可以更新行位置
        # super().dropEvent(event)

                # 获取鼠标释放位置
        pos = event.pos()
        
        # 获取目标行索引
        target_row = self.indexAt(pos).row()
        
        # 如果拖放到空白区域，则放在最后
        if target_row < 0:
            target_row = self.rowCount() - 1
            
        # 获取放置位置指示器类型
        drop_indicator_position = self.dropIndicatorPosition()
        
        # 根据放置指示器位置调整目标行
        if drop_indicator_position == QAbstractItemView.BelowItem:
            target_row += 1
        
        # 获取目标行（移动后当前选中的行）
        # drop_row = self.currentRow()
        print(f"do event start row {self.drag_start_row} to {target_row}")
        # 检查是否有效拖动
        if self.drag_start_row >= 0 and target_row >= 0 and self.drag_start_row != target_row:
            # 发射移动信号
            self.step_moved.emit(self.drag_start_row, target_row)
            print(f"Table widget emitted step move: from {self.drag_start_row} to {target_row}")
        
        # 重置拖动起始行
        self.drag_start_row = -1
        event.accept()

    def keyPressEvent(self, event):
        """拦截键盘事件，支持 Delete 和 Backspace 删除当前选中步骤"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)

class StepListView(QGroupBox):
    """步骤列表视图（表格版）- 支持拖放和美化界面"""

    # 信号需要在类顶层定义
    step_moved = pyqtSignal(int, int)

    def __init__(self, parent=None, columns=None):
        super().__init__(TITEL_STRING, parent)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(10)
        
        # 标题和搜索框布局
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        # 添加标题图标
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #c0c0c0;
                border-radius: 5px;
                margin-top: 1.5ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索步骤名称...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #4a90e2;
            }
        """)
        header_layout.addWidget(self.search_edit)
                # +++ 添加忽略状态筛选按钮 +++
        # 创建按钮组
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)
        # self.filter_group.setExclusive(True)  # 互斥选择
        # 未忽略按钮
        self.unignored_btn = QPushButton("显示未忽略")
        self.unignored_btn.setCheckable(True)
        self.unignored_btn.setChecked(True)  # 默认显示未忽略步骤
        self.unignored_btn.setToolTip("显示未忽略的步骤")
        
        # 已忽略按钮
        self.ignored_btn = QPushButton("显示已忽略")
        self.ignored_btn.setCheckable(True)
        self.ignored_btn.setChecked(True)  # 默认显示已忽略步骤
        self.ignored_btn.setToolTip("显示已忽略的步骤")

        self.unignored_btn.setIcon(self.style().standardIcon(
            QStyle.SP_DialogYesButton if self.unignored_btn.isChecked() 
            else QStyle.SP_DialogNoButton
        ))
        self.ignored_btn.setIcon(self.style().standardIcon(
            QStyle.SP_DialogYesButton if self.ignored_btn.isChecked() 
            else QStyle.SP_DialogNoButton
        ))
        # self.show_unignored_btn.clicked.connect(self.on_filter_changed)
        # self.show_ignored_btn.clicked.connect(self.on_filter_changed)
        # 添加到按钮组
        # self.filter_group.addButton(self.unignored_btn, 1)
        # self.filter_group.addButton(self.ignored_btn, 2)

        filter_layout.addWidget(self.unignored_btn)
        filter_layout.addWidget(self.ignored_btn)
        
        header_layout.addLayout(filter_layout)
        layout.addLayout(header_layout)
        
        # 改变时进行搜索
        self.search_edit.textChanged.connect(self.on_search)
        self.unignored_btn.clicked.connect(self.on_filter_changed)
        self.ignored_btn.clicked.connect(self.on_filter_changed)
        # self.filter_group.buttonClicked.connect(self.on_filter_changed)
        # 拖动时处理
        

        # 自定义要显示的字段及表头TABLE_COLUMNS(key, label)
        self.columns = TABLE_COLUMNS

        # 创建表格控件
        self.table_widget = StepTableWidget()
        self.table_widget.setColumnCount(len(self.columns))
        self.table_widget.setHorizontalHeaderLabels([col[1] for col in self.columns])
        
        # 设置表格样式
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f8f8;
                gridline-color: #e0e0e0;
                border: none;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #d8e8ff;
                color: black;
            }
        """)
        
        # 设置交替行颜色
        # self.table_widget.setAlternatingRowColors(True)
        
        # 让表头自适应窗口宽度
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 序号列自适应内容
        for i in range(1, self.table_widget.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)       # 其它列等比例填充
        
        self.table_widget.verticalHeader().setVisible(False)  # 隐藏默认行头
        
        # 添加拖放支持
        
        self.table_widget.setDragEnabled(True)
        self.table_widget.setAcceptDrops(True)
        self.table_widget.setDropIndicatorShown(True)
        self.table_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # 设置高亮委托
        # self.highlight_delegate = SimpleHighlightDelegate(self.table_widget)
        # self.table_widget.setItemDelegate(self.highlight_delegate)
        
        # 添加表格到布局
        layout.addWidget(self.table_widget)

        #表格行拖动处理
        self.table_widget.step_moved.connect(self.handle_step_moved)
        
        # 按钮区域 - 使用两行布局
        btn_container = QVBoxLayout()
        btn_container.setSpacing(10)
        
        # 第一行按钮
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(5)
        
        self.add_btn = self.create_tool_button(ADD_STRING, "SP_FileDialogNewFolder")
        # self.edit_btn = self.create_tool_button(EDIT_STRING, "SP_FileDialogDetailedView")
        self.remove_btn = self.create_tool_button(DELETE_STRING, "SP_TrashIcon")
        
        btn_row1.addWidget(self.add_btn)
        # btn_row1.addWidget(self.edit_btn)
        btn_row1.addWidget(self.remove_btn)
        btn_row1.addStretch()
        
        # 第二行按钮
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(5)
        
        self.up_btn = self.create_tool_button(UP_STRING, "SP_ArrowUp")
        self.down_btn = self.create_tool_button(DOWN_STRING, "SP_ArrowDown")
        self.copy_btn = self.create_tool_button("复制", "SP_DialogSaveButton")
        self.cut_btn = self.create_tool_button("剪切", "SP_DialogResetButton")
        self.paste_btn = self.create_tool_button("粘贴", "SP_DialogOpenButton")
        
        btn_row2.addWidget(self.up_btn)
        btn_row2.addWidget(self.down_btn)
        btn_row2.addStretch()
        btn_row2.addWidget(self.copy_btn)
        btn_row2.addWidget(self.cut_btn)
        btn_row2.addWidget(self.paste_btn)
        
        btn_container.addLayout(btn_row1)
        btn_container.addLayout(btn_row2)
        layout.addLayout(btn_container)
        
        # 设置快捷键
        self.copy_btn.setShortcut(QKeySequence.Copy)  # 绑定Ctrl+C
        self.paste_btn.setShortcut(QKeySequence.Paste)  # 绑定Ctrl+V
        self.cut_btn.setShortcut(QKeySequence.Cut)  # 绑定Ctrl+X
        
        # 确保窗口能接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)

        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    

        self.steps = []
        self.filtered_indices = [] # 用于筛选时选中的详情idx，存储原始索引
        self.index_mapping = {}    # 映射字典: {原始索引: 筛选后索引}
        self.setLayout(layout)
        
    
    def create_tool_button(self, text, icon_name):
        """创建带图标的工具按钮"""
        btn = QPushButton(text)
        btn.setIcon(self.style().standardIcon(getattr(QStyle, icon_name)))
        btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background-color: #f0f0f0;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        return btn

    def step_clear(self):
        self.steps = []
        self.index_mapping = {}
        self.filtered_indices = []
        self.table_widget.setRowCount(0)

    def search_clear(self):
        self.search_edit.setText("")
        # self.highlight_delegate.set_search_text("")

    def set_steps(self, steps):
        """设置步骤列表（表格显示）"""
        self.steps = steps
        self.on_search(self.search_edit.text())
        # self.show_steps(steps)

    def show_steps(self, steps, search_text=""):
        self.table_widget.setRowCount(0)
        
        # 如果有搜索文本，设置高亮
        # search_text = self.search_edit.text().strip()
        # self.highlight_delegate.set_search_text(search_text)

        highlight_color = QColor(255, 255, 0, 100)  # 黄色半透明
        
        for idx, step in enumerate(steps, 1):
            if not step:
                continue
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            
            # 序号列
            index_item = QTableWidgetItem(str(idx))
            index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)
            index_item.setData(Qt.TextAlignmentRole, Qt.AlignCenter)
            index_item.setFont(QFont("Arial", 9, QFont.Bold))
            self.table_widget.setItem(row, 0, index_item)
            bstp = step.get_base_step_data()
            
            from models.step_model import IS_IGNORE
            is_ignore = bstp.get(IS_IGNORE, 0)
            # 名称列
            name = bstp.get("name", "")
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table_widget.setItem(row, 1, name_item)
            # 其他字段
            for col_idx, (key, _) in enumerate(self.columns[1:], 1):
                
                value = bstp.get(key, "")
                
                if key == STYPE:
                    value = step_model.get_step_type_label_by_idx(value)
                
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
                self.table_widget.setItem(row, col_idx, item)
            if is_ignore:
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row, col)
                    if item:
                        # 设置灰色前景色
                        item.setForeground(QBrush(QColor(192, 192, 192)))
                        # 如果需要也可以设置灰色背景色
                        # item.setBackground(QBrush(QColor(250, 250, 250)))
            # 高亮匹配项
            if search_text and search_text.lower() in name.lower():
                # 设置整行高亮背景
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row, col)
                    if item:
                        item.setBackground(highlight_color)
            

    def on_filter_changed(self):
        """处理筛选按钮点击事件"""
        # 触发搜索更新
        # 更新按钮图标
        # show_unignored = self.unignored_btn.isChecked()
        # show_ignored = self.ignored_btn.isChecked()
        self.unignored_btn.setIcon(self.style().standardIcon(
            QStyle.SP_DialogYesButton if self.unignored_btn.isChecked() 
            else QStyle.SP_DialogNoButton
        ))
        self.ignored_btn.setIcon(self.style().standardIcon(
            QStyle.SP_DialogYesButton if self.ignored_btn.isChecked() 
            else QStyle.SP_DialogNoButton
        ))
        self.on_search(self.search_edit.text())

    def on_search(self, text):
        """根据搜索框内容过滤流程步名称"""
        self.filtered_indices = []
        self.index_mapping = {}
        # self.clear_highlights()
        # 更新高亮委托
        # if not text:
        #     self.highlight_delegate.set_search_text(text.lower())
        show_unignored = self.unignored_btn.isChecked()
        show_ignored = self.ignored_btn.isChecked()

        if not show_unignored and not show_ignored:
            self.show_steps([])
            return

        # if not text:
        #     self.show_steps(self.steps)
        #     return
        
        # 过滤步骤
        for index, step in enumerate(self.steps):
            step_data = step.get_base_step_data()
            name = step_data.get("name", "")
            is_ignored = step_data.get("is_ignore", 0) == 1

            # 检查名称匹配
            name_match = not text or text.lower() in name.lower()#非空文本可以直接
            # 忽略状态匹配
            # 如果未选中任何筛选按钮，则不显示任何步骤
            ignore_match = (is_ignored and show_ignored) or (not is_ignored and show_unignored)
            
            if name_match and ignore_match:
                self.filtered_indices.append(index)
                self.index_mapping[index] = len(self.filtered_indices) - 1
        
        # 显示过滤后的步骤
        filtered_steps = [self.steps[i] for i in self.filtered_indices]
        self.show_steps(filtered_steps, search_text=text)

    def get_selected_index(self):
        """获取当前选中的步骤索引"""
        current_row = self.table_widget.currentRow()
        if current_row < 0:
            return -1
        
        if self.filtered_indices:
            if current_row < len(self.filtered_indices):
                return self.filtered_indices[current_row]
        else:
            return current_row

    def set_selected_index(self, index):
        """设置选中的步骤索引"""
        if not self.steps:
            return
            
        # 在筛选状态下
        if self.filtered_indices:
            if index in self.filtered_indices:
                mapped_index = self.index_mapping[index]
                self.table_widget.selectRow(mapped_index)
                self.table_widget.scrollToItem(
                    self.table_widget.item(mapped_index, 0),
                    QAbstractItemView.PositionAtCenter
                )
            return
        
        # 在非筛选状态下
        if 0 <= index < self.table_widget.rowCount():
            self.table_widget.selectRow(index)
            self.table_widget.scrollToItem(
                self.table_widget.item(index, 0),
                QAbstractItemView.PositionAtCenter
            )


    def handle_step_moved(self, from_row, to_row):
        """处理表格行移动事件"""
        # 在过滤状态下，需要映射回原始索引
        if self.filtered_indices:
            # 获取过滤状态下的原始索引
            original_from = self.filtered_indices[from_row]
            original_to = self.filtered_indices[to_row]
            print(f"Filtered move: {from_row}->{to_row} maps to {original_from}->{original_to}")
            self.step_moved.emit(original_from, original_to)
        else:
            # 没有过滤，直接使用行索引
            print(f"Direct move: {from_row}->{to_row}")
            self.step_moved.emit(from_row, to_row)

