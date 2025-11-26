# 配置文件，集中管理所有字符串常量
#后续有补充加在这里
GLINK_TEST_HEADER = b'GLINK_TEST_DATA\x00'  # Glink测试数据文件头标识
DEFAULT_TIMEOUT_KEY = "default_timeout"      # 全局参数：默认超时时间的键名
MAX_RETRIES_KEY = "max_retries"              # 全局参数：最大重试次数的键名
ENVIRONMENT_KEY = "environment"              # 全局参数：环境字符串的键名
STEP_NAME_KEY = "name"                       # 步骤参数：步骤名称的键名
STEP_TIME_KEY = "time"                       # 步骤参数：步骤时间的键名
STEP_PROTOCOL_KEY = "protocol"               # 步骤参数：协议类型的键名
STEP_DATA_FORMAT_KEY = "data_format"         # 步骤参数：数据格式的键名
STEP_DATA_CONTENT_KEY = "data_content"       # 步骤参数：数据内容的键名
STEP_EXPECT_KEY = "expect"                   # 步骤参数：预期响应的键名
HEX_FORMAT = "Hex"                           # 数据格式：十六进制
BINARY_FORMAT = "Binary"                     # 数据格式：二进制 