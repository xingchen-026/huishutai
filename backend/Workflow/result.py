"""Workflow 统一返回结果与状态码（结构对齐 DBResult / LLMResult）。"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class WFStatus(IntEnum):
    SUCCESS = 0
    PARAM_ERR = 5001
    NOT_FOUND = 5002
    FORBIDDEN = 5003
    CONFLICT = 5004
    NODE_ERROR = 5005
    NODE_LOAD_ERROR = 5006
    EXEC_ERROR = 5007
    UNKNOWN_ERR = 5999


@dataclass
class WFResult:
    code: WFStatus
    message: str
    data: Any | None = None

    @property
    def success(self) -> bool:
        return self.code == WFStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {"code": int(self.code), "message": self.message, "data": self.data}
