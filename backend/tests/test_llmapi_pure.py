"""LLMapi 纯逻辑测试：加密、模型分类/参数规格、供应商协议适配器。

不访问数据库、不发起真实网络请求（requests 全部 mock）。
"""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests
from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings

from LLMapi import crypto, model_meta, templates
from LLMapi.adapters import (
    AnthropicAdapter,
    GeminiAdapter,
    OpenAIAdapter,
    ProviderAccess,
    ProviderError,
    _error_detail,
    _join,
    _request,
    get_adapter,
)
from LLMapi.result import LLMStatus
from tests.utils import reset_crypto_cache

OPENAI_ACCESS = ProviderAccess("openai", "https://api.example.com/v1", "sk-test-123")
ANTHROPIC_ACCESS = ProviderAccess("anthropic", "https://api.anthropic.com", "sk-ant-123")
GEMINI_ACCESS = ProviderAccess("gemini", "https://generativelanguage.googleapis.com", "gem-key-123")


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None, json_error=False):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else ""
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


def provider_error_code(exc_info) -> LLMStatus:
    return exc_info.exception.code


# ==================== crypto ====================
class CryptoTest(SimpleTestCase):
    def setUp(self):
        reset_crypto_cache()

    def tearDown(self):
        reset_crypto_cache()

    def test_encrypt_decrypt_roundtrip(self):
        token = crypto.encrypt_api_key("sk-1234567890abcdef")
        self.assertNotIn("sk-1234567890abcdef", token)
        self.assertEqual(crypto.decrypt_api_key(token), "sk-1234567890abcdef")

    def test_encrypt_empty_key_raises(self):
        with self.assertRaisesMessage(ValueError, "API Key 不能为空"):
            crypto.encrypt_api_key("   ")

    def test_mask_api_key(self):
        self.assertEqual(crypto.mask_api_key(""), "****")
        self.assertEqual(crypto.mask_api_key("short"), "****")
        self.assertEqual(crypto.mask_api_key("12345678"), "****")
        self.assertEqual(crypto.mask_api_key("123456789"), "123****6789")
        self.assertEqual(crypto.mask_api_key("sk-abcdefghijklmn"), "sk-****klmn")

    @override_settings(LLMAPI_ENCRYPTION_KEY="not-a-valid-fernet-key")
    def test_invalid_configured_key_raises(self):
        reset_crypto_cache()
        with self.assertRaisesMessage(ValueError, "LLMAPI_ENCRYPTION_KEY 格式无效"):
            crypto.encrypt_api_key("sk-test")

    @override_settings(LLMAPI_ENCRYPTION_KEY=Fernet.generate_key().decode())
    def test_wrong_key_cannot_decrypt(self):
        reset_crypto_cache()
        token = crypto.encrypt_api_key("sk-secret-value")
        reset_crypto_cache()
        with override_settings(LLMAPI_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            reset_crypto_cache()
            with self.assertRaisesMessage(ValueError, "解密失败"):
                crypto.decrypt_api_key(token)

    @override_settings(LLMAPI_ENCRYPTION_KEY="")
    def test_derive_key_from_secret_key(self):
        reset_crypto_cache()
        token = crypto.encrypt_api_key("sk-derived-key")
        reset_crypto_cache()
        self.assertEqual(crypto.decrypt_api_key(token), "sk-derived-key")


# ==================== templates ====================
class TemplatesTest(SimpleTestCase):
    def test_list_templates_structure(self):
        items = templates.list_templates()
        self.assertGreaterEqual(len(items), 10)
        codes = {item["code"] for item in items}
        for expected in ("openai", "deepseek", "anthropic", "gemini", "ollama"):
            self.assertIn(expected, codes)
        for item in items:
            self.assertIn(item["protocol"], {"openai", "anthropic", "gemini"})
            self.assertTrue(item["default_base_url"].startswith("http"))

    def test_get_template(self):
        self.assertEqual(templates.get_template("ollama").protocol, "openai")
        self.assertFalse(templates.get_template("ollama").requires_api_key)
        self.assertTrue(templates.get_template("openai").requires_api_key)
        self.assertIsNone(templates.get_template("not-exist"))
        self.assertIsNone(templates.get_template(""))


# ==================== model_meta ====================
class ClassifyModelTest(SimpleTestCase):
    def test_classify_by_model_id(self):
        cases = {
            "text-embedding-3-small": "embedding",
            "bge-m3": "embedding",
            "nomic-embed-text": "embedding",
            "gpt-image-1": "image",
            "flux-dev": "image",
            "whisper-1": "audio",
            "gpt-4o": "chat",
            "deepseek-chat": "chat",
            "some-random-model": "chat",
        }
        for model_id, expected in cases.items():
            self.assertEqual(model_meta.classify_model("openai", model_id), expected, model_id)

    @unittest.expectedFailure
    def test_classify_rerank_model(self):
        """已知缺陷：_EMBEDDING_KEYS 先于 _RERANK_KEYS 匹配，bge-reranker 被归成 embedding。"""
        self.assertEqual(model_meta.classify_model("openai", "bge-reranker-v2"), "rerank")

    def test_classify_gemini_uses_supported_methods(self):
        self.assertEqual(
            model_meta.classify_model(
                "gemini", "embedding-001", {"supportedGenerationMethods": ["embedContent"]}
            ),
            "embedding",
        )
        self.assertEqual(
            model_meta.classify_model(
                "gemini", "gemini-1.5-pro", {"supportedGenerationMethods": ["generateContent"]}
            ),
            "chat",
        )
        # 元信息缺失时回退到按名称匹配
        self.assertEqual(model_meta.classify_model("gemini", "text-embedding-004"), "embedding")


class ParamSpecTest(SimpleTestCase):
    @staticmethod
    def _spec_by_name(spec):
        return {item["name"]: item for item in spec}

    def test_openai_chat_spec(self):
        spec = self._spec_by_name(model_meta.build_param_spec("openai", "chat", "gpt-4o"))
        self.assertIn("temperature", spec)
        self.assertIn("top_p", spec)
        self.assertIn("max_tokens", spec)
        self.assertEqual(spec["max_tokens"]["maximum"], 16384)
        self.assertEqual(spec["temperature"]["maximum"], 2.0)
        self.assertEqual(spec["max_tokens"].get("default"), None)

    def test_anthropic_chat_spec_required_max_tokens(self):
        spec = self._spec_by_name(
            model_meta.build_param_spec("anthropic", "chat", "claude-3-7-sonnet")
        )
        self.assertTrue(spec["max_tokens"]["required"])
        self.assertEqual(spec["max_tokens"]["default"], 1024)
        self.assertEqual(spec["max_tokens"]["maximum"], 64000)
        self.assertEqual(spec["temperature"]["maximum"], 1.0)

    def test_gemini_chat_spec(self):
        spec = self._spec_by_name(model_meta.build_param_spec("gemini", "chat", "gemini-2.0-flash"))
        self.assertEqual(spec["temperature"]["maximum"], 2.0)
        self.assertEqual(spec["top_k"]["maximum"], 200)
        self.assertEqual(spec["max_tokens"]["default"], 2048)

    def test_embedding_specs(self):
        openai_spec = self._spec_by_name(
            model_meta.build_param_spec("openai", "embedding", "text-embedding-3-small")
        )
        self.assertIn("dimensions", openai_spec)
        self.assertIn("encoding_format", openai_spec)
        gemini_spec = self._spec_by_name(
            model_meta.build_param_spec("gemini", "embedding", "text-embedding-004")
        )
        self.assertIn("task_type", gemini_spec)

    def test_non_chat_categories_have_no_generation_params(self):
        for category in ("rerank", "image", "audio", "other"):
            self.assertEqual(model_meta.build_param_spec("openai", category, "x"), [], category)

    def test_max_output_tokens_heuristics(self):
        def max_tokens(model_id):
            return self._spec_by_name(model_meta.build_param_spec("openai", "chat", model_id))[
                "max_tokens"
            ]["maximum"]

        self.assertEqual(max_tokens("deepseek-chat"), 8192)
        self.assertEqual(max_tokens("deepseek-reasoner"), 100000)
        self.assertEqual(max_tokens("claude-3-5-sonnet"), 64000)
        self.assertEqual(max_tokens("qwen-max"), 16384)
        self.assertEqual(max_tokens("unknown-model"), 32768)


class ValidateMessagesTest(SimpleTestCase):
    def test_valid_messages(self):
        cleaned, errors = model_meta.validate_messages(
            [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            cleaned, [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
        )

    def test_content_list_allowed(self):
        _, errors = model_meta.validate_messages(
            [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        )
        self.assertEqual(errors, [])

    def test_invalid_messages(self):
        cases = [
            (None, "messages 必须是非空数组"),
            ([], "messages 必须是非空数组"),
            (["x"], "messages[0] 必须是对象"),
            ([{"role": "tool", "content": "x"}], "role 只能是"),
            ([{"role": "user", "content": 1}], "content 必须是字符串或数组"),
            ([{"role": "system", "content": "x"}], "至少需要一条 user 消息"),
        ]
        for value, expected in cases:
            _, errors = model_meta.validate_messages(value)
            self.assertTrue(any(expected in err for err in errors), (value, errors))


class ValidateEmbeddingInputTest(SimpleTestCase):
    def test_valid_input(self):
        self.assertEqual(model_meta.validate_embedding_input("hello"), (["hello"], []))
        self.assertEqual(model_meta.validate_embedding_input(["a", "b"]), (["a", "b"], []))

    def test_invalid_input(self):
        for value in ("", "  ", [], ["a", ""], [1], None):
            data, errors = model_meta.validate_embedding_input(value)
            self.assertEqual(data, [])
            self.assertTrue(errors, value)


class ValidateParamsTest(SimpleTestCase):
    def setUp(self):
        self.chat_spec = model_meta.build_param_spec("openai", "chat", "gpt-4o")

    def test_defaults_are_merged(self):
        merged, errors = model_meta.validate_params(self.chat_spec, None)
        self.assertEqual(errors, [])
        self.assertEqual(merged["temperature"], 1.0)
        self.assertEqual(merged["top_p"], 1.0)
        self.assertEqual(merged["n"], 1)
        self.assertNotIn("max_tokens", merged)

    def test_user_values_override_defaults(self):
        merged, errors = model_meta.validate_params(
            self.chat_spec, {"temperature": 0.2, "max_tokens": 100, "stop": "END"}
        )
        self.assertEqual(errors, [])
        self.assertEqual(merged["temperature"], 0.2)
        self.assertEqual(merged["max_tokens"], 100)
        self.assertEqual(merged["stop"], ["END"])

    def test_unknown_and_protected_params(self):
        merged, errors = model_meta.validate_params(
            self.chat_spec, {"foo": 1, "model": "x", "temperature": 0.5}
        )
        self.assertTrue(any("不支持的参数：foo" in e for e in errors))
        self.assertTrue(any("由系统控制" in e for e in errors))
        self.assertNotIn("model", merged)
        self.assertEqual(merged["temperature"], 0.5)

    def test_type_validation(self):
        cases = [
            ({"temperature": "hot"}, "类型应为 number"),
            ({"max_tokens": True}, "类型应为 integer"),
            ({"n": 1.5}, "类型应为 integer"),
            ({"stop": 123}, "类型应为 string_list"),
            ({"user": 123}, "类型应为 string"),
        ]
        for params, expected in cases:
            _, errors = model_meta.validate_params(self.chat_spec, params)
            self.assertTrue(any(expected in e for e in errors), (params, errors))

    def test_bounds_validation(self):
        cases = [
            ({"temperature": 3}, "不能大于 2.0"),
            ({"temperature": -1}, "不能小于 0.0"),
            ({"n": 0}, "不能小于 1"),
            ({"n": 17}, "不能大于 16"),
            ({"max_tokens": 0}, "不能小于 1"),
        ]
        for params, expected in cases:
            _, errors = model_meta.validate_params(self.chat_spec, params)
            self.assertTrue(any(expected in e for e in errors), (params, errors))

    def test_enum_validation(self):
        spec = model_meta.build_param_spec("openai", "embedding", "text-embedding-3-small")
        _, errors = model_meta.validate_params(spec, {"encoding_format": "json"})
        self.assertTrue(any("只能是" in e for e in errors))
        merged, errors = model_meta.validate_params(spec, {"encoding_format": "base64"})
        self.assertEqual(errors, [])
        self.assertEqual(merged["encoding_format"], "base64")

    def test_required_param(self):
        spec = [
            {"name": "must", "type": "integer", "required": True, "description": ""},
            {"name": "opt", "type": "string", "required": False, "description": ""},
        ]
        _, errors = model_meta.validate_params(spec, {"opt": "x"})
        self.assertTrue(any("缺少必填参数：must" in e for e in errors))
        merged, errors = model_meta.validate_params(spec, {"must": 1})
        self.assertEqual(errors, [])
        self.assertEqual(merged["must"], 1)

    def test_params_must_be_object(self):
        merged, errors = model_meta.validate_params(self.chat_spec, [1, 2])
        self.assertEqual(merged, {})
        self.assertIn("params 必须是 JSON 对象", errors)


# ==================== adapters ====================
class RequestHelperTest(SimpleTestCase):
    def test_join_url(self):
        self.assertEqual(_join("https://a.com/v1/", "/models"), "https://a.com/v1/models")
        self.assertEqual(_join("", "/models"), "/models")

    def test_error_detail_variants(self):
        self.assertEqual(
            _error_detail(FakeResponse(400, {"error": {"message": "bad key"}})), "bad key"
        )
        self.assertEqual(_error_detail(FakeResponse(400, {"error": "bad"})), "bad")
        self.assertEqual(
            _error_detail(FakeResponse(400, "plain text", text="plain text")), "plain text"
        )
        self.assertEqual(_error_detail(FakeResponse(400, None, text="", json_error=True)), "")

    def test_request_success(self):
        with patch(
            "LLMapi.adapters.requests.request",
            return_value=FakeResponse(200, {"ok": True}),
        ):
            self.assertEqual(_request("GET", "https://x/models"), {"ok": True})

    def test_request_maps_http_errors(self):
        cases = [
            (FakeResponse(401, {"error": "unauthorized"}), LLMStatus.PROVIDER_AUTH_ERR),
            (FakeResponse(403, {"error": "forbidden"}), LLMStatus.PROVIDER_AUTH_ERR),
            (
                FakeResponse(400, {"error": {"message": "invalid api key"}}),
                LLMStatus.PROVIDER_AUTH_ERR,
            ),
            (FakeResponse(400, {"error": {"message": "bad request"}}), LLMStatus.PROVIDER_API_ERR),
            (FakeResponse(500, {"error": "boom"}), LLMStatus.PROVIDER_API_ERR),
            (FakeResponse(200, None, json_error=True), LLMStatus.PROVIDER_API_ERR),
        ]
        for response, expected in cases:
            with patch("LLMapi.adapters.requests.request", return_value=response):
                with self.assertRaises(ProviderError) as ctx:
                    _request("GET", "https://x/models")
                self.assertEqual(ctx.exception.code, expected, response.status_code)

    def test_request_network_errors(self):
        for exc, expected in (
            (requests.Timeout("timeout"), LLMStatus.PROVIDER_UNREACHABLE),
            (requests.ConnectionError("down"), LLMStatus.PROVIDER_UNREACHABLE),
        ):
            with patch("LLMapi.adapters.requests.request", side_effect=exc):
                with self.assertRaises(ProviderError) as ctx:
                    _request("GET", "https://x/models")
                self.assertEqual(ctx.exception.code, expected)

    def test_request_wraps_unexpected_json_type(self):
        with patch("LLMapi.adapters.requests.request", return_value=FakeResponse(200, ["a"])):
            self.assertEqual(_request("GET", "https://x/models"), ["a"])


class OpenAIAccessAdapterTest(SimpleTestCase):
    def test_list_models_data_object(self):
        adapter = OpenAIAdapter()
        captured = {}

        def fake_request(method, url, **kwargs):
            captured.update(method=method, url=url, kwargs=kwargs)
            return FakeResponse(
                200,
                {
                    "data": [
                        {"id": "gpt-4o", "name": "GPT-4o"},
                        {"id": "text-embedding-3-small"},
                        {"no_id": True},
                        "bad-item",
                    ]
                },
            )

        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            models = adapter.list_models(OPENAI_ACCESS)
        self.assertEqual([m["model_id"] for m in models], ["gpt-4o", "text-embedding-3-small"])
        self.assertEqual(models[0]["display_name"], "GPT-4o")
        self.assertEqual(captured["url"], "https://api.example.com/v1/models")
        self.assertEqual(captured["kwargs"]["headers"]["Authorization"], "Bearer sk-test-123")

    @override_settings(LLMAPI_MAX_MODELS=2)
    def test_list_models_respects_max(self):
        adapter = OpenAIAdapter()
        with patch(
            "LLMapi.adapters.requests.request",
            return_value=FakeResponse(200, {"data": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}]}),
        ):
            models = adapter.list_models(OPENAI_ACCESS)
        self.assertEqual([m["model_id"] for m in models], ["m1", "m2"])

    def test_chat_parses_content_and_usage(self):
        adapter = OpenAIAdapter()
        captured = {}

        def fake_request(method, url, **kwargs):
            captured.update(url=url, body=kwargs.get("json"))
            return FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "text", "text": "he"},
                                    {"type": "text", "text": "llo"},
                                ]
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                },
            )

        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            result = adapter.chat(
                OPENAI_ACCESS, "gpt-4o", [{"role": "user", "content": "hi"}], {"temperature": 0.5}
            )
        self.assertEqual(captured["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(captured["body"]["model"], "gpt-4o")
        self.assertEqual(captured["body"]["temperature"], 0.5)
        self.assertEqual(result["content"], "hello")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["usage"]["total_tokens"], 5)

    def test_embeddings_input_shape_and_ordering(self):
        adapter = OpenAIAdapter()
        captured = {}

        def fake_request(method, url, **kwargs):
            captured["body"] = kwargs.get("json")
            return FakeResponse(
                200,
                {
                    "data": [
                        {"index": 1, "embedding": [0.3, 0.4]},
                        {"index": 0, "embedding": [0.1, 0.2]},
                    ]
                },
            )

        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            single = adapter.embeddings(OPENAI_ACCESS, "text-embedding-3-small", ["one"], {})
        self.assertEqual(captured["body"]["input"], "one")
        self.assertEqual(single["embeddings"], [[0.1, 0.2], [0.3, 0.4]])
        self.assertEqual(single["dimensions"], 2)

        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            adapter.embeddings(OPENAI_ACCESS, "text-embedding-3-small", ["a", "b"], {})
        self.assertEqual(captured["body"]["input"], ["a", "b"])


class AnthropicAdapterTest(SimpleTestCase):
    def test_api_base_appends_v1(self):
        self.assertEqual(
            AnthropicAdapter()._api_base(ANTHROPIC_ACCESS), "https://api.anthropic.com/v1"
        )
        self.assertEqual(
            AnthropicAdapter()._api_base(ProviderAccess("anthropic", "https://x/v1", "k")),
            "https://x/v1",
        )

    def test_list_models_paginates(self):
        adapter = AnthropicAdapter()
        responses = [
            FakeResponse(
                200, {"data": [{"id": "claude-a"}], "has_more": True, "last_id": "claude-a"}
            ),
            FakeResponse(
                200, {"data": [{"id": "claude-b", "display_name": "Claude B"}], "has_more": False}
            ),
        ]
        mock_request = Mock(side_effect=responses)
        with patch("LLMapi.adapters.requests.request", mock_request):
            models = adapter.list_models(ANTHROPIC_ACCESS)
        self.assertEqual([m["model_id"] for m in models], ["claude-a", "claude-b"])
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(mock_request.call_args.kwargs["params"]["after_id"], "claude-a")

    def test_chat_builds_body_and_parses_blocks(self):
        adapter = AnthropicAdapter()
        captured = {}

        def fake_request(method, url, **kwargs):
            captured.update(url=url, body=kwargs.get("json"), headers=kwargs.get("headers"))
            return FakeResponse(
                200,
                {
                    "content": [
                        {"type": "text", "text": "Hel"},
                        {"type": "text", "text": "lo"},
                        {"type": "tool_use"},
                    ],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 4, "output_tokens": 2},
                },
            )

        messages = [
            {"role": "system", "content": "be nice"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            result = adapter.chat(
                ANTHROPIC_ACCESS, "claude-3", messages, {"temperature": 0.2, "stop": ["END"]}
            )
        self.assertEqual(captured["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(captured["body"]["system"], "be nice")
        self.assertEqual(
            captured["body"]["messages"],
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )
        self.assertEqual(captured["body"]["max_tokens"], 1024)
        self.assertEqual(captured["body"]["stop_sequences"], ["END"])
        self.assertEqual(captured["headers"]["x-api-key"], "sk-ant-123")
        self.assertEqual(result["content"], "Hello")
        self.assertEqual(result["usage"]["prompt_tokens"], 4)

    def test_chat_requires_conversation(self):
        with self.assertRaises(ProviderError) as ctx:
            AnthropicAdapter().chat(
                ANTHROPIC_ACCESS, "claude", [{"role": "system", "content": "x"}], {}
            )
        self.assertEqual(ctx.exception.code, LLMStatus.PARAM_ERR)

    def test_embeddings_unsupported(self):
        with self.assertRaises(ProviderError) as ctx:
            AnthropicAdapter().embeddings(ANTHROPIC_ACCESS, "claude", ["a"], {})
        self.assertEqual(ctx.exception.code, LLMStatus.MODEL_UNSUPPORTED)


class GeminiAdapterTest(SimpleTestCase):
    def test_api_base_appends_v1beta(self):
        self.assertEqual(
            GeminiAdapter()._api_base(GEMINI_ACCESS),
            "https://generativelanguage.googleapis.com/v1beta",
        )

    def test_list_models_strips_prefix_and_paginates(self):
        adapter = GeminiAdapter()
        responses = [
            FakeResponse(
                200,
                {
                    "models": [
                        {"name": "models/gemini-2.0-flash", "displayName": "Gemini 2.0 Flash"},
                        {"name": "models/text-embedding-004"},
                    ],
                    "nextPageToken": "page-2",
                },
            ),
            FakeResponse(200, {"models": [{"name": "models/gemini-2.5-pro"}]}),
        ]
        mock_request = Mock(side_effect=responses)
        with patch("LLMapi.adapters.requests.request", mock_request):
            models = adapter.list_models(GEMINI_ACCESS)
        self.assertEqual(
            [m["model_id"] for m in models],
            ["gemini-2.0-flash", "text-embedding-004", "gemini-2.5-pro"],
        )
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(mock_request.call_args.kwargs["params"]["pageToken"], "page-2")
        self.assertEqual(mock_request.call_args.kwargs["params"]["key"], "gem-key-123")

    def test_chat_builds_body(self):
        adapter = GeminiAdapter()
        captured = {}

        def fake_request(method, url, **kwargs):
            captured.update(url=url, body=kwargs.get("json"), params=kwargs.get("params"))
            return FakeResponse(
                200,
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "Hello"}]}, "finishReason": "STOP"}
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 3,
                        "candidatesTokenCount": 2,
                        "totalTokenCount": 5,
                    },
                },
            )

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            result = adapter.chat(
                GEMINI_ACCESS,
                "gemini-2.0-flash",
                messages,
                {"temperature": 0.5, "max_tokens": 100, "stop": ["X"]},
            )
        self.assertEqual(
            captured["url"],
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        )
        self.assertEqual(captured["params"]["key"], "gem-key-123")
        self.assertEqual(captured["body"]["systemInstruction"], {"parts": [{"text": "sys"}]})
        self.assertEqual(
            captured["body"]["contents"][0], {"role": "user", "parts": [{"text": "hi"}]}
        )
        self.assertEqual(
            captured["body"]["contents"][1], {"role": "model", "parts": [{"text": "hello"}]}
        )
        self.assertEqual(captured["body"]["generationConfig"]["maxOutputTokens"], 100)
        self.assertEqual(result["content"], "Hello")
        self.assertEqual(result["finish_reason"], "STOP")
        self.assertEqual(result["usage"]["total_tokens"], 5)

    def test_embeddings(self):
        adapter = GeminiAdapter()
        captured = {}

        def fake_request(method, url, **kwargs):
            captured.update(url=url, body=kwargs.get("json"))
            return FakeResponse(200, {"embeddings": [{"values": [0.1, 0.2]}, {"values": [0.3]}]})

        with patch("LLMapi.adapters.requests.request", side_effect=fake_request):
            result = adapter.embeddings(GEMINI_ACCESS, "text-embedding-004", ["a", "b"], {})
        self.assertEqual(
            captured["url"],
            "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents",
        )
        self.assertEqual(captured["body"]["requests"][0]["model"], "models/text-embedding-004")
        self.assertEqual(result["embeddings"], [[0.1, 0.2], [0.3]])
        self.assertEqual(result["dimensions"], 2)


class AdapterRegistryTest(SimpleTestCase):
    def test_get_adapter(self):
        self.assertIsInstance(get_adapter("openai"), OpenAIAdapter)
        self.assertIsInstance(get_adapter("anthropic"), AnthropicAdapter)
        self.assertIsInstance(get_adapter("gemini"), GeminiAdapter)
        with self.assertRaises(ProviderError) as ctx:
            get_adapter("unknown")
        self.assertEqual(ctx.exception.code, LLMStatus.PARAM_ERR)
