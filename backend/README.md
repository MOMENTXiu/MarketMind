# MarketMind Backend

FastAPI backend for MarketMind. The implemented runtime uses a layered
architecture:

```text
API Controller
  -> Business Pipeline / RetailAnalysisFlow
  -> Ability Atom
  -> Provider Interface / ProvidersContainer
  -> Infrastructure Adapter
```

## Current Runtime

- API entry: `backend/main.py`
- Active analysis API: `backend/api/analysis.py`
- Current analysis flow: `backend/business/flows/retail_analysis_flow.py`
- Retail pipelines: `backend/business/pipelines/retail_*_pipeline.py`
- Retail abilities: `backend/abilities/retail/`
- Provider contracts: `backend/providers/`
- Local adapters and factory: `backend/infrastructure/`
- Runtime checks: `backend/core/runtime_checks.py`

Legacy project/recommend/association controllers and `backend/services/*` are
retired. Do not reintroduce compatibility wrappers unless explicitly requested.

## Planned Data-Processing Chain

The next target architecture is:

```text
raw upload -> regularization -> analysis2 universal analysis -> outputs
```

Source material is archived under `analysis/data-processing-pipeline/`.
Backend runtime must not import that archive directly. Migrate logic into the
layered backend following:

- `docs/architecture/data-processing-pipeline-integration-design.md`
- `docs/architecture/data-processing-pipeline-integration-checklist.md`

## Commands

Run from the repository root:

```bash
make lint
make format
make test
make build
make check
make hooks
```

`make typecheck` and `make clean` are placeholders; do not report them as
successful verification.
