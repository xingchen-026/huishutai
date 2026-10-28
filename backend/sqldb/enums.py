from enum import IntEnum

class DBStatus(IntEnum):
    SUCCESS = 0             # 成功
    NOT_FOUND = 1001        # 数据不存在
    DUPLICATE_ERR = 1002    # 唯一键冲突
    PARAM_ERR = 1003        # 参数/业务校验不通过
    SERVICE_ERR = 1004      # 外部服务异常（MinIO/Milvus 等）
    UNKNOWN_ERR = 9999      # 数据库异常