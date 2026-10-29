"""测试公共工具：用户、供应商、模型构造与 HTTP 调用辅助。"""
from __future__ import annotations

import json

from django.contrib.auth.hashers import make_password

from LLMapi import crypto
from LLMapi.model_meta import build_param_spec
from sqldb.models import LLMProviderConfig, LLMModel, User
from user.auth import issue_token


def make_user(username: str = "alice", password: str = "secret123") -> User:
    return User.objects.create(username=username, password=make_password(password))


def bearer(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {issue_token(user.pk)}"}


def reset_crypto_cache() -> None:
    """LLMapi.crypto 会缓存 Fernet 实例；override_settings 后需要重置。"""
    crypto._fernet = None


def make_provider(
    user: User,
    *,
    template_code: str = "openai",
    name: str = "默认供应商",
    protocol: str = "openai",
    base_url: str = "https://api.example.com/v1",
    api_key: str = "sk-test-abcdef123456",
    enabled: bool = True,
    **extra,
) -> LLMProviderConfig:
    encrypted = crypto.encrypt_api_key(api_key) if api_key else ""
    masked = crypto.mask_api_key(api_key) if api_key else ""
    return LLMProviderConfig.objects.create(
        user=user,
        template_code=template_code,
        name=name,
        protocol=protocol,
        base_url=base_url,
        api_key_encrypted=encrypted,
        api_key_masked=masked,
        enabled=enabled,
        **extra,
    )


def make_model(
    provider: LLMProviderConfig,
    *,
    model_id: str = "gpt-4o",
    category: str = "chat",
    display_name: str = "",
    param_spec: list | None = None,
    source: str = "auto",
    enabled: bool = True,
    **extra,
) -> LLMModel:
    return LLMModel.objects.create(
        provider=provider,
        model_id=model_id,
        display_name=display_name or model_id,
        category=category,
        param_spec=param_spec
        if param_spec is not None
        else build_param_spec(provider.protocol, category, model_id),
        source=source,
        enabled=enabled,
        **extra,
    )


def api(client, method: str, path: str, user: User | None = None, payload=None):
    """以 JSON 方式调用 DRF 接口，返回 Django test client 的响应。"""
    kwargs = {}
    if user is not None:
        kwargs.update(bearer(user))
    body = json.dumps(payload) if payload is not None else None
    return getattr(client, method)(
        path, data=body, content_type="application/json", **kwargs
    )
