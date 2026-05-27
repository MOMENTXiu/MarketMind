# TTS / Voice 功能废除计划

> Status note (2026-05-26): TTS / Voice runtime has been retired. Current text generation goes through `POST /api/analysis/customer-suggestions`; frontend pages must not call `/api/voice/*`, `/api/ai-voice/*`, `/api/tts/*`, `/chat/completions`, or `/models` directly. This document is retained as the deprecation plan record.

> 创建日期: 2026-05-26
> 分支: `develop/sql-plugin`
> 状态: **历史记录，已由 text-only Customer Suggestions 取代**

---

## 0. 审查结论

当前废除方向可行，但旧版计划不能直接执行。阻塞点如下：

- `frontend/src/views/CustomerAnalysis.vue` 的 AI 文本建议当前复用 `/api/ai-voice/broadcast/`，后端会在生成文本后继续合成音频；废除 TTS 前必须迁移为 text-only 能力，或明确下线该文本建议入口。
- `frontend/src/views/ProjectDetail.vue` 的实际函数名是 `speakCluster`，不是旧计划中的 `speakAnalysis`。
- `GeneratedAssetProvider` 与 `LocalGeneratedAssetAdapter` 同时承载报告资产与音频资产，废除时只删除 audio 专用能力，保留 report / chart / csv 等非音频资产能力。
- 计划必须补齐 `.env.example`、`uv.lock`、启动脚本、根 `app.py`、provider adapter 测试、controller thinness 测试、repository 测试、README/architecture docs 等漏项。
- `edge_tts` 的架构测试不应简单删除约束；依赖移除后应转为“runtime 全仓不得再 import `edge_tts`”的回归门。

结论：先按本文档补齐范围和清单，再进入代码删除。不要在未处理 text-only 替代路径时直接删除 AI Voice Broadcast。

---

## 1. 目的

TTS（Text-to-Speech）语音合成与播报功能在当前产品阶段不再需要，且引入了以下维护负担：

- **外部依赖**：`edge-tts>=6.1.10` 需要 Microsoft 在线语音服务，存在网络可用性和地区限制风险
- **代码复杂度**：两套并行的语音系统（Generic Voice + AI Voice Broadcast）涉及 API、Pipeline、Ability、Provider、Adapter 共 5 层，约 ~1200 行代码
- **测试维护**：6 个测试文件专门覆盖语音功能，每次 LLM/TTS 接口变更都需要同步更新
- **前端耦合**：Settings、ProjectDetail、CustomerAnalysis、ProductRecommend 四个视图嵌入了语音配置和调用逻辑
- **资产残留**：运行时产生的 `outputs/audio/`、`backend/data/audio/`、`/tmp/*.mp3` 文件需要清理策略

废除后，后端架构更聚焦分析核心链（Retail V2 + Data-processing），减少无关依赖和测试基数。

---

## 2. 现状盘点

### 2.1 后端代码（待删除/修改）

| 类别 | 文件 | 处置 |
|------|------|------|
| **API Controller** | `backend/api/voice.py` | **删除**（3 个路由：/voice/tts/, /voice/generate/, /voice/status/） |
| | `backend/api/ai_voice.py` | **删除**（3 个路由：/ai-voice/broadcast/, /tts/, /ai-voice/audio/{filename}/） |
| **Business Pipeline** | `backend/business/pipelines/voice_synthesis_pipeline.py` | **删除** |
| | `backend/business/pipelines/ai_voice_broadcast_pipeline.py` | **删除** |
| **Ability Atom** | `backend/abilities/voice/`（整目录） | **删除**（synthesize_speech.py, generate_broadcast_script.py） |
| | `backend/abilities/report/generate_speech_text.py` | **删除**（仅用于语音播报文本组装） |
| **Provider Protocol** | `backend/providers/speech_synthesis_provider.py` | **删除** |
| **Provider DTO** | `backend/providers/dtos.py` 中 `SpeechSynthesisRequestDTO`, `SpeechSynthesisResultDTO` | **删除**（仅被 TTS 使用） |
| **Provider Container** | `backend/providers/container.py` 的 `speech` 字段 | **移除**字段 |
| **Infrastructure Adapter** | `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py` | **删除** |
| **Provider Factory** | `backend/infrastructure/factories/provider_factory.py` | 移除 `speech=EdgeTtsSpeechSynthesisAdapter()` 及 import |
| **Core Config** | `backend/core/config.py` | 移除 `TTS_VOICE`、`AUDIO_DIR` |
| **Schemas** | `backend/models/schemas.py` | 移除 `VoiceRequest`, `VoiceResponse` |
| **Runtime Checks** | `backend/core/runtime_checks.py` | 移除 `cmd_check_speech` 及 `_RuntimeCheckSpeechProvider` |
| **Dependencies** | `backend/api/dependencies.py` | 移除 `get_voice_synthesis_pipeline()`, `get_ai_voice_broadcast_pipeline()` |
| **Main App** | `backend/main.py` | 移除 `voice.router`, `ai_voice.router` 注册及 import |
| **Project Model / Storage** | `backend/models/project.py`, `backend/core/storage.py` | 移除 TTS 遗留的 `audio_path` 和 `outputs/audio` 初始化逻辑；不得影响 reports/charts/csv outputs |
| **Error Mapping** | `backend/api/error_mapping.py` | 检查是否有 TTS 专属错误码，无则无需改动 |

