# MarketMind 后端 PostgreSQL + Redis + Docker Compose 迁移设计方案

> 版本：v2，已吸收 Oracle 审查意见，并作为 First PR 基础设施切片的实施依据。
> 状态：First PR infra slice 已在工作区落地 SQLAlchemy / Alembic / PostgreSQL Adapter 骨架；Redis Queue、业务 read/write switch、历史数据迁移仍未实施。不删除旧逻辑，不替换现有 API，不改分析算法，不改前端契约。
> 架构约束：遵循 `API Controller -> Business Flow/Pipeline -> Ability Atom -> Provider Interface -> External Adapter`。SQL / ORM / DB session 属于 Infrastructure Layer，业务层只能通过 Provider Boundary 使用。

---

## 1. 信息源与真相约定

- **代码即真相**。本方案基于 `backend/`、`tests/`、`pyproject.toml`、`.env.example`、`Makefile`、实际文件树与运行时调研结论。
- README、既有 `docs/` 仅作背景；若文档与代码冲突，以代码为准。
- 任务运行时证据来自 `.sisyphus/explore/task-execution-model/findings.md` 与代码复核。
- 当前阶段不执行破坏性迁移；历史数据只读盘点，不写入 PostgreSQL。
- 生产终态可能使用 openGauss。Schema 设计采用 PostgreSQL 兼容语义，同时避免 PostgreSQL 专属扩展。JSON 字段在模型层按逻辑 JSON 处理：PostgreSQL dev 可映射为 `JSONB`，openGauss 目标必须映射为 `JSON`。

---

## 2. 后端当前存储现状盘点

| 路径 / 实体 | Function / Class | 存储类型 | 数据内容 | 持久化级别 | 使用方 | 迁移判断 | 风险 |
|---|---|---|---|---|---|---|---|
| `data/projects.json` | `backend/core/storage.py:14-39` `ProjectStorage` | 单文件 JSON | V1 项目列表，含 `parameters`、`results`、`error_message` 等 | 强持久化 | `JsonProjectRepositoryAdapter` | 后续进入 PostgreSQL；First PR 不迁 | 无事务、全量读写、无文件锁，多 worker 会覆盖 |
| `data/projects/{project_id}/` | `ProjectStorage.create_project` | 目录树 | V1 项目目录、dataset、outputs | 强持久化 | V1 ProjectStorage 与本地 Adapter | 大文件保留文件系统；元数据进库 | 目录结构散落，删除项目会递归删目录 |
| `data/projects/{project_id}/analysis/artifacts/{type}/{name}` | `LocalAnalysisArtifactAdapter` | 文件系统 | table / figure / markdown / json 产物 | 强持久化 | `AnalysisArtifactProvider` 实现 | 文件留盘，artifact 元数据进库 | 现有 `save_*` 后写覆盖，同名产物迁移时必须 upsert |
| `data/projects/{project_id}/analysis/regularization/{job_id}/` | `LocalRegularizedDatasetAdapter` | 文件系统 | raw upload、normalized dataset、sidecar JSON | 强持久化 | `RegularizedDatasetProvider` 实现 | 文件留盘，uploaded_files / datasets / artifacts 元数据进库 | `storage_key` 含 project/job，与 artifact `storage_key` 语义不一致 |
| `data/projects/{project_id}/{model_type}/current.pkl` | `LocalAnalysisModelStoreAdapter` | pickle 文件 | Retail V2 项目状态、索引、模型快照 | 强持久化 | `RetailAnalysisFlow` 经 `AnalysisModelStoreProvider` | First PR 不迁；后续把状态元数据迁入 PG，模型文件留盘 | pickle 反序列化风险、无锁、状态覆盖 |
| `backend/data/model_data.pkl` | `LocalRecommendationModelStoreAdapter` | pickle 文件 | 旧推荐模型全局状态 | 强持久化（legacy） | Recommendation model store | 冻结，不纳入 First PR | 全局模型与项目隔离不足 |
| `outputs/charts/` `outputs/reports/` `outputs/audio/` | `backend/main.py` StaticFiles `/outputs` | 文件系统 | 图表、报告、音频等公开产物 | 强持久化 | 前端和 API URL | 不进库；只登记 URI / URL | Worker 容器化后需要共享卷或对象存储 |
| `backend/data/audio/` / voice audio | voice / ai_voice 相关路径 | 文件系统 | 音频产物或占位 URL | 待核验 | `backend/api/voice.py`、`backend/api/ai_voice.py` 存在，但其导入的 voice pipeline 文件当前不在 `backend/business/pipelines/` | 不在 First PR 处理 | 本轮只记录为 out-of-scope；若恢复音频能力，必须先做单独 runtime/storage 盘点 |
| Retail V2 project state | `RetailAnalysisFlow._save_state` | `AnalysisModelStoreProvider` 下的 pickle / dict | `status`、`stage_statuses`、`artifact_refs`、recommendations、marketer_insights、job_id、trace_id | 强持久化 | Retail V2 API | 后续映射为 `projects` + latest `processing_runs` + `artifacts` + `analysis_results` | 当前每 project 只暴露最新状态，历史 run 语义未公开 |
| Retail project index sentinel | `PROJECT_INDEX_ID = "_retail_analysis_index"` | 逻辑哨兵 id | Retail V2 项目索引 | 强持久化但不必然是独立目录 | `RetailAnalysisFlow._load_project_index` / `_save_project_index` | 映射到 `projects` 查询；不要把它当真实目录证据 | v1 文档误写成已确认磁盘目录，已修正 |
| Data Processing job state | `new_job_state` / `job_view` | dict + provider 持久化 | `job_id`、`project_id`、7 阶段状态、quality、capability、output_refs | 强持久化 | Data Processing Flow | 映射为 `processing_runs` + `datasets` + `artifacts` | 独立 job_id，与 Retail project-state 语义不同 |
| 依赖清单 | `pyproject.toml` | Python dependencies | 当前无 DB / queue dependency | N/A | 全后端 | First PR 才引入 SQLAlchemy / psycopg / Alembic | Python 3.13 要求 psycopg 3.2+ |

