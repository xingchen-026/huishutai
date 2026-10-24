# 汇书台（huishutai）

> 面向 AI 应用落地的技术整合实践项目：把 RAG、Agent、文生图、文生视频等 AI 能力，与用户管理等基础技术服务结合，沉淀一套可复用的应用落地方案。

## 项目简介

**汇书台**是一个用于整合 AI 应用落地相关技术的工程实践项目。项目按「基础服务 → 数据访问层 → AI 能力」的顺序推进：先完成用户体系与关系库/向量库访问层等基础设施，再按模块接入向量检索、RAG 问答、大模型调用等能力。

当前阶段：用户管理模块已完成端到端开发（Django REST Framework 后端 + Vue 3 前端），`sqldb`（PostgreSQL）与 `vectordb`（Milvus）数据访问层已完成封装；RAG、LLMapi 等 AI 模块目前只有应用骨架，业务接口尚未开发。

## 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 用户管理 | ✅ 已完成 | 注册 / 登录 / 登出 / 用户名查重 / 个人资料 / 修改密码，后端接口 + 前端页面齐备 |
| 关系库数据层 `sqldb` | ✅ 已完成 | 通用 CRUD 基类、统一结果对象、状态码；表结构集中管理 |
| 向量库数据层 `vectordb` | 🚧 封装完成，未暴露接口 | Milvus 客户端、集合 CRUD、`init_vectordb` 初始化命令 |
| RAG 检索增强 | 🚧 仅骨架 | 应用已注册，无业务实现 |
| LLMapi 大模型调用 | 🚧 仅骨架 | 应用已注册，无业务实现 |
| Agent / 文生图 / 文生视频 | 📋 规划中 | — |
| 容器化部署 | ✅ 已完成 | 前端 + 后端 + PostgreSQL + Milvus（含 etcd / MinIO）统一编排 |

## 功能特性

- **用户体系**：注册、登录、登出、用户名查重、个人资料查看与修改、修改密码。
- **签名 Token 认证**：基于 `django.core.signing`，不新增 token 表；默认所有接口要求登录，公开接口单独放开。
- **分层数据访问**：业务层不直接写 ORM，统一经 `sqldb` / `vectordb` 数据层访问数据库，返回结果收敛为 `DBResult` / `VDBResult`。
- **向量检索基础设施**：Milvus 客户端懒加载单例、集合结构声明式定义、幂等建集合命令，为 RAG 场景预留能力。
- **前后端分离**：后端提供 RESTful 接口；开发态由 Vite 代理请求，生产态由 Nginx 反向代理。
- **容器化部署**：`deploy/docker-compose.yml` 一键拉起前后端与全部依赖服务。

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

> 前端暂未引入 UI 组件库，页面样式为项目内手写 CSS。

### 部署

- Docker / Docker Compose
- Nginx（托管前端静态资源 + `/api` 反向代理）
- PostgreSQL 16、Milvus 2.6 standalone（依赖 etcd + MinIO）、Attu（Milvus 可视化控制台，可选）

## 目录结构

```
huishutai/
├── backend/                    # 后端服务（Django）
│   ├── config/                 # Django 配置：settings / urls / wsgi / asgi
│   ├── api/                    # 接口入口：URL 路由（api/urls.py）
│   ├── user/                   # 用户业务层：views（业务接口）+ auth（签名 Token 认证）
│   ├── sqldb/                  # 关系库数据层
│   │   ├── models.py           # 表结构：User / UserInfo
│   │   ├── crud/               # BaseCRUD 基类 + 各表数据访问对象
│   │   ├── enums.py            # DBStatus 状态码
│   │   └── result.py           # DBResult 统一返回
│   ├── vectordb/               # 向量库数据层（Milvus）
│   │   ├── client.py           # 客户端懒加载单例 / 健康检查
│   │   ├── schemas.py          # 集合结构定义
│   │   ├── crud/               # VectorCollection 通用操作
│   │   ├── management/commands/init_vectordb.py
│   │   ├── enums.py            # VDBStatus
│   │   └── result.py           # VDBResult
│   ├── RAG/                    # RAG 业务应用（骨架）
│   ├── LLMapi/                 # 大模型调用应用（骨架）
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
│   ├── nginx.conf
│   └── Dockerfile
├── deploy/                     # 部署编排
│   ├── docker-compose.yml
│   └── .env.example            # 环境变量样板（复制为 .env 后使用）
├── .gitattributes
├── .gitignore
└── README.md
```

