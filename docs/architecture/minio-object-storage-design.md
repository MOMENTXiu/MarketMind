# MinIO Object Storage Architecture Design

Status: active design, 2026-05-28.

## Goal

Use MinIO as the unified S3-compatible object storage runtime for MarketMind
development and deployable environments. Docker should start MinIO together
with Postgres and Redis.

The immediate product requirements are:

1. When a user uploads a raw file, rename the stored object to a UUID-based key
   and associate it with the project/job metadata.
2. The frontend needs a sample file download entry. The source sample file
   should live in MinIO, and the frontend should receive URL data for download.

This migration should also plan all current runtime outputs that should stop
living as plain local files.

## Current Call Chain

### Data Processing Upload And Analysis

```text
API Controller
  -> DataProcessingAnalysisFlow
  -> DatasetRegularizationPipeline
  -> RegularizedDatasetProvider
  -> LocalRegularizedDatasetAdapter
  -> data/projects/{project_id}/analysis/regularization/{job_id}/...
```

Current stored files:

- raw upload bytes
- normalized dataset CSV
- schema mapping sidecars
- field profile / quality / capability / manifest / preview sidecars

### Universal Analysis Artifacts

```text
Business Pipeline
  -> AnalysisArtifactProvider
  -> LocalAnalysisArtifactAdapter
  -> data/projects/{project_id}/analysis/artifacts/{type}/{name}
```

Current stored files:

- universal JSON artifacts
- Retail CSV table artifacts
- Markdown reports
- figure bytes when generated

### Analysis Models

```text
Business Pipeline / Flow
  -> AnalysisModelStoreProvider
  -> LocalAnalysisModelStoreAdapter
  -> data/projects/{project_id}/analysis/models/{model_type}/{version}.pkl
```

Current stored files:

- segmentation models
- Retail recommendation / signal models
- data-processing job state currently saved through `AnalysisModelStoreProvider`

Note: `AnalysisModelStoreProvider` is for true model artifacts only by project
convention. The data-processing job state currently uses this provider as a
state store. This should be treated carefully during migration and not expanded.

### Metadata

Postgres already has metadata tables with object-storage-ready columns:

- `uploaded_files.storage_key`
- `uploaded_files.storage_uri`
- `datasets.storage_key`
- `datasets.storage_uri`
- `artifacts.storage_key`
- `artifacts.storage_uri`

The target is to keep Postgres as metadata/state storage and MinIO as blob
storage.

## Direct Storage Access Points

| Current file | Storage access | Target |
| --- | --- | --- |
| `backend/infrastructure/adapters/local_regularized_dataset_adapter.py` | Writes raw uploads, normalized CSV, sidecar JSON to local disk. | Replace with MinIO-backed adapter implementing `RegularizedDatasetProvider`. |
| `backend/infrastructure/adapters/local_analysis_artifact_adapter.py` | Writes table/figure/Markdown/JSON artifacts to local disk. | Replace with MinIO-backed adapter implementing `AnalysisArtifactProvider`. |
| `backend/infrastructure/adapters/local_analysis_model_store_adapter.py` | Pickles model payloads to local disk. | Replace true model payload persistence with MinIO-backed adapter. |
| `backend/infrastructure/adapters/local_project_file_storage_adapter.py` | Legacy project dataset/customers workspace files. | Defer unless still used by active frontend/API paths; do not grow this path. |
| `backend/infrastructure/factories/provider_factory.py` | Hard-wires local storage adapters. | Choose MinIO adapters from Settings and assemble them in Providers Container. |
| `backend/core/runtime_checks.py` | Checks local storage/artifacts. | Add MinIO connectivity and object read/write runtime checks. |
| `docker-compose.dev.yml` | Starts Postgres and Redis only. | Add MinIO service and bucket bootstrap service. |
| `.env.example` | No object storage settings. | Add MinIO/S3 settings. |

## Target Architecture

Keep the existing high-level business call chain:

```text
API Controller
  -> Business Flow / Business Pipeline
  -> Provider Interface
  -> MinIO External Adapter
  -> MinIO
```

Business code must not import MinIO, boto3, S3 clients, or read storage env
directly.

## Provider Boundary

