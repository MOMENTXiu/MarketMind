# MarketMind Admin Console — 设计文档

> **版本**: v1.0-draft
> **日期**: 2026-05-30
> **定位**: Ops Admin Console / 系统运维管理端（非业务管理后台）
> **第一版边界**: 只做"观察面"和"权限面"——看状态、看配置、看日志、管角色
> **后端架构约束**: 遵守 `backend-architecture-orchestration`。默认路径为 `API Controller -> Business Pipeline -> Ability Atom -> Provider Interface -> External Adapter`；只有多 Pipeline、状态机、异步生命周期、补偿/恢复等复杂场景才创建 Business Flow。

---

## 目录

1. [系统概述](#1-系统概述)
2. [当前状态盘点](#2-当前状态盘点)
3. [模块设计](#3-模块设计)
   - [3.1 运行状态看板](#31-运行状态看板-adminstatus)
   - [3.2 系统设置](#32-系统设置-adminsettings)
   - [3.3 系统日志](#33-系统日志-adminlogs)
   - [3.4 用户管理](#34-用户管理-adminusers)
4. [数据模型变更](#4-数据模型变更)
5. [后端架构设计](#5-后端架构设计)
6. [前端架构设计](#6-前端架构设计)
7. [安全模型](#7-安全模型)
8. [API 契约](#8-api-契约)

---

## 1. 系统概述

### 1.1 用途

MarketMind Admin Console 面向系统管理员和开发者，解决四个核心问题：

| 问题 | 对应模块 |
|---|---|
| 系统活没活？服务通不通？ | 运行状态看板 |
| 配置是否正确？LLM/Infra/Alert 怎么接？ | 系统设置 |
| 日志有没有异常？谁做了什么？ | 系统日志 |
| 用户和权限有没有乱？ | 用户管理 |

### 1.2 路由结构

```
/admin/status      — 运行状态看板（默认首页）
/admin/settings    — 系统设置
/admin/logs        — 系统日志
/admin/users       — 用户管理
```

### 1.3 MVP 优先级

**P0（第一版必须做）**:
- `/admin/status` — 全部服务状态 + latency + overall status
- `/admin/settings` — LLM / Infra / Bark 只读展示 + Bark test
- `/admin/logs` — event logs + audit logs + export
- `/admin/users` — 用户列表 + 修改 role

**P1（第二版）**:
- SSE 状态、任务状态看板、Artifact 管理
- 配置在线修改（非敏感字段）
- 用户禁用/启用

**P2（第三版）**:
- Alert 自动规则、Runtime log streaming
- Admin 操作审批

---

## 2. 当前状态盘点

### 2.1 已有能力（可直接复用）

| 能力 | 位置 | 状态 |
|---|---|---|
| Health probe (PG/Redis/MinIO/Backend) | `CompositeInfrastructureHealthAdapter` | ✅ 已实现，`GET /api/health/` 已暴露 |
| JWT Auth | `JwtAuthTokenAdapter` + `ResolveCurrentUserPipeline` | ✅ 已实现 |
| User directory (CRUD) | `PostgresUserDirectoryAdapter` | ✅ 已实现 |
| Telemetry (Debug/Audit/Error events) | `TelemetryProvider` + `ConsoleTelemetryAdapter` | ✅ 接口已定义，Console 适配器已在使用 |
| File telemetry | `FileTelemetryAdapter` | ✅ 已实现（JSONL），未启用 |
| LLM Provider | `LLMProvider` (Protocol) + Anthropic/OpenAI adapters | ✅ 已实现 |
| Frontend ServiceStatus 组件 | `ServiceStatus.vue` | ✅ 已实现，navbar 中轮询 `/api/health/` |
| Frontend auth store | `stores/auth.ts` (Pinia) | ✅ 已实现 |
| Frontend API client | `api/client.ts` (Axios + interceptors) | ✅ 已实现 |
| Frontend router guards | `router/index.ts` (`requiresAuth` meta) | ✅ 已实现 |

### 2.2 关键缺口

| 缺口 | 影响范围 | 优先级 |
|---|---|---|
| **UserRecord 无 `role` 字段** | 无法区分 user/admin | P0 |
| **无 `require_admin_user` 依赖** | 无法保护 admin API | P0 |
| **`AuthenticatedUserContext` 无 role** | DB 用户上下文不含角色，无法做服务端授权 | P0 |
| **Health probe 不含 LLM / Bark** | 状态看板不完整 | P0 |
| **无 Settings API** | 无法展示配置 | P0 |
| **Telemetry 当前用 Console（stdout）** | 日志无法查询/导出 | P0 |
| **无 Admin API routes** | `/api/admin/*` 不存在 | P0 |
| **无 Admin 前端路由/视图** | `/admin/*` 不存在 | P0 |
| **无 Bark alert 机制** | Alert 设置无后端支撑 | P1 |
| **无 Audit log 写入** | 管理操作没有审计记录 | P0 |

### 2.3 后端架构审查结论

按 `backend-architecture-orchestration` 审查，原 draft 有以下必须修正的问题：

| 问题 | 风险 | 修正 |
|---|---|---|
| 过早为 status/settings/logs/users 全部创建 Business Flow | Flow 只适合复杂生命周期；单一路径转发会制造空壳编排层 | P0 全部使用 `backend/business/pipelines/admin_*_pipeline.py`。只有后续任务状态看板、审批、runtime streaming 等复杂生命周期再引入 Flow |
| 施工顺序从 migration/provider wiring 开始 | 缺少行为锚点，不符合“未建立行为保护，不得迁移” | 先补 API/auth/settings/log/user 行为测试，再改模型和 Provider |
| admin 授权写成 JWT role claim 验证 | 角色变更后旧 token 可能继续拥有 admin 权限 | JWT 只证明身份；`ResolveCurrentUserPipeline` 必须查 DB，`require_admin_user` 只信 DB 返回的 `user_ctx.role` |
| FileTelemetry JSONL 与日志页面 schema 不一致 | 无法可靠筛选、分页、导出、审计 | 新增 `TelemetryEnvelopeDTO` / `AdminLogRecordDTO`，File adapter 写统一 envelope，查询 adapter 只读 envelope |
| 初始 admin 只写注释 | 没有可执行 bootstrap，Phase 1 无法验收 | Phase 0 增加 seed/CLI 或环境变量指定初始 admin email，并纳入验证 |
| UserDirectoryProvider 被直接扩成管理查询 | 普通认证 Provider 和 admin 查询/统计职责混杂 | 新增 `AdminUserProvider`，由 `PostgresAdminUserAdapter` 实现；认证继续使用 `UserDirectoryProvider` |
| LLM/Bark 配置检查可能放进业务层 | 违反 Settings -> Provider Factory -> Adapter | Settings 只能在 Provider Factory / Infrastructure Adapter 侧读取，业务层只调用 Provider |

### 2.4 Telemetry 现状详解

用户已埋了日志机制，核心接口和 DTO 已就位：

```
TelemetryProvider (Protocol)
├── emit_debug(DebugEvent) → TelemetryResult
├── emit_audit(AuditEvent) → TelemetryResult
├── emit_error(ErrorEvent) → TelemetryResult
├── start_span(name, context?) → SpanHandle
└── end_span(span, status?) → TelemetryResult
```

当前使用 `ConsoleTelemetryAdapter`（stdout），未使用 `FileTelemetryAdapter`（JSONL 文件）。

**Admin Console 需要的变更**:
- 新增统一日志 envelope，FileTelemetryAdapter 写入 `logs/telemetry/events.jsonl`
- 第一版保留 Console + File 双写，业务层仍只依赖 `TelemetryProvider`
- `JsonlLogQueryAdapter` 只读取 envelope，不解析任意历史 stdout
- 第二版再考虑 PostgreSQL `system_events` + `audit_logs` 表

第一版 envelope:

```python
@dataclass(frozen=True)
class TelemetryEnvelopeDTO:
    id: str
    kind: Literal["debug", "audit", "error", "span"]
    level: Literal["info", "warning", "error", "critical"]
    event_type: str
    message: str
    actor_user_id: str | None
    resource_type: str | None
    resource_id: str | None
    project_id: str | None
    job_id: str | None
    request_id: str | None
    trace_id: str | None
    created_at: str
    metadata: dict[str, Any]
```

---

## 3. 模块设计

### 3.1 运行状态看板 `/admin/status`

#### 3.1.1 用途

回答：当前系统各端和基础设施是否可用？延迟是否正常？

#### 3.1.2 监控对象

| 服务 | Category | 检查方式 | 当前状态 |
|---|---|---|---|
| Frontend | app | 前端本地 synthetic status（不由后端返回） | 🆕 需新增 |
| Python Backend | app | `GET /api/health/` 返回 200 + 版本号 + 启动时间 | ✅ 已有 |
| PostgreSQL | infra | `SELECT 1` | ✅ 已有 |
| Redis | infra | `PING` | ✅ 已有 |
| MinIO | infra | bucket exists + list | ✅ 已有 |
| LLM Provider | external | `SettingsInspectionProvider` 配置存在性检查 + 手动 test | 🆕 需新增 |
| Bark Alert | external | `SettingsInspectionProvider` 配置存在性检查（不自动发推送） | 🆕 需新增 |

#### 3.1.3 数据结构

```typescript
type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown'

interface ServiceHealth {
  key: string                    // e.g. "postgres"
  name: string                   // e.g. "PostgreSQL"
  category: 'app' | 'infra' | 'external'
  status: ServiceStatus
  latencyMs?: number
  checkedAt: string              // ISO 8601
  message?: string
  version?: string               // for backend
}
```

#### 3.1.4 后端接口

```
GET /api/admin/status/summary
```

Response:

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

#### 3.1.5 前端设计

- 卡片网格布局（app / infra / external 分组）
- 每个卡片：服务名、状态指示灯、延迟数值、最后检查时间
- 顶部 overall status banner
- 30s 自动刷新
- 点击服务卡片可展开详情（message/version）
- Frontend 卡片由浏览器本地计算，不进入 `/api/admin/status/summary` 的后端服务列表；后端 summary 只返回 backend/infra/external 可由服务端探测的对象。

---

### 3.2 系统设置 `/admin/settings`

#### 3.2.1 用途

回答：当前系统接入了哪些外部服务？关键配置是否正确？Alert 怎么发？

#### 3.2.2 设置分组

**第一版只做只读展示 + 测试连接**。不提供在线修改配置（防止把自己改挂）。

##### LLM 接入设置

```typescript
interface LlmSettings {
  provider: 'openai' | 'deepseek' | 'anthropic' | 'custom'
  baseUrl?: string
  model?: string
  apiKeyConfigured: boolean    // 只显示已配置/未配置，不返回原文
  timeoutSeconds?: number
  enabled: boolean
}
```

##### Docker Infra 接入设置

```typescript
interface InfraSettings {
  postgres: {
    host: string
    port: number
    database: string
    username: string
    passwordConfigured: boolean
  }
  redis: {
    host: string
    port: number
    database?: number
    passwordConfigured: boolean
  }
  minio: {
    endpoint: string
    bucket: string
    accessKeyConfigured: boolean
    secretKeyConfigured: boolean
    secure: boolean
  }
}
```

##### Alert 设置 (Bark)

```typescript
interface BarkAlertSettings {
  enabled: boolean
  serverUrl: string
  deviceKeyConfigured: boolean
  defaultGroup?: string
  alertLevels: Array<'error' | 'warning' | 'critical'>
}
```

#### 3.2.3 敏感字段处理规则

| 字段 | 展示方式 | 原因 |
|---|---|---|
| API Key | `"********abc"` (最后3位) | 避免泄露 |
| Password / Secret | `"已配置"` / `"未配置"` | 二进制判断 |
| Connection String | 只展示 host:port，隐藏 credentials | 最小暴露 |
| Device Key | `"已配置"` / `"未配置"` | 隐私 |

#### 3.2.4 后端接口

```
GET  /api/admin/settings           → 全部设置汇总
GET  /api/admin/settings/llm       → LLM 设置
POST /api/admin/settings/llm/test  → 测试 LLM 连接
GET  /api/admin/settings/infra     → Infra 设置
POST /api/admin/settings/infra/test → 测试 Infra 连接
GET  /api/admin/settings/alert     → Alert 设置
POST /api/admin/settings/alert/bark/test → 发送测试 Bark 推送
```

#### 3.2.5 配置来源

第一版：**环境变量只读映射**（`.env` / Docker env → Settings 对象 → API 响应）

- 真相源是环境变量
- Admin Console 只做展示和测试
- 修改配置需通过环境变量 + 重启
- 业务层不得读取环境变量；配置路径固定为 `Settings -> provider_factory.create_providers() -> Infrastructure Adapter`。
- Settings 展示由 `SettingsInspectionProvider` 提供，Ability/Pipeline 只拿 DTO，不 import `backend.core.config`。

#### 3.2.6 前端设计

- Tab 分组（LLM / Infra / Alert）
- 每个字段：label + 值（敏感字段脱敏）+ 复制按钮
- LLM Tab: provider、model、API key 状态、timeout、Test Connection 按钮
- Infra Tab: PG/Redis/MinIO 卡片，每个展示 host:port + 密码状态 + Test 按钮
- Alert Tab: Bark server URL、device key 状态、alert levels、Send Test 按钮

---

### 3.3 系统日志 `/admin/logs`

#### 3.3.1 用途

回答：系统发生了什么？谁做了什么？能不能下载日志排查？

#### 3.3.2 日志分类

##### Event Log（事件日志）

记录系统运行时事件：

- 用户登录/登出
- 项目创建/删除
- 文件上传
- 诊断任务启动/完成/失败
- Artifact 生成
- Alert 发送
- 配置测试

```typescript
interface SystemEventLog {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  eventType: string              // e.g. "user.login", "project.created"
  message: string
  actorUserId?: string
  projectId?: string
  jobId?: string
  requestId?: string
  traceId?: string
  createdAt: string               // ISO 8601
  metadata?: Record<string, unknown>
}
```

##### Audit Log（审计日志）

记录管理端敏感操作：

- 管理员登录
- 修改用户角色
- 修改设置
- 测试 Bark 连接
- 下载日志/Artifact
- 查看用户详情
- 禁用/启用用户

```typescript
interface AuditLog {
  id: string
  actorUserId: string
  action: string                  // e.g. "admin.modify_user_role"
  targetType: string              // e.g. "user", "setting"
  targetId?: string
  ip?: string
  userAgent?: string
  result: 'success' | 'failed'
  createdAt: string               // ISO 8601
  metadata?: Record<string, unknown>
}
```

##### Runtime Log（运行日志）

第一版**不做 runtime log streaming**（Docker logs 读取复杂）。
第二版再做。

#### 3.3.3 页面能力

第一版：
- 筛选：level / eventType / userId / projectId / jobId / 时间范围
- 查看详情（展开完整 metadata）
- 下载导出 JSON / CSV
- 分页

#### 3.3.4 后端接口

```
GET /api/admin/logs/events          → 事件日志列表（分页+筛选）
GET /api/admin/logs/events/{id}     → 单条事件详情
GET /api/admin/logs/events/export   → 导出事件日志（JSON/CSV）
GET /api/admin/logs/audit           → 审计日志列表
GET /api/admin/logs/audit/{id}      → 单条审计详情
GET /api/admin/logs/audit/export    → 导出审计日志（JSON/CSV）
```

**注意**: `GET /api/admin/logs/audit/export` 自身需要写一条 audit log:
```
admin_download_audit_log
```

#### 3.3.5 存储方案

第一版：**从 FileTelemetryAdapter 的 JSONL 文件读取**

- 在 `create_providers()` 中将 telemetry 切换到 `FileTelemetryAdapter`
- 或者同时使用 Console + File（双写）
- LogQueryAbility 读取 `logs/telemetry/events.jsonl` 按条件过滤

第二版考虑：PostgreSQL `system_events` + `audit_logs` 表。

#### 3.3.6 前端设计

- 左右分栏：左侧筛选面板，右侧日志列表
- 筛选面板：level 多选、eventType 下拉、user/project/job 搜索框、日期范围选择器
- 日志列表：表格形式，列 = 时间、级别、类型、消息、操作人
- 点击行展开详情 modal
- 顶部导出按钮（JSON / CSV）
- Tab 切换 Event Log / Audit Log

---

### 3.4 用户管理 `/admin/users`

#### 3.4.1 用途

回答：系统有哪些用户？谁是管理员？谁能访问用户端？谁能访问管理端？

#### 3.4.2 角色模型

第一版简单二元角色：

```typescript
type UserRole = 'user' | 'admin'
```

- `user`: 可访问用户端（`/projects`, `/data-processing` 等）
- `admin`: 可访问用户端 + 管理端（`/admin/*`）

对应权限：
- 用户端 API：`require_current_user`（现有）
- 管理端 API：`require_admin_user`（🆕 需新增）

#### 3.4.3 数据结构

```typescript
interface AdminUserListItem {
  id: string
  email: string
  displayName?: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  projectCount: number
  lastLoginAt?: string
  createdAt: string
}
```

#### 3.4.4 支持的操作

**第一版**:
- 查看用户列表
- 查看用户详情（含项目列表）
- 修改角色：user ↔ admin
- 禁用/启用用户

**第一版不做**:
- ~~删除用户~~（风险高）
- ~~模拟登录~~（安全风险）
- ~~重置密码~~（需要邮件服务）
- ~~编辑用户邮箱~~（需要验证）

#### 3.4.5 后端接口

```
GET   /api/admin/users                    → 用户列表
GET   /api/admin/users/{user_id}          → 用户详情
PATCH /api/admin/users/{user_id}/role     → 修改角色
PATCH /api/admin/users/{user_id}/status   → 启用/禁用
```

#### 3.4.6 安全约束

- 不能修改自己的角色（防止 admin 把自己降级锁死）
- 至少保留一个 admin（防止全部降级）
- 修改角色写 audit log
- 修改 status 写 audit log

#### 3.4.7 前端设计

- 用户列表表格：email、display name、role badge、status badge、project count、last login、created at
- 搜索：按 email / display name
- 操作列：编辑角色（下拉选择）、启用/禁用（开关）
- 点击用户行 → 用户详情抽屉：基本信息 + 项目列表 + 最近事件
- 修改操作需二次确认弹窗

---

## 4. 数据模型变更

### 4.1 users 表新增 role 字段

**Alembic migration**:

```python
# 0004_add_user_role.py

def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="user",
        ),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # 将第一个用户（或指定用户）设为 admin
    # op.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@example.com'")

def downgrade():
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
```

### 4.2 UserRecord 模型更新

```python
class UserRecord(Base):
    # ... existing fields ...
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="user", server_default="user", index=True
    )
```

### 4.3 UserIdentityDTO 更新

```python
@dataclass(frozen=True)
class UserIdentityDTO:
    # ... existing fields ...
    role: str = "user"
```

### 4.4 AuthenticatedUserContext 更新

```python
@dataclass(frozen=True)
class AuthenticatedUserContext:
    user_id: str
    email: str
    display_name: str | None = None
    role: str = "user"                    # 🆕
```

### 4.5 JWT Claims 更新

JWT 可以包含 `role` claim 作为前端展示缓存，但后端授权不得信任 token 内 role。`require_admin_user` 必须走 `ResolveCurrentUserPipeline` 查 DB 后检查 `AuthenticatedUserContext.role`。

```python
payload = {
    "sub": user.id,
    "email": user.email,
    "display_name": user.display_name,
    "role": user.role,                    # 🆕
    "iat": now,
    "exp": now + timedelta(minutes=...),
    "aud": ...,
    "iss": ...,
}
```

如果实现时选择不把 role 写入 JWT，也可以；前端以 `/api/auth/me` 返回的 DB role 为准。

### 4.6 初始 admin bootstrap

必须提供可执行 bootstrap，不能只依赖 migration 注释：

- 推荐新增一次性脚本 `backend/scripts/bootstrap_admin.py`，读取 `ADMIN_BOOTSTRAP_EMAIL`，将已存在用户提升为 admin。
- 脚本只做本地/部署初始化，不作为运行时 API。
- 验证：创建普通用户 -> 执行 bootstrap -> `/api/auth/me` 返回 `role="admin"` -> `/api/admin/status/summary` 可访问。

---

## 5. 后端架构设计

### 5.1 五层架构映射

严格遵守现有 `backend-architecture-orchestration` 五层架构：

```
┌──────────────────────────────────────────────┐
│ API Layer                                    │
│ backend/api/admin/                           │
│ ├── __init__.py                              │
│ ├── status.py          GET  /api/admin/status/summary
│ ├── settings.py        GET  /api/admin/settings/*
│ ├── logs.py            GET  /api/admin/logs/*
│ └── users.py           GET/PATCH /api/admin/users/*
├──────────────────────────────────────────────┤
│ Business Pipeline / Orchestration           │
│ backend/business/pipelines/                  │
│ ├── admin_status_pipeline.py                 │
│ ├── admin_settings_pipeline.py               │
│ ├── admin_log_pipeline.py                    │
│ └── admin_user_pipeline.py                   │
├──────────────────────────────────────────────┤
│ Ability Layer                                │
│ backend/abilities/admin/                     │
│ ├── __init__.py                              │
│ ├── aggregate_service_status.py              │
│ ├── inspect_settings.py                      │
│ ├── test_llm_connection.py                   │
│ ├── test_alert_connection.py                 │
│ ├── query_logs.py                            │
│ ├── export_logs.py                           │
│ ├── list_admin_users.py                      │
│ ├── get_admin_user_detail.py                 │
│ ├── manage_user_role.py                      │
│ └── manage_user_status.py                    │
├──────────────────────────────────────────────┤
│ Provider Boundary                            │
│ backend/providers/                           │
│ ├── infrastructure_health_provider.py        │
│ ├── settings_inspection_provider.py    (🆕)  │
│ ├── alert_provider.py                  (🆕)  │
│ ├── log_query_provider.py              (🆕)  │
│ └── admin_user_provider.py             (🆕)  │
├──────────────────────────────────────────────┤
│ Infrastructure Layer                         │
│ backend/infrastructure/adapters/             │
│ ├── composite_infrastructure_health_adapter.py│
│ ├── env_settings_inspection_adapter.py (🆕)  │
│ ├── bark_alert_adapter.py             (🆕)  │
│ ├── jsonl_log_query_adapter.py        (🆕)  │
│ ├── postgres_user_directory_adapter.py (扩展: +role for auth DTO)│
│ └── postgres_admin_user_adapter.py     (🆕 admin list/count/role/status)│
├──────────────────────────────────────────────┤
│ Data Models                                  │
│ backend/infrastructure/db/models/            │
│ └── user.py                            (扩展: +role)│
└──────────────────────────────────────────────┘
```

### 5.2 Provider Container 扩展

```python
@dataclass(frozen=True)
class ProvidersContainer:
    # ... existing fields ...

    # 🆕 Admin Console providers
    settings_inspection: SettingsInspectionProvider | None = None
    alert: AlertProvider | None = None
    log_query: LogQueryProvider | None = None
    admin_users: AdminUserProvider | None = None
```

### 5.3 Admin Auth Dependency

```python
# backend/api/admin/dependencies.py

async def require_admin_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    providers: ProvidersContainer = Depends(get_providers),
) -> AuthenticatedUserContext:
    """Require valid JWT + admin role."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    pipeline = ResolveCurrentUserPipeline(providers)
    user_ctx = pipeline.execute(credentials.credentials)

    # user_ctx.role comes from DB lookup, not from trusting a JWT role claim.
    if user_ctx.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_ctx
```

### 5.4 关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 日志存储 | File JSONL (第一版) | Telemetry 已有 DebugEvent/AuditEvent DTO + FileTelemetryAdapter，最小改动 |
| 配置来源 | 环境变量只读 | 安全，简单，防止在线改挂系统 |
| 角色模型 | 二元 (user/admin) | 满足当前需求，不过度设计 |
| LLM health | 只检查配置存在 + 可选 ping | 避免每次 health check 花钱调大模型 |
| Bark health | 只检查配置存在 + 手动测试 | 避免每次 health check 发手机推送 |
| 前端 | 嵌入现有 SPA，新增 `/admin/*` 路由 | 不做独立前端项目 |

### 5.5 Import Rule 与错误策略

- `backend/api/admin/*` 只 import request/response schema、Admin Pipeline、`require_admin_user`、FastAPI 依赖；禁止 import SQLAlchemy/Redis/MinIO/httpx/adapter。
- `backend/business/pipelines/admin_*_pipeline.py` 只编排 Ability 与 Provider Interface；禁止 import FastAPI、Settings、Infrastructure Adapter、SDK。
- `backend/abilities/admin/*` 只做最小业务动作；禁止读取 env、创建 adapter、import infrastructure。
- `backend/providers/*` 只定义 Protocol/DTO；禁止 import infrastructure 或业务层。
- `backend/infrastructure/adapters/*` 捕获 DB/HTTP/SDK 异常并转换为内部错误，API Controller 只通过 `map_internal_error` 或 admin 专用错误映射返回公开错误。
- Architecture Lint 必须扩展覆盖 admin 新模块：禁止业务层直接读取 env，禁止 Provider 反向 import Adapter，禁止 API 直连 DB/SDK。

---

## 6. 前端架构设计

### 6.1 路由新增

```typescript
// frontend/src/router/index.ts

// Admin Console routes
{
  path: '/admin',
  component: () => import('@/views/admin/AdminLayout.vue'),
  meta: { requiresAuth: true, requiresAdmin: true },
  children: [
    {
      path: '',
      redirect: '/admin/status'
    },
    {
      path: 'status',
      name: 'admin-status',
      component: () => import('@/views/admin/StatusDashboard.vue'),
    },
    {
      path: 'settings',
      name: 'admin-settings',
      component: () => import('@/views/admin/SettingsView.vue'),
    },
    {
      path: 'logs',
      name: 'admin-logs',
      component: () => import('@/views/admin/LogsView.vue'),
    },
    {
      path: 'users',
      name: 'admin-users',
      component: () => import('@/views/admin/UsersView.vue'),
    },
  ]
}
```

### 6.2 路由守卫扩展

```typescript
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 🆕 Admin route guard
  if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') {
    next({ path: '/projects' })  // redirect non-admin away
    return
  }

  next()
})
```

### 6.3 组件树

```
AdminLayout.vue
├── AdminSidebar.vue          — 侧边导航
│   ├── Status Icon
│   ├── Settings Icon
│   ├── Logs Icon
│   └── Users Icon
├── AdminHeader.vue           — 顶部栏（面包屑 + 用户）
└── <RouterView>
    ├── StatusDashboard.vue
    │   ├── OverallBanner.vue
    │   └── ServiceCard.vue (x7)
    ├── SettingsView.vue
    │   ├── LlmSettingsTab.vue
    │   ├── InfraSettingsTab.vue
    │   └── AlertSettingsTab.vue
    ├── LogsView.vue
    │   ├── LogFilterPanel.vue
    │   ├── LogTable.vue
    │   └── LogDetailModal.vue
    └── UsersView.vue
        ├── UserTable.vue
        └── UserDetailDrawer.vue
```

### 6.4 API Client 新增

```typescript
// frontend/src/api/admin.ts

import { apiClient, requestDirect, unwrapApiEnvelope } from './client'

// Status
export function getAdminStatusSummary(): Promise<AdminStatusSummary> { ... }

// Settings
export function getSettings(): Promise<AllSettings> { ... }
export function testLlmConnection(): Promise<TestResult> { ... }
export function testBarkAlert(): Promise<TestResult> { ... }

// Logs
export function getEventLogs(params: LogQueryParams): Promise<PaginatedLogs> { ... }
export function getAuditLogs(params: LogQueryParams): Promise<PaginatedLogs> { ... }
export function exportEventLogs(format: 'json' | 'csv'): Promise<Blob> { ... }
export function exportAuditLogs(format: 'json' | 'csv'): Promise<Blob> { ... }

// Users
export function getAdminUsers(): Promise<AdminUserListItem[]> { ... }
export function getUserDetail(userId: string): Promise<AdminUserDetail> { ... }
export function updateUserRole(userId: string, role: string): Promise<void> { ... }
export function updateUserStatus(userId: string, status: string): Promise<void> { ... }
```

### 6.5 Auth Store 扩展

`UserResponse` 需要新增 `role` 字段：

```typescript
export interface UserResponse {
  id: string
  email: string
  display_name: string | null
  status: string
  role: 'user' | 'admin'        // 🆕
}
```

`useAuthStore` 新增 computed:

```typescript
const isAdmin = computed(() => user.value?.role === 'admin')
```

### 6.6 Navbar 扩展

在现有 navbar 中，admin 用户看到额外的 "管理" 入口：

```html
<RouterLink
  v-if="authStore.isAdmin"
  to="/admin"
  class="nav-item"
  :class="{ active: isAdminActive }"
>
  管理
</RouterLink>
```

---

## 7. 安全模型

### 7.1 认证与授权

```
请求 → JWT 验证 → 用户查找 → 角色检查 → 业务逻辑
                                 ↓ (role != 'admin')
                              403 Forbidden
```

### 7.2 安全约束清单

| 约束 | 实施位置 | 方式 |
|---|---|---|
| `/api/admin/*` 全部需要 admin role | 后端 `require_admin_user` dependency | JWT 验证身份 + DB role 授权 |
| `/admin/*` 前端路由保护 | 前端 router guard | `requiresAdmin` meta |
| 敏感配置不返回明文 | `EnvSettingsInspectionAdapter` | 过滤/脱敏 |
| 管理操作写 audit log | Business Pipeline 层 | `telemetry.emit_audit()` |
| 不能修改自己的角色 | `manage_user_role` ability | 检查 `actor_id != target_id` |
| 至少保留一个 admin | `manage_user_role` ability | COUNT admin users > 1 |
| 下载审计日志自身写审计 | `admin_log_pipeline` | `emit_audit("admin.download_audit_log")` |
| 前端只做路由隐藏 | 前端 router guard | 后端是真正的安全边界 |

### 7.3 威胁模型

| 威胁 | 缓解措施 |
|---|---|
| 普通用户直接调用 `/api/admin/*` | `require_admin_user` 依赖 → 403 |
| Admin 查看/下载敏感日志 | 审计所有日志读取操作 |
| Admin 把自己降级锁死 | 不允许修改自己角色 + 至少保留一个 admin |
| API Key 泄露给前端 | `apiKeyConfigured: boolean` 不返回原文 |
| role 变更后旧 token 继续持权 | 授权以 DB role 为准，旧 token 只证明身份 |
| 暴力破解 admin 密码 | 复用现有 rate limit（后续可加） |

---

## 8. API 契约

### 8.1 通用响应格式

```json
{
  "success": true,
  "data": { ... }
}
```

错误响应：

```json
{
  "detail": "Admin access required"
}
```

### 8.2 完整 API 列表

```
# Status
GET  /api/admin/status/summary

# Settings
GET  /api/admin/settings
GET  /api/admin/settings/llm
POST /api/admin/settings/llm/test
GET  /api/admin/settings/infra
POST /api/admin/settings/infra/test
GET  /api/admin/settings/alert
POST /api/admin/settings/alert/bark/test

# Logs
GET  /api/admin/logs/events
GET  /api/admin/logs/events/{event_id}
GET  /api/admin/logs/events/export
GET  /api/admin/logs/audit
GET  /api/admin/logs/audit/{audit_id}
GET  /api/admin/logs/audit/export

# Users
GET   /api/admin/users
GET   /api/admin/users/{user_id}
PATCH /api/admin/users/{user_id}/role
PATCH /api/admin/users/{user_id}/status
```

### 8.3 测试用例预期

| 场景 | 预期 |
|---|---|
| 未登录访问 `/api/admin/status/summary` | 401 |
| 普通 user 访问 `/api/admin/status/summary` | 403 |
| Admin 访问 `/api/admin/status/summary` | 200 + 服务状态数据 |
| `GET /api/admin/settings/llm` | 200, `apiKeyConfigured: true/false`, 无明文 key |
| `POST /api/admin/settings/alert/bark/test` | 200 + test result, 写 audit log |
| `GET /api/admin/logs/audit/export` | 200 + JSON/CSV, 写 audit log |
| Admin 修改自己 role | 400 / 422 |
| 最后一个 admin 被降级 | 400 / 422 |
| 修改 user role | 200, 写 audit log |

---

## 附录 A: 文件变更清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `alembic/versions/0004_add_user_role.py` | 🆕 | Migration: users.role |
| `backend/infrastructure/db/models/user.py` | ✏️ 扩展 | +role field |
| `backend/providers/auth_dtos.py` | ✏️ 扩展 | UserIdentityDTO +role, AuthenticatedUserContext +role |
| `backend/providers/container.py` | ✏️ 扩展 | +settings_inspection, +alert, +log_query |
| `backend/providers/infrastructure_health_provider.py` | 复用 | backend/PG/Redis/MinIO health provider |
| `backend/providers/settings_inspection_provider.py` | 🆕 | Settings provider interface |
| `backend/providers/alert_provider.py` | 🆕 | Alert provider interface |
| `backend/providers/log_query_provider.py` | 🆕 | Log query provider interface |
| `backend/providers/admin_user_provider.py` | 🆕 | Admin user list/count/role/status provider interface |
| `backend/infrastructure/adapters/composite_infrastructure_health_adapter.py` | 复用/轻量扩展 | backend/PG/Redis/MinIO probes；LLM/Bark 配置状态走 SettingsInspectionProvider |
| `backend/infrastructure/adapters/env_settings_inspection_adapter.py` | 🆕 | Env vars → settings DTO |
| `backend/infrastructure/adapters/bark_alert_adapter.py` | 🆕 | Bark push adapter |
| `backend/infrastructure/adapters/jsonl_log_query_adapter.py` | 🆕 | JSONL file reader/query |
| `backend/infrastructure/adapters/postgres_user_directory_adapter.py` | ✏️ 扩展 | +role read for auth DTO |
| `backend/infrastructure/adapters/postgres_admin_user_adapter.py` | 🆕 | Admin user list/count/role/status adapter |
| `backend/infrastructure/adapters/jwt_auth_token_adapter.py` | ✏️ 扩展 | +role in claims |
| `backend/infrastructure/factories/provider_factory.py` | ✏️ 扩展 | Wire new adapters |
| `backend/abilities/admin/` | 🆕 目录 | Admin abilities |
| `backend/business/pipelines/admin_status_pipeline.py` | 🆕 | Status orchestration |
| `backend/business/pipelines/admin_settings_pipeline.py` | 🆕 | Settings orchestration |
| `backend/business/pipelines/admin_log_pipeline.py` | 🆕 | Log orchestration |
| `backend/business/pipelines/admin_user_pipeline.py` | 🆕 | User management orchestration |
| `backend/scripts/bootstrap_admin.py` | 🆕 | One-shot initial admin bootstrap |
| `backend/api/admin/` | 🆕 目录 | Admin API routes |
| `backend/api/admin/dependencies.py` | 🆕 | require_admin_user |
| `backend/api/auth_dependencies.py` | ✏️ 扩展 | (或直接在 admin/dependencies.py) |
| `backend/main.py` | ✏️ 扩展 | Register admin router |
| `frontend/src/router/index.ts` | ✏️ 扩展 | +/admin/* routes |
| `frontend/src/views/admin/` | 🆕 目录 | Admin views |
| `frontend/src/api/admin.ts` | 🆕 | Admin API client |
| `frontend/src/api/auth.ts` | ✏️ 扩展 | UserResponse +role |
| `frontend/src/stores/auth.ts` | ✏️ 扩展 | +isAdmin computed |
| `frontend/src/api/types.ts` | ✏️ 扩展 | Admin types |
| `frontend/src/App.vue` | ✏️ 扩展 | +admin nav link |
| `tests/` | 🆕 | Admin auth tests, admin API tests |

## 附录 B: 与现有架构文档的关系

- `docs/architecture/architecture-change.md` — 五层架构总览
- `docs/architecture/user-system-auth-design.md` — 用户认证设计
- `docs/architecture/user-system-auth-checklist.md` — 用户认证施工清单
- `docs/backend-api.md` — 后端 API 总览

本设计文档在上述基础上增量设计，不推翻现有架构。
