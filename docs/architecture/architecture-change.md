# Backend Architecture Change Plan

## 1. Scope

本文件只规划 `/backend` 的后端架构重构，不执行代码迁移。允许的本阶段改动仅为：

- `docs/architecture/architecture-change.md`
- `docs/architecture/construction-checklist.md`

本阶段禁止修改 `/backend`、`/frontend`、数据 schema、API 行为、环境变量语义、前端调用方式或测试文件。后续迁移必须保持公开 API、状态码、响应字段、文件副作用和前端依赖行为等价。

固定目标方向：

```text
API Controller -> Business Pipeline -> Ability Atom -> Provider Interface -> External Adapter
```

复杂生命周期才允许：

```text
API Controller -> Business Flow -> Business Pipeline -> Ability Atom -> Provider Interface -> External Adapter
```

如果 Business Flow 只是转发到单个 Pipeline，不创建 Flow。

## 2. Current Project Structure

根目录扫描结果：

- `app.py`: Streamlit 单机入口。
- `backend/`: FastAPI 后端。
- `frontend/`: Vue 3 + Vite 前端。
- `analysis/`: 数据分析脚本、示例数据、分析报告。
- `data/`: 项目 JSON 存储与项目级数据目录。
- `outputs/`: 全局生成物目录，包含 `audio/`、`charts/`、`reports/`。
- `docs/`: 现有项目文档。
- `scripts/`: 启动脚本。
- `pyproject.toml`: 根 Python 项目配置、依赖、pytest/black/ruff 配置。
- `frontend/package.json`: 前端 scripts 与依赖。
- `README.md`: 项目说明与启动方式。

重点扫描目录：

```text
backend/
  main.py
  api/
    ai_voice.py
    association.py
    clustering.py
    prediction.py
    projects.py
    recommend.py
    voice.py
  core/
    analysis.py
    config.py
    recommend.py
    storage.py
  models/
    project.py
    schemas.py
  services/
    ai_voice_service.py
    analysis_service.py
    association_service.py
    clustering_service.py
    model_builder_service.py
    prediction_service.py
    recommender_service.py
    tts_service.py
    voice_service.py
  utils/
    __init__.py
```

前端相关扫描目录：

```text
frontend/
  package.json
  vite.config.ts
  src/
    utils/http.ts
    views/*.vue
    components/ServiceStatus.vue
```

允许扫描但未发现的路径或文件：

| Path | Scan Result |
|---|---|
| `/src` at project root | 未发现；存在 `frontend/src/`。 |
| `/app` directory | 未发现；存在根文件 `app.py`。 |
| `/packages` | 未发现。 |
| `.env.example` | 已存在；作为 committed template，不写入 secrets。 |
| `docker-compose.yml` | 未发现。 |
| `Dockerfile` | 未发现。 |
| `Makefile` | 已存在；提供 `setup`、`lint`、`format`、`fix`、`test`、`build`、`check`、`verify`、`hooks`、`clean` 入口。 |
| `justfile` | 未发现。 |
| `.github/workflows` | 已存在；`check.yml` 分离 backend / frontend 检查。 |
| `tox.ini` / `pytest.ini` / `ruff.toml` / `mypy.ini` | 未发现独立文件；pytest/ruff 在 `pyproject.toml` 中配置。 |
| `.eslintrc` / prettier config | 未发现。 |
| `docs/architecture/architecture-change.md` | 本次创建。 |
| `docs/architecture/construction-checklist.md` | 本次创建。 |

## 3. Current Backend Entry Points

后端技术栈：Python 3.13、FastAPI、Uvicorn、Pydantic Settings、pandas、scikit-learn、mlxtend、edge-tts、httpx。

### API Controller / Route

主入口为 `backend/main.py`：

- `FastAPI(title="MarketMind API")`
- CORS 使用 `settings.CORS_ORIGINS`
- 挂载 `/outputs` 静态目录
- 注册 routers：
  - `/api/projects` -> `backend/api/projects.py`
  - `/api/association` -> `backend/api/association.py`
  - `/api/voice` -> `backend/api/voice.py`
  - `/api/recommend/*` -> `backend/api/recommend.py`
  - `/api/ai-voice/*` and `/api/tts/` -> `backend/api/ai_voice.py`
- `prediction` 与 `clustering` router 在 `main.py` 中被注释，当前未注册。

### CLI

未发现 argparse、click、typer 或独立 CLI。仅有：

- `backend/main.py` 的 `if __name__ == "__main__": uvicorn.run(...)`
- 根 `app.py` 的 Streamlit 入口

### Worker / Scheduled Job / Queue Consumer

未发现 Celery、RQ、APScheduler、cron、queue consumer。当前后台任务仅使用 FastAPI `BackgroundTasks`：

- `POST /api/projects/{project_id}/upload/` -> `background_tasks.add_task(run_project_analysis, project_id)`
- `POST /api/projects/{project_id}/reanalyze/` -> `background_tasks.add_task(run_project_analysis, project_id)`

`backend/api/association.py` 接收 `BackgroundTasks` 参数，但未调用 `add_task`。

## 4. Current Backend Call Chains

> **Status note (Phase 9)**: §4.1 – §4.8 describe the pre-migration call chains preserved as behavior anchors. The post-migration runtime path for every active controller is:
>
> `Controller (backend/api/*) -> Pipeline (backend/business/pipelines/*) -> Ability (backend/abilities/*) and/or Provider Interface (backend/providers/*) -> Adapter (backend/infrastructure/adapters/*) -> external SDK / filesystem`
>
> Concrete pipeline wiring:
>
> - `POST /api/projects/{id}/upload/` -> `DatasetUploadPipeline` -> `ProjectRepositoryProvider` + `ProjectFileStorageProvider` -> schedule `ProjectAnalysisFlow` via `AnalysisJobProvider` (`FastapiBackgroundAnalysisJobAdapter`).
> - `/api/projects/*` CRUD -> `ProjectPipeline` / `ProjectReadPipelines` -> `ProjectRepositoryProvider`.
> - `GET /api/projects/{id}/recommend/`, `GET /api/recommend/*`, `POST /api/recommend/calculate/`, `POST /api/recommend/tts/play/` -> `RecommendationPipeline` -> `RecommendationAbility` + `RecommendationModelStoreProvider` + `SpeechSynthesisProvider`.
> - `POST /api/association/analyze/` -> `AssociationAnalysisPipeline` -> `AssociationRuleAbility` + `DatasetProvider` + `AssociationRuleStoreProvider`.
> - `POST /api/voice/tts/`, `POST /api/voice/generate/` -> `VoiceSynthesisPipeline` -> `SpeechSynthesisProvider` (`EdgeTtsSpeechSynthesisAdapter`) + `GeneratedAssetProvider`.
> - `POST /api/ai-voice/broadcast/`, `GET /api/ai-voice/audio/{filename}/` -> `AIVoiceBroadcastPipeline` -> `VoiceBroadcastAbility` -> `LLMProvider` (`OpenAICompatibleLLMAdapter` / `AnthropicLLMAdapter`) + `SpeechSynthesisProvider` + `GeneratedAssetProvider`.
>
> The legacy chain `backend.services.analysis_service.run_project_analysis` is still registered as the default handler of `AnalysisJobProvider` until each step is migrated into ability composition.

### 4.1 Project Upload And Analysis

```text
POST /api/projects/{project_id}/upload/
  -> backend.api.projects.upload_dataset
  -> backend.core.storage.storage.get_project
  -> backend.core.storage.storage.get_project_dir
  -> local file write data/projects/{project_id}/dataset.csv
  -> backend.core.storage.storage.update_project(status=处理中)
  -> FastAPI BackgroundTasks.add_task(run_project_analysis)
  -> backend.services.analysis_service.run_project_analysis
  -> AssociationService.analyze
  -> PredictionService.analyze
  -> ClusteringService.analyze
  -> generate_analysis_report
  -> report markdown write
  -> TTSService.synthesize
  -> ModelBuilderService.build_and_save
  -> clear_recommender_cache
  -> backend.core.storage.storage.update_project(status=已完成/失败)
```

This is a complex lifecycle because it has upload, state transition, background execution, multiple analysis steps, generated artifacts, model build, cache invalidation, and failure status. It is a Business Flow candidate.

### 4.2 Project CRUD

```text
/api/projects/*
  -> backend.api.projects route handlers
  -> backend.core.storage.storage global instance
  -> data/projects.json
  -> data/projects/{project_id}/...
```

Current controller directly calls storage and handles missing project errors.

### 4.3 Project Customers Read Model

```text
GET /api/projects/{project_id}/customers/?cluster_id=...
  -> backend.api.projects.get_project_customers
  -> storage.get_project / storage.get_project_dir
  -> data/projects/{project_id}/customers.csv via pandas.read_csv
  -> optional filter by 客户分群
  -> frontend DTO field mapping
```

Controller contains data access and DTO construction.

### 4.4 Project Recommendation

```text
GET /api/projects/{project_id}/recommend/?item=...
  -> backend.api.projects.recommend_item
  -> storage.get_project
  -> backend.core.recommend.query_item_relations
  -> load_rules(dataset_path or fallback data/association_rules.*)
  -> pandas / mlxtend association rules
```

Controller bypasses service/pipeline and imports core algorithm directly.

### 4.5 Recommendation API

```text
GET /api/recommend/user/?user_id=...
  -> backend.api.recommend.recommend_for_user
  -> get_recommender()
  -> RecommendationSystem.recommend_user
  -> model/data loading from backend/data/model_data.pkl or CSV fallback
```

```text
GET /api/recommend/item/?item=...
  -> backend.api.recommend.recommend_for_item
  -> get_recommender()
  -> RecommendationSystem.recommend_item
```

```text
POST /api/recommend/calculate/
  -> backend.api.recommend.calculate_rules
  -> RecommendationSystem.calculate_realtime_rules
  -> mlxtend Apriori
  -> append backend/data/dynamic_rules.csv
```

```text
POST /api/recommend/tts/play/
  -> backend.api.recommend.play_tts
  -> generate_tts
  -> TTSService.synthesize
  -> outputs/audio/recommend_{project_id}.mp3
```

### 4.6 Association API

```text
POST /api/association/analyze/
  -> backend.api.association.analyze_association_rules
  -> global AssociationService.analyze
  -> pandas / mlxtend Apriori
  -> AssociationRuleResponse
```

### 4.7 Voice API

```text
POST /api/voice/tts/
  -> backend.api.voice.text_to_speech
  -> outputs/audio mkdir + filename creation
  -> TTSService.synthesize
  -> edge_tts.Communicate.save
  -> /outputs/audio/{filename}
```

```text
POST /api/voice/generate/
  -> backend.api.voice.generate_voice
  -> VoiceService.generate
  -> placeholder response
```

### 4.8 AI Voice API

```text
POST /api/ai-voice/broadcast/
  -> backend.api.ai_voice.generate_voice_broadcast
  -> AIVoiceService.generate_voice_broadcast
  -> AIVoiceService.generate_script
  -> httpx.AsyncClient to OpenAI-compatible or Anthropic-compatible API
  -> AIVoiceService.text_to_speech
  -> edge_tts.Communicate.save
  -> backend/data/audio/{filename}
  -> /api/ai-voice/audio/{filename}/
```

```text
GET /api/ai-voice/audio/{filename}/
  -> backend.api.ai_voice.get_audio_file
  -> check /tmp/{filename}
  -> check backend/data/audio/{filename}
  -> FileResponse
```

### 4.9 Inactive Routers

`backend/api/prediction.py` and `backend/api/clustering.py` are not registered in `backend/main.py`. Static scan found likely signature mismatches:

- `PredictionService()` is instantiated without required `data_path`.
- `service.forecast` is referenced but `PredictionService` exposes `analyze`.
- `ClusteringService()` is instantiated without required `data_path`.
- `service.analyze(method=...)` does not match the current `ClusteringService.analyze` signature.

Treat these as inactive risk anchors. Do not expose them without contract tests.

## 5. Frontend / Backend API Matrix