当前 `backend/infrastructure/adapters/` 下有 16 个 `.py` 文件（含 `__init__.py`），其中 15 个为具体 Adapter 实现。后续实施不依赖固定数量，以实际 Provider Interface 与 Adapter 职责为准。

---

## 3. 当前任务运行时盘点

| 入口 | 执行模型 | 状态记录 | 重试 / 取消 / 超时 | 多 worker 结果 | 迁移判断 |
|---|---|---|---|---|---|
| `POST /api/analysis/projects/{id}/run` | `FastApiBackgroundAnalysisJobAdapter` 调用 FastAPI in-process `BackgroundTasks` | Retail state 经 `AnalysisModelStoreProvider` 落盘 | 无 | 提交到哪个进程就只在哪个进程执行 | Phase 6 替换为 Redis-backed queue |
| `POST /api/analysis/jobs/{id}/run` | 同上 | Data Processing job state | 无 | 同上 | Phase 6 替换 |
| `POST /api/analysis/projects/{id}/dataset` | handler 内同步执行 dataset preparation | 立即写状态 | 无 | 阻塞当前请求进程 | 后续可拆成 queued preparation run |
| `POST /api/analysis/jobs/{id}/regularize` | handler 内同步 pandas regularization | 立即写状态 | 无 | 阻塞当前请求进程 | 后续可入 queue，但 First PR 不改 |
| voice / ai_voice | API 文件存在，当前导入的 voice pipeline 文件缺失 | 音频 URL / 文件路径需单独核验 | 无 | 与当前进程绑定 | 不进入 First PR；若恢复音频能力，Phase 6 前单独盘点写入路径与公开 URL |

结论：当前后端没有持久化任务队列，只有 FastAPI 进程内 BackgroundTasks。多 worker / 多副本部署会导致任务不可见、重启丢任务、并发覆盖。Phase 6 之前，部署文档必须保守声明只支持单 worker。

---

## 4. 存储模型判断

- **未发现真实 SQLite 使用**。当前仓库未发现 SQLite 客户端、SQLite 数据文件或实际运行路径。
- 当前真实存储是：文件系统 + JSON 索引 + pickle 模型 / 状态快照 + generated artifacts。
- PostgreSQL 的第一职责是承载**业务真相元数据**：项目、文件、数据集、处理运行、产物索引、小型结构化结果。
- Redis 的第一职责是**运行时辅助**：队列、短 TTL 进度、锁、缓存。Redis 永远不是业务真相源。
- 大 CSV、图表、报告、音频、模型文件不直接塞进 PostgreSQL。PostgreSQL 只保存 `storage_uri` / `storage_key` / `url` / checksum / size / metadata。

---

## 5. 目标架构边界

### 5.1 固定调用方向

```text
API Controller
  -> Business Flow / Business Pipeline
  -> Ability Atom
  -> Provider Interface
  -> External Adapter
  -> DB / FileSystem / Redis / HTTP / SDK
```

### 5.2 SQL 层归属

SQLAlchemy model、engine、session、Alembic migration、PostgreSQL client 全部属于 **Infrastructure Layer / External Adapter 支撑设施**，不得成为业务层直接依赖。