> 目录结构随开发进度调整，以仓库实际内容为准。

## 架构说明

### 分层约定

```
request → api/urls.py（路由） → user/views.py（业务层） → sqldb.crud / vectordb.crud（数据层） → PostgreSQL / Milvus
```

- **`api/urls.py`**：只做 URL 路由；业务接口由 `user` 等应用提供。
- **`user/views.py`**：参数校验、业务编排、调用数据层、返回 `Response`；不出现 `User.objects` 这类 ORM 操作。
- **`user/auth.py`**：签名 Token 的签发与校验，以及 DRF 认证类 `SignedTokenAuthentication`、权限类 `IsLoginUser`。
- **`sqldb/`**：表结构（`models.py`）、通用 CRUD 基类（`crud/base.py`）、数据访问对象（`crud/user.py`、`crud/user_info.py`）、状态码与结果对象。数据层不感知 HTTP 与业务规则。
- **`vectordb/`**：不建 Django 模型；集合结构定义在 `schemas.py`，Milvus 操作在 `crud/`，连接管理在 `client.py`。负责向量读写，不做 embedding、文本切分与 RAG 流程。
- **`RAG/`、`LLMapi/`**：AI 业务应用，目前为骨架，后续分别承载检索增强与大模型调用逻辑。

### 统一返回与状态码

所有接口统一返回 `{ "code": 0, "message": "...", "data": ... }`：

| code | 含义 | 来源 |
| --- | --- | --- |
| 0 | 成功 | `DBStatus.SUCCESS` |
| 1001 | 数据不存在 | `DBStatus.NOT_FOUND` |
| 1002 | 唯一约束冲突（如用户名已存在） | `DBStatus.DUPLICATE_ERR` |
| 9999 | 数据库异常 / 未知错误 | `DBStatus.UNKNOWN_ERR` |
| 2001 | 向量集合或数据不存在 | `VDBStatus.NOT_FOUND` |
| 2002 | 向量操作参数不合法 | `VDBStatus.PARAM_ERR` |
| 2003 | 向量库连接失败 | `VDBStatus.CONNECTION_ERR` |
| 2999 | 其它向量库异常 | `VDBStatus.UNKNOWN_ERR` |

业务校验失败默认返回 HTTP 400；未登录或 Token 无效返回 HTTP 401；服务端异常返回 HTTP 500。

### 认证流程

1. 注册 / 登录成功后，服务端用 `SECRET_KEY` 对 `{uid}` 签名生成 token，有效期 7 天。
2. 前端把 token 存入 `localStorage`，后续请求自动携带 `Authorization: Bearer <token>`。
3. DRF 认证类解析 token 并加载用户；失败返回 401，前端清理登录态并跳转登录页。
4. token 无状态，服务端不保存会话，退出登录仅清前端 token；修改 `SECRET_KEY` 会使全部 token 失效。

### 数据模型

**PostgreSQL**（`backend/sqldb/models.py`）：

| 表 | 说明 |
| --- | --- |
| `user` | 用户表：`username`（唯一）、`password`（哈希值） |
| `user_info` | 用户资料表：与 `user` 一对一，`email` / `phone` / `gender` |

**Milvus**（`backend/vectordb/schemas.py`）：

| 项 | 值 |
| --- | --- |
| 集合名 | `knowledge_chunks`（可用环境变量覆盖） |
| 向量维度 | 1024（需与后续 embedding 模型输出维度一致） |
| 度量方式 | COSINE |
| 标量字段 | `content`（切片原文，8192）/ `source`（来源，512）/ `doc_id`（文档标识，128） |
| 主键 | `id`，自增（`auto_id=True`） |
| 索引 | AUTOINDEX |

## 快速开始

> 以下命令均以仓库根目录为起点，按小节分别执行。

### 环境要求

- Python 3.12+（推荐使用 uv）
- Node.js 24.x（或满足 `^22.18.0 || >=24.12.0`）
- Docker & Docker Compose（容器化部署，或用于启动 PostgreSQL / Milvus 依赖）
- PostgreSQL 16、Milvus 2.6（本地直跑后端时需要）

### 方式一：Docker Compose 部署（推荐）

```bash
cd deploy
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
# 按需修改 .env（至少设置 POSTGRES_PASSWORD）
docker compose up -d --build
```

启动后访问 `http://localhost` 即为前端页面。

