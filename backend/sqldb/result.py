from dataclasses import asdict, dataclass
from typing import Any, Optional

from sqldb.enums import DBStatus


@dataclass
class DBResult:
    code: DBStatus
    message: str
    data: Optional[Any] = None

    def to_dict(self):
        return asdict(self)
