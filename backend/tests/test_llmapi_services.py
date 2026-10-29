"""LLMapi 业务层测试：供应商配置、模型同步、统一调用网关（DB 用 SQLite，供应商 mock）。"""
from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from LLMapi import services
from LLMapi.adapters import ProviderAccess, ProviderError
from LLMapi.model_meta import build_param_spec
from LLMapi.result import LLMStatus
from sqldb.models import LLMModel, LLMProviderConfig
from tests.utils import make_model, make_provider, make_user

CHAT_MODELS = [
    {"model_id": "gpt-4o", "display_name": "GPT-4o", "raw": {"id": "gpt-4o"}},
    {"model_id": "text-embedding-3-small", "display_name": "", "raw": {}},
]


class FakeAdapter:
    """记录调用参数、返回预设结果的供应商适配器替身。"""

    def __init__(
        self,
        models=None,
        chat_result=None,
        embed_result=None,
        list_error=None,
        chat_error=None,
        embed_error=None,
    ):
        self.models = models if models is not None else []
        self.chat_result = chat_result or {
            "content": "你好",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            "raw": {"id": "resp"},
        }
        self.embed_result = embed_result or {
            "embeddings": [[0.1, 0.2]],
            "dimensions": 2,
            "usage": {},
            "raw": {},
        }
        self.list_error = list_error
        self.chat_error = chat_error
        self.embed_error = embed_error
        self.calls: list[tuple] = []

    def list_models(self, access):
        self.calls.append(("list_models", access))
        if self.list_error:
            raise self.list_error
        return self.models

    def chat(self, access, model_id, messages, params):
        self.calls.append(("chat", access, model_id, messages, params))
        if self.chat_error:
            raise self.chat_error
        return self.chat_result

    def embeddings(self, access, model_id, inputs, params):
        self.calls.append(("embeddings", access, model_id, inputs, params))
        if self.embed_error:
            raise self.embed_error
        return self.embed_result


def patch_adapter(fake: FakeAdapter):
    return patch("LLMapi.services.get_adapter", return_value=fake)


class CreateProviderTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")

    def test_create_provider_syncs_models_and_encrypts_key(self):
        fake = FakeAdapter(models=CHAT_MODELS)
        with patch_adapter(fake):
            result = services.create_provider(
                self.user,
                {
                    "template_code": "openai",
                    "name": "我的配置",
                    "base_url": "https://api.example.com/v1",
                    "api_key": "sk-abcdef123456",
                },
            )
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["model_sync"], {"status": "ok", "count": 2, "message": "模型列表已同步"})
        provider = LLMProviderConfig.objects.get(user=self.user)
        self.assertEqual(provider.name, "我的配置")
        self.assertEqual(provider.protocol, "openai")
        self.assertNotIn("sk-abcdef123456", provider.api_key_encrypted)
        self.assertEqual(provider.api_key_masked, "sk-****3456")
        self.assertEqual(LLMProviderConfig.objects.count(), 1)
        self.assertEqual(LLMModel.objects.filter(provider=provider).count(), 2)
        chat = LLMModel.objects.get(provider=provider, model_id="gpt-4o")
        embed = LLMModel.objects.get(provider=provider, model_id="text-embedding-3-small")
        self.assertEqual(chat.category, "chat")
        self.assertEqual(embed.category, "embedding")
        self.assertEqual(chat.source, "auto")
        self.assertTrue(chat.param_spec)
        self.assertEqual(provider.last_sync_error, "")
        self.assertNotIn("sk-abcdef123456", str(result.data))

    @unittest.expectedFailure
    def test_create_provider_should_record_last_synced_at(self):
        """已知缺陷：create_provider 成功同步模型后未写入 last_synced_at。"""
        fake = FakeAdapter(models=CHAT_MODELS)
        with patch_adapter(fake):
            services.create_provider(
                self.user,
                {"template_code": "openai", "api_key": "sk-abcdef123456"},
            )
        provider = LLMProviderConfig.objects.get(user=self.user)
        self.assertIsNotNone(provider.last_synced_at)

    def test_create_provider_defaults_name_to_template_name(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.create_provider(
                self.user, {"template_code": "deepseek", "api_key": "sk-x-12345678"}
            )
        self.assertTrue(result.success)
        self.assertEqual(LLMProviderConfig.objects.get(user=self.user).name, "DeepSeek")

    def test_create_ollama_provider_without_api_key(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.create_provider(self.user, {"template_code": "ollama"})
        self.assertTrue(result.success, result.message)
        provider = LLMProviderConfig.objects.get(user=self.user)
        self.assertEqual(provider.api_key_encrypted, "")
        self.assertEqual(provider.api_key_masked, "")
        self.assertIn("未返回模型列表", str(result.data["model_sync"]["message"]))

    def test_unknown_template(self):
        result = services.create_provider(self.user, {"template_code": "nope"})
        self.assertEqual(result.code, LLMStatus.PARAM_ERR)
        self.assertIn("模板不存在", result.message)
        self.assertEqual(LLMProviderConfig.objects.count(), 0)

    def test_required_api_key(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake) as patched:
            result = services.create_provider(self.user, {"template_code": "openai"})
        self.assertEqual(result.code, LLMStatus.PARAM_ERR)
        self.assertIn("API Key", result.message)
        patched.assert_not_called()
        self.assertEqual(LLMProviderConfig.objects.count(), 0)

    def test_invalid_base_urls(self):
        cases = [
            "ftp://example.com/api",
            "example.com/api",
            "http://user:pass@example.com/api",
        ]
        with patch_adapter(FakeAdapter(models=[])):
            for base_url in cases:
                result = services.create_provider(
                    self.user,
                    {"template_code": "openai", "api_key": "sk-x-12345678", "base_url": base_url},
                )
                self.assertEqual(result.code, LLMStatus.PARAM_ERR, base_url)

    def test_empty_base_url_falls_back_to_template_default(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.create_provider(
                self.user,
                {"template_code": "openai", "api_key": "sk-x-12345678", "base_url": ""},
            )
        self.assertTrue(result.success, result.message)
        provider = LLMProviderConfig.objects.get(user=self.user)
        self.assertEqual(provider.base_url, "https://api.openai.com/v1")

    @override_settings(LLMAPI_ALLOW_PRIVATE_BASE_URL=False)
    def test_private_base_url_rejected_when_disabled(self):
        for base_url in (
            "http://127.0.0.1:11434/v1",
            "http://localhost:11434/v1",
            "http://10.0.0.8/v1",
            "http://169.254.169.254/latest",
        ):
            result = services.create_provider(
                self.user,
                {"template_code": "openai", "api_key": "sk-x-12345678", "base_url": base_url},
            )
            self.assertEqual(result.code, LLMStatus.PARAM_ERR, base_url)
            self.assertIn("内网", result.message)

    @override_settings(LLMAPI_ALLOW_PRIVATE_BASE_URL=True)
    def test_private_base_url_allowed_by_default(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.create_provider(
                self.user,
                {"template_code": "ollama", "base_url": "http://127.0.0.1:11434/v1"},
            )
        self.assertTrue(result.success, result.message)

    def test_auth_error_aborts_save(self):
        fake = FakeAdapter(
            list_error=ProviderError(LLMStatus.PROVIDER_AUTH_ERR, "bad key", upstream_status=401)
        )
        with patch_adapter(fake):
            result = services.create_provider(
                self.user, {"template_code": "openai", "api_key": "sk-x-12345678"}
            )
        self.assertEqual(result.code, LLMStatus.PROVIDER_AUTH_ERR)
        self.assertIn("配置未保存", result.message)
        self.assertEqual(LLMProviderConfig.objects.count(), 0)

    def test_unreachable_still_saves_config_with_sync_error(self):
        fake = FakeAdapter(
            list_error=ProviderError(LLMStatus.PROVIDER_UNREACHABLE, "down")
        )
        with patch_adapter(fake):
            result = services.create_provider(
                self.user, {"template_code": "openai", "api_key": "sk-x-12345678"}
            )
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["model_sync"]["status"], "unavailable")
        provider = LLMProviderConfig.objects.get(user=self.user)
        self.assertTrue(provider.last_sync_error)

    @unittest.expectedFailure
    def test_base_url_with_query_should_be_rejected(self):
        """已知缺陷：_check_base_url 允许 base_url 携带 query/fragment，拼接接口路径后会变成非法 URL。"""
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.create_provider(
                self.user,
                {
                    "template_code": "openai",
                    "api_key": "sk-x-12345678",
                    "base_url": "https://api.example.com/v1?token=1",
                },
            )
        self.assertEqual(result.code, LLMStatus.PARAM_ERR)

    def test_duplicate_name_rejected(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            first = services.create_provider(
                self.user, {"template_code": "openai", "name": "dup", "api_key": "sk-x-12345678"}
            )
            second = services.create_provider(
                self.user, {"template_code": "openai", "name": "dup", "api_key": "sk-x-12345678"}
            )
        self.assertTrue(first.success)
        self.assertEqual(second.code, LLMStatus.PARAM_ERR)
        self.assertIn("已存在", second.message)


class ProviderCrudServiceTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")
        self.provider = make_provider(self.user, name="p1")
        self.other_provider = make_provider(self.other, name="other-p")

    def test_list_providers_counts_models(self):
        make_model(self.provider, model_id="gpt-4o")
        make_model(self.provider, model_id="text-embedding-3-small", category="embedding")
        make_model(self.other_provider, model_id="other-model")
        result = services.list_providers(self.user)
        self.assertTrue(result.success)
        self.assertEqual(result.data["total"], 1)
        item = result.data["providers"][0]
        self.assertEqual(item["model_count"], 2)
        self.assertEqual(item["api_key_masked"], "sk-****3456")

    def test_get_provider_ownership(self):
        self.assertTrue(services.get_provider(self.user, self.provider.pk).success)
        self.assertEqual(
            services.get_provider(self.user, self.other_provider.pk).code,
            LLMStatus.NOT_FOUND,
        )
        self.assertEqual(services.get_provider(self.user, 999999).code, LLMStatus.NOT_FOUND)

    def test_update_name_and_enabled(self):
        result = services.update_provider(
            self.user, self.provider.pk, {"name": "renamed", "enabled": False}
        )
        self.assertTrue(result.success, result.message)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.name, "renamed")
        self.assertFalse(self.provider.enabled)

    def test_update_duplicate_name(self):
        make_provider(self.user, name="taken")
        result = services.update_provider(self.user, self.provider.pk, {"name": "taken"})
        self.assertEqual(result.code, LLMStatus.PARAM_ERR)
        self.assertIn("已存在", result.message)

    def test_update_empty_payload_returns_success_without_changes(self):
        result = services.update_provider(self.user, self.provider.pk, {})
        self.assertTrue(result.success)
        self.assertEqual(result.message, "配置已更新")

    def test_update_other_user_provider(self):
        result = services.update_provider(self.other, self.provider.pk, {"name": "hack"})
        self.assertEqual(result.code, LLMStatus.NOT_FOUND)

    def test_update_base_url_triggers_resync_and_removes_stale_auto_models(self):
        stale = make_model(self.provider, model_id="old-model")
        manual = make_model(self.provider, model_id="manual-model", source="manual")
        fake = FakeAdapter(models=[{"model_id": "new-model", "display_name": "", "raw": {}}])
        with patch_adapter(fake) as patched:
            result = services.update_provider(
                self.user, self.provider.pk, {"base_url": "https://new.example.com/v1"}
            )
        self.assertTrue(result.success, result.message)
        patched.assert_called_once()
        access = fake.calls[0][1]
        self.assertIsInstance(access, ProviderAccess)
        self.assertEqual(access.base_url, "https://new.example.com/v1")
        self.assertFalse(LLMModel.objects.filter(pk=stale.pk).exists())
        self.assertTrue(LLMModel.objects.filter(pk=manual.pk).exists())
        self.assertTrue(LLMModel.objects.filter(provider=self.provider, model_id="new-model").exists())

    def test_update_api_key_reencrypts_and_uses_new_key(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.update_provider(
                self.user, self.provider.pk, {"api_key": "sk-new-key-987654"}
            )
        self.assertTrue(result.success, result.message)
        self.provider.refresh_from_db()
        from LLMapi import crypto

        self.assertEqual(crypto.decrypt_api_key(self.provider.api_key_encrypted), "sk-new-key-987654")
        self.assertEqual(self.provider.api_key_masked, "sk-****7654")
        self.assertEqual(fake.calls[0][1].api_key, "sk-new-key-987654")

    def test_update_auth_failure_keeps_old_config(self):
        old_cipher = self.provider.api_key_encrypted
        fake = FakeAdapter(
            list_error=ProviderError(LLMStatus.PROVIDER_AUTH_ERR, "bad key", upstream_status=401)
        )
        with patch_adapter(fake):
            result = services.update_provider(
                self.user,
                self.provider.pk,
                {"api_key": "sk-bad-key-000000", "base_url": "https://elsewhere.example.com/v1"},
            )
        self.assertEqual(result.code, LLMStatus.PROVIDER_AUTH_ERR)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.api_key_encrypted, old_cipher)
        self.assertEqual(self.provider.base_url, "https://api.example.com/v1")

    def test_delete_provider_cascades_models_and_enforces_ownership(self):
        make_model(self.provider, model_id="gpt-4o")
        self.assertEqual(
            services.delete_provider(self.other, self.provider.pk).code, LLMStatus.NOT_FOUND
        )
        result = services.delete_provider(self.user, self.provider.pk)
        self.assertTrue(result.success)
        self.assertFalse(LLMProviderConfig.objects.filter(pk=self.provider.pk).exists())
        self.assertEqual(LLMModel.objects.filter(provider_id=self.provider.pk).count(), 0)


class RefreshModelsTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.provider = make_provider(self.user)
        self.auto = make_model(self.provider, model_id="auto-old")
        self.manual = make_model(self.provider, model_id="manual-keep", source="manual")

    def test_refresh_success_updates_models_and_timestamp(self):
        fake = FakeAdapter(models=[
            {"model_id": "auto-old", "display_name": "Old", "raw": {}},
            {"model_id": "auto-new", "display_name": "", "raw": {}},
        ])
        before = timezone.now() - timedelta(seconds=1)
        with patch_adapter(fake):
            result = services.refresh_models(self.user, self.provider.pk)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["count"], 2)
        self.provider.refresh_from_db()
        self.assertIsNotNone(self.provider.last_synced_at)
        self.assertGreaterEqual(self.provider.last_synced_at, before)
        self.assertEqual(self.provider.last_sync_error, "")
        self.assertTrue(LLMModel.objects.filter(provider=self.provider, model_id="auto-new").exists())
        self.assertTrue(LLMModel.objects.filter(provider=self.provider, model_id="manual-keep").exists())

    def test_refresh_empty_list_marks_unavailable(self):
        fake = FakeAdapter(models=[])
        with patch_adapter(fake):
            result = services.refresh_models(self.user, self.provider.pk)
        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "unavailable")
        self.provider.refresh_from_db()
        self.assertIsNotNone(self.provider.last_synced_at)
        self.assertTrue(self.provider.last_sync_error)

    def test_refresh_failure_records_error(self):
        fake = FakeAdapter(list_error=ProviderError(LLMStatus.PROVIDER_UNREACHABLE, "down"))
        with patch_adapter(fake):
            result = services.refresh_models(self.user, self.provider.pk)
        self.assertEqual(result.code, LLMStatus.PROVIDER_UNREACHABLE)
        self.provider.refresh_from_db()
        self.assertIsNotNone(self.provider.last_synced_at)
        self.assertTrue(self.provider.last_sync_error)

    def test_refresh_auth_error(self):
        fake = FakeAdapter(
            list_error=ProviderError(LLMStatus.PROVIDER_AUTH_ERR, "bad key", upstream_status=401)
        )
        with patch_adapter(fake):
            result = services.refresh_models(self.user, self.provider.pk)
        self.assertEqual(result.code, LLMStatus.PROVIDER_AUTH_ERR)

    def test_refresh_other_user_provider(self):
        other = make_user("bob")
        self.assertEqual(
            services.refresh_models(other, self.provider.pk).code, LLMStatus.NOT_FOUND
        )


class ModelServiceTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")
        self.provider = make_provider(self.user)
        self.other_provider = make_provider(self.other, name="other")
        self.chat_model = make_model(self.provider, model_id="gpt-4o", category="chat")
        self.embed_model = make_model(
            self.provider, model_id="text-embedding-3-small", category="embedding"
        )
        self.other_model = make_model(self.other_provider, model_id="other-model")

    def test_list_models_groups_and_isolates_users(self):
        result = services.list_models(self.user)
        self.assertTrue(result.success)
        self.assertEqual(result.data["total"], 2)
        categories = [group["category"] for group in result.data["groups"]]
        self.assertIn("chat", categories)
        self.assertIn("embedding", categories)
        for group in result.data["groups"]:
            self.assertEqual(group["count"], len(group["models"]))

    def test_list_models_filters(self):
        chat_only = services.list_models(self.user, {"category": "chat"})
        self.assertEqual(chat_only.data["total"], 1)
        by_provider = services.list_models(self.user, {"provider_id": str(self.provider.pk)})
        self.assertEqual(by_provider.data["total"], 2)
        invalid_category = services.list_models(self.user, {"category": "bogus"})
        self.assertEqual(invalid_category.code, LLMStatus.PARAM_ERR)
        invalid_provider = services.list_models(self.user, {"provider_id": "abc"})
        self.assertEqual(invalid_provider.code, LLMStatus.PARAM_ERR)
        others = services.list_models(self.user, {"provider_id": str(self.other_provider.pk)})
        self.assertEqual(others.code, LLMStatus.NOT_FOUND)

    def test_list_provider_models_ownership(self):
        result = services.list_provider_models(self.user, self.provider.pk)
        self.assertEqual(result.data["total"], 2)
        self.assertEqual(
            services.list_provider_models(self.other, self.provider.pk).code,
            LLMStatus.NOT_FOUND,
        )

    def test_add_manual_model_classifies_and_marks_source(self):
        result = services.add_manual_model(
            self.user, self.provider.pk, {"model_id": "whisper-1"}
        )
        self.assertTrue(result.success, result.message)
        model = LLMModel.objects.get(pk=result.data["model"]["id"])
        self.assertEqual(model.category, "audio")
        self.assertEqual(model.source, "manual")
        self.assertEqual(model.param_spec, [])

    def test_add_manual_model_validations(self):
        self.assertEqual(
            services.add_manual_model(self.user, self.provider.pk, {}).code,
            LLMStatus.PARAM_ERR,
        )
        self.assertEqual(
            services.add_manual_model(
                self.user, self.provider.pk, {"model_id": "x", "category": "bogus"}
            ).code,
            LLMStatus.PARAM_ERR,
        )
        services.add_manual_model(self.user, self.provider.pk, {"model_id": "manual-1"})
        duplicate = services.add_manual_model(
            self.user, self.provider.pk, {"model_id": "manual-1"}
        )
        self.assertEqual(duplicate.code, LLMStatus.PARAM_ERR)
        self.assertIn("已存在", duplicate.message)

    def test_update_model(self):
        result = services.update_model(
            self.user, self.chat_model.pk, {"enabled": False, "display_name": "新名字"}
        )
        self.assertTrue(result.success, result.message)
        self.chat_model.refresh_from_db()
        self.assertFalse(self.chat_model.enabled)
        self.assertEqual(self.chat_model.display_name, "新名字")
        empty = services.update_model(self.user, self.chat_model.pk, {})
        self.assertEqual(empty.code, LLMStatus.PARAM_ERR)
        self.assertIn("没有需要更新的字段", empty.message)
        self.assertEqual(
            services.update_model(self.other, self.chat_model.pk, {"enabled": True}).code,
            LLMStatus.NOT_FOUND,
        )

    def test_delete_model(self):
        self.assertEqual(
            services.delete_model(self.other, self.chat_model.pk).code, LLMStatus.NOT_FOUND
        )
        result = services.delete_model(self.user, self.chat_model.pk)
        self.assertTrue(result.success)
        self.assertFalse(LLMModel.objects.filter(pk=self.chat_model.pk).exists())


class CallGatewayTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")
        self.provider = make_provider(self.user)
        self.chat_model = make_model(self.provider, model_id="gpt-4o", category="chat")
        self.embed_model = make_model(
            self.provider, model_id="text-embedding-3-small", category="embedding"
        )
        self.messages = [{"role": "user", "content": "你好"}]

    # ---------- chat ----------
    def test_chat_success(self):
        fake = FakeAdapter()
        with patch_adapter(fake):
            result = services.chat_completion(
                self.user,
                {
                    "model_id": self.chat_model.pk,
                    "messages": self.messages,
                    "params": {"temperature": 0.3},
                },
            )
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["content"], "你好")
        self.assertEqual(result.data["model"], "gpt-4o")
        self.assertEqual(result.data["usage"]["total_tokens"], 3)
        call = fake.calls[0]
        self.assertEqual(call[0], "chat")
        self.assertEqual(call[1].api_key, "sk-test-abcdef123456")
        self.assertEqual(call[2], "gpt-4o")
        self.assertEqual(call[3], self.messages)
        self.assertEqual(call[4]["temperature"], 0.3)

    def test_chat_model_id_validation(self):
        for data in ({}, {"model_id": None}, {"model_id": "abc"}, {"model_id": ""}):
            result = services.chat_completion(self.user, {**data, "messages": self.messages})
            self.assertEqual(result.code, LLMStatus.PARAM_ERR, data)

    @unittest.expectedFailure
    def test_chat_rejects_non_integer_model_id(self):
        """已知缺陷：_parse_model_id 用 int() 强转，1.5/True 会被静默截断成整数。"""
        result = services.chat_completion(
            self.user, {"model_id": 1.5, "messages": self.messages}
        )
        self.assertEqual(result.code, LLMStatus.PARAM_ERR)

    def test_chat_not_found_and_ownership(self):
        self.assertEqual(
            services.chat_completion(self.user, {"model_id": 999999, "messages": self.messages}).code,
            LLMStatus.NOT_FOUND,
        )
        self.assertEqual(
            services.chat_completion(self.other, {"model_id": self.chat_model.pk, "messages": self.messages}).code,
            LLMStatus.NOT_FOUND,
        )

    def test_chat_disabled_model_or_provider(self):
        self.chat_model.enabled = False
        self.chat_model.save()
        disabled_model = services.chat_completion(
            self.user, {"model_id": self.chat_model.pk, "messages": self.messages}
        )
        self.assertEqual(disabled_model.code, LLMStatus.MODEL_UNSUPPORTED)
        self.assertIn("模型已禁用", disabled_model.message)

        self.chat_model.enabled = True
        self.chat_model.save()
        self.provider.enabled = False
        self.provider.save()
        disabled_provider = services.chat_completion(
            self.user, {"model_id": self.chat_model.pk, "messages": self.messages}
        )
        self.assertEqual(disabled_provider.code, LLMStatus.MODEL_UNSUPPORTED)
        self.assertIn("供应商配置已禁用", disabled_provider.message)

    def test_chat_wrong_category(self):
        result = services.chat_completion(
            self.user, {"model_id": self.embed_model.pk, "messages": self.messages}
        )
        self.assertEqual(result.code, LLMStatus.MODEL_UNSUPPORTED)

    def test_chat_message_validation(self):
        cases = [
            None,
            [],
            [{"role": "tool", "content": "x"}],
            [{"role": "system", "content": "no user"}],
            [{"role": "user", "content": 123}],
        ]
        for messages in cases:
            result = services.chat_completion(
                self.user, {"model_id": self.chat_model.pk, "messages": messages}
            )
            self.assertEqual(result.code, LLMStatus.PARAM_ERR, messages)
            self.assertIn("messages 参数不合法", result.message)

    def test_chat_params_validation(self):
        cases = [
            {"unknown": 1},
            {"model": "hack"},
            {"temperature": 5},
            {"max_tokens": 0},
            {"n": 17},
        ]
        for params in cases:
            result = services.chat_completion(
                self.user,
                {"model_id": self.chat_model.pk, "messages": self.messages, "params": params},
            )
            self.assertEqual(result.code, LLMStatus.PARAM_ERR, params)
            self.assertIn("调用参数不合法", result.message)

    def test_chat_provider_error_mapping(self):
        for code, status in (
            (LLMStatus.PROVIDER_AUTH_ERR, 401),
            (LLMStatus.PROVIDER_UNREACHABLE, None),
            (LLMStatus.PROVIDER_API_ERR, 500),
        ):
            fake = FakeAdapter(
                chat_error=ProviderError(code, "upstream error", upstream_status=status)
            )
            with patch_adapter(fake):
                result = services.chat_completion(
                    self.user, {"model_id": self.chat_model.pk, "messages": self.messages}
                )
            self.assertEqual(result.code, code)
            self.assertEqual(result.data["upstream_status"], status)

    def test_chat_unexpected_exception_returns_unknown(self):
        fake = FakeAdapter(chat_error=RuntimeError("bug"))
        with patch_adapter(fake):
            result = services.chat_completion(
                self.user, {"model_id": self.chat_model.pk, "messages": self.messages}
            )
        self.assertEqual(result.code, LLMStatus.UNKNOWN_ERR)

    def test_chat_decrypt_failure(self):
        self.provider.api_key_encrypted = "not-a-valid-token"
        self.provider.save()
        fake = FakeAdapter()
        with patch_adapter(fake):
            result = services.chat_completion(
                self.user, {"model_id": self.chat_model.pk, "messages": self.messages}
            )
        self.assertEqual(result.code, LLMStatus.DB_ERR)
        self.assertIn("解密失败", result.message)

    # ---------- embeddings ----------
    def test_embeddings_success(self):
        fake = FakeAdapter()
        with patch_adapter(fake):
            result = services.create_embeddings(
                self.user,
                {
                    "model_id": self.embed_model.pk,
                    "input": ["a", "b"],
                    "params": {"encoding_format": "float"},
                },
            )
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["embeddings"], [[0.1, 0.2]])
        self.assertEqual(result.data["dimensions"], 2)
        call = fake.calls[0]
        self.assertEqual(call[0], "embeddings")
        self.assertEqual(call[3], ["a", "b"])

    def test_embeddings_wrong_category_and_input_validation(self):
        wrong = services.create_embeddings(
            self.user, {"model_id": self.chat_model.pk, "input": "x"}
        )
        self.assertEqual(wrong.code, LLMStatus.MODEL_UNSUPPORTED)
        for value in (None, "", [], ["ok", ""]):
            result = services.create_embeddings(
                self.user, {"model_id": self.embed_model.pk, "input": value}
            )
            self.assertEqual(result.code, LLMStatus.PARAM_ERR, value)
            self.assertIn("input 参数不合法", result.message)

    def test_embeddings_params_validation(self):
        result = services.create_embeddings(
            self.user,
            {
                "model_id": self.embed_model.pk,
                "input": "x",
                "params": {"encoding_format": "bogus"},
            },
        )
        self.assertEqual(result.code, LLMStatus.PARAM_ERR)

    def test_get_model_config(self):
        config = services.get_model_config(self.user, self.chat_model.pk)
        self.assertTrue(config.success)
        self.assertEqual(config.data["model"]["model_id"], "gpt-4o")
        self.assertEqual(config.data["provider"]["id"], self.provider.pk)
        self.assertNotIn("api_key_encrypted", config.data["provider"])
        self.assertEqual(
            services.get_model_config(self.other, self.chat_model.pk).code,
            LLMStatus.NOT_FOUND,
        )


class SyncAndHelpersTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.provider = make_provider(self.user)

    def test_sync_models_keeps_manual_and_updates_auto(self):
        make_model(self.provider, model_id="same", source="manual", display_name="旧名字")
        fake = FakeAdapter(models=[{"model_id": "same", "display_name": "新名字", "raw": {}}])
        with patch_adapter(fake):
            services.refresh_models(self.user, self.provider.pk)
        model = LLMModel.objects.get(provider=self.provider, model_id="same")
        self.assertEqual(model.display_name, "新名字")
        self.assertEqual(model.source, "auto")

    def test_health_of_result_helpers(self):
        from sqldb.enums import DBStatus
        from sqldb.result import DBResult

        self.assertEqual(services._from_db(DBResult(DBStatus.SUCCESS, "ok", 1)).code, LLMStatus.SUCCESS)
        self.assertEqual(services._from_db(DBResult(DBStatus.NOT_FOUND, "nf")).code, LLMStatus.NOT_FOUND)
        self.assertEqual(services._from_db(DBResult(DBStatus.DUPLICATE_ERR, "dup")).code, LLMStatus.PARAM_ERR)
        self.assertEqual(services._from_db(DBResult(DBStatus.UNKNOWN_ERR, "db")).code, LLMStatus.DB_ERR)

    def test_as_bool(self):
        for value in (True, 1, "true", "YES", "on"):
            self.assertTrue(services._as_bool(value))
        for value in (False, 0, "false", "off", "0", ""):
            self.assertFalse(services._as_bool(value))
        # 值为 None 时返回调用方给定的默认值
        self.assertFalse(services._as_bool(None, False))
        self.assertTrue(services._as_bool(None, True))
