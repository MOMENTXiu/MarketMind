# Quickstart

MarketMind 当前主应用是 Vue 3 + FastAPI。命令默认从仓库根目录执行。

## Requirements

- Python `>=3.13,<3.14`，建议 3.13.9。
- `uv`。
- Node.js 18+ 与 npm。
- 可选：OrbStack 或 Docker Desktop，用于 PostgreSQL/Redis。

## One-command Start

macOS / Linux：

```bash
bash scripts/start-project.sh
```

Windows：

```bat
scripts\start-project.bat
```

默认地址：

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api`
- Swagger: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

## Manual Start

安装后端依赖：

```bash
uv sync
```

启动后端：

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

安装并启动前端：

```bash
cd frontend
npm install
npm run dev
```

前端开发环境通过 `frontend/vite.config.ts` 代理 `/api` 与 `/outputs` 到 `http://localhost:8000`。跨域部署时使用 `VITE_API_BASE_URL` 和 `VITE_API_TIMEOUT`。

## Optional Local Infrastructure

PostgreSQL/Redis/MinIO 用于 Retail V2 state、Redis/RQ worker queue、SSE event pub/sub、对象存储和 DB smoke tests。

```bash
make infra-up
make db-migrate
```

常用命令：

```bash
make infra-down
make infra-reset
make infra-logs
make db-downgrade
make db-revision DB_REVISION_MESSAGE="describe change"
```

MinIO 服务在 `docker-compose.dev.yml` 中定义，端口 `9000`（API）和 `9001`（Console）。当 `OBJECT_STORAGE_BACKEND=minio` 时，样本文件、原始上传、标准化数据集、sidecars、artifacts 和模型都存储在 MinIO；`local` 时仍使用文件系统。

`TEST_DATABASE_URL` 必须指向隔离测试库；迁移 roundtrip 测试会 drop/recreate 表。新 volume 会通过 `scripts/postgres-init/01-create-test-db.sql` 创建 `marketmind_test`。

## Verify The Workspace

完整本地质量门：

```bash
make check
make hooks
```

拆分命令：

```bash
make lint
make format
make test
make build
```

当前基线：

- Backend tests: `268 collected` (`262 passed, 5 skipped`)。
- Backend lint/format: Ruff。
- Frontend build/type validation: `cd frontend && npm run build`。
- `make typecheck` 和 `make clean` 是占位目标，不能作为验证证据。

## Retail V2 Smoke Data

Retail V2 使用固定中文列 CSV：

```text
tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
```

字段契约以 `backend/providers/dtos.py` 的 `RETAIL_RAW_SALES_COLUMNS` 为准。

## Data Processing Smoke Flow

前端入口：`http://localhost:5173/data-processing`。

后端流程：

```text
create job -> upload raw CSV/Excel -> regularize -> run -> outputs/sidecars
```

当数据没有共购结构时，association 阶段可以 `skipped`，Job 仍可 `completed`。`needs_review` 只应阻断 core 字段需要复核的标准化结果。

## Runtime Checks

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
uv run python -m backend.core.runtime_checks check-object-storage --sandbox
uv run python -m backend.core.runtime_checks check-minio --sandbox
uv run python -m backend.core.runtime_checks check-sample-files
```

## Optional Streamlit Entry

`app.py` 是早期单机版入口，不是当前主应用路径。

```bash
uv run streamlit run app.py
```
