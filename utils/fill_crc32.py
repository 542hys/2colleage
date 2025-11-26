import zlib

def fill_crc32(step_data):
    # 假设step_data为dict，拼接除CRC32外所有字段内容
    crc_fields = [k for k in step_data if k != "CRC32校验"]
    crc_input = "".join(str(step_data[k]) for k in crc_fields)
    crc_val = zlib.crc32(crc_input.encode("utf-8")) & 0xFFFFFFFF
    step_data["CRC32校验"] = f"0x{crc_val:08X}"