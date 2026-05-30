# Admin Settings 在线编辑 — 架构设计

> **版本**: v1.0-draft
> **日期**: 2026-05-31
> **关联**: `docs/admin/admin-console-design.md` §3.2
> **架构约束**: `backend-architecture-orchestration`

## 1. 现状盘点

### 1.1 当前调用链

```
API: GET /api/admin/settings
  → AdminSettingsPipeline.get_all_settings()
    → inspect_all_settings(ability)
      → EnvSettingsInspectionAdapter.get_all_settings()  ← READ ONLY
        → Settings._env_file=".env" (Pydantic) → 只读加载
```

**缺口**: `EnvSettingsInspectionAdapter` 是只读的。前端要编辑只能改代码重启。

### 1.2 .env 字段分类

| 类别 | 字段 | 可编辑 | 敏感 | 需重启 |
|------|------|--------|------|--------|
| LLM | LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL | ✅ | - | ✅ |
| LLM | LLM_API_KEY | ✅ | 🔒 掩码 | ✅ |
| LLM | LLM_TIMEOUT_SECONDS | ✅ | - | ✅ |
| Bark | BARK_ENABLED, BARK_SERVER_URL, BARK_DEFAULT_GROUP | ✅ | - | ✅ |
| Bark | BARK_DEVICE_KEY | ✅ | 🔒 掩码 | ✅ |
| Infra | DATABASE_URL, REDIS_URL | ⚠️ 只读展示 | 🔒 | - |
| Infra | OBJECT_STORAGE_* | ⚠️ 只读展示 | 🔒 | - |
| Auth | AUTH_SECRET_KEY | ❌ 不可编辑 | 🔒 | - |
| 算法 | ASSOCIATION_*, FORECAST_*, RIDGE_* | ⚠️ 只读展示 | - | - |

**策略**: Infra/Auth/算法类只读展示（改错会宕机）；LLM/Bark 类可在线编辑 + 写回 .env。

### 1.3 关键约束

- `.env` 是当前设置的真相源，Pydantic `Settings` 通过 `env_file=".env"` 加载
- 写回 `.env` 后，**需要重启 backend** 才能生效（Pydantic Settings 是启动时一次性加载的）
- 写操作必须写 audit log
- 敏感字段（API Key、Password）只接收有值/无值两种状态；不返回明文，保存时可覆写或保留原值

---

## 2. 目标架构

### 2.1 调用链

```text
API Controller (settings.py)
  → AdminSettingsPipeline (扩展: update_settings / update_llm_config)
    → manage_settings ability (新增: 校验 + 写 audit)
      → EnvFileProvider (新增: 读写 .env)
        → EnvFileAdapter (新增: 文件行操作)
```

与现有 `SettingsInspectionProvider`（只读）**分离**：读走 inspection，写走 env_file，两者互不干扰。

### 2.2 五层映射

```
┌─ API ───────────────────────────────────────────┐
│ backend/api/admin/settings.py  (扩展 PUT/PATCH)  │
├─ Pipeline ───────────────────────────────────────┤
│ backend/business/pipelines/admin_settings_pipeline.py (扩展) │
├─ Ability ────────────────────────────────────────┤
│ backend/abilities/admin/manage_settings.py (新增) │
│ backend/abilities/admin/manage_llm_config.py (新增) │
├─ Provider ───────────────────────────────────────┤
│ backend/providers/settings_inspection_provider.py (保留,只读) │
│ backend/providers/env_file_provider.py (新增,读写) │
├─ Adapter ────────────────────────────────────────┤
│ backend/infrastructure/adapters/env_file_adapter.py (新增) │
└──────────────────────────────────────────────────┘
```

---

## 3. Provider Interface

### 3.1 EnvFileProvider (新增)

```python
class EnvFileProvider(Protocol):
    def read_env(self) -> dict[str, str]:
        """Read all key=value pairs from .env file as a dict."""

    def write_env(self, updates: dict[str, str | None]) -> dict[str, str]:
        """Write key=value pairs back to .env. None value = delete the line.
        Returns the full updated dict.
        Keys not listed in updates are preserved as-is."""

    def get_env_path(self) -> str:
        """Return the resolved .env file path for display/info."""
```

---

## 4. DTO

### 4.1 SettingsEditDTO (新增)

```python
@dataclass(frozen=True)
class SettingsEditDTO:
    """A single key=value edit to .env."""
    key: str
    value: str | None  # None = delete / keep masked
    is_sensitive: bool = False  # If True, None means "keep current value"
```

### 4.2 LlmConfigItemDTO (扩展 LLM 多模型)

```python
@dataclass(frozen=True)
class LlmConfigItemDTO:
    id: str
    name: str               # "GPT-4o", "Claude Opus 4"
    provider: str            # "openai" | "anthropic" | "deepseek" | "custom"
    base_url: str | None
    api_key_configured: bool  # 只返回状态
    model: str | None
    timeout_seconds: int
    is_active: bool           # 同一时间只有一个 active
    created_at: str | None

@dataclass(frozen=True)
class LlmConfigListDTO:
    configs: list[LlmConfigItemDTO]

@dataclass(frozen=True)
class LlmConfigSaveDTO:
    """Input DTO for saving/updating an LLM config."""
    name: str
    provider: str
    base_url: str | None
    api_key: str | None       # 明文输入（掩码后存储）
    model: str | None
    timeout_seconds: int
    is_active: bool

@dataclass(frozen=True)
class EnvSettingsUpdateDTO:
    """Batch update for .env settings."""
    updates: list[SettingsEditDTO]
```

