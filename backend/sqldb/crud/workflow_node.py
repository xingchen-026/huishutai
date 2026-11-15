"""workflow_node 表数据操作（含乐观锁更新）。"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import WorkflowNode
from sqldb.result import DBResult


class WorkflowNodeCRUD(BaseCRUD[WorkflowNode]):
    def __init__(self) -> None:
        super().__init__(WorkflowNode)

    @db_error_handler
    def list_by_workflow(self, workflow_id: int) -> DBResult:
        return self.get_list({"workflow_id": workflow_id}, order_by=("created_at",))

    @db_error_handler
    def get_by_key(self, workflow_id: int, key: str) -> DBResult:
        return self.get(workflow_id=workflow_id, key=key)

    @db_error_handler
    def update_if_version(
        self, workflow_id: int, key: str, expected_version: int, **fields
    ) -> DBResult:
        """按版本条件更新；版本不一致返回 CONFLICT，不存在返回 NOT_FOUND。"""
        if not fields:
            raise ValueError("update_if_version() 至少需要一个待更新字段")
        fields["version"] = expected_version + 1
        fields["updated_at"] = timezone.now()
        with transaction.atomic():
            updated = (
                self._queryset()
                .filter(workflow_id=workflow_id, key=key, version=expected_version)
                .update(**fields)
            )
        if updated:
            return DBResult(
                DBStatus.SUCCESS,
                "更新成功",
                self._queryset().filter(workflow_id=workflow_id, key=key).first(),
            )
        if self._queryset().filter(workflow_id=workflow_id, key=key).exists():
            return DBResult(DBStatus.CONFLICT, "节点已被其他人修改，请刷新后重试")
        return DBResult(DBStatus.NOT_FOUND, "节点不存在")

    @db_error_handler
    def delete_by_workflow(self, workflow_id: int) -> DBResult:
        self._queryset().filter(workflow_id=workflow_id).delete()
        return DBResult(DBStatus.SUCCESS, "删除成功")
