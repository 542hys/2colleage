import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "model_config.json"
TEMPLATE_PATH = Path(__file__).parent / "protocol_templates.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    conf = json.load(f)


# 获取配置字符串
FIELD_CONF = conf["fields"]

STYPES = "step_types"
STYPE = "step_type"

TYPE_CONF = conf[STYPES]

#用来根据idx获取step_type
SUPPORTED_TYPES = TYPE_CONF["support_types"]

SUPPORTED_DTYPES= TYPE_CONF["support_data_types"]

def get_step_type_field_list(step_type: str = None, n: int = -1):
    """
    获取指定step_type的字段列表。
    如果step_type为'uint'，则返回SUPPORTED_TYPES的第n个对应的TYPE_CONF。
    """
    if not step_type:
        # print(n)
        if 0 <= n < len(SUPPORTED_TYPES):
            real_type = SUPPORTED_TYPES[n]
            return TYPE_CONF[real_type]
        else:
            raise IndexError(f"{n}超出SUPPORTED_TYPES范围")
    else:
        return TYPE_CONF[step_type]


BASIC_TYPE_FIELDS = TYPE_CONF["basic_fileds"]
VIEWS_CONF = conf["views_config"]

# 数据类型
FIELD_TYPES = FIELD_CONF["field_data_types"]
def get_field_type(field_name):
    """
    获取字段的数据类型
    :param field_name: 字段名称
    :return: 对应的字段数据类型
    """
    return FIELD_TYPES.get(field_name, "str")

# 字段中文标签
FIELD_LABELS = FIELD_CONF["field_labels"]
def get_field_label(field_name):
    """
    获取字段的中文标签
    :param field_name: 字段名称
    :return: 对应的中文标签
    """
    return FIELD_LABELS.get(field_name, field_name)

# 字段默认值
FIELD_DEFAULTS = FIELD_CONF["field_defaults"]
def get_field_default(field_name):
    """
    获取字段的默认值
    :param field_name: 字段名称
    :return: 对应的默认值
    """
    return FIELD_DEFAULTS.get(field_name, "")

# 字段描述
FIELD_DESCS = FIELD_CONF["field_desc"]
def get_field_desc(field_name):
    """
    获取字段的描述信息
    :param field_name: 字段名称
    :return: 对应的描述信息
    """
    return FIELD_DESCS.get(field_name, "")

# 组合字段列表-所有的combo都用uint来表示，
# 在dtype中使用combo免去查找列表这一步
#COMBO_LIST = FIELD_CONF["combo_list"]
# print(label)  # 输出：否
OPTIONS = FIELD_CONF["combo_options"]
def get_combo_options(combo_name):
    """
    获取组合字段的选项列表
    :param combo_name: 组合字段名称
    :return: 对应的选项列表
    """
    return OPTIONS.get(combo_name, [])

def get_step_type_label_by_idx(idx):
    """
    获取由idx指定step_type的label
    """
    # print(n)
    if 0 <= idx < len(SUPPORTED_TYPES):
        real_type = SUPPORTED_TYPES[idx]
        # print(f"real_type is {real_type}")
        return get_field_label(real_type)
    else:
        raise IndexError(f"{idx}超出SUPPORTED_TYPES范围")

