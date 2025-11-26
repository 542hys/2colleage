class GlobalConfigController:
    def __init__(self, model, view, window_controller):
        """全局配置控制器，负责全局参数的更新和视图交互"""
        '''可以与window_controller合并'''
        self.model = model
        self.global_view = view
        self.window_controller = window_controller
    # 负责全局参数相关逻辑

    def connect_signals(self):
        
         # 全局视图
        # self.global_view.timeout_edit.editingFinished.connect(self.update_global_model)
        # self.global_view.retries_edit.editingFinished.connect(self.update_global_model)
        # self.global_view.env_combo.currentIndexChanged.connect(self.update_global_model)
        # self.global_view.bus_combo.currentIndexChanged.connect(self.update_global_model)
        self.global_view.save_btn.clicked.connect(self.update_global_model)
        self.global_view.load_signal.connect(self.update_global_model)

        # connect 是在上一级的controller中统一完成的，如果搬到搬到构造函数里会好一点，这里为了方便这样写
        # 如果connect在构造函数中完成，则下面这一行加载配置就放在构造函数的最后
        # 初始加载配置已在GlobalConfigView的__init__中完成，这里不需要再次调用

        

    def update_global_model(self):
        """从全局视图更新模型"""
        data = self.global_view.get_data()
        for key, value in data.items():
            self.model.set_global_param(key, value)

        config_manager = getattr(self.global_view, "config_manager", None)
        if config_manager is not None:
            self.model.set_global_param("protocols", config_manager.get_all_protocol_configs())

        print("全局参数已更新:", self.model.global_params.get("input_path", "get None path"))
        print("now get global view update")
        self.window_controller.update_window_title()
        self.update_all_steps()
        # self.update_global_view()

    
    def update_global_view(self):
        """从模型更新全局视图"""
        # print("update global view")
        self.global_view.set_data(self.model.global_params)

    def update_all_steps(self):
        """更新所有流程步的全局配置信息"""
        if not self.model or not self.model.steps:
            return
        
        # 获取全局配置值
        global_params = self.model.global_params
        
        for step in self.model.steps:
            # 获取当前流程步的step_type
            current_step_type = step.get_step_type()
            # 更新流程步的全局配置值，同时保留原step_type
            step.update_base_data({
                'step_type': current_step_type,
                **global_params
            })
        
        # 刷新当前选中的步骤详情，确保界面显示正确
        if hasattr(self, 'step_list_controller') and hasattr(self.step_list_controller, 'on_step_selected'):
            self.step_list_controller.on_step_selected()

