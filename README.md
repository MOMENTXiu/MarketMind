# MarketMind

MarketMind 是一个面向零售与通用交易数据的 AI 营销分析系统。上传销售明细后，系统自动完成数据标准化、质量检查、客户分群、关联规则、个性化推荐和促销效果分析，输出业务可读的图表与行动建议。

主线为 **Vue 3 + FastAPI** 前后端分离应用，后端通过五层架构编排分析流程，前端通过 typed API client 接入 HTTP 契约。

## 项目入口

打开 `http://localhost:5173` 后：

- **首页**：功能概览入口，可直接进入项目介绍或开始分析。
- **项目介绍** `/project-intro`：PPT 式全屏滚动页面，展示项目 What / Why / How、系统架构、分析能力和实现效果。
- **项目空间** `/projects`：创建分析项目、上传零售 CSV、运行诊断、查看结果。
- **数据处理** `/data-processing`：通用 CSV/Excel 上传，执行正则化与通用分析链路。

## 当前能力

- **Retail Analysis V2**：创建项目 → 上传固定中文列零售 CSV → 运行清洗、特征工程、分群、关联、推荐、营销洞察和报告链路。
- **Data Processing**：创建 Job → 上传通用 CSV/Excel → 执行 `regularization → analysis2` 通用分析链路，读取 quality、capability、outputs 和 sidecars。
- **AI 文本建议**：前端通过 `POST /api/analysis/customer-suggestions` 生成客户营销建议与商品洞察文本。
- **项目介绍页**：7 张全屏 scroll-snap slide，含动画流程图、双列系统架构图、分析能力地图和实现状态。
- **Admin Console** `/admin`：运行状态看板、LLM 多模型管理、Bark 告警配置、系统日志、用户管理。仅 admin 角色可访问。Retail V2 runtime 已通过 Provider Boundary 使用 PostgreSQL state、Redis/RQ queue 与 Redis pub/sub SSE。Redis 只承载队列和事件，不作为业务真相源。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI, Uvicorn, Pydantic 2, pandas, scikit-learn, mlxtend, statsmodels, SQLAlchemy, Alembic |
| 前端 | Vue 3, Vite, TypeScript, Vue Router, Pinia, Element Plus, Tailwind CSS, ECharts, lucide-vue-next |
| 基础设施 | PostgreSQL, Redis, MinIO, Docker Compose |
| 工具 | uv, npm, Ruff, pytest, pre-commit |

## 环境要求

- Python `>=3.13,<3.14`
- `uv`
- Node.js 18+ 与 npm
- 可选：OrbStack 或 Docker Desktop，用于 PostgreSQL / Redis / MinIO 本地服务。

## 快速启动

首次运行：

```bash
./scripts/deploy-project.sh && ./scripts/start-project.sh
```

已部署过的日常启动：

```bash
./scripts/start-project.sh
```

默认地址：

- 前端：`http://localhost:5173`
- Admin Console：`http://localhost:5173/admin`
- 后端 API：`http://localhost:8000/api`
- Swagger：`http://localhost:8000/api/docs`

Admin 用户设置：

```bash
./scripts/setup-admin.sh  # 交互式创建管理员账号
```

## 手动启动

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

前端默认通过 `frontend/vite.config.ts` 将 `/api` 与 `/outputs` 代理到 `http://localhost:8000`。需自定义 base URL 时可设置 `VITE_API_BASE_URL`。

## 本地基础设施

```bash
make infra-up
make db-migrate
```

常用 Makefile 命令：

- `make infra-down`：停止基础设施服务。
- `make infra-reset`：删除 named volumes 后重启。
- `make infra-logs`：查看服务日志。
- `make db-downgrade`：Alembic downgrade 到 base。
- `make db-revision DB_REVISION_MESSAGE="describe change"`：生成迁移草稿。

## 使用流程

### Retail Analysis V2

1. 打开 `/projects`，创建项目。
2. 上传 Retail V2 CSV（字段以 `backend/providers/dtos.py` 的 `RETAIL_RAW_SALES_COLUMNS` 为准）。
3. 启动分析；详情页通过 SSE 接收状态，REST snapshot 兜底。
4. 查看 summary、quality、stage status、artifact refs、推荐与营销洞察。

冒烟数据：`tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv`

### Data Processing

1. 打开 `/data-processing`，填写 `project_id` 与 Job 名称。
2. 上传 `.csv`、`.xls` 或 `.xlsx`。
3. 执行标准化，查看 quality / capability / sidecars。
4. 若状态为 `needs_review`，复核 mapping 与 quality 后继续。
5. 标准化通过后运行分析，页面通过 SSE 接收状态。

## 目录结构

```
backend/      FastAPI 后端、业务编排、能力原子、Provider 边界、Infrastructure adapters
frontend/     Vue 3 前端、typed API client、PPT 式项目介绍页、Retail/Data Processing 页面
docs/         架构文档、需求规格、API 参考、项目 intro 内容蓝本
analysis/     离线实验蓝本和源材料归档；runtime 不直接 import
data/         本地项目状态和 runtime 数据
outputs/      静态输出文件挂载目录
scripts/      一键部署与启动脚本
tests/        API、业务流、能力、Provider、DB、架构规则测试
```

## 质量门

```bash
make lint
make format
make check
make hooks
```

`make check` 覆盖 backend Ruff lint + format check + pytest + frontend `npm run build`。当前基线 `262 passed, 5 skipped`。

`make typecheck` 与 `make clean` 为占位目标，不能作为验证通过。

## 主要文档

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 当前架构与分层说明
- [docs/backend-api.md](docs/backend-api.md) — 后端 API 接口参考
- [docs/QUICKSTART.md](docs/QUICKSTART.md) — 快速启动与验收
- [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) — 功能使用指南
- [docs/env.md](docs/env.md) — 环境变量约定
- [docs/development.md](docs/development.md) — 开发环境与工具链
- [docs/intro/INTRO_PAGE_BRIEF.md](docs/intro/INTRO_PAGE_BRIEF.md) — Intro 页面内容蓝本
- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) — 项目路线图

## 可选 Streamlit 入口

`app.py` 是早期单机版实验入口，非当前主应用路径：

```bash
uv run streamlit run app.py
```

## License

MIT License. See [LICENSE](LICENSE).
