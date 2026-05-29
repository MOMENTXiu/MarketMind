# MarketMind 项目方案设计书

## 1. 项目概述

MarketMind 是我们小组开发并开源的 AI 营销分析系统。系统面向零售销售明细和通用交易类数据，提供数据上传、标准化、质量检查、分析任务执行、客户分群、商品关联、个性化推荐、促销效果分析、营销洞察和文本建议能力。

当前主应用采用 Vue 3 + FastAPI 前后端分离架构。前端负责用户工作流、状态展示和结果查看；后端负责 API 接入、业务编排、能力执行、Provider 边界和基础设施适配。项目通过 PostgreSQL、Redis/RQ、Redis pub/sub、MinIO 或本地文件系统承载状态、任务队列、事件流和产物存储。

## 2. 建设目标

1. 建设一套可本地运行、可演示、可测试的 AI 营销分析系统。
2. 支持固定中文列零售 CSV 的 Retail Analysis V2 全流程分析。
3. 支持通用 CSV/Excel 的 Data Processing 标准化和通用分析流程。
4. 支持后端统一的 AI 文本建议接口，避免前端直接调用第三方 LLM 接口。
5. 保持清晰分层架构和 Provider Boundary，使分析、存储、队列、事件和 LLM 能力可替换。
6. 提供完整项目文档、接口文档、启动说明、使用指南和质量门命令。

## 3. 总体方案

系统采用浏览器前端、FastAPI 后端、业务编排层、能力原子层、Provider 接口层和基础设施适配层组成的分层方案：

```text
Browser / Vue 3
  -> frontend/src/api typed client
  -> FastAPI Controller
  -> Business Flow / Pipeline
  -> Ability Atom
  -> Provider Interface / ProvidersContainer
  -> Infrastructure Adapter
  -> PostgreSQL / Redis / MinIO / Local File / LLM HTTP
```

系统以 `/api/analysis` 为主要业务接口前缀，在同一后端内并存两条分析链路：

| 链路 | 入口 | 适用数据 | 前端入口 | 状态 |
| --- | --- | --- | --- | --- |
| Retail Analysis V2 | `/api/analysis/projects...` | 固定中文列零售 CSV | `/projects` | 已接入前后端 runtime |
| Data Processing | `/api/analysis/jobs...` | 通用 CSV/Excel | `/data-processing` | 已接入前后端 runtime |

AI 文本建议通过 `POST /api/analysis/customer-suggestions` 提供。前端业务页面不直接请求第三方 LLM endpoint。

## 4. 技术方案

### 4.1 前端技术

前端使用 Vue 3、Vite、TypeScript、Vue Router、Pinia、Element Plus、Tailwind CSS、ECharts 和 lucide-vue-next。主要目录包括：

```text
frontend/src/api/          # 后端接口 typed wrappers
frontend/src/views/        # 页面入口
frontend/src/components/   # 组件
frontend/src/router/       # 路由
frontend/src/styles/       # 样式
frontend/src/utils/        # 工具函数
```

前端通过 `frontend/src/api/` 统一访问后端。Vite 开发代理将 `/api` 与 `/outputs` 转发到后端，跨域部署时可通过 `VITE_API_BASE_URL` 配置 API base URL。

### 4.2 后端技术

后端使用 FastAPI、Uvicorn、Pydantic 2、pandas、scikit-learn、mlxtend、statsmodels、SQLAlchemy、Alembic、Redis/RQ 等。主要目录包括：

```text
backend/api/               # HTTP Controller
backend/business/flows/    # 长生命周期业务流程
backend/business/pipelines/# 业务阶段编排
backend/abilities/         # 可测试能力原子
backend/providers/         # Provider Protocol、DTO、容器
backend/infrastructure/    # DB、文件、Redis、MinIO、LLM 等适配器
backend/core/              # 配置、错误、runtime checks
backend/workers/           # Retail analysis worker
```

后端遵循以下边界：

