# MarketMind Architecture

MarketMind is a Vue 3 + FastAPI retail marketing system. The backend now uses a layered architecture so future work can change storage, LLM, TTS, and analysis implementations without pushing SDK or filesystem details into API handlers.

## Runtime Shape

```text
Browser / Vue 3
  -> FastAPI Controller
  -> Business Pipeline or ProjectAnalysisFlow
  -> Ability Atom
  -> Provider Interface / ProvidersContainer
  -> Infrastructure Adapter
  -> local files, JSON storage, Edge TTS, LLM HTTP APIs
```

`ProjectAnalysisFlow` is the only Business Flow because upload/reanalysis is a background lifecycle with status transitions, multiple analysis stages, generated artifacts, model refresh, and failure handling. CRUD, recommendation, association, voice, and read-model paths use Business Pipelines.

## Backend Layers

| Layer | Path | Responsibility |
| --- | --- | --- |
| API Controller | `backend/api/` | Parse HTTP input, call one pipeline/flow, map internal errors to current FastAPI responses. |
| Business Orchestration | `backend/business/pipelines/`, `backend/business/flows/` | Coordinate use cases and preserve status/side-effect ordering. No SDK, storage client, or FastAPI response construction. |
| Ability Atom | `backend/abilities/` | Pure or provider-backed atomic actions: association rules, forecast, clustering, recommendations, report text, voice text/TTS. |
| Provider Boundary | `backend/providers/` | Protocols, DTOs, and frozen `ProvidersContainer` for repository, file, model, dataset, LLM, TTS, jobs, and telemetry. |
| Infrastructure | `backend/infrastructure/` | Concrete adapters for JSON storage, local files/assets, CSV/rules/model artifacts, Edge TTS, OpenAI/Anthropic-compatible LLMs, background jobs, telemetry. |
| Core | `backend/core/` | Settings, internal errors, legacy storage compatibility, and runtime check CLI. |

## Key Directories

```text
backend/
  api/
    dependencies.py        # Provider/pipeline dependency factories
    error_mapping.py       # MarketMindError -> HTTPException mapping
    projects.py            # Thin HTTP boundary for project resources
    association.py
    recommend.py
    voice.py
    ai_voice.py
    prediction.py          # Inactive router; not registered in main.py
    clustering.py          # Inactive router; not registered in main.py
  business/
    flows/project_analysis_flow.py
    pipelines/
      project_pipeline.py
      dataset_upload_pipeline.py
      project_read_pipelines.py
      recommendation_pipeline.py
      association_analysis_pipeline.py
      voice_synthesis_pipeline.py
      ai_voice_broadcast_pipeline.py
  abilities/
    association/
    prediction/
    clustering/
    recommendation/
    report/
    voice/
  providers/
    container.py
    *_provider.py
    dtos.py
    telemetry_dtos.py
  infrastructure/
    adapters/
    factories/provider_factory.py
  core/
    config.py
    errors.py
    runtime_checks.py
    storage.py
  services/                # Legacy services retained for compatible handlers/adapters
```

Frontend:

```text
frontend/
  src/
    views/
    components/
    router/
    stores/
    utils/http.ts
    env.d.ts
  package.json
  vite.config.ts
```

## Active API Surface

Base URL in local development is `http://localhost:8000/api`. API docs are served at `http://localhost:8000/api/docs`.

| Area | Active Routes |
| --- | --- |
| Health | `GET /`, `GET /api/health/` |
| Projects | `POST /api/projects/`, `GET /api/projects/`, `GET/PUT/DELETE /api/projects/{id}/` |
| Upload / lifecycle | `POST /api/projects/{id}/upload/`, `POST /api/projects/{id}/reanalyze/` |
| Project outputs | `GET /api/projects/{id}/download/report/`, `GET /api/projects/{id}/audio/`, `GET /api/projects/{id}/customers/` |
| Project recommendation | `GET /api/projects/{id}/recommend/` |
| Association | `POST /api/association/analyze/`, `GET /api/association/status/` |
| Recommendation | `GET /api/recommend/user/`, `GET /api/recommend/item/`, `POST /api/recommend/calculate/`, `POST /api/recommend/tts/play/` |
| Voice | `POST /api/voice/tts/`, `POST /api/voice/generate/`, `GET /api/voice/status/` |
| AI voice | `POST /api/ai-voice/broadcast/`, `POST /api/tts/`, `GET /api/ai-voice/audio/{filename}/` |

`backend/api/prediction.py` and `backend/api/clustering.py` remain inactive and are not registered in `backend/main.py`.

## Main Flows

Project upload:

```text
POST /api/projects/{id}/upload/
  -> DatasetUploadPipeline
  -> ProjectRepositoryProvider + ProjectFileStorageProvider
  -> AnalysisJobProvider
  -> ProjectAnalysisFlow background handler
```

Project analysis:

```text
ProjectAnalysisFlow
  -> association / forecast / clustering / report / voice / recommendation-model steps
  -> generated files and model artifacts through providers/adapters
  -> project status 已完成 or 失败
```

Recommendation:

```text
Controller
  -> RecommendationPipeline or ProjectRecommendationPipeline
  -> recommendation / association abilities
  -> model, rule, dataset, asset, speech providers
```

Voice and AI broadcast:

```text
Controller
  -> VoiceSynthesisPipeline or AIVoiceBroadcastPipeline
  -> report/voice abilities
  -> SpeechSynthesisProvider and LLMProvider
  -> GeneratedAssetProvider for playable URLs
```

## Persistence And Generated Assets

- Project metadata: `data/projects.json`
- Project workspace: `data/projects/{project_id}/`
- Uploaded dataset: `data/projects/{project_id}/dataset.csv`
- Project reports/audio/customers: `data/projects/{project_id}/outputs/` and `data/projects/{project_id}/customers.csv`
- Global static assets: `outputs/`
- AI voice audio lookup: `/tmp/{filename}` then `backend/data/audio/{filename}`
- Recommendation model artifact: `backend/data/model_data.pkl`
- Dynamic rules: `backend/data/dynamic_rules.csv`

## Quality And Runtime Checks

Primary commands:

```bash
make lint
make format
make test
make build
make check
```

`make check` runs backend Ruff lint, backend Ruff format check, backend pytest, and frontend `npm run build`.

Runtime checks live in `backend/core/runtime_checks.py` and are intended for local or CI smoke validation:

```bash
uv run python -m backend.core.runtime_checks check-config
uv run python -m backend.core.runtime_checks check-providers
uv run python -m backend.core.runtime_checks validate-api-schemas
uv run python -m backend.core.runtime_checks check-telemetry
```

Architecture import rules are enforced by `tests/test_architecture_imports.py`. Current backend pytest coverage is 104 tests.