| Frontend File | Frontend Call | Method | Backend Route | Backend Handler | Request Shape | Response Shape | Frontend Depends On | Risk |
|---|---|---|---|---|---|---|---|---|
| `frontend/src/views/ProjectCreate.vue` | `/api/projects/` | POST | `POST /api/projects/` | `backend.api.projects.create_project` | `{name, description?, parameters?}`; `parameters` = `min_support`, `min_confidence`, `min_lift`, `forecast_weeks`, `n_clusters` | `ProjectResponse {success,message,data: Project}` | `success`, `data.id`, FastAPI `detail` on error | MED: project schema is broad and frontend relies on `data.id`. |
| `frontend/src/views/ProjectCreate.vue` | `/api/projects/{id}/upload/` | POST | `POST /api/projects/{project_id}/upload/` | `upload_dataset` | `multipart/form-data` with `file` | `{success,message,project_id}` | `success`, delayed navigation | LOW |
| `frontend/src/views/ProjectList.vue` | `/api/projects/` | GET | `GET /api/projects/` | `list_projects` | query `skip`, `limit` optional | `ProjectListResponse {success,message,total,data: Project[]}` | `success`, `data[]`, project fields | LOW |
| `frontend/src/views/ProjectList.vue` | `/api/projects/{id}/` | DELETE | `DELETE /api/projects/{project_id}/` | `delete_project` | path `project_id` | `{success,message}` | `success` | LOW |
| `frontend/src/views/ProjectDetail.vue` | `/api/projects/{id}/` | GET | `GET /api/projects/{project_id}/` | `get_project` | path `project_id` | `ProjectResponse` | `success`, `data.results.*`, `status` | MED: nested `results` fields drive UI. |
| `frontend/src/views/ProjectDetail.vue` | `/api/projects/{id}/reanalyze/` | POST | `POST /api/projects/{project_id}/reanalyze/` | `reanalyze_project` | path `project_id` | `{success,message}` | `success`, 1s delayed reload | LOW |
| `frontend/src/views/ProjectDetail.vue` | `/api/projects/{id}/customers/` | GET | `GET /api/projects/{project_id}/customers/` | `get_project_customers` | query `cluster_id?` | `{success,data}` | customer `id`, `name`, `recency`, `frequency`, `monetary`, `cluster_id` | LOW |
| `frontend/src/views/ProjectDetail.vue` | `/api/recommend/item/` | GET | `GET /api/recommend/item/` | `recommend_for_item` | query `{item}` | `{item,upstream,downstream,target_customers,success}` | `downstream[].item`, `confidence`, `lift` | LOW |
| `frontend/src/views/ProjectDetail.vue` | `/api/recommend/calculate/` | POST | `POST /api/recommend/calculate/` | `calculate_rules` | `{item, min_confidence?}` | `{success,item,rules,source}` or `{success:false,message,rules:[]}` | `success`, `rules`, `rules.length` | LOW |
| `frontend/src/views/ProjectDetail.vue` | `/api/recommend/user/` | GET | `GET /api/recommend/user/` | `recommend_for_user` | query `{user_id}` | `{item,recommends,target_customers,speech,model_tries,human_fallback,warning}` | `recommends[]`, `target_customers[]` | LOW |
| `frontend/src/views/ProjectDetail.vue` | `/api/ai-voice/broadcast/` | POST | `POST /api/ai-voice/broadcast/` | `generate_voice_broadcast` | `{data,llm_config,scene_type,tts_config?}` | `{success,text,audio_url}` | `success`, `text`, `audio_url`, `detail` | MED: payload `data` is arbitrary JSON. |
| `frontend/src/views/CustomerAnalysis.vue` | `/api/projects/{id}/` | GET | `GET /api/projects/{project_id}/` | `get_project` | path `project_id` | `ProjectResponse` | `success`, `data` | LOW |
| `frontend/src/views/CustomerAnalysis.vue` | `/api/projects/{id}/customers/` | GET | `GET /api/projects/{project_id}/customers/` | `get_project_customers` | path `project_id`; no query | `{success,data}` | `data[]` customer fields | LOW |
| `frontend/src/views/CustomerAnalysis.vue` | `/api/recommend/user/` | GET | `GET /api/recommend/user/` | `recommend_for_user` | query `{user_id}` | `{recommends,target_customers,...}` | `target_customers[0]`, `recommends[]` | LOW |
| `frontend/src/views/CustomerAnalysis.vue` | `/api/ai-voice/broadcast/` | POST | `POST /api/ai-voice/broadcast/` | `generate_voice_broadcast` | `{data,llm_config,tts_config:null,scene_type:'summary'}` | `{success,text,audio_url}` | `success`, `text`, `detail` | MED |
| `frontend/src/views/CustomerAnalysis.vue` | `/api/voice/tts/` | POST | `POST /api/voice/tts/` | `backend.api.voice.text_to_speech` | `{text,voice,rate,volume}` | `{success,audio_url,text}` | `success`, `audio_url` | LOW |
| `frontend/src/views/ProductRecommend.vue` | `/api/recommend/item/` | GET | `GET /api/recommend/item/` | `recommend_for_item` | query `{item}` | `{item,upstream,downstream,target_customers,success}` | `upstream[]`, `downstream[]`, `confidence`, `item` | LOW |
| `frontend/src/views/ProductRecommend.vue` | `${llmConfig.baseUrl}/chat/completions` | POST | external | none | OpenAI-compatible `{model,messages}` + Bearer key | external `{choices[0].message.content}` | `choices[0].message.content` | HIGH: external contract outside backend. |
| `frontend/src/views/ProductRecommend.vue` | `/api/voice/tts/` | POST | `POST /api/voice/tts/` | `text_to_speech` | `{text,voice,rate,volume}` | `{success,audio_url,text}` | `success`, `audio_url` | LOW |
| `frontend/src/views/ProductRecommend.vue` | `/api/recommend/user/` | GET | `GET /api/recommend/user/` | `recommend_for_user` | query `{user_id}` | `{recommends,target_customers,...}` | `recommends[0].item` | LOW |
| `frontend/src/views/Settings.vue` | `${llmConfig.baseUrl}/models` | GET | external | none | provider-specific auth headers | external; status checked | `response.status === 200`, external error message | HIGH: external contract outside backend. |
| `frontend/src/views/Settings.vue` | `/api/voice/tts/` | POST | `POST /api/voice/tts/` | `text_to_speech` | `{text,voice,rate,volume}` | `{success,audio_url,text}` | `success`, `audio_url`, audio playback events | LOW |

Additional frontend observations:

- `frontend/src/utils/http.ts` exports an Axios instance without `baseURL`, interceptor, retry, polling, or streaming.
- `frontend/vite.config.ts` proxies `/api` and `/outputs` to `http://localhost:8000`.
- No active `fetch`, `ky`, GraphQL, WebSocket, or EventSource calls were found.
- `frontend/src/components/ServiceStatus.vue` contains a comment for `/api/status`, but active logic uses mock data and 30-second polling. Backend exposes `/api/health/`, not `/api/status`.

## 6. Direct External Access Points

### 6.1 SDK Direct Access

| File | Direct Access | Current Caller | Target Boundary |
|---|---|---|---|
| `backend/services/tts_service.py` | `edge_tts.Communicate`, `edge_tts.list_voices` | `backend/api/voice.py`, `analysis_service.py`, `recommender_service.py` | `SpeechSynthesisProvider` -> `EdgeTtsSpeechSynthesisAdapter` |
| `backend/services/ai_voice_service.py` | `edge_tts.Communicate` | `backend/api/ai_voice.py` | `SpeechSynthesisProvider` -> `EdgeTtsSpeechSynthesisAdapter` |
| `backend/services/ai_voice_service.py` | `httpx.AsyncClient` to OpenAI-compatible / Anthropic-compatible APIs | `backend/api/ai_voice.py` | `LLMProvider` -> `OpenAICompatibleLLMAdapter` / `AnthropicLLMAdapter` |
| `backend/services/association_service.py` | `pandas`, `mlxtend.frequent_patterns`, `TransactionEncoder` | `association API`, `analysis_service.py` | `AssociationRuleAbility`; dataset read via provider |
| `backend/core/recommend.py` | `pandas`, `mlxtend`, `sklearn.cluster.KMeans` | `projects.recommend_item`, `core.analysis` | `RecommendationAbility`; rule/dataset provider |
| `backend/services/prediction_service.py` | `pandas`, `sklearn.linear_model.Ridge`, `StandardScaler` | `analysis_service.py` | `SalesForecastAbility`; dataset read provider |
| `backend/services/clustering_service.py` | `pandas`, `sklearn.cluster.KMeans`, `mlxtend` | `analysis_service.py` | `CustomerClusteringAbility`; customer store provider |
| `backend/services/model_builder_service.py` | `pandas`, `sklearn.cluster.KMeans`, `pickle` | `analysis_service.py` | `RecommendationModelBuildAbility` + `RecommendationModelStoreProvider` |

### 6.2 DB Direct Access

No SQL/NoSQL database client, ORM, migration, transaction, Redis, or DB URL was found in `/backend`. Current persistence is local JSON and filesystem.

UNKNOWN: whether production deployment intends to replace local JSON with a database. This must be clarified before irreversible repository design.

### 6.3 Storage Direct Access

| File | Storage Access | Side Effect |
|---|---|---|
| `backend/core/storage.py` | `data/projects.json`, `data/projects/{project_id}` | JSON project read/write, project directory create/delete |
| `backend/api/projects.py` | upload file write, report/audio/customers path probing | writes dataset, reads generated artifacts and customers CSV |
| `backend/services/analysis_service.py` | report markdown write, project status update, customers CSV via clustering service, audio path write | generated reports/audio/status |
| `backend/services/model_builder_service.py` | `backend/data/model_data.pkl` | recommender model artifact write |
| `backend/services/recommender_service.py` | CSV/pickle reads, `backend/data/dynamic_rules.csv`, `outputs/audio` | model/data load, dynamic rule append, TTS output |
| `backend/api/voice.py` | `outputs/audio` | TTS file path creation and existence check |
| `backend/api/ai_voice.py` | `/tmp/{filename}`, `backend/data/audio/{filename}` | audio lookup and response |
| `backend/services/ai_voice_service.py` | tempfile, `backend/data/audio` | generated audio write |

### 6.4 HTTP API Direct Access

| File | HTTP API | Current Semantics |
|---|---|---|
| `backend/services/ai_voice_service.py` | `{base_url}/chat/completions` | OpenAI-compatible chat completion; 30s timeout; response parsed from `choices[0].message.content`. |
| `backend/services/ai_voice_service.py` | `{base_url}/messages` | Anthropic-compatible messages API; 30s timeout; response parsed from `content[0].text`. |

Frontend also directly calls external LLM endpoints from `ProductRecommend.vue` and `Settings.vue`; this is outside backend migration scope but is a behavior dependency risk.

### 6.5 Queue / Worker Direct Access

No queue client found. FastAPI `BackgroundTasks` is used as runtime scheduling in `backend/api/projects.py`.

Target: represent this capability as `AnalysisJobProvider` only if the job lifecycle stays asynchronous. It can be backed initially by a FastAPI BackgroundTasks adapter or an in-process scheduler adapter.

## 7. Env / Config Read Points

| File | Read Point | Variables / Settings | Current Consumer | Target Strategy |
|---|---|---|---|---|
| `backend/core/config.py` | `Settings(BaseSettings)` + `.env` | `APP_NAME`, `APP_VERSION`, `DEBUG`, `API_PREFIX`, `CORS_ORIGINS`, `DATA_PATH`, `OUTPUT_DIR`, `CHARTS_DIR`, `REPORTS_DIR`, `AUDIO_DIR`, algorithm defaults, `TTS_VOICE` | `backend/main.py`, `AssociationService`, unused import in `api/recommend.py` | Keep Settings as the only env reader; pass Settings into Provider Factory. |
| `backend/main.py` | `settings.CORS_ORIGINS` | CORS origins | FastAPI bootstrap | Acceptable in bootstrap. |
| `backend/services/association_service.py` | `settings.DATA_PATH`, `settings.CHARTS_DIR` | default dataset/chart path | service constructor | Move into Provider Factory / Adapter config; business ability receives data input explicitly. |
| `backend/api/recommend.py` | imports `settings` | no static usage found | none | Remove during cleanup if still unused after migration. |

Direct `os.environ` / `os.getenv` in application source: none found. Matches under virtual environment files were ignored.

## 8. Cross-layer Import Violations

### 8.1 Pre-migration baseline (historical)

| Importing File | Imported Object | Violation | Target Direction | Status |
|---|---|---|---|---|
| `backend/api/projects.py` | `backend.core.storage.storage` | API Controller imports storage adapter/global repository directly | Controller -> Pipeline -> Provider Interface | Resolved in Phase 7 |
| `backend/api/projects.py` | `backend.core.recommend.query_item_relations` | API Controller imports algorithm/core directly | Controller -> Recommendation Pipeline -> Ability | Resolved in Phase 7 |
| `backend/api/projects.py` | `backend.services.analysis_service.run_project_analysis` | Controller schedules concrete business function directly | Controller -> Flow/Pipeline -> Job Provider | Resolved in Phase 7 |
| `backend/api/association.py` | `AssociationService()` global | Controller constructs concrete service globally | Controller -> Pipeline via dependency/provider wiring | Resolved in Phase 7 |
| `backend/api/voice.py` | `VoiceService()`, `TTSService()` globals | Controller constructs service and SDK-facing wrapper | Controller -> Voice Pipeline -> Provider Interface | Resolved in Phase 7 |
| `backend/api/recommend.py` | `get_recommender`, `generate_tts` | Controller calls cached concrete service and TTS helper | Controller -> Recommendation Pipeline | Resolved in Phase 7 |
| `backend/api/ai_voice.py` | `AIVoiceService` | Controller calls service that directly reaches LLM/TTS SDKs | Controller -> AI Voice Pipeline -> Abilities -> Providers | Resolved in Phase 7 |
| `backend/services/analysis_service.py` | `backend.core.storage.storage` | Business service imports concrete storage | Flow -> Provider Interface | Resolved in Phase 8 (flow routes through providers; legacy module retained only as background-job default handler) |
| `backend/services/ai_voice_service.py` | `httpx`, `edge_tts` | Business service imports HTTP client and TTS SDK | Ability -> Provider Interface -> Adapter | Resolved in Phase 9 (module deleted) |
| `backend/services/tts_service.py` | `edge_tts` | SDK wrapper located in service layer, no provider boundary | Provider Interface -> Adapter | Resolved in Phase 8 (replaced by `SpeechSynthesisProvider` + `EdgeTtsSpeechSynthesisAdapter`; legacy module retained as inactive controller dep) |
| `backend/services/recommender_service.py` | `TTSService` | Recommendation service calls TTS concrete implementation | Pipeline -> SpeechSynthesisProvider | Resolved in Phase 8 (recommendation pipeline now consumes `SpeechSynthesisProvider`; legacy module retained for analysis cache invalidation hook) |

### 8.2 Active controllers (post-migration)

Controllers under `backend/api/{projects,recommend,association,voice,ai_voice}.py` import only `fastapi`, `pydantic`, `backend.api.dependencies`, `backend.api.error_mapping`, `backend.business.pipelines.*`, `backend.core.errors`, and `backend.models.schemas`. The static guard `tests/api/test_controller_thinness.py` enforces the forbidden-prefix list `(backend.services, backend.core.storage, backend.core.recommend, backend.infrastructure, edge_tts, httpx, pandas, sklearn, mlxtend, shutil)`.

### 8.3 Residual references (intentionally retained)