| 服务 | 端口（宿主机） | 说明 |
| --- | --- | --- |
| frontend | 80 | 前端入口，Nginx 托管静态资源并把 `/api/` 转发到后端 |
| backend | 容器内 8000 | 启动时自动执行 `migrate`，再由 Gunicorn 提供服务 |
| db | 127.0.0.1:5432 | PostgreSQL 16，数据卷 `postgres_data` |
| milvus | 127.0.0.1:19530、9091 | Milvus standalone，数据卷 `milvus_data` |
| etcd | 容器内 2379 | Milvus 元数据依赖 |
| minio | 127.0.0.1:9000、9001 | Milvus 对象存储依赖 |
| attu | 127.0.0.1:8080 | Milvus 可视化控制台，仅开发调试用，可删除 |

首次启动说明：

- Milvus 启动较慢，健康检查预留了 90 秒（`start_period`），等 `docker compose ps` 显示 healthy 后再初始化集合。
- 首次部署需要初始化向量集合：

```bash
docker compose exec backend python manage.py init_vectordb
```

> ⚠️ 当前 `backend/Dockerfile` 从 `pip install -r requirements.txt` 切换为 `uv sync` 后，还没有把虚拟环境加进 `PATH`，容器内的 `python` / `gunicorn` 命令会找不到。使用容器化部署前需在 Dockerfile 中补一行 `ENV PATH="/app/.venv/bin:$PATH"`，或把启动命令改为 `uv run python ...`。详见文末「已知问题与待办」。

### 方式二：本地开发

#### 1. 启动依赖服务（可选，也可使用本机已安装的 PostgreSQL / Milvus）

```bash
cd deploy
cp .env.example .env
docker compose up -d db milvus        # 会自动带上 etcd、minio
```

#### 2. 后端

```bash
cd backend
uv sync                               # 安装依赖，生成/复用 .venv
uv run python manage.py migrate       # 初始化数据库表
uv run python manage.py init_vectordb # 初始化向量集合（需 Milvus 可用）
uv run python manage.py runserver 0.0.0.0:8000
```

本地直跑时默认连接 `127.0.0.1:5432` 的 PostgreSQL、`http://127.0.0.1:19530` 的 Milvus。若数据库密码不是空串，需先设置环境变量（PowerShell 示例）：

```powershell
$env:POSTGRES_PASSWORD = "123456"     # 与 deploy/.env 中的值保持一致
uv run python manage.py runserver 0.0.0.0:8000
```

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

后端系统检查与测试（测试当前为占位模板，运行需要可连接的数据库）：

```bash
cd backend
uv run python manage.py check
uv run python manage.py test
```

## 环境变量

后端直接从进程环境变量读取配置（`backend/config/settings.py`），未设置时使用默认值：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `POSTGRES_DB` | `huishutai` | 数据库名 |
| `POSTGRES_USER` | `huishutai` | 数据库用户 |
| `POSTGRES_PASSWORD` | 空字符串 | 数据库密码（无内置默认，需自行提供） |
| `POSTGRES_HOST` | `127.0.0.1` | 容器内由 compose 覆盖为 `db` |
| `POSTGRES_PORT` | `5432` | 数据库端口 |
| `MILVUS_URI` | `http://127.0.0.1:19530` | Milvus 地址，容器内由 compose 覆盖为 `http://milvus:19530` |
| `MILVUS_TOKEN` | 空字符串 | Milvus 鉴权 token（开启鉴权时填写，如 `root:Milvus`） |
| `MILVUS_DB_NAME` | `default` | Milvus 数据库名 |
| `MILVUS_TIMEOUT` | `10` | Milvus 操作超时（秒） |
| `MILVUS_KNOWLEDGE_COLLECTION` | `knowledge_chunks` | 知识库集合名 |
| `MILVUS_KNOWLEDGE_DIM` | `1024` | 知识库向量维度（须与 embedding 模型一致） |
| `MILVUS_KNOWLEDGE_METRIC_TYPE` | `COSINE` | 向量相似度度量方式 |

容器化部署的变量样板见 `deploy/.env.example`（复制为 `deploy/.env` 后使用，`.env` 已被 git 忽略）：

```env
POSTGRES_DB=huishutai
POSTGRES_USER=huishutai
POSTGRES_PASSWORD=123456

MILVUS_URI=http://milvus:19530
MILVUS_TOKEN=
MILVUS_DB_NAME=default
MILVUS_KNOWLEDGE_COLLECTION=knowledge_chunks
MILVUS_KNOWLEDGE_DIM=1024
MILVUS_KNOWLEDGE_METRIC_TYPE=COSINE
```

