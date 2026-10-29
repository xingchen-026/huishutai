# 汇书台（huishutai）

> 面向 AI 应用落地的技术整合实践项目：把 RAG、Agent、文生图、文生视频等 AI 能力，与用户管理、文件存储、模型供应等基础技术服务结合，沉淀一套可复用的应用落地方案。

## 项目简介

**汇书台**是一个用于整合 AI 应用落地相关技术的工程实践项目。项目按「基础服务 → 数据访问层 → AI 能力」的顺序推进：先完成用户体系、文件对象存储、关系库/向量库访问层与模型供应网关等基础设施，再按模块接入检索增强、大模型应用等能力。

当前阶段：

- **已完成**：用户管理（后端 + 前端）、文件上传与对象存储、大模型供应商配置 / 模型目录 / 统一对话与嵌入调用网关（后端），以及 `sqldb`（PostgreSQL）、`vectordb`（Milvus）数据访问层。
- **开发中**：RAG 检索增强（仅应用骨架）、前端新功能页面（文件上传、模型配置目前只有后端接口）。
- **规划中**：Agent、文生图、文生视频。

## 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 用户管理 | ✅ 已完成 | 注册 / 登录 / 登出 / 用户名查重 / 个人资料 / 修改密码，后端接口 + 前端页面齐备 |
| 文件上传与对象存储 | ✅ 后端完成 | MinIO 对象存储 + PostgreSQL 元数据 + 临时签名 URL；前端页面未接入 |
| 大模型供应（LLMapi） | ✅ 后端完成 | 供应商模板与配置、在线模型同步、参数规格与校验、统一 chat / embeddings 网关、API Key 加密 |
| 关系库数据层 `sqldb` | ✅ 已完成 | 通用 CRUD 基类、统一结果对象、状态码；已覆盖用户 / 文件 / 模型 5 张表 |
| 向量库数据层 `vectordb` | 🚧 封装完成，未暴露接口 | Milvus 客户端、集合 CRUD、`init_vectordb` 初始化命令 |
| RAG 检索增强 | 🚧 仅骨架 | 应用已注册，业务逻辑与接口待实现 |
| Agent / 文生图 / 文生视频 | 📋 规划中 | — |
| 自动化测试 | 🚧 部分覆盖 | LLMapi 回归测试 128 个用例（4 个预期失败记录已知缺陷）；用户 / 文件 / 向量库仍为占位测试 |
| 容器化部署 | ✅ 已完成 | 前端 + 后端 + PostgreSQL + Milvus + 独立 MinIO（文件存储）统一编排 |

## 功能特性

- **用户体系**：注册、登录、登出、用户名查重、个人资料查看/修改、修改密码。
- **签名 Token 认证**：基于 `django.core.signing`，不新增 token 表；默认所有接口要求登录，公开接口单独放开。
- **文件上传**：登录用户上传文件，校验大小与扩展名，流式计算 SHA-256，写入 MinIO，元数据落 PostgreSQL，返回可临时访问的签名 URL；上传失败自动回滚已写入对象。
- **大模型供应与统一调用**：内置 10 个供应商模板（OpenAI 兼容 / Anthropic / Gemini 三类协议），API Key 加密存储且接口只回显掩码；在线拉取模型列表并分类、生成调用参数白名单；通过统一网关调用对话与嵌入模型，按模型参数规格严格校验。
- **分层数据访问**：业务层不直接写 ORM，统一经 `sqldb` / `vectordb` 数据层访问数据库，返回结果收敛为 `DBResult` / `VDBResult` / `LLMResult`。
- **路由自检**：`GET /routes/` 返回后端已注册路由的路径、名称、视图与 HTTP 方法，便于联调时核对接口。
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
| uv | 依赖与虚拟环境管理（`pyproject.toml` + `uv.lock`） |
| PostgreSQL | 16（驱动 `psycopg2-binary` 2.9.13） |
| Milvus | 2.6（SDK `pymilvus` 2.6.17） |
| MinIO | 对象存储（SDK `minio` 7.2.20），业务文件独立部署 |
| cryptography | 50.0.2（Fernet 加密 API Key） |
| requests | 2.34.2（调用大模型供应商 HTTP 接口） |
| black | >=26.10.1（代码格式化；当前列在运行依赖中，后续可移入 dev 依赖组） |