### Preferred Shape

Add a narrow object storage provider that represents generic blob operations:

```text
backend/providers/object_storage_provider.py
```

Business-specific providers can either:

- delegate internally to this provider from their MinIO adapters; or
- be implemented directly by MinIO-specific adapters.

The safer migration is:

```text
RegularizedDatasetProvider
  -> MinioRegularizedDatasetAdapter
     -> ObjectStorageProvider-compatible internal client

AnalysisArtifactProvider
  -> MinioAnalysisArtifactAdapter
     -> ObjectStorageProvider-compatible internal client

AnalysisModelStoreProvider
  -> MinioAnalysisModelStoreAdapter
     -> ObjectStorageProvider-compatible internal client
```

This avoids changing business-layer provider contracts too early.

### Object DTOs

Provider DTOs should expose only internal-safe metadata:

- `storage_key`
- `storage_uri`
- `content_type`
- `size_bytes`
- `checksum`
- `etag` if useful
- `metadata`
- API-facing `url`

They must not expose raw MinIO clients, buckets as mutable handles, local paths,
or SDK response objects.

## Object Key Policy

Use stable, project-scoped, UUID-based object keys. Do not use original
filenames as stored object names.

Recommended key layout:

```text
projects/{project_id}/uploads/{upload_uuid}/{original_stem}.{ext}
projects/{project_id}/analysis/regularization/{job_id}/normalized/{dataset_uuid}.csv
projects/{project_id}/analysis/regularization/{job_id}/sidecars/{sidecar_type}.json
projects/{project_id}/analysis/artifacts/{artifact_type}/{artifact_uuid}-{name}
projects/{project_id}/analysis/models/{model_type}/{version}.pkl
samples/{sample_id}/{filename}
```

Raw upload requirement:

- The stored object key must include a UUID.
- The original filename is metadata only.
- Public refs should keep user-friendly `name`, but `storage_key` should be
  UUID-backed.
- `metadata.filename` should keep the original uploaded filename.

Example:

```text
storage_key:
projects/2250.../uploads/018f4c5a-.../order_1.csv

metadata:
{
  "original_filename": "order_1.csv",
  "stored_filename": "018f4c5a-....csv",
  "content_type": "text/csv"
}
```

## URL Strategy

### Phase 1: Backend Proxy URLs

Use existing API URLs as the frontend-facing contract:

```text
/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}
/api/analysis/jobs/{job_id}/sidecars/{sidecar_id}?project_id={project_id}
/api/analysis/projects/{project_id}/artifacts/{artifact_id}
/api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload
/api/samples/{sample_id}/download
```

The backend reads from MinIO and streams payloads. This keeps auth, path safety,
and CORS simple.

### Phase 2: Presigned URLs

Add presigned URL generation only when large file downloads or direct browser
download performance becomes important.

If presigned URLs are added:

- TTL must be short.
- Content disposition should preserve original filename.
- Bucket/key must never be accepted directly from the frontend.
- API response should include `expires_at`.

## Sample File Download

Add a sample file catalog:

```text
GET /api/samples
GET /api/samples/{sample_id}
GET /api/samples/{sample_id}/download
```

Recommended source of truth:

- sample file bytes live in MinIO under `samples/{sample_id}/{filename}`
- sample metadata lives in a small versioned config or Postgres table
- startup/runtime check can seed required sample objects if missing

Frontend should call `GET /api/samples`, render a sample download action, and
use the provided `download_url`. The UI should not hard-code object keys.

Initial sample candidate:

- `order_1.csv` or an anonymized equivalent of the current E2E data
- content type: `text/csv`
- description: data-processing sample order dataset

## What Should Move To MinIO