| Module | Caller | Reason for retention |
|---|---|---|
| `backend/api/prediction.py`, `backend/api/clustering.py` | not registered in `backend/main.py` | Pre-existing inactive routers; out of Phase 9 deletion scope. They still import `backend.services.prediction_service` / `clustering_service`. |
| `backend/services/{analysis,association,clustering,model_builder,prediction,recommender,tts}_service.py` | `backend/infrastructure/factories/provider_factory.py` (only `analysis_service.run_project_analysis` + `recommender_service.clear_recommender_cache`), inactive controllers, and `tests/business/test_project_analysis_current_behavior.py` | Legacy chain still wired as `FastapiBackgroundAnalysisJobAdapter` default handler. Removal requires moving every step of `run_project_analysis` into ability/pipeline composition + replacing the recommender cache-clear hook, which exceeds the Phase 9 cleanup scope. |
| `backend/core/storage.py` | `backend/infrastructure/adapters/json_project_repository_adapter.py`, legacy `analysis_service`, two test fixtures | `JsonProjectRepositoryAdapter` wraps `ProjectStorage` to keep on-disk schema identical; deletion requires inlining the JSON read/write semantics into the adapter and migrating tests. |

### 8.4 Removed in Phase 9 (no remaining references)

- `backend/services/voice_service.py`
- `backend/services/ai_voice_service.py`
- `backend/core/analysis.py`
- `backend/core/recommend.py`

`backend/utils/` exists as an empty package. No active imports were found. Do not expand it as a fallback module.

## 9. Behavior Anchors

### 9.1 Public API Contracts

| Path | Method | Request Schema | Success Response | Error Semantics | Status Codes Observed / Expected |
|---|---|---|---|---|---|
| `/` | GET | none | `{message,version,docs}` | none | 200 |
| `/api/health/` | GET | none | `{status:'healthy',service:'MarketMind Backend'}` | none | 200 |
| `/api/projects/` | POST | `ProjectCreate {name, description?, parameters?}` | `ProjectResponse {success,message,data: Project}` | `HTTPException 500 detail='创建项目失败: ...'` | 200 current; 500 on exception |
| `/api/projects/{project_id}/upload/` | POST | multipart `file`; path `project_id` | `{success,message,project_id}` | 404 project missing; 400 unsupported file; 500 upload failure | 200, 400, 404, 500 |
| `/api/projects/` | GET | query `skip=0`, `limit=100` | `ProjectListResponse {success,message,total,data}` | 500 list failure | 200, 500 |
| `/api/projects/{project_id}/` | GET | path `project_id` | `ProjectResponse` | 404 project missing | 200, 404 |
| `/api/projects/{project_id}/` | PUT | `ProjectUpdate {name?,description?,status?,parameters?}` | `ProjectResponse` | 404 project missing | 200, 404 |
| `/api/projects/{project_id}/` | DELETE | path `project_id` | `{success,message}` | 404 project missing | 200, 404 |
| `/api/projects/{project_id}/reanalyze/` | POST | path `project_id` | `{success,message}` | 404 project missing; 400 missing dataset | 200, 400, 404 |
| `/api/projects/{project_id}/download/report/` | GET | path `project_id` | Markdown `FileResponse` | 404 project/report missing | 200, 404 |
| `/api/projects/{project_id}/customers/` | GET | query `cluster_id?` | `{success,data}` | 404 project missing; 500 CSV read failure | 200, 404, 500 |
| `/api/projects/{project_id}/audio/` | GET | path `project_id` | MP3 `FileResponse` | 404 project/audio missing | 200, 404 |
| `/api/projects/{project_id}/recommend/` | GET | query `item` | recommendation dict from `query_item_relations` | UNKNOWN: no handler-level exception mapping | 200; other status UNKNOWN |
| `/api/association/analyze/` | POST | `AssociationRuleRequest {min_support,min_confidence,min_lift,top_n}` | `AssociationRuleResponse` | 500 detail from exception | 200, 500 |
| `/api/association/status/` | GET | none | `{success,status,message}` | none | 200 |
| `/api/recommend/user/` | GET | query `user_id` | `{item,recommends,target_customers,speech,model_tries,human_fallback,warning}` | 404 dataset missing; 500 recommendation failure | 200, 404, 500 |
| `/api/recommend/item/` | GET | query `item` | `{item,upstream,downstream,target_customers,success}` | 500 recommendation failure | 200, 500 |
| `/api/recommend/calculate/` | POST | `{item,min_confidence=0.1}` | `{success,item,rules,source}` or `{success:false,message,rules:[]}` | 404 dataset missing; 500 realtime calculation failure | 200, 404, 500 |
| `/api/recommend/tts/play/` | POST | `{project_id?,speech}` | `{success,audio_url,speech}` | 500 TTS failure | 200, 500 |
| `/api/voice/tts/` | POST | `{text,voice?,rate?,volume?}` | `{success,audio_url,text}` | 500 TTS synthesis failure | 200, 500 |
| `/api/voice/generate/` | POST | `VoiceRequest {text?,voice,include_modules}` | `VoiceResponse {success,message,text,audio_url,duration?}` | 500 detail | 200, 500 |
| `/api/voice/status/` | GET | none | `{success,status,message}` | none | 200 |
| `/api/ai-voice/broadcast/` | POST | `{data,llm_config,scene_type,tts_config?}` | `{success,text,audio_url}` | 500 detail when service returns unsuccessful result | 200, 500 |
| `/api/tts/` | POST | `{text,voice?,rate?,volume?}` | `{success,audio_url}` | 500 TTS failure | 200, 500 |
| `/api/ai-voice/audio/{filename}/` | GET | path `filename` | MP3 `FileResponse` | 404 audio missing | 200, 404 |

### 9.2 Critical Business Paths

| Business Path | Current Entry | Behavior Anchor |
|---|---|---|
| Project creation | `POST /api/projects/` | returns generated UUID under `data.id`; creates `data/projects/{id}` directories through storage. |
| Dataset upload and analysis | `POST /api/projects/{id}/upload/` | accepts CSV/XLS/XLSX by filename; writes `dataset.csv`; sets status `处理中`; schedules background analysis. |
| Reanalysis | `POST /api/projects/{id}/reanalyze/` | requires `dataset_path`; sets status `处理中`; schedules same analysis function. |
| Analysis completion | `run_project_analysis` | writes report/audio/model/customers; status becomes `已完成`; failure sets `失败` and `error_message`. |
| Customer cluster browse | `/customers/` | returns normalized frontend fields from `customers.csv` or fallback clustering result. |
| Recommendation | `/api/recommend/*`, `/api/projects/{id}/recommend/` | returns upstream/downstream/recommends structures consumed by frontend views. |
| AI broadcast | `/api/ai-voice/broadcast/` | external LLM call plus TTS; returns text and playable URL. |
| TTS | `/api/voice/tts/`, `/api/recommend/tts/play/`, `/api/tts/` | generates MP3 file and returns URL. |

### 9.3 Side Effects

| Side Effect | Current Location | Behavior That Must Stay Equivalent |
|---|---|---|
| JSON project write | `data/projects.json` via `ProjectStorage` | project list and status persistence. |
| Project directory create/delete | `data/projects/{id}` | outputs subfolders exist for charts/reports/audio. |
| Uploaded dataset write | `data/projects/{id}/dataset.csv` | backend analysis uses this path. |
| Customers CSV write/read | `data/projects/{id}/customers.csv` | frontend customer list fields. |
| Report markdown write | `data/projects/{id}/outputs/reports/report_{id}.md` | download route returns markdown. |
| Project audio write | `data/projects/{id}/outputs/audio/report_{id}.mp3` | project audio route returns MP3. |
| Static audio write | `outputs/audio/tts_*.mp3`, `outputs/audio/recommend_*.mp3` | frontend plays `/outputs/audio/...`. |
| AI audio write | `backend/data/audio/{filename}` and `/tmp/{filename}` lookup | frontend plays `/api/ai-voice/audio/{filename}/`. |
| Model artifact write | `backend/data/model_data.pkl` | recommender cache/model loading. |
| Dynamic rules append | `backend/data/dynamic_rules.csv` | realtime calculation persistence. |
| Cache invalidation | `clear_recommender_cache()` | recommendation uses new model after analysis. |
| Logs | `print` and `logging` in services/controllers | trace semantics are informal; no structured trace IDs. |
| External API call | LLM HTTP API, Edge TTS | network side effects and error responses must be isolated before migration. |

### 9.4 Error Semantics

| Error Category | Current Semantics | Migration Risk |
|---|---|---|
| Validation error | FastAPI/Pydantic 422 for request schema; manual 400 for unsupported upload file | Preserve status codes and `detail` field. |
| Not found | 404 `detail` for missing project/report/audio/dataset | Frontend reads `error.response.data.detail`. |
| Provider error | LLM/TTS errors often become 500 `detail` strings | Must convert external errors to internal `ProviderError` before HTTP mapping. |
| Infrastructure error | JSON/file/CSV exceptions often become 500 `detail` strings or fallback empty list | Preserve visible fallback vs failure behavior. |
| Timeout | LLM `httpx.AsyncClient(timeout=30.0)`; Edge TTS timeout UNKNOWN | Define provider timeout DTO/error without changing current visible behavior. |
| Retry | No retry found | Do not add retries during architecture migration unless separately approved. |
| Partial failure | Analysis failure sets project status `失败` and `error_message`; individual step partial result semantics UNKNOWN | Tests must anchor project status transition and outputs. |

### 9.5 Frontend-dependent Behaviors

- Project status strings are Chinese enum values: `待处理`, `处理中`, `已完成`, `失败`. Frontend maps these values and uses `处理中` for loading state.
- Internal API errors are consumed through FastAPI `detail` in several views.
- Internal APIs rely on Axios non-2xx rejection. No internal frontend branch explicitly depends on a numeric backend status code except general error handling.
- External settings page checks external LLM `response.status === 200`.
- `/api/voice/tts/` returns `/outputs/audio/...`; `/api/ai-voice/broadcast/` returns `/api/ai-voice/audio/{filename}/`.
- No backend streaming format is currently used.
- No backend polling endpoint is active; `ServiceStatus.vue` polls mock data every 30 seconds.
- Reanalysis UI does a single delayed `loadProject` after 1000 ms, not job polling.

## 10. Target Architecture

### 10.1 API Controller Layer

Existing `backend/api/*.py` remains the HTTP boundary. Target responsibilities:

- Receive path/query/body/file inputs.
- Use Pydantic request/response schemas.
- Call one Business Pipeline or Business Flow.
- Map internal errors to current public error status and `detail` messages.
- Return current response shapes and file response behavior through explicit output DTOs or approved asset-serving boundary.

Target directory:

```text
backend/api/
  projects.py
  association.py
  recommend.py
  voice.py
  ai_voice.py
  prediction.py      # stays inactive unless contract tests and route registration are approved
  clustering.py      # stays inactive unless contract tests and route registration are approved
```

### 10.2 Business Orchestration Layer

Target directory:

```text
backend/business/
  flows/
    project_analysis_flow.py
  pipelines/
    project_pipeline.py
    dataset_upload_pipeline.py
    project_customer_pipeline.py
    project_recommendation_pipeline.py
    recommendation_pipeline.py
    association_analysis_pipeline.py
    voice_synthesis_pipeline.py
    ai_voice_broadcast_pipeline.py
```

Business Flow is justified for `ProjectAnalysisFlow` because the current path has background lifecycle, state transition, multiple analysis steps, generated artifacts, cache invalidation, and failure status.

All other routes should default to Pipeline unless a later scan proves multi-pipeline lifecycle, pause/resume/cancel, compensation, or long-running state machine.

### 10.3 Ability Layer

Target directory:

```text
backend/abilities/
  association/
    analyze_association_rules.py
    calculate_realtime_rules.py
  prediction/
    forecast_sales.py
  clustering/
    cluster_customers.py
    build_cluster_association_rules.py
  recommendation/
    recommend_for_user.py
    recommend_for_item.py
    build_recommendation_model.py
  report/
    generate_analysis_report.py
    generate_speech_text.py
  voice/
    synthesize_speech.py
    generate_broadcast_script.py
```

Ability Atoms receive explicit DTO/dataframes/values and Providers Container. They do not import FastAPI request/response, SDK clients, storage clients, env readers, or External Adapters.

#### Ability-Level Debug Event Contract

Every Ability Atom must emit or allow its caller Pipeline to emit the same stable event set:

- `ability.started`
- `ability.completed`
- `ability.failed`

Required common fields:

| Field | Rule |
|---|---|
| `ability_run_id` | Required per ability execution; may be created by the caller Pipeline before invoking the ability. |
| `trace_id` | Required; inherited from API request, background job, Flow, or Pipeline context. |
| `pipeline_run_id` | Required when the ability is invoked by a Pipeline. |
| `flow_run_id` | Required when the ability is invoked inside `ProjectAnalysisFlow`. |
| `ability_name` | Stable code-facing name, for example `forecast_sales` or `generate_broadcast_script`; never derived from user input. |
| `operation` | Stable business operation, for example `project_analysis`, `recommendation_lookup`, or `voice_broadcast`. |
| `stage` | Stable stage name matching the Pipeline step that invoked the ability. |
| `input_summary` | Redaction-safe summary only: row counts, field names, thresholds, top-n values, item/user ids, dataset/project ids, and content hashes. |
| `output_summary` | Redaction-safe summary only: result counts, boolean flags, artifact ids/paths after provider storage, score ranges, and model/rule counts. |
| `provider_used` | Provider interface names used by this ability, or empty list for pure algorithm abilities. |
| `duration_ms` | Required on completed/failed events. |
| `error_type` | Required on failed events; use internal error class or stable exception category. |

Prohibited fields and values:

- Raw uploaded file content, full dataset rows, full prompt text, full LLM response text, raw generated speech text, API keys, authorization headers, tokens, cookies, environment variables, and raw external SDK responses.
- User input concatenated into event names, `ability_name`, `operation`, or `stage`.
- Generic module names such as `utils`, `helpers`, `common`, or `misc`.

Ability-specific summaries:

| Ability | `input_summary` | `output_summary` | `provider_used` |
|---|---|---|---|
| `analyze_association_rules` | `row_count`, `order_count`, `item_column_present`, `min_support`, `min_confidence`, `min_lift`, `top_n` | `rule_count`, `chart_count`, `success` | `[]` |
| `calculate_realtime_rules` | `row_count`, `order_count`, `item_name`, `min_confidence`, `top_n` | `rule_count`, `rows_to_persist_count` | `[]` |
| `forecast_sales` | `row_count`, `week_count`, `forecast_weeks`, available numeric fields | `success`, `forecast_count`, `train_samples`, `sales_r2`, `profit_r2` | `[]` |
| `cluster_customers` | `row_count`, `customer_count`, `n_clusters` | `success`, `customer_count`, `cluster_count`, `silhouette_score` | `[]` |
| `build_cluster_association_rules` | `row_count`, `customer_count`, `cluster_count`, `min_support`, `min_confidence` | `cluster_count`, `rule_count_by_cluster` | `[]` |
| `build_recommendation_model` | `row_count`, `customer_count`, `n_clusters`, `association_rule_count` | `success`, `total_customers`, `n_clusters`, `n_rules`, `n_subcategories` | `[]` |
| `recommend_for_user` | `row_count`, `user_id`, `has_model`, `top_n` | `recommend_count`, `has_cluster`, `fallback_used` | `[]` |
| `recommend_for_item` | `item_name`, `has_model`, `has_dataset`, `top_n` | `upstream_count`, `downstream_count`, `target_customer_count` | `[]` |
| `generate_analysis_report` | `project_id`, `has_results`, `association_rule_count`, `forecast_count`, `cluster_count` | `report_character_count`, `section_count` | `[]` |
| `generate_speech_text` | `project_id`, `association_rule_count`, `forecast_count`, `cluster_count` | `speech_character_count` | `[]` |
| `synthesize_speech` | `text_hash`, `text_length`, `voice`, `rate`, `volume`, `output_path_kind` | `audio_path_kind`, `has_audio_url`, `duration_seconds` | `["SpeechSynthesisProvider"]` |
| `generate_broadcast_script` | `scene_type`, `data_field_names`, `data_hash`, `provider`, `model` | `script_hash`, `script_length`, `fallback_used` | `["LLMProvider"]` |

If a pure Ability Atom does not receive a `TelemetryProvider` directly, its caller Pipeline is responsible for emitting `ability.started`, `ability.completed`, and `ability.failed` around the call using these summaries. Provider-calling abilities may emit directly only through `TelemetryProvider`; they must still avoid concrete logging or tracing imports.

### 10.4 Provider Boundary

Target directory:

```text
backend/providers/
  container.py
  dtos.py
  telemetry_dtos.py
  project_repository_provider.py
  project_file_storage_provider.py
  generated_asset_provider.py
  dataset_provider.py
  association_rule_store_provider.py
  recommendation_model_store_provider.py
  speech_synthesis_provider.py
  llm_provider.py
  analysis_job_provider.py
  telemetry_provider.py
```

Provider names describe business capability. Vendor names are allowed only in External Adapter classes/files.

### 10.5 Infrastructure Layer

Target directory:

```text
backend/infrastructure/
  adapters/
    json_project_repository_adapter.py
    local_project_file_storage_adapter.py
    local_generated_asset_adapter.py
    csv_dataset_adapter.py
    local_association_rule_store_adapter.py
    local_recommendation_model_store_adapter.py
    edge_tts_speech_synthesis_adapter.py
    openai_compatible_llm_adapter.py
    anthropic_llm_adapter.py
    fastapi_background_analysis_job_adapter.py
    console_telemetry_adapter.py
    file_telemetry_adapter.py
  factories/
    provider_factory.py
```

Infrastructure Adapters implement Provider Interfaces and may import SDKs, filesystem APIs, HTTP clients, FastAPI background runtime adapters, or data persistence clients. They must return internal DTOs and convert external exceptions to internal errors.

## 11. Provider Boundary Design

### 11.1 Provider Interfaces

| Provider Interface | Business Capability | Methods | Input DTO | Output DTO | External Adapter | Current Direct Call Sites |
|---|---|---|---|---|---|---|
| `ProjectRepositoryProvider` | Project metadata persistence | `create_project`, `get_project`, `list_projects`, `update_project`, `delete_project`, `count_projects` | `Project`, `ProjectUpdateData`, `Pagination` | `Project`, `ProjectList`, `bool` | `JsonProjectRepositoryAdapter` | `backend/api/projects.py`, `backend/services/analysis_service.py`, `backend/core/storage.py` |
| `ProjectFileStorageProvider` | Project workspace files | `save_uploaded_dataset`, `get_project_workspace`, `read_customers`, `write_customers` | `ProjectId`, `UploadedDataset`, `CustomerRows` | `DatasetLocation`, `ProjectWorkspace`, `CustomerRows` | `LocalProjectFileStorageAdapter` | `backend/api/projects.py`, `analysis_service.py`, `clustering_service.py` |
| `GeneratedAssetProvider` | Generated reports/audio asset storage and lookup | `save_report`, `resolve_report`, `save_audio`, `resolve_audio`, `resolve_ai_audio` | `GeneratedReport`, `GeneratedAudio`, `AssetLookup` | `AssetLocation`, `AssetStreamRef` | `LocalGeneratedAssetAdapter` | `backend/api/projects.py`, `backend/api/voice.py`, `backend/api/ai_voice.py`, `analysis_service.py` |
| `DatasetProvider` | Dataset loading | `load_sales_dataset`, `load_customer_dataset` | `DatasetLocation` | `TabularDataset` | `CsvDatasetAdapter` | `association_service.py`, `prediction_service.py`, `clustering_service.py`, `recommender_service.py`, `core/recommend.py` |
| `AssociationRuleStoreProvider` | Rule artifact persistence | `load_rules`, `save_dynamic_rules`, `build_rules_from_dataset` if persisted | `RuleLookup`, `RuleRows` | `AssociationRules` | `LocalAssociationRuleStoreAdapter` | `backend/core/recommend.py`, `recommender_service.py` |
| `RecommendationModelStoreProvider` | Recommendation model artifact storage | `save_model`, `load_model`, `clear_cache_signal` | `RecommendationModelArtifact` | `RecommendationModelArtifact`, `ModelStatus` | `LocalRecommendationModelStoreAdapter` | `model_builder_service.py`, `recommender_service.py` |
| `SpeechSynthesisProvider` | Text-to-speech generation | `synthesize` | `SpeechSynthesisRequest` | `GeneratedAudio` | `EdgeTtsSpeechSynthesisAdapter` | `tts_service.py`, `ai_voice_service.py`, `api/voice.py`, `recommender_service.py` |
| `LLMProvider` | Broadcast/script text generation | `generate_broadcast_script` | `LLMGenerationRequest` | `GeneratedScript` | `OpenAICompatibleLLMAdapter`, `AnthropicLLMAdapter` | `ai_voice_service.py`; frontend external calls remain out of backend scope |
| `AnalysisJobProvider` | Analysis background scheduling | `schedule_project_analysis` | `ProjectAnalysisJobRequest` | `JobSubmission` | `FastApiBackgroundAnalysisJobAdapter` or in-process adapter | `backend/api/projects.py` |
| `TelemetryProvider` | Layer-level debug logging, audit events, trace/span lifecycle | `emit_debug_event`, `emit_audit_event`, `emit_error_event`, `start_span`, `end_span` | `DebugEvent`, `AuditEvent`, `ErrorEvent`, `SpanContext` | `TelemetryResult`, `SpanHandle` | `ConsoleTelemetryAdapter`, `FileTelemetryAdapter`; future `OpenTelemetryAdapter`, `SentryAdapter`, database audit adapter, self-hosted trace adapter | current `logging` in `backend/api/voice.py`, `backend/api/ai_voice.py`, `backend/services/tts_service.py`; current `print` in analysis/recommendation services |

### 11.2 Providers Container

Actual fields required by current backend:

```python
@dataclass(frozen=True)
class ProvidersContainer:
    repository: ProjectRepositoryProvider
    storage: ProjectFileStorageProvider
    assets: GeneratedAssetProvider
    dataset: DatasetProvider
    association_rules: AssociationRuleStoreProvider
    recommendation_models: RecommendationModelStoreProvider
    speech: SpeechSynthesisProvider
    llm: LLMProvider
    analysis_jobs: AnalysisJobProvider
    telemetry: TelemetryProvider
```

Fields intentionally not included because current backend has no direct use:

- `browser`
- `queue` as external queue client; `analysis_jobs` covers current FastAPI BackgroundTasks semantics.
- `auth`
- `email`
- `payment`

### 11.3 Provider Factory

Required direction:

```text
Settings -> Provider Factory -> External Adapter -> Providers Container
```

Target responsibilities:

- `backend/core/config.py` remains the only env/settings reader in the first migration phase.
- `backend/infrastructure/factories/provider_factory.py` receives `Settings` and creates concrete adapters.
- `backend/providers/container.py` exposes typed provider fields.
- Business Pipeline / Flow / Ability receives `ProvidersContainer` and never reads env or creates adapters.
- Vendor selection for LLM moves from `AIVoiceService` to Provider Factory.

### 11.4 External Adapters

| External Adapter | Implements | Vendor / Runtime Detail | Error Conversion |
|---|---|---|---|
| `JsonProjectRepositoryAdapter` | `ProjectRepositoryProvider` | local `data/projects.json` | file/json errors -> `InfrastructureError` |
| `LocalProjectFileStorageAdapter` | `ProjectFileStorageProvider` | local `data/projects/{id}` | file/path errors -> `InfrastructureError` |
| `LocalGeneratedAssetAdapter` | `GeneratedAssetProvider` | local `outputs/`, `data/projects/{id}/outputs`, `backend/data/audio`, `/tmp` lookup if retained | missing asset -> internal not-found error |
| `CsvDatasetAdapter` | `DatasetProvider` | pandas CSV read | parse/read errors -> `InfrastructureError` |
| `LocalAssociationRuleStoreAdapter` | `AssociationRuleStoreProvider` | local CSV/pickle rule files | parse/read/write errors -> `InfrastructureError` |
| `LocalRecommendationModelStoreAdapter` | `RecommendationModelStoreProvider` | pickle model artifact | missing model -> model unavailable result, not raw exception unless current endpoint returns 404 |
| `EdgeTtsSpeechSynthesisAdapter` | `SpeechSynthesisProvider` | `edge_tts` SDK | SDK/network errors -> `ProviderError` |
| `OpenAICompatibleLLMAdapter` | `LLMProvider` | `httpx` `/chat/completions` | HTTP/parse/timeouts -> `ProviderError` |
| `AnthropicLLMAdapter` | `LLMProvider` | `httpx` `/messages` | HTTP/parse/timeouts -> `ProviderError` |
| `FastApiBackgroundAnalysisJobAdapter` | `AnalysisJobProvider` | FastAPI `BackgroundTasks` bridge | scheduling failure -> `InfrastructureError` |
| `ConsoleTelemetryAdapter` | `TelemetryProvider` | structured JSON events to console/stdout | telemetry failure -> best-effort `TelemetryResult` failure, no business failure |
| `FileTelemetryAdapter` | `TelemetryProvider` | local debug/audit event files if approved | file write errors -> best-effort failure unless strong audit mode is configured |
| future `OpenTelemetryAdapter` / `SentryAdapter` / database audit adapter / self-hosted trace adapter | `TelemetryProvider` | optional external or self-hosted observability sinks | must map sink errors to internal telemetry errors and avoid leaking SDK types |

## 12. Migration Mapping

