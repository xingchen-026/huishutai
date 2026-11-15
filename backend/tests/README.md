# 后端测试

本目录包含项目关键路径的回归测试：

- **LLMapi**（供应商配置 / 模型目录 / 统一调用网关）：既有 4 个预期失败记录已知缺陷；
- **Workflow**（工作流 / 成员 / 节点 / 连线 / 事件 / 导入导出 / 执行引擎 / 节点实现）：新增 12 个预期失败记录已确认缺陷。

测试默认使用 SQLite 内存库与 mock 的外部依赖（供应商 HTTP、requests、MinIO/Milvus 均不真实访问），
运行时不依赖 PostgreSQL / MinIO / Milvus，也不会发起真实外网请求。

## 运行方式

在 `backend/` 目录下执行：

```bash
# Windows PowerShell
$env:DJANGO_SETTINGS_MODULE = "tests.settings"
.venv\Scripts\python.exe -B manage.py test tests -v 2

# Linux / macOS
DJANGO_SETTINGS_MODULE=tests.settings .venv/bin/python -B manage.py test tests -v 2
```

当前完整结果（2026-11-14）：

```text
Found 358 test(s).
Ran 358 tests
OK (expected failures=16)
```

> CI 使用项目默认 PostgreSQL 配置执行 `python manage.py test`（无 label），Django 会从当前目录发现
> `tests/` 下的测试；本地无 PostgreSQL 时请使用上面的 `tests.settings` 命令。

按文件/模块运行：

```bash
.venv\Scripts\python.exe -B manage.py test tests.test_workflow_services tests.test_workflow_api -v 2
.venv\Scripts\python.exe -B manage.py test tests.test_workflow_crud tests.test_workflow_executor tests.test_workflow_nodes -v 2
.venv\Scripts\python.exe -B manage.py test tests.test_llmapi_pure tests.test_llmapi_services tests.test_llmapi_api -v 2
```

测试文件也纳入 backend 的 ruff 门禁，修改后请自检：

```bash
.venv\Scripts\python.exe -m ruff check tests
.venv\Scripts\python.exe -m ruff format --check tests
```

## 目录说明

| 文件 | 内容 |
| --- | --- |
| `settings.py` | 测试专用 settings（SQLite 内存库、随机 Fernet key、快速密码哈希、屏蔽预期错误日志） |
| `utils.py` | 用户 / 供应商 / 模型构造、Bearer Header、JSON 请求辅助（LLMapi 测试复用） |
| `test_llmapi_pure.py` | LLMapi 纯逻辑：加密、模板、模型分类、参数规格、三个协议适配器（requests mock） |
| `test_llmapi_services.py` | LLMapi 业务层：供应商 CRUD、模型同步、chat / embeddings 网关（DB + mock adapter） |
| `test_llmapi_api.py` | LLMapi HTTP 接口：认证、参数校验、状态码、用户隔离、API Key 不泄露 |
| `test_workflow_services.py` | Workflow 业务层：工作流/成员/节点/连线/事件/导入导出/run/节点目录（70 用例，7 expectedFailure） |
| `test_workflow_api.py` | Workflow HTTP 接口：19 个端点认证、状态码映射、参数边界、权限矩阵、乐观锁 409（31 用例，1 expectedFailure） |
| `test_workflow_crud.py` | Workflow 数据层：模型默认值/级联/唯一约束、五个 CRUD 的边界与乐观锁版本更新（36 用例） |
| `test_workflow_executor.py` | 执行引擎：缺 start/空图、分支端口、多入边、成环防重、步数上限、失败传播（17 用例，2 expectedFailure） |
| `test_workflow_nodes.py` | 节点实现与注册表：start / condition / http / llm、node_loader、render_template（76 用例，2 expectedFailure） |

## 已知缺陷（用 `expectedFailure` 固定）

以下用例编码的是"应有的正确行为"，当前实现不满足，因此标记为预期失败；
修复后去掉 `@unittest.expectedFailure` 即可转为普通回归测试（若忘记去掉，会报 "unexpected success"）。

### LLMapi（既有 4 个）

1. `CreateProviderTest.test_create_provider_should_record_last_synced_at`
   —— 创建供应商并同步模型后未写入 `last_synced_at`（更新供应商同理）。
2. `CallGatewayTest.test_chat_rejects_non_integer_model_id`
   —— `_parse_model_id` 用 `int()` 强转，`1.5` / `True` 会被静默截断成整数。
3. `ClassifyModelTest.test_classify_rerank_model`
   —— `bge-reranker` 等 rerank 模型先命中 embedding 关键字，被错误归为 `embedding`。
4. `CreateProviderTest.test_base_url_with_query_should_be_rejected`
   —— `base_url` 携带 query/fragment 时未被拒绝，拼接接口路径后会得到非法 URL。

### Workflow（新增 12 个）

| 用例 | 缺陷位置 | 应有行为 / 当前问题 |
| --- | --- | --- |
| `WorkflowServiceTestCase...test_add_node_should_reject_non_object_empty_list_position` | `Workflow/services.py:309-316,334` | `position=[]` / `config=[]` 等 falsy 非对象值被 `or {}` 静默归一并通过校验；应返回 `PARAM_ERR`。 |
| `...test_update_node_should_reject_non_integer_base_version` | `Workflow/services.py:368` | `base_version=1.5` / `True` 被 `int()` 截断后通过乐观锁；应拒绝非整数。 |
| `...test_import_should_reject_falsy_non_list_relations` | `Workflow/services.py:598` | `relations={}` 被 `or []` 归一为空数组，导入会清空原连线；应返回 `PARAM_ERR` 且不覆盖原图。 |
| `...test_import_should_return_param_err_for_invalid_items` | `Workflow/services.py:609-670,678` | 逐项校验的 `_ImportError` 在事务 try 之外抛出，HTTP 返回 **500 HTML** 而非 400。 |
| `WorkflowApiTest.test_import_invalid_item_should_return_400` | `Workflow/views.py:101-103` | 同上问题的 API 层固定：非法导入条目应返回 `{code:5001}` / 400。 |
| `...test_import_should_reject_cyclic_graph` | `Workflow/services.py:587-703` | 导入未复用 `_would_create_cycle`，循环连线图可入库（executor 静默忽略分支）。 |
| `...test_import_should_validate_ports` | `Workflow/services.py:646-670` | 导入未校验 `source_port/target_port`，非法端口连线永不触发且 run 仍报成功。 |
| `...test_import_should_require_exactly_one_start` | `Workflow/services.py:587-703` | 导入不校验 start 节点数量；0 个 start 运行必失败，多个 start 只执行第一个。 |
| `GraphBasicsTest.test_empty_nodes_should_report_workflow_empty` | `Workflow/executor.py:28-31` | 空图先命中"缺少 start 节点"，"工作流为空"分支不可达，提示不准确。 |
| `BranchTest.test_exactly_max_steps_graph_should_succeed` | `Workflow/executor.py:42,92-93` | 恰好执行 100 步且队列已空的合法图仍被判"执行步数超过上限"失败（差一错误）。 |
| `StartNodeTest.test_json_array_string_should_be_rejected` | `Workflow/node/start.py:34-40` | JSON 数组/标量字符串被接受为 payload，与"初始数据必须是 JSON 对象"文案矛盾。 |
| `LlmNodeTest.test_non_integer_float_model_id_should_raise` | `Workflow/node/llm.py:58-60` | `model_id=1.5/True` 被 `int()` 截断后调用错误模型（`max_tokens` 同类）。 |

> 缺陷编号与完整证据/影响/修复方向见项目审查报告；前端已知缺陷见 `frontend/tests/README.md`。