1. API Controller 只负责请求解析、调用 Flow/Pipeline 和错误映射。
2. Business Flow/Pipeline 负责编排状态机、阶段顺序和副作用。
3. Ability Atom 执行可测试的最小业务动作。
4. Provider Interface 隔离业务层与存储、队列、LLM、artifact 等外部资源。
5. Infrastructure Adapter 实现具体数据库、Redis、文件、MinIO 或 LLM 调用。

### 4.3 基础设施

本地基础设施由 `docker-compose.dev.yml` 定义：

| 服务 | 用途 |
| --- | --- |
| PostgreSQL | Retail V2 状态、项目和数据库相关运行能力。 |
| Redis | RQ 异步任务队列和 pub/sub SSE 事件。 |
| MinIO | 对象存储，可用于样本、上传文件、标准化数据集、sidecars、artifacts 和模型。 |

Redis 只承载队列和事件，不作为业务真相源。大 CSV、图表、报告、模型 artifact 不直接写入 PostgreSQL，应通过文件系统、MinIO 或 Provider ref/API URL 暴露。

## 5. 功能设计

### 5.1 Retail Analysis V2

Retail Analysis V2 面向固定中文列零售 CSV，流程如下：

```text
Create project
  -> upload Retail CSV
  -> RetailDatasetPreparationPipeline
  -> run RetailAnalysisFlow
  -> enqueue Redis/RQ worker payload
  -> worker invokes RetailAnalysisExecutionPipeline
  -> feature engineering
  -> segmentation
  -> association / HUIM
  -> recommendation
  -> marketer insights
  -> report/artifact refs
  -> publish Redis pub/sub SSE events
  -> project status completed or failed
```

主要能力：

1. 创建、查询、删除 Retail 项目。
2. 上传零售 CSV 并完成数据准备。
3. 运行异步分析任务。
4. 输出阶段状态、质量摘要、分析摘要、artifact refs、推荐结果和营销洞察。
5. 通过 REST snapshot 和 SSE 事件展示状态。

Retail V2 输入字段包括顾客编号、类目编码/名称、销售日期、销售月份、商品编码、规格型号、商品类型、单位、销售数量、销售金额、商品单价、是否促销等。

### 5.2 Data Processing

Data Processing 面向通用 CSV/Excel，流程如下：

```text
Create job
  -> upload raw CSV/Excel
  -> DatasetRegularizationPipeline
  -> quality/capability/sidecars
  -> needs_review or ready
  -> universal overview/profile/association/recommendation/promotion/summary pipelines
  -> output refs and skipped reasons
  -> job status completed or failed
```

主要能力：

1. 创建数据处理 Job。
2. 上传通用 `.csv`、`.xls`、`.xlsx` 文件。
3. 执行字段映射、类型归一、业务字段标准化、质量检查和能力判断。
4. 输出 schema mapping detail、quality report、capability、manifest、preview rows 等 sidecars。
5. 在 ready 状态下运行通用分析，输出 overview、profile、association、recommendation、promotion、summary 等结果引用。
6. 当 core 字段需要复核时进入 `needs_review`，当前前端会阻止继续 run。

### 5.3 AI 文本建议

AI 文本建议由后端 `customer_text_suggestion_pipeline` 和 LLM Provider 承载，接口为：

```text
POST /api/analysis/customer-suggestions
```

该接口用于生成客户营销建议和商品洞察文本。LLM 调用不可用时，业务层可返回 deterministic fallback 文本。生产环境需要补充服务端侧密钥管理、鉴权和审计后再开放真实模型配置。

### 5.4 样本文件与产物查看

系统提供样本文件接口和产物读取接口。Retail V2 产物通过项目 artifact refs 查询；Data Processing 产物通过 Job outputs 和 sidecars 查询。前端只展示后端返回的 ref/url，不拼接本地绝对路径。

## 6. 接口设计

### 6.1 应用级接口

| Method | Path | 用途 |
| --- | --- | --- |
| GET | `/` | 根路径，返回服务信息。 |
| GET | `/api/health/` | 健康检查。 |
| GET | `/api/docs` | Swagger UI。 |
| GET | `/api/redoc` | ReDoc UI。 |
| GET | `/openapi.json` | OpenAPI schema。 |
| GET | `/api/samples` | 列出样本文件。 |
| GET | `/api/samples/{sample_id}` | 查询样本元数据。 |
| GET | `/api/samples/{sample_id}/download` | 下载样本文件。 |