> 原 `requirements.txt` 已移除，后端依赖统一由 uv 管理。

### 前端

| 组件 | 版本 / 说明 |
| --- | --- |
| Node.js | 24.x（`engines` 要求：`^22.18.0` 或 `>=24.12.0`） |
| Vue | 3.5 |
| Vue Router | 5.4 |
| Vite | 8.2 |
| TypeScript | 6.0 |
| Axios | 1.20 |
| 构建 | npm + `vue-tsc` 类型检查 |

> 前端暂未引入 UI 组件库，页面样式为项目内手写 CSS；构建镜像已统一为 `node:24-alpine`。

### 部署

- Docker / Docker Compose
- Nginx（托管前端静态资源 + `/api` 反向代理，支持最大 60MB 上传、300s 超时）
- PostgreSQL 16
- Milvus 2.6 standalone（依赖 etcd + MinIO）、Attu（Milvus 可视化控制台，可选）
- 独立 MinIO（业务文件对象存储，与 Milvus 依赖的 MinIO 隔离）

## 目录结构

```
huishutai/
├── backend/                    # 后端服务（Django）
│   ├── config/                 # Django 配置：settings / urls / wsgi / asgi
│   ├── api/                    # 接口入口：URL 路由 + 路由列表接口（/routes/）
│   ├── user/                   # 用户业务层：views（业务接口）+ auth（签名 Token 认证）
│   ├── files/                  # 文件上传业务：services（校验/存储编排）+ views + init_storage 命令
│   ├── filestorage.py          # MinIO 对象存储访问层（上传/删除/签名 URL/健康检查）
│   ├── LLMapi/                 # 大模型供应与调用
│   │   ├── templates.py        # 内置供应商模板
│   │   ├── crypto.py           # API Key Fernet 加解密与脱敏
│   │   ├── adapters.py         # OpenAI 兼容 / Anthropic / Gemini 协议适配
│   │   ├── model_meta.py       # 模型分类、参数规格生成、请求参数校验
│   │   ├── services.py         # 供应商配置/模型同步/统一调用网关（业务层）
│   │   ├── views.py / urls.py  # HTTP 接口
│   │   └── result.py           # LLMResult / LLMStatus
│   ├── sqldb/                  # 关系库数据层
│   │   ├── models.py           # 表结构：User / UserInfo / UploadedFile / LLMProviderConfig / LLMModel
│   │   ├── crud/               # BaseCRUD 基类 + 各表数据访问对象
│   │   ├── enums.py            # DBStatus 状态码
│   │   ├── result.py           # DBResult 统一返回
│   │   └── migrations/         # 0001 ~ 0003
│   ├── vectordb/               # 向量库数据层（Milvus，不建 Django 模型）
│   │   ├── client.py           # 客户端懒加载单例 / 健康检查
│   │   ├── schemas.py          # 集合结构定义
│   │   ├── crud/               # VectorCollection 通用操作
│   │   ├── management/commands/init_vectordb.py
│   │   ├── enums.py            # VDBStatus
│   │   └── result.py           # VDBResult
│   ├── RAG/                    # RAG 业务应用（骨架）
│   ├── tests/                  # LLMapi 回归测试（SQLite + 适配器 mock，不依赖外部服务）
│   ├── main.py                 # uv 初始化占位入口（非 Django 启动入口）
│   ├── manage.py
│   ├── pyproject.toml / uv.lock
│   └── Dockerfile
├── frontend/                   # 前端服务（Vue 3 + Vite + TypeScript）
│   ├── src/
│   │   ├── api/                # axios 封装 + 用户接口
│   │   ├── router/             # 路由表与登录守卫
│   │   ├── utils/auth.ts       # token / 用户信息的本地存储
│   │   ├── views/              # Login / Register / Home
│   │   ├── components/         # Vite 模板遗留组件（暂未使用）
│   │   └── assets/             # 全局样式
│   ├── nginx.conf              # 静态资源 + /api 代理（上传 60MB、300s 超时）
│   └── Dockerfile
├── deploy/                     # 部署编排
│   ├── docker-compose.yml      # PostgreSQL / Milvus / 独立 MinIO / 前后端
│   └── .env.example            # 环境变量样板（复制为 .env 后使用）
├── .gitattributes              # 文本统一 LF；bat/cmd/ps1 保留 CRLF
├── .gitignore
└── README.md
```

