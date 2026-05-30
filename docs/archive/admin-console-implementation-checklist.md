# MarketMind Admin Console — 施工清单

> **版本**: v1.1-architecture-reviewed
> **日期**: 2026-05-30
> **对应设计**: `docs/admin/admin-console-design.md`
> **后端约束**: 遵守 `backend-architecture-orchestration`。施工顺序固定为：测试锚点 -> Provider Interface -> External Adapter -> Ability Atom -> Business Pipeline -> API Controller -> Architecture Lint / Runtime Check / 全量验证 -> 清理收尾。

---

## 审查后必须修正的问题

| 问题 | 处理方式 |
|---|---|
| 原清单先做 migration / wiring，缺少行为保护 | Phase 0 先补测试锚点和基线命令，再动实现 |
| 原清单把 status/settings/logs/users 都设计为 Business Flow | P0 改为 Business Pipeline；除非后续出现异步生命周期、审批、状态机、补偿/恢复，否则不创建 Flow |
| 原清单让 admin 授权依赖 JWT role claim | JWT 只证明身份；后端授权必须以 DB lookup 后的 `AuthenticatedUserContext.role` 为准 |
| 原清单直接扩展 `UserDirectoryProvider` 做管理列表/统计 | 新增 `AdminUserProvider`；认证目录和管理查询分离 |
| 原清单 FileTelemetry 与日志页面字段不匹配 | 先定义 telemetry envelope，再实现 JSONL 写入和查询 |
| 原清单没有初始 admin 可执行入口 | 新增 bootstrap script / seed 步骤，并纳入验证 |
| 原清单缺少 Architecture Lint 更新 | 扩展 `tests/test_architecture_imports.py` 覆盖 admin 新模块 |

---

## Phase 0: 行为锚点与架构基线

### 0.1 记录当前基线

- [ ] **WHERE**: `Makefile`, `tests/test_architecture_imports.py`, `tests/api/`, `tests/infrastructure/db/`
- [ ] **WHY**: 架构迁移前必须知道现有测试和 architecture lint 的真实状态。
- [ ] **HOW**: 运行并记录基线：
  - `make lint`
  - `make test`
  - `make check`
- [ ] **EXPECTED_RESULT**: 知道当前失败/通过项；若已有失败，标注是否与 admin 施工相关。
- [ ] **VERIFY**: 在本清单对应 Phase 记录命令结果，不用 echo-only target 当作通过证据。

### 0.2 Admin API 鉴权行为测试

- [ ] **WHERE**: `tests/admin/test_admin_auth.py`
- [ ] **WHY**: `/api/admin/*` 的 401/403/200 是公开安全契约，必须先保护。
- [ ] **HOW**:
  - 构造无 token、普通 user、admin user 三类请求。
  - admin role 必须来自 fake/user provider 的 DB lookup 结果，不从 JWT role claim 判定。
  - 先固定待实现 route contract；实现阶段再接入真实 route。
- [ ] **EXPECTED_RESULT**:
  - 未登录访问 admin API -> 401。
  - 普通 user 访问 admin API -> 403。
  - admin 访问 admin API -> 200。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_auth.py`

### 0.3 Settings 敏感字段测试

- [ ] **WHERE**: `tests/admin/test_admin_settings_contracts.py`
- [ ] **WHY**: Settings 页面最主要风险是密钥/密码泄露。
- [ ] **HOW**:
  - 覆盖 LLM API key、DB password、Redis password、MinIO secret、Bark device key。
  - 断言响应只包含 `configured` / host:port / 非敏感配置，不包含明文 secret。
- [ ] **EXPECTED_RESULT**: settings API 的响应 schema 和脱敏规则被测试固定。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_contracts.py`

### 0.4 Telemetry envelope 与日志查询测试