### 2.2 前端代码（待删除/修改）

| 文件 | 处置 |
|------|------|
| `frontend/src/views/Settings.vue` | **移除**整个 TTS 配置区块（voice、rate、volume 滑块、testTTS、saveTTSConfig、localStorage['tts_config'] 读写） |
| `frontend/src/views/ProjectDetail.vue` | **移除**`speakCluster` 函数、`voiceLoading`、语音播放按钮、字幕显示、`<audio>` 标签相关逻辑 |
| `frontend/src/views/CustomerAnalysis.vue` | **移除**`playVoice` 函数、`voiceLoading`、语音播报按钮及 `<audio>` 相关逻辑；将 AI 文本建议迁移到 text-only API，禁止继续调用 `/api/ai-voice/broadcast/` |
| `frontend/src/views/ProductRecommend.vue` | **移除**`playInsightVoice` 函数、`voiceLoading`、语音播报按钮及 `<audio>` 相关逻辑 |
| `frontend/src/components/ServiceStatus.vue` | **移除**Edge TTS 服务状态卡片 |
| `frontend/src/views/Voice.vue` | 确认路由引用；若未使用则删除陈旧页面，若仍被路由引用则同步移除路由入口 |

### 2.3 测试代码（待删除/修改）

| 文件 | 处置 |
|------|------|
| `tests/business/test_voice_synthesis_pipeline.py` | **删除** |
| `tests/business/test_ai_voice_broadcast_pipeline.py` | **删除** |
| `tests/abilities/test_report_and_voice_abilities.py` | 保留 `generate_analysis_report` 测试，**移除**语音相关测试（`test_generate_speech_text_*`, `test_generate_broadcast_script_*`, `test_synthesize_speech_*`） |
| `tests/providers/test_speech_and_llm_adapters.py` | **移除**`test_edge_tts_speech_adapter_*`，保留 LLM adapter 测试（文件可重命名为 `test_llm_adapters.py`） |
| `tests/api/test_current_api_contracts.py` | 移除 voice/ai-voice 路由的断言 |
| `tests/api/test_frontend_api_matrix_contracts.py` | 移除 voice/ai-voice 路由的断言 |
| `tests/core/test_runtime_checks.py` | 移除 `cmd_check_speech` 相关测试 |
| `tests/test_architecture_imports.py` | 将 `edge_tts` 规则改为全仓 runtime 禁止 import 的回归门，避免废除后重新引入 SDK 直连 |
| `tests/fakes/providers.py` | **移除**`FakeSpeechSynthesisProvider` 类及相关 DTO import；更新所有使用 `FakeSpeechSynthesisProvider` 的 fixture（conftest.py、test_retail_analysis_flow.py 等） |
| `tests/api/conftest.py` | 移除 `speech` 字段及相关 import/fake |
| `tests/api/test_controller_thinness.py` | 移除 voice / ai_voice controller 相关 thinness 断言或白名单 |
| `tests/providers/test_local_file_adapters.py` | 移除 audio asset 方法测试，保留 report asset 方法测试 |
| `tests/providers/test_json_project_repository_adapter.py` | 移除或更新 `audio_path` 相关 project repository 断言 |

### 2.4 项目配置（待修改）

