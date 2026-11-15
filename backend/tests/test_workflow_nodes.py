"""Workflow 节点实现与注册表测试：start / condition / http / llm / node_loader。

所有外部依赖（requests、LLMapi.chat_completion）均 mock，不发起真实网络请求；
节点模块只依赖 NodeContext 假对象，不需要数据库。
"""

from __future__ import annotations

import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from LLMapi.result import LLMResult, LLMStatus
from Workflow import node_loader
from Workflow.node import condition, http, llm, start
from Workflow.node.base import NodeContext, NodeError, NodeResult, render_template

HTTP_REQUEST = "Workflow.node.http.requests.request"
LLM_CHAT = "Workflow.node.llm.llm_services.chat_completion"


def make_context(user=None):
    return NodeContext(
        user=user or SimpleNamespace(pk=1),
        workflow=SimpleNamespace(pk=2),
        node_key="node-1",
    )


def fake_response(status_code=200, text="", reason="OK"):
    return SimpleNamespace(status_code=status_code, text=text, reason=reason)


def success_llm_result(data=None):
    payload = data or {
        "content": "你好",
        "usage": {"total_tokens": 3},
        "model": "gpt-4o",
        "provider": "openai",
    }
    return LLMResult(LLMStatus.SUCCESS, "ok", payload)


# ==================== start 节点 ====================
class StartNodeTest(SimpleTestCase):
    def test_empty_config_returns_empty_payload(self):
        result = start.execute({}, {}, make_context())
        self.assertEqual(result.output, {"payload": {}})
        self.assertEqual(result.next_port, "out")
        self.assertEqual(result.logs, ["工作流开始"])

    def test_none_and_blank_payload_return_empty_dict(self):
        self.assertEqual(
            start.execute({"payload": None}, {}, make_context()).output, {"payload": {}}
        )
        self.assertEqual(
            start.execute({"payload": "   "}, {}, make_context()).output, {"payload": {}}
        )

    def test_dict_payload_passed_through(self):
        payload = {"a": [1, 2], "中文": "值"}
        result = start.execute({"payload": payload}, {}, make_context())
        self.assertEqual(result.output, {"payload": payload})

    def test_json_string_object_parsed(self):
        result = start.execute({"payload": '{"a": 1}'}, {}, make_context())
        self.assertEqual(result.output, {"payload": {"a": 1}})

    def test_invalid_json_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "初始数据不是合法 JSON"):
            start.execute({"payload": '{"a": '}, {}, make_context())

    def test_non_dict_non_str_raises_node_error(self):
        for bad in (123, 1.5, True, ["a", "b"]):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(NodeError, "初始数据必须是 JSON 对象"):
                    start.execute({"payload": bad}, {}, make_context())

    @unittest.expectedFailure
    def test_json_array_string_should_be_rejected(self):
        """缺陷：报错文案要求 JSON 对象，但 JSON 数组字符串会被 json.loads 放行。"""
        with self.assertRaisesMessage(NodeError, "初始数据必须是 JSON 对象"):
            start.execute({"payload": '["a", "b"]'}, {}, make_context())

    def test_node_meta(self):
        self.assertEqual(start.NODE_META["name"], "开始")
        self.assertEqual(start.NODE_META["category"], "触发器")
        self.assertEqual(start.NODE_META["inputs"], [])
        self.assertTrue(any(param["key"] == "payload" for param in start.NODE_META["params"]))