- [ ] **WHERE**: `tests/admin/test_admin_logs_contracts.py`
- [ ] **WHY**: 当前 `FileTelemetryAdapter` JSONL 结构不足以支撑日志列表/筛选/导出，必须先固定目标 envelope。
- [ ] **HOW**:
  - 用临时 JSONL fixture 覆盖 event/audit/span/error envelope。
  - 测试 level、event_type、actor_user_id、project_id、job_id、时间范围、分页、JSON/CSV export。
  - 测试 audit export 自身写一条 `admin.download_audit_log`。
- [ ] **EXPECTED_RESULT**: `JsonlLogQueryAdapter` 的输入输出契约明确。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_logs_contracts.py`

### 0.5 用户管理安全测试

- [ ] **WHERE**: `tests/admin/test_admin_users_contracts.py`
- [ ] **WHY**: 用户角色/status 修改有锁死管理员和越权风险。
- [ ] **HOW**:
  - 覆盖 list/detail/update role/update status。
  - 覆盖不能修改自己 role、不能禁用自己、不能降级最后一个 admin、修改写 audit。
- [ ] **EXPECTED_RESULT**: 用户管理的副作用、安全约束、错误语义被测试保护。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_users_contracts.py`

### 0.6 Architecture Lint 目标规则

- [ ] **WHERE**: `tests/test_architecture_imports.py`
- [ ] **WHY**: admin 新模块必须被机械化边界检查覆盖。
- [ ] **HOW**:
  - 确认 `backend/api/admin/*` 不 import DB/SDK/Infrastructure Adapter。
  - 确认 `backend/business/pipelines/admin_*` 不 import FastAPI/Settings/Infrastructure。
  - 确认 `backend/abilities/admin/*` 不 import FastAPI/Infrastructure/Settings。
  - 确认 `backend/providers/*` 不 import Infrastructure/Business/Ability/API。
- [ ] **EXPECTED_RESULT**: 新 admin 后端文件落地后能被 import rule 自动拦截。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

---

## Phase 1: Provider Interface 与 DTO

### 1.1 Admin DTOs

- [ ] **WHERE**: `backend/providers/admin_dtos.py`
- [ ] **WHY**: Provider Boundary 需要稳定 DTO，避免 API schema、DB record、JSONL payload 在业务层混用。
- [ ] **HOW**:
  - 新增 `ServiceHealthDTO`, `AdminHealthSummaryDTO`。
  - 新增 `SettingsInspectionDTO`, `LlmSettingsDTO`, `InfraSettingsDTO`, `AlertSettingsDTO`。
  - 新增 `TelemetryEnvelopeDTO`, `AdminLogRecordDTO`, `AdminLogQueryDTO`, `AdminLogPageDTO`, `ExportResultDTO`。
  - 新增 `AdminUserListItemDTO`, `AdminUserDetailDTO`, `AdminUserProjectDTO`, `UpdateRoleDTO`, `UpdateStatusDTO`。
- [ ] **EXPECTED_RESULT**: admin 后端跨层传递只使用 DTO/Protocol，不传 DB model 或外部 SDK response。
- [ ] **VERIFY**: `uv run python -m compileall backend/providers`

### 1.2 SettingsInspectionProvider

- [ ] **WHERE**: `backend/providers/settings_inspection_provider.py`
- [ ] **WHY**: 业务层不能读取 env；设置只读展示必须通过 Provider Boundary。
- [ ] **HOW**: 定义 `get_llm_settings()`, `get_infra_settings()`, `get_alert_settings()`, `get_all_settings()`。
- [ ] **EXPECTED_RESULT**: Ability/Pipeline 只依赖 provider，不 import `backend.core.config`。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

### 1.3 AlertProvider

- [ ] **WHERE**: `backend/providers/alert_provider.py`
- [ ] **WHY**: Bark HTTP 调用属于外部能力，不能出现在 Ability/Pipeline/API。
- [ ] **HOW**: 定义 `send_test_alert(...) -> TestResultDTO`；Provider 签名不暴露 HTTP client 或 raw response。
- [ ] **EXPECTED_RESULT**: Bark test 可替换 mock/provider 实现。
- [ ] **VERIFY**: `uv run python -m compileall backend/providers`