目标路径建议：

```text
backend/infrastructure/db/base.py
backend/infrastructure/db/session.py
backend/infrastructure/db/models/*.py
backend/infrastructure/adapters/postgres_project_repository_adapter.py
backend/infrastructure/adapters/postgres_analysis_state_adapter.py   # 后续阶段，非 First PR
```

不创建 `backend/repositories/`。原因：项目已有 `backend/providers/*_provider.py` 作为 Provider Interface，已有 `backend/infrastructure/adapters/*_adapter.py` 作为实现层。新建 `backend/repositories/` 会形成第二套抽象，绕过 Provider Boundary。

### 5.3 Provider Boundary 对齐

| 能力 | 现有 Provider Interface | 现有 Adapter | PostgreSQL 迁移方向 |
|---|---|---|---|
| V1 project metadata | `ProjectRepositoryProvider` | `JsonProjectRepositoryAdapter` | 新增 `PostgresProjectRepositoryAdapter`，实现同一 Protocol，First PR 不接线 |
| 长任务调度 | `AnalysisJobProvider` | `FastApiBackgroundAnalysisJobAdapter` | Phase 6 新增 RQ / Dramatiq Adapter，实现同一 Protocol |
| Retail state / model store | `AnalysisModelStoreProvider` | `LocalAnalysisModelStoreAdapter` | 后续拆分：状态元数据进 PG，模型文件仍由文件 Adapter 管理 |
| Analysis artifact | `AnalysisArtifactProvider` | `LocalAnalysisArtifactAdapter` | 文件保存仍在 Adapter，metadata shadow write 到 PG |
| Regularized dataset | `RegularizedDatasetProvider` | `LocalRegularizedDatasetAdapter` | 文件保存仍在 Adapter，uploaded_files / datasets metadata shadow write 到 PG |
| Generated asset | `GeneratedAssetProvider` | `LocalGeneratedAssetAdapter` | outputs 元数据可后续进 PG，文件仍在 outputs |

### 5.4 Settings 到 Adapter 的配置路径

```text
.env / environment
  -> backend.core.config.Settings
  -> backend.infrastructure.factories.provider_factory.create_providers(...)
  -> External Adapter constructor
```

禁止 Business Flow / Pipeline / Ability 读取 `DATABASE_URL`、`REDIS_URL`、`os.environ` 或直接创建 DB session。

---

## 6. 业务数据模型

| 实体 | 语义 | 关键字段 | 现有来源 | 迁移备注 |
|---|---|---|---|---|
| Project | 用户可见项目 | id、name、description、status、created_at、updated_at、metadata | V1 `Project`、Retail project state、Data Processing project_id | Retail 与 Data Processing 共用项目视角 |
| UploadedFile | 原始上传文件 | id、project_id、kind、filename、storage_key、storage_uri、checksum、size | `dataset.csv`、raw_upload | 文件不入库 |
| Dataset | 规范化数据集 | id、project_id、source_file_id、dataset_type、schema_json、quality_summary_json、storage_uri | clean dataset、normalized dataset | schema / quality 小 JSON 入库，CSV 留盘 |
| ProcessingRun | 一次处理运行 | id、project_id、run_type、status、stage_statuses_json、trace_id、job_id、is_latest、input_refs_json、error_json | Retail run、Data Processing job、regularization、report、tts | Retail 当前公开语义是 project 最新状态；Data Processing 有独立 job_id |
| Artifact | 产物索引 | id、project_id、run_id、artifact_type、name、storage_key、storage_uri、url、metadata_json、created_at、updated_at | `AnalysisArtifactReferenceDTO`、sidecars、outputs | 同 `(project_id, artifact_type, name)` 后写覆盖，需要 upsert |
| AnalysisResult | 小型结构化结果 | id、project_id、run_id、result_type、payload_json | recommendations、marketer_insights、association summaries | 单条 payload 设大小上限；大结果落 artifact |

### 6.1 V1 `Project` 字段映射

| `backend/models/project.py` 字段 | 目标位置 | 说明 |
|---|---|---|
| `id` | `projects.id` | 应用层 UUID 字符串 |
| `name` | `projects.name` | 保持长度约束 |
| `description` | `projects.description` | 可空 |
| `dataset_filename` | `uploaded_files.filename` 或 `projects.metadata_json.dataset_filename` | Phase 4 dual write 时优先落 uploaded_files |
| `dataset_path` | `uploaded_files.storage_uri` | 不暴露主机绝对路径；使用 logical URI |
| `status` | `projects.status` + latest `processing_runs.status` | Project 视图保持现有状态 |
| `parameters` | `projects.metadata_json.parameters` | V1-only 参数先整体保留 |
| `results.association_rules` | `analysis_results.payload_json` 或 artifact JSON | 小量规则进 `analysis_results`；大量规则落 JSON artifact |
| `results.prediction_data` / `clustering_data` | `analysis_results.payload_json` | 仅历史迁移阶段处理 |
| `results.charts` / `report_path` | `artifacts.url` / `artifacts.storage_uri` | 文件不入库 |
| `error_message` | `processing_runs.error_json.message` + `projects.metadata_json.legacy_error_message` | 保留历史可见语义 |
| `created_at` / `updated_at` | `projects.created_at` / `projects.updated_at` | 原样迁移 |