| 文件 | 处置 |
|------|------|
| `pyproject.toml` | **移除**`"edge-tts>=6.1.10,<7.0.0"` 依赖 |
| `uv.lock` | 执行依赖同步后提交锁文件变化，确认 `edge-tts` 及其仅由 TTS 引入的传递依赖已移除 |
| `.env.example` | 移除 audio/TTS 输出目录和语音配置示例 |
| `scripts/start-backend.sh`, `scripts/start-backend.bat` | 移除音频目录初始化和 TTS 相关提示 |
| `app.py` | 移除 Streamlit 旧入口中的“语音播报”页面、`edge-tts` 文案和相关调用 |
| `docs/TTS_VOICE_INVENTORY.md` | 标记为废除历史文档，或移动到 `docs/archive/`；不要作为 active capability 文档保留 |
| `AGENTS.md` | 移除 TTS 相关的 agent notes |
| `docs/ARCHITECTURE.md` | 从 Active API Surface 中移除 Voice 和 AI Voice 路由；从架构图中移除 voice pipeline |
| `docs/QUICKSTART.md` | 移除语音相关运行时检查命令 |
| `docs/development.md` | 更新测试基数预期（废除后测试数会减少） |
| `README.md`, `docs/USAGE_GUIDE.md`, `docs/PROJECT_PLAN.md`, `docs/Project_Report.md` | 移除或改写仍宣称语音/TTS 可用的产品说明 |
| `docs/architecture/architecture-change.md`, `docs/architecture/construction-checklist.md` | 同步删除 active voice pipeline / provider / runtime check 描述 |

### 2.5 运行时资产（需清理）

废除后不再产生以下目录/文件：
- `outputs/audio/*.mp3`
- `backend/data/audio/*.mp3`
- `/tmp/tts_*.mp3`
- `data/projects/{project_id}/outputs/audio/*.mp3`

这些属于运行时生成的临时文件，不纳入 git 管理，但应在废除后的首次部署中清理。

---

## 3. Abolish 方案

### 3.0 范围边界

**废除对象：**

- Generic Voice / TTS API：`/api/voice/*`
- AI Voice Broadcast 的音频合成与音频文件服务：`/api/ai-voice/*`, `/api/tts/`
- `SpeechSynthesisProvider`、speech DTO、`ProvidersContainer.speech`
- `EdgeTtsSpeechSynthesisAdapter` 与 `edge-tts` 依赖
- TTS audio asset persistence：public audio、AI audio、project audio 方法和目录初始化
- 前端 TTS 配置、语音按钮、音频播放、字幕 UI、Edge TTS 服务状态

**保留对象：**

- LLM 文本建议能力，但必须迁移到非 voice 命名的 text-only API / pipeline，不再触发 speech synthesis
- 报告、图表、CSV、analysis outputs 等非音频生成资产能力
- `GeneratedAssetProvider` 中的 `save_project_report` / `resolve_project_report` 等报告资产方法
- Retail V2 与 Data-processing 分析链路

### 3.1 执行顺序

推荐的删除顺序（由外向内，先删调用方再删实现）：

1. **Text-only 决策与迁移** — 先为 `CustomerAnalysis.vue` 的 AI 文本建议提供非 voice API，或明确下线该功能；不得继续调用 `/api/ai-voice/broadcast/`
2. **Frontend** — 移除前端所有 TTS 配置、按钮、调用逻辑、localStorage `tts_config`、音频播放和字幕 UI
3. **API 入口切断** — 先在 `backend/main.py` 移除 `voice.router` / `ai_voice.router` 注册，再清理 `backend/api/dependencies.py`
4. **Tests** — 删除/清理 TTS 相关测试、fake、API matrix、thinness、provider adapter 和 repository 断言
5. **API Controller** — 删除 `backend/api/voice.py`、`backend/api/ai_voice.py`
6. **Business Pipeline** — 删除 voice pipeline 文件；保留或新增 text-only LLM pipeline 时使用非 voice 命名
7. **Ability Atom** — 删除 voice 目录及 `generate_speech_text.py`
8. **Provider Boundary** — 从 container、dtos 中移除 speech 相关字段和类型；只删除 audio asset 方法，保留 report asset 方法
9. **Infrastructure Adapter** — 删除 edge_tts adapter，清理 provider factory
10. **Config / Schemas / Runtime Checks / Storage / Model** — 清理 TTS config、schema、runtime check、audio 目录初始化和 `audio_path`
11. **Dependencies** — 移除 `pyproject.toml` 的 `edge-tts` 并同步 `uv.lock`
12. **Docs / Env / Scripts / Root App** — 更新 README、docs、`.env.example`、启动脚本、`app.py`、agent baseline
13. **质量门** — 按仓库基线运行 `make lint`, `make format`, `make typecheck`, `make test`, `make build`, `make check` 或 `make verify`

### 3.2 文件删除清单

以下文件将被**完全删除**：

