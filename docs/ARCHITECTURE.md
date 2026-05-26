# MarketMind Architecture

MarketMind is a Vue 3 + FastAPI retail marketing system. The backend now uses a layered architecture so future work can change storage, LLM, TTS, and analysis implementations without pushing SDK or filesystem details into API handlers.

As of 2026-05-26, the backend runtime has two analysis chains under `/api/analysis`:

1. **Retail Analysis V2** — the existing project-scoped retail pipeline.
2. **Data-processing chain** — the new `regularization` -> `analysis2` universal
   analysis lifecycle, fully implemented and running alongside Retail V2.

Both chains share the same layered architecture and provider/adapter boundary.
The data-processing design docs remain in
`docs/architecture/data-processing-pipeline-integration-design.md` and
`docs/architecture/data-processing-pipeline-integration-checklist.md` for reference.

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

`RetailAnalysisFlow` is the existing Retail V2 Business Flow.
`DataProcessingAnalysisFlow` is the new chain-native flow for the data-processing
pipeline (raw upload -> regularization -> universal analysis -> outputs).
Both are background lifecycles with status transitions, stage tracking, generated
artifacts, and failure handling. Voice and AI broadcast paths remain separate
Business Pipelines.

## Backend Layers

| Layer | Path | Responsibility |
| --- | --- | --- |
| API Controller | `backend/api/` | Parse HTTP input, call one pipeline/flow, map internal errors to current FastAPI responses. |
| Business Orchestration | `backend/business/pipelines/`, `backend/business/flows/` | Coordinate use cases and preserve status/side-effect ordering. No SDK, storage client, or FastAPI response construction. |
| Ability Atom | `backend/abilities/` | Pure atomic analysis actions, including Retail V2 cleaning, feature engineering, segmentation, association/HUIM, recommendation, marketer insight, and voice/report helpers. |
| Provider Boundary | `backend/providers/` | Protocols, DTOs, and frozen `ProvidersContainer` for repository, files, generated assets, datasets, retail datasets, regularized datasets, analysis artifacts, analysis models, recommendation models, LLM, TTS, jobs, and telemetry. |
| Infrastructure | `backend/infrastructure/` | Concrete adapters for JSON storage, local files/assets, CSV/rules/model artifacts, Retail CSV datasets, regularized datasets, local Analysis V2 artifacts/models, Edge TTS, OpenAI/Anthropic-compatible LLMs, background jobs, telemetry. |
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
    flows/data_processing_analysis_flow.py
    flows/data_processing_analysis_state.py
    pipelines/
      retail_dataset_preparation_pipeline.py
      retail_feature_engineering_pipeline.py
      retail_segmentation_pipeline.py
      retail_association_pipeline.py
      retail_recommendation_pipeline.py
      retail_marketer_insight_pipeline.py
      retail_report_pipeline.py
      dataset_regularization_pipeline.py
      universal_overview_pipeline.py
      universal_profile_segmentation_pipeline.py
      universal_association_pipeline.py
      universal_recommendation_pipeline.py
      universal_promotion_pipeline.py
      universal_summary_pipeline.py
      voice_synthesis_pipeline.py
      ai_voice_broadcast_pipeline.py
  abilities/
    regularization/
    universal_analysis/
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
| Retail Analysis V2 dataset/lifecycle | `POST /api/analysis/projects/{id}/dataset`, `POST /api/analysis/projects/{id}/run`; project status is returned by `GET /api/analysis/projects/{id}` |
| Retail Analysis V2 outputs | `GET /api/analysis/projects/{id}/artifacts/{artifact_id}`, `GET /api/analysis/projects/{id}/datasets/{dataset_id}`, `GET /api/analysis/projects/{id}/models/{model_type}/{version}` |
| Retail Analysis V2 read models | `GET /api/analysis/projects/{id}/recommendations`, `GET /api/analysis/projects/{id}/marketer-insights` |
| Data-processing jobs | `POST /api/analysis/jobs`, `GET /api/analysis/jobs/{job_id}` |
| Data-processing upload/regularize/run | `POST /api/analysis/jobs/{job_id}/raw-dataset`, `POST /api/analysis/jobs/{job_id}/regularize`, `POST /api/analysis/jobs/{job_id}/run` |
| Data-processing read | `GET /api/analysis/jobs/{job_id}/datasets/{dataset_id}`, `GET /api/analysis/jobs/{job_id}/sidecars/{sidecar_id}` |
| Data-processing outputs | `GET /api/analysis/jobs/{job_id}/outputs` |
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

Data-processing chain lifecycle:

```text
POST /api/analysis/jobs/{job_id}/raw-dataset
  -> DataProcessingAnalysisFlow.upload_raw_dataset
  -> RegularizedDatasetProvider (raw upload)

POST /api/analysis/jobs/{job_id}/regularize
  -> DataProcessingAnalysisFlow.regularize
  -> DatasetRegularizationPipeline
  -> regularization ability atoms
  -> RegularizedDatasetProvider (normalized dataset + sidecars)
  -> job status queued, needs_review, or completed

POST /api/analysis/jobs/{job_id}/run
  -> DataProcessingAnalysisFlow.run_analysis
  -> universal analysis pipelines (overview, profile, association, recommendation, promotion, summary)
  -> universal_analysis ability atoms
  -> AnalysisArtifactProvider + AnalysisModelStoreProvider
  -> job status processing, completed, or failed
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

`analysis/data-processing-pipeline/` is a source archive for the planned
generalized data-processing chain. It contains:

- `regularization/`: arbitrary retail input -> standard schema +
  `capability.json`.
- `analysis2/`: standard schema + capability -> universal analysis outputs.
- `analysis/`: fixed retail analysis benchmark and algorithm reference.

Backend runtime code must not import this archive directly. Migrate logic into
`backend/abilities`, `backend/business`, `backend/providers`, and
`backend/infrastructure` according to the data-processing integration design and
checklist.

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
uv run python -m backend.core.runtime_checks check-data-processing --sample --sandbox
uv run python -m backend.core.runtime_checks check-regularization --sandbox
uv run python -m backend.core.runtime_checks check-analysis-optional-runtime
```

Architecture import rules are enforced by `tests/test_architecture_imports.py`. Current backend pytest coverage is 174 tests.
