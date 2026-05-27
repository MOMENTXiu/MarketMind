# TTS / Voice 功能盘点

> 状态: 历史档案。TTS / Voice 运行时已废除，当前代码不再提供 `/api/voice/*`、`/api/ai-voice/*`、`/api/tts/` 或 Edge TTS 依赖。
> 创建日期: 2026-05-26
> 范围: 后端 + 前端全部语音合成与播报能力
> 引擎: Microsoft Edge TTS (edge-tts)
> 语言: 中文为主，通过 voice 参数切换

---

## 1. 概述

MarketMind 曾经有两套并行的语音/TTS 能力：

| 能力 | 路由前缀 | 定位 | LLM 依赖 |
|------|---------|------|----------|
| **Generic Voice / TTS** | `/api/voice/*` | 基础文本转语音，直接合成 | 无 |
| **AI Voice Broadcast** | `/api/ai-voice/*` | AI 生成播报脚本后再合成 | 有 |

两套系统曾共享同一个 **Edge TTS** 适配器，但使用不同的 asset 发布路径和 URL 命名空间。该能力现已废除，本文件仅保留历史盘点。

---

## 2. API 路由清单

### 2.1 Generic Voice (`/api/voice`)

| 方法 | 路由 | 作用 |
|------|------|------|
| `POST` | `/api/voice/tts/` | 纯文本转语音，输出到 `outputs/audio/` |
| `POST` | `/api/voice/generate/` | **占位符**，前端兼容保留，返回固定文案 |
| `GET`  | `/api/voice/status/` | 静态就绪探针 |

### 2.2 AI Voice Broadcast (`/api/ai-voice`)

| 方法 | 路由 | 作用 |
|------|------|------|
| `POST` | `/api/ai-voice/broadcast/` | LLM 生成播报脚本 + TTS 合成，输出到 `backend/data/audio/` |
| `POST` | `/api/tts/` | AI Voice 命名空间下的纯 TTS |
| `GET`  | `/api/ai-voice/audio/{filename}/` | 流式播放 AI 语音音频文件 |

---

## 3. 后端代码地图（分层架构）

### 3.1 API Controller 层

| 文件 | 职责 |
|------|------|
| `backend/api/voice.py` | Generic Voice 路由注册；`SimpleTTSRequest` schema |
| `backend/api/ai_voice.py` | AI Voice Broadcast 路由注册；`VoiceBroadcastRequest`, `TTSRequest` schema |
| `backend/api/dependencies.py` | `get_voice_synthesis_pipeline()`, `get_ai_voice_broadcast_pipeline()` |

### 3.2 Business Pipeline / Flow 层

| 文件 | 职责 |
|------|------|
| `backend/business/pipelines/voice_synthesis_pipeline.py` | 纯 TTS 合成流水线：校验文本 -> 调用 SpeechSynthesisProvider -> 发布 public audio |
| `backend/business/pipelines/ai_voice_broadcast_pipeline.py` | AI 播报流水线：LLM 生成脚本 -> 调用 SpeechSynthesisProvider -> 发布 AI audio；同时提供纯 TTS 路径和音频文件解析 |

### 3.3 Ability Atom 层

| 文件 | 职责 |
|------|------|
| `backend/abilities/voice/synthesize_speech.py` | 透传调用 `SpeechSynthesisProvider.synthesize()` |
| `backend/abilities/voice/generate_broadcast_script.py` | 基于 scene_type 选择 prompt，调用 LLM 生成播报文案；LLM 失败时回退到本地 fallback 文案 |
| `backend/abilities/report/generate_speech_text.py` | 从 analysis results 组装传统播报文本（关联规则 + 预测 + 聚类），无 LLM |

**scene_type prompt 映射：**
- `clustering` — 客户聚类播报
- `association` — 商品关联规则播报
- `prediction` — 销售预测播报
- `summary` — 综合摘要播报（默认）

### 3.4 Provider Boundary 层