### 6.2 Retail run 与 Data Processing job 的差异

- Retail V2 当前由 project state 表达，`start_analysis` 会覆盖同一 project 的 `job_id`、`trace_id`、下游产物和 stage 状态。公开 API `GET /api/analysis/projects/{id}` 返回最新 project state。
- Data Processing 由独立 `job_id` 表达，`GET /api/analysis/jobs/{id}` 返回 job state。
- `processing_runs` 同时支持两类语义：
  - Retail：写入新 run，并用 `is_latest=true` 标记当前公开状态；旧 run 可以保留为审计，但不影响现有 API。
  - Data Processing：`job_id` 是公开查询键，历史 job 保留。
- First PR 不接入读写，不改变现有语义。Phase 4 shadow write 时先记录事实；Phase 5 read switch 时明确 latest 选择规则。

---

## 7. PostgreSQL / openGauss Schema 设计

### 7.1 设计原则

- 主键使用应用层 UUID 字符串，类型为 `VARCHAR(36)` 或 `CHAR(36)`，不使用 `pgcrypto`、`gen_random_uuid()`、`uuid_generate_v4()`。
- JSON 字段用 SQLAlchemy `JSON` 逻辑类型。PostgreSQL dev 可以选择 JSONB variant；openGauss 目标必须渲染为 JSON。业务代码不得依赖 `@>`、`#>`、`?` 等 PostgreSQL JSONB 专属操作符。
- `created_at` / `updated_at` 由应用层写入 UTC 时间；不依赖 DB trigger。
- 所有大对象只保存 URI / key / metadata。
- Adapter 层负责事务、参数化 SQL、错误转换与 session 生命周期。

### 7.2 第一版 6 张表

```text
projects
uploaded_files
datasets
processing_runs
artifacts
analysis_results
```

### 7.3 逻辑 DDL 草案

> 下方是逻辑 schema，不是最终 Alembic 脚本。First PR 生成 migration 时使用 SQLAlchemy 类型，避免手写 PostgreSQL 专属表达式。

