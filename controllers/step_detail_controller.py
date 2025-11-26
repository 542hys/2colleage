from PyQt5.QtCore import QObject, pyqtSignal  # 或其他GUI库的信号机制

class StepDetailController(QObject):
    step_save_signal_finish = pyqtSignal()
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.step_detail_view = view
        self.step_detail_view.set_model(model)  # 设置model引用，用于帧计数计算
        self.step_detail_view.step_save_signal.connect(self.save_step_detail)
        #save_btn点击时应当同时更新list
        #要将view中的save_btn.clicked连接到list_controller中的update_list
        #可以在list_controller中用detail_controller.detail_view.save_btn.clicked.connect
        #一般而言不要越级调用，这里就用信号机制完成这个逻辑

    def connect_signals(self):
        """连接信号 - 在构造函数中已经连接了主要信号"""
        # 主要信号在构造函数中已经连接
        # 这里可以添加其他需要延迟连接的信号
        pass

    def save_step_detail(self):
        #更新数据
        self.step_detail_view.get_step_data()
        #刷新详情
        self.step_detail_view.refresh_fields()
        #发送保存完成信号，以便刷新列表
        self.step_save_signal_finish.emit()


    def update_step_detail(self, index):
        """更新步骤详情视图"""
        if 0 <= index < len(self.model.steps):
            self.clear_step_detail()
            self.step_detail_view.refresh_fields(self.model.steps[index])
        else:
            self.clear_step_detail()
    
    def clear_step_detail(self):
        """清空步骤详情视图"""
        self.step_detail_view.clear()




