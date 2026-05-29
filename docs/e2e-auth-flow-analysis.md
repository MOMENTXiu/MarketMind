# E2E 主线流程与用户鉴权问题分析

**日期**: 2026-05-29  
**范围**: 后端 API / 前端请求链路 / 测试覆盖 / 数据迁移  
**状态**: 已完成扫描与复现，发现 1 个阻断级 Bug + 多个架构级缺陷

---

## 1. 背景

项目在引入用户系统（注册 / 登录 / JWT / 当前用户解析）后，主线的 E2E 流程（新建项目 → 上传文件 → 启动分析 → 查看结果）在**已登录用户场景下**出现 500 崩溃。根本原因是 `DataProcessingAnalysisFlow._assert_project_access` 向 `repository.get_project()` 传入了 `owner_user_id` 关键字参数，但所有 `ProjectRepositoryProvider` 的实现均**未在签名中声明该参数**，导致 `TypeError`。

此外，多个主线接口缺失 JWT dependency，SSE 流未认证，测试全部以匿名方式运行，无法覆盖真实登录流程。

---

## 2. 当前主线流程

```
登录 / 注册
  → 新建项目 (POST /api/analysis/projects)
  → 上传文件 (POST /api/analysis/projects/{id}/dataset)
  → 数据标准化 (POST /api/analysis/projects/{id}/regularize)
  → 启动分析 (POST /api/analysis/projects/{id}/run)
  → 轮询状态 (GET  /api/analysis/projects/{id})
  → 读取 artifact (GET /api/analysis/projects/{id}/artifacts/...)
  → 前端展示 (ProjectDetail.vue)
```

---

## 3. 后端接口扫描结果

### 3.1 Analysis API (`backend/api/analysis.py`)

| Method | Path | Handler | Auth Dependency | User Context | Main Flow | Problem |
|--------|------|---------|-----------------|--------------|-----------|---------|
| POST | `/api/analysis/projects` | `create_project` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects` | `list_projects` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects/{id}` | `get_project` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| DELETE | `/api/analysis/projects/{id}` | `delete_project` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| POST | `/api/analysis/projects/{id}/dataset` | `upload_dataset` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| POST | `/api/analysis/projects/{id}/regularize` | `regularize_project_dataset` | **❌ 无** | ❌ | ✅ | **未鉴权、未校验 owner** |
| POST | `/api/analysis/projects/{id}/run` | `run_analysis` | **❌ 无** | ❌ | ✅ | **未鉴权、未校验 owner** |
| GET | `/api/analysis/projects/{id}/events` | `stream_project_events` | **❌ 无** (SSE Ticket 可选) | ❌ | ✅ | **未校验 owner** |
| GET | `/api/analysis/projects/{id}/artifacts` | `list_artifacts` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects/{id}/artifacts/{aid}/payload` | `get_artifact_payload` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects/{id}/artifacts/{aid}` | `get_artifact_ref` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects/{id}/datasets/{did}` | `get_dataset_ref` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects/{id}/recommendations` | `list_recommendations` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| GET | `/api/analysis/projects/{id}/marketer-insights` | `get_marketer_insights` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| POST | `/api/analysis/jobs` | `create_data_processing_job` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| POST | `/api/analysis/jobs/{id}/raw-dataset` | `upload_raw_dataset` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| POST | `/api/analysis/jobs/{id}/regularize` | `regularize_dataset` | `get_current_user_or_enforce` | ✅ | ✅ | 无 |
| POST | `/api/analysis/jobs/{id}/run` | `run_data_processing_analysis` | `get_current_user_or_enforce` | ✅ | ✅ | **运行时 500（见复现）** |
| GET | `/api/analysis/jobs/{id}` | `get_data_processing_job` | `get_current_user_or_enforce` | ✅ | ✅ | **运行时 500（见复现）** |
| GET | `/api/analysis/jobs/{id}/events` | `stream_data_processing_job_events` | **❌ 无** (SSE Ticket 可选) | ❌ | ✅ | **未校验 owner** |
| GET | `/api/analysis/jobs/{id}/outputs` | `list_data_processing_outputs` | `get_current_user_or_enforce` | ✅ | ✅ | **运行时 500（见复现）** |

### 3.2 Auth API (`backend/api/auth.py`)

