# MarketMind Architecture

MarketMind is a Vue 3 + FastAPI retail marketing system. The backend now uses a layered architecture so future work can change storage, LLM, TTS, and analysis implementations without pushing SDK or filesystem details into API handlers.

## Runtime Shape

```text
Browser / Vue 3
  -> FastAPI Controller
  -> Business Pipeline or RetailAnalysisFlow
  -> Ability Atom
  -> Provider Interface / ProvidersContainer
  -> Infrastructure Adapter
  -> local files, JSON storage, Edge TTS, LLM HTTP APIs
```

`RetailAnalysisFlow` is the main Analysis V2 Business Flow because upload/reanalysis is a background lifecycle with status transitions, multiple retail analysis stages, generated artifacts, model persistence, and failure handling. Voice and AI broadcast paths remain separate Business Pipelines.

## Backend Layers

| Layer | Path | Responsibility |
| --- | --- | --- |
| API Controller | `backend/api/` | Parse HTTP input, call one pipeline/flow, map internal errors to current FastAPI responses. |
| Business Orchestration | `backend/business/pipelines/`, `backend/business/flows/` | Coordinate use cases and preserve status/side-effect ordering. No SDK, storage client, or FastAPI response construction. |
| Ability Atom | `backend/abilities/` | Pure atomic analysis actions, including Retail V2 cleaning, feature engineering, segmentation, association/HUIM, recommendation, marketer insight, and voice/report helpers. |
| Provider Boundary | `backend/providers/` | Protocols, DTOs, and frozen `ProvidersContainer` for repository, files, generated assets, datasets, retail datasets, analysis artifacts, analysis models, recommendation models, LLM, TTS, jobs, and telemetry. |
| Infrastructure | `backend/infrastructure/` | Concrete adapters for JSON storage, local files/assets, CSV/rules/model artifacts, Retail CSV datasets, local Analysis V2 artifacts/models, Edge TTS, OpenAI/Anthropic-compatible LLMs, background jobs, telemetry. |
| Core | `backend/core/` | Settings, internal errors, legacy storage compatibility, and runtime check CLI. |

## Key Directories

```text
backend/
  api/
    dependencies.py        # Provider/pipeline dependency factories
    error_mapping.py       # MarketMindError -> HTTPException mapping
    analysis.py            # Retail Analysis V2 HTTP boundary
    voice.py
    ai_voice.py
  business/
    flows/retail_analysis_flow.py
    flows/retail_analysis_state.py
    pipelines/
      retail_dataset_preparation_pipeline.py
      retail_feature_engineering_pipeline.py
      retail_segmentation_pipeline.py
      retail_association_pipeline.py
      retail_recommendation_pipeline.py
      retail_marketer_insight_pipeline.py
      retail_report_pipeline.py
      voice_synthesis_pipeline.py
      ai_voice_broadcast_pipeline.py
  abilities/
    retail/
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
| Retail Analysis V2 projects | `POST /api/analysis/projects`, `GET /api/analysis/projects`, `GET/DELETE /api/analysis/projects/{id}` |
| Retail Analysis V2 dataset/lifecycle | `POST /api/analysis/projects/{id}/dataset`, `POST /api/analysis/projects/{id}/run`, `GET /api/analysis/projects/{id}/status` |
| Retail Analysis V2 outputs | `GET /api/analysis/projects/{id}/artifacts/{artifact_id}`, `GET /api/analysis/projects/{id}/datasets/{dataset_id}`, `GET /api/analysis/projects/{id}/models/{model_type}/{version}` |
| Retail Analysis V2 read models | `GET /api/analysis/projects/{id}/recommendations`, `GET /api/analysis/projects/{id}/marketer-insights` |
| Voice | `POST /api/voice/tts/`, `POST /api/voice/generate/`, `GET /api/voice/status/` |
| AI voice | `POST /api/ai-voice/broadcast/`, `POST /api/tts/`, `GET /api/ai-voice/audio/{filename}/` |

Legacy `/api/projects`, `/api/recommend`, and `/api/association` routes are retired and intentionally return 404.

## Main Flows

Retail Analysis V2 lifecycle:

```text
POST /api/analysis/projects/{id}/dataset
  -> RetailAnalysisFlow.upload_dataset
  -> RetailDatasetPreparationPipeline
  -> RetailDatasetProvider + AnalysisArtifactProvider
  -> AnalysisJobProvider
  -> RetailAnalysisFlow scheduled handler
```

Retail Analysis V2 analysis:

```text
RetailAnalysisFlow
  -> feature engineering / segmentation / association / recommendation / marketer insight / report pipelines
  -> retail ability atoms
  -> generated Analysis V2 refs through AnalysisArtifactProvider and AnalysisModelStoreProvider
  -> project status pending, processing, completed, or failed
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
- Retail Analysis V2 datasets/artifacts/models: `data/projects/{project_id}/analysis/...`
- Global static assets: `outputs/`
- AI voice audio lookup: `/tmp/{filename}` then `backend/data/audio/{filename}`
- Recommendation model artifact: `backend/data/model_data.pkl`
- Dynamic rules: `backend/data/dynamic_rules.csv`

`analysis/` is an algorithm blueprint/reference directory. Backend runtime code must not import `analysis/code_files` directly and must not write runtime outputs to `analysis/output`.

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
uv run python -m backend.core.runtime_checks check-analysis-artifacts --sandbox
uv run python -m backend.core.runtime_checks check-retail-analysis --sample
uv run python -m backend.core.runtime_checks check-analysis-optional-runtime
```

Architecture import rules are enforced by `tests/test_architecture_imports.py`. Current backend pytest coverage is 123 tests.
