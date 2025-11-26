import re
from typing import Iterable, List, Sequence

HEX_TOKEN_SPLIT = re.compile(r"[,\s]+")


def _normalize_token(token) -> str:
    """Normalize various hex representations (handles 全角×/０x 等)."""
    if token is None:
        return ""
    text = str(token).strip()
    if not text:
        return ""
    replacements = (
        ("×", "x"),
        ("Ｘ", "x"),
        ("０x", "0x"),
        ("０X", "0x"),
        ("０", "0"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _token_to_int(token: str):
    text = _normalize_token(token)
    if not text:
        return None
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        # 如果包含 x 但没有 0x 前缀，尝试补齐
        if "x" in text.lower():
            hex_part = text.lower().replace("x", "")
            return int(f"0x{hex_part}", 16)
        # 默认尝试 16 进制，否则十进制
        try:
            return int(text, 16)
        except ValueError:
            return int(float(text))
    except ValueError:
        return None


def normalize_data_region_value(raw_value) -> str:
    """将 data_region（list/dict/str）统一转换为以空格分隔的16进制字符串。"""
    if raw_value is None:
        return ""
    if isinstance(raw_value, str):
        return raw_value.strip()
    if isinstance(raw_value, (list, tuple)):
        hex_values = []
        for item in raw_value:
            if not isinstance(item, dict):
                continue
            value = item.get("value", 0)
            data_type = item.get("data_type", 0)
            int_value = _token_to_int(value)
            if int_value is None:
                int_value = 0
            if data_type == 0:  # UINT8
                hex_values.append(f"0x{int_value & 0xFF:02X}")
            elif data_type == 1:  # UINT16
                hex_values.append(f"0x{int_value & 0xFFFF:04X}")
            else:
                hex_values.append(f"0x{int_value:X}")
        return " ".join(hex_values)
    return str(raw_value)


def _split_tokens(data_value: str) -> List[str]:
    if not data_value:
        return []
    tokens = HEX_TOKEN_SPLIT.split(str(data_value).strip())
    return [tok for tok in tokens if tok]


def parse_hex_string_to_bytes(data_value: str) -> List[int]:
    """解析字符串为字节列表（超出0xFF的值会拆成大端字节序列）。"""
    bytes_list: List[int] = []
    for token in _split_tokens(data_value):
        intval = _token_to_int(token)
        if intval is None:
            continue
        intval &= 0xFFFFFFFFFFFFFFFF
        # 拆分为字节，保持高字节在前
        temp = []
        if intval == 0:
            temp = [0]
        else:
            while intval > 0:
                temp.append(intval & 0xFF)
                intval >>= 8
            temp.reverse()
        bytes_list.extend(temp)
    return bytes_list


def parse_hex_string_to_words(data_value: str) -> List[int]:
    """解析为16位数据列表，小于16位的值自动补齐。"""
    words: List[int] = []
    for token in _split_tokens(data_value):
        intval = _token_to_int(token)
        if intval is None:
            continue
        words.append(intval & 0xFFFF)
    return words


def format_bytes_to_hex_string(byte_list: Sequence[int]) -> str:
    return " ".join(f"0x{b & 0xFF:02X}" for b in byte_list)


def format_words_to_hex_string(words: Sequence[int]) -> str:
    return " ".join(f"0x{w & 0xFFFF:04X}" for w in words)


def apply_serial_escape_sequence(byte_list: Sequence[int]) -> List[int]:
    """当出现连续0x5A 0xFE时在前面插入0x00。"""
    if not byte_list:
        return []
    result: List[int] = []
    i = 0
    length = len(byte_list)
    while i < length:
        current = byte_list[i] & 0xFF
        next_byte = byte_list[i + 1] & 0xFF if i + 1 < length else None
        if current == 0x5A and next_byte == 0xFE:
            result.append(0x00)
        result.append(current)
        i += 1
    return result


def crc16_ccitt(data: Iterable[int], initial: int = 0xFFFF) -> int:
    """CRC-16/CCITT (XModem)"""
    crc = initial & 0xFFFF
    for value in data:
        crc ^= (value & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def calc_serial_standard_metrics(data_value: str) -> dict:
    raw_bytes = parse_hex_string_to_bytes(data_value)
    processed_bytes = apply_serial_escape_sequence(raw_bytes)
    checksum = sum(processed_bytes) & 0xFF
    length = len(processed_bytes) & 0xFF
    return {
        "data_bytes": processed_bytes,
        "data_hex_items": [f"0x{b:02X}" for b in processed_bytes],
        "overrides": {
            "数据区": format_bytes_to_hex_string(processed_bytes),
            "数据区累加和": f"0x{checksum:02X}",
            "数据区长度": f"0x{length:02X}",
        },
    }


def calc_serial_extended_metrics(data_value: str) -> dict:
    raw_bytes = parse_hex_string_to_bytes(data_value)
    processed_bytes = apply_serial_escape_sequence(raw_bytes)
    crc = crc16_ccitt(processed_bytes)
    length = len(processed_bytes) & 0xFFFF
    return {
        "data_bytes": processed_bytes,
        "data_hex_items": [f"0x{b:02X}" for b in processed_bytes],
        "overrides": {
            "数据区": format_bytes_to_hex_string(processed_bytes),
            "数据区crc校验和低8位": f"0x{crc & 0xFF:02X}",
            "数据区crc校验和高8位": f"0x{(crc >> 8) & 0xFF:02X}",
            "数据区长度低8位": f"0x{length & 0xFF:02X}",
            "数据区长度高8位": f"0x{(length >> 8) & 0xFF:02X}",
        },
    }


def calc_crc_tail_metrics(data_value: str) -> dict:
    words = parse_hex_string_to_words(data_value)
    data_bytes: List[int] = []
    for w in words:
        data_bytes.extend([(w >> 8) & 0xFF, w & 0xFF])
    crc = crc16_ccitt(data_bytes)
    return {
        "data_bytes": data_bytes,
        "data_hex_items": [f"0x{w & 0xFFFF:04X}" for w in words],
        "overrides": {
            "数据区": format_words_to_hex_string(words),
            "数据区crc校验和": f"0x{crc:04X}",
        },
    }


def ensure_hex_prefix(value: str, width: int = 2) -> str:
    """将任意数字/字符串格式化成带0x前缀的字符串。"""
    intval = _token_to_int(value)
    intval = 0 if intval is None else intval
    return f"0x{intval & ((1 << (width * 4)) - 1):0{width}X}"