# ==================== condition 节点 ====================
class ConditionNodeTest(SimpleTestCase):
    def run_node(self, config, input_data=None):
        return condition.execute(config, input_data or {}, make_context())

    def test_eq_operator(self):
        result = self.run_node(
            {"field": "status", "operator": "eq", "value": "ok"},
            {"status": "ok"},
        )
        self.assertTrue(result.output["matched"])
        self.assertEqual(result.output["value"], "ok")
        self.assertEqual(result.next_port, "true")
        self.assertFalse(
            self.run_node(
                {"field": "status", "operator": "eq", "value": "bad"},
                {"status": "ok"},
            ).output["matched"]
        )

    def test_ne_operator(self):
        self.assertTrue(
            self.run_node({"field": "n", "operator": "ne", "value": "2"}, {"n": "1"}).output[
                "matched"
            ]
        )
        self.assertFalse(
            self.run_node({"field": "n", "operator": "ne", "value": "1"}, {"n": "1"}).output[
                "matched"
            ]
        )

    def test_contains_and_not_contains(self):
        self.assertTrue(
            self.run_node(
                {"field": "text", "operator": "contains", "value": "world"},
                {"text": "hello world"},
            ).output["matched"]
        )
        self.assertFalse(
            self.run_node(
                {"field": "text", "operator": "contains", "value": "xxx"},
                {"text": "hello world"},
            ).output["matched"]
        )
        self.assertTrue(
            self.run_node(
                {"field": "text", "operator": "not_contains", "value": "xxx"},
                {"text": "hello world"},
            ).output["matched"]
        )
        self.assertFalse(
            self.run_node(
                {"field": "text", "operator": "not_contains", "value": "world"},
                {"text": "hello world"},
            ).output["matched"]
        )

    def test_gt_and_lt_numeric(self):
        self.assertTrue(
            self.run_node({"field": "n", "operator": "gt", "value": "10"}, {"n": 11}).output[
                "matched"
            ]
        )
        self.assertFalse(
            self.run_node({"field": "n", "operator": "gt", "value": "10"}, {"n": 9}).output[
                "matched"
            ]
        )
        self.assertTrue(
            self.run_node({"field": "n", "operator": "lt", "value": "10"}, {"n": "9"}).output[
                "matched"
            ]
        )
        self.assertFalse(
            self.run_node({"field": "n", "operator": "lt", "value": "10"}, {"n": "11"}).output[
                "matched"
            ]
        )

    def test_gt_non_numeric_is_false(self):
        self.assertFalse(
            self.run_node({"field": "n", "operator": "gt", "value": "10"}, {"n": "abc"}).output[
                "matched"
            ]
        )

    def test_empty_and_not_empty(self):
        for value in (None, "", [], {}):
            with self.subTest(value=value):
                self.assertTrue(
                    self.run_node({"field": "v", "operator": "empty"}, {"v": value}).output[
                        "matched"
                    ]
                )
        self.assertFalse(
            self.run_node({"field": "v", "operator": "empty"}, {"v": "x"}).output["matched"]
        )
        self.assertFalse(
            self.run_node({"field": "v", "operator": "empty"}, {"v": 0}).output["matched"]
        )
        self.assertTrue(
            self.run_node({"field": "v", "operator": "not_empty"}, {"v": "x"}).output["matched"]
        )
        self.assertFalse(
            self.run_node({"field": "v", "operator": "not_empty"}, {"v": None}).output["matched"]
        )

    def test_nested_dict_path(self):
        result = self.run_node(
            {"field": "payload.status", "operator": "eq", "value": "ok"},
            {"payload": {"status": "ok"}},
        )
        self.assertTrue(result.output["matched"])
        self.assertEqual(result.output["value"], "ok")

    def test_list_index_path(self):
        result = self.run_node(
            {"field": "items.1", "operator": "eq", "value": "b"},
            {"items": ["a", "b"]},
        )
        self.assertTrue(result.output["matched"])
        self.assertEqual(result.output["value"], "b")

    def test_missing_path_resolves_to_none(self):
        result = self.run_node(
            {"field": "payload.missing", "operator": "eq", "value": "x"},
            {"payload": {}},
        )
        self.assertIsNone(result.output["value"])
        self.assertFalse(result.output["matched"])

        out_of_range = self.run_node({"field": "items.5", "operator": "empty"}, {"items": ["a"]})
        self.assertIsNone(out_of_range.output["value"])
        self.assertTrue(out_of_range.output["matched"])

    def test_empty_field_resolves_whole_input(self):
        result = self.run_node({"field": "", "operator": "empty"}, {})
        self.assertTrue(result.output["matched"])
        self.assertEqual(result.output["input"], {})

    def test_default_operator_is_eq(self):
        result = self.run_node({"field": "v", "value": "1"}, {"v": "1"})
        self.assertTrue(result.output["matched"])

    def test_invalid_operator_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "不支持的比较方式：in"):
            self.run_node({"field": "v", "operator": "in", "value": "1"}, {"v": "1"})

    def test_output_and_false_port(self):
        input_data = {"v": "x"}
        result = self.run_node({"field": "v", "operator": "eq", "value": "y"}, input_data)
        self.assertFalse(result.output["matched"])
        self.assertEqual(result.output["value"], "x")
        self.assertEqual(result.output["input"], input_data)
        self.assertEqual(result.next_port, "false")
        self.assertTrue(result.logs[0].startswith("条件判断"))


