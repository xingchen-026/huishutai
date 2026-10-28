"""MinIO 对象存储访问层。

只做对象存储读写（bucket、上传、删除、签名 URL、健康检查），
不包含文件归属、大小/扩展名校验等业务逻辑（在 api.file_service）。
"""

from __future__ import annotations

import logging
import threading
from datetime import timedelta
from typing import BinaryIO

from django.conf import settings
from minio import Minio

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client: Minio | None = None
_public_client: Minio | None = None
_bucket_ready = False


class StorageError(Exception):
    """对象存储访问失败。"""


def _split_endpoint(endpoint: str, default_secure: bool) -> tuple[str, bool]:
    endpoint = (endpoint or "").strip().rstrip("/")
    if endpoint.startswith("https://"):
        return endpoint[len("https://"):], True
    if endpoint.startswith("http://"):
        return endpoint[len("http://"):], False
    return endpoint, default_secure


def _build_client(endpoint: str, default_secure: bool) -> Minio:
    host, secure = _split_endpoint(endpoint, default_secure)
    return Minio(
        host,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=secure,
    )


def get_client() -> Minio:
    """内网操作用的客户端（上传/删除/建桶）。"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = _build_client(settings.MINIO_ENDPOINT, settings.MINIO_SECURE)
    return _client


def get_public_client() -> Minio:
    """生成浏览器可访问签名 URL 的客户端（只做签名，不发请求）。"""
    global _public_client
    if _public_client is None:
        with _lock:
            if _public_client is None:
                _public_client = _build_client(
                    settings.MINIO_PUBLIC_ENDPOINT, settings.MINIO_PUBLIC_SECURE
                )
    return _public_client


def ensure_bucket() -> None:
    """幂等创建 bucket（进程内只检查一次）。"""
    global _bucket_ready
    if _bucket_ready:
        return

    client = get_client()
    with _lock:
        if _bucket_ready:
            return
        try:
            if not client.bucket_exists(settings.MINIO_BUCKET):
                client.make_bucket(settings.MINIO_BUCKET)
                logger.info("已创建 MinIO bucket：%s", settings.MINIO_BUCKET)
        except Exception as exc:
            logger.exception("初始化 MinIO bucket 失败")
            raise StorageError("初始化对象存储失败，请检查 MinIO 配置") from exc
        _bucket_ready = True


def upload_object(
    object_key: str,
    data: BinaryIO,
    length: int,
    content_type: str = "",
) -> None:
    """上传对象；失败抛 StorageError。"""
    ensure_bucket()
    try:
        get_client().put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_key,
            data=data,
            length=length,
            content_type=content_type or "application/octet-stream",
        )
    except Exception as exc:
        logger.exception("上传对象失败：%s", object_key)
        raise StorageError("文件写入对象存储失败") from exc


def delete_object(object_key: str) -> None:
    """删除对象（回滚用，失败只记日志不抛异常）。"""
    try:
        get_client().remove_object(settings.MINIO_BUCKET, object_key)
    except Exception:
        logger.exception("删除对象失败：%s", object_key)


def presigned_get_url(object_key: str, expires_seconds: int | None = None) -> str:
    """生成浏览器可直接打开的临时下载 URL（默认 1 小时，最长 7 天）。"""
    expiry = int(expires_seconds or settings.MINIO_PRESIGN_EXPIRY)
    expiry = max(60, min(expiry, 7 * 24 * 3600))
    try:
        return get_public_client().presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=expiry),
        )
    except Exception as exc:
        logger.exception("生成对象签名 URL 失败：%s", object_key)
        raise StorageError("生成文件访问链接失败") from exc


def health_check() -> dict:
    """连接自检，返回端点与 bucket 列表。"""
    try:
        buckets = [bucket.name for bucket in get_client().list_buckets()]
    except Exception as exc:
        logger.exception("MinIO 健康检查失败")
        raise StorageError("对象存储连接失败") from exc
    return {
        "endpoint": settings.MINIO_ENDPOINT,
        "bucket": settings.MINIO_BUCKET,
        "buckets": buckets,
    }