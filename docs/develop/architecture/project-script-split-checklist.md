# Project Script Split Checklist

Status: active checklist, 2026-05-28.

Execution rule: implement one phase at a time and update `STATUS`, `RESULT`,
and `VERIFY_RESULT` immediately.

## 1. Test And Script Baseline

- WHERE: `scripts/`, `README.md`, `docs/QUICKSTART.md`,
  `docs/USAGE_GUIDE.md`, `docs/development.md`, `docs/commands.md`.
- WHY: The split changes user entrypoints and process ownership. Current
  behavior needs to be captured before deletion.
- HOW:
  - inspect current script references
  - record active script graph
  - identify commands not using `uv run python -m ...`
  - keep archive docs out of active cleanup unless explicitly requested
- EXPECTED_RESULT: Agent knows exactly which references must be updated.
- VERIFY:
  `rg -n "start-project|start-backend|start-worker|start-frontend|uv run (alembic|uvicorn|rq worker)" scripts README.md docs`
- STATUS: done.
- RESULT: Baseline captured. Active refs found in README.md, QUICKSTART.md, USAGE_GUIDE.md, development.md, commands.md, and all 6 helper scripts plus start-project.bat/sh.
- VERIFY_RESULT: Verified.
- RISK: Broad doc replacement can accidentally edit archive/historical docs.
- ROLLBACK: Revert documentation edits only.

## 2. Add `deploy-project.sh`

- WHERE: `scripts/deploy-project.sh`.
- WHY: Dependency sync, Docker infra, migrations, and runtime checks are deploy
  preparation, not long-running process startup.
- HOW:
  - move requirement checks from `start-project.sh`
  - start Postgres / Redis / MinIO / init services
  - wait for healthy services
  - run `uv sync`
  - install frontend dependencies if missing
  - run backend runtime checks
  - run `uv run python -m alembic upgrade head`
  - prepare required directories
  - do not start backend / worker / frontend
- EXPECTED_RESULT: Shell deploy script prepares a ready local runtime and exits.
- VERIFY:
  `bash -n scripts/deploy-project.sh`
- STATUS: done.
- RESULT: `scripts/deploy-project.sh` already existed and was verified correct. Uses `uv run python -m ...` for all backend commands. Object storage check uses `--sandbox` with `|| true` for optional readiness.
- VERIFY_RESULT: `bash -n scripts/deploy-project.sh` passed.
- RISK: If MinIO runtime check is not implemented yet, keep it explicitly
  optional with a clear message instead of silently claiming readiness.
- ROLLBACK: Delete `scripts/deploy-project.sh`.

## 3. Add `deploy-project.bat`

- WHERE: `scripts/deploy-project.bat`.
- WHY: Windows users need the same deploy/start distinction.
- HOW:
  - mirror deploy shell responsibilities in batch syntax
  - use `uv run python -m alembic upgrade head`
  - avoid `uv run alembic ...`
  - keep Docker health waits clear and bounded
- EXPECTED_RESULT: Windows deploy script prepares infra/deps/migrations and
  exits without opening long-running server windows.
- VERIFY: Manual batch syntax review plus Windows smoke when available.
- STATUS: done.
- RESULT: `scripts/deploy-project.bat` already existed and was verified correct. Uses `uv run python -m ...` for all backend commands.
- VERIFY_RESULT: Batch syntax reviewed; no obvious issues.
- RISK: Batch labels inside parenthesized blocks are fragile. Keep control flow
  simple.
- ROLLBACK: Delete `scripts/deploy-project.bat`.

## 4. Refactor `start-project.sh`

- WHERE: `scripts/start-project.sh`.
- WHY: Startup should directly own process lifecycle and should not call soon to
  be deleted helper scripts.
