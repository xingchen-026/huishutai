"""LLMapi 业务层。

- 供应商模板查询；
- 用户供应商配置 CRUD（API Key 加密、脱敏返回）；
- 在线拉取模型、分类、生成参数规格并落库；
- 统一模型调用网关（chat / embeddings），调用前严格校验参数。

其它应用只通过本模块获取模型供应，不直接请求供应商。
"""

from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from sqldb.crud import llm_model_crud, llm_provider_crud
from sqldb.enums import DBStatus
from sqldb.result import DBResult

from LLMapi import crypto
from LLMapi.adapters import ProviderAccess, ProviderError, get_adapter
from LLMapi.model_meta import (
    CATEGORIES,
    CATEGORY_LABELS,
    build_param_spec,
    classify_model,
    validate_embedding_input,
    validate_messages,
    validate_params,
)
from LLMapi.result import LLMResult, LLMStatus
from LLMapi.templates import get_template, list_templates

logger = logging.getLogger(__name__)

SYNC_UNAVAILABLE = "供应商暂未配置列表，请手动输入模型名称"
SYNC_EMPTY = "供应商未返回模型列表，请手动输入模型名称"


# ==================== 通用工具 ====================
def _from_db(result: DBResult, message: str | None = None) -> LLMResult:
    if result.code == DBStatus.SUCCESS:
        return LLMResult(LLMStatus.SUCCESS, message or result.message, result.data)
    if result.code == DBStatus.NOT_FOUND:
        return LLMResult(LLMStatus.NOT_FOUND, message or result.message)
    if result.code in (DBStatus.PARAM_ERR, DBStatus.DUPLICATE_ERR):
        return LLMResult(LLMStatus.PARAM_ERR, message or result.message)
    return LLMResult(LLMStatus.DB_ERR, message or result.message)


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _as_bool(value, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


def _check_base_url(raw: str) -> tuple[str | None, str | None]:
    value = (raw or "").strip().rstrip("/")
    if not value:
        return None, "供应商地址不能为空"
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None, "供应商地址必须是 http(s) URL"
    if parsed.username or parsed.password:
        return None, "供应商地址不能包含用户名密码"
    if not settings.LLMAPI_ALLOW_PRIVATE_BASE_URL:
        host = (parsed.hostname or "").lower()
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
                return None, "不允许配置内网/本机地址"
        except ValueError:
            if host in ("localhost",) or host.endswith(".local"):
                return None, "不允许配置内网/本机地址"
    return value, None


def _provider_dict(provider, model_count: int | None = None) -> dict:
    template = get_template(provider.template_code)
    return {
        "id": provider.pk,
        "name": provider.name,
        "template_code": provider.template_code,
        "template_name": template.name if template else provider.template_code,
        "protocol": provider.protocol,
        "base_url": provider.base_url,
        "api_key_masked": provider.api_key_masked,
        "enabled": provider.enabled,
        "model_count": model_count,
        "last_synced_at": _iso(provider.last_synced_at),
        "last_sync_error": provider.last_sync_error,
        "created_at": _iso(provider.created_at),
    }


def _model_dict(model, provider) -> dict:
    return {
        "id": model.pk,
        "provider_id": model.provider_id,
        "provider_name": provider.name if provider else "",
        "template_code": provider.template_code if provider else "",
        "protocol": provider.protocol if provider else "",
        "model_id": model.model_id,
        "display_name": model.display_name or model.model_id,
        "category": model.category,
        "category_label": CATEGORY_LABELS.get(model.category, model.category),
        "param_spec": model.param_spec or [],
        "source": model.source,
        "enabled": model.enabled,
        "synced_at": _iso(model.synced_at),
        "created_at": _iso(model.created_at),
    }


def _access_from_config(provider) -> ProviderAccess:
    api_key = ""
    if provider.api_key_encrypted:
        api_key = crypto.decrypt_api_key(provider.api_key_encrypted)
    return ProviderAccess(
        protocol=provider.protocol,
        base_url=provider.base_url,
        api_key=api_key,
    )


def _sync_models(provider, fetched: list[dict]) -> int:
    """把最新模型列表同步进库；保留 manual 模型，删除消失的 auto 模型。"""
    now = timezone.now()
    keep_ids: list[str] = []
    seen: set[str] = set()
    count = 0

    with transaction.atomic():
        for item in fetched:
            model_id = str(item.get("model_id") or "").strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            keep_ids.append(model_id)

            category = classify_model(provider.protocol, model_id, item.get("raw") or {})
            values = {
                "display_name": str(item.get("display_name") or model_id)[:200],
                "category": category,
                "param_spec": build_param_spec(provider.protocol, category, model_id),
                "source": "auto",
                "raw": item.get("raw") or {},
                "synced_at": now,
                "enabled": True,
            }
            existing = llm_model_crud.get_by_provider_model(provider.pk, model_id)
            if existing.code == DBStatus.SUCCESS:
                llm_model_crud.update(existing.data.pk, **values)
            elif existing.code == DBStatus.NOT_FOUND:
                created = llm_model_crud.create(
                    provider=provider, model_id=model_id, **values
                )
                if created.code != DBStatus.SUCCESS:
                    continue
            else:
                continue
            count += 1

        if keep_ids:
            llm_model_crud.delete_auto_not_in(provider.pk, keep_ids)

    return count


# ==================== 模板 ====================
def list_provider_templates() -> LLMResult:
    return LLMResult(
        LLMStatus.SUCCESS,
        "ok",
        {
            "templates": list_templates(),
            "categories": [
                {"code": code, "label": CATEGORY_LABELS.get(code, code)}
                for code in CATEGORIES
            ],
        },
    )


# ==================== 供应商配置 ====================
def create_provider(user, data: dict | None = None) -> LLMResult:
    data = data or {}
    template = get_template(str(data.get("template_code") or ""))
    if template is None:
        return LLMResult(LLMStatus.PARAM_ERR, "供应商模板不存在")

    name = str(data.get("name") or template.name).strip()[:100]
    if not name:
        return LLMResult(LLMStatus.PARAM_ERR, "配置名称不能为空")

    base_url, error = _check_base_url(
        str(data.get("base_url") or template.default_base_url)
    )
    if error:
        return LLMResult(LLMStatus.PARAM_ERR, error)

    api_key = str(data.get("api_key") or "").strip()
    if template.requires_api_key and not api_key:
        return LLMResult(LLMStatus.PARAM_ERR, "请填写该供应商的 API Key")

    access = ProviderAccess(template.protocol, base_url, api_key)
    fetched: list[dict] = []
    sync_status = "unavailable"
    sync_message = SYNC_UNAVAILABLE
    try:
        fetched = get_adapter(template.protocol).list_models(access)
        if fetched:
            sync_status = "ok"
            sync_message = "模型列表已同步"
        else:
            sync_message = SYNC_EMPTY
    except ProviderError as exc:
        if exc.code == LLMStatus.PROVIDER_AUTH_ERR:
            return LLMResult(LLMStatus.PROVIDER_AUTH_ERR, "API Key 无效或无权限，配置未保存")
        logger.warning("拉取模型列表失败：%s", exc.message)

    try:
        ciphertext = crypto.encrypt_api_key(api_key) if api_key else ""
        masked = crypto.mask_api_key(api_key) if api_key else ""
    except ValueError as exc:
        return LLMResult(LLMStatus.PARAM_ERR, str(exc))

    created = llm_provider_crud.create(
        user=user,
        template_code=template.code,
        name=name,
        protocol=template.protocol,
        base_url=base_url,
        api_key_encrypted=ciphertext,
        api_key_masked=masked,
        last_sync_error="" if fetched else sync_message[:500],
    )
    if created.code != DBStatus.SUCCESS:
        return _from_db(
            created,
            "配置名称已存在" if created.code == DBStatus.DUPLICATE_ERR else None,
        )

    provider = created.data
    count = 0
    if fetched:
        count = _sync_models(provider, fetched)
        provider = llm_provider_crud.get_by_pk(provider.pk).data or provider
        message = "配置已保存，模型列表已同步"
    else:
        message = f"配置已保存，{sync_message}"

    return LLMResult(
        LLMStatus.SUCCESS,
        message,
        {
            "provider": _provider_dict(provider, count),
            "model_sync": {"status": sync_status, "count": count, "message": sync_message},
        },
    )


def list_providers(user) -> LLMResult:
    result = llm_provider_crud.list_by_user(user.pk)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result)
    providers = []
    for provider in result.data:
        count_result = llm_model_crud.count(provider_id=provider.pk)
        count = count_result.data if count_result.code == DBStatus.SUCCESS else 0
        providers.append(_provider_dict(provider, count))
    return LLMResult(
        LLMStatus.SUCCESS, "ok", {"total": len(providers), "providers": providers}
    )


