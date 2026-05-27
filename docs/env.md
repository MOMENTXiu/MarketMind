# Environment

Use `.env.example` as the committed template for local configuration.

Rules:

- Commit `.env.example` and `.env.template` when they contain no secrets.
- Never commit `.env`, `.env.*`, private keys, credentials, or service account files.
- Add new environment variables to `.env.example` with blank or safe development values.

Current stacks: node, python, vue3-vite

The root `.env.example` mirrors backend `Settings` fields in `backend/core/config.py`.

## Backend

| Variable | Purpose | Default/dev note |
| --- | --- | --- |
| `APP_NAME`, `APP_VERSION`, `DEBUG`, `API_PREFIX` | FastAPI app metadata and API prefix | Safe local values are committed in `.env.example`. |
| `CORS_ORIGINS` | Allowed browser origins | Includes Vite dev ports. |
| `OUTPUT_DIR`, `CHARTS_DIR`, `REPORTS_DIR` | Static/generated output directories | Runtime generated assets stay on filesystem. |
| `DATABASE_URL` | PostgreSQL development database | Retail V2 state is PostgreSQL-backed; used by DB infrastructure and migrations. |
| `TEST_DATABASE_URL` | Isolated PostgreSQL test database | Required for live DB adapter and Alembic roundtrip tests. |
| `REDIS_URL`, `REDIS_ENABLED`, `TASK_QUEUE_BACKEND` | Redis/queue configuration | Redis/RQ worker is the default async backend; `TASK_QUEUE_BACKEND=redis`, `REDIS_ENABLED=true`. |

Large CSV files, charts, reports, and model artifacts should remain as filesystem/object references. Do not store them directly in PostgreSQL.

## Frontend

Frontend source reads Vite variables through `frontend/src/api/client.ts`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Axios base URL. Empty string keeps Vite proxy behavior. | empty |
| `VITE_API_TIMEOUT` | Axios timeout in milliseconds. | `30000` |

Local development can rely on `frontend/vite.config.ts` proxying `/api` and `/outputs` to `http://localhost:8000`. Deployed environments should set `VITE_API_BASE_URL` explicitly when the frontend and API do not share an origin.
