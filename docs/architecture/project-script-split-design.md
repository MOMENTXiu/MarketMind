# Project Script Split Design

Status: active design, 2026-05-28.

## Goal

Split the current full-stack startup script into two explicit entrypoints:

```text
scripts/deploy-project.sh
scripts/deploy-project.bat
scripts/start-project.sh
scripts/start-project.bat
```

The target distinction is:

- `deploy-project`: prepare infrastructure, dependencies, runtime wiring,
  migrations, and seed data.
- `start-project`: start backend, worker, and frontend processes, wait until
  they are ready, and clean them up on exit.

All backend Python process entrypoints must use `uv` and prefer
`uv run python -m ...` instead of console scripts.

## Current Findings

`scripts/start-project.sh` currently combines deployment preparation and process
startup:

- checks local requirements
- starts Docker infrastructure
- waits for Postgres / Redis / MinIO
- runs `uv sync`
- installs frontend dependencies
- runs runtime checks
- runs Alembic migrations
- starts backend through `scripts/start-backend.sh`
- starts worker through `scripts/start-worker.sh`
- starts frontend through `scripts/start-frontend.sh`
- cleans up child processes and Docker infrastructure on Ctrl+C

The shell backend/worker scripts already use the safer pattern:

```text
uv run python -m alembic upgrade head
uv run python -m uvicorn backend.main:app ...
uv run python -m rq.cli worker ...
```

The Windows scripts still use console-script forms in several places:

```text
uv run alembic upgrade head
uv run uvicorn backend.main:app ...
uv run rq worker ...
```

Those should be changed to:

```text
uv run python -m alembic upgrade head
uv run python -m uvicorn backend.main:app ...
uv run python -m rq.cli worker ...
```

## Target Script Ownership

### `deploy-project.sh` / `deploy-project.bat`

Responsibilities:

- locate repo root
- check required tools:
  - Python
  - `uv`
  - Node.js
  - npm
  - Docker
  - curl where available
- export or set production-like local runtime defaults:
  - `REDIS_ENABLED=true`
  - `TASK_QUEUE_BACKEND=redis`
  - `REDIS_URL=redis://localhost:6379/0`
  - `DATABASE_URL=postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind`
  - `ANALYSIS_QUEUE_NAME=retail-analysis`
  - when MinIO is implemented, object storage env defaults such as
    `OBJECT_STORAGE_BACKEND=minio`
- start Docker infrastructure:
  - Postgres
  - Redis
  - MinIO
  - MinIO bootstrap/init service if present
- wait until infrastructure is healthy
- run backend dependency sync:
  - `uv sync`
- install frontend dependencies:
  - prefer existing project behavior for `frontend/node_modules`
  - use npm only in `frontend/`
- run backend runtime checks:
  - `uv run python -m backend.core.runtime_checks check-retail-runtime --dry-run`
  - object storage checks once implemented
- run migrations:
  - `uv run python -m alembic upgrade head`
- create required local runtime directories only when still needed:
  - `logs`
  - local fallback paths
- seed sample files into MinIO when the sample download feature lands

Non-responsibilities:

- do not start long-running backend / worker / frontend servers
- do not wait forever on application ports
- do not own Ctrl+C cleanup of application processes

### `start-project.sh` / `start-project.bat`

Responsibilities:

- locate repo root
- check required runtime tools:
  - `uv`
  - Node.js
  - npm
  - curl where available
- verify infrastructure is already ready, or fail with a clear message telling
  the user to run `deploy-project`
- ensure application ports are free:
  - backend API: `8000`
  - frontend: `5173`
  - MinIO API: `9000`
  - MinIO console: `9001`
- create `logs`
- start long-running processes directly, without delegating to deleted scripts:
  - backend
  - worker
  - frontend
- wait for readiness:
  - backend health endpoint
  - worker queue listening log
  - frontend HTTP endpoint
- print access points and log paths
- clean backend / worker / frontend process trees on Ctrl+C
- optionally stop Docker infrastructure unless `MARKETMIND_KEEP_INFRA=1`

Non-responsibilities:

