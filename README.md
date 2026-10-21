# 汇书台（huishutai）

> 一个面向 AI 应用落地的技术整合实践项目。

## 项目简介

**汇书台**是一个用于整合 AI 应用落地相关技术的工程实践项目，目标是将 RAG（检索增强生成）、Agent、文生图、文生视频等 AI 能力，与用户管理等基础技术服务相结合，形成一套可复用的应用落地方案。

项目当前处于持续开发阶段，部分接口尚未开发完成。

## 功能特性

- **AI 应用技术整合**：涵盖 RAG、Agent、文生图、文生视频等方向的落地实践。
- **基础服务支撑**：提供用户管理等通用基础服务。
- **向量检索能力**：集成 Milvus 向量数据库，支撑语义检索相关场景。
- **前后端分离架构**：后端提供 RESTful 接口，前端独立部署。
- **容器化部署**：前后端及数据库服务均通过 Docker 容器化，支持一键编排启动。

> 各功能模块的具体能力仍在持续完善中。

## 技术栈

### 后端

| 组件 | 说明 |
| --- | --- |
| Python | 3.12+ |
| Django | 6.1.2 |
| Django REST Framework | 3.18.3 |
| Gunicorn | 26.2.0（生产环境 WSGI 服务器） |
| PostgreSQL | 关系型数据库（驱动：psycopg2-binary） |
| Milvus | 向量数据库 |

### 前端

| 组件 | 说明 |
| --- | --- |
| Node.js | 24 |
| Vue | 3 |
| Vite | 构建工具 |
| TypeScript | 类型系统 |

> 前端暂未引入特定的 UI 组件库。

### 部署

- Docker / Docker Compose

## 目录结构

```
huishutai/
├── backend/          # 后端服务（Django）
│   ├── user/         # 用户管理相关模块
│   ├── vectordb/     # 向量数据库相关模块
│   ├── sqldb/        # 关系型数据库相关模块
│   ├── api/          # 接口层
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # 前端服务（Vue 3 + Vite + TypeScript）
│   ├── ...
│   └── Dockerfile
├── deploy/           # 部署编排
│   └── docker-compose.yml
└── README.md
```

> 目录结构可能随开发进度调整，以仓库实际内容为准。

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 24+
- PostgreSQL
- Milvus
- Docker & Docker Compose（容器化部署方式）

### 方式一：Docker Compose 部署（推荐）

项目已将前后端、数据库等服务容器化，可通过 `deploy/docker-compose.yml` 统一编排启动：

```bash
cd deploy
docker compose up -d
```

> 启动前请根据实际环境完成相关配置（环境变量文件将在后续提交中补充）。

### 方式二：本地开发

#### 后端

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### 前端

```bash
cd frontend
npm install
npm run dev
```

## 环境变量

项目运行所需的关键环境变量（如数据库连接、密钥等）配置说明，将随环境变量样板文件（`.env.example`）在后续提交中一并补充。

## 接口文档

后端接口尚未开发完成，暂未提供可参考的 API 文档。接口稳定后将补充接口说明。

## 分支说明

- 当前默认开发分支为 `devlop`，新功能与修复请基于该分支进行。