### 1.4 LogQueryProvider

- [ ] **WHERE**: `backend/providers/log_query_provider.py`
- [ ] **WHY**: JSONL 读取、分页、导出属于 Infrastructure Adapter，业务层只调用查询接口。
- [ ] **HOW**: 定义 `list_events()`, `get_event()`, `export_events()`, `list_audit()`, `get_audit()`, `export_audit()`。
- [ ] **EXPECTED_RESULT**: Admin log pipeline 不直接读文件。
- [ ] **VERIFY**: `uv run python -m compileall backend/providers`

### 1.5 AdminUserProvider

- [ ] **WHERE**: `backend/providers/admin_user_provider.py`, `backend/providers/container.py`
- [ ] **WHY**: 管理端用户列表/统计/角色修改不应塞进认证用 `UserDirectoryProvider`。
- [ ] **HOW**:
  - 定义 `list_users`, `count_users`, `get_user_detail`, `count_admin_users`, `update_user_role`, `update_user_status`。
  - `ProvidersContainer` 新增 `admin_users` 字段。
- [ ] **EXPECTED_RESULT**: `UserDirectoryProvider` 继续只承担注册/登录/当前用户解析所需能力。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

---

## Phase 2: Infrastructure Adapter 与 Provider Factory

### 2.1 User role migration 与 ORM

- [ ] **WHERE**: `alembic/versions/0004_add_user_role.py`, `backend/infrastructure/db/models/user.py`
- [ ] **WHY**: admin 授权需要持久化 role；DB 是授权真相源。
- [ ] **HOW**:
  - `users.role String(32) nullable=False server_default="user"`。
  - 索引 `ix_users_role`。
  - `UserRecord.role` 映射。
- [ ] **EXPECTED_RESULT**: 旧用户默认 `user`，后续 bootstrap 可提升 admin。
- [ ] **VERIFY**:
  - `uv run alembic upgrade head`
  - `uv run alembic downgrade -1`
  - `uv run pytest tests/infrastructure/db/test_alembic_roundtrip.py`

### 2.2 Auth DTO / DB lookup role

- [ ] **WHERE**: `backend/providers/auth_dtos.py`, `backend/infrastructure/adapters/postgres_user_directory_adapter.py`, `backend/abilities/auth/resolve_current_user.py`, `backend/api/auth.py`
- [ ] **WHY**: `/api/auth/me` 和 `require_admin_user` 都要拿 DB role；后端授权不能依赖 JWT role claim。
- [ ] **HOW**:
  - `UserIdentityDTO`, `AuthenticatedUserContext`, `AuthTokenClaimsDTO` 新增 `role` 默认值。
  - `_to_dto()` 映射 `record.role`。
  - `resolve_current_user()` 使用查出的 `user.role` 构造 context。
  - `/auth/login` 和 `/auth/me` 返回 `role`。
  - 可选：JWT payload 带 `role` 供展示缓存，但 admin 授权禁止读取 token role 作判断。
- [ ] **EXPECTED_RESULT**: role 改动后，下一次请求即按 DB role 生效。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_auth.py`

### 2.3 初始 admin bootstrap

- [ ] **WHERE**: `backend/scripts/bootstrap_admin.py` 或等价 seed command
- [ ] **WHY**: 没有第一个 admin，Phase 1 之后无法进入管理端。
- [ ] **HOW**:
  - 读取 `ADMIN_BOOTSTRAP_EMAIL`。
  - 使用 DB session 将已存在用户 role 设为 `admin`。
  - 不暴露运行时 HTTP API。
- [ ] **EXPECTED_RESULT**: 本地/部署初始化有可重复、可审计的 admin 生成路径。
- [ ] **VERIFY**:
  - 注册普通用户。
  - 运行 bootstrap。
  - `uv run pytest tests/admin/test_admin_auth.py::test_admin_role_returns_200`

### 2.4 Settings inspection adapter

- [ ] **WHERE**: `backend/infrastructure/adapters/env_settings_inspection_adapter.py`
- [ ] **WHY**: Settings 读取只能位于 Infrastructure/Provider Factory，业务层不能碰 env。
- [ ] **HOW**:
  - Adapter 构造时接收 `Settings` 或 typed config。
  - 返回脱敏 DTO：secret/password/device key 只返回 configured boolean。
  - connection string 只拆 host/port/database，不返回 credentials。
- [ ] **EXPECTED_RESULT**: settings API 无明文 secret。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_contracts.py`