| 文件 | 职责 |
|------|------|
| `backend/providers/speech_synthesis_provider.py` | `SpeechSynthesisProvider` Protocol：`synthesize()`, `list_voices()` |
| `backend/providers/generated_asset_provider.py` | `GeneratedAssetProvider` Protocol：`save_public_audio()`, `save_ai_audio()`, `resolve_ai_audio()`, `save_project_audio()`, `save_project_report()` 等 |
| `backend/providers/dtos.py` | `SpeechSynthesisRequestDTO`, `SpeechSynthesisResultDTO`, `AssetReferenceDTO`, `LLMRequestDTO`, `LLMResponseDTO` 等 |
| `backend/providers/container.py` | `ProvidersContainer` 持有 `speech` 和 `assets` 字段 |

### 3.5 Infrastructure Adapter 层

| 文件 | 职责 |
|------|------|
| `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py` | `EdgeTtsSpeechSynthesisAdapter`：封装 `edge_tts.Communicate` 和 `edge_tts.list_voices` |
| `backend/infrastructure/adapters/local_generated_asset_adapter.py` | `LocalGeneratedAssetAdapter`：本地文件系统资产持久化，区分 public/audio、ai_audio、project/audio、project/reports |
| `backend/infrastructure/factories/provider_factory.py` | `create_providers()` 组装 `speech=EdgeTtsSpeechSynthesisAdapter()` 和 `assets=LocalGeneratedAssetAdapter(...)` |

### 3.6 Core / Config 层

| 文件 | 职责 |
|------|------|
| `backend/core/config.py` | `Settings.TTS_VOICE = "zh-CN-YunxiNeural"`；`OUTPUT_DIR`, `AUDIO_DIR` 等路径配置 |
| `backend/models/schemas.py` | `VoiceRequest`, `VoiceResponse` Pydantic schema |
| `backend/core/runtime_checks.py` | `cmd_check_speech()` — 需要 `--mock` 参数运行 |

---

## 4. 前端代码地图

| 文件 | 语音相关功能 |
|------|-------------|
| `frontend/src/views/Settings.vue` | TTS 配置面板：voice、rate、volume 滑块，保存到 `localStorage['tts_config']` |
| `frontend/src/views/ProjectDetail.vue` | 聚类分析播报：调用 `/api/ai-voice/broadcast/`（scene_type=clustering/summary），播放返回音频并显示字幕 |
| `frontend/src/views/CustomerAnalysis.vue` | 客户详情 AI 建议：调用 `/api/ai-voice/broadcast/`（scene_type=summary），**仅使用返回文本**，不自动播放语音 |
| `frontend/src/views/ProductRecommend.vue` | 商品洞察语音播报：调用 `/api/voice/tts/` 合成 insight 文本，自动播放 |
| `frontend/src/components/ServiceStatus.vue` | 服务状态检查，可能包含语音服务状态 |

**前端配置存储：**
- `localStorage['tts_config']` — `{ voice, rate, volume }`
- `localStorage['llm_config']` — `{ provider, baseUrl, apiKey, modelName }`（AI Voice Broadcast 需要）

---

## 5. 数据流

### 5.1 Generic TTS 流

```
Frontend Settings / ProductRecommend
  POST /api/voice/tts/
    -> VoiceSynthesisPipeline.synthesize()
      -> edge_tts.Communicate (写入 /tmp/tts_{uuid}.mp3)
      -> LocalGeneratedAssetAdapter.save_public_audio()
        -> 复制到 outputs/audio/tts_{uuid}.mp3
    <- 返回 { audio_url: "/outputs/audio/tts_{uuid}.mp3" }
```

### 5.2 AI Voice Broadcast 流

```
Frontend ProjectDetail / CustomerAnalysis
  POST /api/ai-voice/broadcast/
    -> AIVoiceBroadcastPipeline.broadcast()
      -> generate_broadcast_script()
        -> LLMProvider.generate_text() (或 fallback)
      -> edge_tts.Communicate (写入 /tmp/{scene_type}_{hash}.mp3)
      -> LocalGeneratedAssetAdapter.save_ai_audio()
        -> 复制到 backend/data/audio/{filename}.mp3
    <- 返回 { text, audio_url: "/api/ai-voice/audio/{filename}/" }

  GET /api/ai-voice/audio/{filename}/
    -> AIVoiceBroadcastPipeline.resolve_audio_path()
      -> 查找 /tmp/{filename} 或 backend/data/audio/{filename}
    <- FileResponse (audio/mpeg)
```

