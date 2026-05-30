# MarketMind 架构

MarketMind 当前运行形态是 Vue 3 前端 + FastAPI 后端。后端以 Provider Boundary 隔离业务编排与外部资源，前端通过 `frontend/src/api/` typed client 调用后端公开契约。

## 运行时总览

```text
Browser / Vue 3
  -> frontend/src/api typed client
  -> FastAPI Controller
  -> Business Flow / Pipeline
  -> Ability Atom
  -> Provider Interface / ProvidersContainer
  -> Infrastructure Adapter
  -> PostgreSQL / Redis / MinIO (object storage) / LLM HTTP
```

`/api/analysis` 下并存两条分析链路：

| 链路 | 入口 | 适用数据 | 前端入口 | 当前状态 |
| --- | --- | --- | --- | --- |
| Retail Analysis V2 | `/api/analysis/projects...` | 固定中文列零售 CSV | `/projects` | 已接入前后端 runtime |
| Data Processing | `/api/analysis/jobs...` | 通用 CSV/Excel | `/data-processing` | 已接入前后端 runtime |

Customer Suggestions 是文本生成链路，入口为 `POST /api/analysis/customer-suggestions`。前端业务页面不直接调用第三方 LLM endpoint。

## 后端分层

| 层 | 路径 | 职责 | 禁止事项 |
| --- | --- | --- | --- |
| API Controller | `backend/api/` | 解析 HTTP 输入、调用单个 flow/pipeline、映射错误。`dependencies.py` 是 API 层唯一可直接 import `backend.core.config` 的模块；其他 API 模块通过它获取 `Settings` 类型和 `get_settings()`。 | 不写算法、存储细节、SDK 调用；不直接 import `backend.core.config`。 |
| Business Orchestration | `backend/business/flows/`, `backend/business/pipelines/` | 编排状态机、阶段顺序和副作用。 | 不直接 import DB/SDK/本地路径实现。 |
| Ability Atom | `backend/abilities/` | 执行可测试的原子分析能力。 | 不依赖 FastAPI request/response。 |
| Provider Boundary | `backend/providers/` | Protocol、DTO、`ProvidersContainer`。 | 不放具体基础设施实现。 |
| Infrastructure | `backend/infrastructure/` | JSON/local file/LLM/artifact/model/PostgreSQL adapter 等实现。 | 不反向依赖 API controller。 |
| Core | `backend/core/` | Settings、错误类型、runtime checks、legacy storage compatibility。 | 不承载业务流程。 |

架构规则由 `tests/test_architecture_imports.py` 保护。

## 主要目录

```text
backend/
  api/
    analysis.py              # Retail V2 + Data Processing + Customer Suggestions HTTP 边界
    dependencies.py          # Provider/pipeline/flow 依赖工厂
    error_mapping.py         # MarketMindError -> HTTPException
  business/
    flows/
      retail_analysis_flow.py
      data_processing_analysis_flow.py
    pipelines/
      retail_*_pipeline.py
      dataset_regularization_pipeline.py
      universal_*_pipeline.py
      customer_text_suggestion_pipeline.py
  abilities/
    retail/
    regularization/
    universal_analysis/
    report/
  providers/
    container.py
    *_provider.py
    dtos.py
  infrastructure/
    adapters/
    db/
    factories/provider_factory.py
  core/
    config.py
    errors.py
    runtime_checks.py

frontend/
  src/
    api/                     # axios client、types、retail/data-processing/suggestions wrappers
    views/
      Project*.vue           # Retail V2 工作流
      DataProcessing.vue     # 通用数据处理工作流
      ProductRecommend.vue   # 推荐与商品洞察
      CustomerAnalysis.vue   # 客户建议
    components/ServiceStatus.vue
    router/index.ts
```

`analysis/` 是离线实验与迁移源材料归档。后端 runtime 不直接 import `analysis/code_files` 或 `analysis/data-processing-pipeline`。

## API Surface

本地默认 base URL：`http://localhost:8000`。

| Area | Routes |
| --- | --- |
| App | `GET /`, `GET /api/health/`, `GET /api/docs`, `GET /api/redoc`, `GET /openapi.json` |
| Retail projects | `POST /api/analysis/projects`, `GET /api/analysis/projects`, `GET /api/analysis/projects/{project_id}`, `DELETE /api/analysis/projects/{project_id}` |
| Retail lifecycle | `POST /api/analysis/projects/{project_id}/dataset`, `POST /api/analysis/projects/{project_id}/run` |
| Retail results | `GET /api/analysis/projects/{project_id}/artifacts`, `GET /api/analysis/projects/{project_id}/artifacts/{artifact_id}`, `GET /api/analysis/projects/{project_id}/datasets/{dataset_id}`, `GET /api/analysis/projects/{project_id}/models/{model_type}/{version}` |
| Retail read models | `GET /api/analysis/projects/{project_id}/recommendations`, `GET /api/analysis/projects/{project_id}/marketer-insights` |
| Text suggestions | `POST /api/analysis/customer-suggestions` |
| Data Processing jobs | `POST /api/analysis/jobs`, `GET /api/analysis/jobs/{job_id}` |
| Data Processing lifecycle | `POST /api/analysis/jobs/{job_id}/raw-dataset`, `POST /api/analysis/jobs/{job_id}/regularize`, `POST /api/analysis/jobs/{job_id}/run` |
| Data Processing outputs | `GET /api/analysis/jobs/{job_id}/outputs`, `GET /api/analysis/jobs/{job_id}/datasets/{dataset_id}`, `GET /api/analysis/jobs/{job_id}/sidecars/{sidecar_id}` |
| Sample files | `GET /api/samples`, `GET /api/samples/{sample_id}`, `GET /api/samples/{sample_id}/download` |

