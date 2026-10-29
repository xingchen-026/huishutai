"""API Key 加解密与脱敏。

Fernet 对称加密：数据库只存密文；接口只返回掩码，不返回明文。
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    configured = (settings.LLMAPI_ENCRYPTION_KEY or "").strip()
    if configured:
        raw_key = configured.encode("utf-8")
    else:
        digest = hashlib.sha256(f"llmapi-key:{settings.SECRET_KEY}".encode("utf-8")).digest()
        raw_key = base64.urlsafe_b64encode(digest)
        logger.warning(
            "LLMAPI_ENCRYPTION_KEY 未配置，当前使用 SECRET_KEY 派生密钥；"
            "生产环境请显式配置，否则更换 SECRET_KEY 会导致已存 Key 无法解密"
        )
    try:
        _fernet = Fernet(raw_key)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "LLMAPI_ENCRYPTION_KEY 格式无效，应为 Fernet.generate_key() 生成的 base64 字符串"
        ) from exc
    return _fernet


def encrypt_api_key(raw_key: str) -> str:
    value = (raw_key or "").strip()
    if not value:
        raise ValueError("API Key 不能为空")
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_api_key(token: str) -> str:
    try:
        return _get_fernet().decrypt((token or "").encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("API Key 解密失败（加密密钥可能已更换），请重新录入") from exc


def mask_api_key(raw_key: str) -> str:
    value = (raw_key or "").strip()
    if len(value) <= 8:
        return "****"
    return f"{value[:3]}****{value[-4:]}"
