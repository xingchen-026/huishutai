"""向量数据库操作统一返回结果。"""

from dataclasses import dataclass
from typing import Any

from vectordb.enums import VDBStatus


@dataclass
class VDBResult:
    """说明本次向量库操作的结果。"""

    code: VDBStatus
    message: str
    data: Any | None = None

    @property
    def success(self) -> bool:
        return self.code == VDBStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {"code": int(self.code), "message": self.message, "data": self.data}