### 2.5 Alert adapter

- [ ] **WHERE**: `backend/infrastructure/adapters/bark_alert_adapter.py`
- [ ] **WHY**: Bark HTTP 请求是外部 API 调用，必须留在 Infrastructure。
- [ ] **HOW**:
  - 使用 HTTP client，设置短超时。
  - 捕获 HTTP/client 原始异常，转换为内部错误或失败 DTO。
  - 不在 health check 自动发送 Bark。
- [ ] **EXPECTED_RESULT**: Bark test 可失败但不泄漏原始 secret/trace。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_contracts.py`

### 2.6 Telemetry file adapter envelope

- [ ] **WHERE**: `backend/infrastructure/adapters/file_telemetry_adapter.py`, `backend/providers/telemetry_dtos.py`, `backend/providers/admin_dtos.py`
- [ ] **WHY**: 日志 UI 依赖标准 envelope；现有 JSONL payload 不足。
- [ ] **HOW**:
  - `FileTelemetryAdapter` 写 `TelemetryEnvelopeDTO` JSON。
  - 写入时补 `id`, `created_at`, `level`, `event_type`, `message`。
  - 保留 Console adapter；如需双写，新增 `CompositeTelemetryAdapter`。
- [ ] **EXPECTED_RESULT**: JSONL 每行都是可查询、可导出的稳定结构。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_logs_contracts.py`

### 2.7 Log query adapter

- [ ] **WHERE**: `backend/infrastructure/adapters/jsonl_log_query_adapter.py`
- [ ] **WHY**: 文件读取、CSV/JSON 导出是 Infrastructure 能力。
- [ ] **HOW**:
  - 只读取 envelope v1。
  - 支持 filters、offset/limit、详情、JSON/CSV export。
  - 处理文件不存在、坏行、超大文件限制。
- [ ] **EXPECTED_RESULT**: Pipeline 不直接读写 `logs/telemetry/events.jsonl`。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_logs_contracts.py`

### 2.8 Admin user adapter

- [ ] **WHERE**: `backend/infrastructure/adapters/postgres_admin_user_adapter.py`
- [ ] **WHY**: list/count/project_count/role/status 修改属于 DB adapter 责任。
- [ ] **HOW**:
  - 实现 `AdminUserProvider`。
  - 所有 DB 异常转换为内部错误。
  - 不把 SQLAlchemy record 返回给业务层。
- [ ] **EXPECTED_RESULT**: 用户管理业务层只处理 DTO 和业务规则。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_users_contracts.py`

### 2.9 Provider Factory 装配

- [ ] **WHERE**: `backend/infrastructure/factories/provider_factory.py`
- [ ] **WHY**: 外部 adapter 只能由 Provider Factory 根据 Settings 创建。
- [ ] **HOW**:
  - 装配 `settings_inspection`, `alert`, `log_query`, `admin_users`。
  - health adapter 如需 LLM/Bark 配置，只注入脱敏/显式 config，不让业务层读取 Settings。
- [ ] **EXPECTED_RESULT**: `ProvidersContainer` 是业务层唯一外部能力入口。
- [ ] **VERIFY**:
  - `uv run pytest tests/test_architecture_imports.py`
  - `uv run pytest tests/admin`

---

## Phase 3: Ability Atom

### 3.1 Status abilities

