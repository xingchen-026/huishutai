"""LLMapi HTTP 接口测试：认证、权限隔离、状态码与统一响应结构。"""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from LLMapi.adapters import ProviderError
from LLMapi.result import LLMStatus
from sqldb.models import LLMModel, LLMProviderConfig
from tests.utils import api, make_model, make_provider, make_user

CHAT_MODELS = [
    {"model_id": "gpt-4o", "display_name": "GPT-4o", "raw": {}},
    {"model_id": "text-embedding-3-small", "display_name": "", "raw": {}},
]


class FakeAdapter:
    def __init__(self, models=None, chat_error=None, embed_error=None):
        self.models = models if models is not None else []
        self.chat_error = chat_error
        self.embed_error = embed_error
        self.calls = []

    def list_models(self, access):
        self.calls.append(("list_models", access))
        return self.models

    def chat(self, access, model_id, messages, params):
        self.calls.append(("chat", access, model_id, messages, params))
        if self.chat_error:
            raise self.chat_error
        return {
            "content": "API 调用成功",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            "raw": {"ok": True},
        }

    def embeddings(self, access, model_id, inputs, params):
        self.calls.append(("embeddings", access, model_id, inputs, params))
        if self.embed_error:
            raise self.embed_error
        return {"embeddings": [[0.1, 0.2]], "dimensions": 2, "usage": {}, "raw": {}}


def patch_adapter(fake):
    return patch("LLMapi.services.get_adapter", return_value=fake)


def assert_api_success(testcase, response, expected_http=200):
    testcase.assertEqual(response.status_code, expected_http, response.content[:300])
    testcase.assertEqual(response["Content-Type"].split(";")[0], "application/json")
    body = response.json()
    testcase.assertIsInstance(body, dict)
    testcase.assertIn("code", body)
    testcase.assertIn("message", body)
    testcase.assertIn("data", body)
    testcase.assertIsInstance(body["code"], int)
    return body


class LLMapiAuthTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.provider = make_provider(self.user)
        self.model = make_model(self.provider, model_id="gpt-4o")

    def test_all_endpoints_require_login(self):
        endpoints = [
            ("GET", "/llm/provider-templates/"),
            ("GET", "/llm/providers/"),
            ("POST", "/llm/providers/"),
            ("GET", f"/llm/providers/{self.provider.pk}/"),
            ("PATCH", f"/llm/providers/{self.provider.pk}/"),
            ("DELETE", f"/llm/providers/{self.provider.pk}/"),
            ("POST", f"/llm/providers/{self.provider.pk}/refresh-models/"),
            ("GET", f"/llm/providers/{self.provider.pk}/models/"),
            ("POST", f"/llm/providers/{self.provider.pk}/models/"),
            ("GET", "/llm/models/"),
            ("PATCH", f"/llm/models/{self.model.pk}/"),
            ("DELETE", f"/llm/models/{self.model.pk}/"),
            ("POST", "/llm/chat/"),
            ("POST", "/llm/embeddings/"),
        ]
        for method, path in endpoints:
            response = getattr(self.client, method.lower())(path)
            self.assertEqual(response.status_code, 401, (method, path, response.content[:120]))


class ProviderTemplatesApiTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")

    def test_provider_templates(self):
        response = api(self.client, "get", "/llm/provider-templates/", self.user)
        body = assert_api_success(self, response)
        self.assertEqual(body["code"], 0)
        self.assertIn("templates", body["data"])
        self.assertIn("categories", body["data"])
        self.assertGreaterEqual(len(body["data"]["templates"]), 10)
        self.assertIn("chat", [item["code"] for item in body["data"]["categories"]])


class ProviderApiTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")

    def test_create_provider_success_and_list(self):
        fake = FakeAdapter(models=CHAT_MODELS)
        with patch_adapter(fake):
            response = api(
                self.client,
                "post",
                "/llm/providers/",
                self.user,
                {
                    "template_code": "openai",
                    "name": "API 创建的配置",
                    "base_url": "https://api.example.com/v1",
                    "api_key": "sk-api-key-123456",
                },
            )
        body = assert_api_success(self, response)
        provider_data = body["data"]["provider"]
        self.assertEqual(provider_data["name"], "API 创建的配置")
        self.assertEqual(provider_data["api_key_masked"], "sk-****3456")
        self.assertEqual(body["data"]["model_sync"]["count"], 2)
        provider = LLMProviderConfig.objects.get(pk=provider_data["id"])
        self.assertEqual(provider.user_id, self.user.pk)

        listing = assert_api_success(self, api(self.client, "get", "/llm/providers/", self.user))
        self.assertEqual(listing["data"]["total"], 1)
        self.assertEqual(listing["data"]["providers"][0]["model_count"], 2)

    def test_create_provider_validation_errors(self):
        cases = [
            ({"template_code": "nope"}, 400, "模板不存在"),
            ({"template_code": "openai"}, 400, "API Key"),
            (
                {"template_code": "openai", "api_key": "sk-x-12345678", "base_url": "not-a-url"},
                400,
                "http",
            ),
        ]
        for payload, status, message in cases:
            response = api(self.client, "post", "/llm/providers/", self.user, payload)
            self.assertEqual(response.status_code, status, payload)
            self.assertIn(message, response.json()["message"])
        self.assertEqual(LLMProviderConfig.objects.count(), 0)

    def test_create_provider_duplicate_name(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            api(
                self.client,
                "post",
                "/llm/providers/",
                self.user,
                {"template_code": "openai", "name": "dup", "api_key": "sk-x-12345678"},
            )
            second = api(
                self.client,
                "post",
                "/llm/providers/",
                self.user,
                {"template_code": "openai", "name": "dup", "api_key": "sk-x-12345678"},
            )
        self.assertEqual(second.status_code, 400)
        self.assertIn("已存在", second.json()["message"])

    def test_create_provider_auth_error_returns_400(self):
        fake = FakeAdapter()
        fake.list_models = lambda access: (_ for _ in ()).throw(
            ProviderError(LLMStatus.PROVIDER_AUTH_ERR, "bad key", upstream_status=401)
        )
        with patch_adapter(fake):
            response = api(
                self.client,
                "post",
                "/llm/providers/",
                self.user,
                {"template_code": "openai", "api_key": "sk-bad-123456"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], int(LLMStatus.PROVIDER_AUTH_ERR))
        self.assertEqual(LLMProviderConfig.objects.count(), 0)

    def test_create_provider_unreachable_still_returns_200(self):
        class FailingAdapter(FakeAdapter):
            def list_models(self, access):
                raise ProviderError(LLMStatus.PROVIDER_UNREACHABLE, "down")

        with patch_adapter(FailingAdapter()):
            response = api(
                self.client,
                "post",
                "/llm/providers/",
                self.user,
                {"template_code": "openai", "api_key": "sk-x-12345678"},
            )
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["model_sync"]["status"], "unavailable")
        self.assertEqual(LLMProviderConfig.objects.count(), 1)

    def test_provider_detail_patch_delete(self):
        provider = make_provider(self.user, name="old")
        response = api(self.client, "get", f"/llm/providers/{provider.pk}/", self.user)
        assert_api_success(self, response)

        response = api(
            self.client,
            "patch",
            f"/llm/providers/{provider.pk}/",
            self.user,
            {"name": "new", "enabled": False},
        )
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["provider"]["name"], "new")
        self.assertFalse(body["data"]["provider"]["enabled"])

        response = api(self.client, "delete", f"/llm/providers/{provider.pk}/", self.user)
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["id"], provider.pk)
        self.assertFalse(LLMProviderConfig.objects.filter(pk=provider.pk).exists())

    def test_provider_isolation(self):
        provider = make_provider(self.user)
        responses = [
            api(self.client, "get", f"/llm/providers/{provider.pk}/", self.other),
            api(self.client, "patch", f"/llm/providers/{provider.pk}/", self.other, {"name": "x"}),
            api(self.client, "delete", f"/llm/providers/{provider.pk}/", self.other),
            api(self.client, "post", f"/llm/providers/{provider.pk}/refresh-models/", self.other),
            api(self.client, "get", f"/llm/providers/{provider.pk}/models/", self.other),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 404, response.content[:200])
            self.assertEqual(response.json()["code"], int(LLMStatus.NOT_FOUND))

    def test_refresh_models_api(self):
        provider = make_provider(self.user)
        fake = FakeAdapter(models=[{"model_id": "gpt-4o", "display_name": "", "raw": {}}])
        with patch_adapter(fake):
            response = api(
                self.client, "post", f"/llm/providers/{provider.pk}/refresh-models/", self.user
            )
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["count"], 1)
        self.assertTrue(LLMModel.objects.filter(provider=provider, model_id="gpt-4o").exists())

    def test_refresh_models_unreachable_maps_502(self):
        provider = make_provider(self.user)

        class FailingAdapter(FakeAdapter):
            def list_models(self, access):
                raise ProviderError(LLMStatus.PROVIDER_UNREACHABLE, "down")

        with patch_adapter(FailingAdapter()):
            response = api(
                self.client, "post", f"/llm/providers/{provider.pk}/refresh-models/", self.user
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], int(LLMStatus.PROVIDER_UNREACHABLE))

    def test_refresh_models_auth_error_maps_400(self):
        provider = make_provider(self.user)

        class FailingAdapter(FakeAdapter):
            def list_models(self, access):
                raise ProviderError(LLMStatus.PROVIDER_AUTH_ERR, "bad", upstream_status=401)

        with patch_adapter(FailingAdapter()):
            response = api(
                self.client, "post", f"/llm/providers/{provider.pk}/refresh-models/", self.user
            )
        self.assertEqual(response.status_code, 400)


class ModelApiTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")
        self.provider = make_provider(self.user)
        self.chat_model = make_model(self.provider, model_id="gpt-4o", category="chat")
        self.embed_model = make_model(self.provider, model_id="embed", category="embedding")

    def test_provider_models_list_and_add_manual(self):
        response = api(self.client, "get", f"/llm/providers/{self.provider.pk}/models/", self.user)
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["total"], 2)

        response = api(
            self.client,
            "post",
            f"/llm/providers/{self.provider.pk}/models/",
            self.user,
            {"model_id": "whisper-1"},
        )
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["model"]["category"], "audio")
        self.assertEqual(body["data"]["model"]["source"], "manual")

        duplicate = api(
            self.client,
            "post",
            f"/llm/providers/{self.provider.pk}/models/",
            self.user,
            {"model_id": "whisper-1"},
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_models_grouping_and_filters(self):
        response = api(self.client, "get", "/llm/models/", self.user)
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["total"], 2)
        codes = [group["category"] for group in body["data"]["groups"]]
        self.assertIn("chat", codes)
        self.assertIn("embedding", codes)

        response = api(self.client, "get", "/llm/models/?category=chat", self.user)
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["total"], 1)

        response = api(self.client, "get", "/llm/models/?category=invalid", self.user)
        self.assertEqual(response.status_code, 400)

    def test_models_isolation(self):
        response = api(self.client, "get", "/llm/models/", self.other)
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["total"], 0)

    def test_model_update_and_delete(self):
        response = api(
            self.client,
            "patch",
            f"/llm/models/{self.chat_model.pk}/",
            self.user,
            {"enabled": False, "display_name": "别名"},
        )
        body = assert_api_success(self, response)
        self.assertFalse(body["data"]["model"]["enabled"])
        self.assertEqual(body["data"]["model"]["display_name"], "别名")

        response = api(self.client, "delete", f"/llm/models/{self.chat_model.pk}/", self.user)
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["id"], self.chat_model.pk)
        self.assertFalse(LLMModel.objects.filter(pk=self.chat_model.pk).exists())

    def test_model_other_user_not_found(self):
        for method in ("patch", "delete"):
            response = api(
                self.client,
                method,
                f"/llm/models/{self.chat_model.pk}/",
                self.other,
                {"enabled": True} if method == "patch" else None,
            )
            self.assertEqual(response.status_code, 404)


class ChatApiTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")
        self.provider = make_provider(self.user)
        self.chat_model = make_model(self.provider, model_id="gpt-4o", category="chat")
        self.embed_model = make_model(self.provider, model_id="embed", category="embedding")
        self.messages = [{"role": "user", "content": "你好"}]

    def test_chat_success(self):
        fake = FakeAdapter()
        with patch_adapter(fake):
            response = api(
                self.client,
                "post",
                "/llm/chat/",
                self.user,
                {
                    "model_id": self.chat_model.pk,
                    "messages": self.messages,
                    "params": {"temperature": 0.2},
                },
            )
        body = assert_api_success(self, response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["content"], "API 调用成功")
        self.assertEqual(body["data"]["model"], "gpt-4o")
        self.assertEqual(body["data"]["usage"]["total_tokens"], 5)

    def test_chat_validation_errors(self):
        cases = [
            ({}, 400),
            ({"model_id": 999999, "messages": self.messages}, 404),
            ({"model_id": self.chat_model.pk, "messages": []}, 400),
            (
                {"model_id": self.chat_model.pk, "messages": self.messages, "params": {"bad": 1}},
                400,
            ),
            ({"model_id": self.embed_model.pk, "messages": self.messages}, 400),
        ]
        for payload, status in cases:
            response = api(self.client, "post", "/llm/chat/", self.user, payload)
            self.assertEqual(response.status_code, status, payload)
            self.assertIn("code", response.json())

    def test_chat_other_user_model_not_found(self):
        response = api(
            self.client,
            "post",
            "/llm/chat/",
            self.other,
            {"model_id": self.chat_model.pk, "messages": self.messages},
        )
        self.assertEqual(response.status_code, 404)

    def test_chat_provider_unreachable_maps_502(self):
        fake = FakeAdapter(chat_error=ProviderError(LLMStatus.PROVIDER_UNREACHABLE, "down"))
        with patch_adapter(fake):
            response = api(
                self.client,
                "post",
                "/llm/chat/",
                self.user,
                {"model_id": self.chat_model.pk, "messages": self.messages},
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], int(LLMStatus.PROVIDER_UNREACHABLE))

    def test_embeddings_success(self):
        fake = FakeAdapter()
        with patch_adapter(fake):
            response = api(
                self.client,
                "post",
                "/llm/embeddings/",
                self.user,
                {"model_id": self.embed_model.pk, "input": "hello"},
            )
        body = assert_api_success(self, response)
        self.assertEqual(body["data"]["dimensions"], 2)
        self.assertEqual(body["data"]["embeddings"], [[0.1, 0.2]])

    def test_embeddings_validation_errors(self):
        cases = [
            ({"model_id": self.chat_model.pk, "input": "x"}, 400),
            ({"model_id": self.embed_model.pk, "input": ""}, 400),
            ({"model_id": self.embed_model.pk, "input": ["ok", ""]}, 400),
            (
                {
                    "model_id": self.embed_model.pk,
                    "input": "x",
                    "params": {"encoding_format": "bad"},
                },
                400,
            ),
        ]
        for payload, status in cases:
            response = api(self.client, "post", "/llm/embeddings/", self.user, payload)
            self.assertEqual(response.status_code, status, payload)

    def test_api_key_never_returned_in_plaintext(self):
        fake = FakeAdapter()
        with patch_adapter(fake):
            create = api(
                self.client,
                "post",
                "/llm/providers/",
                self.user,
                {
                    "template_code": "openai",
                    "name": "secret-test",
                    "api_key": "sk-very-secret-key-123456",
                },
            )
            self.assertEqual(create.status_code, 200, create.content[:200])
            listing = api(self.client, "get", "/llm/providers/", self.user)
        self.assertNotIn("sk-very-secret-key-123456", create.content.decode("utf-8"))
        self.assertNotIn("sk-very-secret-key-123456", listing.content.decode("utf-8"))
        self.assertIn("sk-****3456", listing.content.decode("utf-8"))