| Method | Path | Auth | 状态 |
|--------|------|------|------|
| POST | `/api/auth/register` | 公开 | ✅ |
| POST | `/api/auth/login` | 公开 | ✅ |
| GET | `/api/auth/me` | `get_current_user` 强制 | ✅ |
| POST | `/api/auth/logout` | `get_current_user` 强制 | ✅ |
| POST | `/api/auth/sse-ticket` | `get_current_user` 强制 | ✅ |

### 3.3 JWT 实现

- **Payload**: `sub` = `user_id` (uuid4 hex, `str`), `email`, `display_name`, `iat`, `exp`
- **算法**: HS256
- **过期**: 60 分钟
- **Refresh Token**: ❌ 不存在
- **签发/验证**: `JwtAuthTokenAdapter`
- **`get_current_user`**: 解析 token → `ResolveCurrentUserPipeline` → `AuthenticatedUserContext(user_id, email, display_name)`
- **`get_current_user_or_enforce`**: 如果 `AUTH_ENFORCE_ANALYSIS_AUTH=False` 且未提供 token，返回 `None`（允许匿名）

---

## 4. 前端请求链路扫描结果

### 4.1 API Client
- **统一 Client**: `axios` 实例 `apiClient`，所有请求均通过它
- **Token 注入**: Request 拦截器自动读取 `authStore.accessToken` 并注入 `Authorization: Bearer <token>`
- **401 处理**: Response 拦截器捕获 401，调用 `onUnauthorized` → 清除 auth + 跳转登录页

### 4.2 Auth Store
- **框架**: Pinia + Composition API
- **Token 存储**: `localStorage`, key = `marketmind_access_token`
- **启动恢复**: `main.ts` 在 `app.mount()` 前 `await authStore.loadMe()`，恢复登录态

### 4.3 Router Guard
- **requiresAuth 路由**: `/projects`, `/projects/new`, `/projects/:id`, `/me/*`, `/data-processing/*` 等
- **守卫逻辑**: 仅检查 `requiresAuth && !isAuthenticated` 则跳 `/login`
- **guestOnly 未处理**: `/login`, `/register` 标记了 `guestOnly: true`，但守卫不拦截已登录用户

### 4.4 主线请求是否携带 Token

| API 调用 | 文件 | 是否携带 Token |
|----------|------|---------------|
| `createRetailProject` | `api/retail.ts` | ✅ |
| `uploadRetailDataset` | `api/retail.ts` | ✅ |
| `regularizeProjectDataset` | `api/data-processing.ts` | ✅ |
| `runRetailAnalysis` | `api/retail.ts` | ✅ |
| `getRetailProject` | `api/retail.ts` | ✅ |
| `listRetailArtifacts` | `api/retail.ts` | ✅ |
| `getRetailArtifactPayload` | `api/retail.ts` / `analysis-artifacts.ts` | ✅ |
| `openRetailProjectEvents` | `api/retail.ts` | ❌ **EventSource 无法带 header** |
| `runDataProcessingJob` | `api/data-processing.ts` | ✅ |
| `getDataProcessingJob` | `api/data-processing.ts` | ✅ |

### 4.5 前端问题
1. **SSE EventSource 未携带认证**: `openRetailProjectEvents` / `openDataProcessingJobEvents` 使用原生 `EventSource`，无法设置 `Authorization` header。后端 `/events` 端点 fallback 到无认证模式。
2. **guestOnly 未处理**: 已登录用户仍可访问 `/login`。
3. **死代码**: `frontend/src/utils/http.ts` 独立 axios 实例未被任何文件引用。

---

## 5. E2E 测试扫描结果

### 5.1 测试框架
- **Playwright / Cypress**: ❌ 不存在
- **API Contract Tests**: `tests/api/` 下共 58 个 pytest 用例

### 5.2 测试覆盖情况

| 测试文件 | 鉴权覆盖 | 说明 |
|----------|---------|------|
| `test_auth_contracts.py` | ✅ | 注册/登录/me/logout/SSE ticket 均使用 fake auth providers |
| `test_retail_analysis_contracts.py` | ❌ | 全部匿名调用，无 Authorization header |
| `test_data_processing_analysis_contracts.py` | ❌ | 全部匿名调用 |
| `test_project_data_processing_entry_contracts.py` | ❌ | 全部匿名调用 |
| `test_frontend_api_matrix_contracts.py` | ❌ | 全部匿名调用 |