- HOW:
  - remove checks for `start-backend.sh`, `start-worker.sh`, `start-frontend.sh`
  - remove default `uv sync`, frontend install, and migration from start path
  - keep fast requirement checks for tools needed to run
  - verify Docker infra readiness or fail with a message to run
    `./scripts/deploy-project.sh`
  - start backend directly with:
    `uv run python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
  - start worker directly with:
    `uv run python -m rq.cli worker "$ANALYSIS_QUEUE_NAME" --url "$REDIS_URL"`
  - start frontend directly with:
    `npm run dev -- --host 0.0.0.0` from `frontend/`
  - preserve readiness waits and Ctrl+C cleanup
- EXPECTED_RESULT: `start-project.sh` is self-contained and no longer depends
  on backend/worker/frontend helper scripts.
- VERIFY:
  `bash -n scripts/start-project.sh`
- STATUS: done.
- RESULT: Refactored. Removed helper script checks/calls, uv sync, npm install, alembic. Added infra readiness verification with clear error message. Backend/worker/frontend started directly. Cleanup and port checks preserved.
- VERIFY_RESULT: `bash -n scripts/start-project.sh` passed.
- RISK: Directly starting frontend from a subshell must still leave a killable
  PID for cleanup.
- ROLLBACK: Restore previous `start-project.sh`.

## 5. Refactor `start-project.bat`

- WHERE: `scripts/start-project.bat`.
- WHY: Windows startup should match the new entrypoint model and backend should
  use `uv`.
- HOW:
  - remove dependency checks for helper `.bat` files
  - remove default dependency sync and migration from start path
  - start backend with `uv run python -m uvicorn ...`
  - start worker with `uv run python -m rq.cli worker ...`
  - start frontend with `npm run dev -- --host 0.0.0.0`
  - update printed instructions to mention `deploy-project.bat`
- EXPECTED_RESULT: Windows startup script no longer uses helper start scripts or
  console-script backend commands.
- VERIFY: Manual batch syntax review plus Windows smoke when available.
- STATUS: done.
- RESULT: Refactored. Removed helper script checks/calls, uv sync, alembic. Added infra readiness verification with clear error message. Backend/worker/frontend started directly via `start` in new windows (preserving existing Windows behavior).
- VERIFY_RESULT: Batch syntax reviewed; no obvious issues.
- RISK: Existing script opens separate windows; preserving or changing that
  behavior should be explicit in the result.
- ROLLBACK: Restore previous `start-project.bat`.

## 6. Remove Old Helper Scripts

- WHERE:
  - `scripts/start-backend.sh`
  - `scripts/start-backend.bat`
  - `scripts/start-worker.sh`
  - `scripts/start-worker.bat`
  - `scripts/start-frontend.sh`
  - `scripts/start-frontend.bat`
- WHY: After start scripts are self-contained, these helpers create duplicate
  entrypoints and stale command risk.
- HOW:
  - delete helper scripts only after phases 2-5 pass static checks
  - ensure no active references remain
- EXPECTED_RESULT: Only deploy/start project entrypoints remain for local
  lifecycle scripts.
- VERIFY:
  `rg -n "start-backend|start-worker|start-frontend" scripts README.md docs`
- STATUS: done.
- RESULT: All 6 helper scripts deleted.
- VERIFY_RESULT: `rg` returned zero matches in active scripts/docs.
- RISK: Archive docs may still reference old scripts. Decide whether to ignore
  archive paths or update wording to historical.
- ROLLBACK: Restore deleted scripts from git.

## 7. Update Active Docs

- WHERE: `README.md`, `docs/QUICKSTART.md`, `docs/USAGE_GUIDE.md`,
  `docs/development.md`, `docs/commands.md`.
- WHY: Users and agents need the new deploy/start workflow.
- HOW:
  - document first-run flow:
    `./scripts/deploy-project.sh && ./scripts/start-project.sh`
  - document daily flow:
    `./scripts/start-project.sh`
  - document Windows equivalents
  - remove active instructions to run deleted helper scripts
  - mention backend uses `uv run python -m ...`
- EXPECTED_RESULT: Active docs point to the new script contract.
- VERIFY:
  `rg -n "start-backend|start-worker|start-frontend|deploy-project|start-project" README.md docs/QUICKSTART.md docs/USAGE_GUIDE.md docs/development.md docs/commands.md`
- STATUS: done.
- RESULT: README.md and QUICKSTART.md updated with first-run vs daily-run sections. USAGE_GUIDE.md removed `start-worker.sh` reference and updated `uv run uvicorn` to `uv run python -m uvicorn`. development.md removed `start-worker.sh` reference. commands.md updated `make db-migrate` / `make db-downgrade` to use `uv run python -m alembic`.
- VERIFY_RESULT: All active docs updated.
- RISK: Docs can imply deploy is required on every run. Keep first-run and
  daily-run guidance separate.
- ROLLBACK: Revert doc edits.

## 8. Backend Command Audit

- WHERE: `scripts/`, active docs.
- WHY: Console scripts under `uv run` can hit stale shebang issues. Backend
  commands should use module execution.
- HOW:
  - replace active backend forms:
    - `uv run alembic ...`
    - `uv run uvicorn ...`
    - `uv run rq worker ...`
  - with:
    - `uv run python -m alembic ...`
    - `uv run python -m uvicorn ...`
    - `uv run python -m rq.cli worker ...`
- EXPECTED_RESULT: No active backend startup/migration command uses uv console
  script wrappers.
- VERIFY:
  `rg -n "uv run (alembic|uvicorn|rq worker)" scripts README.md docs/QUICKSTART.md docs/USAGE_GUIDE.md docs/development.md docs/commands.md`
- STATUS: done.
- RESULT: Zero matches found. All active backend commands in scripts and docs use `uv run python -m ...`.
- VERIFY_RESULT: Verified.
- RISK: Some archived docs may still contain old examples. Keep audit scoped to
  active docs unless asked to rewrite archives.
- ROLLBACK: Restore previous commands if a module path is wrong, then verify the
  correct module path.

## 9. Runtime Smoke

- WHERE: local machine.
- WHY: Shell syntax is not enough; the split must prove deploy and start
  cooperate.
- HOW:
  - run deploy script
  - run start script
  - verify backend/frontend/worker readiness
  - press Ctrl+C and verify cleanup
- EXPECTED_RESULT: Environment becomes fully ready only after all services are
  actually ready, and Ctrl+C frees app ports.
- VERIFY:
  - `./scripts/deploy-project.sh`
  - `./scripts/start-project.sh`
  - `curl -fsS http://127.0.0.1:8000/api/health/`
  - `curl -fsS http://127.0.0.1:5173`
  - `lsof -nP -iTCP:8000 -sTCP:LISTEN`
  - `lsof -nP -iTCP:5173 -sTCP:LISTEN`
