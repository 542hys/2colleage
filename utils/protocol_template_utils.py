import re
import struct
from typing import Iterable, List, Sequence, Any, Dict

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


# 支持的数据类型
SUPPORTED_DTYPES = ["UINT8", "UINT16", "UINT32", "INT8", "INT16", "INT32", "FLOAT32", "FLOAT64"]

# 需要进行16位字交换的小端数据类型
LITTLE_ENDIAN_WORD_SWAP_DTYPES = {"UINT32", "FLOAT32", "REAL32", "FLOAT64", "REAL64", "DOUBLE"}


def to_int(val: Any) -> int:
    """将值转换为整数，支持十六进制字符串和浮点数"""
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        s_val = val.strip().lower()
        if s_val.startswith("0x"):
            try:
                return int(s_val, 16)
            except ValueError:
                pass
        try:
            return int(float(s_val))
        except ValueError:
            pass
    return 0


def value_to_bytes(val: Any, dtype_str: str, big_endian: bool = True) -> bytes:
    """将值转换为字节数组，考虑端序"""
    u = dtype_str.upper()
    endian_prefix = '>' if big_endian else '<'
    try:
        if u in ("UINT8", "INT8"):
            return bytes([val & 0xFF])
        elif u in ("UINT16", "INT16"):
            val = val & 0xFFFF
            if big_endian:
                return bytes([val >> 8, val & 0xFF])
            else:
                return bytes([val & 0xFF, val >> 8])
        elif u in ("UINT32", "INT32"):
            val = val & 0xFFFFFFFF
            if big_endian:
                return bytes([val >> 24, (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF])
            else:
                return bytes([val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF, val >> 24])
        elif u in ("FLOAT32", "REAL32", "FLOAT", "REAL"):
            if isinstance(val, str):
                s_val = val.strip().lower()
                if s_val.startswith("0x"):
                    try:
                        bits = int(s_val, 16) & 0xFFFFFFFF
                        return bits.to_bytes(4, byteorder='big' if big_endian else 'little')
                    except ValueError:
                        pass
            fv = float(val) if val not in (None, "") else 0.0
            return struct.pack(endian_prefix + 'f', fv)
        elif u in ("FLOAT64", "REAL64", "DOUBLE"):
            if isinstance(val, str):
                s_val = val.strip().lower()
                if s_val.startswith("0x"):
                    try:
                        bits = int(s_val, 16) & 0xFFFFFFFFFFFFFFFF
                        return bits.to_bytes(8, byteorder='big' if big_endian else 'little')
                    except ValueError:
                        pass
            fv = float(val) if val not in (None, "") else 0.0
            return struct.pack(endian_prefix + 'd', fv)
        elif u in ("BOOL", "BOOLEAN"):
            return bytes([1 if val else 0])
        else:
            # 默认按16位处理
            val = val & 0xFFFF
            if big_endian:
                return bytes([val >> 8, val & 0xFF])
            else:
                return bytes([val & 0xFF, val >> 8])
    except Exception:
        return bytes([0])


def swap_16bit_words_for_little_endian(b: bytes) -> bytes:
    """对小端字节序的16位字进行交换"""
    if len(b) <= 2:
        return b
    result = bytearray()
    for i in range(0, len(b), 2):
        if i + 1 < len(b):
            result.extend([b[i+1], b[i]])
        else:
            result.append(b[i])
    return bytes(result)


def calculate_total_bytes(union_list: List[Dict], display_big_endian: bool = True, is_little_endian: bool = False) -> int:
    """计算数据区的总字节数，与file_controller.py中的逻辑一致"""
    total_bytes = 0
    
    for item in union_list:
        if not isinstance(item, dict):
            continue
            
        dtype = item.get('data_type')
        value = item.get('value')
        
        # 获取原始数据类型，用于特殊处理字符串
        original_dtype_str = None
        if isinstance(dtype, str):
            original_dtype_str = dtype.strip().upper()
        
        # 标记是否为未知数据类型
        is_unknown_type = False
        
        # 获取标准化的数据类型
        dtype_str = None
        if isinstance(dtype, int) and 0 <= dtype < len(SUPPORTED_DTYPES):
            dtype_str = SUPPORTED_DTYPES[dtype]
        elif isinstance(dtype, str):
            dtype_str = dtype.strip().upper()
            # 确保数据类型在SUPPORTED_DTYPES中
            if dtype_str not in SUPPORTED_DTYPES:
                # 尝试映射常见的别名
                type_mappings = {
                    "INT8": "INT8",
                    "UINT8": "UINT8",
                    "INT16": "INT16",
                    "UINT16": "UINT16",
                    "INT32": "INT32",
                    "UINT32": "UINT32",
                    "FLOAT32": "FLOAT32",
                    "FLOAT": "FLOAT32",
                    "REAL32": "FLOAT32",
                    "REAL": "FLOAT32",
                    "FLOAT64": "FLOAT64",
                    "DOUBLE": "FLOAT64",
                    "REAL64": "FLOAT64",
                    "BOOL": "UINT8",
                    "BOOLEAN": "UINT8"
                }
                dtype_str = type_mappings.get(dtype_str)
                if not dtype_str:
                    is_unknown_type = True
                    dtype_str = "UINT16"  # 未知类型默认使用16位
        if not dtype_str:
            is_unknown_type = True
            dtype_str = "UINT16"  # 未知类型默认使用16位
            
        u = dtype_str.upper()
        try:
            # 特殊处理字符串类型
            if original_dtype_str in ("STR", "STRING"):
                # 字符串类型使用UTF-8编码的长度
                val = value if value is not None else ""
                total_bytes += len(str(val).encode('utf-8'))
                continue
                
            # 根据数据类型选择正确的转换方式
            if u in ("FLOAT32", "REAL32", "FLOAT", "REAL", "FLOAT64", "REAL64", "DOUBLE"):
                item_bytes = None
                if isinstance(value, str):
                    s_val = value.strip().lower()
                    if s_val.startswith("0x"):
                        hex_part = s_val[2:]
                        expected_bits = 32 if u in ("FLOAT32", "REAL32", "FLOAT", "REAL") else 64
                        expected_bytes = expected_bits // 8
                        try:
                            bits_val = int(hex_part, 16) & ((1 << expected_bits) - 1)
                            byteorder = 'big' if display_big_endian else 'little'
                            item_bytes = bits_val.to_bytes(expected_bytes, byteorder=byteorder, signed=False)
                        except ValueError:
                            item_bytes = None
                if item_bytes is None:
                    try:
                        converted_value = float(value) if value is not None else 0.0
                    except (TypeError, ValueError):
                        converted_value = 0.0
                    endian_prefix_local = '>' if display_big_endian else '<'
                    fmt = 'f' if u in ("FLOAT32", "REAL32", "FLOAT", "REAL") else 'd'
                    item_bytes = struct.pack(endian_prefix_local + fmt, converted_value)
                    
            else:
                # 整数类型使用to_int转换
                iv = to_int(value)
                item_bytes = value_to_bytes(iv, dtype_str, display_big_endian)
                
            # 处理小端字节序的16位字交换
            if is_little_endian and u in LITTLE_ENDIAN_WORD_SWAP_DTYPES:
                item_bytes = swap_16bit_words_for_little_endian(item_bytes)
                
            total_bytes += len(item_bytes)
            
        except Exception as err:
            # 处理出错时使用默认值0
            total_bytes += 1
    
    return total_bytes


def ensure_hex_prefix(value: str, width: int = 2) -> str:
    """将任意数字/字符串格式化成带0x前缀的字符串。"""
    intval = _token_to_int(value)
    intval = 0 if intval is None else intval
    return f"0x{intval & ((1 << (width * 4)) - 1):0{width}X}"