# ==================== http 节点 ====================
class HttpNodeTest(SimpleTestCase):
    def setUp(self):
        # 单测不依赖真实 DNS：SSRF 校验仍执行，但解析结果固定为公网 IP
        self._gai = patch(
            "url_safety.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        )
        self._gai.start()
        self.addCleanup(self._gai.stop)

    def test_get_request_and_output(self):
        response = fake_response(status_code=200, text='{"ok": true}', reason="OK")
        with patch(HTTP_REQUEST, return_value=response) as mock_request:
            result = http.execute({"url": "https://api.example.com/x"}, {}, make_context())

        self.assertEqual(result.output, {"status_code": 200, "body": {"ok": True}, "reason": "OK"})
        self.assertEqual(result.next_port, "out")
        self.assertEqual(result.logs, ["GET https://api.example.com/x → HTTP 200"])
        mock_request.assert_called_once()
        self.assertEqual(mock_request.call_args.args, ("GET", "https://api.example.com/x"))
        self.assertEqual(mock_request.call_args.kwargs["headers"], {})
        self.assertNotIn("data", mock_request.call_args.kwargs)
        self.assertEqual(mock_request.call_args.kwargs["timeout"], 15)

    def test_lowercase_method_is_uppercased(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute({"method": "post", "url": "https://api.example.com/x"}, {}, make_context())
        self.assertEqual(mock_request.call_args.args[0], "POST")

    def test_url_template_replaced_with_input_json(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {"url": "https://api.example.com/echo/{{input}}"},
                {"a": 1},
                make_context(),
            )
        self.assertEqual(
            mock_request.call_args.args[1],
            'https://api.example.com/echo/{"a": 1}',
        )

    def test_headers_json_string(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {
                    "url": "https://api.example.com/x",
                    "headers": '{"X-Token": "abc"}',
                },
                {},
                make_context(),
            )
        self.assertEqual(mock_request.call_args.kwargs["headers"], {"X-Token": "abc"})

    def test_headers_dict(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {"url": "https://api.example.com/x", "headers": {"Accept": "text/plain"}},
                {},
                make_context(),
            )
        self.assertEqual(mock_request.call_args.kwargs["headers"], {"Accept": "text/plain"})

    def test_headers_not_object_raises_node_error(self):
        with patch(HTTP_REQUEST) as mock_request:
            with self.assertRaisesMessage(NodeError, "请求头必须是 JSON 对象"):
                http.execute(
                    {"url": "https://api.example.com/x", "headers": '["a"]'},
                    {},
                    make_context(),
                )
            with self.assertRaisesMessage(NodeError, "请求头必须是 JSON 对象"):
                http.execute(
                    {"url": "https://api.example.com/x", "headers": 123},
                    {},
                    make_context(),
                )
        mock_request.assert_not_called()

    def test_headers_invalid_json_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "请求头不是合法 JSON"):
            http.execute(
                {"url": "https://api.example.com/x", "headers": "not-json"},
                {},
                make_context(),
            )

    def test_json_body_parsed_when_content_type_json(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {
                    "url": "https://api.example.com/x",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"name": "张三"}',
                },
                {},
                make_context(),
            )
        self.assertEqual(mock_request.call_args.kwargs["json"], {"name": "张三"})
        self.assertNotIn("data", mock_request.call_args.kwargs)

    def test_json_body_parsed_with_lowercase_content_type(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {
                    "url": "https://api.example.com/x",
                    "headers": {"content-type": "application/json; charset=utf-8"},
                    "body": '{"x": 1}',
                },
                {},
                make_context(),
            )
        self.assertEqual(mock_request.call_args.kwargs["json"], {"x": 1})
        self.assertNotIn("data", mock_request.call_args.kwargs)

    def test_invalid_json_body_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "请求体不是合法 JSON"):
            http.execute(
                {
                    "url": "https://api.example.com/x",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"name": ',
                },
                {},
                make_context(),
            )

    def test_plain_body_passed_as_string(self):
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {
                    "url": "https://api.example.com/x",
                    "body": "a=1&b=2",
                },
                {},
                make_context(),
            )
        self.assertEqual(mock_request.call_args.kwargs["data"], "a=1&b=2")

    def test_json_response_parsed(self):
        with patch(HTTP_REQUEST, return_value=fake_response(text='{"a": [1, 2]}')):
            result = http.execute({"url": "https://api.example.com/x"}, {}, make_context())
        self.assertEqual(result.output["body"], {"a": [1, 2]})

    def test_non_json_response_kept_as_text(self):
        with patch(HTTP_REQUEST, return_value=fake_response(text="plain-text")):
            result = http.execute({"url": "https://api.example.com/x"}, {}, make_context())
        self.assertEqual(result.output["body"], "plain-text")

    def test_non_json_response_truncated_to_100k(self):
        with patch(HTTP_REQUEST, return_value=fake_response(text="x" * 100_005)):
            result = http.execute({"url": "https://api.example.com/x"}, {}, make_context())
        self.assertEqual(len(result.output["body"]), 100_000)

    def test_large_json_response_not_truncated(self):
        # 当前行为：截断只作用于非 JSON 文本；合法 JSON 会整段 json.loads（缺陷，见报告）。
        text = '{"data": "' + "x" * 150_000 + '"}'
        with patch(HTTP_REQUEST, return_value=fake_response(text=text)):
            result = http.execute({"url": "https://api.example.com/x"}, {}, make_context())
        self.assertEqual(len(result.output["body"]["data"]), 150_000)

    def test_empty_response_body_is_empty_dict(self):
        with patch(HTTP_REQUEST, return_value=fake_response(text="", status_code=204, reason=None)):
            result = http.execute({"url": "https://api.example.com/x"}, {}, make_context())
        self.assertEqual(result.output, {"status_code": 204, "body": {}, "reason": ""})

    def test_request_exception_raises_node_error(self):
        with patch(HTTP_REQUEST, side_effect=requests.ConnectionError("boom")):
            with self.assertRaisesMessage(NodeError, "HTTP 请求失败：boom"):
                http.execute({"url": "https://api.example.com/x"}, {}, make_context())

    def test_invalid_url_raises_node_error(self):
        for url in ("", "ftp://example.com/x", "api.example.com/x", "http://"):
            with self.subTest(url=url):
                with patch(HTTP_REQUEST) as mock_request:
                    with self.assertRaisesMessage(NodeError, "URL 必须是合法的 http/https 地址"):
                        http.execute({"url": url}, {}, make_context())
                mock_request.assert_not_called()

    def test_invalid_method_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "不支持的请求方法：HEAD"):
            http.execute(
                {"method": "HEAD", "url": "https://api.example.com/x"},
                {},
                make_context(),
            )

    def test_timeout_clamped_and_invalid_falls_back(self):
        cases = [
            ({"timeout": 0.2}, 1),
            ({"timeout": 120}, 60),
            ({"timeout": -3}, 1),
            ({"timeout": "30"}, 30),
            ({"timeout": "abc"}, 15),
            ({"timeout": None}, 15),
        ]
        for config, expected in cases:
            with self.subTest(config=config):
                with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
                    http.execute(
                        {"url": "https://api.example.com/x", **config},
                        {},
                        make_context(),
                    )
                self.assertEqual(mock_request.call_args.kwargs["timeout"], expected)

    def test_timeout_zero_falls_back_to_15_not_clamped_to_1(self):
        # 当前行为：0 为假值走 or 15 回退，而不是夹取到下限 1（缺陷，见报告）。
        with patch(HTTP_REQUEST, return_value=fake_response()) as mock_request:
            http.execute(
                {"url": "https://api.example.com/x", "timeout": 0},
                {},
                make_context(),
            )
        self.assertEqual(mock_request.call_args.kwargs["timeout"], 15)