> 目录结构随开发进度调整，以仓库实际内容为准。

## 架构说明

### 分层约定

```
HTTP 请求
  └─ api/urls.py（路由）
      ├─ user/views.py     → sqldb.crud（user / user_info）──────────────→ PostgreSQL
      ├─ files/views.py    → files/services.py → filestorage.py ─────────→ MinIO
      │                                     └──→ sqldb.crud（uploaded_file）→ PostgreSQL
      └─ LLMapi/views.py   → LLMapi/services.py → adapters（供应商 HTTP）
                                  ├──→ crypto / model_meta（纯函数）
                                  └──→ sqldb.crud（llm_provider / llm_model）→ PostgreSQL
```

- **`api/urls.py`**：只做 URL 路由；业务接口由 `user` / `files` / `LLMapi` 等应用提供。`api/views.py` 仅提供只读的路由列表接口。
- **业务层**（`user/views.py`、`files/services.py`、`LLMapi/services.py`）：参数校验、业务编排、调用数据层、返回统一结果；不直接出现 `User.objects` 这类 ORM 操作。
- **`user/auth.py`**：签名 Token 的签发与校验，以及 DRF 认证类 `SignedTokenAuthentication`、权限类 `IsLoginUser`。
- **`sqldb/`**：表结构（`models.py`）、通用 CRUD 基类（`crud/base.py`）、各表数据访问对象、状态码与结果对象。数据层不感知 HTTP 与业务规则。
- **`filestorage.py`**：MinIO 对象存储访问层，只做 bucket / 上传 / 删除 / 签名 URL / 健康检查；文件归属与校验在 `files/services.py`。
- **`vectordb/`**：不建 Django 模型；集合结构定义在 `schemas.py`，Milvus 操作在 `crud/`，连接管理在 `client.py`。负责向量读写，不做 embedding、文本切分与 RAG 流程。
- **`LLMapi/`**：大模型供应业务。适配器只做协议转换；业务层负责供应商配置、模型同步、调用参数校验；对其它应用提供 `services.get_model_config` / `services.chat_completion` / `services.create_embeddings` 入口，不直接暴露供应商请求。
- **`RAG/`**：AI 业务应用，目前为骨架，后续承载检索增强逻辑。

### 统一返回与状态码

所有接口统一返回 `{ "code": 0, "message": "...", "data": ... }`，不同领域使用各自的状态码枚举：

**数据库 / 文件（`DBStatus`）**

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 1001 | 数据不存在 |
| 1002 | 唯一约束冲突（如用户名、配置名称重复） |
| 1003 | 参数 / 业务校验不通过 |
| 1004 | 外部服务异常（如 MinIO） |
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

业务校验失败默认 HTTP 400；未登录或 Token 无效 HTTP 401；服务端异常 HTTP 500。

### 认证流程

1. 注册 / 登录成功后，服务端用 `SECRET_KEY` 对 `{uid}` 签名生成 token，有效期 7 天。
2. 前端把 token 存入 `localStorage`，后续请求自动携带 `Authorization: Bearer <token>`。
3. DRF 认证类解析 token 并加载用户；失败返回 401，前端清理登录态并跳转登录页。
4. token 无状态，服务端不保存会话，退出登录仅清前端 token；修改 `SECRET_KEY` 会使全部 token 失效。

> 文件上传、LLM 供应与路由列表接口均沿用全局配置，需要登录；数据按 `request.user` 隔离，接口不接受前端传入的 `user_id`。

### 文件上传流程

