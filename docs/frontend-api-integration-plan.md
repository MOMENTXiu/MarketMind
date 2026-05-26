# 前端接入方案

本文面向后续负责前端接入与联调的开发者，基于当前 `frontend/src` 代码和 [docs/backend-api.md](backend-api.md) 盘点现状、识别差距，并给出分阶段接入方案。

## 当前前端状态

前端为 Vue 3 + Vite + TypeScript + Element Plus。当前路由集中在 Retail V2 项目流：

| 前端路由 | 页面 | 当前定位 |
| --- | --- | --- |
| `/` | `Home.vue` | 首页入口 |
| `/projects` | `ProjectList.vue` | Retail V2 项目列表 |
| `/projects/new` | `ProjectCreate.vue` | Retail V2 创建、上传、启动分析 |
| `/projects/:id` | `ProjectDetail.vue` | Retail V2 项目详情 |
| `/me/projects` | `MyProjects.vue` | 跳转到 `/projects` |
| `/projects/:id/recommend` | `ProductRecommend.vue` | 基于 recommendations 的商品关联查询 |
| `/projects/:id/customer/:customerId` | `CustomerAnalysis.vue` | 客户详情和 AI 建议 |
| `/settings` | `Settings.vue` | 浏览器本地 LLM 配置 |

HTTP 基础设施较薄：`frontend/src/utils/http.ts` 只创建了一个无 `baseURL`、无拦截器、无统一解包逻辑的 axios 实例。开发环境依赖 `frontend/vite.config.ts` 中 `/api` 和 `/outputs` proxy 到 `http://localhost:8000`。

## 当前接口调用盘点

| 文件 | 当前调用 | 对应后端文档 |
| --- | --- | --- |
| `ProjectList.vue` | `GET /api/analysis/projects` | Retail V2 列表 |
| `ProjectList.vue` | `DELETE /api/analysis/projects/{id}` | Retail V2 删除 |
| `ProjectCreate.vue` | `POST /api/analysis/projects` | Retail V2 创建 |
| `ProjectCreate.vue` | `POST /api/analysis/projects/{project_id}/dataset` | Retail V2 上传 CSV |
| `ProjectCreate.vue` | `POST /api/analysis/projects/{project_id}/run` | Retail V2 启动分析 |
| `ProjectDetail.vue` | `GET /api/analysis/projects/{id}` | Retail V2 项目详情 |
| `ProjectDetail.vue` | `POST /api/analysis/projects/{id}/run` | Retail V2 重新分析 |
| `ProjectDetail.vue` | `GET /api/analysis/projects/{id}/recommendations?top_k=100` | Retail V2 推荐结果 |
| `ProductRecommend.vue` | `GET /api/analysis/projects/{id}/recommendations?top_k=100` | Retail V2 推荐结果 |
| `ProductRecommend.vue` | `GET /api/analysis/projects/{id}/recommendations?customer_id=...&top_k=1` | Retail V2 客户推荐 |
| `CustomerAnalysis.vue` | `GET /api/analysis/projects/{project_id}` | Retail V2 项目详情 |
| `CustomerAnalysis.vue` | `GET /api/analysis/projects/{project_id}/recommendations?customer_id=...&top_k=10` | Retail V2 客户推荐 |
| `CustomerAnalysis.vue` | `POST /api/analysis/customer-suggestions` | Customer Suggestions |
| `Settings.vue` | `GET {llm_base_url}/models` | 不走 MarketMind 后端 |
| `ProductRecommend.vue` | `POST {llm_base_url}/chat/completions` | 不走 MarketMind 后端 |
| `ServiceStatus.vue` | mock 数据 | 未接入 `GET /api/health/` |

当前完全未接入 Data Processing 的 `/api/analysis/jobs...` 系列接口。

## 与后端接口文档的差距

### 通用 API 层

- 成功响应包络 `{ success, data }` 由页面各自读取，没有统一类型、统一 unwrap、统一错误提示。
- `customer-suggestions` 是直返 `{ success, text, metadata }` 的例外，目前只在 `CustomerAnalysis.vue` 局部处理。
- `http.ts` 没有读取 `VITE_API_BASE_URL` 和 `VITE_API_TIMEOUT`，与 README 中的环境变量约定不一致。
- 错误处理分散在页面内，多数只读取 `error.response?.data?.detail`，没有覆盖 FastAPI 422 的数组 detail。
- 没有集中声明 `ProjectStatus`、`JobStatus`、`StageStatus`、ref、quality、capability 等类型。

### Retail V2

