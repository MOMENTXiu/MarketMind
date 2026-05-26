# MarketMind Backend

FastAPI backend for Retail V2, Data Processing, and customer text suggestions.

## Runtime Architecture

```text
API Controller
  -> Business Flow / Pipeline
  -> Ability Atom
  -> Provider Interface / ProvidersContainer
  -> Infrastructure Adapter
```

## Active Runtime

- App entry: `backend/main.py`
- Active API: `backend/api/analysis.py`
- Dependency factories: `backend/api/dependencies.py`
- Error mapping: `backend/api/error_mapping.py`
- Retail flow: `backend/business/flows/retail_analysis_flow.py`
- Data Processing flow: `backend/business/flows/data_processing_analysis_flow.py`
- Retail pipelines: `backend/business/pipelines/retail_*_pipeline.py`
- Data Processing pipelines: `backend/business/pipelines/dataset_regularization_pipeline.py`, `backend/business/pipelines/universal_*_pipeline.py`
- Ability atoms: `backend/abilities/retail/`, `backend/abilities/regularization/`, `backend/abilities/universal_analysis/`
- Provider contracts: `backend/providers/`
- Infrastructure adapters and DB foundation: `backend/infrastructure/`
- Runtime checks: `backend/core/runtime_checks.py`

Legacy project/recommend/association controllers and `backend/services/*` are retired. Do not reintroduce compatibility wrappers unless explicitly requested.

## API Groups

| Group | Purpose |
| --- | --- |
| `/api/analysis/projects...` | Retail Analysis V2 projects, upload, run, artifacts, recommendations, marketer insights. |
| `/api/analysis/jobs...` | Data Processing create/upload/regularize/run/status/outputs/datasets/sidecars. |
| `/api/analysis/customer-suggestions` | Text-only customer/product suggestion generation through the LLM provider boundary. |
| `/api/health/` | Health check. |

Detailed contract: `docs/backend-api.md`.

## Data Processing

The generalized chain is implemented in backend runtime:

```text
raw upload -> regularization -> analysis2 universal analysis -> outputs
```

Source material under `analysis/data-processing-pipeline/` is archive/reference only. Runtime code must live under `backend/abilities/`, `backend/business/`, `backend/providers/`, and `backend/infrastructure/`.

Regularization review gate blocks only core fields with `need_review`; optional/marketing fuzzy mappings do not block analysis.

## Persistence

Current runtime truth source remains filesystem/JSON:

- `data/projects.json`
- `data/projects/{project_id}/`
- `data/projects/{project_id}/analysis/...`
- `outputs/`

PostgreSQL infrastructure exists for migration work:

- `backend/infrastructure/db/`
- `backend/infrastructure/adapters/postgres_project_repository_adapter.py`
- `alembic/`
- `docker-compose.dev.yml`

Business read/write switch, historical migration, and Redis-backed queue are not implemented yet.

## Commands

Run from repository root:

```bash
make lint
make format
make test
make check
make hooks
```

Optional local infrastructure:

```bash
make infra-up
make db-migrate
make infra-down
```

`make typecheck` and `make clean` are placeholders.
