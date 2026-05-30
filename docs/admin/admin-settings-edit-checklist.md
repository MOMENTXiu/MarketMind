# Admin Settings 在线编辑 — 施工清单

> **版本**: v1.0
> **日期**: 2026-05-31
> **对应设计**: `docs/admin/admin-settings-edit-design.md`
> **架构约束**: `backend-architecture-orchestration`

---

## 审查要点

| # | 要点 | 处理方式 |
|---|------|---------|
| 1 | 读/写分离 | EnvFileProvider (写) 与 SettingsInspectionProvider (读) 独立 |
| 2 | .env 编辑白名单 | 只允许 LLM_* 和 BARK_* 字段可写 |
| 3 | 敏感字段不回传明文 | apiKeyConfigured: bool, 编辑时 none=保留 |
| 4 | LLM 多模型存储 | data/llm-configs.json，不在 .env 里 |
| 5 | 原子写入 | .env.tmp → os.replace() |
| 6 | 重启提醒 | .env 修改后提示重启 |

---

## Phase 0: 测试锚点

### 0.1 Settings 编辑安全测试

- [ ] **WHERE**: `tests/admin/test_admin_settings_edit.py`
- [ ] **WHY**: .env 编辑是最危险的 admin 操作，必须先保护。
- [ ] **HOW**: 覆盖编辑白名单、敏感字段不回传、未知 key 拒绝、admin-only 鉴权。
- [ ] **EXPECTED_RESULT**: 401/403/400/200 覆盖完善。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_edit.py`

### 0.2 LLM Config CRUD 测试

- [ ] **WHERE**: `tests/admin/test_admin_llm_config.py`
- [ ] **WHY**: 多模型管理的互斥激活逻辑需要验证。
- [ ] **HOW**: 覆盖 list/create/update/delete/activate，验证只有一个 active。
- [ ] **EXPECTED_RESULT**: CRUD 契约 + 互斥逻辑通过。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_llm_config.py`

---

## Phase 1: Provider Interface & DTO

### 1.1 DTO 扩展

- [ ] **WHERE**: `backend/providers/admin_dtos.py`
- [ ] **WHY**: SettingsEditDTO, LlmConfigItemDTO, LlmConfigSaveDTO, LlmConfigListDTO, EnvSettingsUpdateDTO
- [ ] **HOW**: 在现有 DTO 文件末尾追加新 dataclass。
- [ ] **EXPECTED_RESULT**: 所有新 DTO 可编译。
- [ ] **VERIFY**: `uv run python -m compileall backend/providers`

### 1.2 EnvFileProvider

- [ ] **WHERE**: `backend/providers/env_file_provider.py`
- [ ] **WHY**: .env 读写在业务层需要通过 Provider Interface。
- [ ] **HOW**: read_env() / write_env() / get_env_path()
- [ ] **EXPECTED_RESULT**: Provider 签名只使用内置类型和 DTO。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

### 1.3 ProvidersContainer 扩展

- [ ] **WHERE**: `backend/providers/container.py`
- [ ] **WHY**: 新 Provider 需要在容器中声明。
- [ ] **HOW**: 新增 `env_file: EnvFileProvider | None = None`
- [ ] **EXPECTED_RESULT**: container.py import 和字段通过 lint。
- [ ] **VERIFY**: `make lint`

---

## Phase 2: Infrastructure Adapter

### 2.1 EnvFileAdapter

- [ ] **WHERE**: `backend/infrastructure/adapters/env_file_adapter.py`
- [ ] **WHY**: .env 文件 I/O + data/llm-configs.json I/O 属于 Infrastructure。
- [ ] **HOW**:
  - 构造: `__init__(env_path: str, llm_config_path: str = "data/llm-configs.json")`
  - read_env(): 逐行解析 KEY=VALUE 为 dict
  - write_env(updates): 白名单过滤 → 原子写入 .env.tmp → os.replace()
  - llm_config CRUD: list/get/save/delete/activate (JSON file)
  - 敏感字段处理: 写时检查 is_sensitive 标志
  - 所有异常 → InfrastructureError
- [ ] **EXPECTED_RESULT**: .env 读写 + llm-configs.json CRUD 通过 contract test。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_edit.py`

### 2.2 Provider Factory 装配

- [ ] **WHERE**: `backend/infrastructure/factories/provider_factory.py`
- [ ] **WHY**: EnvFileAdapter 只能由 Provider Factory 根据 Settings 创建。
- [ ] **HOW**: 
  - 从 settings 取 .env 路径
  - 创建 EnvFileAdapter 并注入
- [ ] **EXPECTED_RESULT**: env_file provider 在生产/测试环境都可切换。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

---

## Phase 3: Ability Atoms

### 3.1 manage_settings

- [ ] **WHERE**: `backend/abilities/admin/manage_settings.py`
- [ ] **WHY**: 白名单校验 + 敏感字段规则必须放在 Ability 层。
- [ ] **HOW**:
  - `EDITABLE_KEYS = frozenset({...})` (LLM_* + BARK_*)
  - 校验 update key 在白名单内
  - 敏感字段 value=None 时保留原值不修改
  - 返回成功/失败 + 变更摘要
- [ ] **EXPECTED_RESULT**: 非法 key 被拒绝，敏感字段语义正确。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_settings_edit.py`

