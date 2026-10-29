"""user 表的数据操作（增删改查），不含任何业务逻辑。

继承 BaseCRUD 后即可使用：
    增：create(username=..., password=<已哈希值>)
    删：delete(pk)
    改：update(pk, **fields)
    查：get / get_by_pk / get_list / exists / count
另外提供按用户名的查询：get_by_username。

密码哈希、密码校验、登录/注册流程都属于业务，由 user 应用完成。
"""

from __future__ import annotations

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.models import User
from sqldb.result import DBResult


class UserCRUD(BaseCRUD[User]):
    """user 表 CRUD。"""

    def __init__(self) -> None:
        super().__init__(User)

    @db_error_handler
    def get_by_username(self, username: str) -> DBResult:
        """按用户名查询用户，NOT_FOUND 表示不存在。"""
        return self.get(username=username)
