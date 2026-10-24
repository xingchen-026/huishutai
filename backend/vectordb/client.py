"""Milvus 连接管理。

- 懒加载单例：第一次用到时才建连接，Milvus 暂时不可用不影响 Django 启动；
- 多 gunicorn worker 各自持有一个客户端（进程级单例）；
- 统一从 settings.MILVUS_* 读取配置，不在代码里写死地址。
"""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from pymilvus import MilvusClient

from vectordb.enums import VDBStatus
from vectordb.result import VDBResult

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    """获取进程内复用的 Milvus 客户端（懒加载 + 双重检查锁）。"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = MilvusClient(
                    uri=settings.MILVUS_URI,
                    token=settings.MILVUS_TOKEN or "",
                    db_name=settings.MILVUS_DB_NAME,
                    timeout=settings.MILVUS_TIMEOUT,
                )
                logger.info("Milvus 客户端已初始化：%s", settings.MILVUS_URI)
    return _client


def close_client() -> None:
    """关闭连接（测试/进程退出时使用）。"""
    global _client
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                logger.exception("关闭 Milvus 客户端失败")
            _client = None


def check_health() -> VDBResult:
    """健康检查：能列出集合即视为连接正常。"""
    try:
        collections = get_client().list_collections()
    except Exception:
        logger.exception("Milvus 健康检查失败")
        return VDBResult(VDBStatus.CONNECTION_ERR, "向量数据库连接失败")
    return VDBResult(
        VDBStatus.SUCCESS,
        "向量数据库连接正常",
        {"uri": settings.MILVUS_URI, "collections": list(collections)},
    )