1. 前端以 `multipart/form-data` 调用 `POST /files/upload/`，字段名固定为 `file`。
2. 校验：文件名非空、大小不超过 `MAX_UPLOAD_SIZE`（默认 50MB）、扩展名在 `ALLOWED_UPLOAD_EXTENSIONS` 白名单内。
3. 流式计算 SHA-256（同时统计实际大小），读完复位文件指针。
4. 写入 MinIO，对象键格式 `uploads/{user_id}/{YYYY}/{MM}/{uuid}{扩展名}`。
5. 生成浏览器可访问的临时签名 URL（`MINIO_PUBLIC_ENDPOINT`，默认 1 小时，最长 7 天）。
6. 写入 PostgreSQL 元数据；若元数据写入失败，删除已上传对象避免孤儿文件。

### LLM 调用流程

```
供应商模板（内置 10 个，openai / anthropic / gemini 三类协议）
   └─ 用户创建供应商配置（base_url、API Key 加密入库、脱敏回显）
        └─ 在线拉取模型列表 → 分类（chat / embedding / rerank / image / audio / other）
             └─ 生成参数规格 param_spec（白名单 + 类型/范围/枚举）
                  └─ 统一网关校验并调用适配器 → 归一化响应返回
```

- API Key 使用 Fernet 对称加密后入库，接口只返回掩码（如 `sk-****abcd`）；`LLMAPI_ENCRYPTION_KEY` 为空时由 `SECRET_KEY` 派生（仅开发方便）。
- 模型列表来自在线拉取（`source=auto`）或用户手动登记（`source=manual`）；重新同步时保留手动模型，删除已消失的自动模型。
- 调用时按模型 `param_spec` 严格校验参数；`model` / `messages` / `input` / `stream` 由系统控制，不允许用户传入。
- 当前实现为同步一次性返回，未支持流式输出与工具调用。

### 数据模型

**PostgreSQL**（`backend/sqldb/models.py`）：

| 表 | 说明 |
| --- | --- |
| `user` | 用户表：`username`（唯一）、`password`（哈希值） |
| `user_info` | 用户资料表：与 `user` 一对一，`email` / `phone` / `gender` |
| `uploaded_file` | 上传文件元数据：归属用户、原始文件名、`bucket` + `object_key`、SHA-256、大小、MIME、上传时间；唯一约束 `(bucket, object_key)` |
| `llm_provider_config` | 大模型供应商配置：归属用户、模板编码、协议、`base_url`、加密 API Key、脱敏 Key、启用状态、最近同步时间/错误；唯一约束 `(user, name)` |
| `llm_model` | 模型目录：所属供应商、供应商模型 ID、展示名、分类、参数规格（JSON）、来源（auto/manual）、启用状态、原始信息、同步时间；唯一约束 `(provider, model_id)` |

**Milvus**（`backend/vectordb/schemas.py`）：

| 项 | 值 |
| --- | --- |
| 集合名 | `knowledge_chunks`（可用环境变量覆盖） |
| 向量维度 | 1024（需与 embedding 模型输出维度一致） |
| 度量方式 | COSINE |
| 标量字段 | `content`（切片原文，8192）/ `source`（来源，512）/ `doc_id`（文档标识，128） |
| 主键 | `id`，自增（`auto_id=True`） |
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

### 方式一：Docker Compose 部署（推荐）

```bash
cd deploy
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
# 按需修改 .env：至少设置 POSTGRES_PASSWORD、MINIO_ROOT_PASSWORD，
# 生产环境还需显式设置 LLMAPI_ENCRYPTION_KEY
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

- Milvus 启动较慢，健康检查预留了 90 秒（`start_period`），等 `docker compose ps` 显示 healthy 后再初始化向量集合。
- 首次部署需要初始化向量集合（对象存储 bucket 已由后端启动命令 `init_storage` 自动创建）：

```bash
docker compose exec backend python manage.py init_vectordb
```

- 文件上传经前端 Nginx 转发：`client_max_body_size 60m` 需大于后端 `MAX_UPLOAD_SIZE`（默认 50MB），调大上传上限时两处要同步修改。
- 生产环境务必显式配置 `LLMAPI_ENCRYPTION_KEY`（Fernet key），否则 API Key 加密密钥由 `SECRET_KEY` 派生，更换 `SECRET_KEY` 会导致已存 Key 无法解密。

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

本地直跑时默认连接 `127.0.0.1:5432` 的 PostgreSQL、`http://127.0.0.1:19530` 的 Milvus、`127.0.0.1:9004` 的 MinIO；数据库密码与 MinIO 账号需通过环境变量提供，请在**同一终端**中先设置（PowerShell 示例）：