### 6.2 Retail V2 接口

| Method | Path | 用途 |
| --- | --- | --- |
| POST | `/api/analysis/projects` | 创建项目。 |
| GET | `/api/analysis/projects` | 列出项目。 |
| GET | `/api/analysis/projects/{project_id}` | 查询项目详情、状态和结果摘要。 |
| DELETE | `/api/analysis/projects/{project_id}` | 删除项目。 |
| POST | `/api/analysis/projects/{project_id}/dataset` | 上传 Retail V2 CSV 并完成数据准备。 |
| POST | `/api/analysis/projects/{project_id}/run` | 启动或复用分析任务。 |
| GET | `/api/analysis/projects/{project_id}/events` | 订阅项目状态事件。 |
| GET | `/api/analysis/projects/{project_id}/artifacts` | 列出项目产物引用。 |
| GET | `/api/analysis/projects/{project_id}/recommendations` | 查询推荐结果。 |
| GET | `/api/analysis/projects/{project_id}/marketer-insights` | 查询营销洞察。 |

### 6.3 Data Processing 接口

| Method | Path | 用途 |
| --- | --- | --- |
| POST | `/api/analysis/jobs` | 创建 Job。 |
| GET | `/api/analysis/jobs/{job_id}` | 查询 Job 状态。 |
| GET | `/api/analysis/jobs/{job_id}/events` | 订阅 Job 状态事件。 |
| POST | `/api/analysis/jobs/{job_id}/raw-dataset` | 上传原始数据。 |
| POST | `/api/analysis/jobs/{job_id}/regularize` | 执行标准化。 |
| POST | `/api/analysis/jobs/{job_id}/run` | 运行通用分析。 |
| GET | `/api/analysis/jobs/{job_id}/outputs` | 查询输出产物。 |
| GET | `/api/analysis/jobs/{job_id}/datasets/{dataset_id}` | 读取数据集引用。 |
| GET | `/api/analysis/jobs/{job_id}/sidecars/{sidecar_id}` | 读取 sidecar。 |

### 6.4 文本建议接口

| Method | Path | 用途 |
| --- | --- | --- |
| POST | `/api/analysis/customer-suggestions` | 生成客户营销建议或商品洞察文本。 |

## 7. 数据与存储设计

### 7.1 Retail V2 数据

Retail V2 输入为固定中文列 CSV，支持 GBK/UTF-8-SIG 等场景的处理要求来自需求文档。系统在数据准备阶段生成 clean dataset、质量摘要和后续分析所需的结构化数据。

### 7.2 Data Processing 数据

Data Processing 输入为通用 CSV/Excel。标准化阶段生成字段映射、质量报告、能力判断、manifest 和预览数据。是否能进入后续分析由 core 字段映射质量决定。

### 7.3 状态与产物

1. Retail V2 state 使用 PostgreSQL-backed provider。
2. 异步任务通过 Redis/RQ worker 执行。
3. 状态事件通过 Redis pub/sub SSE 推送，并以 REST snapshot 兜底。
4. 大文件、图表、报告、模型和 sidecars 通过文件系统或 MinIO 存储，并通过 Provider ref/API URL 暴露。

## 8. 前端页面设计

| 页面/入口 | 功能 |
| --- | --- |
| `/` | 首页与功能概览入口。 |
| `/project-intro` | PPT 式全屏滚动项目介绍页。 |
| `/projects` | 项目空间，查看和管理 Retail 项目。 |
| `/projects/new` | 创建 Retail 项目。 |
| `/projects/{project_id}` | 查看项目详情、状态、质量摘要和产物。 |
| `/data-processing` | 创建并执行通用数据处理 Job。 |
| `/data-processing/jobs/{job_id}` | 查看 Data Processing Job 状态、outputs 和 sidecars。 |

