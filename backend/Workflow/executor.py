"""工作流执行器：按连线从 start 节点推进，支持 condition 分支。"""

from __future__ import annotations

import time
from typing import Any

from Workflow.node.base import NodeContext, NodeError
from Workflow.node_loader import execute_node

MAX_STEPS = 100


def run_graph(user, workflow, nodes: list, edges: list) -> dict[str, Any]:
    started_at = time.perf_counter()

    def failed(message: str, steps: list) -> dict[str, Any]:
        return {
            "status": "failed",
            "error": message,
            "steps": steps,
            "output": steps[-1]["output"] if steps and steps[-1].get("output") else {},
            "duration_ms": int((time.perf_counter() - started_at) * 1000),
        }

    node_map = {node.key: node for node in nodes}
    start_node = next((node for node in nodes if node.node_type == "start"), None)
    if start_node is None:
        return failed("工作流缺少 start 节点", [])
    if not nodes:
        return failed("工作流为空", [])

    outgoing: dict[str, list] = {}
    for edge in edges:
        outgoing.setdefault(edge.source_key, []).append(edge)

    steps: list[dict[str, Any]] = []
    outputs: dict[str, dict] = {}
    visited: set[str] = set()
    queue = [start_node]

    while queue and len(steps) < MAX_STEPS:
        node = queue.pop(0)
        if node.key in visited:
            continue
        visited.add(node.key)

        incoming = [edge for edge in edges if edge.target_key == node.key]
        input_data = outputs.get(incoming[0].source_key, {}) if incoming else {}

        step_started = time.perf_counter()
        try:
            result = execute_node(
                node.node_type,
                node.config or {},
                input_data,
                NodeContext(user=user, workflow=workflow, node_key=node.key),
            )
        except NodeError as exc:
            steps.append(
                {
                    "node_key": node.key,
                    "node_type": node.node_type,
                    "name": node.name or node.node_type,
                    "status": "failed",
                    "error": str(exc),
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                }
            )
            return failed(f"节点「{node.name or node.node_type}」执行失败：{exc}", steps)

        outputs[node.key] = result.output
        steps.append(
            {
                "node_key": node.key,
                "node_type": node.node_type,
                "name": node.name or node.node_type,
                "status": "success",
                "output": result.output,
                "logs": result.logs,
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
            }
        )

        for edge in outgoing.get(node.key, []):
            if edge.source_port != result.next_port:
                continue
            target = node_map.get(edge.target_key)
            if target and target.key not in visited:
                queue.append(target)

    if len(steps) >= MAX_STEPS:
        return failed(f"执行步数超过上限（{MAX_STEPS}），请检查工作流是否成环", steps)

    return {
        "status": "success",
        "error": "",
        "steps": steps,
        "output": steps[-1]["output"] if steps else {},
        "duration_ms": int((time.perf_counter() - started_at) * 1000),
    }
