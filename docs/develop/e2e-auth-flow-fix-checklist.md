# E2E 用户鉴权主线修复 Checklist

**日期**: 2026-05-29  
**关联文档**: [e2e-auth-flow-analysis.md](./e2e-auth-flow-analysis.md)

---

## P0：恢复主线流程（阻断级 Bug）

### 后端

- [x] **Fix `JsonProjectRepositoryAdapter.get_project()` 签名**
  - 文件: `backend/infrastructure/adapters/json_project_repository_adapter.py`
  - 改为 `get_project(self, project_id: str, owner_user_id: str | None = None) -> Project | None`
  - 当 `owner_user_id is not None` 时，从 `ProjectStorage` 读取后校验 `project.owner_user_id == owner_user_id`
  - 同理修复 `list_projects()`, `delete_project()`, `count_projects()`

- [x] **Fix `PostgresProjectRepositoryAdapter.get_project()` 签名**
  - 文件: `backend/infrastructure/adapters/postgres_project_repository_adapter.py`
  - 改为 `get_project(self, project_id: str, owner_user_id: str | None = None) -> Project | None`
  - 当 `owner_user_id is not None` 时，SQL 增加 `WHERE owner_user_id = :owner_user_id`
  - 同理修复 `list_projects()`, `delete_project()`, `count_projects()`

- [x] **Fix `POST /api/analysis/projects/{id}/run` 缺失 auth dependency**
  - 文件: `backend/api/analysis.py`
  - 添加 `user: AuthenticatedUserContext | None = Depends(get_current_user_or_enforce)`
  - `flow.get_project(project_id)` → `flow.get_project(project_id, user_context=user)`
  - `dp_flow.run_analysis(...)` → `dp_flow.run_analysis(..., user_context=user)`

- [x] **Fix `POST /api/analysis/projects/{id}/regularize` 缺失 auth dependency**
  - 文件: `backend/api/analysis.py`
  - 添加 `user: AuthenticatedUserContext | None = Depends(get_current_user_or_enforce)`
  - `flow.get_project(project_id)` → `flow.get_project(project_id, user_context=user)`
  - `dp_flow.regularize(...)` → `dp_flow.regularize(..., user_context=user)`

- [x] **Fix `GET /api/analysis/projects/{id}/events` 缺失 auth dependency**
  - 文件: `backend/api/analysis.py`
  - 添加 `user: AuthenticatedUserContext | None = Depends(get_current_user_or_enforce)`
  - `flow.get_project(project_id)` → `flow.get_project(project_id, user_context=user)`

- [x] **Fix `GET /api/analysis/jobs/{id}/events` 缺失 auth dependency**
  - 文件: `backend/api/analysis.py`
  - 添加 `user: AuthenticatedUserContext | None = Depends(get_current_user_or_enforce)`
  - `flow.get_job(...)` → `flow.get_job(..., user_context=user)`

- [x] **Fix `RetailAnalysisState` 序列化丢失 `owner_user_id`**
  - 文件: `backend/business/flows/retail_analysis_state.py`
  - `_state_payload` 增加 `owner_user_id` 参数并写入返回 dict
  - `state_from_provider_dto` 传递 `owner_user_id=state.owner_user_id`

- [x] **为 `isolated_env` fixture 配置 fake auth providers**
  - 文件: `tests/api/conftest.py`
  - 在 `ProvidersContainer` 中设置 `user_directory`, `password_hasher`, `auth_token`, `sse_ticket`
  - 引入 `tests/fakes/auth_providers.py` 中的 fake 实现

- [x] **添加覆盖"登录用户创建 DP 项目并运行分析"的 API contract 测试**
  - 文件: `tests/api/test_data_processing_analysis_contracts.py`
  - 流程: register → login → create project → upload → regularize → run (chain-native)
  - 验证所有步骤返回 200/201/202，不出现 500

### 前端

- [ ] **确认 `apiClient` 统一注入 Authorization header**
  - 文件: `frontend/src/api/client.ts`
  - 状态: ✅ 已实现，无需修改

- [ ] **确认 auth store 在 mount 前完成 `loadMe()`**
  - 文件: `frontend/src/main.ts`
  - 状态: ✅ 已实现，无需修改

### E2E

- [ ] **创建最小 E2E 探测脚本**
  - 文件: `tests/e2e/test_auth_main_flow.py`
  - 覆盖: 登录 → 创建项目 → 上传 → regularize → run → 查询详情 → 读取 artifact

---

## P1：架构修复

### API Layer

- [ ] **所有修改资源的 analysis 端点统一声明 `get_current_user_or_enforce`**
  - 当前缺失: `/projects/{id}/run`, `/projects/{id}/regularize`, `/projects/{id}/events`, `/jobs/{id}/events`
  - 完成后进行 code review，确保没有遗漏

- [ ] **API 层只做鉴权依赖、DTO 转换、调用 Flow**
  - 禁止在 API handler 中直接处理用户业务逻辑
  - 状态: 当前已符合，继续保持

### Business Flow / Orchestration Layer

- [ ] **`RetailAnalysisFlow` 所有方法签名保持 `user_context` 参数**
  - 状态: ✅ 已实现，继续保持

- [ ] **`DataProcessingAnalysisFlow` 所有方法签名保持 `user_context` 参数**
  - 状态: ✅ 已实现，继续保持

