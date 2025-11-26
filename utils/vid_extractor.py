import json
from pathlib import Path
from typing import Iterable, List, Set, Union, Any


def extract_vids_from_json(json_path: Union[str, Path], target_vids: Iterable[str]) -> List[str]:
    """
    从 json 文件中提取指定的 vid 列表。

    参数:
        json_path: json 文件路径。
        target_vids: 需要匹配的 vid 列表或集合。

    返回:
        按照在 json 中出现顺序的 vid 列表，且仅包含目标 vid。
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"未找到 json 文件: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    targets: Set[str] = set(target_vids)
    found: List[str] = []

    def _visit(node: Any):
        if isinstance(node, dict):
            vid_value = node.get("vid")
            if isinstance(vid_value, str) and vid_value in targets:
                found.append(vid_value)
                targets.remove(vid_value)
                if not targets:
                    return
            for value in node.values():
                if not targets:
                    break
                _visit(value)
        elif isinstance(node, list):
            for item in node:
                if not targets:
                    break
                _visit(item)

    _visit(data)
    return found


def remove_vids_from_json(
    json_path: Union[str, Path],
    output_path: Union[str, Path],
    target_vids: Iterable[str],
) -> Any:
    """
    将 json 文件中包含指定 vid 的节点剔除，并输出新的 json 内容。

    参数:
        json_path: 原始 json 文件路径。
        output_path: 剔除后的 json 输出路径。
        target_vids: 待剔除 vid 列表或集合。

    返回:
        剔除后的 json 结构（同时写入 output_path）。
    """
    source = Path(json_path)
    if not source.exists():
        raise FileNotFoundError(f"未找到 json 文件: {source}")

    with source.open("r", encoding="utf-8") as f:
        data = json.load(f)

    targets: Set[str] = set(target_vids)
    _REMOVE = object()

    def _clean(node: Any) -> Any:
        if isinstance(node, dict):
            vid_value = node.get("vid")
            if isinstance(vid_value, str) and vid_value in targets:
                return _REMOVE
            cleaned_dict = {}
            for key, value in node.items():
                cleaned_value = _clean(value)
                if cleaned_value is _REMOVE:
                    continue
                cleaned_dict[key] = cleaned_value
            return cleaned_dict

        if isinstance(node, list):
            cleaned_list = []
            for item in node:
                cleaned_item = _clean(item)
                if cleaned_item is _REMOVE:
                    continue
                cleaned_list.append(cleaned_item)
            return cleaned_list

        return node

    cleaned_data = _clean(data)

    output = Path(output_path)
    with output.open("w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    return cleaned_data


if __name__ == "__main__":
    # 示例：将结果打印成所需格式
    demo_vids = [
        "hykvaGYvRD0", "p5H1ZEBAM-g", "Uklt4zVVtS0", "aiGo8a5R010",
        "zg4w0oOPd3Q", "glvWBeYJQIU", "53Zfh-HJSbM", "737QhBtLBR0",
        "FKwMrMI4wJs", "dTPMn8cmdwI", "9TyVapaAr68", "mauLDkS8jcg",
        "vHtmMPRi-L4", "2I_FHvEVzXo", "1JrrafGWV4U", "CLRT2j9Cvqc",
        "1fJzq-HBqIg", "N0qGxAgf6S0", "N8Vo9Rcpy18", "gOwFMoC8xaE",
        "Y6JOB6BL6Uc", "oBwq9-t7jh8", "pDRfz5Pkkbo", "tM_0hA0IZ5Q",
        "64VXXx4H1xA", "WiF30l2F_yU", "7PighNvbs9c", "DqAGlzm88xI",
        "FBZz0TMbdpY", "8Yu0PVJmRmM", "Gj46KvzQ5fE",
    ]

    # 替换成实际 json 文件路径
    json_file = Path("video_list.json")
    try:
        # 1. 打印被找到的 vid，便于核对
        result = extract_vids_from_json(json_file, demo_vids)
        print("匹配结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # 2. 剔除对应 vid 并输出新 json
        cleaned_file = json_file.with_suffix(".cleaned.json")
        remove_vids_from_json(json_file, cleaned_file, demo_vids)
        print(f"\n已生成剔除后的文件: {cleaned_file}")
    except FileNotFoundError as exc:
        print(exc)