| Current File | Current Object | Current Responsibility | Problem | Target Layer | Target File | Target Object | Migration Action |
|---|---|---|---|---|---|---|---|
| `backend/api/projects.py` | project CRUD handlers | Project CRUD controller + direct storage | Controller imports storage | Business Pipeline | `backend/business/pipelines/project_pipeline.py` | `ProjectPipeline` | Move CRUD orchestration into pipeline; controller delegates. |
| `backend/api/projects.py` | `upload_dataset` | Upload, file persistence, status transition, background analysis | Controller handles filesystem and lifecycle | Business Flow | `backend/business/flows/project_analysis_flow.py` | `ProjectAnalysisFlow.start_from_upload` | Move lifecycle; storage and scheduling through providers. |
| `backend/api/projects.py` | `reanalyze_project` | Reanalysis lifecycle | Controller schedules concrete function | Business Flow | `backend/business/flows/project_analysis_flow.py` | `ProjectAnalysisFlow.restart` | Preserve status/error semantics behind flow. |
| `backend/api/projects.py` | `download_report`, `get_audio_file` | Generated asset serving | Controller probes filesystem | Provider Interface | `backend/providers/generated_asset_provider.py` | `GeneratedAssetProvider` | Introduce asset lookup contract; controller maps to current FileResponse. |
| `backend/api/projects.py` | `get_project_customers` | Customer read model | Controller reads CSV and maps fields | Business Pipeline | `backend/business/pipelines/project_customer_pipeline.py` | `ProjectCustomerPipeline` | Move CSV/result fallback and DTO mapping. |
| `backend/api/projects.py` | `recommend_item` | Project item relation lookup | Direct core algorithm import | Business Pipeline | `backend/business/pipelines/project_recommendation_pipeline.py` | `ProjectRecommendationPipeline` | Delegate rule lookup through ability/provider. |
| `backend/services/analysis_service.py` | `run_project_analysis` | Full analysis lifecycle | Concrete storage/services/TTS/model/cache mixed | Business Flow | `backend/business/flows/project_analysis_flow.py` | `ProjectAnalysisFlow` | Promote to flow; split steps into pipelines/abilities. |
| `backend/services/association_service.py` | `AssociationService.analyze` | Apriori analysis | Algorithm reads default settings and filesystem | Ability Atom | `backend/abilities/association/analyze_association_rules.py` | `analyze_association_rules` | Make pure ability over input dataset and thresholds. |
| `backend/services/prediction_service.py` | `PredictionService.analyze` | Ridge forecast | Algorithm reads CSV directly | Ability Atom | `backend/abilities/prediction/forecast_sales.py` | `forecast_sales` | Accept dataset DTO and return forecast DTO. |
| `backend/services/clustering_service.py` | `ClusteringService.analyze` | RFM/KMeans clustering and CSV write | Algorithm writes storage output | Ability Atom | `backend/abilities/clustering/cluster_customers.py` | `cluster_customers` | Return cluster/customer data; storage through provider. |
| `backend/services/clustering_service.py` | cluster association rules | Cluster-level rule mining | Mixed into clustering service | Ability Atom | `backend/abilities/clustering/build_cluster_association_rules.py` | `build_cluster_association_rules` | Extract distinct ability. |
| `backend/services/model_builder_service.py` | `build_and_save` | Model build and persistence | Ability and storage mixed | Ability Atom | `backend/abilities/recommendation/build_recommendation_model.py` | `build_recommendation_model` | Return artifact; store via provider. |
| `backend/services/recommender_service.py` | `RecommendationSystem` | Model/data loading and recommendation | Business, storage, cache singleton mixed | Business Pipeline | `backend/business/pipelines/recommendation_pipeline.py` | `RecommendationPipeline` | Split recommend orchestration from model/data providers. |
| `backend/services/recommender_service.py` | `calculate_realtime_rules` | Rule calculation and dynamic CSV append | Ability writes storage directly | Ability Atom | `backend/abilities/association/calculate_realtime_rules.py` | `calculate_realtime_rules` | Return rules; persistence through `AssociationRuleStoreProvider`. |
| `backend/core/storage.py` | `ProjectStorage` | JSON project persistence | Concrete adapter global instance | External Adapter | `backend/infrastructure/adapters/json_project_repository_adapter.py` | `JsonProjectRepositoryAdapter` | Implement `ProjectRepositoryProvider`; remove global direct imports later. |
| `backend/core/storage.py` | storage contract | Project repository capability | Missing interface | Provider Interface | `backend/providers/project_repository_provider.py` | `ProjectRepositoryProvider` | Define protocol/ABC and DTOs. |
| `backend/services/tts_service.py` | `TTSService` | Edge TTS wrapper | Vendor SDK in service layer | External Adapter | `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py` | `EdgeTtsSpeechSynthesisAdapter` | Move SDK call behind `SpeechSynthesisProvider`. |
| `backend/services/ai_voice_service.py` | `_call_openai`, `_call_claude` | LLM HTTP calls | Vendor branching in business code | External Adapter | `backend/infrastructure/adapters/openai_compatible_llm_adapter.py`, `anthropic_llm_adapter.py` | `OpenAICompatibleLLMAdapter`, `AnthropicLLMAdapter` | Implement `LLMProvider`; factory selects adapter. |
| `backend/services/ai_voice_service.py` | `generate_voice_broadcast` | LLM + TTS flow | Complete business flow in service | Business Pipeline | `backend/business/pipelines/ai_voice_broadcast_pipeline.py` | `AIVoiceBroadcastPipeline` | Use `generate_broadcast_script` and `synthesize_speech` abilities. |
| `backend/api/ai_voice.py` | local request models | Controller-local DTOs | DTOs not centralized | DTO / Schema | `backend/models/voice.py` | `VoiceBroadcastRequest`, `TTSRequest` | Move after behavior tests exist. |
| `backend/api/recommend.py` | local request models | Controller-local DTOs | DTOs not centralized | DTO / Schema | `backend/models/recommendation.py` | `RecommendationTtsRequest`, `CalculateRulesRequest` | Move after behavior tests exist. |
| `backend/core/config.py` | `Settings` | config/env reader | Provider factory absent | Provider Factory | `backend/infrastructure/factories/provider_factory.py` | `create_providers(settings)` | Assemble adapters once from settings. |
| whole backend | provider wiring | no Providers Container | Business layers would have no stable injection point | Providers Container | `backend/providers/container.py` | `ProvidersContainer` | Add typed container with actual current fields. |
| `backend/api/voice.py`, `backend/api/ai_voice.py`, `backend/services/tts_service.py` | stdlib `logging` usage | ad hoc debug logging | concrete logging calls are scattered and not schema-bound | Provider Interface | `backend/providers/telemetry_provider.py` | `TelemetryProvider` | Route structured debug/error/audit events through provider boundary. |
| `backend/services/analysis_service.py`, `backend/services/recommender_service.py`, `backend/services/model_builder_service.py`, `backend/core/storage.py` | `print` debugging/status output | lifecycle and error diagnostics | no request/trace correlation or redaction policy | Business Pipeline / Business Flow | `backend/business/**` with `TelemetryProvider` | trace-aware debug events | Replace ad hoc prints during migration after behavior protection exists. |
| whole backend | exception handling | mixed `HTTPException`, strings, prints | No internal error model | Internal Error | `backend/core/errors.py` | `MarketMindError` subclasses | Add internal errors before adapter migration. |
| whole backend | import rules | no architecture lint | Violations can regress | Architecture Lint | `tests/test_architecture_imports.py` or `backend/tests/test_architecture_imports.py` | import boundary tests | Add minimal mechanical checks. |
| whole backend | runtime provider facts | no runtime check | Provider wiring/config can be broken silently | Runtime Check | `backend/core/runtime_checks.py` | `check_providers`, `check_config` | Add minimal provider/config checks. |
| public APIs | behavior protection | no tests found | Migration has no equivalence guard | Test | `tests/` | API smoke and pipeline tests | Add behavior anchors before code movement. |

## 13. Config Strategy

- Keep `backend/core/config.py` as the only env reader at first to avoid unnecessary churn.
- Introduce `create_providers(settings: Settings) -> ProvidersContainer` in the Provider Factory.
- Move LLM vendor selection and local path wiring into Provider Factory / External Adapter config.
- Business Pipeline / Flow / Ability receives explicit input and `ProvidersContainer`; it must not import `settings`, `os.environ`, or `os.getenv`.
- Current request-provided `llm_config` is a public behavior dependency. Do not replace it with env-only config without explicit product decision.
- Future Settings must describe paths as typed config values, not scattered literals: `data/projects.json`, `outputs/audio`, `backend/data/audio`, `backend/data/model_data.pkl`, dynamic rule file paths.

## 14. Error Handling Strategy

Target internal errors:

- `ValidationError`: business input rejected after request schema validation.
- `NotFoundError`: project, dataset, report, audio, or model artifact missing.
- `ProviderError`: LLM/TTS/external provider failed.
- `InfrastructureError`: filesystem, JSON, CSV, pickle, background scheduling failed.
- `PipelineExecutionError`: Business Pipeline step failed.
- `BusinessFlowError`: long lifecycle failed and state transition must be recorded.

Controller mapping must preserve current public behavior:

| Internal Error | Current-compatible HTTP Mapping |
|---|---|
| `ValidationError` | 400 or 422 depending on current route behavior. |
| `NotFoundError` | 404 with `detail`. |
| `ProviderError` | 500 with existing user-visible `detail` wording unless separately approved. |
| `InfrastructureError` | 500 with current route-specific prefix. |
| `PipelineExecutionError` | 500 or stored project status `失败`, depending on current path. |
| `BusinessFlowError` | stored project status `失败` and `error_message` for background analysis. |

External Adapter must not return SDK raw response or expose SDK exception types to business code.

## Debug Logger and Audit Trace Strategy

### 1. Observability Goals

Debug Logger / Audit Trace is an architecture-level diagnostic and audit chain, not ordinary `print` output. The goal is to make every important request, pipeline step, ability execution, provider call, external adapter call, configuration load, runtime check, and side effect searchable by stable identifiers and layer metadata.

Target capabilities:

- Locate which layer produced a bug: API Controller, Business Flow, Business Pipeline, Ability Atom, Provider Interface, External Adapter, Provider Factory, Settings / Config, or Runtime Check.
- Locate the exact module, operation, stage, pipeline step, provider interface, adapter, and external capability involved.
- Correlate HTTP requests, background jobs, Business Flow executions, Pipeline runs, Ability runs, Provider calls, and external side effects.
- Support Runtime Check, trace inspection, and future Agent-assisted troubleshooting.
- Preserve behavior equivalence: logging/audit failure must not change normal business behavior unless a future strong-audit requirement explicitly chooses fail-closed semantics.

Current state to migrate:

- `backend/api/voice.py`, `backend/api/ai_voice.py`, and `backend/services/tts_service.py` use Python standard library `logging` directly.
- `backend/services/analysis_service.py`, `backend/services/recommender_service.py`, `backend/services/model_builder_service.py`, `backend/services/ai_voice_service.py`, `backend/services/clustering_service.py`, and `backend/core/storage.py` use `print` for lifecycle or error diagnostics.
- No `TelemetryProvider`, `request_id`, `trace_id`, structured audit event, audit sink, OpenTelemetry, Sentry, Datadog, `structlog`, or `loguru` integration was found.

### 2. Trace Context Model

All layers pass trace information through an explicit context object or DTO. Global variables must not carry business trace context. Framework request context may hold request-level metadata, but Business Flow, Business Pipeline, and Ability Atom still receive explicit context.

| Field | Meaning | Created By | Propagated To | Required | Notes |
|---|---|---|---|---|---|
| `request_id` | HTTP request correlation id | API Controller accepts inbound header or creates one | all downstream layers | required for HTTP entrypoints | Do not expose internal details through this value. |
| `trace_id` | end-to-end trace id across request/job/pipeline | API Controller or job scheduler | all layers and telemetry events | required | Stable root id for `inspect-trace`. |
| `actor_id` | user or anonymous actor identity | API Controller when auth/user context exists | Flow/Pipeline/Audit events | optional | Use `UNKNOWN` when identity strategy is unavailable. |
| `session_id` | UI/session correlation id | API Controller if provided | Flow/Pipeline/Audit events | optional | Not the same as secret session token. |
| `flow_run_id` | one Business Flow execution | Business Flow | Flow, Pipeline, Ability, Provider, Adapter events | required when flow exists | Current candidate: `ProjectAnalysisFlow`. |
| `pipeline_run_id` | one Business Pipeline execution | Business Pipeline | Pipeline, Ability, Provider, Adapter events | required for pipeline execution | Created per pipeline call. |
| `ability_run_id` | one Ability Atom execution | Ability Atom or caller pipeline | Ability, Provider, Adapter events | required for ability execution | May be pre-created by pipeline for planned steps. |
| `provider_call_id` | one provider boundary call | External Adapter or provider wrapper | Provider and Adapter events | required for provider calls | Created before external side effect attempt. |
| `job_id` | async/background job id | AnalysisJobProvider or Business Flow | Flow/Pipeline/Audit events | required for async jobs | Current FastAPI BackgroundTasks lacks durable job id; use generated id until real job system exists. |
| `source_id` | source dataset/document/request source id | API Controller, Pipeline, or Provider | Pipeline/Audit events | optional | Avoid raw source contents. |
| `content_id` | generated or processed content id | Ability or Provider | Ability/Audit events | optional | Prefer stable id/hash over content body. |
| `operation` | business operation name | Controller/Pipeline | all events | required | Stable value such as `project_analysis`, not user input. |
| `layer` | architecture layer name | each emitting layer | telemetry event | required | Values match architecture boundaries. |
| `module` | module/component name | each emitting layer | telemetry event | required | Must map to an architecture module, not `misc` or `helper`. |
| `stage` | current stage/step | Flow/Pipeline/Ability/Adapter | telemetry event | required for multi-step work | Use stable stage names. |

Creation rules:

- API Controller creates or accepts `request_id` / `trace_id`.
- Business Flow creates `flow_run_id` only for complex lifecycle execution.
- Business Pipeline creates `pipeline_run_id`.
- Ability Atom creates or receives `ability_run_id`.
- External Adapter creates `provider_call_id` for each external capability call.
- Provider Factory emits provider assembly events but does not create business run ids.

### 3. Layer-level Logging Contract

| Layer | Required Events | Required Fields | Forbidden Fields | Notes |
|---|---|---|---|---|
| API Controller | `api.request.received`, `api.request.validated`, `api.response.returned`, `api.error.mapped` | `request_id`, `trace_id`, `route`, `method`, `status_code`, `duration_ms`, `actor_id`, `error_code` | `raw_password`, `raw_token`, `raw_file_content`, `full_llm_prompt` | Controller maps errors and starts request trace. |
| Business Flow | `flow.started`, `flow.stage.completed`, `flow.stage.failed`, `flow.compensation.started`, `flow.completed`, `flow.cancelled` | `flow_run_id`, `trace_id`, `flow_name`, `stage`, `state_before`, `state_after`, `error_type` | raw dataset/document content, full prompt/response | Required only for complex lifecycle such as project analysis. |
| Business Pipeline | `pipeline.started`, `pipeline.step.started`, `pipeline.step.completed`, `pipeline.step.failed`, `pipeline.completed`, `pipeline.failed` | `pipeline_run_id`, `trace_id`, `pipeline_name`, `step_name`, `stage`, `duration_ms`, `error_type`, `is_retryable` | concrete SDK response, raw file content, secret values | Step-level events are required before controller thinning. |
| Ability Atom | `ability.started`, `ability.completed`, `ability.failed` | `ability_run_id`, `trace_id`, `ability_name`, `input_summary`, `output_summary`, `provider_used`, `error_type` | full raw content, full LLM prompt, complete uploaded file | `input_summary` / `output_summary` use counts, hashes, ids, and field names. |
| Provider Boundary | `provider.call.requested`, `provider.call.completed`, `provider.call.failed` | `provider_call_id`, `trace_id`, `provider_name`, `provider_interface`, `operation`, `timeout_ms`, `retry_policy` | concrete adapter object, SDK raw response | Provider Interface must not import concrete telemetry adapters. |
| External Adapter | `adapter.external_call.started`, `adapter.external_call.completed`, `adapter.external_call.failed`, `adapter.error.mapped` | `adapter_name`, `provider_name`, `provider_call_id`, `external_service`, `external_operation`, `latency_ms`, `external_status`, `mapped_error_type`, `retry_count` | raw SDK response, raw authorization headers, API key values | Adapter maps external error to internal DTO/error before logging. |
| Provider Factory / Settings | `provider_factory.started`, `provider_factory.completed`, `provider_factory.failed`, `settings.loaded`, `settings.validation_failed` | `profile`, `provider_fields`, `missing_config`, `config_source` | secret value, api key value, token value, password value | Only log config sources, field names, and missing field names. |

