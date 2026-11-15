"""条件分支节点：按输入字段比较结果走 true / false 端口。"""

from __future__ import annotations

from typing import Any

from Workflow.node.base import NodeError, NodeResult

NODE_META = {
    "name": "条件分支",
    "description": "按输入字段的取值进行判断，选择「是 / 否」分支。",
    "category": "逻辑",
    "inputs": [{"id": "in", "label": "输入"}],
    "outputs": [
        {"id": "true", "label": "是"},
        {"id": "false", "label": "否"},
    ],
    "params": [
        {
            "key": "field",
            "label": "判断字段",
            "type": "text",
            "default": "payload",
            "help": "输入数据的字段路径，例如 payload.status 或 status_code。",
        },
        {
            "key": "operator",
            "label": "比较方式",
            "type": "select",
            "default": "eq",
            "options": [
                {"value": "eq", "label": "等于"},
                {"value": "ne", "label": "不等于"},
                {"value": "contains", "label": "包含"},
                {"value": "not_contains", "label": "不包含"},
                {"value": "gt", "label": "大于"},
                {"value": "lt", "label": "小于"},
                {"value": "empty", "label": "为空"},
                {"value": "not_empty", "label": "不为空"},
            ],
        },
        {"key": "value", "label": "比较值", "type": "text", "default": "", "required": False},
    ],
}

_OPERATORS = {"eq", "ne", "contains", "not_contains", "gt", "lt", "empty", "not_empty"}


def _resolve(data: Any, path: str) -> Any:
    current = data
    for part in (path or "").split("."):
        if not part:
            continue
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def execute(config: dict, input_data: dict, context) -> NodeResult:
    operator = str(config.get("operator") or "eq")
    if operator not in _OPERATORS:
        raise NodeError(f"不支持的比较方式：{operator}")

    actual = _resolve(input_data, str(config.get("field") or ""))
    expected = config.get("value")
    matched = False

    if operator == "eq":
        matched = str(actual) == str(expected)
    elif operator == "ne":
        matched = str(actual) != str(expected)
    elif operator == "contains":
        matched = str(expected) in str(actual)
    elif operator == "not_contains":
        matched = str(expected) not in str(actual)
    elif operator == "gt":
        left, right = _as_number(actual), _as_number(expected)
        matched = left is not None and right is not None and left > right
    elif operator == "lt":
        left, right = _as_number(actual), _as_number(expected)
        matched = left is not None and right is not None and left < right
    elif operator == "empty":
        matched = actual in (None, "", [], {})
    elif operator == "not_empty":
        matched = actual not in (None, "", [], {})

    return NodeResult(
        output={"matched": matched, "value": actual, "input": input_data},
        next_port="true" if matched else "false",
        logs=[f"条件判断 {config.get('field')} {operator} {expected!r} → {matched}"],
    )
