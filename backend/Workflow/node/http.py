"""HTTP 请求节点。"""

from __future__ import annotations

import json

import requests

from url_safety import UnsafeUrlError, validate_http_url
from Workflow.node.base import NodeError, NodeResult, render_template

NODE_META = {
    "name": "HTTP 请求",
    "description": "请求一个 HTTP 接口，返回状态码与响应体。",
    "category": "网络",
    "inputs": [{"id": "in", "label": "输入"}],
    "outputs": [{"id": "out", "label": "输出"}],
    "params": [
        {
            "key": "method",
            "label": "请求方法",
            "type": "select",
            "default": "GET",
            "options": [
                {"value": "GET", "label": "GET"},
                {"value": "POST", "label": "POST"},
                {"value": "PUT", "label": "PUT"},
                {"value": "PATCH", "label": "PATCH"},
                {"value": "DELETE", "label": "DELETE"},
            ],
        },
        {
            "key": "url",
            "label": "URL",
            "type": "text",
            "required": True,
            "help": "支持 {{input}} 占位；仅允许 http/https。",
        },
        {"key": "headers", "label": "请求头（JSON）", "type": "json", "default": "{}"},
        {"key": "body", "label": "请求体", "type": "textarea", "default": "", "required": False},
        {
            "key": "timeout",
            "label": "超时（秒）",
            "type": "number",
            "default": 15,
            "required": False,
        },
    ],
}

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def execute(config: dict, input_data: dict, context) -> NodeResult:
    method = str(config.get("method") or "GET").upper()
    if method not in _ALLOWED_METHODS:
        raise NodeError(f"不支持的请求方法：{method}")

    url = render_template(str(config.get("url") or ""), input_data).strip()
    try:
        url = validate_http_url(url, allow_private=False)
    except UnsafeUrlError as exc:
        raise NodeError(str(exc)) from exc

    raw_headers = config.get("headers") or "{}"
    if isinstance(raw_headers, str):
        try:
            headers = json.loads(raw_headers or "{}")
        except json.JSONDecodeError as exc:
            raise NodeError(f"请求头不是合法 JSON：{exc}") from exc
    elif isinstance(raw_headers, dict):
        headers = raw_headers
    else:
        raise NodeError("请求头必须是 JSON 对象")
    if not isinstance(headers, dict):
        raise NodeError("请求头必须是 JSON 对象")

    body = render_template(str(config.get("body") or ""), input_data)
    content_type = str(headers.get("Content-Type") or headers.get("content-type") or "")

    try:
        timeout = min(max(float(config.get("timeout") or 15), 1), 60)
    except (TypeError, ValueError):
        timeout = 15

    request_kwargs: dict = {
        "headers": headers,
        "timeout": timeout,
        "allow_redirects": False,
    }
    if body and content_type.lower().startswith("application/json"):
        try:
            request_kwargs["json"] = json.loads(body)
        except json.JSONDecodeError as exc:
            raise NodeError(f"请求体不是合法 JSON：{exc}") from exc
    elif body:
        request_kwargs["data"] = body

    try:
        response = requests.request(
            method,
            url,
            **request_kwargs,
        )
    except requests.RequestException as exc:
        raise NodeError(f"HTTP 请求失败：{exc}") from exc
    if 300 <= response.status_code < 400:
        raise NodeError(f"目标地址返回重定向（HTTP {response.status_code}），已拒绝跟随")

    text = response.text or ""
    response_body: object = text[:100_000]
    try:
        response_body = json.loads(text) if text else {}
    except json.JSONDecodeError:
        pass

    return NodeResult(
        output={
            "status_code": response.status_code,
            "body": response_body,
            "reason": response.reason or "",
        },
        logs=[f"{method} {url} → HTTP {response.status_code}"],
    )
