# from views.dialog import StepConfigDialog
from PyQt5.QtWidgets import QDialog
from models.step_model import StepModel
import pickle
from PyQt5.QtCore import QMimeData, QByteArray, QTimer
from PyQt5.QtWidgets import QApplication

class StepListController:
    def __init__(self, model, list_view, step_detail_controller, global_controller, strings):
        self.model = model
        self.step_list_view = list_view
        self.step_detail_controller = step_detail_controller
        self.global_controller = global_controller
        self.STRINGS = strings
    
    def connect_signals(self):
        """连接步骤列表视图信号"""
        # 步骤列表视图
        self.step_list_view.table_widget.itemSelectionChanged.connect(self.on_step_selected)
        # 键盘删除支持（Delete/Backspace）
        self.step_list_view.table_widget.delete_pressed.connect(self.remove_step)
        self.step_list_view.add_btn.clicked.connect(self.add_step)
        # self.step_list_view.edit_btn.clicked.connect(self.edit_step)
        self.step_list_view.remove_btn.clicked.connect(self.remove_step)
        self.step_list_view.up_btn.clicked.connect(self.move_step_up)
        self.step_list_view.down_btn.clicked.connect(self.move_step_down)

        self.step_list_view.copy_btn.clicked.connect(self.copy_step)
        self.step_list_view.cut_btn.clicked.connect(self.cut_step)
        self.step_list_view.paste_btn.clicked.connect(self.paste_step)
        self.step_list_view.step_moved.connect(self.move_step)

        self.step_detail_controller.step_save_signal_finish.connect(self.update_step_list)
        # 为按钮设置系统标准快捷键


    # def enable_drag_drop(self):
    #     self.step_list_view.setDragEnabled(True)
    #     self.step_list_view.setAcceptDrops(True)
    #     self.step_list_view.setDropIndicatorShown(True)
    #     self.step_list_view.setDragDropMode(QAbstractItemView.InternalMove)

    def clear_step_data(self):
        print(f"step_list_controller: {len(self.model.steps)}")
        self.step_list_view.step_clear()


    def update_step_list(self):
        """更新步骤列表视图"""
        # 保存当前选中的步骤索引
        current_selected_index = self.step_list_view.get_selected_index()
        
        self.model.sort_steps_by_time()  # 确保步骤按时间排序
        #由于是在拖拽后进行的更新步骤列表，所以可以获得同时间流程步之间可以互换位置
        self.step_list_view.set_steps(self.model.steps)

        #列表更新后 清除搜索框内容 避免出错
        #可以绑定把detail的东西清空 或者在搜索框更新后把detail清空
        # 恢复之前的选中状态，保持用户在当前流程步界面
        if current_selected_index >= 0:
            self.step_list_view.set_selected_index(current_selected_index)
        else:
            self.step_list_view.set_selected_index(-1)
            self.step_list_view.search_clear()

    def add_step(self):
        """添加新步骤"""
        new_step_model = StepModel()
        self.model.add_step(new_step_model)
        self.update_step_list()
        self.step_list_view.set_selected_index(len(self.model.steps) - 1)
        ### 需要主controller给接口
        # self.global_controller.update_global_view()
        # print(f"before dialog add init stype: {new_step_model.step_type}")
        # dialog = StepConfigDialog(smodel=new_step_model, strings=self.STRINGS["dialog"])
        # if dialog.exec_() == QDialog.Accepted:#需要添加检查
        #     step_data = dialog.get_step_data()
        #     # print(f"add_step:"+step_data)
        #     if not step_data:
        #         print("添加步骤数据为空，操作取消")
        #         return
        #     self.model.add_step(step_data)
        #     self.update_step_list()
        #     self.step_list_view.set_selected_index(len(self.model.steps) - 1)
        #     ### 需要主controller给接口
        #     self.global_controller.update_global_view()
        
        # self.step_list_view.search_clear()

    def on_step_selected(self):
        """步骤选择变化事件"""
        index = self.step_list_view.get_selected_index()
        
        ### 这个部分的处理逻辑要与update_window_title()处理类似？，由主controller给接口
        self.step_detail_controller.update_step_detail(index)

    def set_selected_step(self, index):
        """设置选中的步骤"""
        if 0 <= index < len(self.model.steps):
            
            self.step_list_view.set_selected_index(index)
            # self.step_detail_controller.update_step_detail(index)
        else:
            print(f"无效的步骤索引: {index}")
    
    # def edit_step(self):
    #     """编辑步骤"""
    #     index = self.step_list_view.get_selected_index()
    #     print(f"edit_step: {index}")
    #     if 0 <= index < len(self.model.steps):
    #         dialog = StepConfigDialog(smodel=self.model.steps[index], strings=self.STRINGS["dialog"])
    #         if dialog.exec_() == QDialog.Accepted:
    #             step_data = dialog.get_step_data()
    #             if not step_data:
    #                 print("编辑步骤数据为空，操作取消")
    #                 return
    #             self.model.update_step(index, step_data)
    #             self.update_step_list()
    #             self.step_list_view.set_selected_index(index)
    #             self.step_detail_controller.update_step_detail(index)
    #             self.global_controller.update_global_view()
    
    def remove_step(self):
        """删除步骤"""
        index = self.step_list_view.get_selected_index()
        if 0 <= index < len(self.model.steps):
            self.model.remove_step(index)
            self.update_step_list()
            new_index = min(index, len(self.model.steps) - 1)
            self.step_list_view.set_selected_index(new_index)
            self.step_detail_controller.update_step_detail(new_index)
            self.global_controller.update_global_view()


    def move_step(self, from_index, to_index):
        print(f"step list controller move step idx_from {from_index}, to {to_index}")
        if 0 <= from_index < len(self.model.steps) and 0 <= to_index < len(self.model.steps):
            self.model.move_step(from_index, to_index)
            # self.step_list_view.set_steps(self.model.steps)
            self.step_list_view.search_clear()
            # 刷新视图 - 使用延迟刷新确保Qt完成内部更新
            QTimer.singleShot(0, self.update_step_list)
            # self.update_step_list()
            # self.step_list_view.set_steps(self.model.steps)

            #刷新视图
        print(f"step list controller move step update list")
        # self.update_step_list()
        self.step_list_view.set_selected_index(to_index)
        self.global_controller.update_global_view()

    
    def move_step_up(self):
        """上移步骤"""
        index = self.step_list_view.get_selected_index()
        if index > 0:
            self.model.move_step(index, index - 1)
            self.update_step_list()
            self.step_list_view.set_selected_index(index - 1)
            self.global_controller.update_global_view()
    
    def move_step_down(self):
        """下移步骤"""
        index = self.step_list_view.get_selected_index()
        if index >= 0 and index < len(self.model.steps) - 1:
            self.model.move_step(index, index + 1)
            self.update_step_list()
            self.step_list_view.set_selected_index(index + 1)
            self.global_controller.update_global_view()



    def copy_step(self):
        """复制当前选中的步骤"""
        index = self.step_list_view.get_selected_index()
        if 0 <= index < len(self.model.steps):
            # 序列化步骤对象
            step_data = self.model.steps[index]
            serialized = pickle.dumps(step_data)
            
            # 创建MIME数据
            mime_data = QMimeData()
            mime_data.setData("application/x-step-object", QByteArray(serialized))
            
            # 添加文本表示以便在其他程序中查看
            text_rep = f"Step: {step_data.get_name()}\nType: {step_data.get_step_type()}"
            mime_data.setText(text_rep)
            
            # 存入剪切板
            clipboard = QApplication.clipboard()
            clipboard.setMimeData(mime_data)
            
            # 更新状态
            # self.global_controller.update_status(f"已复制步骤: {step_data.name}")
            print(f"已复制步骤: {step_data.get_name()}")
            return True
        return False

    def cut_step(self):
        """剪切当前选中的步骤"""
        if self.copy_step():  # 先复制
            self.remove_step()  # 然后删除
            return True
        return False

    def paste_step(self):
        """粘贴步骤到当前选中位置之后"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        # 检查是否有我们的步骤数据
        if mime_data.hasFormat("application/x-step-object"):
            try:
                # 获取并反序列化数据
                byte_data = mime_data.data("application/x-step-object").data()
                step_data = pickle.loads(byte_data)
                
                # 确保粘贴的是StepModel对象
                if not isinstance(step_data, StepModel):
                    raise ValueError("剪切板内容不是有效的步骤对象")
                
                # 深拷贝对象以避免引用问题
                from copy import deepcopy
                new_step = deepcopy(step_data)
                # new_step.name = f"{new_step.get_name()} (副本)"  # 添加副本标记

                new_step.set_name(f"{new_step.get_name()} (副本)")
                
                # 确定插入位置
                index = self.step_list_view.get_selected_index()
                insert_index = index + 1 if index >= 0 else len(self.model.steps)
                
                # 插入步骤
                self.model.steps.insert(insert_index, new_step)
                self.update_step_list()
                self.step_list_view.set_selected_index(insert_index)
                self.step_detail_controller.update_step_detail(insert_index)
                self.global_controller.update_global_view()
                
                # 更新状态
                # self.global_controller.update_status(f"已粘贴步骤: {new_step.get_name()}")
                print(f"已粘贴步骤: {new_step.get_name()}")
                return True
            
            except Exception as e:
                print(f"粘贴失败: {str(e)}")
                # self.global_controller.update_status(f"粘贴失败: {str(e)}")
                print(f"粘贴步骤错误: {str(e)}")
                return False
        
        # 如果没有步骤数据，但剪切板有文本，则尝试作为新步骤创建
        elif mime_data.hasText():
            text = mime_data.text()
            print(("剪切板中没有步骤对象，创建新步骤"))
            # self.global_controller.update_status("剪切板中没有步骤对象，创建新步骤")
            return self._create_step_from_text(text)
        print("剪切板中没有可粘贴的内容")
        # self.global_controller.update_status("剪切板中没有可粘贴的内容")
        return False