# ==================== llm 节点 ====================
class LlmNodeTest(SimpleTestCase):
    def test_success_full_call(self):
        user = SimpleNamespace(pk=7)
        context = make_context(user=user)
        config = {
            "model_id": 7,
            "system_prompt": "你是助手",
            "prompt": "问题：{{input}}",
            "temperature": "0.3",
            "max_tokens": "256",
        }
        with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
            result = llm.execute(config, {"q": 1}, context)

        self.assertEqual(
            result.output,
            {
                "content": "你好",
                "usage": {"total_tokens": 3},
                "model": "gpt-4o",
                "provider": "openai",
            },
        )
        self.assertEqual(result.next_port, "out")
        self.assertEqual(result.logs, ["调用模型：gpt-4o"])
        mock_chat.assert_called_once()
        called_user, payload = mock_chat.call_args.args
        self.assertIs(called_user, user)
        self.assertEqual(payload["model_id"], 7)
        self.assertEqual(
            payload["messages"],
            [
                {"role": "system", "content": "你是助手"},
                {"role": "user", "content": '问题：{"q": 1}'},
            ],
        )
        self.assertEqual(payload["params"], {"temperature": 0.3, "max_tokens": 256})

    def test_llm_failure_raises_node_error_with_reason(self):
        with patch(
            LLM_CHAT,
            return_value=LLMResult(LLMStatus.PROVIDER_API_ERR, "令牌无效", None),
        ):
            with self.assertRaisesMessage(NodeError, "模型调用失败：令牌无效"):
                llm.execute({"model_id": 1}, {}, make_context())

    def test_missing_model_id_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "请配置有效的模型 ID"):
            llm.execute({}, {}, make_context())

    def test_non_integer_model_id_string_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "请配置有效的模型 ID"):
            llm.execute({"model_id": "abc"}, {}, make_context())

    @unittest.expectedFailure
    def test_non_integer_float_model_id_should_raise(self):
        """缺陷：int(1.5) 被静默截断为 1，非整数 model_id 未拒绝。"""
        with patch(LLM_CHAT, return_value=success_llm_result()):
            with self.assertRaises(NodeError):
                llm.execute({"model_id": 1.5}, {}, make_context())

    def test_temperature_conversion_and_optional(self):
        for temperature, expected in (("0.5", 0.5), (0, 0.0), ("0.0", 0.0)):
            with self.subTest(temperature=temperature):
                with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
                    llm.execute({"model_id": 1, "temperature": temperature}, {}, make_context())
                self.assertEqual(mock_chat.call_args.args[1]["params"]["temperature"], expected)

        for temperature in (None, ""):
            with self.subTest(temperature=temperature):
                with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
                    llm.execute({"model_id": 1, "temperature": temperature}, {}, make_context())
                self.assertNotIn("temperature", mock_chat.call_args.args[1]["params"])

    def test_temperature_invalid_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "temperature 必须是数字"):
            llm.execute({"model_id": 1, "temperature": "hot"}, {}, make_context())

    def test_max_tokens_conversion(self):
        with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
            llm.execute({"model_id": 1, "max_tokens": "128"}, {}, make_context())
        self.assertEqual(mock_chat.call_args.args[1]["params"]["max_tokens"], 128)

        with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
            llm.execute({"model_id": 1, "max_tokens": ""}, {}, make_context())
        self.assertNotIn("max_tokens", mock_chat.call_args.args[1]["params"])

    def test_max_tokens_invalid_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "max_tokens 必须是整数"):
            llm.execute({"model_id": 1, "max_tokens": "many"}, {}, make_context())

    def test_empty_system_prompt_not_added(self):
        for system_prompt in (None, "", "   "):
            with self.subTest(system_prompt=system_prompt):
                with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
                    llm.execute(
                        {"model_id": 1, "system_prompt": system_prompt},
                        {},
                        make_context(),
                    )
                messages = mock_chat.call_args.args[1]["messages"]
                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0]["role"], "user")

    def test_default_prompt_renders_input_json(self):
        with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
            llm.execute({"model_id": 1}, {"a": 1, "中文": "值"}, make_context())
        messages = mock_chat.call_args.args[1]["messages"]
        self.assertEqual(messages[-1], {"role": "user", "content": '{"a": 1, "中文": "值"}'})

    def test_custom_prompt_template(self):
        with patch(LLM_CHAT, return_value=success_llm_result()) as mock_chat:
            llm.execute({"model_id": 1, "prompt": "hi {{input}}"}, {"x": 2}, make_context())
        self.assertEqual(
            mock_chat.call_args.args[1]["messages"][-1],
            {"role": "user", "content": 'hi {"x": 2}'},
        )


