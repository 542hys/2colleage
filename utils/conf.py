import json
from pathlib import Path



def get_config_strings():
    CONFIG_PATH = Path(__file__).parent / "config_strings.json"
    with open(CONFIG_PATH, encoding="utf-8") as f:
        STRINGS = json.load(f)
    return STRINGS

STRINGS = get_config_strings()
DIALOG_STRINGS = STRINGS["dialog"]
# LIST_STRINGS = STRINGS["list_view"]
STEP_LIST_STRINGS = STRINGS["step_list_view"]

TITEL_STRING = STEP_LIST_STRINGS["group_title"] #标题
UP_STRING = STEP_LIST_STRINGS["button_text"]["up"]
EDIT_STRING = STEP_LIST_STRINGS["button_text"]["edit"]
DOWN_STRING = STEP_LIST_STRINGS["button_text"]["down"]
DELETE_STRING = STEP_LIST_STRINGS["button_text"]["remove"]
ADD_STRING = STEP_LIST_STRINGS["button_text"]["add"]


if __name__ == "__main__":

    
    print(DIALOG_STRINGS["window_titles"]["custom_step_config"])