---

## 5. Adapter

### 5.1 EnvFileAdapter

```
backend/infrastructure/adapters/env_file_adapter.py
```

- 构造时接收 `.env` 文件路径
- `read_env()`: 逐行解析 `KEY=VALUE`，跳过注释和空行
- `write_env(updates)`: 
  - 读入所有行，遍历 updates：
    - key 在文件中存在 → 替换 value（is_sensitive=True 且 value=None → 保留原行）
    - key 不存在 → 追加到文件末尾
    - value=None 且 is_sensitive=False → 删除该行
  - 原子写入：先写 `.env.tmp` 然后 `os.replace()` 原子 rename
  - 保留注释行和空行不变
- 所有 I/O 异常转换为 `InfrastructureError` 内部错误

### 5.2 敏感字段处理规则

| 字段 | 展示 | 编辑回写 |
|------|------|---------|
| LLM_API_KEY | `apiKeyConfigured: bool` | value="" → 清空；value="***keep***" → 保留；value="sk-xxx" → 覆写 |
| BARK_DEVICE_KEY | `deviceKeyConfigured: bool` | 同上 |
| AUTH_SECRET_KEY | 不展示，不可编辑 | - |
| DATABASE_URL | host:port 脱敏展示 | 只读 |

---

## 6. API 端点

```
获取可编辑设置（合并展示+可编辑标记）:
GET  /api/admin/settings              (现有, 扩展返回可编辑字段列表)

获取 LLM 模型配置列表:
GET  /api/admin/settings/llm-configs

保存/更新单个 LLM 模型配置:
PUT  /api/admin/settings/llm-configs/{config_id}

新增 LLM 模型配置:
POST /api/admin/settings/llm-configs

删除 LLM 模型配置:
DELETE /api/admin/settings/llm-configs/{config_id}

激活某个 LLM 模型:
POST /api/admin/settings/llm-configs/{config_id}/activate

更新 .env 设置（LLM / Bark）:
PUT  /api/admin/settings/env
  Body: {
    "updates": [
      {"key": "LLM_PROVIDER", "value": "openai"},
      {"key": "LLM_API_KEY", "value": "sk-xxx", "isSensitive": true},
      {"key": "BARK_ENABLED", "value": "true"}
    ]
  }
```

### 通用响应

```json
{"success": true, "data": {...}}
```

---

## 7. LLM 多模型存储

LLM 配置不存 `.env`（`.env` 只有单套 LLM_* 变量），存独立 JSON 文件 `data/llm-configs.json`。

```json
{
  "configs": [
    {
      "id": "llm-001",
      "name": "GPT-4o",
      "provider": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-****",
      "model": "gpt-4o",
      "timeout_seconds": 30,
      "is_active": true,
      "created_at": "2026-05-31T10:00:00Z"
    }
  ]
}
```

`is_active` 互斥：激活一个时自动取消其他。

---

## 8. 错误策略

| 场景 | 响应 |
|------|------|
| 编辑不可编辑字段 | 400 "field X is not editable" |
| 写 .env 失败 (权限) | 500 "Failed to write .env" |
| API Key 明文泄露检查 | adapter 层拦截，不返回明文 |
| 并发写冲突 | 乐观锁：原子 rename 覆盖 |
| 删除最后一个 LLM config | 400 "Cannot delete the last config" |
| 激活不存在的 config | 404 |

---

## 9. 安全约束

- 所有 `/api/admin/settings` 写操作需要 `require_admin_user`
- 写操作全部 emit audit log
- `.env` 路径从 Settings 获取，不允许 API 传入
- 只允许编辑白名单字段：`LLM_*`, `BARK_*`
- `.env` 备份：每次写入前 copy 到 `.env.backup`

---

## 10. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/providers/env_file_provider.py` | 🆕 | EnvFileProvider interface |
| `backend/providers/admin_dtos.py` | ✏️ 扩展 | +SettingsEditDTO, +LlmConfigItemDTO, +LlmConfigSaveDTO, +EnvSettingsUpdateDTO |
| `backend/infrastructure/adapters/env_file_adapter.py` | 🆕 | .env read/write + data/llm-configs.json read/write |
| `backend/abilities/admin/manage_settings.py` | 🆕 | 校验编辑白名单、敏感字段处理 |
| `backend/abilities/admin/manage_llm_config.py` | 🆕 | LLM config CRUD + 互斥激活 |
| `backend/business/pipelines/admin_settings_pipeline.py` | ✏️ 扩展 | +update_env, +llm_config CRUD, +audit |
| `backend/api/admin/settings.py` | ✏️ 扩展 | +PUT /env, +llm-configs CRUD |
| `backend/infrastructure/factories/provider_factory.py` | ✏️ 扩展 | 装配 EnvFileAdapter |
| `backend/providers/container.py` | ✏️ 扩展 | +env_file 字段 |
| `frontend/src/api/admin.ts` | ✏️ 扩展 | +llm config API, +env update API |
| `frontend/src/views/admin/SettingsView.vue` | ✏️ 重写 | LLM 多模型管理 UI + .env 编辑 |