def convert_value_by_dtype(value_str, dtype):
    """根据数据类型转换输入值"""
    
    if isinstance(dtype, int):
        dtype = SUPPORTED_DTYPES[dtype]
        dtype = dtype.upper().strip()
    try:
        # 处理整数类型
        if dtype in ("UINT","UINT8", "UINT16", "UINT32", "UINT64", 
                     "INT8", "INT16", "INT32", "INT64"):
            # 自动识别进制
            if value_str.lower().startswith(("0x", "0X")):
                value = int(value_str, 16)
            elif value_str.lower().startswith(("0o", "0O")):
                value = int(value_str, 8)
            elif value_str.lower().startswith(("0b", "0B")):
                value = int(value_str, 2)
            else:
                value = int(value_str)
            
            # 根据类型检查范围
            if dtype == "UINT8":
                if value < 0 or value > 0xFF:
                    raise ValueError(f"UINT8值必须在0-255之间，当前值: {value}")
                return value
            elif dtype == "UINT16":
                if value < 0 or value > 0xFFFF:
                    raise ValueError(f"UINT16值必须在0-65535之间，当前值: {value}")
                return value
            elif dtype == "UINT32":
                if value < 0 or value > 0xFFFFFFFF:
                    raise ValueError(f"UINT32值必须在0-4294967295之间，当前值: {value}")
                return value
            elif dtype == "UINT64":
                if value < 0:
                    raise ValueError(f"UINT64值不能为负数")
                return value
            elif dtype == "INT8":
                if value < -128 or value > 127:
                    raise ValueError(f"INT8值必须在-128-127之间，当前值: {value}")
                return value
            elif dtype == "INT16":
                if value < -32768 or value > 32767:
                    raise ValueError(f"INT16值必须在-32768-32767之间，当前值: {value}")
                return value
            elif dtype == "INT32":
                return value  # Python int通常为32/64位，无需额外检查
            elif dtype == "INT64":
                return value
            else:
                return value  # 默认返回整数
            
        # 处理浮点数类型
        elif dtype in ("FLOAT", "DOUBLE","REAL32", "REAL64"):
            return float(value_str)
            
        # 处理布尔类型
        elif dtype == "BOOL":
            lower_str = value_str.lower()
            if lower_str in ("true", "1", "yes", "t"):
                return True
            elif lower_str in ("false", "0", "no", "f"):
                return False
            else:
                raise ValueError(f"无效的布尔值: {value_str}")
                
        # 默认返回字符串
        else:
            return str(value_str)
            
    except ValueError as e:
        # 返回错误信息用于显示
        return str(e)


def get_combo_opt_label_value(opt):
    # if field == "step_type":
    label = get_field_label(opt["label"])
    
    return label, opt["value"]

def get_combo_label_by_value(combo_name, value):
    """
    获取组合字段的标签
    :param combo_name: 组合字段名称
    :param value: 组合字段的值
    :return: 对应的标签
    """
    options = OPTIONS.get(combo_name, [])
    for item in options:
        if item["value"] == value:
            return item["label"]
    return value
# 必需字段键列表

# REQUIRED_FIELD_KEYS = FIELD_CONF["required_fields"]
REQUIRED_FIELD_KEYS = TYPE_CONF["basic_fileds"]

# 表格列配置
CLOUMNS= VIEWS_CONF["table_columns"]

# 必需字段列表
GLINK_REQUIRED_FIELDS = [
    (key, FIELD_DEFAULTS[key], FIELD_DESCS[key])
    for key in REQUIRED_FIELD_KEYS
]

TABLE_COLUMNS = [
    (key, FIELD_LABELS[key])
    for key in CLOUMNS
]

DTYPE_MAP = {
    "str": str,
    "uint": int,
    "int": int,
    "double": float,
    "real32": float,
    "real64": float,
    "combo": int,  # 如果 combo 存储为 int
    # 其它类型可继续扩展
}

FILEDS = "fields"
LABEL = "label"
DEFAULT = "default"
DESC = "desc"
BASIC = "basic_require_fields"
DTYPE = "data_type"
COMBO = "combo"
DETAIL_STRINGS = None
IS_IGNORE = "is_ignore"


def get_dtype(field):
    # if idx < 0 | idx > len(SUPPORTED_DTYPES):
    #     raise IndexError(f"{idx}SUPPORTED_DTYPES")
    # dtype = SUPPORTED_DTYPES[idx]
    # print(f"get_dtype dtype: {field}")
    dtype = get_field_type(field)
    pyd = DTYPE_MAP.get(dtype, str)
    # print(f"get_dtype pyd: {pyd}")
    return pyd

def get_dtype_by_string(dtype_string):
    pyd = DTYPE_MAP.get(dtype_string, str)
    return pyd


def get_dtype_by_idx(idx):
    if idx < 0 | idx > len(SUPPORTED_DTYPES):
        raise IndexError(f"{idx}SUPPORTED_DTYPES")
    # dtype = SUPPORTED_DTYPES[idx]
    return DTYPE_MAP.get(SUPPORTED_DTYPES[idx], str)

def is_value_type_match(dtype, value):
    '''
    如果value是dtype代表的数据类型则返回True，否则False
    '''
    py_type = DTYPE_MAP.get(dtype, str)  # 默认为 str
    return isinstance(value, py_type)