Retired routes `/api/projects`, `/api/recommend`, `/api/association`, `/api/voice/*`, `/api/ai-voice/*` and `/api/tts/*` are intentionally absent.

## Retail Analysis V2 Flow

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

状态：`queued`, `processing`, `completed`, `failed`。阶段：`dataset_preparation`, `feature_engineering`, `segmentation`, `association`, `recommendation`, `marketer_insights`, `report`。

Retail V2 输入是固定中文列 CSV，字段以 `backend/providers/dtos.py` 的 `RETAIL_RAW_SALES_COLUMNS` 为准。

## Data Processing Flow

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

状态：`queued`, `processing`, `completed`, `failed`, `needs_review`。标准化只会因为 core 字段需要复核而阻断后续分析；optional/marketing fuzzy mapping 不阻断通用分析。

重要 sidecars：

- `sidecar:schema_mapping_detail`
- `sidecar:quality_report`
- `sidecar:capability`
- `sidecar:manifest`
- `sidecar:preview_rows`

## 前端接入边界

`frontend/src/api/` 是页面访问后端的唯一业务 API 边界：

- `client.ts`：axios 实例、timeout、envelope 解包。
- `errors.ts`：400/404/422/500 错误归一化。
- `types.ts`：API DTO、状态枚举和状态 helper。
- `retail.ts`：Retail V2 endpoint wrappers。
- `data-processing.ts`：Data Processing endpoint wrappers。
- `suggestions.ts`：Customer Suggestions 直返接口。
- `health.ts`：`GET /api/health/`。

Retail 项目详情页与 Data Processing Job 页使用 REST 做初始加载和兜底刷新，使用 EventSource 订阅 `/api/analysis/projects/{project_id}/events` 与 `/api/analysis/jobs/{job_id}/events` 作为正常状态更新路径。

Vite dev proxy 在 `frontend/vite.config.ts` 中将 `/api` 与 `/outputs` 转发到后端。部署时可用 `VITE_API_BASE_URL` 改写 base URL。

## Persistence And Infrastructure

Retail V2 runtime 已切到 PostgreSQL state、Redis/RQ queue 和 Redis pub/sub SSE：

- Compose：`docker-compose.dev.yml`
- Alembic：`alembic/`, `alembic.ini`
- SQLAlchemy base/session/models：`backend/infrastructure/db/`
- Retail state adapter：`backend/infrastructure/adapters/postgres_retail_analysis_state_adapter.py`
- Redis queue adapter：`backend/infrastructure/adapters/redis_analysis_job_queue_adapter.py`
- Redis event stream adapter：`backend/infrastructure/adapters/redis_analysis_event_stream_adapter.py`
- Worker entry：`backend/workers/retail_analysis_worker.py`

大 CSV、图表、报告、模型 artifact 和 Data Processing raw/normalized datasets/sidecars 仍保留在文件系统，通过 Provider ref 和 API URL 暴露。Redis 只承载队列与事件，不是业务真相源。D5 采用 start blank：历史 Retail pickle state 不迁移。

## Quality Gate

```bash
make lint
make format
make check
make hooks
```

`make check` 运行 backend Ruff lint、backend Ruff format check、pytest、frontend `npm run build`。当前测试基线为 `306 passed, 6 skipped`。`make typecheck` 与 `make clean` 是占位目标。

Runtime smoke checks：

```bash
uv run python -m backend.core.runtime_checks check-config
uv run python -m backend.core.runtime_checks check-providers
uv run python -m backend.core.runtime_checks validate-api-schemas
uv run python -m backend.core.runtime_checks check-telemetry
uv run python -m backend.core.runtime_checks check-analysis-artifacts --sandbox
uv run python -m backend.core.runtime_checks check-retail-analysis --sample
uv run python -m backend.core.runtime_checks check-retail-runtime --dry-run
uv run python -m backend.core.runtime_checks check-data-processing --sample
uv run python -m backend.core.runtime_checks check-regularization --sandbox
uv run python -m backend.core.runtime_checks check-analysis-optional-runtime
```
