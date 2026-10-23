"""sqldb.crud —— 数据库操作统一入口。

其它应用只从这里获取数据操作对象，不要直接写 ORM：

    from sqldb.crud import user_crud, user_info_crud

新增一张表时：
1. 在 sqldb/models.py 中定义模型；
2. 在本目录新增 <table>.py，继承 BaseCRUD 并注入模型；
3. 在这里导出 <table>_crud 实例。
"""

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.crud.user import UserCRUD
from sqldb.crud.user_info import UserInfoCRUD

# 无状态对象，进程内复用；测试时也可直接 UserCRUD() 新建。
user_crud = UserCRUD()
user_info_crud = UserInfoCRUD()

__all__ = [
    "BaseCRUD",
    "db_error_handler",
    "UserCRUD",
    "UserInfoCRUD",
    "user_crud",
    "user_info_crud",
]