```powershell
$env:POSTGRES_PASSWORD = "123456"                       # 与 deploy/.env 一致
$env:MINIO_ACCESS_KEY = "huishutai_files"               # 即 deploy/.env 的 MINIO_ROOT_USER
$env:MINIO_SECRET_KEY = "ChangeMe_Strong_123"           # 即 deploy/.env 的 MINIO_ROOT_PASSWORD
```

```bash
uv run python manage.py migrate       # 初始化数据库表
uv run python manage.py init_storage  # 检查 MinIO 并创建 bucket（幂等）
uv run python manage.py init_vectordb # 初始化向量集合（需 Milvus 可用）
uv run python manage.py runserver 0.0.0.0:8000
```

> 若使用其他 MinIO 地址或端口，可覆盖 `MINIO_ENDPOINT`、`MINIO_PUBLIC_ENDPOINT`、`MINIO_BUCKET` 等变量（见「环境变量」）。

#### 3. 前端

```bash
cd frontend
npm install
npm run dev                           # http://localhost:5173
```

开发服务器会把 `/api/*` 代理到 `http://127.0.0.1:8000` 并去掉 `/api` 前缀，因此前端只需统一使用 `/api` 前缀（例如 `/api/user/login/` 对应后端的 `/user/login/`）。

#### 4. 构建与检查

前端生产构建（含 `vue-tsc` 类型检查）：

```bash
cd frontend
npm run build
```

后端系统检查：

```bash
cd backend
uv run python manage.py check
```

### 测试

后端测试使用 SQLite 内存库 + mock 供应商适配器，不依赖 PostgreSQL / MinIO / Milvus，也不会发起真实外网请求：

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

如本机有可用的 PostgreSQL，也可使用默认配置运行：`uv run python manage.py test tests -v 2`。

当前结果：共 **128 个用例**，运行结果为 OK（其中 4 个以 `expectedFailure` 标记记录已知缺陷：供应商同步未写 `last_synced_at`、`model_id` 强转接受小数/布尔、`rerank` 模型被误分类为 `embedding`、`base_url` 带 query/fragment 未被拒绝），详见 [backend/tests/README.md](backend/tests/README.md)。用户 / 文件 / 向量库模块目前仍是占位测试。

## 环境变量

后端直接从进程环境变量读取配置（`backend/config/settings.py`），未设置时使用默认值。

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
| `MINIO_ACCESS_KEY` | 空字符串 | MinIO 访问账号（对应 compose 的 `MINIO_ROOT_USER`） |
| `MINIO_SECRET_KEY` | 空字符串 | MinIO 访问密码（对应 compose 的 `MINIO_ROOT_PASSWORD`） |
| `MINIO_SECURE` | `false` | 内网访问是否走 HTTPS |
| `MINIO_PUBLIC_SECURE` | `false` | 签名 URL 是否走 HTTPS |
| `MINIO_BUCKET` | `huishutai-files` | 文件 bucket 名称 |
| `MINIO_PRESIGN_EXPIRY` | `3600` | 签名 URL 有效期（秒，代码限制最长 7 天） |
| `MAX_UPLOAD_SIZE` | `52428800`（50MB） | 单文件大小上限（字节） |

> 允许上传的扩展名在 `settings.ALLOWED_UPLOAD_EXTENSIONS` 中维护：`.pdf .txt .md .doc .docx .xls .xlsx .ppt .pptx .png .jpg .jpeg .gif .webp .zip`。

