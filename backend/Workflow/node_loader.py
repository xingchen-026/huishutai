"""节点注册表：先加载目录，具体节点按需 import（惰性 + 缓存）。"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from types import ModuleType
from typing import Any

from Workflow.node.base import NodeContext, NodeError, NodeResult

NODE_DIR = Path(__file__).resolve().parent / "node"
_NODE_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SKIP_FILES = {"base"}
_cache: dict[str, ModuleType] = {}


def list_node_files() -> list[str]:
    """只扫描节点目录，不导入任何节点实现。"""
    if not NODE_DIR.is_dir():
        return []
    types: list[str] = []
    for path in sorted(NODE_DIR.glob("*.py")):
        stem = path.stem
        if stem.startswith("_") or stem in _SKIP_FILES:
            continue
        if _NODE_TYPE_RE.fullmatch(stem):
            types.append(stem)
    return types


def get_node_module(node_type: str) -> ModuleType:
    """按需导入具体节点文件并缓存。"""
    if not node_type or not _NODE_TYPE_RE.fullmatch(node_type):
        raise NodeError(f"非法节点类型：{node_type!r}")
    if node_type not in list_node_files():
        raise NodeError(f"节点类型不存在：{node_type}")

    module = _cache.get(node_type)
    if module is None:
        try:
            module = importlib.import_module(f"Workflow.node.{node_type}")
        except Exception as exc:  # noqa: BLE001
            raise NodeError(f"节点加载失败：{node_type}（{exc}）") from exc
        if not hasattr(module, "execute"):
            raise NodeError(f"节点 {node_type} 缺少 execute() 方法")
        _cache[node_type] = module
    return module


def get_node_meta(node_type: str) -> dict[str, Any]:
    module = get_node_module(node_type)
    meta = dict(getattr(module, "NODE_META", {}) or {})
    meta.setdefault("name", node_type)
    meta.setdefault("description", "")
    meta.setdefault("category", "通用")
    meta.setdefault("inputs", [{"id": "in", "label": "输入"}])
    meta.setdefault("outputs", [{"id": "out", "label": "输出"}])
    meta.setdefault("params", [])
    meta["type"] = node_type
    return meta


def execute_node(
    node_type: str, config: dict, input_data: dict, context: NodeContext
) -> NodeResult:
    module = get_node_module(node_type)
    try:
        result = module.execute(config or {}, input_data or {}, context)
    except NodeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise NodeError(f"节点执行异常：{exc}") from exc
    if not isinstance(result, NodeResult):
        raise NodeError("节点 execute() 必须返回 NodeResult")
    return result