### 5.3 测试 Fixture 问题
- `isolated_env` / `isolated_env_real_adapter` **未配置 auth providers** (`user_directory`, `password_hasher`, `auth_token`, `sse_ticket` 均为 `None`)
- 如果测试尝试发送 auth header，后端 `ResolveCurrentUserPipeline` 会因 `auth_token is None` 抛出 `RuntimeError`

---

## 6. 复现结果

使用最小探测脚本复现已登录用户的主线流程：

```
Register:  201 ✅
Login:     200 ✅
Create project: 201 ✅
Upload dataset: 200 ✅
Regularize (project-facing): 200 ✅
Run analysis (project-facing): 202 ✅
Run analysis (chain-native DP): 500 ❌ TypeError
```

**崩溃堆栈**:
```
File "backend/business/flows/data_processing_analysis_flow.py", line 304, in _assert_project_access
    project = self.providers.repository.get_project(project_id, owner_user_id=user_context.user_id)
TypeError: JsonProjectRepositoryAdapter.get_project() got an unexpected keyword argument 'owner_user_id'
```

同样的错误会在以下链-native DP 端点发生（只要用户已登录并携带 token）：
- `POST /api/analysis/jobs/{id}/run`
- `GET /api/analysis/jobs/{id}`
- `GET /api/analysis/jobs/{id}/outputs`
- `POST /api/analysis/jobs/{id}/regularize`
- `POST /api/analysis/jobs/{id}/raw-dataset`
- `GET /api/analysis/jobs/{id}/datasets/{did}`
- `GET /api/analysis/jobs/{id}/sidecars/{sid}`

---

## 7. 问题归因

### 7.1 后端问题

#### A. 接口鉴权问题
| # | 问题 | 位置 |
|---|------|------|
| 1 | `POST /projects/{id}/run` 未声明 JWT dependency | `backend/api/analysis.py:332` |
| 2 | `POST /projects/{id}/regularize` 未声明 JWT dependency | `backend/api/analysis.py:311` |
| 3 | `GET /projects/{id}/events` 未声明 JWT dependency | `backend/api/analysis.py:377` |
| 4 | `GET /jobs/{id}/events` 未声明 JWT dependency | `backend/api/analysis.py:616` |

#### B. 业务数据归属问题
| # | 问题 | 位置 |
|---|------|------|
| 5 | `JsonProjectRepositoryAdapter` 未实现 `owner_user_id` 参数 | `backend/infrastructure/adapters/json_project_repository_adapter.py:28` |
| 6 | `PostgresProjectRepositoryAdapter` 未实现 `owner_user_id` 参数 | `backend/infrastructure/adapters/postgres_project_repository_adapter.py:48` |
| 7 | `DataProcessingAnalysisFlow._assert_project_access` 依赖 repository 做 owner 校验，但实现不生效 | `backend/business/flows/data_processing_analysis_flow.py:301` |
| 8 | `LocalAnalysisArtifactAdapter` / `MinioAnalysisArtifactAdapter` 忽略 `owner_user_id` | Provider 接口声明了参数但实现未使用 |
| 9 | `LocalRegularizedDatasetAdapter` / `MinioRegularizedDatasetAdapter` 忽略 `owner_user_id` | Provider 接口声明了参数但实现未使用 |

#### C. 后端架构接入问题
| # | 问题 | 位置 |
|---|------|------|
| 10 | `AUTH_ENFORCE_ANALYSIS_AUTH = False` 导致所有 `get_current_user_or_enforce` 实际上允许匿名 | `backend/core/config.py:85` |
| 11 | 双存储架构不一致：Retail V2 state 有 owner 隔离，Project metadata (repository) 无 owner 隔离 | `backend/infrastructure/factories/provider_factory.py` |
| 12 | DP job state 存储在 `analysis_models` 中，无 `owner_user_id` 字段，仅通过 `project_id` 间接推导 | `backend/business/flows/data_processing_analysis_flow.py` |

### 7.2 前端问题

| # | 问题 | 位置 |
|---|------|------|
| 1 | SSE EventSource 无法携带 Authorization header，当前使用无 ticket 模式 | `frontend/src/api/client.ts:49` |
| 2 | `guestOnly` 路由未在守卫中处理 | `frontend/src/router/index.ts:99` |
| 3 | `utils/http.ts` 死代码 | `frontend/src/utils/http.ts` |

### 7.3 E2E 测试问题