### LLMapi

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLMAPI_ENCRYPTION_KEY` | 空字符串 | API Key 加密用的 Fernet key（base64）；留空时由 `SECRET_KEY` 派生，生产必须显式配置 |
| `LLMAPI_HTTP_TIMEOUT` | `30` | 调用供应商接口超时（秒） |
| `LLMAPI_MAX_MODELS` | `1000` | 单次模型列表同步的最大条数 |
| `LLMAPI_ALLOW_PRIVATE_BASE_URL` | `true` | 是否允许配置内网/本机 `base_url`（本地 Ollama 需要 true；生产建议 false 防 SSRF） |

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
MINIO_PUBLIC_ENDPOINT=127.0.0.1:9004
MINIO_FILES_API_PORT=9004
MINIO_FILES_CONSOLE_PORT=9005
MINIO_PRESIGN_EXPIRY=3600
MAX_UPLOAD_SIZE=52428800

# ===== LLMapi =====
LLMAPI_ENCRYPTION_KEY=
LLMAPI_HTTP_TIMEOUT=30
LLMAPI_ALLOW_PRIVATE_BASE_URL=true
```

> 当前 compose 向后端容器注入 `POSTGRES_*`、固定 `MILVUS_URI`、`MINIO_*`、`MAX_UPLOAD_SIZE` 与 `LLMAPI_*`；`MILVUS_TOKEN`、`MILVUS_DB_NAME`、`MILVUS_KNOWLEDGE_*` 尚未透传，如需自定义需在 `deploy/docker-compose.yml` 的 backend `environment` 中补充。
>
> `SECRET_KEY`、`DEBUG=True`、空 `ALLOWED_HOSTS` 目前为开发配置直接写在 `settings.py` 中，生产部署前需改为环境变量注入（compose 传入的 `DJANGO_ALLOWED_HOSTS` 尚未被读取）。

## 接口文档

### 约定

- 后端路由直接挂在根路径（如 `/user/login/`）；前端统一请求 `/api/*`，由 Vite（开发）或 Nginx（生产）转发并去掉 `/api` 前缀。
- 请求体与响应体均为 JSON（文件上传为 `multipart/form-data`），响应统一为 `{ "code": 0, "message": "...", "data": ... }`。
- 除标注「公开」的接口外，均需要携带 `Authorization: Bearer <token>`，否则返回 HTTP 401。
- 下列路径均为 Django 侧路径（未加 `/api` 前缀）。联调时可用 `GET /routes/` 获取当前全部路由。

### 接口列表

**用户**

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| POST | `/user/register/` | 注册，成功后直接返回 token | 公开 |
| POST | `/user/login/` | 登录，返回 token | 公开 |
| POST | `/user/logout/` | 退出登录（服务端无状态，前端清除 token 即可） | 公开 |
| GET | `/user/check-username/?username=xxx` | 用户名查重 | 公开 |
| GET | `/user/info/` | 获取当前用户资料 | 需登录 |
| PATCH | `/user/info/` | 修改当前用户资料（email / phone / gender） | 需登录 |
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
      "last_synced_at": "2026-10-29T13:00:00+00:00",
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
| 扩展名 | 必须在 `ALLOWED_UPLOAD_EXTENSIONS` 白名单内 |

**LLM 调用**

| 字段 | 规则 |
| --- | --- |
| `messages` | 非空数组；每项含 `role`（`system` / `user` / `assistant`）与 `content`（字符串或数组）；至少一条 `user` 消息 |
| `input` | 非空字符串，或非空字符串数组 |
| `params` | JSON 对象，按模型 `param_spec` 白名单校验类型、范围、枚举；自动合并默认值；缺少必填参数会报错 |
| `base_url` | 必须是 http(s) URL，不能包含用户名密码；`LLMAPI_ALLOW_PRIVATE_BASE_URL=false` 时拒绝内网/本机地址 |
| `model_id` | 整数，须为当前用户所属且已启用的模型主键 |

> `model` / `messages` / `input` / `stream` 属于系统控制参数，不允许通过 `params` 传入。

## 数据库与向量库

### 迁移与初始化

```bash
cd backend
uv run python manage.py makemigrations   # 修改模型后生成迁移
uv run python manage.py migrate          # 应用迁移（0001 ~ 0003）
uv run python manage.py init_storage     # 检查 MinIO 并创建 bucket（幂等）
uv run python manage.py init_vectordb    # 幂等创建 Milvus 集合（已存在则跳过）
```

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

## 前端说明

### 路由