# ==================== node_loader 注册表 ====================
class NodeLoaderTest(SimpleTestCase):
    def setUp(self):
        node_loader._cache.clear()

    def tearDown(self):
        node_loader._cache.clear()

    def test_list_node_files_sorted_and_no_base(self):
        types = node_loader.list_node_files()
        self.assertEqual(types, ["condition", "http", "llm", "start"])
        self.assertNotIn("base", types)
        self.assertNotIn("__init__", types)

    def test_list_node_files_does_not_import(self):
        with patch(
            "Workflow.node_loader.importlib.import_module",
            side_effect=AssertionError("list_node_files 不应导入节点模块"),
        ):
            self.assertEqual(node_loader.list_node_files(), ["condition", "http", "llm", "start"])

    def test_invalid_node_type_raises_node_error(self):
        for bad in ("", None, "Start", "1condition", "cond-ition", "a b", "a" * 65):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(NodeError, "非法节点类型"):
                    node_loader.get_node_module(bad)

    def test_unknown_node_type_raises_node_error(self):
        with self.assertRaisesMessage(NodeError, "节点类型不存在：not_exist"):
            node_loader.get_node_module("not_exist")

    def test_base_is_not_a_node_type(self):
        with self.assertRaisesMessage(NodeError, "节点类型不存在：base"):
            node_loader.get_node_module("base")

    def test_get_node_meta_fills_defaults(self):
        fake_module = SimpleNamespace(NODE_META={"name": "自定义"})
        with patch("Workflow.node_loader.get_node_module", return_value=fake_module):
            meta = node_loader.get_node_meta("fake_type")
        self.assertEqual(meta["name"], "自定义")
        self.assertEqual(meta["type"], "fake_type")
        self.assertEqual(meta["description"], "")
        self.assertEqual(meta["category"], "通用")
        self.assertEqual(meta["inputs"], [{"id": "in", "label": "输入"}])
        self.assertEqual(meta["outputs"], [{"id": "out", "label": "输出"}])
        self.assertEqual(meta["params"], [])

    def test_get_node_meta_without_node_meta(self):
        with patch("Workflow.node_loader.get_node_module", return_value=SimpleNamespace()):
            meta = node_loader.get_node_meta("bare")
        self.assertEqual(meta["name"], "bare")
        self.assertEqual(meta["type"], "bare")

    def test_get_node_meta_real_start(self):
        meta = node_loader.get_node_meta("start")
        self.assertEqual(meta["name"], "开始")
        self.assertEqual(meta["type"], "start")
        self.assertTrue(meta["params"])
        self.assertEqual(meta["outputs"], [{"id": "out", "label": "输出"}])

    def test_execute_node_normal(self):
        result = node_loader.execute_node("start", {}, {}, make_context())
        self.assertIsInstance(result, NodeResult)
        self.assertEqual(result.output, {"payload": {}})

    def test_execute_node_wraps_non_node_error(self):
        with patch("Workflow.node.condition.execute", side_effect=RuntimeError("boom")):
            with self.assertRaisesMessage(NodeError, "节点执行异常：boom"):
                node_loader.execute_node("condition", {}, {}, make_context())

    def test_execute_node_passes_node_error_through(self):
        with patch("Workflow.node.condition.execute", side_effect=NodeError("原样错误")):
            with self.assertRaises(NodeError) as ctx:
                node_loader.execute_node("condition", {}, {}, make_context())
        self.assertEqual(str(ctx.exception), "原样错误")

    def test_execute_node_requires_node_result(self):
        with patch("Workflow.node.start.execute", return_value={"bad": 1}):
            with self.assertRaisesMessage(NodeError, "节点 execute() 必须返回 NodeResult"):
                node_loader.execute_node("start", {}, {}, make_context())

    def test_get_node_module_cached(self):
        with patch(
            "Workflow.node_loader.importlib.import_module",
            wraps=importlib.import_module,
        ) as mock_import:
            first = node_loader.get_node_module("start")
            second = node_loader.get_node_module("start")
        self.assertIs(first, second)
        self.assertEqual(mock_import.call_count, 1)
        self.assertIs(node_loader._cache["start"], first)

    def test_get_node_module_returns_real_module(self):
        module = node_loader.get_node_module("condition")
        self.assertIs(module, condition)
        self.assertTrue(hasattr(module, "execute"))
        self.assertIs(node_loader._cache["condition"], condition)

    def test_node_context_fields(self):
        context = make_context()
        self.assertEqual(context.node_key, "node-1")
        self.assertEqual(context.workflow.pk, 2)


