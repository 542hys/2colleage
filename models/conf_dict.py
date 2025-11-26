from pathlib import Path
import json

# 获取当前文件所在目录
base_dir = Path(__file__).parent
# 如果直接用./会根据工作目录来寻找文件
# 拼接 JSON 文件路径
json_path = base_dir / "model_config_new.json"

with open(json_path, encoding="utf-8") as f:
    conf = json.load(f)

fields_list = conf["fields"]
support_types_list = conf["support_types"]
table_columns_list = conf["table_columns"]
basic_require_fields_list = conf["basic_require_fields"]
type_fields_list = conf["type_fields"]


fields_dict = {field["key"]: field for field in fields_list}
type_fields_dict = {item["key"]: item for item in type_fields_list}
type_field_map = {}

basic_field_map = {}
for field_key in basic_require_fields_list:
    field_info = fields_dict.get(field_key)
    if field_info:
        basic_field_map[field_key] = field_info

type_field_map["basic_require_fields"] = {
    "fields": basic_field_map
}


for type_key in conf["support_types"]:
    type_info = type_fields_dict.get(type_key)
    if not type_info:
        continue
    field_map = {}
    for field_key in type_info.get("fields", []):
        field_info = fields_dict.get(field_key)
        if field_info:
            field_map[field_key] = field_info
    type_field_map[type_key] = {
        "label": type_info.get("label", type_key),
        "fields": field_map
    }

FILEDS = "fields"
LABEL = "label"
DEFAULT = "default"
DESC = "desc"
BASIC = "basic_require_fields"
DTYPE = "data_type"
STYPE = "step_type"
COMBO = "combo"

OPTIONS = "options"


TYPE_FIELD_MAP = type_field_map
BASIC_FILEDS = TYPE_FIELD_MAP[BASIC][FILEDS]
# 生成快速访问的字段映射
if __name__ == "__main__":
    # 使用示例：快速访问
    # 获取“glink_fileds_non_periodic”类型下“site_type”字段的全部信息
    # 测试输出
    info2 = type_field_map["basic_require_fields"]["fields"]["step_type"]
    info = type_field_map["interrupt_fileds"]["fields"]
    print(info)
    # for key in BASIC_FILEDS:
    #     field_info = BASIC_FILEDS[key]
    #     print(f"字段: {field_info[LABEL]} (key: {key})，默认值: {field_info[DEFAULT]}，说明: {field_info[DESC]}")

