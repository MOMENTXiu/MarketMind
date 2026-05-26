# Quickstart

MarketMind runs as a split Vue 3 + FastAPI application. Run commands from the repository root unless a step says otherwise.

## Requirements

- Python 3.13.x (`pyproject.toml` requires `>=3.13,<3.14`)
- uv
- Node.js 18+ and npm

## One-command Start

macOS / Linux:

```bash
bash scripts/start-project.sh
```

Windows:

```bat
scripts\start-project.bat
```

Default local URLs:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api`
- API docs: `http://localhost:8000/api/docs`

## Manual Start

Install backend dependencies:

```bash
uv sync
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the backend:

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

## Verify The Workspace

Run the full local quality gate:

```bash
make check
```

Equivalent pieces:

```bash
make lint
make test
make build
```

Current baseline after the Analysis V2 and data-processing pipeline migrations:

- Backend tests: 188 pytest tests
- Backend lint/format: Ruff
- Frontend build/type validation: `npm run build` (`vue-tsc && vite build`)

`make typecheck` and `make clean` are placeholders and should not be treated as verification evidence.

## Runtime Checks

The backend includes a CLI smoke-check module:

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

## Example Dataset

Use `tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv` for Retail Analysis V2 smoke tests. Uploaded runtime datasets and generated outputs are project-scoped under:

```text
data/projects/{project_id}/analysis/...
```

Supported upload file type:

- `.csv`

Retail Analysis V2 expects the Chinese raw retail sales columns defined by `RETAIL_RAW_SALES_COLUMNS` in `backend/providers/dtos.py`.

The generalized data-processing chain is implemented in backend runtime
(`backend/abilities/regularization/`, `backend/abilities/universal_analysis/`,
`backend/business/flows/data_processing_analysis_flow.py`). The original source
archive remains under `analysis/data-processing-pipeline/` as reference.

## Optional Streamlit Entry

The repository still contains `app.py` as an optional standalone Streamlit entry. It is not the primary application path after the FastAPI + Vue architecture migration.

```bash
uv run streamlit run app.py
```

## Useful Files

- `AGENTS.md`: agent-facing project baseline and quality rules
- `docs/ARCHITECTURE.md`: current architecture overview
- `docs/architecture/architecture-change.md`: detailed migration record
- `docs/architecture/construction-checklist.md`: staged migration checklist and verification notes
- `docs/architecture/data-processing-pipeline-integration-design.md`: future raw upload -> regularization -> analysis2 architecture plan
- `docs/architecture/data-processing-pipeline-integration-checklist.md`: future data-processing migration checklist
- `docs/commands.md`: Makefile command contract
- `docs/env.md`: environment variable policy
