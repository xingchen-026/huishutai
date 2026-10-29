"""文件上传业务：校验、SHA-256、写入 MinIO、记录 PG 元数据。

分层：
    api.file_views.file_upload（HTTP）
        -> api.file_service.save_uploaded_file（业务编排）
            -> filestorage（MinIO 对象存储）
            -> sqldb.crud.file_crud（只写 PG 元数据）
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

import filestorage
from sqldb.crud import file_crud
from sqldb.enums import DBStatus
from sqldb.result import DBResult

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1024 * 1024  # 1MB
_MB = 1024 * 1024
_MAX_NAME_LENGTH = 255


def _fail(message: str, code: DBStatus = DBStatus.PARAM_ERR) -> DBResult:
    return DBResult(code=code, message=message)


def _safe_original_name(raw: str) -> str:
    """只保留文件名本身，去掉客户端可能带上的目录部分。"""
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name[:_MAX_NAME_LENGTH]


def save_uploaded_file(uploaded_file: UploadedFile, user) -> DBResult:
    """保存上传文件并记录元数据；成功时 data 为文件信息 dict（含签名 URL）。"""
    original_name = _safe_original_name(uploaded_file.name)
    if not original_name:
        return _fail("文件名不能为空")

    if uploaded_file.size is None or uploaded_file.size <= 0:
        return _fail("不能上传空文件")
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        return _fail(f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // _MB}MB）")

    suffix = Path(original_name).suffix.lower()
    if suffix not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        return _fail(f"不支持的文件类型：{suffix or '无扩展名'}")

    content_type = (uploaded_file.content_type or "")[:128]

    # 对象键：uploads/{user_id}/{YYYY}/{MM}/{uuid}{ext}
    today = timezone.localdate()
    object_key = f"uploads/{user.pk}/{today:%Y}/{today:%m}/{uuid.uuid4().hex}{suffix}"

    # 1) 流式计算 SHA-256，读完复位文件指针
    digest = hashlib.sha256()
    total = 0
    try:
        for chunk in uploaded_file.chunks(chunk_size=_CHUNK_SIZE):
            digest.update(chunk)
            total += len(chunk)
        uploaded_file.seek(0)
    except Exception:
        logger.exception("读取上传文件失败：%s", original_name)
        return _fail("读取上传文件失败，请稍后重试", DBStatus.UNKNOWN_ERR)

    # 2) 写入 MinIO
    try:
        filestorage.upload_object(
            object_key=object_key,
            data=uploaded_file,
            length=total,
            content_type=content_type,
        )
    except filestorage.StorageError as exc:
        return _fail(str(exc), DBStatus.SERVICE_ERR)

    # 3) 生成浏览器可访问的签名 URL；失败则删掉已上传对象
    try:
        url = filestorage.presigned_get_url(object_key)
    except filestorage.StorageError:
        filestorage.delete_object(object_key)
        return _fail("生成文件访问链接失败，请稍后重试", DBStatus.SERVICE_ERR)

    # 4) 写 PG 元数据；失败则删掉已上传对象，避免孤儿文件
    result = file_crud.create(
        user=user,
        original_name=original_name,
        bucket=settings.MINIO_BUCKET,
        object_key=object_key,
        file_hash=digest.hexdigest(),
        file_size=total,
        content_type=content_type,
    )
    if result.code != DBStatus.SUCCESS:
        filestorage.delete_object(object_key)
        return DBResult(result.code, "文件信息保存失败，请稍后重试")

    saved = result.data
    return DBResult(
        DBStatus.SUCCESS,
        "上传成功",
        {
            "id": saved.pk,
            "user_id": saved.user_id,
            "original_name": saved.original_name,
            "bucket": saved.bucket,
            "object_key": saved.object_key,
            "file_hash": saved.file_hash,
            "file_size": saved.file_size,
            "content_type": saved.content_type,
            "created_at": saved.created_at.isoformat(),
            "url": url,
            "url_expires_in": settings.MINIO_PRESIGN_EXPIRY,
        },
    )