def get_provider(user, provider_id: int) -> LLMResult:
    result = llm_provider_crud.get_by_user(user.pk, provider_id)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result, "供应商配置不存在")
    provider = result.data
    count_result = llm_model_crud.count(provider_id=provider.pk)
    count = count_result.data if count_result.code == DBStatus.SUCCESS else 0
    return LLMResult(LLMStatus.SUCCESS, "ok", {"provider": _provider_dict(provider, count)})


def update_provider(user, provider_id: int, data: dict | None = None) -> LLMResult:
    data = data or {}
    existing = llm_provider_crud.get_by_user(user.pk, provider_id)
    if existing.code != DBStatus.SUCCESS:
        return _from_db(existing, "供应商配置不存在")
    provider = existing.data

    fields: dict = {}
    if "name" in data:
        name = str(data.get("name") or "").strip()[:100]
        if not name:
            return LLMResult(LLMStatus.PARAM_ERR, "配置名称不能为空")
        fields["name"] = name
    if "enabled" in data:
        fields["enabled"] = _as_bool(data.get("enabled"), True)

    connection_changed = False
    new_base_url = provider.base_url
    new_api_key: str | None = None

    if "base_url" in data:
        base_url, error = _check_base_url(str(data.get("base_url") or ""))
        if error:
            return LLMResult(LLMStatus.PARAM_ERR, error)
        if base_url != provider.base_url:
            connection_changed = True
        new_base_url = base_url

    template = get_template(provider.template_code)
    if "api_key" in data:
        new_api_key = str(data.get("api_key") or "").strip()
        if template and template.requires_api_key and not new_api_key:
            return LLMResult(LLMStatus.PARAM_ERR, "API Key 不能为空")
        connection_changed = True

    fetched: list[dict] | None = None
    sync_status = "skipped"
    sync_message = ""
    if connection_changed:
        try:
            current_key = (
                new_api_key
                if new_api_key is not None
                else (
                    crypto.decrypt_api_key(provider.api_key_encrypted)
                    if provider.api_key_encrypted
                    else ""
                )
            )
        except ValueError as exc:
            return LLMResult(LLMStatus.DB_ERR, str(exc))

        access = ProviderAccess(provider.protocol, new_base_url, current_key)
        try:
            fetched = get_adapter(provider.protocol).list_models(access)
            if fetched:
                sync_status = "ok"
                sync_message = "模型列表已同步"
            else:
                sync_status = "unavailable"
                sync_message = SYNC_EMPTY
        except ProviderError as exc:
            if exc.code == LLMStatus.PROVIDER_AUTH_ERR:
                return LLMResult(
                    LLMStatus.PROVIDER_AUTH_ERR, "API Key 无效或无权限，配置未保存"
                )
            sync_status = "unavailable"
            sync_message = SYNC_UNAVAILABLE

        fields["base_url"] = new_base_url
        fields["last_sync_error"] = "" if fetched else sync_message[:500]
        if new_api_key is not None:
            try:
                fields["api_key_encrypted"] = (
                    crypto.encrypt_api_key(new_api_key) if new_api_key else ""
                )
                fields["api_key_masked"] = (
                    crypto.mask_api_key(new_api_key) if new_api_key else ""
                )
            except ValueError as exc:
                return LLMResult(LLMStatus.PARAM_ERR, str(exc))

    updated = llm_provider_crud.update(provider.pk, **fields) if fields else existing
    if updated.code != DBStatus.SUCCESS:
        return _from_db(
            updated,
            "配置名称已存在" if updated.code == DBStatus.DUPLICATE_ERR else None,
        )

    provider = updated.data
    count = 0
    if fetched:
        count = _sync_models(provider, fetched)
        provider = llm_provider_crud.get_by_pk(provider.pk).data or provider

    return LLMResult(
        LLMStatus.SUCCESS,
        sync_message if connection_changed else "配置已更新",
        {
            "provider": _provider_dict(provider, count or None),
            "model_sync": {"status": sync_status, "count": count, "message": sync_message},
        },
    )


