"""统一 URL 安全校验：scheme、userinfo、query/fragment、内网/回环/链路本地地址。"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from django.conf import settings


class UnsafeUrlError(ValueError):
    pass


def validate_http_url(raw: str, *, allow_private: bool | None = None) -> str:
    value = (raw or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeUrlError("URL 必须是合法的 http/https 地址")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URL 不能包含用户名密码")
    if parsed.query or parsed.fragment:
        raise UnsafeUrlError("URL 不能包含 query/fragment")

    allow = settings.LLMAPI_ALLOW_PRIVATE_BASE_URL if allow_private is None else allow_private
    if allow:
        return value

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError("URL 域名解析失败") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeUrlError("不允许访问内网/本机地址")
    return value
