"""开始节点：工作流入口，把初始数据传给下游。"""

from __future__ import annotations

import json

from Workflow.node.base import NodeError, NodeResult

NODE_META = {
    "name": "开始",
    "description": "工作流入口，向后传递初始数据。",
    "category": "触发器",
    "inputs": [],
    "outputs": [{"id": "out", "label": "输出"}],
    "params": [
        {
            "key": "payload",
            "label": "初始数据（JSON）",
            "type": "json",
            "default": "{}",
            "required": False,
            "help": "作为下游节点的输入；留空表示空对象。",
        },
    ],
}


def execute(config: dict, input_data: dict, context) -> NodeResult:
    raw = config.get("payload", "{}")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        payload = {}
    elif isinstance(raw, dict):
        payload = raw
    elif isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise NodeError(f"初始数据不是合法 JSON：{exc}") from exc
    else:
        raise NodeError("初始数据必须是 JSON 对象")
    return NodeResult(output={"payload": payload}, logs=["工作流开始"])