def delete_provider(user, provider_id: int) -> LLMResult:
    existing = llm_provider_crud.get_by_user(user.pk, provider_id)
    if existing.code != DBStatus.SUCCESS:
        return _from_db(existing, "供应商配置不存在")
    deleted = llm_provider_crud.delete(existing.data.pk)
    if deleted.code != DBStatus.SUCCESS:
        return _from_db(deleted)
    return LLMResult(LLMStatus.SUCCESS, "供应商配置已删除", {"id": provider_id})


def refresh_models(user, provider_id: int) -> LLMResult:
    existing = llm_provider_crud.get_by_user(user.pk, provider_id)
    if existing.code != DBStatus.SUCCESS:
        return _from_db(existing, "供应商配置不存在")
    provider = existing.data

    try:
        access = _access_from_config(provider)
        fetched = get_adapter(provider.protocol).list_models(access)
    except ValueError as exc:
        return LLMResult(LLMStatus.DB_ERR, str(exc))
    except ProviderError as exc:
        llm_provider_crud.update(
            provider.pk,
            last_synced_at=timezone.now(),
            last_sync_error=SYNC_UNAVAILABLE[:500],
        )
        return LLMResult(
            exc.code, SYNC_UNAVAILABLE,
            {"detail": exc.message, "upstream_status": exc.upstream_status},
        )

    if not fetched:
        llm_provider_crud.update(
            provider.pk,
            last_synced_at=timezone.now(),
            last_sync_error=SYNC_EMPTY[:500],
        )
        return LLMResult(LLMStatus.SUCCESS, SYNC_EMPTY, {"status": "unavailable", "count": 0})

    count = _sync_models(provider, fetched)
    llm_provider_crud.update(
        provider.pk, last_synced_at=timezone.now(), last_sync_error=""
    )
    return LLMResult(
        LLMStatus.SUCCESS, f"模型列表已同步（{count} 个）", {"count": count}
    )


