"""workflow_event 表数据操作。"""

from __future__ import annotations

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import WorkflowEvent
from sqldb.result import DBResult


class WorkflowEventCRUD(BaseCRUD[WorkflowEvent]):
    def __init__(self) -> None:
        super().__init__(WorkflowEvent)

    @db_error_handler
    def list_after(self, workflow_id: int, after_id: int = 0, limit: int = 100) -> DBResult:
        qs = (
            self._queryset()
            .filter(workflow_id=workflow_id, id__gt=max(after_id, 0))
            .order_by("id")[: max(1, min(limit, 200))]
        )
        return DBResult(DBStatus.SUCCESS, "查询成功", list(qs))

    @db_error_handler
    def latest_id(self, workflow_id: int) -> DBResult:
        row = self._queryset().filter(workflow_id=workflow_id).order_by("-id").first()
        return DBResult(DBStatus.SUCCESS, "查询成功", row.id if row else 0)