- [ ] **WHERE**: `backend/abilities/admin/aggregate_service_status.py`
- [ ] **WHY**: 服务健康汇总是最小业务动作，不能放在 API 或 Adapter。
- [ ] **HOW**: 输入 provider 返回的 component health，输出 `AdminHealthSummaryDTO`，计算 overall status。
- [ ] **EXPECTED_RESULT**: status aggregation 可用 fake provider 单测。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_status_contracts.py`

### 3.2 Settings abilities

- [ ] **WHERE**: `backend/abilities/admin/inspect_settings.py`, `backend/abilities/admin/test_alert_connection.py`, `backend/abilities/admin/test_llm_connection.py`
- [ ] **WHY**: Ability 只组合 Provider 调用和结果转换，不读取 env、不创建 HTTP client。
- [ ] **HOW**:
  - inspect ability 调用 `SettingsInspectionProvider`。
  - test ability 调用 `AlertProvider` / `LLMProvider`。
  - test 操作返回结构化 result，审计由 Pipeline 统一编排。
- [ ] **EXPECTED_RESULT**: settings 能用 fake providers 单测。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_contracts.py`

### 3.3 Log abilities

- [ ] **WHERE**: `backend/abilities/admin/query_logs.py`, `backend/abilities/admin/export_logs.py`
- [ ] **WHY**: 日志筛选/导出动作通过 Provider 完成，业务层不读文件。
- [ ] **HOW**:
  - query ability 调用 `LogQueryProvider`。
  - export audit ability 不直接写审计，由 Pipeline 负责 audit 副作用顺序。
- [ ] **EXPECTED_RESULT**: query/export 可用 JSONL fake provider 测试。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_logs_contracts.py`

### 3.4 User management abilities

- [ ] **WHERE**: `backend/abilities/admin/list_admin_users.py`, `backend/abilities/admin/get_admin_user_detail.py`, `backend/abilities/admin/manage_user_role.py`, `backend/abilities/admin/manage_user_status.py`
- [ ] **WHY**: 不能修改自己、不能禁用自己、至少保留一个 admin 是业务规则，应放在 Ability 层。
- [ ] **HOW**:
  - `manage_user_role` 检查 `actor_id != target_id`。
  - 降级 admin 前检查 `count_admin_users() > 1`。
  - `manage_user_status` 检查不能禁用自己。
- [ ] **EXPECTED_RESULT**: 用户管理规则脱离 API 可测。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_users_contracts.py`

---

## Phase 4: Business Pipeline

### 4.1 AdminStatusPipeline

- [ ] **WHERE**: `backend/business/pipelines/admin_status_pipeline.py`
- [ ] **WHY**: status 是单一同步编排，不需要 Business Flow。
- [ ] **HOW**: 调用 health provider -> status ability -> 返回 DTO。
- [ ] **EXPECTED_RESULT**: API controller 只调用 pipeline。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_status_contracts.py`

### 4.2 AdminSettingsPipeline

- [ ] **WHERE**: `backend/business/pipelines/admin_settings_pipeline.py`
- [ ] **WHY**: settings inspect/test 是同步编排；审计副作用顺序由 Pipeline 统一管理。
- [ ] **HOW**:
  - inspect：调用 settings abilities。
  - test：先/后写 audit，调用 test ability，捕获内部错误并记录 failed audit。
- [ ] **EXPECTED_RESULT**: test LLM/Bark 的成功和失败都会产生审计记录。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_contracts.py`

### 4.3 AdminLogPipeline

- [ ] **WHERE**: `backend/business/pipelines/admin_log_pipeline.py`
- [ ] **WHY**: logs list/detail/export 是同步查询，不需要 Flow。
- [ ] **HOW**:
  - 调用 query/export abilities。
  - `export_audit` 先执行查询导出，再写 `admin.download_audit_log`；失败也记录 failed audit。