### 4. Debug Event Naming Convention

Event names use stable dot-separated identifiers:

```text
<layer>.<module>.<event>
```

Examples:

- `api.project_upload.request.received`
- `pipeline.project_upload.step.completed`
- `ability.cluster_customers.completed`
- `provider.llm.call.failed`
- `adapter.openai.external_call.failed`
- `factory.providers.completed`
- `settings.validation_failed`

Rules:

- Use lowercase only.
- Use dot-separated hierarchy.
- Do not concatenate user input into event names.
- Keep event names stable for search, alerting, Runtime Check, and trace inspection.
- Module names must correspond to architecture modules; do not use `misc`, `common`, `helper`, or `utils` as event modules.

### 5. Debug Log Schema

Target schema, not implemented in this planning stage:

```json
{
  "timestamp": "2026-05-25T00:00:00.000Z",
  "level": "INFO",
  "event": "pipeline.project_analysis.step.completed",
  "trace_id": "trace_...",
  "request_id": "req_...",
  "layer": "BusinessPipeline",
  "module": "ProjectAnalysisPipeline",
  "operation": "project_analysis",
  "stage": "cluster_customers",
  "duration_ms": 123,
  "status": "success",
  "error": null,
  "context": {
    "pipeline_run_id": "pipeline_...",
    "job_id": "job_...",
    "source_id": "dataset_...",
    "content_id": "report_..."
  }
}
```

Required fields: `timestamp`, `level`, `event`, `trace_id`, `layer`, `module`, `operation`, `stage`, `status`.

Required when available: `request_id`, `duration_ms`, `context.pipeline_run_id`, `context.flow_run_id`, `context.ability_run_id`, `context.provider_call_id`, `error.error_type`, `error.error_code`, `error.is_retryable`.

Optional fields: `actor_id`, `session_id`, `job_id`, `source_id`, `content_id`, `external_status`, `retry_count`, `timeout_ms`.

Masking rules:

- PII and secrets are redacted before emission.
- Large text content records `sha256`, `length`, `mime_type`, `field_names`, `content_id`, or short safe summary, not full text.
- LLM prompt/response logs record prompt hash, response hash, model name, token usage if available, latency, and mapped status, not full prompt or response.
- Uploaded files record file hash, size, mime type, and object key, not content.

### 6. Audit Event Schema

Audit events focus on side effects, not ordinary debug information.

```json
{
  "timestamp": "2026-05-25T00:00:00.000Z",
  "audit_event": "storage.object.write.completed",
  "trace_id": "trace_...",
  "actor_id": "UNKNOWN",
  "layer": "ExternalAdapter",
  "module": "LocalGeneratedAssetAdapter",
  "operation": "write_object",
  "resource_type": "file_system",
  "resource_id": "data/projects/project_123/outputs/reports/report_project_123.md",
  "action": "write",
  "result": "success",
  "state_before": null,
  "state_after": {
    "object_key": "data/projects/project_123/outputs/reports/report_project_123.md",
    "size_bytes": 12345,
    "sha256": "..."
  },
  "risk_level": "medium"
}
```

Audit action categories:

- `read`
- `write`
- `delete`
- `publish`
- `transition`
- `external_call`
- `auth_decision`
- `permission_check`
- `config_load`

Risk levels:

- `low`: read-only or local debug event with no sensitive content.
- `medium`: local file write, generated asset write, cache write, job status transition.
- `high`: external API call, destructive delete, audit-required state transition.
- `critical`: auth decision, permission decision, irreversible destructive action, strong-audit failure.

Audit failure policy options:

- `best-effort`: telemetry failure does not fail business flow; default for debug and current project migration.
- `required`: operation reports telemetry failure but may still use business-defined fallback.
- `fallback buffer`: write to local safe buffer when primary sink fails.
- `fail-open`: continue business operation and record sink failure when possible.
- `fail-closed`: block business operation if audit cannot be written; only allowed for explicitly approved strong-audit paths.

### 7. Error Correlation Strategy

Internal errors carry `error_code`. Error telemetry must answer:

- Which request failed?
- Which flow, pipeline, step, ability, provider, and adapter failed?
- Which external service/status was involved?
- Is the error retryable?
- Did a side effect occur?
- Does a side effect need compensation or rollback?

Correlation requirements:

- `ProviderError` records `provider_name`, `provider_interface`, `provider_call_id`, `adapter_name`, `operation`, `timeout_ms`, `retry_count`, and `mapped_error_type`.
- `InfrastructureError` records `external_service`, `resource_type`, `resource_id`, and `mapped_error_type`.
- `PipelineExecutionError` records `pipeline_run_id`, `failed_step`, `stage`, `error_code`, and `is_retryable`.
- `BusinessFlowError` records `flow_run_id`, `failed_stage`, `state_before`, `state_after`, and compensation status.
- API Controller preserves internal `trace_id` in logs and safe support metadata, but public responses must not expose internal sensitive details.

### 8. Telemetry Provider Boundary

Business and Ability layers must not call concrete logging, audit, tracing, Sentry, Datadog, OpenTelemetry, `structlog`, `loguru`, or standard library `logging` directly. They use a Provider Boundary.

| Provider Interface | Methods | Used By | External Adapter Candidates | Notes |
|---|---|---|---|---|
| `TelemetryProvider` | `emit_debug_event(event)`, `emit_audit_event(event)`, `emit_error_event(event)`, `start_span(context)`, `end_span(span, result)` | API Controller, Business Flow, Business Pipeline, Ability Atom, Provider Factory, External Adapter wrappers, Runtime Check | `ConsoleTelemetryAdapter`, `FileTelemetryAdapter`, future `OpenTelemetryAdapter`, `SentryAdapter`, database audit writer, self-hosted trace adapter | Start with one provider because the project is small; split `AuditProvider` only if strong audit requirements emerge. |

Current logging migration:

- Replace direct `logging` in `backend/api/voice.py`, `backend/api/ai_voice.py`, and `backend/services/tts_service.py` with structured events through `TelemetryProvider` during controller/adapter migration.
- Replace `print` in analysis/recommendation/model/storage services with trace-aware debug/audit events after behavior tests exist.
- Concrete output remains in Infrastructure Layer. Initial adapters should be console/file only unless the project explicitly adopts another sink later.

### 9. Runtime Check Extension

This Python project should adapt runtime check commands to the `backend` package:

| Runtime Check | Purpose | Suggested Command |
|---|---|---|
| inspect trace | Query one request/job/pipeline chain by `trace_id` | `uv run python -m backend.core.runtime_checks inspect-trace <trace_id>` |
| telemetry check | Verify `TelemetryProvider` can emit debug/error/span events to configured sink | `uv run python -m backend.core.runtime_checks check-telemetry` |
| audit sink check | Verify audit events can be emitted or buffered according to failure policy | `uv run python -m backend.core.runtime_checks check-audit-sink` |
| traced pipeline dry-run | Validate Pipeline execution emits required trace events with sample input | `uv run python -m backend.core.runtime_checks dry-run-pipeline <pipeline_name> --sample <sample_file> --trace` |
| debug schema validation | Validate debug event structure | `uv run python -m backend.core.runtime_checks validate-log-schema tests/fixtures/logging/debug_event.json` |
| audit schema validation | Validate audit event structure | `uv run python -m backend.core.runtime_checks validate-audit-schema tests/fixtures/logging/audit_event.json` |

### 10. Architecture Lint Extension

Additional lint rules:

1. Business Pipeline, Business Flow, and Ability Atom must not import concrete logging/tracing/audit SDKs.
2. Business layers must not directly import OpenTelemetry, Sentry, Datadog, `structlog`, `loguru`, or standard library `logging`; standard library `logging` is allowed only inside Telemetry External Adapters if used as an implementation detail.
3. Business layers must not directly write audit database/files.
4. External Adapters must not call Business layer logger helpers or business modules.
5. Secret-like fields must not be logged directly.
6. Event names must not be dynamically built from user input.
7. Key Pipelines must define required trace events.
8. External Adapter external-call failures must record `adapter.error.mapped`.
9. Provider Factory must record provider assembly failures.
10. Runtime Check must include telemetry, audit, and trace-inspection commands.

Architecture Lint keeps the fixed error format:

```text
Architecture violation:
<specific file> violated <rule>.

Reason:
<why this violates architecture boundary>.

Fix:
<specific fix>.

Expected direction:
<API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter>
```

### 11. Privacy and Redaction Policy

Forbidden in debug/audit logs:

- password
- token
- authorization header
- cookie
- api key
- secret
- private key
- raw uploaded file content
- raw document full text
- full LLM prompt
- full LLM response
- personal sensitive content

Allowed in debug/audit logs:

- hash
- length
- mime_type
- object_key
- content_id
- source_id
- job_id
- model_name
- provider_name
- duration_ms
- status_code
- error_code
- retry_count

Adapter rules:

- All Adapter logs of external responses first convert the response to an internal DTO summary.
- LLM logs default to prompt hash, response hash, token usage if available, model name, provider name, latency, retry count, and mapped status.
- File-processing logs default to file hash, size, mime type, object key, and content id.
- `actor_id` follows the project identity strategy; until that strategy exists, audit events use `UNKNOWN`.

## 15. Architecture Lint Strategy

No current Architecture Lint was found. Add a minimal mechanical lint before migration.

Minimum rules:

1. `backend/api/**` must not import `backend.core.storage`, external SDKs, database clients, `httpx`, `edge_tts`, or `backend.infrastructure.adapters`.
2. `backend/business/**` must not import FastAPI request/response classes, `settings`, external SDKs, filesystem adapter implementations, or `backend.api`.
3. `backend/abilities/**` must not import `backend.business`, `backend.infrastructure`, external SDKs, FastAPI classes, or env readers.
4. `backend/providers/**` must not import `backend.infrastructure`, SDKs, DB/storage clients, `backend.business`, or `backend.api`.
5. `backend/infrastructure/**` must not import `backend.business`, `backend.abilities`, or `backend.api`.
6. No new `utils`, `helpers`, or `common` fallback modules.
7. Provider Interfaces must not contain vendor names such as OpenAI, Anthropic, EdgeTTS, Postgres, S3, Playwright.
8. External Adapters must return internal DTOs, not raw SDK response types.
9. Business layers must not import concrete logging/tracing/audit SDKs or standard library `logging`; use `TelemetryProvider`.
10. Business layers must not write audit sinks directly.
11. Event names must be stable and must not include user input.
12. Secret-like fields must not be emitted directly in debug or audit event payloads.
13. Provider Factory and External Adapter failure paths must emit required telemetry events through the provider boundary.

Suggested command after implementation: `uv run pytest tests/test_architecture_imports.py`.

## 16. Runtime Check Strategy

No current Runtime Check was found. Add minimal runtime checks after Provider Factory exists.

Minimum checks:

| Runtime Check | Purpose | Suggested Command |
|---|---|---|
| config check | Settings can load required paths/defaults | `uv run python -m backend.core.runtime_checks check-config` |
| provider check | Provider Factory creates every container field | `uv run python -m backend.core.runtime_checks check-providers` |
| storage check | JSON repository and local directories are readable/writable in sandbox | `uv run python -m backend.core.runtime_checks check-storage --sandbox` |
| TTS check | Speech provider can be mocked or probed without irreversible output | `uv run python -m backend.core.runtime_checks check-speech --mock` |
| LLM check | LLM provider config shape is valid; real connectivity only with explicit credentials | `uv run python -m backend.core.runtime_checks check-llm --dry-run` |
| pipeline dry-run | Project analysis pipeline can run against fixture without changing real data | `uv run python -m backend.core.runtime_checks dry-run-project-analysis --fixture tests/fixtures/sample_dataset.csv` |
| schema validation | sample request/response contracts validate | `uv run python -m backend.core.runtime_checks validate-api-schemas` |
| trace/log inspection | core flow emits expected phase logs | `uv run python -m backend.core.runtime_checks inspect-logs --latest` |
| telemetry check | TelemetryProvider can emit debug/error/span events to configured sink | `uv run python -m backend.core.runtime_checks check-telemetry` |
| audit sink check | Audit events can be emitted or buffered according to configured failure policy | `uv run python -m backend.core.runtime_checks check-audit-sink` |
| inspect trace | trace id can reconstruct one request/job/pipeline chain | `uv run python -m backend.core.runtime_checks inspect-trace <trace_id>` |
| log schema validation | sample debug event validates required fields and redaction rules | `uv run python -m backend.core.runtime_checks validate-log-schema tests/fixtures/logging/debug_event.json` |
| audit schema validation | sample audit event validates required fields and redaction rules | `uv run python -m backend.core.runtime_checks validate-audit-schema tests/fixtures/logging/audit_event.json` |

### Implementation status

The Runtime Check CLI is implemented at `backend/core/runtime_checks.py`. Commands are dispatched via subparsers; each command is a top-level `cmd_*` function. The module is non-destructive by contract: file-emitting commands use `tempfile.TemporaryDirectory`, and the LLM/Speech checks never invoke real network or synthesis calls.