def init_default_dict(dict, field_list):
    # print(f"StepModel init list {field_list}")
    for field in field_list:
        
        #置为初始值
        # 获取字段数据类型与默认值
        dtype = get_field_type(field)
        default = get_field_default(field)
        
        # 对于local_site、recip_site、sub_address字段，默认值也要转为字符串
        if field in ("local_site", "recip_site", "sub_address", "base_address"):
            dict[field] = str(default) if default is not None else ""
        #如果不满足对应数据类型置为空
        elif is_value_type_match(dtype, default):
            dict[field] = default
        else:
            dict[field] = None
        print(f"StepModel init field {field} default {default}, dtype: {dtype} type: {type(dict[field])}")


with open(TEMPLATE_PATH, encoding="utf-8") as f:
    template = json.load(f)

class StepModel():
    PLACEHOLDER_FIELDS = ("time", "period", "local_site", "recip_site", "sub_address", "base_address", "address")

    def __init__(self):
        #保留基础流程步字段
        self.step_type = 0
        self.base_step_data = {}
        self.type_step_data = {}
        self.expand_step_data = {}
        self.protocol_data = {}
        self.placeholder_state = {field: True for field in self.PLACEHOLDER_FIELDS}
        # 全局保存local_site、recip_site、sub_address的原始输入字符串（如"0x11"）
        self.raw_input_strings = {
            "local_site": None,
            "recip_site": None,
            "sub_address": None,
            "base_address": None,
            "address": None
        }
        base_field_list = BASIC_TYPE_FIELDS
        type_field_list = get_step_type_field_list(n=self.step_type)
        init_default_dict(self.base_step_data, base_field_list)
        init_default_dict(self.type_step_data, type_field_list)

    def _set_placeholder_state(self, field, value):
        if field not in self.placeholder_state:
            return
        if value is None:
            self.placeholder_state[field] = True
        elif isinstance(value, str):
            self.placeholder_state[field] = (value.strip() == "")
        else:
            self.placeholder_state[field] = False


        
    def get_value(self, field, default):
        """获取字段的数值（用于内部处理和导出）
        对于local_site、recip_site、sub_address字段，如果是字符串，会转换为数值
        """
        value = self.base_step_data.get(field, None)
        if value is not None:
            if field in self.placeholder_state and self.placeholder_state[field]:
                return default
            # 如果是这三个字段且值是字符串，转换为数值
            if field in ("local_site", "recip_site", "sub_address", "base_address", "address") and isinstance(value, str):
                return self._parse_string_to_int(value)
            return value
        value = self.type_step_data.get(field, None)
        if value is not None:
            if field in self.placeholder_state and self.placeholder_state[field]:
                return default
            # 如果是这三个字段且值是字符串，转换为数值
            if field in ("local_site", "recip_site", "sub_address", "base_address", "address") and isinstance(value, str):
                return self._parse_string_to_int(value)
            return value
        value = self.expand_step_data.get(field, None)
        if value is not None:
            return value
        return default
    
    def _parse_string_to_int(self, value_str):
        """将字符串（可能是16进制格式如"0x15"）转换为整数"""
        if not value_str:
            return 0
        try:
            value_str = str(value_str).strip().lower()
            if value_str.startswith('0x'):
                return int(value_str, 16)
            else:
                return int(value_str)
        except (ValueError, TypeError):
            return 0
    
    def get_display_value(self, field, default):
        """获取字段的显示值（对于local_site、recip_site、sub_address，返回原始输入字符串）"""
        if field in self.placeholder_state and self.placeholder_state[field]:
            return ""
        # 对于local_site、recip_site、sub_address字段，优先返回原始输入字符串
        if field in ("local_site", "recip_site", "sub_address", "base_address", "address"):
            raw_input = self.raw_input_strings.get(field)
            if raw_input is not None:
                return raw_input
        
        # 其他字段使用get_value的逻辑
        return self.get_value(field, default)
    
    def set_raw_input_string(self, field, raw_string):
        """设置字段的原始输入字符串（全局保存）"""
        if field in ("local_site", "recip_site", "sub_address", "base_address", "address"):
            self.placeholder_state[field] = not bool(raw_string)
            self.raw_input_strings[field] = raw_string if raw_string else None
    
    def get_raw_input_string(self, field):
        """获取字段的原始输入字符串"""
        return self.raw_input_strings.get(field)
    
    def get_union_data(self):
        """假设只有一个union_data"""
        for field in self.type_step_data:
            if get_field_type(field) == 'union':
                return self.type_step_data[field]
        return None

    def get_name(self):
        return self.base_step_data['name']
    
    def set_name(self, text):
        self.base_step_data['name'] = text
    
    def get_step_type(self):
        return self.step_type
    
    def get_base_step_data(self):
        return self.base_step_data
    
    def get_type_step_data(self):
        return self.type_step_data
    
    def get_expand_step_data(self):
        return self.expand_step_data
    
    def get_step_type_label(self, step_type):
        return get_field_label(SUPPORTED_TYPES[step_type])
    
    def set_step_type(self, step_type):
        print(f"set_step_type before {self.step_type} to {step_type}")
        if step_type != self.step_type and step_type is not None:
            self.type_step_data.clear()
        if step_type is not None:
            self.step_type = step_type
        

    def add_extension(self, key, value):
        """添加扩展数据"""
        self.expand_step_data[key] = value

    def del_extension(self, key):
        self.expand_step_data.pop(key, None)

    def get_extension_item(self, key):
        return self.expand_step_data.get(key, None)
    
    def update_base_data(self, step_data):
        print(f"update_base_data: stype: {int(step_data.get(STYPE, 0))}")
        self.set_step_type(int(step_data.get(STYPE, 0)))
        
        return self.update_step_data(self.base_step_data, 
                                     step_data, BASIC_TYPE_FIELDS)
    
    def update_type_data(self, step_type, step_data):
        print(f"StepModel.update_type_data before update: {self.step_type}")
        self.set_step_type((step_type))
        print(f"StepModel.update_type_data step_type: {step_type}")
        field_list = get_step_type_field_list(n=self.step_type)
        return self.update_step_data(self.type_step_data, 
                                     step_data, field_list)
    
    def update_expand_data(self, step_data):
        self.expand_step_data = step_data

    def update_step_data(self, step_dict, step_data, field_list=[]):
        #检测所有字段都有
        for field in field_list:
            dtype = get_field_type(field)
            if step_data is not None:
                value = step_data.get(field, None)
            else:
                value = None
            if dtype == "union":
                # print(f"filed: {field} value {value} is match type {dtype}")
                step_dict[field] = value
                self._set_placeholder_state(field, value)
            elif field in ("local_site", "recip_site", "sub_address", "base_address"):
                # 对于这些字段，保留原始值（可能是16进制字符串）
                if value is not None:
                    # 确保保存为字符串格式（即使输入是数字也要转为字符串）
                    if isinstance(value, str):
                        step_dict[field] = value
                        # 同时保存到全局原始输入字符串
                        if hasattr(self, 'raw_input_strings'):
                            self.raw_input_strings[field] = value
                        print(f"update_step_data: {field} 保存字符串值 '{value}' (类型: {type(value).__name__})")
                        self._set_placeholder_state(field, value)
                    else:
                        # 如果是数字，转为字符串（但无法保留16进制格式，这是旧数据的限制）
                        step_dict[field] = str(value)
                        # 如果原始输入字符串不存在，使用转换后的字符串
                        if hasattr(self, 'raw_input_strings') and field not in self.raw_input_strings:
                            self.raw_input_strings[field] = step_dict[field]
                        print(f"update_step_data: {field} 值 {value} 是数字，转为字符串 '{step_dict[field]}'（旧数据，无法保留16进制格式）")
                        self._set_placeholder_state(field, step_dict[field])
                else:
                    # 如果值为None，不设置（保持原有值）
                    print(f"update_step_data: {field} 值为None，保持原有值")
                    self._set_placeholder_state(field, None)
            elif value is not None and is_value_type_match(dtype, value):
                # print(f"filed: {field} value {value} is match type {dtype}")
                step_dict[field] = value
                self._set_placeholder_state(field, value)
            else:
                print(f"filed: {field} value {value} {type(value)} is not match type {dtype}")
                if value is None:
                    self._set_placeholder_state(field, None)

    def set_protocol_data(self, data):
        """设置协议模板数据"""
        self.protocol_data = data
    
    def get_protocol_data(self):
        """获取协议模板数据"""
        return self.protocol_data


    

if __name__ == "__main__":
    # 测试输出
    step_model = StepModel()
    print(get_dtype("time"))
    print(TYPE_CONF["basic_fileds"])

    # print(step_model.get_base_step_data().get("name"))
    # print("字段类型:", FIELD_TYPES)
    # print("字段标签:", FIELD_LABELS)
    # # print("必需字段:", GLINK_REQUIRED_FIELDS)
    # print("表格列配置:", TABLE_COLUMNS)
    # print("字段默认值:", FIELD_DEFAULTS)
    # print("字段描述:", FIELD_DESCS)
