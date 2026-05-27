# MarketMind 项目计划

## 当前基线

MarketMind 已从早期 Streamlit/单体实验形态迁移为 Vue 3 + FastAPI 前后端分离应用。

已完成：

- Retail Analysis V2 runtime：项目创建、CSV 上传、分析任务、阶段状态、产物引用、推荐、营销洞察。
- Data Processing runtime：通用 CSV/Excel 上传、regularization、quality/capability、`analysis2` 通用分析、outputs/sidecars。
- 前端接入：typed API client、Retail 页面迁移、Data Processing 页面、Health 状态、Customer Suggestions 后端收敛。
- 架构边界：`API Controller -> Business Flow/Pipeline -> Ability Atom -> Provider Interface -> Infrastructure Adapter`。
- PostgreSQL/Redis 基础设施：Retail V2 state 已切到 PostgreSQL；异步任务通过 Redis/RQ worker 执行；前端状态刷新通过 SSE + REST fallback；Docker Compose、SQLAlchemy、Alembic 就绪。
- 质量门：`make check` 覆盖 backend lint/format/test 和 frontend build；当前基线 `217 passed, 5 skipped`。

## 核心产品目标

1. 让零售数据通过 Retail V2 快速得到分群、关联、推荐、营销洞察和报告。
2. 让字段不固定的通用业务数据通过 Data Processing 自动标准化并运行可用分析。
3. 通过后端 LLM Provider 生成可解释、可落地的文本建议。
4. 保持 Provider Boundary，使存储、LLM、队列、分析实现可替换。

## 已完成阶段

- P2: PostgreSQL read/write switch — Retail V2 state 已切到 PostgreSQL，通过 `RetailAnalysisStateProvider` + `PostgresRetailAnalysisStateAdapter`。
- P3: Redis-backed queue — 异步任务通过 Redis/RQ worker 执行，状态更新通过 Redis pub/sub SSE + REST fallback。

## 下一阶段路线

| 阶段 | 目标 | 交付 |
| --- | --- | --- |
| P1 | 前端测试补强 | API client 单测、SSE composable、关键页面状态测试。 |
| P4 | 认证与安全 | 鉴权、API key 管理、LLM 密钥服务端托管、审计日志。 |
| P5 | 产物存储治理 | 大文件/图表/报告对象引用策略、清理策略、下载权限。 |
| P6 | 前端性能 | Vite manual chunks、Data Processing JSON viewer 虚拟化、图表 lazy loading。 |

## 红线

- 不恢复 `/api/projects`、`/api/recommend`、`/api/association` 兼容路由。
- 不让业务层直接依赖 SQLAlchemy、Redis client、SDK 或本地绝对路径。
- 不把 Redis 当业务真相源。
- 不把大 CSV、图表、报告、音频、模型文件直接塞进 PostgreSQL。
- 不从 `analysis/data-processing-pipeline/` 直接 import runtime 逻辑。

## 验收命令

```bash
make lint
make format
make check
make hooks
```

涉及 DB 迁移或 adapter 时补充：

```bash
make infra-up
make db-migrate
TEST_DATABASE_URL=postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind_test uv run python -m pytest tests/infrastructure/db tests/infrastructure/adapters/test_postgres_project_repository_adapter.py
```
