"""vectordb.crud —— 向量数据库操作统一入口。

其它应用只从这里获取操作对象，例如：

    from vectordb.crud import knowledge_collection
"""

from vectordb.crud.base import VectorCollection
from vectordb.crud.knowledge import knowledge_collection

__all__ = ["VectorCollection", "knowledge_collection"]