- [ ] **EXPECTED_RESULT**: 下载审计日志自身可追踪。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_logs_contracts.py`

### 4.4 AdminUserPipeline

- [ ] **WHERE**: `backend/business/pipelines/admin_user_pipeline.py`
- [ ] **WHY**: 用户管理是同步业务编排，Pipeline 足够；修改副作用需要审计。
- [ ] **HOW**:
  - list/detail 调用 user abilities。
  - update role/status 调用 ability 后写 audit；失败写 failed audit。
- [ ] **EXPECTED_RESULT**: role/status 修改约束和审计顺序稳定。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_users_contracts.py`

---

## Phase 5: API Controller

### 5.1 Admin auth dependency

- [ ] **WHERE**: `backend/api/admin/dependencies.py`
- [ ] **WHY**: `/api/admin/*` 的后端安全边界必须集中且可测。
- [ ] **HOW**:
  - 复用 `ResolveCurrentUserPipeline`。
  - 未登录 -> 401。
  - DB role 非 admin -> 403。
  - 禁止直接解 JWT payload 判断 role。
- [ ] **EXPECTED_RESULT**: role 修改后下一次请求立即按 DB 生效。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_auth.py`

### 5.2 Admin routers

- [ ] **WHERE**: `backend/api/admin/status.py`, `backend/api/admin/settings.py`, `backend/api/admin/logs.py`, `backend/api/admin/users.py`, `backend/api/admin/__init__.py`, `backend/main.py`
- [ ] **WHY**: API Controller 只负责协议输入输出、鉴权绑定、错误映射。
- [ ] **HOW**:
  - 每个 route 依赖 `require_admin_user`。
  - route 调用对应 `Admin*Pipeline`。
  - request/response schema 放在 API/model 层，不在 route 中写业务规则。
  - 不 import SQLAlchemy、Redis、MinIO、httpx、Infrastructure Adapter。
- [ ] **EXPECTED_RESULT**: `/api/admin/status|settings|logs|users` 契约可用。
- [ ] **VERIFY**:
  - `uv run pytest tests/admin`
  - `uv run pytest tests/test_architecture_imports.py`

---

## Phase 6: 前端集成

### 6.1 基础路由与 auth store

- [ ] **WHERE**: `frontend/src/router/index.ts`, `frontend/src/stores/auth.ts`, `frontend/src/api/auth.ts`, `frontend/src/App.vue`
- [ ] **WHY**: 前端只做体验边界；真正授权在后端。
- [ ] **HOW**:
  - `/admin/*` 路由使用 `meta: { requiresAuth: true, requiresAdmin: true }`。
  - `UserResponse` 新增 `role`。
  - `authStore.isAdmin` 来自 `/api/auth/me`。
  - navbar 仅 admin 显示“管理”。
- [ ] **EXPECTED_RESULT**: 非 admin 看不到入口，直访也会被前端重定向；后端仍返回 403。
- [ ] **VERIFY**: `npm run build`

### 6.2 Admin API client 与页面

- [ ] **WHERE**: `frontend/src/api/admin.ts`, `frontend/src/api/types.ts`, `frontend/src/views/admin/`
- [ ] **WHY**: 前端页面必须走 typed API wrapper，不在 page-local 写 axios。
- [ ] **HOW**:
  - 实现 status/settings/logs/users typed wrapper。
  - 创建 `AdminLayout.vue`, `StatusDashboard.vue`, `SettingsView.vue`, `LogsView.vue`, `UsersView.vue`。
  - Frontend synthetic health 卡片在浏览器本地计算，不要求后端返回 frontend service。
- [ ] **EXPECTED_RESULT**: 管理端四个页面可导航、可刷新、可展示空态/错误态/loading。
- [ ] **VERIFY**: `npm run build`

---

## Phase 7: Architecture Lint / Runtime Check / 全量验证

### 7.1 后端架构验证

- [ ] **WHERE**: `tests/test_architecture_imports.py`
- [ ] **WHY**: 防止 admin 新模块突破层边界。
- [ ] **HOW**: 跑 architecture import rules。
- [ ] **EXPECTED_RESULT**: 无跨层 import、无业务层 env 读取、无 API 直连 SDK/DB。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

### 7.2 后端行为验证

- [ ] **WHERE**: `tests/admin/`, `tests/infrastructure/db/`
- [ ] **WHY**: 保护公开 API、鉴权语义、审计副作用、敏感字段脱敏。
- [ ] **HOW**: 跑 admin 相关测试和 DB migration roundtrip。
- [ ] **EXPECTED_RESULT**: admin 后端契约全部通过。
- [ ] **VERIFY**:
  - `uv run pytest tests/admin`
  - `uv run pytest tests/infrastructure/db/test_alembic_roundtrip.py`

### 7.3 项目质量门禁

- [ ] **WHERE**: repo root
- [ ] **WHY**: 交付前必须符合 AGENTS.md 的质量循环。
- [ ] **HOW**:
  - `make lint`
  - 如安全则 `make fix`
  - `make lint`
  - `make format`
  - `make lint`
  - `make typecheck`
  - `make test`
  - `make build`
  - `make check`
- [ ] **EXPECTED_RESULT**: 能明确区分真实通过、placeholder target、已知无关失败。
- [ ] **VERIFY**: `make check`

### 7.4 本地集成验证

- [ ] **WHERE**: 完整本地环境（backend + frontend + PostgreSQL + Redis + MinIO）
- [ ] **WHY**: 管理端依赖真实 auth/DB/infra/log 文件路径。
- [ ] **HOW**:
  - 启动完整环境。
  - 注册普通用户。
  - 执行 admin bootstrap。
  - admin 登录访问 `/admin/status`, `/admin/settings`, `/admin/logs`, `/admin/users`。
  - 普通用户直访 `/api/admin/status/summary` 返回 403。
- [ ] **EXPECTED_RESULT**: 管理端真实可用，普通用户无法越权。
- [ ] **VERIFY**: 记录接口响应和页面 smoke 结果。

---

## Phase 8: 清理与收尾

### 8.1 文档同步

- [ ] **WHERE**: `docs/admin/admin-console-design.md`, `docs/backend-api.md`, `docs/development.md`
- [ ] **WHY**: 新 API、bootstrap、架构边界和验证命令需要对齐长期文档。
- [ ] **HOW**: 同步 `/api/admin/*` 契约、bootstrap 命令、admin role 授权规则、telemetry envelope。
- [ ] **EXPECTED_RESULT**: 后续 Agent 不会按旧 Flow/JWT-role/无 bootstrap 方案施工。
- [ ] **VERIFY**: `rg -n "admin_.*flow|JWT role claim 验证|user_management_provider|手动 SQL" docs | rg -v "docs/admin/admin-console-(design|implementation-checklist)\\.md"`

### 8.2 回滚记录

- [ ] **WHERE**: 本清单每个 Phase 的完成记录
- [ ] **WHY**: 每个阶段必须能独立回滚。
- [ ] **HOW**:
  - 记录新增/修改文件。
  - 记录 migration downgrade 步骤。
  - 记录 Provider Factory 新字段回滚影响。
  - 记录前端路由/API wrapper 回滚影响。
- [ ] **EXPECTED_RESULT**: 任一阶段失败时可以按文件和 migration 逆序回滚。
- [ ] **VERIFY**: 本清单对应 Phase 记录完整。

---

## 阶段依赖关系

```text
Phase 0 行为锚点
  -> Phase 1 Provider Interface / DTO
  -> Phase 2 Infrastructure Adapter / Factory / Migration
  -> Phase 3 Ability Atom
  -> Phase 4 Business Pipeline
  -> Phase 5 API Controller
  -> Phase 6 Frontend
  -> Phase 7 全量验证
  -> Phase 8 清理收尾
```

Phase 2-5 可以按模块小切片推进，但每个切片仍必须保持：测试锚点先于实现，Provider 先于 Adapter，Ability 先于 Pipeline，Pipeline 先于 API。
