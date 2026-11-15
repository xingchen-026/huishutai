"""节点接口定义：节点文件统一返回 NodeResult，失败抛 NodeError。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeContext:
    user: Any
    workflow: Any
    node_key: str


@dataclass
class NodeResult:
    output: dict[str, Any]
    next_port: str = "out"
    logs: list[str] = field(default_factory=list)


class NodeError(Exception):
    """节点可预期失败（参数不合法、依赖调用失败等），由执行器转成执行结果。"""


def render_template(text: str, input_data: dict[str, Any]) -> str:
    """把模板中的 {{input}} 替换为上游输出 JSON。"""
    if not text:
        return ""
    try:
        payload = json.dumps(input_data or {}, ensure_ascii=False, default=str)
    except Exception:
        payload = str(input_data)
    return text.replace("{{input}}", payload)
