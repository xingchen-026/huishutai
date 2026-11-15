"""workflow_edge 表数据操作。"""

from __future__ import annotations

from django.db.models import Q

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import WorkflowEdge
from sqldb.result import DBResult


class WorkflowEdgeCRUD(BaseCRUD[WorkflowEdge]):
    def __init__(self) -> None:
        super().__init__(WorkflowEdge)

    @db_error_handler
    def list_by_workflow(self, workflow_id: int) -> DBResult:
        return self.get_list({"workflow_id": workflow_id}, order_by=("created_at",))

    @db_error_handler
    def delete_by_workflow(self, workflow_id: int) -> DBResult:
        self._queryset().filter(workflow_id=workflow_id).delete()
        return DBResult(DBStatus.SUCCESS, "删除成功")

    @db_error_handler
    def delete_by_node_key(self, workflow_id: int, node_key: str) -> DBResult:
        self._queryset().filter(
            Q(workflow_id=workflow_id),
            Q(source_key=node_key) | Q(target_key=node_key),
        ).delete()
        return DBResult(DBStatus.SUCCESS, "删除成功")