| Command | Implemented | Side effects | Secrets required | Exit code semantics |
|---|---|---|---|---|
| `check-config` | yes | Loads `Settings()`; reads `.env` if present. | none | `0` on success; `1` on settings load failure. |
| `check-providers` | yes | Builds `ProvidersContainer` via `create_providers(Settings())`. | none | `0` when every container field is non-null; `1` otherwise. |
| `check-storage --sandbox` | yes | Creates a `tempfile.TemporaryDirectory`, exercises `JsonProjectRepositoryAdapter`, `LocalProjectFileStorageAdapter`, `CsvDatasetAdapter` end-to-end inside the sandbox, then deletes. | none | `0` on success; `1` on any storage assertion failure; `1` when `--sandbox` is omitted. |
| `check-llm --dry-run` | yes (interface probe only) | Builds providers; checks `providers.llm.generate_text` is callable. **No real LLM request is sent.** | none | `0` on interface present (logs `skipped: requires network`); `1` when `--dry-run` is omitted or interface missing. |
| `check-speech --mock` | yes (interface probe only) | Builds providers; checks `providers.speech.synthesize` is callable. **No real synthesis is invoked.** | none | `0` on interface present; `1` when `--mock` is omitted or interface missing. |
| `validate-api-schemas` | yes | Calls `backend.main.app.openapi()` and asserts non-empty `paths`. | none | `0` on success; `1` on schema failure. |
| `check-telemetry` | yes | Emits 3 events (debug/audit/error) to `ConsoleTelemetryAdapter` with an in-memory writer; asserts required `DebugEvent` fields are present in the serialized payload. | none | `0` when all 3 emits succeed and required fields match; `1` otherwise. |
| `check-audit-sink` | yes | Writes one `AuditEvent` to `FileTelemetryAdapter` under a `tempfile.TemporaryDirectory`; asserts file exists and required fields are present. | none | `0` on success; `1` otherwise. |
| `validate-log-schema [--fixture]` | yes | Reads a JSON fixture (default `tests/fixtures/logging/debug_event.json`) and asserts every `DebugEvent` dataclass field is present. | none | `0` on success; `1` when fixture missing fields or unreadable. |
| `validate-audit-schema [--fixture]` | yes | Same as above against `AuditEvent`. | none | `0` on success; `1` otherwise. |
| `inspect-trace --trace-id` | placeholder | Currently logs `skipped: not implemented in MVP`. Trace store backend not yet present. | none | `0` (placeholder skip). |
| `dry-run-project-analysis` | not implemented | Reserved for a future pipeline-fixture replay. | n/a | n/a |
| `inspect-logs --latest` | not implemented | Replaced by `validate-log-schema` / `validate-audit-schema` for MVP. | n/a | n/a |

### Scope and non-substitution

- Runtime checks are deployment-time self-tests. They MUST NOT replace `uv run pytest tests/` in CI; they complement it by validating that the wired Provider Factory, Settings, and telemetry adapters can boot in the target environment.
- All commands MUST remain non-destructive against real project data. Any future write must be confined to `tempfile.TemporaryDirectory` or explicitly gated behind a `--sandbox`-equivalent flag.
- LLM and Speech checks MUST stay interface-only until an out-of-band credential gate is added; do not introduce real-call modes inside this CLI.

### Test coverage

`tests/core/test_runtime_checks.py` invokes each command via `subprocess.run` and asserts both exit code `0` and the expected stdout marker for the happy path; it also asserts gating flags (`--sandbox`, `--dry-run`, `--mock`) are enforced.

## 17. Test Strategy

Existing tests: none found. Existing test tooling exists in `pyproject.toml`:

| Purpose | Command | Exists | Notes |
|---|---|---|---|
| Install Python deps | `uv sync` | YES | Documented in README/scripts. |
| Run backend dev server | `uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` | YES | Used by `scripts/start-backend.sh`. |
| Python tests | `uv run pytest tests/` | PARTIAL | pytest configured, but no tests found. |
| Python formatter | `uv run ruff format .` | YES | exposed through `make format` and pre-commit `ruff-format`; black remains configured in `pyproject.toml` but is not the current harness formatter. |
| Python linter | `uv run ruff check .` | YES | exposed through `make lint`. |
| Frontend dev server | `cd frontend && npm run dev` | YES | `frontend/package.json`. |
| Frontend build/type check | `cd frontend && npm run build` | YES | runs `vue-tsc && vite build`. |
| Frontend preview | `cd frontend && npm run preview` | YES | Vite preview. |
| Architecture Lint | `uv run pytest tests/test_architecture_imports.py` | NO | Must be added before migration. |
| Runtime Check | `uv run python -m backend.core.runtime_checks check-providers` | NO | Must be added after provider factory exists. |
| CI | YES | `.github/workflows/check.yml` runs split backend and frontend checks. |
| Makefile / justfile | YES | `Makefile` exposes setup, lint, format, fix, test, build, check, verify, hooks, and clean targets. |

Required validation order for migration phases:

1. Project static check: `uv run ruff check .`
2. Architecture Lint: `uv run pytest tests/test_architecture_imports.py`
3. Type/contract check: Python Pydantic schema tests and `cd frontend && npm run build`
4. Affected tests: API smoke / pipeline / provider contract tests for touched path
5. Full tests: `uv run pytest tests/`
6. Runtime Check: provider/config/storage/dry-run commands
7. Trace/log inspection: inspect flow logs, debug events, audit events, and error paths

Minimum behavior protection before code migration:

- API smoke tests for project create/upload/reanalyze/list/detail/customers/recommendation/TTS/AI voice response shapes.
- Business flow test for project analysis status transitions and output paths using fixtures and fake providers.
- Provider contract tests for JSON project repository, local asset storage, Edge TTS fake adapter, LLM fake adapter.
- Architecture import lint to prevent new direct SDK/storage access from controllers/business layers.
- Debug/audit schema fixture validation for `tests/fixtures/logging/debug_event.json` and `tests/fixtures/logging/audit_event.json`.

## 18. Phased Migration Plan

1. Establish behavior anchors: add fake/sandbox test support, tests for current public API contracts, status strings, generated asset URLs, analysis status transitions, and debug/audit schema fixtures.
2. Add Architecture Lint with a temporary allowlist for known current violations; prohibit new boundary, SDK, telemetry, and fallback utility violations before migration continues.
3. Add Provider Interfaces, internal DTOs, internal errors, Providers Container, and Provider Factory without rewiring behavior.
4. Add minimal Runtime Check commands for provider/config/storage/telemetry validation once provider assembly exists.
5. Add External Adapters that wrap current JSON/filesystem/LLM/TTS/telemetry behavior while preserving paths and response shapes.
6. Extract Ability Atoms from analysis, recommendation, clustering, prediction, report, and voice code behind provider interfaces.
7. Extract Business Pipelines for CRUD, recommendation, customer read model, association analysis, voice synthesis, and AI broadcast.
8. Extract `ProjectAnalysisFlow` for upload/reanalysis background lifecycle.
9. Thin API Controllers to protocol conversion and error mapping only.
10. Run full validation and trace/log inspection.
11. Remove dead compatibility code only after tests prove no frontend/API behavior changed.

## 19. Rollback Strategy

Each migration phase must be independently reversible:

| Phase | Rollback |
|---|---|
| Tests only | Delete or skip newly added tests only if they are proven incorrect; do not change product code. |
| Provider Interfaces | Remove unused interface files if no business code depends on them. |
| External Adapters | Restore direct calls by reverting adapter wiring; keep old service behavior intact until controller rewiring completes. |
| Ability Atoms | Revert extracted function calls to existing service implementation. |
| Business Pipelines | Revert controller delegation to current services/routes. |
| Business Flow | Revert upload/reanalysis scheduling to `run_project_analysis`. |
| Controller thinning | Revert individual route handler to previous body from version control. |
| Architecture Lint / Runtime Check | Fix rules or implementation; do not delete rules to pass migration. |

No database schema rollback is needed currently because no DB was found. File outputs must retain current paths during migration.

## 20. Open Questions / Clarifications

- Should local JSON persistence remain the long-term repository, or is a database planned? Current code has no transaction semantics.
- Should `/api/tts/` from `backend/api/ai_voice.py` remain public alongside `/api/voice/tts/`? Both exist and return different audio URL styles.
- Should inactive `prediction` and `clustering` routers stay inactive? They appear inconsistent with current service constructors/methods.
- Should frontend direct LLM calls remain in frontend settings/product recommendation views, or move behind backend LLM provider in a later phase? This would change security and API behavior and requires separate approval.
- Should FastAPI `BackgroundTasks` remain the runtime for project analysis, or should a real queue be introduced later? Current phase must preserve behavior.
- Current error responses are mostly route-specific `detail` strings. Should migration preserve exact strings or standardize later behind a versioned API contract?
- Current generated audio paths differ: `/outputs/audio/...` vs `/api/ai-voice/audio/{filename}/`. Preserve both unless product decides to normalize.
- Should audit events use only best-effort console/file output for the first migration, or does any path require durable audit storage?
- What trace header names should the API accept from upstream clients: `X-Request-ID`, `traceparent`, both, or generated ids only?
- What retention period and access policy should apply to audit events once a durable sink exists?
- Which fields are considered personal sensitive content for customer analytics outputs beyond obvious secrets/tokens?

## 21. Risks

Architecture violation:
`backend/api/voice.py`, `backend/api/ai_voice.py`, and `backend/services/tts_service.py` violated direct logging implementation dependency rule.

Reason:
These files import and use Python standard library `logging` directly. Target architecture requires structured debug/error/audit events through `TelemetryProvider`, with concrete logging implementation isolated in External Adapters.

Fix:
During controller and adapter migration, replace ad hoc logging calls with `TelemetryProvider.emit_debug_event`, `emit_error_event`, or `emit_audit_event`; keep console/file logging inside `ConsoleTelemetryAdapter` or `FileTelemetryAdapter`.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/services/analysis_service.py`, `backend/services/recommender_service.py`, `backend/services/model_builder_service.py`, and `backend/core/storage.py` violated trace-correlated debug event rule.

Reason:
These modules use `print` for lifecycle and error diagnostics. The output has no `trace_id`, `request_id`, layer, module, operation, stage, error code, retryability, or redaction contract.

Fix:
After behavior tests exist, replace lifecycle prints with schema-bound debug/audit events emitted through `TelemetryProvider`; keep side-effect audit events focused on state transitions and file/model writes.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/api/projects.py` violated API Controller direct storage access rule.

Reason:
The controller imports `backend.core.storage.storage`, performs CRUD, calculates project directories, writes uploaded files, reads generated artifacts and customers CSV, and updates statuses directly.

Fix:
Move project operations into `ProjectPipeline`, `DatasetUploadPipeline`, `ProjectCustomerPipeline`, and `ProjectAnalysisFlow`; expose storage through `ProjectRepositoryProvider`, `ProjectFileStorageProvider`, and `GeneratedAssetProvider`.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/api/projects.py` violated API Controller direct algorithm access rule.

Reason:
The project recommendation route imports `query_item_relations` from `backend.core.recommend`, bypassing Business Pipeline and Ability boundaries.

Fix:
Create `ProjectRecommendationPipeline` and recommendation abilities that use `AssociationRuleStoreProvider` / `DatasetProvider`.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/api/voice.py` violated API Controller direct SDK-facing service and file layout rule.

Reason:
The route creates output directories, names files, calls `TTSService`, checks filesystem output, and returns generated URLs.

Fix:
Move voice generation into `VoiceSynthesisPipeline`; use `SpeechSynthesisProvider` and `GeneratedAssetProvider`.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/api/ai_voice.py` violated API Controller direct generated asset lookup rule.

Reason:
The route probes `/tmp` and `backend/data/audio` directly and returns `FileResponse`.

Fix:
Introduce `GeneratedAssetProvider.resolve_ai_audio` and keep controller limited to HTTP response mapping.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/services/analysis_service.py` violated Business Pipeline external storage and concrete service dependency rule.

Reason:
`run_project_analysis` is a full lifecycle orchestration that directly imports storage, instantiates concrete services, writes reports/audio/model artifacts, invalidates cache, and updates status.

Fix:
Promote it to `ProjectAnalysisFlow`; split algorithmic steps into Ability Atoms and access storage/asset/model/speech capabilities through Provider Interfaces.

Expected direction:
API Controller -> Business Flow -> Business Pipeline -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/services/ai_voice_service.py` violated Business layer direct HTTP client and vendor-specific provider selection rule.

Reason:
Business code branches on `provider == 'claude'`, calls vendor-named methods `_call_openai` and `_call_claude`, and uses `httpx.AsyncClient` directly.

Fix:
Move HTTP calls into `OpenAICompatibleLLMAdapter` and `AnthropicLLMAdapter`; expose only `LLMProvider.generate_broadcast_script` to business code.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/services/tts_service.py` violated External Adapter isolation rule.

Reason:
`edge_tts` SDK is imported and invoked in the service layer, with no Provider Interface boundary.

Fix:
Move Edge TTS code into `EdgeTtsSpeechSynthesisAdapter` implementing `SpeechSynthesisProvider`.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/core/storage.py` violated Provider Interface and Providers Container rule.

Reason:
`ProjectStorage` is globally instantiated and imported directly by controllers/services. It performs JSON persistence and project directory operations without an interface or factory.

Fix:
Define `ProjectRepositoryProvider` and `ProjectFileStorageProvider`; implement current behavior in JSON/local filesystem adapters created by Provider Factory.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/services/recommender_service.py` violated Ability Atom storage side-effect rule.

Reason:
`calculate_realtime_rules` computes rules and appends `backend/data/dynamic_rules.csv`, mixing calculation and persistence.

Fix:
Split `calculate_realtime_rules` ability from `AssociationRuleStoreProvider.save_dynamic_rules`.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/main.py` violated bootstrap storage initialization boundary.

Reason:
Application bootstrap creates `outputs` and mounts static generated assets directly, coupling runtime startup with generated asset storage.

Fix:
Move storage readiness into Runtime Check / provider initialization while preserving `/outputs` serving behavior until frontend contract changes are approved.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/` violated missing Provider Interface rule.

Reason:
No Provider Interface layer exists, so business and controller code directly use storage, HTTP clients, SDKs, filesystem, and runtime scheduling.

Fix:
Add capability-named Provider Interfaces under `backend/providers/` before moving business code.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/` violated missing Providers Container rule.

Reason:
No typed container exists to inject external capabilities. Current code relies on global service/storage instances and concrete constructors.

Fix:
Add `ProvidersContainer` with only actual current fields: repository, storage, assets, dataset, association_rules, recommendation_models, speech, llm, analysis_jobs.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/` violated missing Architecture Lint rule.

