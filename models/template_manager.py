import json
import os
from pathlib import Path

"""
TemplateManager: 管理协议模板的单例类
- 从配置文件加载模板及其适用的流程步类型
- 根据 step_type / protocol_type 获取模板
- 提供协议类型下拉框的可选项
"""


class TemplateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TemplateManager, cls).__new__(cls)
            cls._instance.load_templates()
        return cls._instance

    def load_templates(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_file = os.path.join(script_dir, "protocol_templates.json")
        model_config = os.path.join(script_dir, "model_config.json")

        self.templates = []
        self.data_types = {}
        self.template_dict = {}
        self.templates_by_step = {}
        self.templates_by_key = {}
        self.none_value = -1
        self.none_label = "无"

        self.step_type_names = self._load_step_type_names(model_config)
        self.step_type_map = {name: idx for idx, name in enumerate(self.step_type_names)}

        try:
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.templates = data.get("templates", [])
                self.data_types = data.get("data_types", {})
                none_opt = data.get("none_option", {})
                self.none_value = none_opt.get("value", -1)
                self.none_label = none_opt.get("label", "无")
        except Exception as exc:
            print(f"加载协议模板失败: {exc}")
            return

        self.template_dict = {tpl["id"]: tpl for tpl in self.templates if "id" in tpl}
        self._build_indices()

    def _load_step_type_names(self, config_path: str):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("step_types", {}).get("support_types", [])
        except Exception as exc:
            print(f"加载step_type配置失败: {exc}")
            return []

    def _resolve_step_types(self, entries):
        indices = set()
        for entry in entries or []:
            if isinstance(entry, int):
                indices.add(entry)
            elif isinstance(entry, str):
                idx = self.step_type_map.get(entry)
                if idx is not None:
                    indices.add(idx)
        return sorted(idx for idx in indices if idx is not None)

    def _build_indices(self):
        self.templates_by_step = {}
        self.templates_by_key = {}
        for tpl in self.templates:
            value = tpl.get("protocol_value")
            if value is None:
                continue
            resolved_steps = self._resolve_step_types(tpl.get("step_types", []))
            tpl["step_type_indices"] = resolved_steps
            merge_flag = tpl.get("merge_8bit_to_16bit")
            if merge_flag is None:
                tpl["merge_8bit_to_16bit"] = True
            for step_idx in resolved_steps:
                self.templates_by_step.setdefault(step_idx, []).append(tpl)
                self.templates_by_key[(step_idx, value)] = tpl

    def get_protocol_options_for_step(self, step_type: int):
        options = [{"value": self.none_value, "label": self.none_label}]
        templates = self.templates_by_step.get(step_type, [])
        
        # 根据流程步类型过滤协议模板
        for tpl in templates:
            protocol_value = tpl.get("protocol_value")
            template_name = tpl.get("name")
            
            # GLINK流程步（非周期0/周期1）：过滤掉GLINK扩展模板（protocol_value=1）
            if step_type in [0, 1] and protocol_value == 1:
                continue
            
            # 1553流程步（非周期4/周期5）：过滤掉1553扩展模板（protocol_value=5）
            if step_type in [4, 5] and protocol_value == 5:
                continue
            
            options.append({"value": protocol_value, "label": template_name})
        
        return options

    def get_template_by_id(self, template_id):
        return self.template_dict.get(template_id)

    def get_data_type_info(self, dtype):
        return self.data_types.get(dtype, {})

    def is_step_type_template_valid(self, step_type: int) -> bool:
        return step_type in self.templates_by_step and bool(self.templates_by_step[step_type])

    def get_template_by_step_and_protocol(self, step_type, protocol_type):
        if protocol_type == self.none_value:
            return None
        return self.templates_by_key.get((step_type, protocol_type))


template_manager = TemplateManager()