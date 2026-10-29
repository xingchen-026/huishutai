"""通用表操作基类。

本层只负责数据库读写：增（create）、删（delete）、改（update）、查（get…）。
不包含任何业务逻辑，也不感知 HTTP / request / response。
所有操作统一返回 DBResult，说明本次操作结果。
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Generic, ParamSpec, TypeVar

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Model, QuerySet

from sqldb.enums import DBStatus
from sqldb.result import DBResult

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=Model)
P = ParamSpec("p")


def db_error_handler(func: Callable[P, DBResult]) -> Callable[P, DBResult]:
    """把数据库异常转换成 DBResult，调用方无需关心 ORM 异常。

    写操作内部都包了 transaction.atomic：即使被上层事务包裹，
    异常也能在 savepoint 内回滚，不会污染上层事务。
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> DBResult:
        try:
            return func(*args, **kwargs)
        except IntegrityError:
            logger.warning("数据库完整性约束冲突：%s", func.__qualname__, exc_info=True)
            return DBResult(DBStatus.DUPLICATE_ERR, "数据已存在或违反唯一性/外键约束")
        except DatabaseError:
            logger.warning("数据库操作失败：%s", func.__qualname__)
            return DBResult(DBStatus.UNKNOWN_ERR, "数据库操作失败")

    return wrapper


class BaseCRUD(Generic[M]):
    """单表增删改查基类。

    基类不 import 任何具体模型，由子类构造时注入，例如：
        class UserCRUD(BaseCRUD[User]):
            def __init__(self):
                super().__init__(User)
    """

    def __init__(self, model: type[M]) -> None:
        self.model = model

    def _queryset(self) -> QuerySet[M]:
        return self.model.objects.all()

    # ==================== 查 ====================
    @db_error_handler
    def get(self, **filters: Any) -> DBResult:
        """按条件查询单条记录。

        - 未命中：NOT_FOUND
        - 命中多条：UNKNOWN_ERR（调用方应缩小查询条件）
        """
        objs = list(self._queryset().filter(**filters)[:2])
        if not objs:
            return DBResult(DBStatus.NOT_FOUND, "数据不存在")
        if len(objs) > 1:
            return DBResult(DBStatus.UNKNOWN_ERR, "查询结果不唯一，请补充查询条件")
        return DBResult(DBStatus.SUCCESS, "查询成功", objs[0])

    @db_error_handler
    def get_by_pk(self, pk: Any) -> DBResult:
        """按主键查询单条记录。"""
        return self.get(pk=pk)

    @db_error_handler
    def get_list(
        self,
        filters: dict[str, Any] | None = None,
        *,
        order_by: tuple[str, ...] = (),
        limit: int | None = None,
        offset: int = 0,
    ) -> DBResult:
        """条件列表查询，排序与分页下推到数据库执行。"""
        qs = self._queryset()
        if filters:
            qs = qs.filter(**filters)
        if order_by:
            qs = qs.order_by(*order_by)

        start = max(offset, 0)
        if limit is None:
            if start:
                qs = qs[start:]
        else:
            qs = qs[start : start + max(limit, 0)]
        return DBResult(DBStatus.SUCCESS, "查询成功", list(qs))

    @db_error_handler
    def exists(self, **filters: Any) -> DBResult:
        """判断是否存在符合条件的记录，data 为 bool。"""
        return DBResult(DBStatus.SUCCESS, "查询成功", self._queryset().filter(**filters).exists())

    @db_error_handler
    def count(self, **filters: Any) -> DBResult:
        """统计符合条件的记录数，data 为 int。"""
        return DBResult(DBStatus.SUCCESS, "统计成功", self._queryset().filter(**filters).count())

    # ==================== 增 ====================
    @db_error_handler
    def create(self, **fields: Any) -> DBResult:
        """新增一条记录，data 为新建的模型实例。

        注意：敏感字段（如 password）由业务层处理（哈希）后再传入。
        """
        with transaction.atomic():
            obj = self.model.objects.create(**fields)
        return DBResult(DBStatus.SUCCESS, "创建成功", obj)

    # ==================== 改 ====================
    @db_error_handler
    def update(self, pk: Any, **fields: Any) -> DBResult:
        """按主键局部更新（QuerySet.update，不触发 save()/信号）。"""
        if not fields:
            raise ValueError("update() 至少需要一个待更新字段")
        with transaction.atomic():
            updated = self._queryset().filter(pk=pk).update(**fields)
        if not updated:
            return DBResult(DBStatus.NOT_FOUND, "数据不存在，更新失败")
        return DBResult(DBStatus.SUCCESS, "更新成功", self._queryset().filter(pk=pk).first())

    # ==================== 删 ====================
    @db_error_handler
    def delete(self, pk: Any) -> DBResult:
        """按主键删除；级联删除由模型字段的 on_delete 决定。"""
        with transaction.atomic():
            deleted, _ = self._queryset().filter(pk=pk).delete()
        if not deleted:
            return DBResult(DBStatus.NOT_FOUND, "数据不存在，删除失败")
        return DBResult(DBStatus.SUCCESS, "删除成功")
