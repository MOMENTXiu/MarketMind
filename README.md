# MarketMind

MarketMind 是一个面向零售与通用交易数据的 AI 营销分析系统。当前主线是 **Vue 3 + FastAPI** 前后端分离应用，后端通过分层架构编排分析流程，前端通过 typed API client 接入公开 HTTP 契约。

## 当前能力

- Retail Analysis V2：创建项目、上传固定中文列零售 CSV、运行清洗、特征工程、分群、关联、推荐、营销洞察和报告链路。
- Data Processing：创建 Job、上传通用 CSV/Excel、执行 `regularization -> analysis2` 通用分析链路，读取 quality、capability、outputs 和 sidecars。
- AI 文本建议：前端通过后端 `POST /api/analysis/customer-suggestions` 生成客户营销建议与商品洞察文本。
- 前端工作台：Retail 项目页、Data Processing 页、SSE 状态刷新、产物引用展示、服务健康状态和设置页 LLM 配置。
- 本地基础设施：Docker Compose 提供 PostgreSQL 与 Redis；Retail V2 runtime 已通过 Provider Boundary 使用 PostgreSQL state、Redis/RQ queue 与 Redis pub/sub SSE。Redis 只承载队列和事件，不作为业务真相源。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI, Uvicorn, Pydantic 2, pandas, scikit-learn, mlxtend, SQLAlchemy, Alembic |
| 前端 | Vue 3, Vite, TypeScript, Vue Router, Pinia, Element Plus, ECharts, Axios |
| 工具 | uv, npm, Ruff, pytest, pre-commit, Docker Compose |

## 环境要求

- Python `>=3.13,<3.14`，建议 Python 3.13.9。
- `uv`。
- Node.js 18+ 与 npm。
- 可选：OrbStack 或 Docker Desktop，用于 PostgreSQL/Redis 本地服务。

## 快速启动

一键启动前后端：

```bash
bash scripts/start-project.sh
```

Windows：

```bat
scripts\start-project.bat
```

默认地址：

- 前端：`http://localhost:5173`
- 后端 API：`http://localhost:8000/api`
- Swagger：`http://localhost:8000/api/docs`
- ReDoc：`http://localhost:8000/api/redoc`

## 手动启动

后端：

```bash
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

前端默认通过 `frontend/vite.config.ts` 将 `/api` 与 `/outputs` 代理到 `http://localhost:8000`。需要跨域或部署时可设置 `VITE_API_BASE_URL` 与 `VITE_API_TIMEOUT`。

## 本地基础设施

PostgreSQL/Redis 是当前 Retail V2 state、队列和 SSE 事件的默认开发期基础设施。大文件、模型 artifact、CSV、报告和图表仍保留在文件系统，通过 API ref 访问。

```bash
make infra-up
make db-migrate
```

常用命令：

- `make infra-down`：停止 PostgreSQL/Redis。
- `make infra-reset`：删除 named volumes 后重启。
- `make infra-logs`：查看 PostgreSQL/Redis 日志。
- `make db-downgrade`：Alembic downgrade 到 base。
- `make db-revision DB_REVISION_MESSAGE="describe change"`：生成迁移草稿。

## 使用入口

### Retail Analysis V2

1. 打开 `http://localhost:5173/projects`。
2. 创建项目。
3. 上传 Retail V2 CSV。
4. 启动分析；详情页会通过 SSE 接收状态变化，并以 REST snapshot 兜底。
5. 在项目详情页查看 summary、quality、stage status、artifact refs、推荐与营销洞察。

Retail V2 CSV 字段以 `backend/providers/dtos.py` 的 `RETAIL_RAW_SALES_COLUMNS` 为准。冒烟数据位于：

```text
tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
```

### Data Processing

1. 打开 `http://localhost:5173/data-processing`。
2. 填写 `project_id` 与 Job 名称。
3. 上传 `.csv`、`.xls` 或 `.xlsx`。
4. 执行标准化，查看 quality/capability/sidecars。
5. 若状态为 `needs_review`，先复核 mapping 与 quality；当前后端没有 approval endpoint，前端会阻止继续 run。
6. 标准化通过后运行分析；页面会通过 SSE 接收状态变化，并以 REST snapshot 兜底。

## 目录结构

```text
backend/      FastAPI 后端、业务编排、能力原子、Provider 边界、Infrastructure adapters
frontend/     Vue 3 前端、typed API client、Retail/Data Processing 页面
docs/         当前架构、接口、运行、开发、接入和历史计划文档
analysis/     离线实验蓝本和 data-processing 源材料归档；runtime 不直接 import
data/         本地项目状态和 runtime 数据
outputs/      静态输出文件挂载目录
scripts/      一键启动脚本与 PostgreSQL 初始化脚本
tests/        API、业务流、能力、Provider、DB、架构规则测试
```

## 质量门

```bash
make lint
make format
make check
make hooks
```

当前 `make check` 覆盖 backend Ruff lint、backend Ruff format check、pytest、frontend `npm run build`。最近基线为 `217 passed, 5 skipped`，pytest 仍有 pandas/numpy/pydantic 运行时 warnings。

`make typecheck` 与 `make clean` 是占位目标，不能作为验证通过的证据。

## 主要文档

- [docs/README.md](docs/README.md)：文档地图。
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)：当前架构。
- [docs/backend-api.md](docs/backend-api.md)：后端 HTTP 接口。
- [docs/frontend-api-integration-plan.md](docs/frontend-api-integration-plan.md)：前端接入状态与后续计划。
- [docs/QUICKSTART.md](docs/QUICKSTART.md)：启动和验收。
- [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)：功能使用指南。
- [docs/commands.md](docs/commands.md)：Makefile 命令契约。
- [docs/env.md](docs/env.md)：环境变量约定。

## 可选 Streamlit 入口

`app.py` 是早期单机版入口，不是当前主应用路径。

```bash
uv run streamlit run app.py
```

## License

MIT License. See [LICENSE](LICENSE).
