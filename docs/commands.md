# Commands

Run commands from the repository root.

| Command | Behavior |
| --- | --- |
| `make setup` | Runs `uv sync`; `cd frontend && npm ci` |
| `make lint` | Runs backend lint via `uv run ruff check .` |
| `make format` | Runs backend formatting via `uv run ruff format .` |
| `make fix` | Runs backend Ruff fix and Ruff format |
| `make test` | Runs `uv run pytest` |
| `make typecheck` | No confirmed typecheck command; placeholder only. |
| `make build` | Runs `cd frontend && npm run build` |
| `make check` | Runs backend lint, backend format check, backend pytest, and frontend build |
| `make verify` | Runs `$(MAKE) check`; `$(MAKE) hooks` |
| `make hooks` | Runs `pre-commit run --all-files` |
| `make clean` | No confirmed clean command; placeholder only. |
| `make infra-up` | Starts PostgreSQL and Redis from `docker-compose.dev.yml` |
| `make infra-down` | Stops PostgreSQL and Redis without deleting named volumes |
| `make infra-reset` | Stops services, deletes named volumes, then starts services again |
| `make infra-logs` | Follows PostgreSQL and Redis logs |
| `make db-migrate` | Runs `uv run alembic upgrade head` |
| `make db-downgrade` | Runs `uv run alembic downgrade base` |
| `make db-revision` | Runs Alembic autogenerate; set `DB_REVISION_MESSAGE` |

Quality loop after code changes:

1. `make lint`
2. `make fix` when safe, otherwise make minimal manual fixes
3. `make lint`
4. `make format`
5. `make lint`
6. `make check` or `make verify` when commands are configured

Run `make hooks` before commit.

`make check` currently reports the backend pytest baseline as `262 passed, 5 skipped` when optional live DB URLs are not configured. Pytest warnings from pandas/numpy/pydantic are known and do not fail the gate.

Echo-only targets are placeholders. They are not evidence that lint, format, test, build, hooks, or CI passed.

Detected package managers:

- python: uv (selected by --python-manager uv)
- node: npm (selected by --node-manager npm)
- java: auto (not detected)
- swift: auto (not detected)

Detected package scripts:

- frontend: dev, build, preview
