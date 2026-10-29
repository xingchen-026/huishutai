# 后端测试

本目录包含 LLMapi（供应商配置 / 模型目录 / 统一调用网关）及数据层的关键路径测试。

## 运行方式

测试默认使用 SQLite 内存库与 mock 的供应商适配器，不依赖 PostgreSQL / MinIO / Milvus，
也不会发起真实外网请求。

在 `backend/` 目录下执行：

```bash
# Windows PowerShell
$env:DJANGO_SETTINGS_MODULE = "tests.settings"
.venv\Scripts\python.exe -B manage.py test tests -v 2

# Linux / macOS
DJANGO_SETTINGS_MODULE=tests.settings .venv/bin/python -B manage.py test tests -v 2
```

如本机有可用的 PostgreSQL，也可以用项目默认配置运行：

```bash
.venv\Scripts\python.exe -B manage.py test tests -v 2
```

## 目录说明

| 文件 | 内容 |
| --- | --- |
| `settings.py` | 测试专用 settings（SQLite 内存库、固定 Fernet key、快速密码哈希） |
| `utils.py` | 用户 / 供应商 / 模型构造、Bearer Header、JSON 请求辅助 |
| `test_llmapi_pure.py` | 加密、供应商模板、模型分类与参数规格、三个协议适配器（requests mock） |
| `test_llmapi_services.py` | 供应商 CRUD、模型同步、统一 chat / embeddings 网关（适配器 mock + SQLite） |
| `test_llmapi_api.py` | HTTP 接口：认证、参数校验、状态码、用户隔离、API Key 不泄露 |

## 已知缺陷（用 `expectedFailure` 标记）

以下用例编码的是“应有的正确行为”，当前实现不满足，因此被标记为预期失败；
修复后去掉 `@unittest.expectedFailure` 即可转为正常回归测试：

1. `CreateProviderTest.test_create_provider_should_record_last_synced_at`
   —— 创建供应商并同步模型后未写入 `last_synced_at`（更新供应商同理）。
2. `CallGatewayTest.test_chat_rejects_non_integer_model_id`
   —— `_parse_model_id` 用 `int()` 强转，`1.5` / `True` 会被静默截断成整数。
3. `ClassifyModelTest.test_classify_rerank_model`
   —— `bge-reranker` 等 rerank 模型先命中 embedding 关键字，被错误归为 `embedding`。
4. `CreateProviderTest.test_base_url_with_query_should_be_rejected`
   —— `base_url` 携带 query/fragment 时未被拒绝，拼接接口路径后会得到非法 URL。