| # | 问题 | 说明 |
|---|------|------|
| 1 | 无 E2E 框架（Playwright / Cypress） | 未覆盖浏览器级 E2E |
| 2 | API contract 测试全部匿名运行 | 58 个用例无一个携带 token |
| 3 | `isolated_env` fixture 未配置 auth providers | 测试无法发送有效 auth header |
| 4 | 无覆盖登录 → 创建项目 → 分析 → 查看结果的完整流程测试 | 需要补充 |

### 7.4 数据 / migration 问题

| # | 问题 | 说明 |
|---|------|------|
| 1 | `0003_make_owner_user_id_nullable.py` 与 `0002` 当前状态冗余 | `0002` 已注释掉 `nullable=False`，`0003` 再次设为 nullable 无实际作用 |
| 2 | Legacy JSON 存储的 `Project` 对象有 `owner_user_id` 字段但 `ProjectStorage` 不读写 | `backend/core/storage.py` |
| 3 | 子表（datasets/artifacts/processing_runs 等）无 `user_id`，完全依赖 `project_id` 间接关联 | 数据模型设计 |

---

## 8. 修复建议

### P0：恢复主线流程
1. ✅ 为 `JsonProjectRepositoryAdapter` 和 `PostgresProjectRepositoryAdapter` 添加 `owner_user_id` 参数支持
2. ✅ 为 `POST /projects/{id}/run` 和 `POST /projects/{id}/regularize` 添加 `get_current_user_or_enforce` dependency
3. ✅ 为 `GET /projects/{id}/events` 和 `GET /jobs/{id}/events` 添加 `get_current_user_or_enforce` dependency
4. ✅ 修复 `RetailAnalysisState` 序列化丢失 `owner_user_id` 的问题（`state_from_provider_dto` / `_state_payload`）
5. ✅ 为 `isolated_env` fixture 配置 fake auth providers
6. ✅ 添加至少一个覆盖“登录用户创建 DP 项目并运行分析”的 API contract 测试

### P1：架构修复
1. API 层统一鉴权：所有修改资源的端点必须声明 `get_current_user_or_enforce`
2. Business Flow 层统一接收 `UserContext`
3. Ability 层不依赖 HTTP current_user
4. Provider / Repository 按 `user/project` scope 查询
5. Infrastructure 层路径/存储有明确 namespace

### P2：测试补强
1. 添加 auth helper fixture（`auth_headers()`, `create_test_user()`）
2. 为每个主线端点补充“已登录用户”和“未登录用户”两种场景的 contract test
3. 补充 401/403 前端行为测试

### P3：历史数据 / migration
1. 决定 `0003` migration 是否保留（建议删除，因为 `0002` 当前版本已满足需求）
2. 明确 dev 环境兼容策略：当 `AUTH_ENFORCE_ANALYSIS_AUTH=False` 时，匿名项目 `owner_user_id=NULL` 是合法的

---

## 9. 风险点

1. **如果直接启用 `AUTH_ENFORCE_ANALYSIS_AUTH=True`**，所有现有匿名 API contract 测试会立即失败，前端未登录用户无法使用任何功能。
2. **`JsonProjectRepositoryAdapter` 和 `PostgresProjectRepositoryAdapter` 的修复是 breaking change**——任何直接调用 `get_project(project_id)`（无关键字参数）的代码仍然兼容，但内部实现必须新增 `owner_user_id` 过滤逻辑。
3. **SSE 认证改造需要前后端配合**：前端改为 `createEventSourceWithTicket`，后端 `/events` 端点在没有 ticket 时拒绝连接。
4. **旧项目（`owner_user_id = LEGACY_USER_ID`）在启用强制鉴权后**，legacy user 的密码 hash 是无效占位符，无法登录，这些项目将变成“孤儿项目”。

---

## 10. 后续建议

1. **分阶段 rollout**：保持 `AUTH_ENFORCE_ANALYSIS_AUTH=False` 直到所有修复完成、测试覆盖到位，再逐步开启。
2. **统一 UserContext DTO**：定义显式的 `UserContext` / `ActorContext` dataclass，在 API → Flow → Service → Repository 全链路传递，禁止底层模块直接解析 JWT。
3. **引入 Refresh Token**：当前 access_token 仅 60 分钟，无 refresh 机制，用户体验不佳。
4. **建立 E2E 测试套件**：引入 Playwright，覆盖“注册 → 登录 → 创建项目 → 上传 → 分析 → 查看结果”完整浏览器流程。
