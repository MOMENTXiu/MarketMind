# Development

## Workflow

1. Create or update code in the relevant module.
2. Update docs when behavior or commands change.
3. Run `make lint`.
4. Fix lint issues with minimal changes.
5. Run `make lint` again.
6. Run `make format`.
7. Run `make lint` again after formatting.
8. Run `make check` or `make verify` when commands are configured.

Do not treat placeholder targets as successful verification.

## Quality Gate

Quality gate level: full

Setup scripts generate command entry points and hook configuration only. They do not run lint, format, test, build, pre-commit, or CI, and they cannot prove those commands pass.

Current configured checks:

- Backend lint: `uv run ruff check .`
- Backend format check: `uv run ruff format --check .`
- Backend tests: `uv run pytest`
- Frontend build/type validation: `cd frontend && npm run build`

Current backend test baseline covers API contracts (Retail V2 + data-processing
chain-native), controller thinness, Retail V2 flows/pipelines, data-processing
regularization/universal analysis abilities, provider adapters, DB
infrastructure smoke tests, runtime checks, and architecture import rules.
The latest local baseline is `217 passed, 5 skipped`; the skipped tests are optional/live-infra paths.

The backend runtime now has two analysis chains:
1. Retail V2 — the existing project-scoped retail pipeline.
2. Data-processing chain (`regularization -> analysis2`) — implemented in
   `backend/abilities/regularization/`, `backend/abilities/universal_analysis/`,
   `backend/business/pipelines/`, and `backend/business/flows/`. The original
   source archive remains under `analysis/data-processing-pipeline/` as
   reference; backend runtime code must not import from it directly.

`make check` is the canonical local gate because it combines backend lint, backend format check, backend tests, and frontend build/type validation.

Frontend business pages call backend endpoints through `frontend/src/api/`. Do not add page-local raw axios calls for MarketMind business APIs, retired `/api/projects` / `/api/recommend` / `/api/association` routes, or browser direct LLM `/chat/completions` / `/models` calls.

## Local Infrastructure

The PostgreSQL and Redis development services are available through Docker Compose, but the backend still runs on the host in this phase.

- Start services: `make infra-up`
- Stop services: `make infra-down`
- Reset named volumes and restart services: `make infra-reset`
- Follow service logs: `make infra-logs`
- Apply migrations: `make db-migrate`
- Downgrade migrations to base: `make db-downgrade`
- Create an Alembic revision: `make db-revision DB_REVISION_MESSAGE="describe change"`

`DATABASE_URL` points at the local development database. `TEST_DATABASE_URL` must point at an isolated database because DB integration tests and migration roundtrips may drop and recreate tables.
On a fresh named volume, `docker-compose.dev.yml` runs `scripts/postgres-init/01-create-test-db.sql` to create `marketmind_test`; use `make infra-reset` if an older local volume was initialized before that script existed.

## Retail Worker Runtime

Retail V2 analysis jobs use Redis/RQ through `AnalysisJobQueueProvider`, and workers enter through `backend/workers/retail_analysis_worker.py`. Run `scripts/start-worker.sh` or `scripts/start-project.sh` when testing the full local stack. Retail project state is PostgreSQL-backed; generated artifacts and model payloads still remain file-backed and must be accessed through API refs.

## Commit Convention

feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert, arch, prompt, agent

## Hooks

Hook level: full

Install hooks only after reviewing `.pre-commit-config.yaml`. Before commit, run `make hooks` when hooks are enabled. If hooks modify files, inspect the diff and rerun lint and hooks.
