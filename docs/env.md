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
| `OBJECT_STORAGE_BACKEND` | Object storage backend selection | `minio` (default, uses docker-compose MinIO); `local` for filesystem-only. |
| `OBJECT_STORAGE_BUCKET` | MinIO bucket name | `marketmind-dev` for local dev. |
| `OBJECT_STORAGE_ENDPOINT` | MinIO API endpoint | `http://localhost:9000` for local dev. |
| `OBJECT_STORAGE_PUBLIC_ENDPOINT` | Public-facing MinIO endpoint | Same as endpoint unless behind a proxy. |
| `OBJECT_STORAGE_ACCESS_KEY` | MinIO access key | `marketmind` for local dev. |
| `OBJECT_STORAGE_SECRET_KEY` | MinIO secret key | `marketmind_dev_password` for local dev. |
| `OBJECT_STORAGE_REGION` | S3 region | `us-east-1` (MinIO ignores this). |
| `OBJECT_STORAGE_SECURE` | Use HTTPS for MinIO | `false` for local dev. |
| `OBJECT_STORAGE_PRESIGNED_URL_TTL_SECONDS` | Presigned URL TTL | `900` (15 minutes). |
| `OBJECT_STORAGE_FORCE_PATH_STYLE` | Force path-style URLs | `true` for MinIO compatibility. |

Large CSV files, charts, reports, model artifacts, and Data Processing raw/normalized datasets/sidecars are stored through the object storage provider. When `OBJECT_STORAGE_BACKEND=minio`, bytes live in MinIO and Postgres keeps metadata only. When `OBJECT_STORAGE_BACKEND=local`, bytes remain on the filesystem under `data/projects/...`.

Do not store blob payloads directly in PostgreSQL.

## Frontend

Frontend source reads Vite variables through `frontend/src/api/client.ts`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Axios base URL. Empty string keeps Vite proxy behavior. | empty |
| `VITE_API_TIMEOUT` | Axios timeout in milliseconds. | `30000` |

Local development can rely on `frontend/vite.config.ts` proxying `/api` and `/outputs` to `http://localhost:8000`. Deployed environments should set `VITE_API_BASE_URL` explicitly when the frontend and API do not share an origin.
