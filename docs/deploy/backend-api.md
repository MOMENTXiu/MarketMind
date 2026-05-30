# 后端接口接入文档

本文面向前端、脚本、自动化测试和第三方调用方，描述当前 FastAPI 后端已经公开的 HTTP 接口。后端入口为 `backend.main:app`，本地默认服务地址为 `http://localhost:8000`。

## 基础约定

| 项 | 说明 |
| --- | --- |
| API base URL | `http://localhost:8000` |
| 业务接口前缀 | `/api/analysis` |
| Swagger | `/api/docs` |
| ReDoc | `/api/redoc` |
| OpenAPI JSON | `/openapi.json` |
| 健康检查 | `GET /api/health/` |

除根路径、健康检查、文档页、静态资源和 `customer-suggestions` 外，`/api/analysis` 下的业务接口成功响应统一包一层：

```json
{
  "success": true,
  "data": {}
}
```

`POST /api/analysis/customer-suggestions` 是例外，成功时直接返回：

```json
{
  "success": true,
  "text": "...",
  "metadata": {}
}
```

内部业务错误统一映射为 FastAPI `HTTPException`：

| 错误来源 | HTTP 状态码 | 响应形态 |
| --- | ---: | --- |
| 请求参数、JSON body、multipart 表单校验失败 | 422 | FastAPI 默认 `{ "detail": [...] }` |
| 业务校验失败 | 400 | `{ "detail": "..." }` |
| 资源不存在 | 404 | `{ "detail": "..." }` |
| Provider、Infrastructure、Pipeline、BusinessFlow 执行失败 | 500 | `{ "detail": "..." }` |

## 应用级接口

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/` | 根路径，返回服务版本和文档入口 |
| `GET` | `/api/health/` | 健康检查 |
| `GET` | `/api/docs` | Swagger UI |
| `GET` | `/api/redoc` | ReDoc UI |
| `GET` | `/openapi.json` | OpenAPI schema |
| `GET` | `/outputs/{path}` | 静态输出文件挂载，不在 OpenAPI paths 中列出 |
| `GET` | `/api/samples` | 列出样本文件 catalog |
| `GET` | `/api/samples/{sample_id}` | 查询单个样本文件元数据 |
| `GET` | `/api/samples/{sample_id}/download` | 下载样本文件字节流 |

## Customer Suggestions

### `POST /api/analysis/customer-suggestions`

生成客户营销建议文本。该接口不返回 TTS 或音频地址。

请求体：

```json
{
  "data": {},
  "llm_config": {
    "provider": "openai-compatible",
    "baseUrl": "https://example.com/v1",
    "apiKey": "optional",
    "modelName": "optional"
  }
}
```

响应体：

```json
{
  "success": true,
  "text": "...",
  "metadata": {
    "provider": "...",
    "model": "...",
    "scene_type": "customer"
  }
}
```

LLM 调用不可用时，业务层会返回 deterministic fallback 文本。

## Retail V2 接口

Retail V2 是项目级零售分析链路，适合固定中文字段的零售销售 CSV。它与 Data Processing 链路并存。

### 接口清单

| Method | Path | 用途 | 参数 | Body |
| --- | --- | --- | --- | --- |
| `POST` | `/api/analysis/projects` | 创建项目 | 无 | JSON：`name` 必填，`description` 可选 |
| `GET` | `/api/analysis/projects` | 列出项目 | 无 | 无 |
| `GET` | `/api/analysis/projects/{project_id}` | 查询项目详情、状态和结果摘要 | `project_id` path | 无 |
| `DELETE` | `/api/analysis/projects/{project_id}` | 删除项目 | `project_id` path | 无 |
| `POST` | `/api/analysis/projects/{project_id}/dataset` | 上传 Retail V2 CSV 并完成数据准备 | `project_id` path | `multipart/form-data`，字段名 `file` |
| `POST` | `/api/analysis/projects/{project_id}/run` | 启动或复用分析任务 | `project_id` path | 无 |
| `GET` | `/api/analysis/projects/{project_id}/artifacts` | 列出项目产物引用 | `project_id` path | 无 |
| `GET` | `/api/analysis/projects/{project_id}/datasets/{dataset_id}` | 获取 dataset ref | `project_id`、`dataset_id` path | 无 |
| `GET` | `/api/analysis/projects/{project_id}/artifacts/{artifact_id}` | 获取 artifact ref，`artifact_id` 可包含 `:` | `project_id`、`artifact_id` path | 无 |
| `GET` | `/api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload` | 读取 table/json/markdown artifact payload，`artifact_id` 可包含 `:` | `project_id`、`artifact_id` path | 无 |
| `GET` | `/api/analysis/projects/{project_id}/models/{model_type}/{version}` | 获取 model ref | `project_id`、`model_type`、`version` path | 无 |
| `GET` | `/api/analysis/projects/{project_id}/recommendations` | 查询推荐结果 | `project_id` path；`customer_id` query 可选；`top_k` query 默认 10，范围 1-100 | 无 |
| `GET` | `/api/analysis/projects/{project_id}/marketer-insights` | 查询营销洞察 | `project_id` path | 无 |

### 创建项目

```bash
curl -X POST http://localhost:8000/api/analysis/projects \
  -H 'Content-Type: application/json' \
  -d '{"name":"门店销售分析","description":"2025 Q1"}'
