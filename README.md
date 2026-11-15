# 汇书台（huishutai）

[![CI](https://github.com/xingchen-026/huishutai/actions/workflows/ci.yml/badge.svg?branch=devlop)](https://github.com/xingchen-026/huishutai/actions/workflows/ci.yml)

> 面向 AI 应用落地的技术整合实践项目：把 RAG、Agent、工作流编排、文生图、文生视频等 AI 能力，与用户管理、文件存储、模型供应等基础技术服务结合，沉淀一套可复用的应用落地方案。

## 项目简介

**汇书台**是一个用于整合 AI 应用落地相关技术的工程实践项目。项目按「基础服务 → 数据访问层 → AI 能力」的顺序推进：先完成用户体系、文件对象存储、关系库/向量库访问层与模型供应网关等基础设施，再按模块接入大模型应用、工作流编排与检索增强等能力。

当前阶段：

- **已完成**：用户管理（后端 + 前端）、文件上传与对象存储、大模型供应商配置 / 模型目录 / 统一对话与嵌入调用网关、`sqldb`（PostgreSQL）与 `vectordb`（Milvus）数据访问层、**工作流与无限画布**（后端工作流应用 + 前端可视化编排器）、前端全站页面（登录 / 注册 / 首页 / 知识库 / 模型服务 / 工作流 / 个人中心）、CI 与容器化部署。
- **开发中**：RAG 检索增强（仅应用骨架；知识库页面的文档解析、向量化与问答为占位）。
- **规划中**：Agent、文生图、文生视频（首页对应入口为「即将上线」占位）。

## 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 用户管理 | ✅ 已完成 | 注册 / 登录 / 登出 / 用户名查重 / 个人资料 / 修改密码，后端接口 + 前端页面齐备 |
| 文件上传与对象存储 | ✅ 已完成 | MinIO 对象存储 + PostgreSQL 元数据 + 临时签名 URL；前端「知识库」页已接入上传（进度、签名链接、本地历史）；「我的文件」列表 / 删除 / 重新签名接口尚未提供 |
| 大模型供应（LLMapi） | ✅ 已完成 | 后端：供应商模板与配置、在线模型同步、参数规格与校验、统一 chat / embeddings 网关、API Key 加密；前端：模型服务页（供应商 / 模型目录 / 参数规格管理） |
| 工作流与无限画布（Workflow） | ✅ 首版完成 | 后端 14 个接口 + 前端列表与编辑器；4 类内置节点、成员协作、事件同步、导入导出、执行引擎、乐观锁；回放 / 撤销等能力待补 |
| 关系库数据层 `sqldb` | ✅ 已完成 | 通用 CRUD 基类、统一结果对象、状态码；已覆盖用户 / 文件 / 模型 / 工作流共 **10 张表** |
| 向量库数据层 `vectordb` | 🚧 封装完成，未暴露接口 | Milvus 客户端、集合 CRUD、`init_vectordb` 初始化命令 |
| RAG 检索增强 | 🚧 仅骨架 | 应用已注册，无路由与业务逻辑 |
| Agent / 文生图 / 文生视频 | 📋 规划中 | — |
| 自动化测试 | 🚧 部分覆盖 | 后端 358 个用例（7 个 `expectedFailure` 记录已知缺陷）；前端 96 个用例（95 通过 + 1 个 todo）；用户 / 文件 / 向量库仍为占位测试 |
| 代码质量与 CI | ✅ 已完成 | GitHub Actions 3 个 job（后端 / 前端 / Docker 镜像）、pre-commit、Ruff / ESLint / Prettier |
| 容器化部署 | ✅ 已完成 | 前端 + 后端 + PostgreSQL + Milvus + 独立 MinIO（文件存储）统一编排 |
| UI 设计原型 | ✅ 参考产物 | `frontend/prototype/` 为静态 HTML 概念原型，不参与构建、部署与路由 |

## 功能特性

- **用户体系**：注册、登录、登出、用户名查重、个人资料查看/修改、修改密码。
- **签名 Token 认证**：基于 `django.core.signing`，不新增 token 表；默认所有接口要求登录，公开接口单独放开。
- **文件上传**：登录用户上传文件，校验大小与扩展名，流式计算 SHA-256，写入 MinIO，元数据落 PostgreSQL，返回可临时访问的签名 URL；上传失败自动回滚已写入对象。
- **大模型供应与统一调用**：内置 10 个供应商模板（OpenAI 兼容 / Anthropic / Gemini 三类协议），API Key 加密存储且接口只回显掩码；在线拉取模型列表并分类、生成调用参数白名单；通过统一网关调用对话与嵌入模型，按模型参数规格严格校验。
- **工作流与无限画布**：前端基于 Vue Flow 的可视化编排器（节点目录、连线、参数配置抽屉、运行结果、导入导出、成员协作、2s 事件轮询同步）；后端由「节点注册表 + 执行器 + 业务服务」组成，内置开始 / 大模型 / 条件分支 / HTTP 请求 4 类节点，支持乐观锁并发控制与事件日志。
- **前端应用体系**：8 个页面路由 + 布局组件（侧边栏 / 顶栏 / 面包屑）、Pinia 状态（登录态 / 主题 / Toast / 上传历史）、亮暗双主题（CSS 变量设计令牌）、图标系统（`@lucide/vue`）、统一请求封装（自动附加 Token、401 跳登录、错误信息提取）。
- **分层数据访问**：业务层不直接写 ORM，统一经 `sqldb` / `vectordb` 数据层访问数据库，返回结果收敛为 `DBResult` / `VDBResult` / `LLMResult` / `WFResult`。
- **URL 安全（SSRF 防护）**：`url_safety.validate_http_url` 统一校验供应商 `base_url` 与工作流 HTTP 节点 URL，默认拒绝内网 / 本机 / 保留地址，并拒绝重定向跟随。
- **路由自检**：`GET /routes/` 返回后端已注册路由（当前 31 条）的路径、名称、视图与 HTTP 方法，便于联调时核对接口。
- **向量检索基础设施**：Milvus 客户端懒加载单例、集合结构声明式定义、幂等建集合命令，为 RAG 场景预留能力。
- **前后端分离 + 容器化部署**：开发态由 Vite 代理请求，生产态由 Nginx 反向代理；`deploy/docker-compose.yml` 一键拉起全部服务。

## 技术栈

### 后端

| 组件 | 版本 / 说明 |
| --- | --- |
| Python | 3.12（见 `backend/.python-version`） |
| Django | 6.1.2 |
| Django REST Framework | 3.18.3 |
| Gunicorn | 26.2.0（容器内 WSGI 服务器） |
| uv | 依赖与虚拟环境管理（`pyproject.toml` + `uv.lock`，依赖全部锁定版本） |
| PostgreSQL | 16（驱动 `psycopg2-binary` 2.9.13） |
| Milvus | 2.6（SDK `pymilvus` 2.6.17） |
| MinIO | 对象存储（SDK `minio` 7.2.20），业务文件独立部署 |
| cryptography | 50.0.2（Fernet 加密 API Key） |
| requests | 2.34.2（调用大模型供应商 / 工作流 HTTP 节点） |
| Ruff | 0.17.3（dev 依赖，格式化 + Lint） |
| pre-commit | 4.7.0（dev 依赖，本地提交钩子） |

> 原 `requirements.txt` 已移除，后端依赖统一由 uv 管理；`black` 已不再使用（格式化统一为 Ruff）。

### 前端

| 组件 | 版本 / 说明 |
| --- | --- |
| Node.js | 24.x（`engines` 要求：`^22.18.0` 或 `>=24.12.0`） |
| Vue | 3.5（`^3.5.42`） |
| Vue Router | 5.4（history 模式 + 登录守卫） |
| Pinia | 4.1（登录态 / 主题 / Toast / 上传历史） |
| Vite | 8.2（`^8.2.2`） |
| TypeScript | 6.0（`~6.0.0`，由 `vue-tsc` 做类型检查） |
| Axios | 1.20 |
| 工作流画布 | `@vue-flow/core` 1.48 + background 1.3 / controls 1.1 / minimap 1.5 |
| 图标 / 工具库 | `@lucide/vue` 1.68、`@vueuse/core` 15 |
| 构建 | npm + `npm-run-all2`（`npm run build` = `type-check` 与 `vite build` 并行） |
| 代码质量 | ESLint 10 + eslint-plugin-vue 10 + Prettier 3.9 |
| 测试 | Node.js 24 内置 `node:test`（不引入 vitest / jest / jsdom） |

> 前端没有完整 UI 组件库：页面与组件为项目内手写 CSS，配合 `tokens.css` 的亮/暗双主题设计令牌；图标使用 `@lucide/vue`，无限画布使用 `@vue-flow/*`。

### 部署

- Docker / Docker Compose
- Nginx（托管前端静态资源 + `/api` 反向代理；`client_max_body_size 60m`、300s 超时、SPA history 回退）
- PostgreSQL 16
- Milvus 2.6 standalone（依赖 etcd + MinIO）、Attu（Milvus 可视化控制台，可选）
- 独立 MinIO（业务文件对象存储，与 Milvus 依赖的 MinIO 隔离）
- 镜像：后端 `python:3.12-slim`（`uv sync --frozen --no-dev` + Gunicorn）；前端 `node:24-alpine` 构建 → `nginx:alpine` 运行

## 目录结构

```
huishutai/
├── backend/                    # 后端服务（Django）
│   ├── config/                 # Django 配置：settings / urls / wsgi / asgi
│   ├── api/                    # 路由入口（集中注册 URL）+ 路由列表接口（/routes/）
│   ├── user/                   # 用户业务层：views（业务接口）+ auth（签名 Token 认证）
│   ├── files/                  # 文件上传业务：services（校验/存储编排）+ views + init_storage 命令
│   ├── filestorage.py          # MinIO 对象存储访问层（上传/删除/签名 URL/健康检查）
│   ├── url_safety.py           # URL 安全校验（SSRF 防护，LLMapi 与 Workflow 共用）
│   ├── LLMapi/                 # 大模型供应与调用
│   │   ├── templates.py        # 内置供应商模板
│   │   ├── crypto.py           # API Key Fernet 加解密与脱敏
│   │   ├── adapters.py         # OpenAI 兼容 / Anthropic / Gemini 协议适配
│   │   ├── model_meta.py       # 模型分类、参数规格生成、请求参数校验
│   │   ├── services.py         # 供应商配置/模型同步/统一调用网关（业务层）
│   │   ├── views.py / urls.py  # HTTP 接口
│   │   └── result.py           # LLMResult / LLMStatus
│   ├── Workflow/               # 工作流编排（业务层 + 执行引擎）
│   │   ├── views.py / urls.py  # 14 个工作流 HTTP 接口
│   │   ├── services.py         # 工作流/成员/节点/连线/事件/导入导出/执行编排
│   │   ├── executor.py         # 执行器：从 start 节点按连线推进（BFS）
│   │   ├── node_loader.py      # 节点注册表：扫描 node/ 目录、惰性导入、缓存
│   │   ├── node/               # 节点实现：start / llm / condition / http（新增节点 = 新增文件）
│   │   └── result.py           # WFResult / WFStatus
│   ├── sqldb/                  # 关系库数据层
│   │   ├── models.py           # 10 张表：用户 / 资料 / 文件 / 供应商 / 模型 / 工作流 5 表
│   │   ├── crud/               # BaseCRUD 基类 + 各表数据访问对象
│   │   ├── enums.py            # DBStatus 状态码
│   │   ├── result.py           # DBResult 统一返回
│   │   └── migrations/         # 0001 ~ 0004
│   ├── vectordb/               # 向量库数据层（Milvus，不建 Django 模型）
│   │   ├── client.py           # 客户端懒加载单例 / 健康检查
│   │   ├── schemas.py          # 集合结构定义
│   │   ├── crud/               # VectorCollection 通用操作
│   │   ├── management/commands/init_vectordb.py
│   │   ├── enums.py            # VDBStatus
│   │   └── result.py           # VDBResult
│   ├── RAG/                    # RAG 业务应用（骨架，无路由）
│   ├── tests/                  # 后端回归测试：LLMapi + Workflow（SQLite + mock，不依赖外部服务）
│   ├── main.py                 # uv 初始化占位入口（非 Django 启动入口）
│   ├── manage.py
│   ├── pyproject.toml / uv.lock
│   └── Dockerfile
├── frontend/                   # 前端服务（Vue 3 + Vite + TypeScript）
│   ├── src/
│   │   ├── api/                # axios 封装 + user / files / llm / workflow 接口
│   │   ├── router/             # 路由表与登录守卫
│   │   ├── stores/             # Pinia：auth / theme / toast / uploads
│   │   ├── utils/              # auth（token / 用户信息存储）、error（错误信息提取）
│   │   ├── views/              # 8 个页面：Login / Register / Home / Knowledge / Models / Profile / WorkflowList / WorkflowEditor
│   │   ├── components/
│   │   │   ├── layout/         # AppLayout：侧边栏 / 顶栏 / 面包屑 / 用户菜单
│   │   │   ├── ui/             # AppIcon：@lucide/vue 图标映射
│   │   │   └── workflow/       # WorkflowNode：画布节点渲染
│   │   └── assets/styles/      # tokens.css（亮/暗设计令牌）+ app.css + workflow.css
│   ├── tests/                  # 前端工作流测试（node:test + Vite SSR harness + mocks）
│   ├── prototype/              # 静态 HTML 设计概念原型（不参与构建 / 部署 / 路由）
│   ├── nginx.conf              # 静态资源 + /api 代理（上传 60MB、300s 超时、history 回退）
│   ├── Dockerfile
│   ├── vite.config.ts / package.json
│   ├── eslint.config.js / .prettierrc.json / tsconfig*.json
│   └── README.md               # 仍为 Vite 脚手架模板说明（待替换为项目文档）
├── deploy/                     # 部署编排
│   ├── docker-compose.yml      # PostgreSQL / Milvus / 独立 MinIO / 前后端
│   └── .env.example            # 环境变量样板（复制为 .env 后需填密钥）
├── .github/
│   ├── workflows/ci.yml        # CI：后端检查与测试 / 前端检查与构建 / Docker 镜像
│   └── dependabot.yml          # uv / npm / GitHub Actions 每周依赖更新
├── .pre-commit-config.yaml     # 本地提交钩子（后端 Ruff、前端 Prettier）
├── .editorconfig
├── .gitattributes              # 文本统一 LF；bat/cmd/ps1 保留 CRLF
├── .gitignore
└── README.md
```

> 目录结构随开发进度调整，以仓库实际内容为准。

## 架构说明

### 分层约定

```
HTTP 请求
  └─ api/urls.py（集中注册路由）
      ├─ user/views.py     → sqldb.crud（user / user_info）──────────────→ PostgreSQL
      ├─ files/views.py    → files/services.py → filestorage.py ─────────→ MinIO
      │                                     └──→ sqldb.crud（uploaded_file）→ PostgreSQL
      ├─ LLMapi/views.py   → LLMapi/services.py → adapters（供应商 HTTP）
      │                           ├──→ crypto / model_meta / url_safety（纯函数与安全校验）
      │                           └──→ sqldb.crud（llm_provider / llm_model）→ PostgreSQL
      └─ Workflow/views.py → Workflow/services.py → sqldb.crud（workflow 5 表）→ PostgreSQL
                                  └──→ Workflow/executor.py
                                        └──→ Workflow/node_loader.py
                                              └──→ Workflow/node/*.py（start / llm / condition / http）
                                                    ├─ llm 节点  → LLMapi/services.py（统一网关）
                                                    └─ http 节点 → url_safety.py + requests
```

- **`api/urls.py`**：只做 URL 路由；业务接口由 `user` / `files` / `LLMapi` / `Workflow` 等应用提供。`api/views.py` 仅提供只读的路由列表接口。
- **业务层**（`user/views.py`、`files/services.py`、`LLMapi/services.py`、`Workflow/services.py`）：参数校验、业务编排、调用数据层、返回统一结果；不直接出现 `User.objects` 这类 ORM 操作。
- **`user/auth.py`**：签名 Token 的签发与校验，以及 DRF 认证类 `SignedTokenAuthentication`、权限类 `IsLoginUser`。
- **`sqldb/`**：表结构（`models.py`）、通用 CRUD 基类（`crud/base.py`）、各表数据访问对象、状态码与结果对象。数据层不感知 HTTP 与业务规则。
- **`filestorage.py`**：MinIO 对象存储访问层，只做 bucket / 上传 / 删除 / 签名 URL / 健康检查；文件归属与校验在 `files/services.py`。
- **`vectordb/`**：不建 Django 模型；集合结构定义在 `schemas.py`，Milvus 操作在 `crud/`，连接管理在 `client.py`。负责向量读写，不做 embedding、文本切分与 RAG 流程。
- **`LLMapi/`**：大模型供应业务。适配器只做协议转换；业务层负责供应商配置、模型同步、调用参数校验；对其它应用提供 `services.get_model_config` / `services.chat_completion` / `services.create_embeddings` 入口，不直接暴露供应商请求。
- **`Workflow/`**：工作流业务与执行。HTTP 层只做方法分发；业务层负责权限、事件记录、节点/连线/成员 CRUD、导入导出；执行层由 `executor.py` 驱动、`node_loader.py` 按目录加载节点实现。节点内部调用 LLM 时复用 `LLMapi.services` 网关，不自行请求供应商。
- **`url_safety.py`**：LLMapi 与 Workflow 共用的 URL 安全层（scheme / userinfo / query / fragment / 内网 IP / 重定向）。
- **`RAG/`**：AI 业务应用，目前为骨架，后续承载检索增强逻辑。

### 工作流与无限画布

**数据拆分**：工作流主体、成员、节点、连线、事件分别建表（`workflow` / `workflow_member` / `workflow_node` / `workflow_edge` / `workflow_event`），JSON 仅用于导入导出，不把整图塞进单个字段。

**节点体系（`Workflow/node/`）**

- `node_loader.py` 扫描 `node/` 目录发现节点类型（文件名即类型名，如 `start.py` → `start`），**惰性导入 + 进程内缓存**；
- 每个节点模块提供 `NODE_META`（名称、分类、输入/输出端口、参数规格）与 `execute(config, input_data, context)`，返回 `NodeResult(output, next_port, logs)`；可预期失败抛 `NodeError`；
- 模板占位目前只支持 `{{input}}`（替换为上游节点输出的 JSON 字符串）。

| 节点 | 说明 | 输出端口 / 关键参数 |
| --- | --- | --- |
| `start` | 工作流入口，向下游传递初始数据 | `out`；`payload`（JSON 对象） |
| `llm` | 调用「模型服务」中已启用的对话模型 | `out`；`model_id`（必填）、`system_prompt`、`prompt`（支持 `{{input}}`）、`temperature`、`max_tokens` |
| `condition` | 按输入字段比较结果选择分支 | `true` / `false`；`field`（字段路径）、`operator`（eq / ne / contains / not_contains / gt / lt / empty / not_empty）、`value` |
| `http` | 请求外部 HTTP 接口 | `out`；`method`、`url`（支持模板）、`headers`（JSON）、`body`、`timeout`（1–60s，默认 15） |

**执行引擎（`executor.py`）**：从唯一的 `start` 节点开始按连线推进；`visited` 去重防环；每个节点执行后按 `next_port` 选择出边；节点失败返回 `status=failed` 与已执行步骤；`MAX_STEPS=100` 防止成环死循环；返回 `{status, error, steps[], output, duration_ms}`。

**权限模型**：创建者为 `owner`，被邀请成员为 `editor`（可编辑）/ `viewer`（只读）。owner 才可删除工作流、增删成员；editor 可修改节点/连线、导入、运行；viewer 只读。列表只返回自己创建的与被邀请的工作流。

**事件与协作**：每次变更（创建/更新/节点/连线/成员/导入/运行）写入 `workflow_event`，自增 `id` 作为协作同步游标；`GET /workflow/workflows/<id>/events/?after=&limit=` 返回增量事件与 `last_event_seq`，前端每 2s 轮询并静默刷新。

**乐观锁**：`workflow_node.version` 每次更新 +1；修改节点必须携带整数 `base_version`，版本不一致返回 `5004` / HTTP 409，前端提示后刷新最新状态。

**导入 / 导出**：导出格式为 `{"format": "huishutai.workflow", "format_version": 1, nodes, relations}`；导入限制 ≤200 节点 / ≤500 连线，校验节点类型、key 唯一、坐标、config、连线引用、端口、重复边、成环，并且**必须且只能有一个 start 节点**（`nodes` 为空时允许清空画布），整体在事务内替换，失败回滚。

> 说明：`GET /workflow/workflows/<id>/members/` 当前返回的是**整份工作流状态**（与 `GET /workflow/workflows/<id>/` 相同），不是成员数组；这是首版实现的已知行为。

### 统一返回与状态码

所有接口统一返回 `{ "code": 0, "message": "...", "data": ... }`，不同领域使用各自的状态码枚举：

**数据库 / 文件（`DBStatus`）**

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 1001 | 数据不存在 |
| 1002 | 唯一约束冲突（如用户名、配置名称、节点 key、连线重复） |
| 1003 | 参数 / 业务校验不通过 |
| 1004 | 外部服务异常（如 MinIO） |
| 1005 | 并发冲突（乐观锁版本不一致，Workflow 映射为 5004 / HTTP 409） |
| 9999 | 数据库 / 未知异常 |

**向量库（`VDBStatus`）**

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 2001 | 集合或向量数据不存在 |
| 2002 | 参数不合法（空数据、维度不匹配等） |
| 2003 | 向量库连接失败 |
| 2999 | 其它向量库异常 |

**大模型（`LLMStatus`）**

| code | 含义 | HTTP 状态 |
| --- | --- | --- |
| 0 | 成功 | 200 |
| 4001 | 参数 / 业务校验不通过 | 400 |
| 4002 | 资源不存在 | 404 |
| 4003 | 供应商鉴权失败（API Key 无效） | 400 |
| 4004 | 供应商不可达（超时 / 网络错误） | 502 |
| 4005 | 供应商返回错误 | 502 |
| 4006 | 模型不受支持（分类不符 / 已禁用） | 400 |
| 4007 | 数据库 / 解密等内部错误 | 500 |
| 4999 | 未知异常 | 500 |

**工作流（`WFStatus`）**

| code | 含义 | HTTP 状态 |
| --- | --- | --- |
| 0 | 成功 | 200 |
| 5001 | 参数 / 业务校验不通过 | 400 |
| 5002 | 工作流 / 节点 / 连线不存在 | 404 |
| 5003 | 无权限（非成员、viewer 执行写操作、非 owner 管理成员） | 403 |
| 5004 | 并发冲突（节点乐观锁版本不一致） | 409 |
| 5005 | 节点执行失败（`NodeError`） | 400 |
| 5006 | 节点加载失败（节点文件缺失 / 导入异常） | 500 |
| 5007 | 工作流执行失败 | 400 |
| 5999 | 未知异常 | 500 |

> 注意：`POST /workflow/workflows/<id>/run/` 只要请求被受理就返回 `code=0` / HTTP 200，图执行的成败在 `data.status`（`success` / `failed`）中体现。

业务校验失败默认 HTTP 400；未登录或 Token 无效 HTTP 401；无权限 HTTP 403；资源不存在 HTTP 404；并发冲突 HTTP 409；服务端异常 HTTP 500。

### 认证流程

1. 注册 / 登录成功后，服务端用 `SECRET_KEY`（来自环境变量 `DJANGO_SECRET_KEY`）对 `{uid}` 签名生成 token，有效期 7 天。
2. 前端把 token 存入 `localStorage`，后续请求自动携带 `Authorization: Bearer <token>`。
3. DRF 认证类解析 token 并加载用户；失败返回 401，前端清理登录态并跳转登录页。
4. token 无状态，服务端不保存会话，退出登录仅清前端 token；修改 `DJANGO_SECRET_KEY` 会使全部 token 失效。

> 文件上传、LLM 供应、工作流与路由列表接口均沿用全局配置，需要登录；数据按 `request.user` 隔离，接口不接受前端传入的 `user_id`。工作流在登录之外还有 owner / editor / viewer 的业务层权限控制。

### 文件上传流程

1. 前端以 `multipart/form-data` 调用 `POST /files/upload/`，字段名固定为 `file`（知识库页支持拖拽 / 选择文件并展示上传进度）。
2. 校验：文件名非空、大小不超过 `MAX_UPLOAD_SIZE`（默认 50MB）、扩展名在 `ALLOWED_UPLOAD_EXTENSIONS` 白名单内。
3. 流式计算 SHA-256（同时统计实际大小），读完复位文件指针。
4. 写入 MinIO，对象键格式 `uploads/{user_id}/{YYYY}/{MM}/{uuid}{扩展名}`。
5. 生成浏览器可访问的临时签名 URL（`MINIO_PUBLIC_ENDPOINT`，默认 1 小时，最长 7 天）。
6. 写入 PostgreSQL 元数据；若元数据写入失败，删除已上传对象避免孤儿文件。

> 前端「知识库」页的上传历史暂存在 `localStorage`（按用户隔离），因为后端尚未提供文件列表 / 删除 / 重新签名接口。

### LLM 调用流程

```
供应商模板（内置 10 个，openai / anthropic / gemini 三类协议）
   └─ 用户创建供应商配置（base_url、API Key 加密入库、脱敏回显）
        └─ 在线拉取模型列表 → 分类（chat / embedding / rerank / image / audio / other）
             └─ 生成参数规格 param_spec（白名单 + 类型/范围/枚举）
                  └─ 统一网关校验并调用适配器 → 归一化响应返回
```

- API Key 使用 Fernet 对称加密后入库，接口只返回掩码（如 `sk-****abcd`）；`LLMAPI_ENCRYPTION_KEY` 未配置时：`DJANGO_DEBUG=true` 下由 `SECRET_KEY` 派生（仅开发方便），**非 DEBUG 环境应用会直接拒绝启动**。
- 模型列表来自在线拉取（`source=auto`）或用户手动登记（`source=manual`）；重新同步时保留手动模型，删除已消失的自动模型。
- 调用时按模型 `param_spec` 严格校验参数；`model` / `messages` / `input` / `stream` 由系统控制，不允许用户传入。
- `base_url` 与每次供应商请求都会经过 `url_safety` 校验，适配器不跟随 3xx 重定向。
- 当前实现为同步一次性返回，未支持流式输出与工具调用。

### URL 安全与 SSRF 防护

`backend/url_safety.py` 的 `validate_http_url()` 被 LLMapi（保存 `base_url` 时、每次供应商请求前）与 Workflow HTTP 节点共同使用：

- 必须是合法的 `http` / `https` 地址且有 hostname；
- 拒绝携带用户名密码、query、fragment 的 URL；
- `LLMAPI_ALLOW_PRIVATE_BASE_URL=false`（默认）时，对域名做 DNS 解析并逐一检查解析结果，拒绝 private / loopback / link-local / reserved / multicast / unspecified 地址；解析失败同样拒绝；
- LLMapi 适配器与工作流 HTTP 节点均设置 `allow_redirects=False`，遇到 3xx 直接报错，避免重定向绕过校验；
- 已知残余风险：仅在解析时校验、未固定解析结果（DNS rebinding 场景未做防护）。

### 数据模型

**PostgreSQL**（`backend/sqldb/models.py`，迁移 `0001 ~ 0004`）：

| 表 | 说明 |
| --- | --- |
| `user` | 用户表：`username`（唯一）、`password`（哈希值）；普通 Django Model，不依赖 `django.contrib.auth` |
| `user_info` | 用户资料表：与 `user` 一对一，`email` / `phone` / `gender` |
| `uploaded_file` | 上传文件元数据：归属用户、原始文件名、`bucket` + `object_key`、SHA-256、大小、MIME、上传时间；唯一约束 `(bucket, object_key)`，索引 `(user, file_hash)` |
| `llm_provider_config` | 大模型供应商配置：归属用户、模板编码、协议、`base_url`、加密 API Key、脱敏 Key、启用状态、最近同步时间/错误；唯一约束 `(user, name)` |
| `llm_model` | 模型目录：所属供应商、供应商模型 ID、展示名、分类、参数规格（JSON）、来源（auto/manual）、启用状态、原始信息、同步时间；唯一约束 `(provider, model_id)` |
| `workflow` | 工作流主体：`owner`、`name`、`description`、时间戳；索引 `owner` |
| `workflow_member` | 协作成员：`workflow` + `user` + `role`（editor / viewer）；唯一约束 `(workflow, user)` |
| `workflow_node` | 工作流节点：`key`（业务键）、`node_type`、`name`、`position_x/y`、`config`（JSON）、`version`（乐观锁）；唯一约束 `(workflow, key)` |
| `workflow_edge` | 工作流连线：`source_key` / `source_port` / `target_key` / `target_port`，不建节点外键；五元组唯一约束 |
| `workflow_event` | 操作事件日志：`actor`、`op`、`payload`（JSON）、时间；自增 `id` 作为协作同步序号 |

**Milvus**（`backend/vectordb/schemas.py`）：

| 项 | 值 |
| --- | --- |
| 集合名 | `knowledge_chunks`（可用环境变量覆盖） |
| 向量维度 | 1024（需与 embedding 模型输出维度一致） |
| 度量方式 | COSINE |
| 标量字段 | `content`（切片原文，8192）/ `source`（来源，512）/ `doc_id`（文档标识，128） |
| 主键 | `id`，自增（`auto_id=True`，因此不支持 upsert） |
| 索引 | AUTOINDEX |

**MinIO**（业务文件）：

| 项 | 值 |
| --- | --- |
| bucket | `huishutai-files`（可用 `MINIO_BUCKET` 覆盖） |
| 对象键 | `uploads/{user_id}/{YYYY}/{MM}/{uuid}{扩展名}` |
| 访问方式 | 后端生成临时签名 URL，浏览器直接访问；bucket 不做公开读 |

## 快速开始

> 以下命令均以仓库根目录为起点，按小节分别执行。

### 环境要求

- Python 3.12+（推荐使用 uv）
- Node.js 24.x（或满足 `^22.18.0 || >=24.12.0`）
- Docker & Docker Compose（容器化部署，或用于启动 PostgreSQL / Milvus / MinIO 依赖）
- 本地直跑后端时需可用的 PostgreSQL 16、Milvus 2.6、MinIO
- **后端运行必须提供 `DJANGO_SECRET_KEY`，或显式开启开发模式 `DJANGO_DEBUG=true`**；非 DEBUG 环境还必须提供 `LLMAPI_ENCRYPTION_KEY`

### 方式一：Docker Compose 部署（推荐）

先在仓库根目录生成密钥（`.env.example` 内也有生成命令注释）：

```bash
cd backend
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
cd ..
```

`deploy/.env` 中 **`DJANGO_SECRET_KEY` 与 `LLMAPI_ENCRYPTION_KEY` 必须填写**（compose 默认 `DJANGO_DEBUG=false`，缺失密钥时后端容器会因 `ImproperlyConfigured` 启动失败）：把上面两条命令的输出分别填入，并按需修改 `POSTGRES_PASSWORD`、`MINIO_ROOT_PASSWORD`、`DJANGO_ALLOWED_HOSTS`。

```bash
cd deploy
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
# 编辑 deploy/.env：填入 DJANGO_SECRET_KEY 与 LLMAPI_ENCRYPTION_KEY
docker compose up -d --build
```

启动后访问 `http://localhost` 即为前端页面。

| 服务 | 端口（宿主机） | 说明 |
| --- | --- | --- |
| frontend | 80 | 前端入口，Nginx 托管静态资源并把 `/api/` 转发到后端（上传上限 60MB） |
| backend | 容器内 8000 | 启动时自动执行 `migrate`、`init_storage`，再由 Gunicorn 提供服务 |
| db | 127.0.0.1:5432 | PostgreSQL 16，数据卷 `postgres_data` |
| milvus | 127.0.0.1:19530、9091 | Milvus standalone，数据卷 `milvus_data` |
| etcd | 容器内 2379 | Milvus 元数据依赖 |
| minio | 127.0.0.1:9000、9001 | Milvus 依赖的对象存储（与业务文件隔离） |
| minio-files | 127.0.0.1:9004、9005 | 业务文件对象存储：9004 供浏览器访问签名 URL，9005 为控制台 |
| attu | 127.0.0.1:8080 | Milvus 可视化控制台，仅开发调试用，可删除 |

首次启动说明：

- **务必先填密钥**：`DJANGO_SECRET_KEY`、`LLMAPI_ENCRYPTION_KEY` 为空时后端容器无法启动（见「环境变量」）。
- Milvus 启动较慢，健康检查预留了 90 秒（`start_period`），等 `docker compose ps` 显示 healthy 后再初始化向量集合。
- 首次部署需要初始化向量集合（对象存储 bucket 已由后端启动命令 `init_storage` 自动创建）：

```bash
docker compose exec backend python manage.py init_vectordb
```

- 文件上传经前端 Nginx 转发：`client_max_body_size 60m` 需大于后端 `MAX_UPLOAD_SIZE`（默认 50MB），调大上传上限时两处要同步修改。
- `MINIO_PUBLIC_ENDPOINT` 必须是浏览器实际能访问的 `host:port`（默认 `127.0.0.1:9004`），否则签名 URL 打不开；非本机访问时改为服务器地址/域名。
- `DJANGO_ALLOWED_HOSTS` 需包含实际访问的域名或 IP（compose 默认 `localhost,127.0.0.1,backend`）。

### 方式二：本地开发

#### 1. 启动依赖服务（可选，也可使用本机已安装的 PostgreSQL / Milvus / MinIO）

```bash
cd deploy
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
docker compose up -d db milvus minio-files   # 会自动带上 etcd、minio
```

#### 2. 后端

```bash
cd backend
uv sync                               # 安装依赖，生成/复用 .venv
```

本地直跑时默认连接 `127.0.0.1:5432` 的 PostgreSQL、`http://127.0.0.1:19530` 的 Milvus、`127.0.0.1:9004` 的 MinIO；数据库密码、MinIO 账号以及 Django / LLMapi 密钥需通过环境变量提供。

**方式 A（开发态最省事）**：在**同一终端**开启 DEBUG（DEBUG 下 `SECRET_KEY` 使用固定开发值、`LLMAPI_ENCRYPTION_KEY` 由 `SECRET_KEY` 派生，无需额外密钥），并导出数据库 / MinIO 账号：

```powershell
# Windows PowerShell
$env:DJANGO_DEBUG = "true"
$env:POSTGRES_PASSWORD = "123456"                       # 与 deploy/.env 一致
$env:MINIO_ACCESS_KEY = "huishutai_files"               # 即 deploy/.env 的 MINIO_ROOT_USER
$env:MINIO_SECRET_KEY = "ChangeMe_Strong_123"           # 即 deploy/.env 的 MINIO_ROOT_PASSWORD
```

随后直接执行下面「初始化命令」中的命令。

**方式 B**：复用 `deploy/.env`（需先把其中 `DJANGO_SECRET_KEY`、`LLMAPI_ENCRYPTION_KEY` 填好，或把 `DJANGO_DEBUG` 改为 `true`），并在每条命令前加 `--env-file`：

```bash
uv run --env-file "..\deploy\.env" python manage.py migrate
uv run --env-file "..\deploy\.env" python manage.py init_storage
uv run --env-file "..\deploy\.env" python manage.py init_vectordb
uv run --env-file "..\deploy\.env" python manage.py runserver 0.0.0.0:8000
```

初始化命令（使用方式 A 时执行这一段）：

```bash
uv run python manage.py migrate       # 初始化数据库表（0001 ~ 0004）
uv run python manage.py init_storage  # 检查 MinIO 并创建 bucket（幂等）
uv run python manage.py init_vectordb # 初始化向量集合（需 Milvus 可用）
uv run python manage.py runserver 0.0.0.0:8000
```

> 说明：后端默认按**非 DEBUG（生产模式）**启动，若既未设置 `DJANGO_DEBUG=true`、也未提供 `DJANGO_SECRET_KEY`，任何 `manage.py` 命令都会直接报 `ImproperlyConfigured`。若使用其他 MinIO 地址或端口，可覆盖 `MINIO_ENDPOINT`、`MINIO_PUBLIC_ENDPOINT`、`MINIO_BUCKET` 等变量（见「环境变量」）。

#### 3. 前端

```bash
cd frontend
npm install
npm run dev                           # http://localhost:5173
```

开发服务器会把 `/api/*` 代理到 `http://127.0.0.1:8000` 并去掉 `/api` 前缀，因此前端只需统一使用 `/api` 前缀（例如 `/api/user/login/` 对应后端的 `/user/login/`）。

#### 4. 构建与检查

前端生产构建（`type-check` 与 `vite build` 并行）：

```bash
cd frontend
npm run build
```

后端系统检查（需先提供 `DJANGO_DEBUG=true` 或 `DJANGO_SECRET_KEY`）：

```bash
cd backend
uv run python manage.py check
```

### 测试

**后端**：使用 SQLite 内存库 + mock 供应商适配器 / 外部依赖，不依赖 PostgreSQL / MinIO / Milvus，也不会发起真实外网请求：

```powershell
# Windows PowerShell
cd backend
$env:DJANGO_SETTINGS_MODULE = "tests.settings"
uv run python -B manage.py test tests -v 2
```

```bash
# Linux / macOS
cd backend
DJANGO_SETTINGS_MODULE=tests.settings uv run python -B manage.py test tests -v 2
```

当前实测结果：**358 个用例通过**（`Ran 358 tests ... OK (expected failures=7)`，约 4 秒）。其中 7 个以 `expectedFailure` 标记记录已知缺陷（3 个 LLMapi + 4 个 Workflow，详见「已知问题与待办」）；`user` / `files` / `vectordb` 仍是占位测试。

> 逐文件说明见 [backend/tests/README.md](backend/tests/README.md)，但其统计数字与已知缺陷清单为历史记录，其中部分缺陷已在后续提交修复、数字与当前实测不一致，请以实际运行结果为准。

**前端**：使用 Node.js 内置 `node:test` + Vite SSR 加载器 + mock 替身，不引入测试框架依赖，不联网、不连后端：

```bash
cd frontend
npm test                              # 等价于 node --test tests/
```

当前实测结果：**96 个用例，95 通过、1 个 todo、0 失败**（约 1.5 秒）。覆盖 API 契约（含与后端 14 条工作流路由对齐）、`WorkflowNode` / `WorkflowListView` / `WorkflowEditorView` 视图逻辑、路由与导航集成契约；不覆盖真实浏览器 DOM / e2e、CSS、Vue Flow 画布交互等。

> 测试组织与 mock 机制见 [frontend/tests/README.md](frontend/tests/README.md)；该文件部分统计（用例数、已修复缺陷清单、文件列表）与当前实测不一致，以实际运行为准。

## 代码质量与 CI

### 本地检查

```bash
# 后端（backend/）
uv sync
uv run ruff format --check .
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test          # 本地无 PostgreSQL 时用 tests.settings，见「测试」

# 前端（frontend/）
npm ci
npm run lint:check
npm run format:check
npm test
npm run type-check
npm run build
```

> `npm run lint` / `npm run format`（不带 `:check`）会直接改写文件，CI 与提交前请使用 `lint:check` / `format:check`。

### pre-commit

`.pre-commit-config.yaml` 提供本地提交钩子（后端 `ruff check --fix` + `ruff format`，前端 `prettier --write`）：

```bash
uv run --project backend pre-commit install
uv run --project backend pre-commit run --all-files
```

### CI（GitHub Actions）

工作流文件：[.github/workflows/ci.yml](.github/workflows/ci.yml)，在 `push` / `pull_request`（`devlop`、`main`）以及手动 `workflow_dispatch` 时触发，并带并发取消。

| Job | 内容 |
| --- | --- |
| `backend` | PostgreSQL 16 service；`uv lock --check` → `uv sync --frozen` → Ruff 格式 / Lint → `manage.py check` → `makemigrations --check --dry-run` → 后端测试（`DJANGO_SETTINGS_MODULE=tests.settings`） |
| `frontend` | Node 24 + `npm ci` → `npm run lint:check` → `npm run format:check` → `npm test` → `npm run type-check` → `npm run build` → 上传 `frontend/dist` artifact（保留 7 天） |
| `docker` | 依赖前两个 job；构建后端镜像并 `manage.py check` 冒烟（注入 `DJANGO_DEBUG` / `DJANGO_SECRET_KEY` / `LLMAPI_ENCRYPTION_KEY`）；构建前端镜像并 `nginx -t` 校验配置 |

> 注意：当前工作区对 `.github/workflows/ci.yml` 有一处未提交修改，正是为 Docker 冒烟步骤补齐上述环境变量（HEAD 版缺少这些变量时，后端镜像会因生产模式缺 `SECRET_KEY` 而检查失败），提交时请一并纳入。

### 依赖更新

[.github/dependabot.yml](.github/dependabot.yml) 每周检查后端 uv、前端 npm 与 GitHub Actions 依赖，自动创建更新 PR。

## 环境变量

后端直接从进程环境变量读取配置（`backend/config/settings.py`），未设置时使用默认值。

### Django 运行配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DJANGO_DEBUG` | `false` | 是否开启调试模式；默认按生产模式运行（`SESSION_COOKIE_SECURE` / HSTS 等随之生效） |
| `DJANGO_SECRET_KEY` | 空字符串 | Django `SECRET_KEY`，同时用于签名 Token；**为空时**：DEBUG 下使用开发固定值，非 DEBUG 下抛 `ImproperlyConfigured` 拒绝启动 |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | 允许的 Host，逗号分隔 |
| `DJANGO_SECURE_SSL_REDIRECT` | `false` | 是否强制 HTTPS 跳转（生产启用 HTTPS 时设为 `true`） |

### 数据库

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `POSTGRES_DB` | `huishutai` | 数据库名 |
| `POSTGRES_USER` | `huishutai` | 数据库用户 |
| `POSTGRES_PASSWORD` | 空字符串 | 数据库密码（需自行提供） |
| `POSTGRES_HOST` | `127.0.0.1` | 容器内由 compose 覆盖为 `db` |
| `POSTGRES_PORT` | `5432` | 数据库端口 |

### Milvus

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MILVUS_URI` | `http://127.0.0.1:19530` | Milvus 地址，容器内由 compose 覆盖为 `http://milvus:19530` |
| `MILVUS_TOKEN` | 空字符串 | Milvus 鉴权 token（开启鉴权时填写，如 `root:Milvus`） |
| `MILVUS_DB_NAME` | `default` | Milvus 数据库名 |
| `MILVUS_TIMEOUT` | `10` | Milvus 操作超时（秒） |
| `MILVUS_KNOWLEDGE_COLLECTION` | `knowledge_chunks` | 知识库集合名 |
| `MILVUS_KNOWLEDGE_DIM` | `1024` | 知识库向量维度（须与 embedding 模型一致） |
| `MILVUS_KNOWLEDGE_METRIC_TYPE` | `COSINE` | 向量相似度度量方式 |

### MinIO 文件存储

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MINIO_ENDPOINT` | `127.0.0.1:9004` | 后端访问 MinIO 的地址；容器内为 `minio-files:9000` |
| `MINIO_PUBLIC_ENDPOINT` | `127.0.0.1:9004` | 生成签名 URL 用的浏览器可达地址，必须与实际访问一致 |
| `MINIO_ACCESS_KEY` | 空字符串（回退 `MINIO_ROOT_USER`） | MinIO 访问账号 |
| `MINIO_SECRET_KEY` | 空字符串（回退 `MINIO_ROOT_PASSWORD`） | MinIO 访问密码 |
| `MINIO_SECURE` | `false` | 内网访问是否走 HTTPS |
| `MINIO_PUBLIC_SECURE` | `false` | 签名 URL 是否走 HTTPS |
| `MINIO_BUCKET` | `huishutai-files` | 文件 bucket 名称 |
| `MINIO_PRESIGN_EXPIRY` | `3600` | 签名 URL 有效期（秒，代码限制 60 秒 ~ 7 天） |
| `MAX_UPLOAD_SIZE` | `52428800`（50MB） | 单文件大小上限（字节） |

> 允许上传的扩展名在 `settings.ALLOWED_UPLOAD_EXTENSIONS` 中维护：`.pdf .txt .md .doc .docx .xls .xlsx .ppt .pptx .png .jpg .jpeg .gif .webp .zip`（共 15 种）。

### LLMapi

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLMAPI_ENCRYPTION_KEY` | 空字符串 | API Key 加密用的 Fernet key（base64）；DEBUG 下留空可由 `SECRET_KEY` 派生，**非 DEBUG 下留空会拒绝启动**，生产必须显式配置 |
| `LLMAPI_HTTP_TIMEOUT` | `30` | 调用供应商接口超时（秒） |
| `LLMAPI_MAX_MODELS` | `1000` | 单次模型列表同步的最大条数 |
| `LLMAPI_ALLOW_PRIVATE_BASE_URL` | `false` | 是否允许配置内网/本机 `base_url`（本地 Ollama 需要 `true`；生产保持 `false` 防 SSRF） |

### 容器化部署变量样板

`deploy/.env.example`（复制为 `deploy/.env` 后使用，`.env` 已被 git 忽略）：

```env
# ===== Postgres =====
POSTGRES_DB=huishutai
POSTGRES_USER=huishutai
POSTGRES_PASSWORD=123456

# ===== Milvus =====
MILVUS_URI=http://milvus:19530
MILVUS_TOKEN=
MILVUS_DB_NAME=default
MILVUS_KNOWLEDGE_COLLECTION=knowledge_chunks
MILVUS_KNOWLEDGE_DIM=1024
MILVUS_KNOWLEDGE_METRIC_TYPE=COSINE

# ===== 文件对象存储（独立 MinIO，与 Milvus 的 minio 隔离） =====
MINIO_ROOT_USER=huishutai_files
MINIO_ROOT_PASSWORD=ChangeMe_Strong_123
MINIO_BUCKET=huishutai-files
# 浏览器访问 MinIO 的 host:port，签名 URL 用它拼地址，必须与实际访问一致
MINIO_PUBLIC_ENDPOINT=127.0.0.1:9004
MINIO_FILES_API_PORT=9004
MINIO_FILES_CONSOLE_PORT=9005
MINIO_PRESIGN_EXPIRY=3600
# 单文件上限（字节），默认 50MB
MAX_UPLOAD_SIZE=52428800

# ===== LLMapi =====
# Fernet 密钥；留空则由 SECRET_KEY 派生（生产必须显式配置）
# 生成：uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
LLMAPI_ENCRYPTION_KEY=
LLMAPI_HTTP_TIMEOUT=30
LLMAPI_ALLOW_PRIVATE_BASE_URL=false

DJANGO_SECRET_KEY=
# 请用下面的命令生成DJANGO_SECRET_KEY
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend,你的域名
```

> 当前 compose 向后端容器注入 `POSTGRES_*`、固定 `MILVUS_URI`、`MINIO_*`、`MAX_UPLOAD_SIZE`、`LLMAPI_*` 以及 `DJANGO_SECRET_KEY` / `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS`；`MILVUS_TOKEN`、`MILVUS_DB_NAME`、`MILVUS_KNOWLEDGE_*`、`DJANGO_SECURE_SSL_REDIRECT` 尚未透传，如需自定义需在 `deploy/docker-compose.yml` 的 backend `environment` 中补充。
>
> 容器默认 `DJANGO_DEBUG=false`，因此 `DJANGO_SECRET_KEY` 与 `LLMAPI_ENCRYPTION_KEY` 在 compose 场景都是必填项。

## 接口文档

### 约定

- 后端路由直接挂在根路径（如 `/user/login/`）；前端统一请求 `/api/*`，由 Vite（开发）或 Nginx（生产）转发并去掉 `/api` 前缀。
- 请求体与响应体均为 JSON（文件上传为 `multipart/form-data`），响应统一为 `{ "code": 0, "message": "...", "data": ... }`。
- 除标注「公开」的接口外，均需要携带 `Authorization: Bearer <token>`，否则返回 HTTP 401。
- 下列路径均为 Django 侧路径（未加 `/api` 前缀）。当前后端共注册 **31 条**叶子路由，联调时可用 `GET /routes/` 获取全部路由。

### 接口列表

**用户**

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| POST | `/user/register/` | 注册，成功后直接返回 token | 公开 |
| POST | `/user/login/` | 登录，返回 token | 公开 |
| POST | `/user/logout/` | 退出登录（服务端无状态，前端清除 token 即可） | 公开 |
| GET | `/user/check-username/?username=xxx` | 用户名查重 | 公开 |
| GET / PATCH | `/user/info/` | 获取 / 修改当前用户资料（email / phone / gender） | 需登录 |
| POST | `/user/password/` | 修改密码（old_password / new_password / confirm_password） | 需登录 |

**文件与调试**

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| POST | `/files/upload/` | 上传文件（multipart 字段 `file`），返回元数据与临时签名 URL | 需登录 |
| GET | `/routes/` | 返回后端已注册路由列表（路径 / 名称 / 视图 / HTTP 方法） | 需登录 |

**大模型（LLMapi）**

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| GET | `/llm/provider-templates/` | 内置供应商模板 + 模型分类 | 需登录 |
| GET / POST | `/llm/providers/` | 列出 / 新增供应商配置（新增时尝试在线同步模型） | 需登录 |
| GET / PATCH / DELETE | `/llm/providers/<id>/` | 查看 / 更新 / 删除供应商配置 | 需登录 |
| POST | `/llm/providers/<id>/refresh-models/` | 重新在线同步模型列表 | 需登录 |
| GET / POST | `/llm/providers/<id>/models/` | 查看该供应商模型 / 手动登记模型 | 需登录 |
| GET | `/llm/models/` | 我的模型列表（按分类分组，支持 `category`、`provider_id` 过滤） | 需登录 |
| PATCH / DELETE | `/llm/models/<pk>/` | 更新（启用/禁用、改名）/ 删除模型 | 需登录 |
| POST | `/llm/chat/` | 统一对话调用（仅 `chat` 分类模型） | 需登录 |
| POST | `/llm/embeddings/` | 统一嵌入调用（仅 `embedding` 分类模型） | 需登录 |

**工作流（Workflow）** —— 全部需登录，另有 owner / editor / viewer 业务权限

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET / POST | `/workflow/workflows/` | 我的工作流列表 / 创建（创建者即 owner） |
| GET / PATCH / DELETE | `/workflow/workflows/<id>/` | 获取完整状态（工作流 + 节点 + 连线 + 成员 + 事件序号 + 节点类型）/ 改名改描述 / 删除（仅 owner） |
| GET | `/workflow/workflows/<id>/events/?after=&limit=` | 增量事件（协作同步，默认 after=0、limit=100） |
| POST | `/workflow/workflows/<id>/nodes/` | 新增节点 |
| PATCH / DELETE | `/workflow/workflows/<id>/nodes/<node_key>/` | 更新节点（需 `base_version` 乐观锁）/ 删除节点 |
| POST | `/workflow/workflows/<id>/edges/` | 新增连线 |
| DELETE | `/workflow/workflows/<id>/edges/<edge_id>/` | 删除连线 |
| GET / POST | `/workflow/workflows/<id>/members/` | 查看成员（实际返回整份工作流状态）/ 邀请成员（仅 owner） |
| DELETE | `/workflow/workflows/<id>/members/<user_id>/` | 移除成员（仅 owner） |
| POST | `/workflow/workflows/<id>/import/` | 导入工作流 JSON（整体替换当前图，仅 owner / editor） |
| GET | `/workflow/workflows/<id>/export/` | 导出工作流 JSON |
| POST | `/workflow/workflows/<id>/run/` | 运行工作流（同步返回执行结果；执行失败时 `code=0`、`data.status=failed`） |
| GET | `/workflow/node-types/` | 可用节点类型列表 |
| GET | `/workflow/node-types/<node_type>/` | 单个节点类型的元信息（端口 / 参数规格） |

### 用户接口示例

**注册**

```http
POST /user/register/
Content-Type: application/json

{ "username": "demo", "password": "123456", "confirm_password": "123456" }
```

```json
{
  "code": 0,
  "message": "注册成功",
  "data": { "token": "<签名token>", "user_id": 1, "username": "demo" }
}
```

**登录**

```http
POST /user/login/
Content-Type: application/json

{ "username": "demo", "password": "123456" }
```

```json
{
  "code": 0,
  "message": "登录成功",
  "data": { "token": "<签名token>", "user_id": 1, "username": "demo" }
}
```

**获取 / 修改资料**

```http
GET /user/info/
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": { "user_id": 1, "username": "demo", "email": "", "phone": "", "gender": "unknown" }
}
```

```http
PATCH /user/info/
Authorization: Bearer <token>
Content-Type: application/json

{ "email": "demo@example.com", "phone": "13800138000", "gender": "male" }
```

字段均为可选，只更新请求中出现的字段；全部未提供时返回「没有需要更新的字段」。

**修改密码**

```http
POST /user/password/
Authorization: Bearer <token>
Content-Type: application/json

{ "old_password": "123456", "new_password": "654321", "confirm_password": "654321" }
```

### 文件上传示例

```bash
curl -X POST http://127.0.0.1:8000/files/upload/ \
     -H "Authorization: Bearer <token>" \
     -F "file=@demo.pdf"
```

```json
{
  "code": 0,
  "message": "上传成功",
  "data": {
    "id": 1,
    "user_id": 1,
    "original_name": "demo.pdf",
    "bucket": "huishutai-files",
    "object_key": "uploads/1/2026/10/2f6f...c1.pdf",
    "file_hash": "<sha256>",
    "file_size": 12345,
    "content_type": "application/pdf",
    "created_at": "2026-10-29T21:00:00+00:00",
    "url": "http://127.0.0.1:9004/huishutai-files/uploads/...?X-Amz-Signature=...",
    "url_expires_in": 3600
  }
}
```

> `url` 为临时签名链接，过期后需重新上传或重新签名；当前尚未提供「我的文件」列表 / 重新签名 / 删除接口。

### LLM 接口示例

**新增供应商配置**（保存后会自动尝试拉取模型列表）

```http
POST /llm/providers/
Authorization: Bearer <token>
Content-Type: application/json

{ "template_code": "deepseek", "name": "我的 DeepSeek", "api_key": "sk-xxxx" }
```

```json
{
  "code": 0,
  "message": "配置已保存，模型列表已同步",
  "data": {
    "provider": {
      "id": 1,
      "name": "我的 DeepSeek",
      "template_code": "deepseek",
      "template_name": "DeepSeek",
      "protocol": "openai",
      "base_url": "https://api.deepseek.com/v1",
      "api_key_masked": "sk-****xxxx",
      "enabled": true,
      "model_count": 8,
      "last_synced_at": null,
      "last_sync_error": "",
      "created_at": "2026-10-29T13:00:00+00:00"
    },
    "model_sync": { "status": "ok", "count": 8, "message": "模型列表已同步" }
  }
}
```

> 内置供应商模板（`template_code`）：`openai`、`deepseek`、`zhipu`、`moonshot`、`dashscope`、`siliconflow`、`openrouter`、`ollama`（本地、免 Key）、`anthropic`、`gemini`。接口不会返回明文 API Key。

**统一对话调用**

```http
POST /llm/chat/
Authorization: Bearer <token>
Content-Type: application/json

{
  "model_id": 12,
  "messages": [
    { "role": "system", "content": "你是一个简洁的助手" },
    { "role": "user", "content": "用一句话介绍汇书台" }
  ],
  "params": { "temperature": 0.7, "max_tokens": 512 }
}
```

```json
{
  "code": 0,
  "message": "调用成功",
  "data": {
    "model_id": 12,
    "model": "deepseek-chat",
    "provider": "我的 DeepSeek",
    "protocol": "openai",
    "content": "汇书台是一个面向 AI 应用落地的技术整合实践项目。",
    "finish_reason": "stop",
    "usage": { "prompt_tokens": 25, "completion_tokens": 18, "total_tokens": 43 },
    "raw": { "...": "供应商原始响应" }
  }
}
```

> 这里的 `model_id` 是数据库 `llm_model.id`（主键），不是供应商侧的模型字符串；模型需属于当前用户的供应商配置且处于启用状态。

**统一嵌入调用**

```http
POST /llm/embeddings/
Authorization: Bearer <token>
Content-Type: application/json

{ "model_id": 13, "input": ["第一段文本", "第二段文本"], "params": { "dimensions": 1024 } }
```

```json
{
  "code": 0,
  "message": "调用成功",
  "data": {
    "model_id": 13,
    "model": "text-embedding-3-small",
    "provider": "我的 OpenAI",
    "protocol": "openai",
    "embeddings": [[0.0123, -0.0456, 0.0789]],
    "dimensions": 1024,
    "usage": { "prompt_tokens": 12, "total_tokens": 12 }
  }
}
```

> `embeddings` 为二维数组，示例中仅展示单个向量前 3 个分量。

**错误响应示例**

```json
{ "code": 1002, "message": "用户名已存在", "data": null }
```

```json
{ "code": 4003, "message": "API Key 无效或无权限，配置未保存", "data": null }
```

```json
{ "code": 4001, "message": "调用参数不合法", "data": { "errors": ["参数 temperature 不能大于 2"] } }
```

### 工作流接口示例

**创建工作流**

```http
POST /workflow/workflows/
Authorization: Bearer <token>
Content-Type: application/json

{ "name": "内容摘要流水线", "description": "抓取网页 → 大模型总结" }
```

```json
{
  "code": 0,
  "message": "工作流已创建",
  "data": {
    "workflow": {
      "id": 1,
      "name": "内容摘要流水线",
      "description": "抓取网页 → 大模型总结",
      "owner_id": 1,
      "owner_name": "demo",
      "role": "owner",
      "node_count": 0,
      "created_at": "2026-11-15T10:00:00+00:00",
      "updated_at": "2026-11-15T10:00:00+00:00"
    }
  }
}
```

**新增节点**（`node_type` 取自 `GET /workflow/node-types/`，如 `start` / `llm` / `condition` / `http`）

```http
POST /workflow/workflows/1/nodes/
Authorization: Bearer <token>
Content-Type: application/json

{ "node_type": "start", "name": "开始", "position": { "x": 80, "y": 160 }, "config": { "payload": "{}" } }
```

```json
{
  "code": 0,
  "message": "节点已添加",
  "data": {
    "node": {
      "key": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
      "node_type": "start",
      "name": "开始",
      "position": { "x": 80, "y": 160 },
      "config": { "payload": "{}" },
      "version": 1,
      "created_at": "2026-11-15T10:01:00+00:00",
      "updated_at": "2026-11-15T10:01:00+00:00"
    }
  }
}
```

**新增连线**

```http
POST /workflow/workflows/1/edges/
Authorization: Bearer <token>
Content-Type: application/json

{ "source_key": "<start 节点 key>", "source_port": "out", "target_key": "<llm 节点 key>", "target_port": "in" }
```

```json
{
  "code": 0,
  "message": "连线已添加",
  "data": {
    "relation": {
      "id": 1,
      "source_key": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
      "source_port": "out",
      "target_key": "a1b2c3d4e5f6...",
      "target_port": "in",
      "created_at": "2026-11-15T10:02:00+00:00"
    }
  }
}
```

**更新节点**（乐观锁：`base_version` 必须等于节点当前 `version`，否则返回 5004 / HTTP 409）

```http
PATCH /workflow/workflows/1/nodes/<node_key>/
Authorization: Bearer <token>
Content-Type: application/json

{
  "base_version": 1,
  "position": { "x": 120, "y": 200 },
  "config": { "payload": "{\"topic\":\"AI\"}" }
}
```

**运行工作流**（同步执行；请求被受理即 `code=0`，成败看 `data.status`）

```http
POST /workflow/workflows/1/run/
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "执行完成",
  "data": {
    "status": "success",
    "error": "",
    "steps": [
      {
        "node_key": "0f1e2d3c...",
        "node_type": "start",
        "name": "开始",
        "status": "success",
        "output": { "payload": {} },
        "logs": ["工作流开始"],
        "duration_ms": 0
      }
    ],
    "output": { "payload": {} },
    "duration_ms": 12
  }
}
```

**增量事件（协作同步）**

```http
GET /workflow/workflows/1/events/?after=10&limit=100
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "events": [
      {
        "id": 11,
        "op": "node_added",
        "payload": { "node": { "key": "...", "node_type": "start" } },
        "actor_id": 2,
        "actor_name": "collaborator",
        "created_at": "2026-11-15T10:05:00+00:00"
      }
    ],
    "last_event_seq": 11
  }
}
```

**导入 / 导出**

```json
{
  "format": "huishutai.workflow",
  "format_version": 1,
  "name": "内容摘要流水线",
  "description": "抓取网页 → 大模型总结",
  "nodes": [
    { "key": "n1", "type": "start", "name": "开始", "position": { "x": 80, "y": 160 }, "config": { "payload": "{}" } },
    { "key": "n2", "type": "llm", "name": "大模型", "position": { "x": 360, "y": 160 }, "config": { "model_id": 12 } }
  ],
  "relations": [
    { "source": "n1", "source_port": "out", "target": "n2", "target_port": "in" }
  ]
}
```

> 导入为整体替换当前图，需满足：≤200 节点 / ≤500 连线、节点类型存在、key 唯一、恰好一个 `start`、端口合法、禁止自连 / 成环 / 重复边；空 `nodes` 可用于清空画布。导出文档结构与此一致。

**错误响应示例**

```json
{ "code": 5004, "message": "节点已被其他人修改，请刷新后重试", "data": null }
```

```json
{ "code": 5003, "message": "只读成员不能修改工作流", "data": null }
```

```json
{ "code": 5001, "message": "不允许形成环", "data": null }
```

### 参数校验规则

**用户模块**

| 字段 | 规则 |
| --- | --- |
| username | 3–50 位，仅限中文、字母、数字、下划线 |
| password | 6–128 位 |
| email | 合法邮箱格式（可为空） |
| phone | 11 位中国大陆手机号（可为空） |
| gender | `male` / `female` / `unknown` |

**文件上传**

| 项 | 规则 |
| --- | --- |
| 大小 | 大于 0 且不超过 `MAX_UPLOAD_SIZE`（默认 50MB） |
| 扩展名 | 必须在 `ALLOWED_UPLOAD_EXTENSIONS` 白名单内（15 种） |

**LLM 调用**

| 字段 | 规则 |
| --- | --- |
| `messages` | 非空数组；每项含 `role`（`system` / `user` / `assistant`）与 `content`（字符串或数组）；至少一条 `user` 消息 |
| `input` | 非空字符串，或非空字符串数组 |
| `params` | JSON 对象，按模型 `param_spec` 白名单校验类型、范围、枚举；自动合并默认值；缺少必填参数会报错 |
| `base_url` | 必须是 http(s) URL；不能包含用户名密码、query、fragment；`LLMAPI_ALLOW_PRIVATE_BASE_URL=false`（默认）时拒绝解析到内网 / 本机 / 保留地址的域名 |
| `model_id` | 整数，须为当前用户所属且已启用的模型主键 |

> `model` / `messages` / `input` / `stream` 属于系统控制参数，不允许通过 `params` 传入。

**工作流**

| 字段 / 项 | 规则 |
| --- | --- |
| `name` / `description` | 创建与更新时名称非空、最长 100；描述最长 500 |
| `node_type` | 必须是 `Workflow/node/` 下已存在的节点类型 |
| `position` | `{ "x": number, "y": number }`；导入时缺省为 0 |
| `config` | JSON 对象；节点内部会按自身参数规格校验（如 `llm.model_id` 必填） |
| `base_version` | 更新节点时必填整数，须与节点当前 `version` 一致，否则 5004 / HTTP 409 |
| 连线 | `source_key` / `target_key` 必须存在且不能相同；`source_port` / `target_port` 必须属于对应节点的端口；禁止成环；同一五元组不能重复 |
| 导入 | 文件格式 `huishutai.workflow`；≤200 节点 / ≤500 连线；节点 key 唯一；恰好一个 `start`；端口合法；禁止自连 / 成环 / 重复边；整体事务替换 |
| 运行 | owner / editor 可运行；viewer 不可运行；单次最多执行 100 步 |

## 数据库与向量库

### 迁移与初始化

```bash
cd backend
uv run python manage.py makemigrations   # 修改模型后生成迁移
uv run python manage.py migrate          # 应用迁移（0001 ~ 0004）
uv run python manage.py init_storage     # 检查 MinIO 并创建 bucket（幂等）
uv run python manage.py init_vectordb    # 幂等创建 Milvus 集合（已存在则跳过）
```

> 上述命令都需要后端配置可加载：本地需 `DJANGO_DEBUG=true` 或提供 `DJANGO_SECRET_KEY`。

**迁移记录**

| 迁移 | 内容 |
| --- | --- |
| `0001_initial` | `user` / `user_info` |
| `0002_uploadedfile` | `uploaded_file` + 唯一约束 + 索引 |
| `0003_llmproviderconfig_llmmodel_and_more` | `llm_provider_config` / `llm_model` + 唯一约束 + 索引 |
| `0004_workflow_*` | `workflow` / `workflow_member` / `workflow_node` / `workflow_edge` / `workflow_event` 5 张表 + 索引与唯一约束 |

### 扩展约定

**新增关系库表**

1. 在 `backend/sqldb/models.py` 定义模型；
2. 执行 `makemigrations sqldb` 生成迁移；
3. 在 `backend/sqldb/crud/<table>.py` 中继承 `BaseCRUD` 并注入模型；
4. 在 `backend/sqldb/crud/__init__.py` 导出 `<table>_crud` 实例；
5. 业务层只通过 `sqldb.crud` 提供的数据访问对象操作数据。

**新增向量集合**

1. 在 `backend/vectordb/schemas.py` 中定义 `CollectionSchema`；
2. 在 `backend/vectordb/crud/` 下实例化 `VectorCollection` 并导出；
3. 参考 `init_vectordb` 命令或直接在业务层调用 `ensure()` 幂等建集合。

**新增 LLM 供应商模板 / 参数规格**

1. 在 `backend/LLMapi/templates.py` 增加 `ProviderTemplate`（协议需属于 `openai` / `anthropic` / `gemini`，或在 `adapters.py` 注册新协议适配器）；
2. 在 `backend/LLMapi/model_meta.py` 的 `build_param_spec` 中按协议 / 分类补充参数白名单；
3. 模型分类与参数规格会在同步模型时写入 `llm_model`，可用 `LLMAPI_MAX_MODELS` 限制单次同步数量。

**新增工作流节点类型**

1. 在 `backend/Workflow/node/` 下新建 `<type>.py`（文件名即类型名，需匹配 `^[a-z][a-z0-9_]{0,63}$`）；
2. 模块内定义 `NODE_META`（名称、分类、输入/输出端口、参数规格）与 `execute(config, input_data, context) -> NodeResult`；
3. 无需注册：`node_loader` 会扫描目录并按需加载，前端通过 `GET /workflow/node-types/` 自动获得新节点；
4. 在 `backend/tests/` 补充节点测试（参照 `test_workflow_nodes.py`）。

## 前端说明

### 路由

| 路径 | 页面 | 访问控制 |
| --- | --- | --- |
| `/` | 布局路由（AppLayout：侧边栏 + 顶栏），子路径为空时重定向 `/home` | 需登录 |
| `/home` | 首页 / 应用入口（知识库、模型服务、工作流；Agent 等显示「即将上线」） | 需登录 |
| `/knowledge` | 知识库（文件上传、上传历史、签名链接、复制/打开） | 需登录 |
| `/models` | 模型服务（供应商配置、模型目录、参数规格、手动登记模型） | 需登录 |
| `/workflows` | 工作流列表（新建、角色徽标、删除） | 需登录 |
| `/workflows/:id` | 工作流编辑器（无限画布、节点/连线、运行、导入导出、成员协作） | 需登录 |
| `/profile` | 个人中心（资料查看/编辑、修改密码、退出登录） | 需登录 |
| `/login` | 登录页 | 仅未登录可访问 |
| `/register` | 注册页（含用户名实时查重） | 仅未登录可访问 |
| 其它路径 | 重定向到 `/home` | — |

路由守卫读取本地登录态：未登录访问受保护页面会跳转登录页并记录 `redirect` 参数；已登录访问登录/注册页会跳回 `/home`。`afterEach` 把浏览器标题设为「页面标题 · 汇书台」。

### 页面与组件

- **AppLayout**：侧边栏（首页 / 知识库 / 工作流 / 模型服务，可折叠并持久化）、面包屑、主题切换、用户菜单与退出登录。
- **AppIcon**：基于 `@lucide/vue` 的语义化图标映射（约 48 个键），未知键回退 `Circle`。
- **WorkflowNode**：画布节点渲染（节点类型图标、多输入/输出端口按百分比分布）。
- **状态管理（Pinia）**：`auth`（token / 用户信息）、`theme`（亮暗主题，默认跟随系统，持久化 `huishutai-theme`）、`toast`（成功/警告/错误/提示，自动消失）、`uploads`（上传历史按用户隔离存 `localStorage`，最多 50 条）。
- **样式体系**：`tokens.css` 提供亮/暗双主题的设计令牌（颜色、字号、间距、圆角、阴影等），`app.css` 为应用外壳与通用组件样式，`workflow.css` 为工作流列表/画布/抽屉样式；无 UI 组件库。
- **请求封装**：axios 实例 `baseURL: '/api'`、默认超时 10s，自动附加 `Authorization: Bearer <token>`，响应直接解包 `{code, message, data}`；401 时清除登录态并跳转登录页；业务错误优先展示后端 `message`。

### 工作流编辑器

- **画布**：Vue Flow 无限画布 + 背景网格 + 缩放控制 + 小地图；支持拖拽节点、从端口拉线、框选、Delete/Backspace 删除选中、Esc 关闭弹层；缩放范围 0.25–2、连接严格模式、网格吸附。
- **节点目录**：右侧浮层按后端节点类型动态列出，展开时按需拉取节点元信息；点击添加节点，默认参数取元信息中的默认值。
- **参数配置**：按节点参数规格动态渲染 text / textarea / number / boolean / select / json 控件；保存时做 JSON / 数字 / 布尔转换与必填校验。
- **运行**：点击运行后同步调用后端（前端超时 120s），结果弹窗展示总状态、耗时、错误与每步状态 / 名称 / 类型 / 耗时 / 输出 JSON。
- **协作**：每 2s 轮询事件接口，检测到他人修改时静默刷新并提示；成员弹窗支持 owner 按用户名邀请 editor / viewer、移除成员；viewer 只读并隐藏写操作。
- **导入 / 导出**：导入 JSON 文件（确认后整体覆盖当前图），导出为 `<工作流名>.json` 下载。
- **当前限制**：无回放（事件仅用于增量同步）、无撤销/重做、无自动布局、节点只能点击目录添加（不支持拖入画布）、不能修改工作流名称/描述、运行同步无流式与历史记录、协作基于 2s 轮询（非 WebSocket）、多入边节点只取第一条入边输出。

### 设计原型（prototype/）

`frontend/prototype/` 是早期 UI 概念原型（8 个静态 HTML：登录/注册/首页/知识库/模型/个人中心/原型总览/设计规范，配套 4 个 CSS 与 `shell.js` 交互脚本），用于设计评审与样式参考：

- **不参与**构建、部署与路由（Dockerfile 只复制 `dist`，Nginx 只服务构建产物）；
- 被 ESLint / Prettier 配置排除（`eslint.config.js`、`.prettierignore`）；
- 早于工作流模块，原型中没有工作流页面；实际实现以 `src/` 为准。

### 部署与代理

生产环境由 Nginx 托管构建后的静态资源并反向代理 `/api`：配置了 `client_max_body_size 60m`、`proxy_request_buffering off` 与 300s 读写超时，用于支撑文件上传和大模型 / 工作流长耗时调用；`try_files $uri $uri/ /index.html` 保证 Vue Router history 模式可用。

## 分支说明

- `devlop`：当前默认开发分支，新功能与修复请基于该分支进行。
- `ZYP`：协作分支（登录/注册功能已合入 `devlop`）。
- `main`：基础应用设施分支。
- CI 在 `devlop` / `main` 的 push 与 PR 上触发。
- 仓库通过 `.gitattributes` 统一换行：文本文件以 LF 存储，Windows 脚本（`*.bat` / `*.cmd` / `*.ps1`）保留 CRLF。

## 已知问题与待办

- **RAG / Agent**：`RAG` 仅为应用骨架（无路由、无业务逻辑）；知识库页的文档解析、向量化与问答为占位；Agent、文生图、文生视频尚未开始。
- **工作流首版限制**：无回放 / 撤销 / 重做 / 自动布局；节点仅支持点击目录添加；不支持修改工作流名称/描述（`updateWorkflow` 接口已有、前端未接入）；运行为同步调用、无流式与运行历史；协作依赖 2s HTTP 轮询；多入边节点只取第一条入边；viewer 不能运行；导入会整体覆盖当前图且不可撤销。
- **工作流 / LLMapi 已知缺陷（7 个 `expectedFailure`）**：
  1. `rerank` 模型被误分类为 `embedding`（`bge-reranker` 等命中 embedding 关键字，`LLMapi/model_meta.py`）；
  2. 创建 / 同步供应商后未写入 `last_synced_at`（仅刷新模型时写入，`LLMapi/services.py`）；
  3. chat 网关的 `model_id` 使用 `int()` 强转，`1.5` / `True` 会被静默截断（`LLMapi/services.py`）；
  4. 执行器空图提示不准确：「工作流为空」分支不可达（`Workflow/executor.py`）；
  5. 执行器步数判断差一错误：恰好执行 100 步且队列已空的合法图被判超限（`Workflow/executor.py`）；
  6. `start` 节点接受 JSON 数组 / 标量字符串作为初始数据，与「必须是 JSON 对象」文案矛盾（`Workflow/node/start.py`）；
  7. `llm` 节点的 `model_id` / `max_tokens` 非整数会被 `int()` 截断（`Workflow/node/llm.py`）。
- **调用网关覆盖范围**：当前只提供 chat / embeddings 两个调用入口；`rerank` / `image` / `audio` 分类的模型可被识别和列出，但尚无对应调用接口；仅支持同步一次性调用，未支持流式输出与工具调用。工作流大模型节点复用 chat 网关。
- **文件模块缺口**：「我的文件」列表、删除、重新签名等 HTTP 接口尚未提供；知识库页的上传历史来自 `localStorage`（按用户隔离），删除仅移除本地记录。
- **前端已知小问题**：登录页「保持登录」复选框为静态展示、未绑定逻辑（token 始终持久化）；运行结果弹窗未展示节点 `logs`；`selectedEdgeId` 状态未被模板消费；`ModelsView.vue` 存在未使用的深层类型导入与一条 ESLint 警告（不影响构建）；无浏览器 DOM / e2e 测试。
- **测试覆盖不均**：LLMapi 与 Workflow 有较完整的后端回归测试；`user` / `files` / `vectordb` 仍为占位测试。前端测试仅覆盖工作流模块，且不覆盖真实 DOM / 画布交互 / 第三方库行为。
- **测试文档与现状不同步**：[backend/tests/README.md](backend/tests/README.md) 写「16 个预期失败 / CI 使用默认 PostgreSQL 配置」，实际为 7 个 `expectedFailure` 且 CI 使用 `tests.settings`；[frontend/tests/README.md](frontend/tests/README.md) 引用了已不存在的 `workflow-known-defects.test.mjs`、统计为 106 用例 / 7 todo，实际为 5 个测试文件 / 96 用例 / 1 todo，其列出的部分缺陷已修复。后续提交时建议同步更新这两个文档。
- **安全配置**：生产环境必须显式配置 `DJANGO_SECRET_KEY`、`LLMAPI_ENCRYPTION_KEY` 与非空 `DJANGO_ALLOWED_HOSTS`；`DJANGO_DEBUG` 默认关闭（生产模式安全开关默认生效），但 `DJANGO_SECURE_SSL_REDIRECT` 默认 `false`，启用 HTTPS 时需手动开启；`MINIO_PUBLIC_ENDPOINT` 必须与浏览器实际访问的 `host:port` 一致。
- **SSRF 防护**：`LLMAPI_ALLOW_PRIVATE_BASE_URL` 默认 `false`（本地 Ollama 场景需显式设为 `true`）；URL 校验仅在 DNS 解析阶段进行，未固定解析结果，DNS rebinding 场景未防护；工作流 HTTP 节点始终拒绝内网 / 本机地址。
- **仓库清理项**：`backend/api` 中的 `Book` 模型 / 序列化器 / 迁移为早期示例（无 ViewSet、未挂路由，但迁移会创建 `api_book` 表）；`backend/sqldb/crud/user_crud.py` 为旧版数据访问实现（未被引用，且调用了不存在的 `User.set_password`）；根目录 `package-lock.json` 为空锁文件（无对应根 `package.json`）；`backend/README.md` 为空文件、`frontend/README.md` 仍为 Vite 模板说明；Django admin 已安装但未挂载路由（`/admin` 不可用）；`files/services.py` 顶部的文档字符串仍是旧路径描述。
- **未实现功能**：邮箱验证、找回密码、用户列表 / 权限管理、OpenAPI 接口文档、文件列表 / 删除 / 重新签名接口、知识库文档解析与问答。
- **提交提醒**：README 更新时，工作区中 `.github/workflows/ci.yml` 的未提交修复（Docker 冒烟检查补充密钥环境变量）建议一并提交；`frontend/dist/`、`backend/.venv/` 等构建产物已被 `.gitignore` 忽略。
