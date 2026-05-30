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

## 文档

| 想看什么 | 去哪儿 |
|----------|--------|
| 部署、环境变量、API 契约、运维操作 | [docs/README.md § Part 2 运维](docs/README.md#part-2--运维文档) |
| 架构设计、施工清单、开发规范 | [docs/README.md § Part 3 开发](docs/README.md#part-3--开发文档) |
| 项目架构、路线图、需求背景 | [docs/README.md § Part 1 介绍](docs/README.md#part-1--项目介绍) |
| Admin Console 使用与配置 | [docs/admin/admin-console-design.md](docs/admin/admin-console-design.md) |

质量门禁：`make check`（lint + format + pytest + frontend build），当前基线 `370 passed, 6 skipped`。

## 可选 Streamlit 入口

`app.py` 是早期单机版实验入口，非当前主应用路径：

```bash
uv run streamlit run app.py
```

## License

MIT License. See [LICENSE](LICENSE).