- 现有页面只接入项目、上传、run、详情、推荐、删除；未接入 `artifacts`、`datasets`、`models`、独立 `marketer-insights`。
- `ProjectCreate.vue` 有分析参数表单，但后端 `POST /api/analysis/projects` 当前只接收 `name` 和 `description`，这些参数没有提交目标。
- `ProjectDetail.vue` 仍读取 `project.results.*` 的旧形态；后端当前公开的是 `summary`、`artifact_refs`、`recommendations`、`marketer_insights`、`stage_statuses` 等字段，详情页存在空渲染风险。
- `run` 后只跳转或延迟单次刷新，没有按文档轮询到 `completed` 或 `failed`。
- 状态处理混有英文枚举和中文旧状态，`reanalyze` loading 判断仍使用 `project?.status === '处理中'`。

### Data Processing

- 没有 job 创建、raw dataset 上传、regularize、needs_review、run、轮询、outputs、datasets、sidecars 页面或 API 封装。
- 没有展示 `quality.analysis_ready_score`、`capability`、`skipped_reasons`、stage `skipped` 原因。
- 没有处理 `needs_review`：前端需要引导用户查看 `sidecar:schema_mapping_detail`、`sidecar:quality_report`、`sidecar:capability`。
- 没有将 `order_4.csv` 这类通用数据文件从 Retail V2 固定中文列上传入口中分流。

### LLM 与服务状态

- `ProductRecommend.vue` 直接从浏览器调用第三方 LLM，API Key 存在 `localStorage` 并暴露给浏览器运行时。
- `Settings.vue` 的连接测试也直接调用第三方模型列表接口。
- `ServiceStatus.vue` 使用 mock 数据，注释中的 `/api/status` 与真实健康检查 `/api/health/` 不一致。

## 接入目标

1. 前端只通过统一 API client 访问 MarketMind 后端；外部 LLM 直连保留为明确的临时兼容路径，不再作为新功能默认路径。
2. Retail V2 现有体验不回退，页面字段与 `docs/backend-api.md` 中的公开 response shape 对齐。
3. Data Processing 增加独立接入路径，支持 CSV/Excel 上传、标准化、复核提示、通用分析和输出读取。
4. 任务状态使用轮询或可取消的 polling composable，准确展示 `queued`、`processing`、`completed`、`failed`、`needs_review`、`skipped`。
5. 所有页面只依赖 API 返回的 ref / url，不拼接本地文件路径。

## 分阶段方案

### P0：建立 API Client 与类型边界

新增目录建议：

```text
frontend/src/api/
  client.ts
  errors.ts
  types.ts
  health.ts
  retail.ts
  dataProcessing.ts
  suggestions.ts
```

核心职责：

- `client.ts` 创建 axios 实例，读取 `import.meta.env.VITE_API_BASE_URL`，默认回退为空字符串以继续支持 Vite proxy。
- `client.ts` 设置 timeout，读取 `VITE_API_TIMEOUT`，默认 30000ms。
- `errors.ts` 提供 `normalizeApiError(error)`，统一解析 400/404/500 `{detail}` 和 422 `{detail: [...]}`。
- `types.ts` 定义 `ApiEnvelope<T>`、`ApiRef`、`RetailProject`、`RetailStage`、`DataProcessingJob`、`DataProcessingStage`、`RegularizationQuality`、`RegularizationCapability`。
- `retail.ts` 封装 Retail V2 所有 endpoint，不让页面直接写 URL。
- `dataProcessing.ts` 封装 `/api/analysis/jobs...` 全链路。
- `suggestions.ts` 单独处理 `customer-suggestions` 的直返响应，不套 `ApiEnvelope<T>`。

完成标准：所有页面不直接 import `@/utils/http`；`@/utils/http` 可删除或只保留为 API client 内部实现。

### P1：稳定 Retail V2 现有页面

改造范围：`ProjectList.vue`、`ProjectCreate.vue`、`ProjectDetail.vue`、`ProductRecommend.vue`、`CustomerAnalysis.vue`。

动作：

- 页面调用切换到 `retailApi` 和 `suggestionsApi`。
- `ProjectCreate.vue` 移除或降级未被后端接收的参数提交承诺；保留 UI 时必须明确为“本阶段不提交”。
- `ProjectDetail.vue` 从当前后端字段读取：`summary`、`quality_summary`、`artifact_refs`、`recommendations`、`marketer_insights`、`stage_statuses`。
- `ProjectDetail.vue` 对缺失 `results.*` 的情况展示空态，而不是默默渲染空图。
- 新增 `usePolling` 或 `useAnalysisPolling` composable：run 后每 2-3 秒查询详情，`completed`、`failed` 或组件卸载时停止。
- 状态统一使用英文枚举映射中文标签，不再判断中文状态值。
- `ServiceStatus.vue` 接入 `GET /api/health/`，并在组件卸载时清理 interval。

完成标准：Retail V2 创建、上传、启动、轮询、详情、推荐、客户建议全部通过 typed API 层完成；旧 `/api/projects`、`/api/recommend`、`/api/association` 不出现在前端源码。