前端业务页面应使用 `frontend/src/api/` 下的 client 和 wrapper，不在页面中直接拼接后端请求逻辑。

## 9. 部署与运行方案

### 9.1 环境要求

1. Python `>=3.13,<3.14`。
2. `uv`。
3. Node.js 18+ 与 npm。
4. 可选：Docker Desktop 或 OrbStack，用于 PostgreSQL、Redis 和 MinIO。

### 9.2 快速启动

首次运行或基础设施变更后：

```bash
./scripts/deploy-project.sh && ./scripts/start-project.sh
```

Windows：

```bat
scripts\deploy-project.bat
scripts\start-project.bat
```

默认地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://localhost:5173` |
| 后端 API | `http://localhost:8000/api` |
| Swagger | `http://localhost:8000/api/docs` |
| ReDoc | `http://localhost:8000/api/redoc` |
| MinIO API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` |

### 9.3 手动启动

后端：

```bash
uv sync
uv run python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

本地基础设施：

```bash
make infra-up
make db-migrate
```

## 10. 质量保障方案

项目使用 Makefile 作为稳定命令入口：

```bash
make lint
make format
make test
make build
make check
make hooks
```

其中 `make check` 覆盖后端 Ruff lint、后端 Ruff format check、pytest 和前端 `npm run build`。`make hooks` 运行 `pre-commit run --all-files`。`make typecheck` 和 `make clean` 当前是占位目标，不能作为验证通过依据。

测试目录按 API、business、abilities、providers、infrastructure、core、architecture import rules 等分类组织。架构规则由 `tests/test_architecture_imports.py` 保护。

## 11. 项目约束与风险

### 11.1 约束

1. 不恢复 `/api/projects`、`/api/recommend`、`/api/association` 等退役接口。
2. 不让业务层直接依赖 SQLAlchemy、Redis client、外部 SDK 或本地绝对路径。
3. 不把 Redis 当业务真相源。
4. 不把大 CSV、图表、报告、音频、模型文件直接塞进 PostgreSQL。
5. 不从 `analysis/data-processing-pipeline/` 直接 import runtime 逻辑。
6. 不提供 TTS、语音播报或音频生成能力。

### 11.2 风险与待确认事项

1. 生产环境鉴权、API key 管理、服务端 LLM 密钥托管和审计仍属于后续路线，待确认具体方案。
2. Data Processing 进入 `needs_review` 时，当前文档显示没有 approval endpoint，待确认后续人工确认流程。
3. 前端测试补强、产物存储治理和大 JSON/图表性能优化仍在项目计划后续阶段。
4. 文档中的测试基线数量存在差异，验收时应以实际执行 `make check` 和 `make hooks` 结果为准。

## 12. 交付内容

1. 前端应用源码：`frontend/`。
2. 后端应用源码：`backend/`。
3. 数据库迁移与基础设施配置：`alembic/`、`docker-compose.dev.yml`。
4. 算法蓝本和离线实验归档：`analysis/`。
5. 自动化测试：`tests/`。
6. 启动和部署脚本：`scripts/`。
7. 项目文档：`README.md`、`docs/`。
8. 开源许可：`LICENSE`。

## 13. 依据来源

- `README.md`：项目定位、入口、当前能力、技术栈、启动方式和质量门。
- `docs/ARCHITECTURE.md`：分层架构、API surface、Retail/Data Processing 流程、前端 API 边界、基础设施说明。
- `docs/backend-api.md`：后端接口清单和响应约定。
- `docs/USAGE_GUIDE.md`：用户流程、状态说明、数据要求和产物入口。
- `docs/PROJECT_PLAN.md`：当前基线、产品目标、下一阶段路线和红线。
- `docs/requirements/software-requirements-specification.md`：业务需求、数据字段和设计约束。
- `docs/requirements/user-story.md`：用户角色、Epic、验收条件和范围外能力。
- `pyproject.toml`、`frontend/package.json`：后端与前端技术栈和依赖。
- `docker-compose.dev.yml`：PostgreSQL、Redis、MinIO 本地基础设施。
- `Makefile`：质量门、构建、测试和基础设施命令。
