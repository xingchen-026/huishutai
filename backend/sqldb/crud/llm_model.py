"""llm_model 表的数据操作，不含业务逻辑。"""

from __future__ import annotations

from django.db import transaction

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import LLMModel
from sqldb.result import DBResult


class LLMModelCRUD(BaseCRUD[LLMModel]):
    """大模型 CRUD。"""

    def __init__(self) -> None:
        super().__init__(LLMModel)

    @db_error_handler
    def list_by_provider(self, provider_id: int) -> DBResult:
        return self.get_list({"provider_id": provider_id}, order_by=("category", "model_id"))

    @db_error_handler
    def list_by_user(
        self,
        user_id: int,
        *,
        category: str | None = None,
        provider_id: int | None = None,
    ) -> DBResult:
        filters: dict = {"provider__user_id": user_id}
        if category:
            filters["category"] = category
        if provider_id:
            filters["provider_id"] = provider_id
        return self.get_list(filters, order_by=("category", "model_id"))

    @db_error_handler
    def get_by_provider_model(self, provider_id: int, model_id: str) -> DBResult:
        return self.get(provider_id=provider_id, model_id=model_id)

    @db_error_handler
    def delete_auto_not_in(self, provider_id: int, keep_model_ids: list[str]) -> DBResult:
        """删除该供应商下已不在最新列表中的自动拉取模型（保留 manual 模型）。"""
        with transaction.atomic():
            deleted, _ = (
                self._queryset()
                .filter(provider_id=provider_id, source="auto")
                .exclude(model_id__in=keep_model_ids)
                .delete()
            )
        return DBResult(DBStatus.SUCCESS, "清理完成", {"deleted": deleted})