# ==================== 模型 ====================
def list_models(user, data: dict | None = None) -> LLMResult:
    data = data or {}
    category = str(data.get("category") or "").strip() or None
    if category and category not in CATEGORIES:
        return LLMResult(LLMStatus.PARAM_ERR, f"分类只能是：{', '.join(CATEGORIES)}")

    provider_id = data.get("provider_id")
    if provider_id not in (None, "", 0):
        try:
            provider_id = int(provider_id)
        except (TypeError, ValueError):
            return LLMResult(LLMStatus.PARAM_ERR, "provider_id 必须是整数")
        owned = llm_provider_crud.get_by_user(user.pk, provider_id)
        if owned.code != DBStatus.SUCCESS:
            return LLMResult(LLMStatus.NOT_FOUND, "供应商配置不存在")
    else:
        provider_id = None

    result = llm_model_crud.list_by_user(
        user.pk, category=category, provider_id=provider_id
    )
    if result.code != DBStatus.SUCCESS:
        return _from_db(result)

    providers_result = llm_provider_crud.list_by_user(user.pk)
    providers = (
        {item.pk: item for item in providers_result.data}
        if providers_result.code == DBStatus.SUCCESS
        else {}
    )

    rows = result.data
    groups = []
    for code in CATEGORIES:
        models = [
            _model_dict(model, providers.get(model.provider_id))
            for model in rows
            if model.category == code
        ]
        if models:
            groups.append(
                {
                    "category": code,
                    "label": CATEGORY_LABELS.get(code, code),
                    "count": len(models),
                    "models": models,
                }
            )
    return LLMResult(
        LLMStatus.SUCCESS, "ok", {"total": len(rows), "groups": groups}
    )