```

响应中的 `data.id` 是后续 `project_id`。

### 上传数据集

```bash
curl -X POST http://localhost:8000/api/analysis/projects/{project_id}/dataset \
  -F 'file=@tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv'
```

Retail V2 当前只接受非空 `.csv` 文件，且必须包含这些中文列：

```text
顾客编号,大类编码,大类名称,中类编码,中类名称,小类编码,小类名称,销售日期,销售月份,商品编码,规格型号,商品类型,单位,销售数量,销售金额,商品单价,是否促销
```

### 启动分析并订阅状态

```bash
curl -X POST http://localhost:8000/api/analysis/projects/{project_id}/run
curl http://localhost:8000/api/analysis/projects/{project_id}
curl -N http://localhost:8000/api/analysis/projects/{project_id}/events
```

`run` 成功时返回 HTTP 202。Retail V2 通过 Redis/RQ worker 执行，调用方应先读取项目详情作为 REST snapshot，再订阅 SSE；重连或丢事件时重新读取项目详情兜底，直到 `status` 变为 `completed` 或 `failed`。

项目详情 `data` 主要字段：

```json
{
  "id": "...",
  "name": "...",
  "description": "...",
  "status": "queued|processing|completed|failed",
  "dataset_ref": null,
  "dataset_filename": "...",
  "quality_summary": {},
  "artifact_refs": [],
  "recommendations": [],
  "marketer_insights": {},
  "stage_statuses": [],
  "summary": {},
  "job_id": "...",
  "trace_id": "...",
  "error": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Retail V2 阶段名：

```text
dataset_preparation, feature_engineering, segmentation, association, recommendation, marketer_insights, report
```

阶段状态：

```text
queued, processing, completed, failed, skipped
```

### 读取结果

推荐结果：

```bash
curl 'http://localhost:8000/api/analysis/projects/{project_id}/recommendations?top_k=10'
curl 'http://localhost:8000/api/analysis/projects/{project_id}/recommendations?customer_id=U001&top_k=5'
```

营销洞察：

```bash
curl http://localhost:8000/api/analysis/projects/{project_id}/marketer-insights
```

产物引用：

```bash
curl http://localhost:8000/api/analysis/projects/{project_id}/artifacts
curl http://localhost:8000/api/analysis/projects/{project_id}/artifacts/{artifact_id}
curl http://localhost:8000/api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload
curl http://localhost:8000/api/analysis/projects/{project_id}/datasets/{dataset_id}
curl http://localhost:8000/api/analysis/projects/{project_id}/models/{model_type}/{version}
```

Retail V2 public ref 只公开 `id`、`type`、`name`、`url`、`metadata`，不会暴露本地绝对路径。

Artifact payload 读取只支持 `table`、`json` 和 `markdown`：

```json
{
  "success": true,
  "data": {
    "project_id": "...",
    "artifact": {},
    "payload_type": "table",
    "rows": [],
    "payload": null,
    "content": null
  }
}
```

`table` 使用 `rows`，`json` 使用 `payload`，`markdown` 使用 `content`。`figure` payload 当前不公开，调用会返回 400。

## Data Processing 接口

Data Processing 是通用链路，流程为：

```text
raw dataset upload -> regularization -> analysis2 universal analysis -> output refs
```

它更适合任意业务 CSV/Excel。以 `order_4.csv` 为例，后端可识别 GBK CSV，完成标准化和通用分析；当数据没有共购结构时，关联规则阶段会 `skipped`，其他可运行阶段仍可完成。

### 接口清单

| Method | Path | 用途 | 参数 | Body |
| --- | --- | --- | --- | --- |
| `POST` | `/api/analysis/jobs` | 创建 job | 无 | JSON：`project_id` 必填，`name` 必填 |
| `POST` | `/api/analysis/jobs/{job_id}/raw-dataset` | 上传原始数据 | `job_id` path；`project_id` query 必填 | `multipart/form-data`，字段名 `file` |
| `POST` | `/api/analysis/jobs/{job_id}/regularize` | 执行标准化 | `job_id` path；`project_id` query 必填 | 无 |
| `POST` | `/api/analysis/jobs/{job_id}/run` | 启动通用分析 | `job_id` path；`project_id` query 必填 | 无 |
| `GET` | `/api/analysis/jobs/{job_id}` | 查询 job 详情和状态 | `job_id` path；`project_id` query 必填 | 无 |
| `GET` | `/api/analysis/jobs/{job_id}/outputs` | 列出 output refs | `job_id` path；`project_id` query 必填 | 无 |
| `GET` | `/api/analysis/jobs/{job_id}/datasets/{dataset_id}` | 获取 dataset ref | `job_id`、`dataset_id` path；`project_id` query 必填 | 无 |
| `GET` | `/api/analysis/jobs/{job_id}/sidecars/{sidecar_id}` | 读取 sidecar JSON payload，`sidecar_id` 可包含 `:` | `job_id`、`sidecar_id` path；`project_id` query 必填 | 无 |

### 创建 job

```bash
curl -X POST http://localhost:8000/api/analysis/jobs \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"demo-project","name":"order_4 E2E"}'
```

响应中的 `data.job_id` 是后续 `job_id`。

### 上传原始数据

```bash
curl -X POST 'http://localhost:8000/api/analysis/jobs/{job_id}/raw-dataset?project_id=demo-project' \
  -F 'file=@order_4.csv'
```

上传要求：

- 文件名非空。
- 文件内容非空。
- 扩展名为 `.csv`、`.xlsx` 或 `.xls`。
- CSV 会依次尝试 `utf-8-sig`、`utf-8`、`gbk`、`gb18030`、`big5`、`latin1` 等编码。

### 标准化

```bash
curl -X POST 'http://localhost:8000/api/analysis/jobs/{job_id}/regularize?project_id=demo-project'
```

标准化成功后，job view 中会出现：

- `quality`：数据质量报告，例如行数、字段覆盖、缺失率、`analysis_ready_score`、`grade`。
- `capability`：可运行能力开关，例如 `can_run_sales_stats`、`can_run_association`、`can_run_recommendation`。
- `output_refs`：包含 raw upload、normalized dataset 和 sidecar refs。

常见 ref id：

```text
raw-upload
normalized-dataset
sidecar:schema_mapping
sidecar:schema_mapping_detail
sidecar:field_profile
sidecar:quality_report
sidecar:capability
sidecar:manifest
sidecar:preview_rows
```

如果核心标准字段需要人工复核，job 会进入 `needs_review`，此时 `run` 会返回 400。可先读取 `sidecar:schema_mapping_detail`、`sidecar:quality_report`、`sidecar:capability` 和 `sidecar:manifest` 判断问题。目前未提供公开 approval/resolution endpoint。

### 启动通用分析并订阅状态

```bash
curl -X POST 'http://localhost:8000/api/analysis/jobs/{job_id}/run?project_id=demo-project'
curl 'http://localhost:8000/api/analysis/jobs/{job_id}?project_id=demo-project'
curl -N 'http://localhost:8000/api/analysis/jobs/{job_id}/events?project_id=demo-project'
```

`run` 成功时返回 HTTP 202。调用方应先读取 job 详情作为 REST snapshot，再订阅 SSE；重连或丢事件时重新读取 job 详情兜底，直到 `status` 变为 `completed` 或 `failed`。

job view 主要字段：

```json
{
  "job_id": "...",
  "project_id": "...",
  "name": "...",
  "status": "queued|processing|completed|failed|needs_review",
  "stages": [],
  "quality": null,
  "capability": null,
  "output_refs": [],
  "skipped_reasons": {},
  "error": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Data Processing 阶段名：

```text
dataset_regularization, overview, profile_segmentation, association, recommendation, promotion, summary
```

阶段状态：

```text
queued, processing, completed, skipped, failed, needs_review
```

阶段可因 capability 或数据结构不足跳过。例如 `order_4.csv` 的单品订单没有共购结构，`association` 会 `skipped`，但 job 仍可 `completed`。

### 读取结果和 sidecar

```bash
curl 'http://localhost:8000/api/analysis/jobs/{job_id}/outputs?project_id=demo-project'
curl 'http://localhost:8000/api/analysis/jobs/{job_id}/datasets/raw-upload?project_id=demo-project'
curl 'http://localhost:8000/api/analysis/jobs/{job_id}/datasets/normalized-dataset?project_id=demo-project'
curl 'http://localhost:8000/api/analysis/jobs/{job_id}/sidecars/sidecar:quality_report?project_id=demo-project'
curl 'http://localhost:8000/api/analysis/jobs/{job_id}/sidecars/sidecar:capability?project_id=demo-project'
```

Data Processing 项目 completed 后，前端通过 Retail V2 同款的 artifact payload 接口读取 universal analysis JSON 产物（例如 `json:universal_overview.json`）：

```bash
curl 'http://localhost:8000/api/analysis/projects/{project_id}/artifacts/json:universal_overview.json/payload'
```

可用的 universal analysis artifact id 示例：

```text
json:universal_overview.json
json:universal_profile_segments.json
json:universal_association.json
json:universal_recommendation.json
json:universal_promotion.json
json:universal_summary.json
```

Data Processing dataset ref 和 sidecar ref 会包含 `id`、`project_id`、`job_id`、`type` 或 `sidecar_type`、`name`、`storage_key`、`url`、`metadata`、`created_at`。调用方不应依赖本地文件路径。

## 推荐接入流程

### Retail V2

1. `POST /api/analysis/projects` 创建项目。
2. `POST /api/analysis/projects/{project_id}/dataset` 上传固定中文列 Retail CSV。
3. `POST /api/analysis/projects/{project_id}/run` 启动分析。
4. 订阅 `GET /api/analysis/projects/{project_id}/events`，并用 `GET /api/analysis/projects/{project_id}` 作为初始快照和兜底刷新。
5. 完成后读取 recommendations、marketer-insights 和 artifacts。

### Data Processing

1. `POST /api/analysis/jobs` 创建 job。
2. `POST /api/analysis/jobs/{job_id}/raw-dataset?project_id=...` 上传 CSV/Excel。
3. `POST /api/analysis/jobs/{job_id}/regularize?project_id=...` 标准化。
4. 如果状态不是 `needs_review`，调用 `POST /api/analysis/jobs/{job_id}/run?project_id=...`。
5. 订阅 `GET /api/analysis/jobs/{job_id}/events?project_id=...`，并用 `GET /api/analysis/jobs/{job_id}?project_id=...` 作为初始快照和兜底刷新。
6. 完成后读取 outputs、datasets 和 sidecars。

## Admin Console API

Admin API 统一前缀为 `/api/admin`，所有接口需要 admin 角色（通过 `users.role = 'admin'` 授权）。

### 认证方式

所有 `/api/admin/*` 接口需要 Bearer Token（JWT），且 DB 中用户的 `role` 必须为 `"admin"`。

- 未登录 → 401
- 普通用户（role='user'）→ 403
- Admin（role='admin'）→ 200

**注意**：授权以 `ResolveCurrentUserPipeline` 查 DB 后返回的 `AuthenticatedUserContext.role` 为准，不信任 JWT payload 中的 role claim。

### 运行状态

```
GET /api/admin/status/summary
```

**Response:**
```json
{
  "success": true,
  "data": {
    "overallStatus": "healthy",
    "services": [
      {
        "key": "backend",
        "name": "Python Backend",
        "category": "app",
        "status": "healthy",
        "latencyMs": 0.5,
        "checkedAt": "2026-05-30T10:00:00Z",
        "version": "1.0.0"
      }
    ],
    "generatedAt": "2026-05-30T10:00:00Z"
  }
}
```

### 系统设置

```
GET  /api/admin/settings           → 全部设置（LLM/Infra/Alert 脱敏）
POST /api/admin/settings/llm/test  → 测试 LLM 连接
POST /api/admin/settings/alert/bark/test → 发送测试 Bark 推送
```

敏感字段（API Key、Password、Device Key）只返回 `*Configured: boolean`，不返回明文。

### 系统日志

```
GET  /api/admin/logs/events?level=&eventType=&offset=&limit=    → 事件日志列表
GET  /api/admin/logs/events/{event_id}                          → 单条事件详情
GET  /api/admin/logs/events/export?format=json|csv              → 导出事件日志
GET  /api/admin/logs/audit?actorUserId=&offset=&limit=          → 审计日志列表
GET  /api/admin/logs/audit/{audit_id}                           → 单条审计详情
GET  /api/admin/logs/audit/export?format=json|csv               → 导出审计日志
```

审计日志导出自身会写一条 `admin.download_audit_log` 审计记录。

### 用户管理

```
GET   /api/admin/users?search=&offset=&limit=  → 用户列表
GET   /api/admin/users/{user_id}               → 用户详情（含项目列表）
PATCH /api/admin/users/{user_id}/role           → 修改角色 { "role": "admin"|"user" }
PATCH /api/admin/users/{user_id}/status         → 启用/禁用 { "status": "active"|"disabled" }
```

安全约束：
- 不能修改自己的角色
- 不能禁用自己
- 不能将最后一个 admin 降级为 user
- 角色/状态修改写审计日志

### Admin Bootstrap

通过一次性脚本创建初始 admin：

```bash
ADMIN_BOOTSTRAP_EMAIL=admin@example.com uv run python -m backend.scripts.bootstrap_admin
```

DB Migration: `alembic/versions/0004_add_user_role.py` 为 `users` 表增加 `role` 列（`String(32)`, `server_default="user"`）。

## 已退役路由

以下旧路由已不在当前 OpenAPI 中，契约测试要求返回 404。新接入方不要使用这些路径：

```text
/api/projects
/api/recommend
/api/association
```

## 运行模型注意事项

- Retail V2 分析任务通过 Redis/RQ 入队，worker 入口是 `backend/workers/retail_analysis_worker.py`。状态变化通过 Redis pub/sub SSE 暴露；REST snapshot 仍是兜底一致性来源。
- Retail V2 项目状态写入 PostgreSQL；大文件、CSV、报告、图表和模型 artifact 仍通过文件型 Provider 保存。不要把 Redis 当业务真相源。
- 读取 artifact、dataset、model、sidecar 时应通过 API 返回的 ref 与 URL 继续访问，不应拼接本地路径。
