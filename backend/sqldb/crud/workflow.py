"""workflow 表数据操作。"""

from __future__ import annotations

from django.db.models import Q

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import Workflow
from sqldb.result import DBResult


class WorkflowCRUD(BaseCRUD[Workflow]):
    def __init__(self) -> None:
        super().__init__(Workflow)

    @db_error_handler
    def list_for_user(self, user_id: int, *, limit: int = 100) -> DBResult:
        """我创建的 + 我被邀请协作的工作流。"""
        qs = (
            self._queryset()
            .filter(Q(owner_id=user_id) | Q(members__user_id=user_id))
            .distinct()
            .order_by("-updated_at")[: max(1, min(limit, 200))]
        )
        return DBResult(DBStatus.SUCCESS, "查询成功", list(qs))