Reason:
No mechanical check prevents controllers from importing storage/SDKs or business code from importing external adapters/env readers.

Fix:
Add minimal architecture import tests before code migration.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`backend/` violated missing Runtime Check rule.

Reason:
No runtime command verifies Settings, Provider Factory, adapter wiring, storage paths, or dry-run behavior.

Fix:
Add `backend/core/runtime_checks.py` after Provider Factory exists and expose check commands.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

Architecture violation:
`tests/` violated missing behavior protection rule.

Reason:
No test files were found, while migration would affect public API contracts, generated file paths, background lifecycle, status strings, and external provider behavior.

Fix:
Add API smoke tests, flow orchestration tests with fake providers, provider contract tests, and architecture lint before moving code.

Expected direction:
API Controller -> Business Pipeline / Business Flow -> Ability Atom -> Provider Interface -> External Adapter

## 22. Pipeline-Level Trace Event Contract

This section is the binding contract for Business Pipeline trace events. Pipelines emit telemetry only through `TelemetryProvider`; they never call loggers, file sinks, or external SDKs directly. Pipelines must not pass raw user input, raw uploaded bytes, secrets, tokens, or unbounded payloads into events.

### Event names

Each Business Pipeline run must emit at minimum:

- `pipeline.started` — when a `ProvidersContainer`-bound pipeline operation begins.
- `pipeline.step.started` — before each internal step (provider call, ability invocation, or branch decision).
- `pipeline.step.completed` — after a step finishes successfully.
- `pipeline.step.failed` — when a step raises before returning a normal result.
- `pipeline.completed` — when the whole pipeline returns a normal result.
- `pipeline.failed` — when the pipeline propagates an error to the controller.

`step.started` and `step.completed` / `step.failed` must be paired with the same `step_name`.

### Required event fields

Every event in the contract includes the following fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `pipeline_run_id` | string | Unique per pipeline invocation; stable across all events of one run. |
| `trace_id` | string | Inherited from the inbound request when present; otherwise generated at pipeline entry. |
| `pipeline_name` | string | Class name of the pipeline, e.g. `ProjectPipeline`. |
| `operation` | string | Pipeline method name, e.g. `create`, `upload`, `recommend_user`. |
| `step_name` | string \| null | Required on `step.*` events; null on `started` / `completed` / `failed`. |
| `stage` | string | One of `entry`, `validate`, `provider_call`, `ability_call`, `persist`, `dispatch`, `exit`. |
| `duration_ms` | number | Set on `*.completed` and `*.failed`; omitted on `*.started`. |
| `error_type` | string \| null | Required on `*.failed`; must be a class name exported by `backend.core.errors`. |
| `provider_used` | string \| null | Provider interface name when the step crossed a provider boundary, e.g. `ProjectRepositoryProvider`. |

### `error_type` enumeration

`error_type` must be one of the class names defined in `backend.core.errors`:

- `ValidationError`
- `NotFoundError`
- `ProviderError`
- `InfrastructureError`
- `PipelineExecutionError`
- `BusinessFlowError`

Pipelines must translate any non-listed exception caught from below them into one of the above before emission and before propagation.

### Redaction rules

Identical to Ability-layer redaction in the Debug Logger and Audit Trace Strategy section:

- Dataset rows, uploaded bytes, full file paths under user content, LLM prompts, TTS text, and personal identifiers are forbidden in event payloads.
- Only counts, lengths, IDs, status strings, and provider interface names may be recorded.
- Errors must be summarized as `error_type` plus a non-sensitive short message; raw stack traces stay in the runtime logger, not in trace events.
- TelemetryProvider failures must not change pipeline business behavior.

### Emission boundary

- Pipelines emit via `providers.telemetry` only. Direct imports of logging, `print`, `httpx`, `edge_tts`, `pandas`, `sklearn`, `mlxtend`, `fastapi`, `backend.api`, and `backend.infrastructure` remain forbidden in `backend/business/` and are enforced by Architecture Lint.
- Controllers, abilities, and providers retain their own event contracts; this section governs Pipeline scope only.

## Flow Lifecycle Audit Contract

`ProjectAnalysisFlow` is currently the only Business Flow with a complex lifecycle (long-running upload / reanalyze with multiple stages, generated artifacts and cache invalidation). Future flows that orchestrate multi-stage state transitions must follow this same contract; one-step routes stay in Pipelines.

### Required events

- `flow.started` — emitted at flow entry after the target resource is resolved and before the first stage runs.
- `flow.stage.completed` — emitted after each named stage finishes successfully (`load_dataset`, `association_rules`, `forecast_sales`, `cluster_customers`, `report`, `speech`, `model_build`).
- `flow.stage.failed` — emitted when a stage raises. Best-effort stages (currently `speech`, `model_build`) emit `stage.failed` without aborting the flow; mandatory stages additionally trigger `flow.cancelled` or `flow.completed` with terminal failure state.
- `flow.compensation.started` — emitted when a stage failure triggers rollback of previously persisted side effects. `ProjectAnalysisFlow` currently has no compensation logic; future flows that rollback writes must emit this event.
- `flow.completed` — emitted at the terminal successful boundary, after `mark_analysis_completed` persists the final results.
- `flow.cancelled` — emitted when the flow ends in a terminal failure state, after `mark_analysis_failed` persists `error_message`. Also emitted on cooperative cancellation (e.g. user-initiated abort) once such a path exists.

`stage.started` and `stage.completed` / `stage.failed` must share the same `stage` value within one `flow_run_id`.

### Required event fields

| Field | Type | Meaning |
| --- | --- | --- |
| `flow_run_id` | string | Unique per flow invocation; stable across all events of one run. |
| `trace_id` | string | Inherited from the inbound request when present; otherwise generated at flow entry. |
| `flow_name` | string | Class name of the flow, e.g. `ProjectAnalysisFlow`. |
| `stage` | string \| null | Required on `stage.*` events; null on `flow.started` / `flow.completed` / `flow.cancelled`. |
| `state_before` | string | Project status snapshot before the transition; uses `ProjectStatus` value (`待处理`, `处理中`, `已完成`, `失败`). |
| `state_after` | string | Project status snapshot after the transition; same enumeration as `state_before`. |
| `duration_ms` | number | Required on `*.completed` and `*.failed`; omitted on `*.started`. |
| `error_type` | string \| null | Required on `*.failed`; must be a class name exported by `backend.core.errors` (`ValidationError`, `NotFoundError`, `ProviderError`, `InfrastructureError`, `PipelineExecutionError`, `BusinessFlowError`) or an upstream stdlib exception (`FileNotFoundError`, `RuntimeError`) translated at the flow boundary. |
| `provider_used` | string \| null | Provider interface name when the stage crossed a provider boundary, e.g. `ProjectFileStorageProvider`, `GeneratedAssetProvider`, `SpeechSynthesisProvider`, `RecommendationModelStoreProvider`. |

### Redaction rules

Identical to Pipeline-layer redaction in the Debug Logger and Audit Trace Strategy section:

- Dataset rows, uploaded bytes, full file paths under user content, LLM prompts, TTS text, customer-level analytics outputs and personal identifiers are forbidden in event payloads.
- Only counts, lengths, IDs, status strings, stage names, and provider interface names may be recorded.
- Errors must be summarized as `error_type` plus a non-sensitive short message; raw stack traces stay in the runtime logger or `error_message` persisted on the project, never in audit events.
- `TelemetryProvider` failures must not change flow business behavior; flow emission helpers swallow telemetry errors silently.

## Implemented Layout (Post-Migration Snapshot)

Migration completed 2026-05-25 on top of working tree at commit `18578a4` (uncommitted Phase 9 cleanup applied on top).

```text
backend/
  api/                         HTTP boundary. FastAPI routers only. Import surface limited to fastapi, pydantic,
                               backend.api.dependencies, backend.api.error_mapping, backend.business.pipelines.*,
                               backend.core.errors, backend.models.schemas. Enforced by tests/api/test_controller_thinness.py.
  business/
    pipelines/                 Stateless request-scoped orchestration. One pipeline per controller capability.
    flows/                     Long-running stateful lifecycles. Currently only ProjectAnalysisFlow.
  abilities/                   Pure domain atoms (association, prediction, clustering, recommendation, report, voice).
                               No fastapi / SDK / filesystem / global state.
  providers/                   Provider Interface contracts + DTOs + TelemetryProvider + ProvidersContainer.
                               Defines the only allowed boundary between business and infrastructure.
  infrastructure/
    adapters/                  Concrete provider implementations. The only place that may import edge_tts, httpx,
                               pandas, sklearn, mlxtend, json/pickle persistence, or FastAPI BackgroundTasks.
    factories/                 Provider Factory: assembles ProvidersContainer for a given request scope.
  core/
    config.py                  Settings(BaseSettings). Sole env reader.
    errors.py                  MarketMindError hierarchy. Internal error model.
    runtime_checks.py          CLI gate for config, providers, schemas, telemetry, audit, log schema, LLM/speech dry-run.
  models/                      Pydantic request/response schemas (frozen contract for frontend matrix).
  main.py                      FastAPI bootstrap. CORS + router registration only.
  services/                    Legacy. Retained as default handler of AnalysisJobProvider and dependency of inactive
                               prediction/clustering routers. New code MUST NOT import from here.
  utils/                       Empty package. MUST stay empty.
```

Layer responsibilities (one sentence each):

- **API**: Map HTTP <-> Pipeline call. Translate `MarketMindError` via `map_internal_error`.
- **Pipelines**: Compose ability + provider calls for one request.
- **Flows**: Own multi-step state transitions (`处理中 -> 已完成 / 失败`) and lifecycle events.
- **Abilities**: Pure algorithm / domain logic. No I/O.
- **Providers**: Capability contracts (interface + DTO). No implementation.
- **Adapters**: Bind a provider contract to a concrete SDK or persistence backend.
- **Factories**: Wire adapters into a `ProvidersContainer` per request.
- **Core**: Settings, error hierarchy, runtime check entry points.

## Observability Coverage Checklist

- [x] Request-Level Trace Context defined — §6 of the Debug Logger and Audit Trace Strategy block plus the trace context propagation section near the document tail.
- [x] Ability-Level Debug Event Contract defined — Debug Logger section, Ability-layer event schema.
- [x] Pipeline-Level Trace Event Contract defined — Debug Logger section, Pipeline-layer event schema.
- [x] Flow Lifecycle Audit Contract defined — Audit Trace section covering `ProjectAnalysisFlow` state transitions.
- [x] Telemetry Provider boundary defined — §11 Provider Boundary Design (`TelemetryProvider`) plus §15 Architecture Lint and §16 Runtime Check Strategy.
- [x] Runtime Check Strategy (including `check-telemetry`, `check-audit-sink`, `validate-log-schema`, `validate-audit-schema`) defined — §16. Verified live by `uv run python -m backend.core.runtime_checks check-telemetry` returning `events_emitted=3`.
- [x] Redaction policy defined — present at Ability layer, Pipeline layer, and Flow layer; final summary appears immediately above this checklist. Forbids dataset rows, uploaded bytes, user-content paths, LLM prompts, TTS text, customer analytics outputs, personal identifiers, and raw stack traces in event payloads.

### Emission boundary

- Flows emit via `providers.telemetry` only. Direct imports of `logging`, `print`, `httpx`, `edge_tts`, `pandas`, `sklearn`, `mlxtend`, `fastapi`, `backend.api`, and `backend.infrastructure` remain forbidden in `backend/business/flows/` and are enforced by Architecture Lint.
- Pipelines, controllers, abilities and providers retain their own event contracts; this section governs Business Flow scope only.
- Multi-flow scenarios in the future must keep `flow_run_id` distinct per flow invocation even when `trace_id` is shared via an upstream request.

## Request-Level Trace Context

Scope: every inbound HTTP request handled by `backend/api/*.py` controllers.

### Trace identifier lifecycle

- Each request carries a `trace_id`. If the inbound request supplies an `X-Trace-Id` or `X-Request-Id` header, that value is reused; otherwise a fresh `uuid4().hex` is generated at the controller boundary middleware.
- Controllers never call `uuid.uuid4` or other identifier generators directly; identifier creation lives in a single FastAPI dependency / middleware shared by all routers.
- The active `trace_id`, together with optional `actor_id` and `session_id` parsed from authentication, is attached to a per-request context object surfaced via `providers.telemetry`.

### Propagation rules

- `get_providers(background_tasks: BackgroundTasks)` builds the per-request `ProvidersContainer`. The trace context attaches to the `TelemetryProvider` for the lifetime of the request only.
- Pipelines and flows read trace context from `providers.telemetry`; they MUST NOT import `fastapi`, `starlette`, the logging SDK or any HTTP client to inject identifiers themselves.
- Background tasks scheduled through `providers.analysis_jobs` inherit the originating `trace_id` by passing it as a job field; the background handler attaches the same identifier when it builds its own telemetry events.

### Error mapping coupling

- `backend/api/error_mapping.py:map_internal_error` is the single conversion point from `MarketMindError` to `HTTPException`. The `trace_id` of the failing request is recorded by the controller-boundary middleware on the response (header `X-Trace-Id`) and emitted by telemetry; the `detail` body remains a stable end-user string.
- Controllers MUST catch `MarketMindError` exactly once at handler exit and delegate to `map_internal_error`. No per-handler `try/except` on concrete error subclasses, no logging from controllers — telemetry events are emitted by pipelines/flows or by the middleware that owns the request lifecycle.

### Forbidden patterns

- Controller files call `uuid.uuid4` / `secrets.token_hex` for tracing purposes.
- Business code (`backend/business/`, `backend/abilities/`) imports `logging`, `structlog`, `httpx`, or `fastapi` to read or stamp trace identifiers.
- Trace identifiers are echoed back into response bodies as part of the public contract (only as headers and as fields of telemetry events).