---

## 6. 配置项

| 配置项 | 位置 | 默认值 | 说明 |
|--------|------|--------|------|
| `TTS_VOICE` | `backend/core/config.py` | `zh-CN-YunxiNeural` | 默认语音角色 |
| `OUTPUT_DIR` | `backend/core/config.py` | `outputs` | public 输出根目录 |
| `AUDIO_DIR` | `backend/core/config.py` | `outputs/audio` | public 音频目录 |
| `voice` | 前端 localStorage | `zh-CN-XiaoxiaoNeural` | 用户选择的语音角色 |
| `rate` | 前端 localStorage | `+0%` | 语速，范围通常为 `-100%` ~ `+100%` |
| `volume` | 前端 localStorage | `+0%` | 音量，范围通常为 `-100%` ~ `+100%` |

**常用 Edge TTS 中文语音：**
- `zh-CN-XiaoxiaoNeural` — 晓晓（女声，前端默认）
- `zh-CN-YunxiNeural` — 云希（男声，后端默认）
- `zh-CN-YunjianNeural` — 云健

---

## 7. 测试覆盖

| 测试文件 | 覆盖内容 |
|----------|----------|
| `tests/business/test_voice_synthesis_pipeline.py` | VoiceSynthesisPipeline 合成成功返回 public URL；空文本校验 |
| `tests/business/test_ai_voice_broadcast_pipeline.py` | AIVoiceBroadcastPipeline broadcast 成功返回 AI URL；LLM + TTS 集成 |
| `tests/abilities/test_report_and_voice_abilities.py` | `generate_speech_text` 文本组装；`generate_broadcast_script` LLM 合约 + fallback；`synthesize_speech` provider 合约 |
| `tests/providers/test_speech_and_llm_adapters.py` | EdgeTtsSpeechSynthesisAdapter 使用注入 factory；OpenAI/Anthropic LLM adapter 请求映射 |
| `tests/api/test_current_api_contracts.py` | 当前 API 合同（可能包含 voice 路由） |
| `tests/api/test_frontend_api_matrix_contracts.py` | 前端 API 矩阵合同 |
| `tests/core/test_runtime_checks.py` | `cmd_check_speech` 运行时检查 |

---

## 8. 运行时检查

```bash
# TTS 运行时检查（mock 模式，不发起真实网络请求）
uv run python -m backend.core.runtime_checks check-speech --mock

# 通用 provider 组装检查
uv run python -m backend.core.runtime_checks check-providers

# 全量可选运行时检查（含 speech/llm 接口存在性验证）
uv run python -m backend.core.runtime_checks check-analysis-optional-runtime
```

---

## 9. 架构约束

- `edge_tts` **禁止**在 `backend/api/`、`backend/business/`、`backend/abilities/`、`backend/providers/` 中直接导入，必须通过 `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py` 引入。
- `SpeechSynthesisProvider` 和 `GeneratedAssetProvider` 是 Protocol 接口，业务代码依赖接口而非具体实现。
- TTS 输出音频先写入 `/tmp/`，再由 `LocalGeneratedAssetAdapter` 复制到目标目录。
- AI Voice audio 查找顺序：`/tmp/{filename}` -> `backend/data/audio/{filename}`。

---

## 10. 扩展点 / 注意事项

- **替换 TTS 引擎**：实现新的 `SpeechSynthesisProvider`，在 `provider_factory.py` 中替换 `EdgeTtsSpeechSynthesisAdapter` 即可，上层代码无感知。
- **新增 scene_type**：在 `backend/abilities/voice/generate_broadcast_script.py` 的 `PROMPTS` 字典中添加新 prompt。
- **音频存储路径变更**：修改 `LocalGeneratedAssetAdapter` 的构造参数和 `save_*_audio` / `resolve_*_audio` 方法。
- **前端默认语音不一致**：后端默认 `zh-CN-YunxiNeural`，前端默认 `zh-CN-XiaoxiaoNeural`。如需统一，请同步修改 `backend/core/config.py` 和 `frontend/src/views/Settings.vue`。
- **占位符 API**：`POST /api/voice/generate/` 是前端兼容占位符，返回固定文案，未调用真实 TTS。
