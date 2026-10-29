"""向量集合通用操作：建集合 / 写入 / 删除 / 检索 / 查询。

本层只负责向量数据库读写，返回 VDBResult：
- 不做 embedding（向量由调用方提供）；
- 不做文本切分、prompt、RAG 流程（属于 RAG/LLMapi 业务层）；
- 不依赖 Django ORM。
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, ParamSpec

from pymilvus import DataType, MilvusClient
from pymilvus.exceptions import MilvusException

from vectordb.client import get_client
from vectordb.enums import VDBStatus
from vectordb.result import VDBResult
from vectordb.schemas import CollectionSchema

logger = logging.getLogger(__name__)

P = ParamSpec("P")


def vdb_error_handler(func: Callable[P, VDBResult]) -> Callable[P, VDBResult]:
    """把 pymilvus 异常翻译为 VDBResult，调用方不需要 try/except。"""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> VDBResult:
        try:
            return func(*args, **kwargs)
        except MilvusException as exc:
            logger.warning("Milvus 操作失败：%s", func.__qualname__, exc_info=True)
            message = getattr(exc, "message", None) or str(exc)
            return VDBResult(VDBStatus.UNKNOWN_ERR, f"向量数据库操作失败：{message}")
        except Exception:
            logger.exception("Milvus 访问异常：%s", func.__qualname__)
            return VDBResult(VDBStatus.CONNECTION_ERR, "向量数据库连接失败")

    return wrapper


class VectorCollection:
    """一个 Milvus 集合的数据操作对象。"""

    def __init__(self, schema: CollectionSchema) -> None:
        self.schema = schema

    # ---------- 内部工具 ----------
    def _client(self) -> MilvusClient:
        return get_client()

    def _missing(self, client: MilvusClient) -> VDBResult | None:
        if client.has_collection(collection_name=self.schema.name):
            return None
        return VDBResult(
            VDBStatus.NOT_FOUND,
            f"集合不存在：{self.schema.name}，请先执行 python manage.py init_vectordb",
        )

    # ==================== 建集合 ====================
    @vdb_error_handler
    def ensure(self) -> VDBResult:
        """幂等创建集合 + 向量索引（已存在则跳过）。"""
        client = self._client()
        if client.has_collection(collection_name=self.schema.name):
            return VDBResult(
                VDBStatus.SUCCESS,
                "集合已存在",
                {"name": self.schema.name, "created": False},
            )

        schema = MilvusClient.create_schema(
            auto_id=self.schema.auto_id,
            enable_dynamic_field=False,
        )
        schema.add_field(
            field_name=self.schema.primary_field,
            datatype=DataType.INT64,
            is_primary=True,
        )
        schema.add_field(
            field_name=self.schema.vector_field,
            datatype=DataType.FLOAT_VECTOR,
            dim=self.schema.dim,
        )
        for field in self.schema.scalar_fields:
            schema.add_field(
                field_name=field.name,
                datatype=DataType.VARCHAR,
                max_length=field.max_length,
            )

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name=self.schema.vector_field,
            index_type=self.schema.index_type,
            metric_type=self.schema.metric_type,
        )
        client.create_collection(
            collection_name=self.schema.name,
            schema=schema,
            index_params=index_params,
        )
        return VDBResult(
            VDBStatus.SUCCESS,
            "集合创建成功",
            {"name": self.schema.name, "dim": self.schema.dim, "created": True},
        )

    # ==================== 增 ====================
    @vdb_error_handler
    def insert(self, rows: list[dict[str, Any]], *, upsert: bool = False) -> VDBResult:
        """写入向量数据。

        rows 每行必须包含 vector 字段（list[float]）和 schemas.py 声明的标量字段；
        auto_id=True 时不要传主键。返回生成的 id 列表。
        """
        if not rows:
            return VDBResult(VDBStatus.PARAM_ERR, "写入数据为空")
        if upsert and self.schema.auto_id:
            return VDBResult(
                VDBStatus.PARAM_ERR,
                "当前集合使用自动主键，无法 upsert；请改用 insert，或把 schemas.py 的 auto_id 改为 False",
            )

        client = self._client()
        missing = self._missing(client)
        if missing:
            return missing

        if upsert:
            result = client.upsert(collection_name=self.schema.name, data=rows)
            count = result.get("upsert_count", len(rows))
            message = "更新完成"
        else:
            result = client.insert(collection_name=self.schema.name, data=rows)
            count = result.get("insert_count", len(rows))
            message = "写入完成"
        return VDBResult(
            VDBStatus.SUCCESS,
            message,
            {"count": count, "ids": result.get("ids", [])},
        )

    # ==================== 删 ====================
    @vdb_error_handler
    def delete(
        self,
        *,
        ids: list[int] | None = None,
        filter_expr: str | None = None,
    ) -> VDBResult:
        """按主键或过滤条件删除（例如按 doc_id 删除整篇文档的切片）。"""
        if not ids and not filter_expr:
            return VDBResult(VDBStatus.PARAM_ERR, "删除条件不能为空")

        client = self._client()
        missing = self._missing(client)
        if missing:
            return missing

        if ids:
            result = client.delete(collection_name=self.schema.name, ids=ids)
        else:
            result = client.delete(collection_name=self.schema.name, filter=filter_expr)
        return VDBResult(
            VDBStatus.SUCCESS,
            "删除完成",
            {"count": result.get("delete_count", 0)},
        )

    # ==================== 查 ====================
    @vdb_error_handler
    def search(
        self,
        vector: list[float],
        *,
        top_k: int = 5,
        filter_expr: str | None = None,
        output_fields: list[str] | None = None,
    ) -> VDBResult:
        """向量相似度检索，返回 [{"id", "distance", "entity"}, ...]。"""
        if not vector:
            return VDBResult(VDBStatus.PARAM_ERR, "查询向量不能为空")
        if len(vector) != self.schema.dim:
            return VDBResult(
                VDBStatus.PARAM_ERR,
                f"向量维度不匹配：集合要求 {self.schema.dim}，实际 {len(vector)}",
            )

        client = self._client()
        missing = self._missing(client)
        if missing:
            return missing

        results = client.search(
            collection_name=self.schema.name,
            data=[vector],
            anns_field=self.schema.vector_field,
            limit=top_k,
            filter=filter_expr or "",
            output_fields=output_fields or [],
            search_params={"metric_type": self.schema.metric_type},
        )
        hits = results[0] if results else []
        rows = [
            {
                "id": hit.get("id"),
                "distance": hit.get("distance"),
                "entity": hit.get("entity", {}),
            }
            for hit in hits
        ]
        return VDBResult(VDBStatus.SUCCESS, f"检索完成，命中 {len(rows)} 条", rows)

    @vdb_error_handler
    def get_by_ids(
        self,
        ids: list[int],
        *,
        output_fields: list[str] | None = None,
    ) -> VDBResult:
        """按主键批量取数据。"""
        if not ids:
            return VDBResult(VDBStatus.PARAM_ERR, "ids 不能为空")

        client = self._client()
        missing = self._missing(client)
        if missing:
            return missing

        rows = client.get(
            collection_name=self.schema.name,
            ids=ids,
            output_fields=output_fields or [],
        )
        return VDBResult(VDBStatus.SUCCESS, f"查询完成，共 {len(rows)} 条", rows)

    @vdb_error_handler
    def query(
        self,
        filter_expr: str,
        *,
        output_fields: list[str] | None = None,
        limit: int = 100,
    ) -> VDBResult:
        """按标量字段条件查询（不过向量相似度）。"""
        if not filter_expr:
            return VDBResult(VDBStatus.PARAM_ERR, "查询条件不能为空")

        client = self._client()
        missing = self._missing(client)
        if missing:
            return missing

        rows = client.query(
            collection_name=self.schema.name,
            filter=filter_expr,
            output_fields=output_fields or [],
            limit=limit,
        )
        return VDBResult(VDBStatus.SUCCESS, f"查询完成，共 {len(rows)} 条", rows)
