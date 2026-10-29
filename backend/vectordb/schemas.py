"""向量集合结构定义。

对应 sqldb/models.py 的角色：这里只描述“集合长什么样”
（集合名、向量维度、度量方式、标量字段），
不包含 embedding、文本切分、检索策略等业务逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ScalarField:
    """标量字段（用于过滤、返回原文/元数据）。"""

    name: str
    max_length: int = 512


@dataclass(frozen=True)
class CollectionSchema:
    """一个 Milvus 集合的结构描述。"""

    name: str
    dim: int
    metric_type: str = "COSINE"
    primary_field: str = "id"
    vector_field: str = "vector"
    auto_id: bool = True
    index_type: str = "AUTOINDEX"
    scalar_fields: tuple[ScalarField, ...] = ()
    description: str = ""


KNOWLEDGE_SCHEMA = CollectionSchema(
    name=settings.MILVUS_KNOWLEDGE_COLLECTION,
    dim=settings.MILVUS_KNOWLEDGE_DIM,
    metric_type=settings.MILVUS_KNOWLEDGE_METRIC_TYPE,
    scalar_fields=(
        ScalarField("content", 8192),  # 切片原文
        ScalarField("source", 512),  # 来源（文件名/URL）
        ScalarField("doc_id", 128),  # 文档标识，便于按文档删除/过滤
    ),
    description="RAG 知识库切片集合",
)
