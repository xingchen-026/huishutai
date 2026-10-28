"""接口层：后端路由列表查询。

只读扫描 Django URLconf，返回所有已注册路由的路径、名称、视图与 HTTP 方法；
不涉及任何业务数据，因此放在 api（接口层），业务代码仍然放在各领域应用。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.decorators import api_view
from rest_framework.response import Response

from sqldb.enums import DBStatus
from sqldb.result import DBResult

# HTTP 方法探测时忽略这些自动支持的方法
_IGNORED_METHODS = {"options", "head", "trace"}


def _walk_patterns(
    resolver: URLResolver, prefix: str = ""
) -> Iterator[tuple[str, URLPattern]]:
    """递归遍历 URLconf，产出 (完整路径, URLPattern)。"""
    for entry in resolver.url_patterns:
        path = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            yield from _walk_patterns(entry, path)
        elif isinstance(entry, URLPattern):
            yield path, entry


def _view_info(pattern: URLPattern) -> dict[str, Any]:
    """从回调里提取视图名、支持的 HTTP 方法与所属模块。"""
    callback = pattern.callback
    view_class = getattr(callback, "view_class", None)

    if view_class is not None:
        # DRF 的 @api_view 会把原函数包成 WrappedAPIView，
        # __name__ / __module__ 已被 DRF 还原成原函数的值。
        methods = sorted(
            method.upper()
            for method in getattr(view_class, "http_method_names", [])
            if method.lower() not in _IGNORED_METHODS
        )
        return {
            "name": view_class.__name__,
            "methods": methods or ["*"],
            "module": view_class.__module__,
        }

    # 普通 Django 函数视图无法静态推断支持的 HTTP 方法
    return {
        "name": getattr(callback, "__name__", callback.__class__.__name__),
        "methods": ["*"],
        "module": getattr(callback, "__module__", ""),
    }


@api_view(["GET"])
def route_list(request):
    """GET /routes/ —— 返回后端已注册路由列表（只读 URLconf 元信息）。"""
    routes = []
    for path, pattern in _walk_patterns(get_resolver()):
        info = _view_info(pattern)
        routes.append(
            {
                "path": "/" + path.lstrip("/"),
                "name": pattern.name,
                "view": info["name"],
                "methods": info["methods"],
                "module": info["module"],
            }
        )

    routes.sort(key=lambda item: item["path"])
    return Response(
        DBResult(
            DBStatus.SUCCESS,
            "ok",
            {"count": len(routes), "routes": routes},
        ).to_dict()
    )