"""供应商协议适配器：OpenAI 兼容 / Anthropic / Gemini。

只负责 HTTP 协议转换与归一化，不含业务规则。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

from LLMapi.result import LLMStatus


@dataclass(frozen=True)
class ProviderAccess:
    protocol: str
    base_url: str
    api_key: str = ""


class ProviderError(Exception):
    def __init__(
        self,
        code: LLMStatus,
        message: str,
        *,
        upstream_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.upstream_status = upstream_status


def _join(base_url: str, path: str) -> str:
    return f"{(base_url or '').rstrip('/')}{path}"


def _error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return (response.text or "")[:200]
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or "")[:200]
        if isinstance(error, str):
            return error[:200]
        return str(payload.get("message") or "")[:200]
    return str(payload)[:200]


_AUTH_HINTS = (
    "api key",
    "apikey",
    "invalid key",
    "incorrect api key",
    "authentication",
    "unauthorized",
    "auth failed",
    "permission",
    "鉴权",
    "认证",
    "无效的api",
    "无效的 api",
)


def _request(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    json_body: dict | None = None,
    params: dict | None = None,
) -> Any:
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=json_body,
            params=params,
            timeout=(5, settings.LLMAPI_HTTP_TIMEOUT),
        )
    except requests.Timeout as exc:
        raise ProviderError(LLMStatus.PROVIDER_UNREACHABLE, "连接供应商超时") from exc
    except requests.RequestException as exc:
        raise ProviderError(
            LLMStatus.PROVIDER_UNREACHABLE, "无法连接供应商，请检查 base_url 或网络"
        ) from exc

    if response.status_code in (401, 403):
        raise ProviderError(
            LLMStatus.PROVIDER_AUTH_ERR,
            "API Key 无效或无权限",
            upstream_status=response.status_code,
        )

    if response.status_code >= 400:
        detail = _error_detail(response)
        if any(hint in detail.lower() for hint in _AUTH_HINTS):
            raise ProviderError(
                LLMStatus.PROVIDER_AUTH_ERR,
                "API Key 无效或无权限",
                upstream_status=response.status_code,
            )
        if response.status_code >= 500:
            raise ProviderError(
                LLMStatus.PROVIDER_API_ERR,
                f"供应商服务异常（HTTP {response.status_code}）",
                upstream_status=response.status_code,
            )
        raise ProviderError(
            LLMStatus.PROVIDER_API_ERR,
            f"供应商返回错误（HTTP {response.status_code}）：{detail}",
            upstream_status=response.status_code,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError(LLMStatus.PROVIDER_API_ERR, "供应商返回了非 JSON 响应") from exc


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content or "")


class OpenAIAdapter:
    protocol = "openai"

    def _headers(self, access: ProviderAccess) -> dict:
        headers = {"Content-Type": "application/json"}
        if access.api_key:
            headers["Authorization"] = f"Bearer {access.api_key}"
        return headers

    def list_models(self, access: ProviderAccess) -> list[dict]:
        payload = _request("GET", _join(access.base_url, "/models"), headers=self._headers(access))
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("data") or payload.get("models") or []
        else:
            items = []
        result: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id") or item.get("model")
            if not model_id:
                continue
            result.append(
                {
                    "model_id": str(model_id),
                    "display_name": str(item.get("name") or model_id),
                    "raw": item,
                }
            )
            if len(result) >= settings.LLMAPI_MAX_MODELS:
                break
        return result

    def chat(
        self, access: ProviderAccess, model_id: str, messages: list[dict], params: dict
    ) -> dict:
        payload = _request(
            "POST",
            _join(access.base_url, "/chat/completions"),
            headers=self._headers(access),
            json_body={"model": model_id, "messages": messages, **params},
        )
        choices = payload.get("choices") or []
        first = choices[0] if choices else {}
        content = (first.get("message") or {}).get("content")
        return {
            "content": _text_content(content),
            "finish_reason": first.get("finish_reason"),
            "usage": payload.get("usage") or {},
            "raw": payload,
        }

    def embeddings(
        self, access: ProviderAccess, model_id: str, inputs: list[str], params: dict
    ) -> dict:
        payload = _request(
            "POST",
            _join(access.base_url, "/embeddings"),
            headers=self._headers(access),
            json_body={
                "model": model_id,
                "input": inputs if len(inputs) > 1 else inputs[0],
                **params,
            },
        )
        data = payload.get("data") or []
        vectors = [
            item.get("embedding")
            for item in sorted(data, key=lambda x: x.get("index", 0))
            if isinstance(item, dict)
        ]
        return {
            "embeddings": vectors,
            "dimensions": len(vectors[0]) if vectors and isinstance(vectors[0], list) else 0,
            "usage": payload.get("usage") or {},
            "raw": payload,
        }


class AnthropicAdapter:
    protocol = "anthropic"

    def _api_base(self, access: ProviderAccess) -> str:
        base = (access.base_url or "").rstrip("/")
        return base if base.endswith("/v1") else f"{base}/v1"

    def _headers(self, access: ProviderAccess) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": access.api_key,
            "anthropic-version": "2023-06-01",
        }

    def list_models(self, access: ProviderAccess) -> list[dict]:
        url = _join(self._api_base(access), "/models")
        params = {"limit": 1000}
        result: list[dict] = []
        for _ in range(5):
            payload = _request("GET", url, headers=self._headers(access), params=params)
            for item in payload.get("data") or []:
                if not isinstance(item, dict):
                    continue
                model_id = item.get("id")
                if not model_id:
                    continue
                result.append(
                    {
                        "model_id": str(model_id),
                        "display_name": str(item.get("display_name") or model_id),
                        "raw": item,
                    }
                )
            if not payload.get("has_more"):
                break
            last_id = payload.get("last_id")
            if not last_id:
                break
            params["after_id"] = last_id
            if len(result) >= settings.LLMAPI_MAX_MODELS:
                break
        return result[: settings.LLMAPI_MAX_MODELS]

    def chat(
        self, access: ProviderAccess, model_id: str, messages: list[dict], params: dict
    ) -> dict:
        system_parts = [_text_content(m["content"]) for m in messages if m["role"] == "system"]
        conversation = [
            {"role": m["role"], "content": _text_content(m["content"])}
            for m in messages
            if m["role"] in ("user", "assistant")
        ]
        if not conversation:
            raise ProviderError(LLMStatus.PARAM_ERR, "messages 中没有 user/assistant 消息")

        body: dict[str, Any] = {
            "model": model_id,
            "messages": conversation,
            "max_tokens": params.get("max_tokens", 1024),
        }
        system_text = "\n".join(part for part in system_parts if part).strip()
        if system_text:
            body["system"] = system_text
        if "temperature" in params:
            body["temperature"] = params["temperature"]
        if "top_p" in params:
            body["top_p"] = params["top_p"]
        if "top_k" in params:
            body["top_k"] = params["top_k"]
        if "stop" in params:
            body["stop_sequences"] = params["stop"]

        payload = _request(
            "POST",
            _join(self._api_base(access), "/messages"),
            headers=self._headers(access),
            json_body=body,
        )
        text = "".join(
            block.get("text", "")
            for block in payload.get("content") or []
            if isinstance(block, dict) and block.get("type") == "text"
        )
        usage = payload.get("usage") or {}
        return {
            "content": text,
            "finish_reason": payload.get("stop_reason"),
            "usage": {
                "prompt_tokens": usage.get("input_tokens"),
                "completion_tokens": usage.get("output_tokens"),
                "total_tokens": None,
            },
            "raw": payload,
        }

    def embeddings(
        self, access: ProviderAccess, model_id: str, inputs: list[str], params: dict
    ) -> dict:
        raise ProviderError(LLMStatus.MODEL_UNSUPPORTED, "Anthropic 协议不提供 embeddings 接口")


class GeminiAdapter:
    protocol = "gemini"

    def _api_base(self, access: ProviderAccess) -> str:
        base = (access.base_url or "").rstrip("/")
        return base if base.endswith("/v1beta") else f"{base}/v1beta"

    def list_models(self, access: ProviderAccess) -> list[dict]:
        url = _join(self._api_base(access), "/models")
        result: list[dict] = []
        page_token = None
        for _ in range(5):
            params = {"pageSize": 1000, "key": access.api_key}
            if page_token:
                params["pageToken"] = page_token
            payload = _request("GET", url, params=params)
            for item in payload.get("models") or []:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or ""
                model_id = name[len("models/") :] if name.startswith("models/") else name
                if not model_id:
                    continue
                result.append(
                    {
                        "model_id": model_id,
                        "display_name": str(item.get("displayName") or model_id),
                        "raw": item,
                    }
                )
            page_token = payload.get("nextPageToken")
            if not page_token or len(result) >= settings.LLMAPI_MAX_MODELS:
                break
        return result[: settings.LLMAPI_MAX_MODELS]

    def chat(
        self, access: ProviderAccess, model_id: str, messages: list[dict], params: dict
    ) -> dict:
        system_texts: list[str] = []
        contents: list[dict] = []
        for message in messages:
            text = _text_content(message["content"])
            if message["role"] == "system":
                system_texts.append(text)
                continue
            role = "user" if message["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": text}]})
        if not contents:
            raise ProviderError(LLMStatus.PARAM_ERR, "messages 中没有 user/assistant 消息")

        body: dict[str, Any] = {"contents": contents}
        if system_texts:
            body["systemInstruction"] = {"parts": [{"text": "\n".join(system_texts)}]}

        generation_config: dict[str, Any] = {}
        if "temperature" in params:
            generation_config["temperature"] = params["temperature"]
        if "top_p" in params:
            generation_config["topP"] = params["top_p"]
        if "top_k" in params:
            generation_config["topK"] = params["top_k"]
        if "max_tokens" in params:
            generation_config["maxOutputTokens"] = params["max_tokens"]
        if "stop" in params:
            generation_config["stopSequences"] = params["stop"]
        if generation_config:
            body["generationConfig"] = generation_config

        payload = _request(
            "POST",
            _join(self._api_base(access), f"/models/{model_id}:generateContent"),
            params={"key": access.api_key},
            json_body=body,
        )
        candidates = payload.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        content = candidate.get("content") or {}
        text = "".join(
            part.get("text", "") for part in content.get("parts") or [] if isinstance(part, dict)
        )
        usage = payload.get("usageMetadata") or {}
        return {
            "content": text,
            "finish_reason": candidate.get("finishReason"),
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount"),
                "completion_tokens": usage.get("candidatesTokenCount"),
                "total_tokens": usage.get("totalTokenCount"),
            },
            "raw": payload,
        }

    def embeddings(
        self, access: ProviderAccess, model_id: str, inputs: list[str], params: dict
    ) -> dict:
        requests_body = [
            {
                "model": f"models/{model_id}",
                "content": {"parts": [{"text": text}]},
            }
            for text in inputs
        ]
        payload = _request(
            "POST",
            _join(self._api_base(access), f"/models/{model_id}:batchEmbedContents"),
            params={"key": access.api_key},
            json_body={"requests": requests_body},
        )
        vectors = [item.get("values") for item in payload.get("embeddings") or []]
        return {
            "embeddings": vectors,
            "dimensions": len(vectors[0]) if vectors and isinstance(vectors[0], list) else 0,
            "usage": {},
            "raw": payload,
        }


_ADAPTERS: dict[str, Any] = {
    adapter.protocol: adapter for adapter in (OpenAIAdapter(), AnthropicAdapter(), GeminiAdapter())
}


def get_adapter(protocol: str):
    adapter = _ADAPTERS.get(protocol or "")
    if adapter is None:
        raise ProviderError(LLMStatus.PARAM_ERR, f"暂不支持的供应商协议：{protocol}")
    return adapter