### P2：新增 Data Processing 接入路径

建议路由：

```text
/data-processing
/data-processing/new
/data-processing/jobs/:jobId
```

也可在 `/projects/new` 中使用模式切换，但必须明确区分：

- Retail V2：固定中文列 CSV，走 `/api/analysis/projects`。
- Data Processing：任意 CSV/Excel，走 `/api/analysis/jobs`。

页面流程：

1. 创建 job：填写 `project_id` 和 `name`，调用 `POST /api/analysis/jobs`。
2. 上传 raw dataset：调用 `POST /api/analysis/jobs/{job_id}/raw-dataset?project_id=...`。
3. 标准化：调用 `POST /api/analysis/jobs/{job_id}/regularize?project_id=...`。
4. 标准化结果页展示 `quality`、`capability`、stage、output refs。
5. 若 `status === "needs_review"`，展示 mapping detail、quality report、capability sidecar，并禁用 run。
6. 若 regularization 完成，调用 `POST /api/analysis/jobs/{job_id}/run?project_id=...`。
7. 轮询 `GET /api/analysis/jobs/{job_id}?project_id=...` 到终态。
8. 完成后进入 outputs/sidecars 结果页。

完成标准：`order_4.csv` 可通过 Data Processing 前端流程上传、标准化、run；当 association 因无共购结构 skipped 时，页面显示 skipped 原因，job 仍显示 completed。

### P3：结果与产物读取

Retail V2：

- 在项目详情页增加 artifacts 面板，调用 `GET /api/analysis/projects/{project_id}/artifacts`。
- 对 dataset/artifact/model ref 只展示 `id`、`type`、`name`、`metadata` 和 API 返回的 `url`。
- 不读取或展示本地 path。

Data Processing：

- 增加 outputs 列表，调用 `GET /api/analysis/jobs/{job_id}/outputs?project_id=...`。
- 对 `raw-upload`、`normalized-dataset` 提供 metadata 展示和下载/打开入口。
- 对 sidecar 提供 JSON viewer：`schema_mapping_detail`、`quality_report`、`capability`、`manifest`、`preview_rows`。
- 对 stage artifact refs 使用统一 ref card 展示。

完成标准：前端可以从 API 返回的 ref/url 追踪所有可公开产物，不需要知道后端 filesystem 目录。

### P4：LLM 接入收敛

短期：

- `CustomerAnalysis.vue` 继续使用 `POST /api/analysis/customer-suggestions`。
- `ProductRecommend.vue` 的商品洞察改为调用后端建议接口，或暂时降级为本地规则文案，不再默认直接请求外部 LLM。
- `Settings.vue` 明确标记本地 LLM 配置只用于传给后端建议接口；避免在页面自动触发第三方 LLM 请求。

中期：

- 后端新增统一 LLM provider 测试接口后，`Settings.vue` 再接入后端测试 endpoint。
- 前端不在源码中新增任何第三方 LLM endpoint 拼接逻辑。

完成标准：业务页面不会把 API Key 直接发送给非 MarketMind 后端；需要外部模型时通过后端 Provider 边界处理。

### P5：测试与验收

最小验证：

- `cd frontend && npm run build`
- `make check`

建议补充测试能力后覆盖：

- API client：成功包络解包、`customer-suggestions` 例外、400/404/422/500 错误归一化。
- Retail V2：创建项目、上传、run 后轮询、失败态、空推荐态。
- Data Processing：upload -> regularize -> needs_review、upload -> regularize -> run -> completed、stage skipped 展示、outputs/sidecars 读取。
- ServiceStatus：健康检查成功、失败和 interval cleanup。
- LLM：页面不直接调用外部 LLM，建议接口 fallback 可展示。

## 推荐施工顺序

1. 先做 P0 API client/types，不动页面 UI 结构。
2. 再做 P1 Retail V2 页面迁移，保证现有路径可用。
3. 然后做 P2 Data Processing 新入口，用 `order_4.csv` 做端到端验收数据。
4. 接着做 P3 outputs/sidecars 结果读取。
5. 最后收敛 P4 LLM 直连和 P5 测试补齐。

## 验收清单

- 前端源码中只通过 API 模块调用 MarketMind 后端业务接口。
- `GET /api/health/` 驱动服务状态组件。
- Retail V2 现有用户路径不回退。
- Data Processing 能上传 `order_4.csv`，标准化质量显示为优秀，run 后 job completed，association skipped 原因可见。
- 页面能展示 `needs_review` 并阻止用户继续 run。
- 页面能读取 outputs、datasets、sidecars。
- 不再新增旧路由 `/api/projects`、`/api/recommend`、`/api/association`。
- `npm run build` 和 `make check` 通过。