| 路径 | 页面 | 访问控制 |
| --- | --- | --- |
| `/` | 重定向到 `/home` | — |
| `/login` | 登录页 | 仅未登录可访问 |
| `/register` | 注册页（含用户名实时查重） | 仅未登录可访问 |
| `/home` | 个人中心（资料查看/编辑、修改密码、退出登录） | 需登录 |
| 其它路径 | 重定向到 `/home` | — |

路由守卫读取本地登录态：未登录访问受保护页面会跳转登录页并记录 `redirect` 参数；已登录访问登录/注册页会跳回 `/home`。

### 登录态

- token 与基础用户信息保存在 `localStorage`（`access_token`、`auth_user`）。
- axios 请求拦截器自动附加 `Authorization: Bearer <token>`。
- 响应拦截器统一解包 `{ code, message, data }`；遇到 401 时清除本地登录态并跳转登录页。

### 部署与代理

生产环境由 Nginx 托管构建后的静态资源并反向代理 `/api`：配置了 `client_max_body_size 60m`、`proxy_request_buffering off` 与 300s 读写超时，用于支撑文件上传和大模型长耗时调用。

> 前端目前只实现了用户模块页面；文件上传、LLM 供应商配置与模型调用暂时只有后端接口，页面待开发。

## 分支说明

- `devlop`：当前默认开发分支，新功能与修复请基于该分支进行。
- `ZYP`：协作分支，登录/注册功能已合入 `devlop`。
- `main`：基础应用设施分支。
- 仓库通过 `.gitattributes` 统一换行：文本文件以 LF 存储，Windows 脚本（`*.bat` / `*.cmd` / `*.ps1`）保留 CRLF。

## 已知问题与待办

- **前端功能缺口**：文件上传、LLM 供应商配置与模型调用、路由列表均只有后端接口，前端页面尚未实现。
- **RAG / Agent**：`RAG` 仅为应用骨架；Agent、文生图、文生视频尚未开始。
- **调用网关覆盖范围**：当前只提供 chat / embeddings 两个调用入口；`rerank` / `image` / `audio` 分类的模型可被识别和列出，但尚无对应调用接口；仅支持同步一次性调用，未支持流式输出与工具调用。
- **LLM 已知缺陷（4 个预期失败用例）**：创建/更新供应商并同步模型后未写入 `last_synced_at`；`model_id` 使用 `int()` 强转，`1.5` / `True` 会被静默接受；`bge-reranker` 等 rerank 模型被误分类为 embedding；`base_url` 携带 query / fragment 时未被拒绝。详见 [backend/tests/README.md](backend/tests/README.md)。
- **文件模块待补充**：「我的文件」列表、删除、重新签名等 HTTP 接口尚未提供（数据层已预留 `list_by_user`）。
- **测试覆盖不均**：仅 LLMapi 有完整回归测试；用户 / 文件 / 向量库仍为占位测试。
- **安全配置**：`SECRET_KEY`、`DEBUG=True`、空 `ALLOWED_HOSTS` 为开发配置；compose 传入的 `DJANGO_ALLOWED_HOSTS` 尚未在 `settings.py` 中读取。
- **加密密钥**：`LLMAPI_ENCRYPTION_KEY` 未配置时由 `SECRET_KEY` 派生，生产必须显式配置；更换密钥后已存 API Key 无法解密，需要重新录入。
- **SSRF 防护**：`LLMAPI_ALLOW_PRIVATE_BASE_URL` 默认 `true`（方便本地 Ollama），生产环境应设为 `false`。
- **MinIO 签名地址**：`MINIO_PUBLIC_ENDPOINT` 必须与浏览器实际访问的 `host:port` 一致，否则签名 URL 无法打开；当前默认 `127.0.0.1:9004`，仅适合本机访问。
- **依赖归类**：`black` 目前列在运行依赖中，建议移入 dev 依赖组；Django admin 已安装但未挂载路由（`/admin` 不可用）。
- **示例 / 遗留代码**：`backend/api` 中的 `Book` 模型 / 序列化器 / ViewSet 为早期示例，尚未挂载路由；`backend/sqldb/crud/user_crud.py` 为旧版数据访问实现，当前未被引用，均可清理。
- **未实现功能**：邮箱验证、找回密码、用户列表 / 权限管理、接口文档（OpenAPI）、CI 等。