```sql
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL,
    metadata_json JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE uploaded_files (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    kind VARCHAR(32) NOT NULL,
    filename VARCHAR(512) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    storage_uri TEXT NOT NULL,
    checksum VARCHAR(128),
    size_bytes BIGINT,
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE datasets (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    source_file_id VARCHAR(36) REFERENCES uploaded_files (id) ON DELETE SET NULL,
    dataset_type VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    storage_uri TEXT NOT NULL,
    schema_json JSON NOT NULL,
    row_count BIGINT,
    column_count INTEGER,
    quality_summary_json JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE processing_runs (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    run_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    job_id VARCHAR(64),
    trace_id VARCHAR(64),
    is_latest BOOLEAN NOT NULL,
    attempt INTEGER NOT NULL,
    stage_statuses_json JSON NOT NULL,
    input_refs_json JSON NOT NULL,
    result_summary_json JSON NOT NULL,
    error_json JSON,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_ms BIGINT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE artifacts (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    run_id VARCHAR(36) REFERENCES processing_runs (id) ON DELETE SET NULL,
    artifact_type VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    storage_uri TEXT NOT NULL,
    url VARCHAR(512),
    metadata_json JSON NOT NULL,
    size_bytes BIGINT,
    checksum VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (project_id, artifact_type, name)
);

CREATE TABLE analysis_results (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    run_id VARCHAR(36) REFERENCES processing_runs (id) ON DELETE SET NULL,
    result_type VARCHAR(32) NOT NULL,
    payload_json JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### 7.4 索引建议

- `projects(status)`、`projects(updated_at)`
- `uploaded_files(project_id)`
- `datasets(project_id)`、`datasets(source_file_id)`
- `processing_runs(project_id)`、`processing_runs(job_id)`、`processing_runs(status)`、`processing_runs(run_type)`
- `artifacts(project_id)`、`artifacts(run_id)`、`artifacts(project_id, artifact_type, name)`
- `analysis_results(project_id)`、`analysis_results(run_id)`、`analysis_results(result_type)`

不在 First PR 建 GIN / expression / partial index。若 PostgreSQL dev 想为 `is_latest` 建 partial unique index，必须先确认 openGauss 替代方案；First PR 先用 Adapter 事务与测试保证 latest 语义。

---

## 8. Redis 设计

Redis 不进入 First PR 的 Python 代码；Compose 可以先提供 Redis 服务，后端默认 `REDIS_ENABLED=false`、`TASK_QUEUE_BACKEND=none`。

未来用途：

| 用途 | Key 形态 | 真相级别 | TTL | 说明 |
|---|---|---|---|---|
| 任务队列 | 由 RQ / Dramatiq 管理 | 运行时辅助 | 队列策略决定 | 替换 FastAPI BackgroundTasks |
| 进度哈希 | `run:{run_id}:progress` | 辅助缓存 | 24h | UI 轮询优化；PostgreSQL `processing_runs.status` 仍是真相 |
| 分布式锁 | `lock:project:{project_id}:run` | 并发保护 | 短 TTL + watchdog | 防止同 project 重复 run 覆盖 |
| TTS / LLM 缓存 | `cache:tts:{hash}` / `cache:llm:{hash}` | 可丢缓存 | 按业务决定 | 缓存值为 artifact / text ref，不存大文件 |

队列建议：

- 倾向 **Dramatiq** 作为 Phase 6 默认候选：有 broker 抽象，后续可从 Redis 切 RabbitMQ；同步 worker 模型适配 pandas/sklearn。
- RQ 是备选：上手快、Redis 绑定强，适合较小任务规模。
- 不选 Celery 作为默认：运维面与配置复杂度过高。
- 不选 Arq 作为默认：代码库不是 async-first，当前 pipeline 大多是同步 CPU / pandas 工作负载。

---

## 9. Docker Compose 与环境变量设计

### 9.1 `docker-compose.dev.yml`

First PR 可新增开发用 Compose，只提供基础服务，不容器化后端：

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: marketmind-postgres-dev
    restart: unless-stopped
    environment:
      POSTGRES_DB: marketmind
      POSTGRES_USER: marketmind
      POSTGRES_PASSWORD: marketmind_dev_password
    ports:
      - "5432:5432"
    volumes:
      - marketmind_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U marketmind -d marketmind"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: marketmind-redis-dev
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "6379:6379"
    volumes:
      - marketmind_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  marketmind_postgres_data:
  marketmind_redis_data:
```

### 9.2 `.env.example` 追加项

```dotenv
DATABASE_URL=postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind
TEST_DATABASE_URL=postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind_test
DB_ECHO=false
DB_POOL_SIZE=5
DB_POOL_MAX_OVERFLOW=10

REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=false
TASK_QUEUE_BACKEND=none
```

约束：

- `.env.example` 中的 `marketmind_dev_password` 仅用于本地开发 Compose。生产必须由 secret manager / deployment secret 注入。
- `.env` / `.env.local` 必须被 `.gitignore` 覆盖，First PR 需要复核。
- 本地后端运行在宿主机时使用 `localhost`；后续若后端容器化，连接串改为 `postgres:5432` / `redis:6379`。
- Phase 6 worker 容器化时必须决定 `outputs/` 的共享卷或对象存储策略，否则 FastAPI `StaticFiles(directory="outputs")` 读不到 worker 写出的产物。

---

## 10. 分阶段迁移路线

| Phase | 名称 | 范围 | 可验证结果 | 回滚方式 |
|---|---|---|---|---|
| 0 | 设计与审查 | 本文档、Oracle 审查、用户确认 | 文档 GO | 不改代码 |
| 1 | Infra Shell | Compose、`.env.example`、Makefile infra targets、CI PG service | `make infra-up` healthy；CI 能连 PG | 删除 Compose / targets / CI service |
| 2 | DB Infrastructure | `backend/infrastructure/db/*`、SQLAlchemy / psycopg / Alembic、初始 migration | `alembic upgrade head` / `downgrade base` | downgrade + 回退文件 |
| 3 | Adapter Skeleton | `PostgresProjectRepositoryAdapter` 实现现有 `ProjectRepositoryProvider`，不接线 | Adapter contract tests pass | 删除新 Adapter，不影响 runtime |
| 4 | Dual Write | 现有文件 Adapter 写文件，同时 PG shadow write 元数据 | 一致性核对通过；读仍走旧逻辑 | 关闭 shadow write，清空 shadow tables |
| 5 | Read Switch | metadata read 切 PG；文件仍由 FileSystem Adapter 读取 | API contract tests 全绿 | feature flag 切回旧读路径 |
| 6 | Redis Queue / Worker | Dramatiq / RQ Adapter 替换 BackgroundTasks，加入锁和进度 | 单 worker + 多 worker 冒烟通过 | queue backend 切回 none（仅限未发布前） |
| 7 | Historical Migration | `data/projects.json` / pickle state dry-run + 迁移脚本 | dry-run 报告、校验报告、可回滚 | 保留原文件，只回滚 DB 写入 |
| 8 | openGauss / Cleanup | JSON 类型映射、驱动兼容、删除旧 JSON 索引路径 | openGauss regression pass | 保留 PostgreSQL 兼容迁移路径 |