### 3.2 manage_llm_config

- [ ] **WHERE**: `backend/abilities/admin/manage_llm_config.py`
- [ ] **WHY**: 多模型管理 + 互斥激活逻辑。
- [ ] **HOW**:
  - CRUD 调用 EnvFileProvider 的 JSON 操作方法
  - activate 设置 is_active=True，同时将其他的设为 False
  - 不允许删除最后一个 config
  - api_key 不在返回中暴露明文
- [ ] **EXPECTED_RESULT**: CRUD 合法，互斥激活正确。
- [ ] **VERIFY**: `uv run pytest tests/admin/test_admin_llm_config.py`

---

## Phase 4: Business Pipeline

### 4.1 AdminSettingsPipeline 扩展

- [ ] **WHERE**: `backend/business/pipelines/admin_settings_pipeline.py`
- [ ] **WHY**: 编排 settings 编辑流程，统一写 audit log。
- [ ] **HOW**:
  - `update_env(actor_id, dto)`: 调 manage_settings → 调 env_file.write → emit audit
  - `list_llm_configs()`: 调 manage_llm_config → 返回 list
  - `save_llm_config(actor_id, dto)`: 调 manage_llm_config → emit audit
  - `delete_llm_config(actor_id, config_id)`: 同上
  - `activate_llm_config(actor_id, config_id)`: 同上
- [ ] **EXPECTED_RESULT**: 所有写操作产生 audit 记录。
- [ ] **VERIFY**: `uv run pytest tests/admin/`

---

## Phase 5: API Controller

### 5.1 settings.py 扩展

- [ ] **WHERE**: `backend/api/admin/settings.py`
- [ ] **WHY**: 暴露新的 REST 端点。
- [ ] **HOW**:
  - `PUT /api/admin/settings/env` → update_env
  - `GET /api/admin/settings/llm-configs` → list
  - `POST /api/admin/settings/llm-configs` → create
  - `PUT /api/admin/settings/llm-configs/{id}` → update
  - `DELETE /api/admin/settings/llm-configs/{id}` → delete
  - `POST /api/admin/settings/llm-configs/{id}/activate` → activate
  - 所有端点依赖 `require_admin_user`
- [ ] **EXPECTED_RESULT**: REST 契约完整。
- [ ] **VERIFY**: `uv run pytest tests/admin/`

---

## Phase 6: Frontend

### 6.1 API Client 扩展

- [ ] **WHERE**: `frontend/src/api/admin.ts`
- [ ] **WHY**: 前端调用必须走 typed wrapper。
- [ ] **HOW**: 新增 env update / llm config CRUD 函数和类型。
- [ ] **EXPECTED_RESULT**: TypeScript 编译通过。
- [ ] **VERIFY**: `npm run build`

### 6.2 SettingsView 重写 LLM Tab

- [ ] **WHERE**: `frontend/src/views/admin/SettingsView.vue`
- [ ] **WHY**: 现在 LLM Tab 只是只读展示 + 测试按钮。
- [ ] **HOW**:
  - 显示已配置模型列表（卡片式，标注 active）
  - 新增/编辑模型表单（name/provider/base_url/api_key/model）
  - 激活按钮 (active toggle)
  - 删除按钮（需确认，最后一个不可删）
  - .env 设置编辑区（LLM 运行时配置 + Bark 配置）
  - 保存按钮 + 成功/失败提示 + 重启提醒
- [ ] **EXPECTED_RESULT**: LLM 多模型可管理，.env 设置可编辑保存。
- [ ] **VERIFY**: `npm run build`

---

## Phase 7: Architecture Lint / 全量验证

### 7.1 架构验证

- [ ] **WHERE**: `tests/test_architecture_imports.py`
- [ ] **WHY**: EnvFileAdapter 不能反向 import 业务层。
- [ ] **HOW**: 跑 architecture import rules。
- [ ] **EXPECTED_RESULT**: 无跨层 import 违规。
- [ ] **VERIFY**: `uv run pytest tests/test_architecture_imports.py`

### 7.2 全量验证

- [ ] **WHERE**: repo root
- [ ] **WHY**: 交付前质量门禁。
- [ ] **HOW**: `make check`
- [ ] **EXPECTED_RESULT**: lint + test + build 全过。
- [ ] **VERIFY**: `make check`

---

## 阶段依赖

```text
Phase 0 测试锚点
  → Phase 1 Provider Interface / DTO
  → Phase 2 Infrastructure Adapter / Factory
  → Phase 3 Ability Atom
  → Phase 4 Business Pipeline
  → Phase 5 API Controller
  → Phase 6 Frontend
  → Phase 7 全量验证
```

---

## 白名单字段

```python
EDITABLE_KEYS = frozenset({
    "LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL",
    "LLM_API_KEY", "LLM_TIMEOUT_SECONDS",
    "BARK_ENABLED", "BARK_SERVER_URL", "BARK_DEVICE_KEY", "BARK_DEFAULT_GROUP",
})
```