- [ ] **`_assert_project_access` 在 repository 修复后实际生效**
  - 验证: 编写测试，确认已登录用户 A 无法访问已登录用户 B 的项目

### Ability Layer

- [ ] **Ability 层不直接依赖 HTTP / JWT**
  - `resolve_current_user` ability 只接收 `token`, `auth_token`, `user_directory`
  - 状态: ✅ 已实现，继续保持

### Provider Boundary

- [ ] **`ProjectRepositoryProvider` 协议与实现签名一致**
  - 所有实现必须接受 `owner_user_id: str | None = None`
  - 实现列表: `JsonProjectRepositoryAdapter`, `PostgresProjectRepositoryAdapter`, `FakeProjectRepositoryProvider`

- [ ] **`RetailAnalysisStateProvider` 协议与实现签名一致**
  - 状态: ✅ 已实现

- [ ] **`AnalysisArtifactProvider` 实现补充 `owner_user_id` 校验**
  - 当前 `LocalAnalysisArtifactAdapter` / `MinioAnalysisArtifactAdapter` 忽略该参数
  - 建议: 至少通过 `project_id` 间接校验归属（如读取 `retail_analysis_state` 确认 owner）

### Infrastructure Layer

- [ ] **Postgres 适配器路径/查询有明确 namespace**
  - `PostgresRetailAnalysisStateAdapter` 已按 `owner_user_id` 过滤
  - `PostgresProjectRepositoryAdapter` 修复后需同样过滤

- [ ] **JSON 存储适配器路径/查询有明确 namespace**
  - `JsonProjectRepositoryAdapter` 修复后需支持 owner 过滤
  - `ProjectStorage` 可能需要新增按 owner 过滤的方法

---

## P2：测试补强

### Auth Helper

- [ ] **添加 `auth_headers()` fixture**
  - 文件: `tests/api/conftest.py`
  - 返回一个可复用的 helper: `auth_headers(email, password) -> dict[str, str]`

- [ ] **添加 `create_test_user()` fixture**
  - 通过 `RegisterUserPipeline` 创建测试用户

- [ ] **添加 `authenticated_client()` fixture**
  - 返回一个已登录的 `TestClient`（已设置默认 Authorization header）

### Contract Tests

- [ ] **为每个主线端点补充"已登录用户"场景**
  - `test_retail_analysis_contracts.py`: create / list / get / delete / upload / run / artifacts / recommendations
  - `test_data_processing_analysis_contracts.py`: create job / upload / regularize / run / outputs
  - `test_project_data_processing_entry_contracts.py`: create project / upload / regularize / run

- [ ] **为受保护端点补充"未登录用户 401"场景**
  - `GET /api/auth/me` 无 token → 401
  - `POST /api/analysis/projects` 无 token（当 `AUTH_ENFORCE_ANALYSIS_AUTH=True` 时）→ 401

- [ ] **添加跨用户隔离测试**
  - 用户 A 创建项目 → 用户 B 尝试 GET / DELETE / run → 404 或 403

### Frontend Tests

- [ ] **添加 401 行为测试**
  - 前端收到 401 后是否正确清除 token 并跳转登录页

- [ ] **添加路由守卫测试**
  - 未登录访问 `/projects` → 跳转 `/login?redirect=/projects`
  - 已登录访问 `/login` → 建议跳转 `/projects`（待实现）

---

## P3：历史数据 / migration

- [ ] **审查 `0003_make_owner_user_id_nullable.py`**
  - 由于 `0002` 当前已注释掉 `nullable=False`，`0003` 逻辑上冗余
  - 建议: 如果 `0002` 未在任何环境执行过，将 `0003` 的内容合并到 `0002` 并删除 `0003`
  - 如果 `0002` 已在某些环境执行（且当时设为 non-nullable），保留 `0003`

- [ ] **Legacy User 处理策略**
  - `LEGACY_USER_ID = "00000000000000000000000000000000"`
  - 该用户密码 hash 是无效占位符，无法登录
  - 策略选项:
    a) 保留 legacy user，允许管理员将其项目转移给真实用户
    b) 在启用强制鉴权前，为 legacy user 生成有效密码并创建登录接口
    c) 将所有 legacy 项目 `owner_user_id` 设为 `NULL`（匿名项目）

- [ ] **Dev 环境兼容策略**
  - 当 `AUTH_ENFORCE_ANALYSIS_AUTH=False` 时，允许匿名创建项目（`owner_user_id=NULL`）
  - 前端需要支持未登录用户仍可浏览公开页面（如 `/project-intro`）
  - 后端需要继续支持 `get_current_user_or_enforce` 返回 `None`

---

## 验收标准

本 Checklist 完成后必须满足:

1. [ ] 已登录用户通过链-native DP 端点（`/jobs/{id}/run` 等）不再出现 500 TypeError
2. [ ] `POST /projects/{id}/run` 和 `POST /projects/{id}/regularize` 已接入鉴权并校验 owner
3. [ ] 所有 API contract 测试通过（包括新增 auth 场景）
4. [ ] 匿名模式（`AUTH_ENFORCE_ANALYSIS_AUTH=False`）仍可正常工作
5. [ ] 至少有一个测试覆盖"登录用户创建 DP 项目 → 上传 → regularize → run → 查看结果"完整流程
6. [ ] 分析文档和修复 checklist 已更新并同步到代码仓库
