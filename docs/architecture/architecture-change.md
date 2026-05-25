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
| `.env.example` | 未发现。 |
| `docker-compose.yml` | 未发现。 |
| `Dockerfile` | 未发现。 |
| `Makefile` | 未发现。 |
| `justfile` | 未发现。 |
| `.github/workflows` | 未发现。 |
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

| Importing File | Imported Object | Violation | Target Direction |
|---|---|---|---|
| `backend/api/projects.py` | `backend.core.storage.storage` | API Controller imports storage adapter/global repository directly | Controller -> Pipeline -> Provider Interface |
| `backend/api/projects.py` | `backend.core.recommend.query_item_relations` | API Controller imports algorithm/core directly | Controller -> Recommendation Pipeline -> Ability |
| `backend/api/projects.py` | `backend.services.analysis_service.run_project_analysis` | Controller schedules concrete business function directly | Controller -> Flow/Pipeline -> Job Provider |
| `backend/api/association.py` | `AssociationService()` global | Controller constructs concrete service globally | Controller -> Pipeline via dependency/provider wiring |
| `backend/api/voice.py` | `VoiceService()`, `TTSService()` globals | Controller constructs service and SDK-facing wrapper | Controller -> Voice Pipeline -> Provider Interface |
| `backend/api/recommend.py` | `get_recommender`, `generate_tts` | Controller calls cached concrete service and TTS helper | Controller -> Recommendation Pipeline |
| `backend/api/ai_voice.py` | `AIVoiceService` | Controller calls service that directly reaches LLM/TTS SDKs | Controller -> AI Voice Pipeline -> Abilities -> Providers |
| `backend/services/analysis_service.py` | `backend.core.storage.storage` | Business service imports concrete storage | Flow -> Provider Interface |
| `backend/services/ai_voice_service.py` | `httpx`, `edge_tts` | Business service imports HTTP client and TTS SDK | Ability -> Provider Interface -> Adapter |
| `backend/services/tts_service.py` | `edge_tts` | SDK wrapper located in service layer, no provider boundary | Provider Interface -> Adapter |
| `backend/services/recommender_service.py` | `TTSService` | Recommendation service calls TTS concrete implementation | Pipeline -> SpeechSynthesisProvider |

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

### 10.4 Provider Boundary

Target directory:

```text
backend/providers/
  container.py
  factory.py
  project_repository_provider.py
  project_file_storage_provider.py
  generated_asset_provider.py
  dataset_provider.py
  association_rule_store_provider.py
  recommendation_model_store_provider.py
  speech_synthesis_provider.py
  llm_provider.py
  analysis_job_provider.py
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
```

Fields intentionally not included because current backend has no direct use:

- `browser`
- `queue` as external queue client; `analysis_jobs` covers current FastAPI BackgroundTasks semantics.
- `telemetry`
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

## 17. Test Strategy

Existing tests: none found. Existing test tooling exists in `pyproject.toml`:

| Purpose | Command | Exists | Notes |
|---|---|---|---|
| Install Python deps | `uv sync` | YES | Documented in README/scripts. |
| Run backend dev server | `uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` | YES | Used by `scripts/start-backend.sh`. |
| Python tests | `uv run pytest tests/` | PARTIAL | pytest configured, but no tests found. |
| Python formatter | `uv run black .` | YES | black configured in `pyproject.toml`. |
| Python linter | `uv run ruff check .` | YES | ruff configured in `pyproject.toml`. |
| Frontend dev server | `cd frontend && npm run dev` | YES | `frontend/package.json`. |
| Frontend build/type check | `cd frontend && npm run build` | YES | runs `vue-tsc && vite build`. |
| Frontend preview | `cd frontend && npm run preview` | YES | Vite preview. |
| Architecture Lint | `uv run pytest tests/test_architecture_imports.py` | NO | Must be added before migration. |
| Runtime Check | `uv run python -m backend.core.runtime_checks check-providers` | NO | Must be added after provider factory exists. |
| CI | UNKNOWN | `.github/workflows` not found. |
| Makefile / justfile | NO | Not present. |

Required validation order for migration phases:

1. Project static check: `uv run ruff check .`
2. Architecture Lint: `uv run pytest tests/test_architecture_imports.py`
3. Type/contract check: Python Pydantic schema tests and `cd frontend && npm run build`
4. Affected tests: API smoke / pipeline / provider contract tests for touched path
5. Full tests: `uv run pytest tests/`
6. Runtime Check: provider/config/storage/dry-run commands
7. Trace/log inspection: inspect flow logs and error paths

Minimum behavior protection before code migration:

- API smoke tests for project create/upload/reanalyze/list/detail/customers/recommendation/TTS/AI voice response shapes.
- Business flow test for project analysis status transitions and output paths using fixtures and fake providers.
- Provider contract tests for JSON project repository, local asset storage, Edge TTS fake adapter, LLM fake adapter.
- Architecture import lint to prevent new direct SDK/storage access from controllers/business layers.

## 18. Phased Migration Plan

1. Establish behavior anchors: add tests for current public API contracts, status strings, generated asset URLs, and analysis status transitions.
2. Add Provider Interfaces, internal DTOs, internal errors, Providers Container, and Provider Factory without rewiring behavior.
3. Add External Adapters that wrap current JSON/filesystem/LLM/TTS behavior while preserving paths and response shapes.
4. Extract Ability Atoms from analysis, recommendation, clustering, prediction, report, and voice code behind provider interfaces.
5. Extract Business Pipelines for CRUD, recommendation, customer read model, association analysis, voice synthesis, and AI broadcast.
6. Extract `ProjectAnalysisFlow` for upload/reanalysis background lifecycle.
7. Thin API Controllers to protocol conversion and error mapping only.
8. Add Architecture Lint, Runtime Check, full test run, and trace/log inspection.
9. Remove dead compatibility code only after tests prove no frontend/API behavior changed.

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

## 21. Risks

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
