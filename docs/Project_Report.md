# MarketMind 项目汇报

## 解决的问题

- 零售运营依赖经验判断促销组合、补货优先级和客户触达策略，缺少统一的分析链路。
- 固定字段数据和通用字段数据需要不同处理方式，手工清洗与多工具串联成本高。
- 分析结果如果只停留在表格和图表，很难直接转化为营销动作。

## 系统能力

| 能力 | 说明 |
| --- | --- |
| Retail Analysis V2 | 面向固定中文列零售 CSV，运行清洗、特征工程、客户分群、关联/HUIM、推荐、营销洞察和报告。 |
| Data Processing | 面向通用 CSV/Excel，先做 regularization，再运行 `analysis2` 通用分析，输出 quality、capability、outputs 和 sidecars。 |
| AI 文本建议 | 通过后端 LLM Provider 生成客户营销建议和商品洞察，前端不直接请求第三方 LLM。 |
| 前端工作台 | Vue 3 页面覆盖 Retail 项目管理、Data Processing Job、产物查看、服务状态与设置。 |
| 基础设施迁移 | PostgreSQL/Redis/Docker Compose/Alembic 已作为迁移基础，业务 runtime 仍以 filesystem/JSON 为真相源。 |

## 架构

```text
Vue 3 frontend
  -> typed API client
  -> FastAPI Controller
  -> Business Flow / Pipeline
  -> Ability Atom
  -> Provider Interface
  -> Infrastructure Adapter
```

核心价值：API 层薄、业务编排可测试、算法能力可替换、存储和 LLM 通过 Provider Boundary 隔离。

## 主要接口

Base URL：`http://localhost:8000`

| 分类 | 接口 |
| --- | --- |
| Health | `GET /api/health/` |
| Retail projects | `POST/GET /api/analysis/projects`, `GET/DELETE /api/analysis/projects/{project_id}` |
| Retail lifecycle | `POST /api/analysis/projects/{project_id}/dataset`, `POST /api/analysis/projects/{project_id}/run` |
| Retail results | `GET /api/analysis/projects/{project_id}/artifacts`, `GET /api/analysis/projects/{project_id}/recommendations`, `GET /api/analysis/projects/{project_id}/marketer-insights` |
| Data Processing | `POST /api/analysis/jobs`, `POST /api/analysis/jobs/{job_id}/raw-dataset`, `POST /api/analysis/jobs/{job_id}/regularize`, `POST /api/analysis/jobs/{job_id}/run`, `GET /api/analysis/jobs/{job_id}` |
| Data Processing results | `GET /api/analysis/jobs/{job_id}/outputs`, `GET /api/analysis/jobs/{job_id}/datasets/{dataset_id}`, `GET /api/analysis/jobs/{job_id}/sidecars/{sidecar_id}` |
| Text suggestions | `POST /api/analysis/customer-suggestions` |

退役接口 `/api/projects`、`/api/recommend`、`/api/association` 不再作为兼容入口。

## 当前验证

- `make check` 通过：backend lint、backend format check、pytest、frontend build。
- pytest 基线：`188 passed, 5 skipped`。
- `make hooks` 通过。
- 前端源码没有旧 API 路由、旧 `@/utils/http` 或浏览器直连 LLM endpoint 残留。

## 后续重点

1. PostgreSQL read/write switch 和历史数据迁移。
2. Redis-backed queue 与独立 worker。
3. 服务端 LLM 密钥管理、鉴权与审计。
4. 前端 API client 单测、polling composable 和大 JSON/图表性能优化。
