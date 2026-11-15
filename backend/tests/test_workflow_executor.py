"""Workflow 执行引擎测试：图遍历、分支、环路、步数上限与失败传播。

执行器只读取节点的 key/node_type/name/config，因此用 SimpleNamespace 构造
假节点/假连线；真实节点实现由 node_loader 按类型加载，http/llm 全部 mock。
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from Workflow import executor
from Workflow.executor import MAX_STEPS


def make_node(key, node_type, config=None, name=""):
    return SimpleNamespace(key=key, node_type=node_type, name=name, config=config or {})


def make_edge(source_key, target_key, source_port="out", target_port="in"):
    return SimpleNamespace(
        source_key=source_key,
        source_port=source_port,
        target_key=target_key,
        target_port=target_port,
    )


def run_graph(nodes, edges):
    return executor.run_graph(None, None, nodes, edges)


def condition_config(matched):
    """让 condition 节点稳定走 true/false 端口的参数（输入带 payload={} 时）。"""
    if matched:
        return {"field": "payload", "operator": "empty"}
    return {"field": "payload", "operator": "eq", "value": "不会相等"}


class GraphBasicsTest(SimpleTestCase):
    """入口节点缺失、空图、单节点成功等基本结构。"""

    def test_missing_start_node_failed(self):
        nodes = [make_node("c1", "condition", condition_config(True))]
        result = run_graph(nodes, [])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "工作流缺少 start 节点")
        self.assertEqual(result["steps"], [])
        self.assertEqual(result["output"], {})
        self.assertIsInstance(result["duration_ms"], int)
        self.assertGreaterEqual(result["duration_ms"], 0)

    def test_empty_nodes_failed(self):
        result = run_graph([], [])
        self.assertEqual(result["status"], "failed")
        self.assertIn("start", result["error"])
        self.assertEqual(result["steps"], [])

    @unittest.expectedFailure
    def test_empty_nodes_should_report_workflow_empty(self):
        """缺陷：工作流为空 分支永远不会命中（start 检查在 nodes 空检查之前）。"""
        result = run_graph([], [])
        self.assertEqual(result["error"], "工作流为空")

    def test_single_start_success_structure(self):
        nodes = [make_node("s", "start", {"payload": {"a": 1}}, name="开始")]
        result = run_graph(nodes, [])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["error"], "")
        self.assertEqual(len(result["steps"]), 1)

        step = result["steps"][0]
        self.assertEqual(step["node_key"], "s")
        self.assertEqual(step["node_type"], "start")
        self.assertEqual(step["name"], "开始")
        self.assertEqual(step["status"], "success")
        self.assertIsInstance(step["duration_ms"], int)
        self.assertGreaterEqual(step["duration_ms"], 0)
        self.assertEqual(step["output"], {"payload": {"a": 1}})
        self.assertEqual(step["logs"], ["工作流开始"])
        self.assertEqual(result["output"], step["output"])
        self.assertIsInstance(result["duration_ms"], int)
        self.assertGreaterEqual(result["duration_ms"], 0)

    def test_node_name_falls_back_to_type(self):
        nodes = [make_node("s", "start", {}, name="")]
        result = run_graph(nodes, [])
        self.assertEqual(result["steps"][0]["name"], "start")

    def test_output_is_last_step_output(self):
        nodes = [
            make_node("s", "start", {"payload": {"q": 1}}),
            make_node("c", "condition", condition_config(True)),
        ]
        edges = [make_edge("s", "c")]
        result = run_graph(nodes, edges)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["steps"]), 2)
        last = result["steps"][-1]
        self.assertEqual(last["node_key"], "c")
        self.assertEqual(result["output"], last["output"])
        self.assertIn("matched", result["output"])
        self.assertIn("value", result["output"])
        self.assertIn("input", result["output"])

    def test_all_success_steps_status(self):
        nodes = [
            make_node("s", "start"),
            make_node("c1", "condition", condition_config(True)),
            make_node("c2", "condition", condition_config(True)),
        ]
        edges = [
            make_edge("s", "c1"),
            make_edge("c1", "c2", source_port="true"),
        ]
        result = run_graph(nodes, edges)
        self.assertEqual(result["status"], "success")
        self.assertEqual(
            [(step["node_key"], step["status"]) for step in result["steps"]],
            [("s", "success"), ("c1", "success"), ("c2", "success")],
        )


class BranchTest(SimpleTestCase):
    """condition 分支、端口匹配、多入边与环路控制。"""

    def _branch_graph(self, matched):
        nodes = [
            make_node("s", "start"),
            make_node("c", "condition", condition_config(matched)),
            make_node("yes", "condition", {"operator": "eq", "value": "x"}),
            make_node("no", "condition", {"operator": "eq", "value": "x"}),
        ]
        edges = [
            make_edge("s", "c"),
            make_edge("c", "yes", source_port="true"),
            make_edge("c", "no", source_port="false"),
        ]
        return nodes, edges

    def test_true_branch_only(self):
        nodes, edges = self._branch_graph(True)
        result = run_graph(nodes, edges)
        keys = [step["node_key"] for step in result["steps"]]
        self.assertEqual(keys, ["s", "c", "yes"])

    def test_false_branch_only(self):
        nodes, edges = self._branch_graph(False)
        result = run_graph(nodes, edges)
        keys = [step["node_key"] for step in result["steps"]]
        self.assertEqual(keys, ["s", "c", "no"])

    def test_source_port_mismatch_edge_skipped(self):
        nodes = [
            make_node("s", "start"),
            make_node("c", "condition", condition_config(True)),
            make_node("next", "condition"),
        ]
        edges = [
            make_edge("s", "c"),
            make_edge("c", "next", source_port="false"),
        ]
        result = run_graph(nodes, edges)
        keys = [step["node_key"] for step in result["steps"]]
        self.assertEqual(keys, ["s", "c"])

    def test_multi_incoming_uses_first_source_output(self):
        nodes = [
            make_node("s", "start", {"payload": {}}),
            make_node("a", "condition", condition_config(True)),
            make_node("b", "condition", condition_config(False)),
            make_node("c", "condition"),
        ]
        edges = [
            make_edge("s", "a"),
            make_edge("s", "b"),
            make_edge("a", "c", source_port="true"),
            make_edge("b", "c", source_port="false"),
        ]
        result = run_graph(nodes, edges)
        self.assertEqual(result["status"], "success")
        steps = {step["node_key"]: step for step in result["steps"]}
        self.assertIn("c", steps)
        # 多入边时取 edges 中第一条入边的 source 输出：a → c 在前，故取 a 的输出。
        self.assertEqual(steps["c"]["output"]["input"], steps["a"]["output"])

    def test_visited_prevents_cycle_loop(self):
        nodes = [
            make_node("s", "start"),
            make_node("c", "condition", condition_config(True)),
        ]
        edges = [
            make_edge("s", "c"),
            make_edge("c", "s", source_port="true"),
        ]
        result = run_graph(nodes, edges)
        self.assertEqual(result["status"], "success")
        keys = [step["node_key"] for step in result["steps"]]
        self.assertEqual(keys, ["s", "c"])

    def test_max_steps_failure(self):
        # start + 100 个 condition 串成链，处理满 100 步后仍有队列 → 触发上限。
        nodes = [make_node("s", "start")]
        edges = []
        previous = "s"
        for index in range(MAX_STEPS):
            key = "c{0}".format(index)
            nodes.append(make_node(key, "condition", condition_config(True)))
            edges.append(
                make_edge(
                    previous,
                    key,
                    source_port="out" if previous == "s" else "true",
                )
            )
            previous = key
        self.assertEqual(len(nodes), MAX_STEPS + 1)

        result = run_graph(nodes, edges)
        self.assertEqual(result["status"], "failed")
        self.assertIn("执行步数超过上限", result["error"])
        self.assertEqual(len(result["steps"]), MAX_STEPS)
        self.assertIsInstance(result["steps"][-1]["duration_ms"], int)

    @unittest.expectedFailure
    def test_exactly_max_steps_graph_should_succeed(self):
        """缺陷：恰好执行 MAX_STEPS 步且队列已空时被误判为超限失败（差一错误）。"""
        nodes = [make_node("s", "start")]
        edges = []
        previous = "s"
        for index in range(MAX_STEPS - 1):
            key = "c{0}".format(index)
            nodes.append(make_node(key, "condition", condition_config(True)))
            edges.append(
                make_edge(
                    previous,
                    key,
                    source_port="out" if previous == "s" else "true",
                )
            )
            previous = key

        result = run_graph(nodes, edges)
        self.assertEqual(len(result["steps"]), MAX_STEPS)
        self.assertEqual(result["status"], "success")


class FailureTest(SimpleTestCase):
    """节点错误传播：NodeError 直接失败，非 NodeError 由 node_loader 包装。"""

    def test_node_error_fails_with_node_name_and_reason(self):
        nodes = [
            make_node("s", "start"),
            make_node("h", "http", {"url": "ftp://bad"}, name="我的HTTP"),
        ]
        edges = [make_edge("s", "h")]
        result = run_graph(nodes, edges)

        self.assertEqual(result["status"], "failed")
        self.assertIn("节点「我的HTTP」执行失败", result["error"])
        self.assertIn("URL 必须是合法的 http/https 地址", result["error"])
        self.assertEqual(result["output"], {})

        last = result["steps"][-1]
        self.assertEqual(last["node_key"], "h")
        self.assertEqual(last["status"], "failed")
        self.assertIn("URL 必须是合法", last["error"])
        self.assertIsInstance(last["duration_ms"], int)
        self.assertGreaterEqual(last["duration_ms"], 0)
        self.assertNotIn("output", last)

    def test_node_error_uses_type_when_name_empty(self):
        nodes = [
            make_node("s", "start"),
            make_node("h", "http", {"url": ""}),
        ]
        result = run_graph(nodes, [make_edge("s", "h")])
        self.assertEqual(result["status"], "failed")
        self.assertIn("节点「http」执行失败", result["error"])

    def test_non_node_error_wrapped_by_node_loader(self):
        nodes = [make_node("s", "start")]
        with patch("Workflow.node.start.execute", side_effect=RuntimeError("boom")):
            result = run_graph(nodes, [])
        self.assertEqual(result["status"], "failed")
        self.assertIn("节点执行异常：boom", result["error"])
        self.assertEqual(result["steps"][-1]["status"], "failed")