> 当前 compose 向后端容器注入的变量为 `POSTGRES_*` 与 `MILVUS_URI`；如需自定义 `MILVUS_TOKEN`、`MILVUS_DB_NAME`、`MILVUS_KNOWLEDGE_*`，需在 `deploy/docker-compose.yml` 的 backend `environment` 中补充。
>
> `SECRET_KEY`、`DEBUG` 目前直接写在 `settings.py` 中（开发配置），生产部署前需改为环境变量注入。

## 接口文档

### 约定

- 后端路由直接挂在根路径（如 `/user/login/`）；前端统一请求 `/api/*`，由 Vite（开发）或 Nginx（生产）转发并去掉 `/api` 前缀。
- 请求体与响应体均为 JSON，响应统一为 `{ "code": 0, "message": "...", "data": ... }`。
- 除标注「公开」的接口外，均需要携带 `Authorization: Bearer <token>`，否则返回 HTTP 401。
- 下列路径均为 Django 侧路径（未加 `/api` 前缀）。

### 接口列表

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| POST | `/user/register/` | 注册，成功后直接返回 token | 公开 |
| POST | `/user/login/` | 登录，返回 token | 公开 |
| POST | `/user/logout/` | 退出登录（服务端无状态，前端清除 token 即可） | 公开 |
| GET | `/user/check-username/?username=xxx` | 用户名查重 | 公开 |
| GET | `/user/info/` | 获取当前用户资料 | 需登录 |
| PATCH | `/user/info/` | 修改当前用户资料（email / phone / gender） | 需登录 |
| POST | `/user/password/` | 修改密码（old_password / new_password / confirm_password） | 需登录 |

### 请求与响应示例

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

**错误响应示例**

```json
{ "code": 1002, "message": "用户名已存在", "data": null }
```

### 参数校验规则

| 字段 | 规则 |
| --- | --- |
| username | 3–50 位，仅限中文、字母、数字、下划线 |
| password | 6–128 位 |
| email | 合法邮箱格式（可为空） |
| phone | 11 位中国大陆手机号（可为空） |
| gender | `male` / `female` / `unknown` |

## 数据库与向量库

### 迁移与初始化

```bash
cd backend
uv run python manage.py makemigrations   # 修改模型后生成迁移
uv run python manage.py migrate          # 应用迁移
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

## 分支说明

- `devlop`：当前默认开发分支，新功能与修复请基于该分支进行。
- `ZYP`：协作分支，登录/注册功能已合入 `devlop`。
- `main`：基础应用设施分支。

## 已知问题与待办

- **RAG / LLMapi**：应用骨架已注册到 `INSTALLED_APPS`，业务逻辑与接口尚未实现。
- **向量库接口**：`vectordb` 仅完成数据层封装，暂未暴露 HTTP 接口，等待 RAG 业务层接入。
- **示例代码**：`backend/api` 中的 `Book` 模型 / 序列化器 / ViewSet 为早期示例，尚未挂载路由，可清理。
- **重复实现**：`backend/sqldb/crud/user_crud.py` 为旧版数据访问实现，当前未被引用，可删除。
- **测试**：前后端测试均为占位模板，未覆盖核心流程。
- **安全配置**：`SECRET_KEY`、`DEBUG=True`、空 `ALLOWED_HOSTS` 为开发配置；`deploy/docker-compose.yml` 传入的 `DJANGO_ALLOWED_HOSTS` 尚未在 `settings.py` 中读取。
- **后端镜像启动命令**：`backend/Dockerfile` 改用 `uv sync` 安装依赖后，未将 `/app/.venv/bin` 加入 `PATH`，容器内直接执行 `python` / `gunicorn` 会提示找不到命令；需补 `ENV PATH="/app/.venv/bin:$PATH"`，或把启动命令统一改为 `uv run ...`。
- **前端镜像版本**：`frontend/Dockerfile` 使用 `node:20-alpine`，与 `package.json` 的 `engines` 要求（`^22.18.0 || >=24.12.0`）不一致，建议统一为 Node 24。
- **模板遗留**：`frontend/src/components/` 下为 Vite 脚手架组件，当前页面未使用，可清理。
- **未实现功能**：邮箱验证、找回密码、用户列表 / 权限管理、接口文档（OpenAPI）等。