阶段门禁：一次只做一个内聚阶段；每阶段要有行为保护、Architecture Lint、Runtime Check 或等价验证。未通过不得进入下一阶段。

---

## 11. First PR 代码改动计划

### 11.1 新增

- `docker-compose.dev.yml`
- `backend/infrastructure/db/__init__.py`
- `backend/infrastructure/db/base.py`
- `backend/infrastructure/db/session.py`
- `backend/infrastructure/db/models/__init__.py`
- `backend/infrastructure/db/models/project.py`
- `backend/infrastructure/db/models/uploaded_file.py`
- `backend/infrastructure/db/models/dataset.py`
- `backend/infrastructure/db/models/processing_run.py`
- `backend/infrastructure/db/models/artifact.py`
- `backend/infrastructure/db/models/analysis_result.py`
- `backend/infrastructure/adapters/postgres_project_repository_adapter.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/0001_initial_schema.py`
- `tests/infrastructure/db/test_alembic_roundtrip.py`
- `tests/infrastructure/db/test_schema_compatibility.py`
- `tests/infrastructure/adapters/test_postgres_project_repository_adapter.py`

### 11.2 修改

- `pyproject.toml`
  - runtime dependencies：`sqlalchemy>=2.0.31`、`psycopg[binary]>=3.2.4`、`alembic>=1.13.2`
  - 不新增 `redis`、`rq`、`dramatiq`
- `.env.example`
  - 追加第 9.2 节字段
- `backend/core/config.py`
  - 新增 DB / Redis / queue setting 字段
  - 只由 Infrastructure factory / Adapter 使用，不让业务层读取
- `Makefile`
  - `infra-up`、`infra-down`、`infra-reset`、`infra-logs`
  - `db-migrate`、`db-downgrade`、`db-revision`
- `.github/workflows/*.yml`
  - backend job 增加 `postgres:16-alpine` service 或等价 `TEST_DATABASE_URL`
  - CI 加 `uv run alembic upgrade head` / `downgrade base` / `upgrade head`
- `tests/api/test_controller_thinness.py`
  - `FORBIDDEN_PREFIXES` 增加 `backend.infrastructure.db`、`sqlalchemy`
- `tests/test_architecture_imports.py`
  - `api`、`business`、`abilities`、`providers` 禁止 import `backend.infrastructure.db`、`sqlalchemy`、`psycopg`
  - AST 检查 `os.environ`、`os.getenv`、直接实例化 `Settings()` 或直接读取 settings reader；仅允许 `backend/api/dependencies.py` 与 `backend/infrastructure/factories/provider_factory.py` 等装配入口按既有 allowlist 使用
  - 禁止新增 `backend/repositories` 层，除非后续有显式架构决策
- `docs/development.md` 或 `docs/QUICKSTART.md`
  - 记录 Phase 6 前只支持单 worker；不要用 `uvicorn --workers > 1` 承载长任务

### 11.3 不改

- 不修改 `backend/api/**` 路由行为
- 不修改 `backend/business/**` Flow / Pipeline 行为
- 不修改 `backend/abilities/**` 算法
- 不修改 `backend/providers/**` Protocol 签名，除非测试证明必须补窄接口
- 不替换 `ProvidersContainer` 接线
- 不修改现有 `JsonProjectRepositoryAdapter`、`LocalAnalysisArtifactAdapter`、`LocalRegularizedDatasetAdapter` 等本地 Adapter 运行路径
- 不修改 `frontend/**`
- 不新增历史数据迁移脚本
- 不新增 Redis 代码

### 11.4 Session 策略

- First PR 使用同步 SQLAlchemy engine / session，与当前同步 pandas/sklearn pipeline 一致。
- Adapter 方法内创建短生命周期 session，进入事务，完成后释放。
- 禁止跨业务 stage 持有 DB connection。
- Adapter 捕获 SQLAlchemy / psycopg 异常并转换为内部基础设施错误，不向业务层泄漏原始 DB 异常。

---