| Category | Move to MinIO? | Reason |
| --- | --- | --- |
| Raw user uploads | Yes, first priority | User-provided source files need durable object storage and download/audit support. |
| Sample files | Yes, first priority | Frontend needs stable download URLs; samples should not depend on local filesystem. |
| Normalized datasets | Yes | Workers and API readers need shared durable access. |
| Regularization sidecars | Yes | They are project/job artifacts and should be addressable through refs. |
| Universal JSON artifacts | Yes | Frontend dashboard reads them as payloads. |
| Retail/data-processing CSV table artifacts | Yes | They are downloadable/exportable analysis outputs. |
| Markdown reports | Yes | Reports are downloadable artifacts. |
| Figure/image artifacts | Yes | Future chart/report figures should be stored consistently. |
| True model artifacts | Yes | Pickle/model files are binary artifacts and should not require local shared disk. |
| Data-processing job state | Not as a future target | It currently uses model store, but long-term state belongs in Postgres/state provider, not object storage. |
| Temporary intermediate frames | No by default | Keep in memory or temp files unless needed for replay/audit. |
| Logs/traces | No for this scope | Use logging/telemetry stack, not MinIO. |

## Docker Runtime

Add MinIO to `docker-compose.dev.yml`:

```text
minio:
  image: minio/minio
  command: server /data --console-address ":9001"
  ports: 9000, 9001
  volumes: marketmind_minio_data:/data
  healthcheck: minio health endpoint

minio-init:
  image: minio/mc
  depends_on: minio healthy
  create bucket and seed samples
```

Recommended bucket:

```text
marketmind-dev
```

The app should use one bucket per environment, not one bucket per project.
Project isolation belongs in the object key prefix.

## Settings

Add Settings fields:

```text
OBJECT_STORAGE_BACKEND=minio
OBJECT_STORAGE_BUCKET=marketmind-dev
OBJECT_STORAGE_ENDPOINT=http://localhost:9000
OBJECT_STORAGE_PUBLIC_ENDPOINT=http://localhost:9000
OBJECT_STORAGE_ACCESS_KEY=marketmind
OBJECT_STORAGE_SECRET_KEY=marketmind_dev_password
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_SECURE=false
OBJECT_STORAGE_PRESIGNED_URL_TTL_SECONDS=900
OBJECT_STORAGE_FORCE_PATH_STYLE=true
```

The exact SDK can be chosen during implementation. Prefer an S3-compatible
client interface so MinIO remains replaceable.

## Error Strategy

External adapters must catch SDK/storage exceptions and convert them to
internal errors:

- missing object -> `NotFoundError`
- invalid key / unsafe id -> `ValidationError`
- connectivity, timeout, permission, bucket missing -> `InfrastructureError`

Do not leak MinIO bucket/key internals in public error responses.

## Test Strategy

Minimum behavior protection:

- Provider contract tests for put/get/stat/delete/presign or proxy read.
- Adapter tests using fake object storage for unit speed.
- Optional live MinIO tests gated by env or Docker profile.
- API contract tests for raw upload refs, dataset download, sample listing, and
  sample download.
- Runtime checks for MinIO settings, bucket access, write/read/delete probe, and
  sample object presence.

Existing tests that assert path-free refs must continue to pass.

## Runtime Check Strategy

Add commands such as:

```text
uv run python -m backend.core.runtime_checks check-object-storage --sandbox
uv run python -m backend.core.runtime_checks check-minio
uv run python -m backend.core.runtime_checks check-sample-files
```

Runtime checks should verify:

- Settings load required object storage fields.
- Provider Factory assembles MinIO adapters when backend is `minio`.
- Bucket exists and is writable.
- A sandbox object can be written, read, and removed.
- Required sample files exist and have expected content type/size/checksum.

## Migration Strategy

The implementation should be incremental:

1. Add Docker/Settings/runtime checks without changing business behavior.
2. Add object storage provider and MinIO adapter with tests.
3. Move sample file download to MinIO.
4. Move raw upload storage to MinIO with UUID keys.
5. Move normalized datasets and sidecars.
6. Move analysis artifacts.
7. Move true model artifacts.
8. Decide and migrate data-processing job state away from model store if needed.

Each step must preserve public API URLs unless explicitly changed later.

## Rollback

Keep local adapters as a fallback profile during migration:

```text
OBJECT_STORAGE_BACKEND=local
```

Rollback steps:

- switch Provider Factory back to local adapters
- keep Postgres metadata untouched
- leave MinIO objects in place for audit
- do not delete buckets or volumes during rollback

If MinIO is unavailable, startup/runtime checks should fail loudly before the
app claims full readiness.