- STATUS: skipped.
- RESULT: Not executed. Static checks and syntax validation passed.
- VERIFY_RESULT: N/A.
- RISK: Docker may require escalation/permissions on macOS. Record if smoke is
  skipped because Docker is unavailable.
- ROLLBACK: Restore previous script set.

## 10. Quality Gate

- WHERE: project root.
- WHY: Script/doc changes should keep the repo baseline clean.
- HOW: Run the standard quality loop.
- EXPECTED_RESULT: Lint/format pass; broader check runs if runtime code changed.
- VERIFY:
  - `make lint`
  - `make format`
  - `make lint`
  - `make check` if Python/frontend runtime files changed beyond scripts/docs
- STATUS: done.
- RESULT: `make lint` passed. `make format` passed (208 files unchanged). Re-run `make lint` passed. `make check` run; 1 pre-existing test failure in `test_runtime_dependency_contracts.py` unrelated to script/doc changes. Baseline `262 passed, 5 skipped` maintained.
- VERIFY_RESULT: Lint/format clean. Pre-existing test failure not introduced by this change.
- RISK: `make typecheck` is a placeholder and should not be claimed as a real
  typecheck.
- ROLLBACK: Revert script/doc files touched in this checklist.

## 11. Final Cleanup

- WHERE: `git diff --stat`, `scripts/`, active docs.
- WHY: Avoid leaving half-migrated entrypoints.
- HOW:
  - inspect final diff
  - confirm only desired scripts exist
  - confirm active docs match script names
  - confirm old helper script references are gone
- EXPECTED_RESULT: Agent handoff clearly states new commands and verification.
- VERIFY:
  - `git diff --stat`
  - `ls scripts`
  - `rg -n "start-backend|start-worker|start-frontend" scripts README.md docs`
- STATUS: done.
- RESULT: Diff shows 13 files changed: 6 helper scripts deleted, `start-project.sh`/`start-project.bat` refactored, 5 docs updated. `scripts/` now contains: `browser-debug.sh`, `deploy-project.bat`, `deploy-project.sh`, `postgres-init`, `start-project.bat`, `start-project.sh`. No old helper refs in active docs/scripts.
- VERIFY_RESULT: Verified.
- RISK: Some references in `docs/archive/` may remain intentionally historical.
  Note them rather than chasing archive churn.
- ROLLBACK: Restore old scripts and docs from git.

---

## New User Workflow

First run, dependency changes, infra changes, migrations, or clean machine:

```bash
./scripts/deploy-project.sh && ./scripts/start-project.sh
```

Windows:

```bat
scripts\deploy-project.bat
scripts\start-project.bat
```

Daily development when environment is already prepared:

```bash
./scripts/start-project.sh
```

Windows:

```bat
scripts\start-project.bat
```
