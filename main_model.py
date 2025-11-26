class DataModel:
    """存储测试配置的核心数据模型"""
    def __init__(self):
        self.global_params = {
        }
        self.path_setting = {}
        self.steps = []
        self.file_path = None
        self.dirty = False  # 标记数据是否已修改未保存
    
    def to_dict(self):
        """将模型数据转换为字典"""
        return {
            "global_params": self.global_params,
            "steps": self.steps
        }
    
    def sort_steps_by_time(self):
        """根据步骤的 base_data["time"] 进行升序排序"""
        # 使用 sorted() 函数和自定义排序键
        sorted_steps = sorted(self.steps, key=lambda step: step.base_step_data.get("time", 0))
        
        # 检查排序是否改变了列表顺序
        if sorted_steps != self.steps:
            self.steps = sorted_steps
            self.dirty = True
            return True  # 返回排序是否实际发生了改变
        return False

    def from_dict(self, data):
        """从字典加载数据到模型"""
        self.global_params = data.get("global_params", {})
        self.steps = data.get("steps", [])
        self.dirty = False
    
    def add_step(self, step_data):
        """添加新步骤"""
        self.steps.append(step_data)
        self.dirty = True
    
    def update_step(self, index, step_data):
        """更新步骤"""
        if 0 <= index < len(self.steps):
            self.steps[index] = step_data
            self.dirty = True
    
    def remove_step(self, index):
        """删除步骤"""
        if 0 <= index < len(self.steps):
            del self.steps[index]
            self.dirty = True
    
    def move_step(self, from_index, to_index):
        """移动步骤位置"""
        if 0 <= from_index < len(self.steps) and 0 <= to_index < len(self.steps):
            step = self.steps.pop(from_index)
            self.steps.insert(to_index, step)
            self.dirty = True
    
    def set_global_param(self, key, value):
        """设置全局参数"""
        if key in self.global_params and self.global_params[key] != value:
            self.global_params[key] = value
            self.dirty = True
        else:
            self.global_params[key] = value
            self.dirty = False  # 新增参数不标记为修改
    
    def is_dirty(self):
        """检查数据是否已修改"""
        return self.dirty
    
    def reset_dirty(self):
        """重置修改标志"""
        self.dirty = False