- do not run `uv sync` by default
- do not run frontend dependency install by default
- do not run migrations by default
- do not call `scripts/start-backend.*`, `scripts/start-worker.*`, or
  `scripts/start-frontend.*`

## Process Commands

Backend:

```text
uv run python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Worker:

```text
uv run python -m rq.cli worker "$ANALYSIS_QUEUE_NAME" --url "$REDIS_URL"
```

Frontend:

```text
cd frontend
npm run dev -- --host 0.0.0.0
```

Migrations:

```text
uv run python -m alembic upgrade head
```

Runtime checks:

```text
uv run python -m backend.core.runtime_checks check-retail-runtime --dry-run
uv run python -m backend.core.runtime_checks check-object-storage --sandbox
```

## Deletion Targets

After the new scripts are working, remove these old split process scripts:

```text
scripts/start-backend.sh
scripts/start-backend.bat
scripts/start-worker.sh
scripts/start-worker.bat
scripts/start-frontend.sh
scripts/start-frontend.bat
```

Before deletion, update all references in:

- `README.md`
- `docs/QUICKSTART.md`
- `docs/USAGE_GUIDE.md`
- `docs/development.md`
- `docs/commands.md`
- architecture/checklist docs if they describe current local commands

## Suggested User Workflow

First run, dependency changes, infra changes, migrations, or clean machine:

```text
./scripts/deploy-project.sh
./scripts/start-project.sh
```

Daily development when environment is already prepared:

```text
./scripts/start-project.sh
```

Windows equivalents:

```text
scripts\deploy-project.bat
scripts\start-project.bat
```

## Optional Flag

If a one-command mode is desired, add:

```text
./scripts/start-project.sh --deploy
```

This flag should call `deploy-project.sh` first and only start servers when the
deploy step succeeds.

Default `start-project` should stay fast and should not run dependency sync or
migrations on every invocation.

## Readiness Rules

`deploy-project` may claim success only when:

- Docker services are running and healthy
- `uv sync` succeeds
- frontend dependencies are present
- runtime checks pass or documented optional checks are skipped intentionally
- Alembic migration succeeds

`start-project` may claim success only when:

- backend health endpoint responds
- worker is listening on the expected queue
- frontend responds on `5173`
- no required process has exited early

## Cleanup Rules

`start-project.sh` should preserve the current good behavior:

- Ctrl+C exits with code `130`
- child process trees are stopped
- backend/worker/frontend logs are closed
- ports are checked after cleanup
- Docker infrastructure is stopped by default if this script started or owns it
- `MARKETMIND_KEEP_INFRA=1` leaves infrastructure running

For `start-project.bat`, process cleanup can be weaker than shell because
Windows batch has fewer portable process-tree tools, but the script should stop
opening orphaned windows where possible and should clearly document stop
instructions.

## Verification Strategy

Static:

```text
bash -n scripts/deploy-project.sh scripts/start-project.sh
```

Backend command safety:

```text
rg -n "uv run (alembic|uvicorn|rq worker)" scripts
```

Expected result: no matches in active scripts. Active backend commands should
use `uv run python -m ...`.

Reference cleanup:

```text
rg -n "start-backend|start-worker|start-frontend" scripts README.md docs
```

Expected result after deletion: no active-doc references except archive docs.

Runtime:

```text
./scripts/deploy-project.sh
./scripts/start-project.sh
```

Then verify:

- `http://127.0.0.1:8000/api/health/`
- `http://127.0.0.1:5173`
- worker log says it is listening on `retail-analysis`
- Ctrl+C frees ports `8000` and `5173`

Quality loop:

```text
make lint
make format
make lint
```

Run `make check` if implementation also touches Python code, runtime checks,
or frontend code beyond documentation.

## Rollback

Rollback before old scripts are deleted:

- restore calls to `start-backend.*`, `start-worker.*`, and `start-frontend.*`
  from `start-project.*`
- keep `deploy-project.*` unused

Rollback after old scripts are deleted:

- recover old script files from git
- revert README/docs entrypoint changes
- restore previous `start-project.*` behavior

Do not delete Docker volumes or runtime data during script rollback.