```text
backend/api/voice.py
backend/api/ai_voice.py
backend/business/pipelines/voice_synthesis_pipeline.py
backend/business/pipelines/ai_voice_broadcast_pipeline.py
backend/abilities/voice/
backend/abilities/report/generate_speech_text.py
backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py
backend/providers/speech_synthesis_provider.py
tests/business/test_voice_synthesis_pipeline.py
tests/business/test_ai_voice_broadcast_pipeline.py
tests/providers/test_speech_and_llm_adapters.py  （或重命名保留 LLM 部分）
docs/TTS_VOICE_INVENTORY.md  （或移动到 docs/archive/ 作为历史盘点）
```

### 3.3 文件修改清单

以下文件将被**修改**（移除 TTS 相关代码但保留文件）：

```text
backend/api/dependencies.py
backend/main.py
backend/core/config.py
backend/core/runtime_checks.py
backend/models/schemas.py
backend/providers/container.py
backend/providers/dtos.py
backend/infrastructure/factories/provider_factory.py
backend/providers/generated_asset_provider.py  （移除 save_public_audio, save_ai_audio, resolve_ai_audio, save_project_audio, resolve_project_audio）
backend/infrastructure/adapters/local_generated_asset_adapter.py  （移除 audio 方法，保留 report 方法）
backend/models/project.py  （移除 audio_path，如确认仅为 TTS 遗留）
backend/core/storage.py  （移除 outputs/audio 初始化，保留其他 outputs 目录）
tests/fakes/providers.py
tests/api/conftest.py
tests/api/test_current_api_contracts.py
tests/api/test_frontend_api_matrix_contracts.py
tests/api/test_controller_thinness.py
tests/abilities/test_report_and_voice_abilities.py
tests/core/test_runtime_checks.py
tests/test_architecture_imports.py
tests/providers/test_local_file_adapters.py
tests/providers/test_json_project_repository_adapter.py
tests/business/test_retail_analysis_flow.py
tests/business/test_retail_analysis_pipelines.py
tests/business/test_data_processing_analysis_flow.py
tests/business/test_data_processing_pipelines.py
pyproject.toml
uv.lock
.env.example
scripts/start-backend.sh
scripts/start-backend.bat
app.py
frontend/src/views/Settings.vue
frontend/src/views/ProjectDetail.vue
frontend/src/views/CustomerAnalysis.vue
frontend/src/views/ProductRecommend.vue
frontend/src/components/ServiceStatus.vue
frontend/src/views/Voice.vue
AGENTS.md
README.md
docs/ARCHITECTURE.md
docs/QUICKSTART.md
docs/USAGE_GUIDE.md
docs/PROJECT_PLAN.md
docs/Project_Report.md
docs/development.md
docs/architecture/architecture-change.md
docs/architecture/construction-checklist.md
```

### 3.4 保留项（仅移除 audio 方法）

`GeneratedAssetProvider` Protocol 及 `LocalGeneratedAssetAdapter` 中的 **报告相关方法**（`save_project_report`, `resolve_project_report`）**保留**。

但所有 **audio 相关方法**（`save_public_audio`, `save_ai_audio`, `resolve_ai_audio`, `save_project_audio`, `resolve_project_audio`）将**移除**，因为废除后项目不再生成音频资产。

如果未来需要保留项目报告音频（非 TTS，而是上传音频），可保留 `save_project_audio` / `resolve_project_audio`；但当前无此需求，建议一并移除。

### 3.5 AI 文本建议迁移

`CustomerAnalysis.vue` 当前使用 `/api/ai-voice/broadcast/` 获取文本建议，即使前端不播放音频，后端仍会调用 speech synthesis。废除 TTS 前必须完成其中一种处理：

1. **推荐方案：迁移为 text-only 能力**
	- 新增或复用非 voice 命名的 LLM 文本建议 pipeline / API。
	- 返回结构只包含文本建议和必要 metadata，不生成 `audio_url`。
	- 前端 `CustomerAnalysis.vue` 改为调用 text-only endpoint。

2. **下线方案：删除该入口**
	- 若当前阶段不保留 AI 文本建议，前端必须移除对应按钮、状态和展示区域。
	- 文档需明确这是产品行为下线，不是单纯 TTS 删除。

禁止保留 `/api/ai-voice/broadcast/` 作为“临时文本接口”，否则会继续保留 TTS 维护面和命名债务。

### 3.6 Provider / Storage 边界

`GeneratedAssetProvider` 和 `LocalGeneratedAssetAdapter` 不应整体删除。处理规则：

