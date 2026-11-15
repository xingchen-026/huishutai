"""workflow_member 表数据操作。"""

from __future__ import annotations

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import WorkflowMember
from sqldb.result import DBResult


class WorkflowMemberCRUD(BaseCRUD[WorkflowMember]):
    def __init__(self) -> None:
        super().__init__(WorkflowMember)

    @db_error_handler
    def list_by_workflow(self, workflow_id: int) -> DBResult:
        return self.get_list({"workflow_id": workflow_id}, order_by=("created_at",))

    @db_error_handler
    def get_by_workflow_user(self, workflow_id: int, user_id: int) -> DBResult:
        return self.get(workflow_id=workflow_id, user_id=user_id)

    @db_error_handler
    def delete_by_workflow_user(self, workflow_id: int, user_id: int) -> DBResult:
        deleted, _ = self._queryset().filter(workflow_id=workflow_id, user_id=user_id).delete()
        if not deleted:
            return DBResult(DBStatus.NOT_FOUND, "成员不存在")
        return DBResult(DBStatus.SUCCESS, "删除成功")
