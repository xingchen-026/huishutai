"""llm_provider_config 表的数据操作，不含业务逻辑。"""

from __future__ import annotations

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.models import LLMProviderConfig
from sqldb.result import DBResult


class LLMProviderConfigCRUD(BaseCRUD[LLMProviderConfig]):
    """大模型供应商配置 CRUD。"""

    def __init__(self) -> None:
        super().__init__(LLMProviderConfig)

    @db_error_handler
    def list_by_user(self, user_id: int, *, enabled_only: bool = False) -> DBResult:
        filters = {"user_id": user_id}
        if enabled_only:
            filters["enabled"] = True
        return self.get_list(filters, order_by=("-created_at",))

    @db_error_handler
    def get_by_user(self, user_id: int, pk: int) -> DBResult:
        """按主键 + 归属用户查询，避免越权。"""
        return self.get(pk=pk, user_id=user_id)