def list_provider_models(user, provider_id: int) -> LLMResult:
    existing = llm_provider_crud.get_by_user(user.pk, provider_id)
    if existing.code != DBStatus.SUCCESS:
        return _from_db(existing, "供应商配置不存在")
    provider = existing.data
    result = llm_model_crud.list_by_provider(provider.pk)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result)
    models = [_model_dict(model, provider) for model in result.data]
    return LLMResult(
        LLMStatus.SUCCESS, "ok", {"total": len(models), "models": models}
    )


def add_manual_model(user, provider_id: int, data: dict | None = None) -> LLMResult:
    data = data or {}
    existing = llm_provider_crud.get_by_user(user.pk, provider_id)
    if existing.code != DBStatus.SUCCESS:
        return _from_db(existing, "供应商配置不存在")
    provider = existing.data

    model_id = str(data.get("model_id") or "").strip()[:200]
    if not model_id:
        return LLMResult(LLMStatus.PARAM_ERR, "模型名称不能为空")

    category = str(data.get("category") or "").strip()
    if not category:
        category = classify_model(provider.protocol, model_id, {})
    if category not in CATEGORIES:
        return LLMResult(LLMStatus.PARAM_ERR, f"分类只能是：{', '.join(CATEGORIES)}")

    display_name = str(data.get("display_name") or model_id)[:200]
    created = llm_model_crud.create(
        provider=provider,
        model_id=model_id,
        display_name=display_name,
        category=category,
        param_spec=build_param_spec(provider.protocol, category, model_id),
        source="manual",
        raw={},
        enabled=True,
    )
    if created.code != DBStatus.SUCCESS:
        return _from_db(created, "该模型已存在" if created.code == DBStatus.DUPLICATE_ERR else None)
    return LLMResult(
        LLMStatus.SUCCESS,
        "模型已添加（手动登记，可用性由录入者负责）",
        {"model": _model_dict(created.data, provider)},
    )


def update_model(user, model_pk: int, data: dict | None = None) -> LLMResult:
    data = data or {}
    result = llm_model_crud.get_by_pk(model_pk)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result, "模型不存在")
    model = result.data
    owner = llm_provider_crud.get_by_user(user.pk, model.provider_id)
    if owner.code != DBStatus.SUCCESS:
        return LLMResult(LLMStatus.NOT_FOUND, "模型不存在")

    fields: dict = {}
    if "enabled" in data:
        fields["enabled"] = _as_bool(data.get("enabled"), True)
    if "display_name" in data:
        display_name = str(data.get("display_name") or "").strip()[:200]
        if display_name:
            fields["display_name"] = display_name
    if not fields:
        return LLMResult(LLMStatus.PARAM_ERR, "没有需要更新的字段")

    updated = llm_model_crud.update(model.pk, **fields)
    if updated.code != DBStatus.SUCCESS:
        return _from_db(updated)
    return LLMResult(
        LLMStatus.SUCCESS,
        "模型已更新",
        {"model": _model_dict(updated.data, owner.data)},
    )


def delete_model(user, model_pk: int) -> LLMResult:
    result = llm_model_crud.get_by_pk(model_pk)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result, "模型不存在")
    model = result.data
    owner = llm_provider_crud.get_by_user(user.pk, model.provider_id)
    if owner.code != DBStatus.SUCCESS:
        return LLMResult(LLMStatus.NOT_FOUND, "模型不存在")
    deleted = llm_model_crud.delete(model.pk)
    if deleted.code != DBStatus.SUCCESS:
        return _from_db(deleted)
    return LLMResult(LLMStatus.SUCCESS, "模型已删除", {"id": model_pk})


# ==================== 统一调用网关 ====================
def _parse_model_id(data: dict) -> tuple[int | None, LLMResult | None]:
    try:
        return int(data.get("model_id")), None
    except (TypeError, ValueError):
        return None, LLMResult(LLMStatus.PARAM_ERR, "model_id 必须是整数")


def _resolve_model(user, model_pk: int):
    result = llm_model_crud.get_by_pk(model_pk)
    if result.code != DBStatus.SUCCESS:
        return None, None, LLMResult(LLMStatus.NOT_FOUND, "模型不存在")
    model = result.data
    owner = llm_provider_crud.get_by_user(user.pk, model.provider_id)
    if owner.code != DBStatus.SUCCESS:
        return None, None, LLMResult(LLMStatus.NOT_FOUND, "模型不存在")
    provider = owner.data
    if not model.enabled:
        return None, None, LLMResult(LLMStatus.MODEL_UNSUPPORTED, "该模型已禁用")
    if not provider.enabled:
        return None, None, LLMResult(LLMStatus.MODEL_UNSUPPORTED, "该供应商配置已禁用")
    return model, provider, None