# ==================== base.render_template ====================
class RenderTemplateTest(SimpleTestCase):
    def test_empty_text(self):
        self.assertEqual(render_template("", {"a": 1}), "")
        self.assertEqual(render_template(None, {"a": 1}), "")

    def test_no_placeholder_unchanged(self):
        self.assertEqual(render_template("hello", {"a": 1}), "hello")

    def test_input_placeholder_replaced(self):
        self.assertEqual(render_template("{{input}}", {"a": 1}), '{"a": 1}')
        self.assertEqual(
            render_template("前缀 {{input}} 后缀", {"a": 1}),
            '前缀 {"a": 1} 后缀',
        )

    def test_none_input_renders_empty_object(self):
        self.assertEqual(render_template("{{input}}", None), "{}")

    def test_chinese_not_escaped(self):
        rendered = render_template("{{input}}", {"名字": "张三"})
        self.assertIn("张三", rendered)
        self.assertNotIn("\\u5f20", rendered)

    def test_non_serializable_uses_default_str(self):
        class Custom:
            def __str__(self):
                return "自定义对象"

        rendered = render_template("{{input}}", {"obj": Custom()})
        self.assertIn("自定义对象", rendered)

    def test_multiple_placeholders(self):
        self.assertEqual(
            render_template("{{input}}|{{input}}", {"a": 1}),
            '{"a": 1}|{"a": 1}',
        )
