"""LLMapi 统一返回结果与状态码（结构对齐 DBResult / VDBResult）。"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class LLMStatus(IntEnum):
    SUCCESS = 0
    PARAM_ERR = 4001
    NOT_FOUND = 4002
    PROVIDER_AUTH_ERR = 4003
    PROVIDER_UNREACHABLE = 4004
    PROVIDER_API_ERR = 4005
    MODEL_UNSUPPORTED = 4006
    DB_ERR = 4007
    UNKNOWN_ERR = 4999


@dataclass
class LLMResult:
    code: LLMStatus
    message: str
    data: Any | None = None

    @property
    def success(self) -> bool:
        return self.code == LLMStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {"code": int(self.code), "message": self.message, "data": self.data}
    