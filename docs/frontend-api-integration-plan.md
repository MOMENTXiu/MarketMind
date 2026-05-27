# 前端 API 接入状态与后续计划

前端已经完成 P0-P5 接入闭环：typed API client、Retail V2 页面迁移、Data Processing 页面、outputs/sidecars 展示、LLM 后端收敛、build/check/hooks 验证。

## 当前接入边界

```text
frontend/src/api/
  client.ts
  errors.ts
  types.ts
  health.ts
  retail.ts
  data-processing.ts
  suggestions.ts
  index.ts
```

页面不直接 import 旧 `@/utils/http`，不调用旧 `/api/projects`、`/api/recommend`、`/api/association`，不直接请求第三方 `/chat/completions` 或 `/models`。

## API 模块职责

| 文件 | 职责 |
| --- | --- |
| `client.ts` | 创建 axios 实例，读取 `VITE_API_BASE_URL`、`VITE_API_TIMEOUT`，处理 `{ success, data }` envelope。 |
| `errors.ts` | 归一化 Axios、FastAPI 422、`{ detail }`、未知错误。 |
| `types.ts` | 共享 API DTO、Retail/Data Processing 状态枚举、状态 helper。 |
| `retail.ts` | 封装 Retail V2 project/dataset/run/artifacts/recommendations/marketer-insights。 |
| `data-processing.ts` | 封装 job create/upload/regularize/run/status/outputs/datasets/sidecars。 |
| `suggestions.ts` | 封装 `POST /api/analysis/customer-suggestions` 直返响应。 |
| `health.ts` | 封装 `GET /api/health/`。 |

## 页面接入状态

| 页面 | 状态 |
| --- | --- |
| `ProjectList.vue` | 使用 Retail API list/delete；状态统一映射。 |
| `ProjectCreate.vue` | 使用 Retail API create/upload/run；移除后端不接收的高级参数提交承诺。 |
| `ProjectDetail.vue` | 使用 Retail API detail/run/artifacts/recommendations；展示 summary、quality、stages、artifact refs；run 后轮询。 |
| `ProductRecommend.vue` | 使用 recommendations 与 customer-suggestions；商品洞察不再直连第三方 LLM。 |
| `CustomerAnalysis.vue` | 使用 Retail detail/recommendations 与 customer-suggestions。 |
| `Settings.vue` | 保存本地 LLM config，并通过后端 suggestion endpoint 做连接测试。 |
| `ServiceStatus.vue` | 使用真实 `/api/health/` 并清理 interval。 |
| `DataProcessing.vue` | 支持 create/upload/regularize/run/status polling/outputs/sidecars/needs_review。 |

## Data Processing UX

前端入口：

```text
/data-processing
/data-processing/jobs/:jobId?project_id=...
```

用户流程：

1. 创建 Job：`POST /api/analysis/jobs`。
2. 上传 raw dataset：`POST /api/analysis/jobs/{job_id}/raw-dataset?project_id=...`。
3. 标准化：`POST /api/analysis/jobs/{job_id}/regularize?project_id=...`。
4. 展示 `quality`、`capability`、stages、skipped reasons。
5. 读取 sidecars：schema mapping、quality report、capability、manifest、preview rows。
6. `needs_review` 时禁用 run。
7. 运行分析并轮询到 `completed` 或 `failed`。
8. 读取 outputs。

## 验收记录

最近一次接入验收执行：

```bash
cd frontend && npm run build
make lint
make format
make lint
make hooks
make check
```

结果：

- Frontend build passed。
- `make hooks` passed。
- `make check` passed：`217 passed, 5 skipped`。
- grep 确认无旧 API/旧 HTTP/直连 LLM 残留。

## 剩余建议

| 优先级 | 工作 |
| --- | --- |
| P1 | 为 `frontend/src/api/` 增加单元测试：envelope unwrap、customer-suggestions 直返、422 错误归一化。 |
| P1 | 拆出通用 polling composable，减少 Retail 和 Data Processing 页面重复。 |
| P2 | 为 Data Processing 增加更细的 sidecar 渲染组件，避免大型 JSON 影响页面可读性。 |
| P2 | 后端提供 LLM config validation endpoint 后，Settings 改用专门测试接口。 |
| P3 | 处理 Vite 大 chunk 警告，按 ECharts/Element Plus/页面分包。 |
