"""知识库集合：RAG 业务通过这个对象操作 Milvus。"""

from vectordb.crud.base import VectorCollection
from vectordb.schemas import KNOWLEDGE_SCHEMA

knowledge_collection = VectorCollection(KNOWLEDGE_SCHEMA)