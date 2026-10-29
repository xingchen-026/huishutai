"""user_info 表的数据操作（增删改查），不含任何业务逻辑。

继承 BaseCRUD 后即可使用：
    增：create(user=..., email=..., phone=..., gender=...)
    删：delete(pk)
    改：update(pk, **fields)
    查：get / get_by_pk / get_list / exists / count
另外提供：get_by_user_id、update_by_user_id。

本层不检查邮箱/手机号格式（属于业务）；
外键/唯一性冲突由数据库约束兜底，返回 DUPLICATE_ERR。
"""

from __future__ import annotations

from typing import Any

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.enums import DBStatus
from sqldb.models import UserInfo
from sqldb.result import DBResult


class UserInfoCRUD(BaseCRUD[UserInfo]):
    """user_info 表 CRUD。"""

    def __init__(self) -> None:
        super().__init__(UserInfo)

    @db_error_handler
    def get_by_user_id(self, user_id: int) -> DBResult:
        """按用户 ID 查询资料（OneToOne）。"""
        return self.get(user_id=user_id)

    @db_error_handler
    def update_by_user_id(self, user_id: int, **fields: Any) -> DBResult:
        """按用户 ID 更新资料，data 为更新后的 UserInfo。"""
        if not fields:
            return DBResult(DBStatus.UNKNOWN_ERR, "没有需要更新的字段")

        result = self.get_by_user_id(user_id)
        if result.code != DBStatus.SUCCESS:
            return result

        return self.update(result.data.pk, **fields)
