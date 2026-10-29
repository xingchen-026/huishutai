from enum import IntEnum


class VDBStatus(IntEnum):
    """向量数据库操作状态码（结构上与 sqldb.DBStatus 对应）。"""

    SUCCESS = 0
    NOT_FOUND = 2001  # 集合/数据不存在
    PARAM_ERR = 2002  # 参数不合法（空数据、维度不匹配等）
    CONNECTION_ERR = 2003  # 连接/访问失败
    UNKNOWN_ERR = 2999  # 其它数据库异常