- 删除 `save_public_audio`, `save_ai_audio`, `resolve_ai_audio`, `save_project_audio`, `resolve_project_audio`。
- 保留 `save_project_report`, `resolve_project_report` 以及非音频资产能力。
- 删除 `outputs/audio` 与 `backend/data/audio` 的主动初始化逻辑。
- `backend/models/project.py` 的 `audio_path` 如仅用于 TTS，应同步删除并更新 repository 测试。
- 不修改 charts、reports、csv、regularized datasets、analysis outputs 的存储路径和 provider 契约。

---

## 4. 影响评估

### 4.1 测试基数变化

废除前语音相关测试约 ~12 个：
- `test_voice_synthesis_pipeline.py`：2
- `test_ai_voice_broadcast_pipeline.py`：1
- `test_report_and_voice_abilities.py`：3（语音相关）
- `test_speech_and_llm_adapters.py`：1（edge_tts 相关）
- `test_runtime_checks.py`：若干（cmd_check_speech）
- API 合同测试中 voice 断言：若干

预计废除后 pytest 测试数从 **188** 降至约 **175-180**。

### 4.2 依赖变化

移除 `edge-tts>=6.1.10,<7.0.0` 后：
- 减少一个外部网络依赖
- 将 `edge_tts` 相关架构规则改为“runtime 全仓不得 import `edge_tts`”的回归门
- `uv.lock`（如有）需同步更新

### 4.3 前端影响

- **Settings 页面**：移除 TTS 配置区块后，页面仅剩 LLM 配置
- **ProjectDetail 页面**：移除聚类播报按钮后，聚类卡片仅剩数据展示
- **CustomerAnalysis 页面**：保留 LLM 文本建议时必须迁移到 text-only API；否则明确下线 AI 建议入口
- **ProductRecommend 页面**：移除洞察语音播报按钮
- **ServiceStatus 页面**：移除 Edge TTS 状态卡片

---

## 5. Rollback 策略

废除后如需恢复 TTS，按以下顺序回退：

1. 从 git history 恢复被删除的文件（`voice.py`, `ai_voice.py`, `voice_synthesis_pipeline.py`, `ai_voice_broadcast_pipeline.py`, `edge_tts_speech_synthesis_adapter.py`, `speech_synthesis_provider.py`, `voice/` 目录等）
2. 恢复 `pyproject.toml` 中的 `edge-tts` 依赖并执行 `uv sync`
3. 恢复 `backend/providers/container.py` 的 `speech` 字段
4. 恢复 `backend/main.py` 的路由注册
5. 恢复前端 TTS 相关代码（或从 git history cherry-pick）
6. 恢复测试文件

建议在执行 abolish 前打 tag：`git tag pre-abolish-tts`，便于快速回退。

---

## 6. Commit Criteria

执行 abolish 后，满足以下条件方可提交：

- [ ] 全仓 runtime 代码无 `edge_tts` import，架构测试覆盖重新引入风险
- [ ] `backend/` 无 `SpeechSynthesisProvider` / `SpeechSynthesisRequestDTO` / `SpeechSynthesisResultDTO` 引用
- [ ] `backend/main.py` 不再注册 `voice.router` / `ai_voice.router`
- [ ] `backend/api/dependencies.py` 无 voice pipeline 依赖导出
- [ ] `ProvidersContainer` 无 `speech` 字段，provider factory 不再创建 speech provider
- [ ] `GeneratedAssetProvider` 仅移除 audio 方法，report asset 方法仍可用且测试覆盖
- [ ] `tests/` 无 TTS 相关测试失败
- [ ] `pyproject.toml` 已移除 `edge-tts`
- [ ] `uv.lock` 已同步移除 `edge-tts`
- [ ] `frontend/` 无 TTS 相关编译错误
- [ ] `frontend/` 无 `/api/voice/tts/`, `/api/ai-voice/broadcast/`, `/api/tts/` 调用
- [ ] `CustomerAnalysis.vue` 已迁移到 text-only API，或 AI 文本建议入口已明确下线
- [ ] `.env.example`、启动脚本、`app.py`、README、USAGE、architecture docs 不再宣称 TTS/Voice 可用
- [ ] `make lint` 通过
- [ ] `make test` 通过（测试数下降在预期范围内）
- [ ] `make build` 通过
- [ ] `make check` 或 `make verify` 通过；如目标为 placeholder，需在交付报告中说明
- [ ] 架构文档已同步（AGENTS.md, ARCHITECTURE.md, QUICKSTART.md, USAGE_GUIDE.md, development.md, architecture-change.md, construction-checklist.md）