## 12. 风险分析与约束

| 风险 | 影响 | 文档约束 / 后续动作 |
|---|---|---|
| 另起 `backend/repositories/` | 绕过 Provider Boundary | 已删除该设计；PG repository 是 External Adapter |
| 控制器直连 DB | API 层变厚，破坏架构 | First PR 增加 controller thinness 与 architecture import guard |
| Python 3.13 dependency 不兼容 | `uv sync` / CI 失败 | psycopg 3.2.4+、SQLAlchemy 2.0.31+、Alembic 1.13.2+ |
| DB 集成测试无服务 | CI 假绿或必红 | CI service PostgreSQL + `TEST_DATABASE_URL` |
| `storage_key` 语义不一致 | 对象存储迁移困难 | Phase 4 前决策：artifact 是否补齐 `projects/{pid}/...` 规范前缀；现阶段只记录事实 |
| artifact 同名覆盖 | unique constraint 与现有行为冲突 | Adapter upsert 或 select-then-update；`artifacts.updated_at` 必填 |
| Retail run / Data Processing job 语义不同 | read switch 误读历史 | `processing_runs.is_latest` 表达 Retail 公开最新状态；Data Processing 保留 job_id |
| JSON 字段无限增长 | DB 行膨胀 | Adapter 层 payload size guard，超过阈值落 artifact 并存 ref |
| pickle 路径注入 | 反序列化 RCE | Phase 6/7 前加入 path whitelist：必须落在项目存储根目录下 |
| SQL 注入 | 数据破坏 | 迁移脚本与 Adapter 只能使用 SQLAlchemy 参数化表达；禁字符串拼接 SQL |
| 连接池耗尽 | 长任务阻塞请求 | 短 session；长任务 stage 不持有连接；Phase 6 worker 单独池配置 |
| outputs 跨容器不可见 | 前端 artifact URL 404 | Phase 6 必须决定共享卷或对象存储 |
| openGauss JSON 兼容 | `JSONB` DDL 失败 | 模型层使用逻辑 JSON；openGauss 渲染 JSON；不使用 JSONB operator |
| 明文 dev password | 误用于生产 | `.env.example` 标注 dev only，生产 secret 注入 |
| Alembic downgrade 误删 | 回滚破坏数据 | First PR 初始 migration 可 drop 空表；业务数据进入后任何 downgrade 必须有数据影响说明 |

---

## 13. First PR 推荐范围

### 13.1 必须包含

First PR 可以是一个 PR，但必须按三个可回滚子阶段验收，不得把验证混成一个“大改完成”口径。

1. Substage A - Infra Shell：本文档 v2、Docker Compose dev infra、`.env.example` 配置、Makefile infra targets、单 worker 运维说明。
2. Substage B - DB Infrastructure：`backend/infrastructure/db/`、SQLAlchemy / psycopg / Alembic dependency、6 张表 SQLAlchemy model、initial Alembic migration、CI PostgreSQL service、Alembic roundtrip。
3. Substage C - Adapter Skeleton：`PostgresProjectRepositoryAdapter` skeleton，作为 External Adapter 实现现有 `ProjectRepositoryProvider`；Adapter contract tests 覆盖 create/get/list/update/delete/count。
4. Architecture Lint 增强贯穿三个子阶段：API / business / abilities / providers 不得 import DB / SQLAlchemy / psycopg，不得直接读取 env，不得新增 `backend/repositories`。

### 13.2 必须排除

- 业务 API read/write switch。
- 删除旧 JSON / pickle / 文件系统逻辑。
- Redis queue / worker 代码。
- 历史数据迁移脚本。
- 前端变更。
- 分析算法变更。
- 大文件入库。
- 改 Provider Protocol 签名。

### 13.3 施工清单骨架（进入实施前复制为阶段清单或直接在 PR 描述中逐项验收）