def get_model_config(user, model_pk: int) -> LLMResult:
    """供项目内其它应用获取模型配置（不含明文 Key）。"""
    model, provider, error = _resolve_model(user, model_pk)
    if error:
        return error
    return LLMResult(
        LLMStatus.SUCCESS,
        "ok",
        {"provider": _provider_dict(provider), "model": _model_dict(model, provider)},
    )


def chat_completion(user, data: dict | None = None) -> LLMResult:
    data = data or {}
    model_pk, error = _parse_model_id(data)
    if error:
        return error
    model, provider, error = _resolve_model(user, model_pk)
    if error:
        return error
    if model.category != "chat":
        return LLMResult(LLMStatus.MODEL_UNSUPPORTED, "该模型不是对话模型，无法通过 chat 接口调用")

    messages, errors = validate_messages(data.get("messages"))
    if errors:
        return LLMResult(LLMStatus.PARAM_ERR, "messages 参数不合法", {"errors": errors})
    params, errors = validate_params(model.param_spec or [], data.get("params"))
    if errors:
        return LLMResult(LLMStatus.PARAM_ERR, "调用参数不合法", {"errors": errors})

    try:
        access = _access_from_config(provider)
        normalized = get_adapter(provider.protocol).chat(
            access, model.model_id, messages, params
        )
    except ValueError as exc:
        return LLMResult(LLMStatus.DB_ERR, str(exc))
    except ProviderError as exc:
        return LLMResult(
            exc.code, exc.message, {"upstream_status": exc.upstream_status}
        )
    except Exception:
        logger.exception("调用对话模型失败：%s", model.model_id)
        return LLMResult(LLMStatus.UNKNOWN_ERR, "调用供应商失败")

    return LLMResult(
        LLMStatus.SUCCESS,
        "调用成功",
        {
            "model_id": model.pk,
            "model": model.model_id,
            "provider": provider.name,
            "protocol": provider.protocol,
            "content": normalized.get("content") or "",
            "finish_reason": normalized.get("finish_reason"),
            "usage": normalized.get("usage") or {},
            "raw": normalized.get("raw"),
        },
    )


def create_embeddings(user, data: dict | None = None) -> LLMResult:
    data = data or {}
    model_pk, error = _parse_model_id(data)
    if error:
        return error
    model, provider, error = _resolve_model(user, model_pk)
    if error:
        return error
    if model.category != "embedding":
        return LLMResult(LLMStatus.MODEL_UNSUPPORTED, "该模型不是嵌入模型，无法通过 embeddings 接口调用")

    inputs, errors = validate_embedding_input(data.get("input"))
    if errors:
        return LLMResult(LLMStatus.PARAM_ERR, "input 参数不合法", {"errors": errors})
    params, errors = validate_params(model.param_spec or [], data.get("params"))
    if errors:
        return LLMResult(LLMStatus.PARAM_ERR, "调用参数不合法", {"errors": errors})

    try:
        access = _access_from_config(provider)
        normalized = get_adapter(provider.protocol).embeddings(
            access, model.model_id, inputs, params
        )
    except ValueError as exc:
        return LLMResult(LLMStatus.DB_ERR, str(exc))
    except ProviderError as exc:
        return LLMResult(
            exc.code, exc.message, {"upstream_status": exc.upstream_status}
        )
    except Exception:
        logger.exception("调用嵌入模型失败：%s", model.model_id)
        return LLMResult(LLMStatus.UNKNOWN_ERR, "调用供应商失败")

    return LLMResult(
        LLMStatus.SUCCESS,
        "调用成功",
        {
            "model_id": model.pk,
            "model": model.model_id,
            "provider": provider.name,
            "protocol": provider.protocol,
            "embeddings": normalized.get("embeddings") or [],
            "dimensions": normalized.get("dimensions") or 0,
            "usage": normalized.get("usage") or {},
        },
    )