| 顺序 | WHERE | WHY | HOW | EXPECTED_RESULT | VERIFY |
|---|---|---|---|---|---|
| 1 测试锚点 | `tests/api/test_controller_thinness.py`、`tests/test_architecture_imports.py` | 防止 DB 直连和 env 读取进入 Controller / Business / Provider | 增加 forbidden import 前缀，并用 AST 检查 `os.environ` / `os.getenv` / 直接实例化 `Settings()` | 架构边界机械化保护 | `uv run pytest tests/api/test_controller_thinness.py tests/test_architecture_imports.py` |
| 2 Provider Interface | `backend/providers/project_repository_provider.py` | 复用现有边界，不另起接口 | 不改签名，仅确认 PG Adapter 满足 Protocol | 业务层仍只见 Provider Interface | `uv run python -m py_compile backend/providers/project_repository_provider.py` |
| 3 External Adapter | `backend/infrastructure/adapters/postgres_project_repository_adapter.py` | SQL 实现在 Adapter Layer | 实现 ProjectRepositoryProvider，内部用 session factory | Adapter contract tests 通过 | `uv run pytest tests/infrastructure/adapters/test_postgres_project_repository_adapter.py` |
| 4 DB Infrastructure | `backend/infrastructure/db/*`、`alembic/*` | DB client / ORM 属于 Infrastructure | 建 base/session/models/migration | Alembic 可升降级 | `uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head` |
| 5 Config | `backend/core/config.py`、`.env.example` | Settings 是唯一配置入口 | 添加 DATABASE_URL 等字段 | 业务层无 env 读取 | Architecture Lint |
| 6 Runtime / CI | `.github/workflows/*.yml`、`Makefile` | DB 行为必须可验证 | PG service + infra/db targets | CI 可跑 DB 测试 | CI backend job |
| 7 Docs | `docs/development.md` 或 `docs/QUICKSTART.md` | Phase 6 前多 worker 不安全 | 写明 single-worker limitation | 运维不会误开多 worker | 文档 grep |

---

## 14. 验证计划

### 14.1 文档阶段（当前）

- Oracle 审查本设计文档。
- 修复 Critical Gaps 后再进入实施决策。

### 14.2 First PR 本地验证

```bash
make infra-up
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
uv run pytest tests/infrastructure/db tests/infrastructure/adapters/test_postgres_project_repository_adapter.py
uv run pytest tests/api/test_controller_thinness.py tests/test_architecture_imports.py
make lint
make format
make lint
make check
```

如果 `make check` 因既有无关债务失败，必须记录失败项、证明 touched-scope 通过，不得声称全量通过。

### 14.3 API 契约回归（确保 First PR 未改业务行为）

```bash
uv run pytest tests/api/test_retail_analysis_contracts.py
uv run pytest tests/api/test_data_processing_analysis_contracts.py
```

期望：First PR 不碰 Controller / Flow，因此这两组测试应与基线一致。

### 14.4 Schema / openGauss 兼容守护

新增测试或脚本检查 Alembic SQL 不含：

- `gen_random_uuid`
- `uuid_generate_v4`
- `CREATE EXTENSION pgcrypto`
- `JSONB` 类型字面量（openGauss 目标使用 `JSON`）
- JSONB 专属 operator：`@>`、`#>`、`?`、`?&`、`?|`
- PostgreSQL 方言专属 migration 选项：`postgresql_where`、`postgresql_using`、`postgresql_ops`
- 业务层直接 import `sqlalchemy` / `psycopg`

openGauss 切换前补充真实 openGauss dry-run。First PR 只承诺 PostgreSQL dev + openGauss-compatible design，不承诺已在 openGauss 实例验证。

### 14.5 Phase 6 前置验证

Redis / worker 阶段进入前必须新增：

- queue Adapter contract test。
- project-level distributed lock test。
- job replay test。
- `outputs/` 共享卷或对象存储端到端 smoke。
- 多 worker smoke：两个 worker 并发，重复 run 不覆盖，任务不丢失。

---

## 附录：关键代码锚点

- Provider Interface：`backend/providers/project_repository_provider.py:8`
- 现有 JSON Adapter：`backend/infrastructure/adapters/json_project_repository_adapter.py:13`
- Provider Container：`backend/providers/container.py:18-32`
- Provider Factory：`backend/infrastructure/factories/provider_factory.py:36-64`
- Controller 依赖入口：`backend/api/dependencies.py:13-20`
- Controller thinness guard：`tests/api/test_controller_thinness.py:19-30`
- Architecture import guard：`tests/test_architecture_imports.py:9-42`
- FastAPI BackgroundTasks Adapter：`backend/infrastructure/adapters/fastapi_background_analysis_job_adapter.py:35-43`
- Retail state shape：`backend/business/flows/retail_analysis_state.py:18-37`
- Retail latest project state write：`backend/business/flows/retail_analysis_flow.py:344-369`
- Data Processing job state：`backend/business/flows/data_processing_analysis_state.py:22-39`
- Artifact `storage_key` / URL：`backend/infrastructure/adapters/local_analysis_artifact_adapter.py:105-119`
- Regularized dataset `storage_key`：`backend/infrastructure/adapters/local_regularized_dataset_adapter.py:56-72`、`93-109`
- V1 Project model：`backend/models/project.py:39-59`
- V1 JSON storage：`backend/core/storage.py:14-39`
- Current dependencies：`pyproject.toml:7-35`

— 文档结束 —
