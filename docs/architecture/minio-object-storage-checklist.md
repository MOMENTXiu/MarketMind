# MinIO Object Storage Construction Checklist

Status: active checklist, 2026-05-28.

Execution rule: complete one phase at a time and record verification
immediately. Do not implement code before this checklist and the design doc are
reviewed for scope.

## 1. Test Anchors

- WHERE: `tests/providers/`, `tests/api/`, `tests/core/`,
  `tests/test_architecture_imports.py`.
- WHY: Moving blobs from local filesystem to MinIO changes durable side effects
  while public refs and API URLs should remain stable.
- HOW: Add or extend tests for:
  - object storage provider contract using a fake adapter
  - raw upload ref uses UUID-backed storage key and preserves original filename
  - sample listing/download API returns URL data and streams sample content
  - artifact payload reads remain path-free
  - runtime checks cover object storage readiness
- EXPECTED_RESULT: Tests define behavior before adapters are swapped.
- VERIFY:
  `uv run pytest tests/providers tests/api/test_data_processing_analysis_contracts.py tests/core/test_runtime_checks.py tests/test_architecture_imports.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Live MinIO tests can be flaky if Docker is unavailable. Keep fake
  contract tests as the default and gate live tests.
- ROLLBACK: Remove the new tests if scope is cancelled before implementation.

## 2. Provider Interface

- WHERE: `backend/providers/object_storage_provider.py`,
  `backend/providers/dtos.py`, `backend/providers/container.py`.
- WHY: Business and domain-specific providers must not depend on MinIO/S3 SDKs.
- HOW: Add a narrow object storage Provider Interface and DTOs for stored object
  refs, object payload reads, metadata/stat, and optional presigned download
  data. Add a Providers Container field only if the adapter composition needs
  shared object storage access; otherwise keep it internal to storage-specific
  adapters.
- EXPECTED_RESULT: Storage capability is expressed without vendor types.
- VERIFY:
  `uv run python -m py_compile backend/providers/object_storage_provider.py backend/providers/dtos.py backend/providers/container.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: A generic provider can become too broad. Keep only methods needed by
  raw upload, sample download, dataset/artifact/model storage, and runtime
  checks.
- ROLLBACK: Delete the new provider and DTO additions.

## 3. External Adapter

- WHERE: `backend/infrastructure/adapters/minio_object_storage_adapter.py`,
  `backend/infrastructure/adapters/minio_regularized_dataset_adapter.py`,
  `backend/infrastructure/adapters/minio_analysis_artifact_adapter.py`,
  `backend/infrastructure/adapters/minio_analysis_model_store_adapter.py`,
  `tests/infrastructure/adapters/`.
- WHY: MinIO SDK access belongs in Infrastructure and must convert external
  errors into internal errors.
- HOW:
  - implement S3-compatible MinIO object operations
  - implement domain adapters for regularized datasets, artifacts, and true
    model artifacts
  - preserve public API-facing refs
  - generate UUID-backed keys for raw uploads
  - preserve original filename/content type/size/checksum in metadata
  - keep local adapters available as fallback
- EXPECTED_RESULT: MinIO-backed adapters satisfy existing provider contracts.
- VERIFY:
  `uv run pytest tests/providers/test_regularized_dataset_adapter.py tests/providers/test_analysis_v2_adapters.py tests/infrastructure/adapters`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Pickle model payloads need binary-safe read/write and may be large.
  Avoid loading objects into memory for large downloads where streaming is
  required.
- ROLLBACK: Switch Provider Factory to local adapters and leave MinIO adapters
  unused.

## 4. Ability Atom

- WHERE: likely none for existing analysis flows; optional
  `backend/abilities/samples/`.
- WHY: Storing bytes is infrastructure, not an Ability Atom. Sample catalog
  shaping may need a small pure ability only if it contains business filtering
  or validation.
- HOW: Do not create an Ability Atom unless sample metadata needs pure business
  transformation.
- EXPECTED_RESULT: No unnecessary ability layer is added.
- VERIFY: `rg -n "minio|boto3|s3" backend/abilities backend/business`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Putting storage SDK logic into abilities would violate architecture
  rules.
- ROLLBACK: Move any accidental SDK usage into Infrastructure.

## 5. Business Pipeline

- WHERE: `backend/business/pipelines/dataset_regularization_pipeline.py`,
  possible new `backend/business/pipelines/sample_file_pipeline.py`.
- WHY: Raw upload persistence and sample catalog/download are business actions
  that must remain Provider-driven.
- HOW:
  - keep regularization pipeline behavior unchanged while underlying provider
    writes to MinIO
  - add a sample file pipeline only if sample listing needs metadata assembly
    beyond simple provider lookup
  - do not pass MinIO bucket/key from API into business code
- EXPECTED_RESULT: Business pipelines depend only on Providers Container and
  return structured refs/URLs.
- VERIFY:
  `uv run pytest tests/business/test_data_processing_analysis_flow.py tests/business/test_data_processing_pipelines.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Sample download can be mistaken as static frontend asset serving. Keep
  it behind backend API so source can be MinIO.
- ROLLBACK: Remove sample pipeline and expose sample metadata through a thinner
  flow/controller path if no orchestration is needed.

## 6. Business Flow

- WHERE: `backend/business/flows/data_processing_analysis_flow.py`.
- WHY: Data-processing already has a long-running job lifecycle; MinIO must fit
  into existing state transitions without changing them.
- HOW:
  - preserve upload -> regularize -> run status semantics
  - ensure raw upload object ref is appended to `output_refs`
  - ensure job reload can resolve MinIO-backed normalized datasets and sidecars
  - do not store job state blobs in MinIO as a new pattern
- EXPECTED_RESULT: Flow behavior remains equivalent; only storage backend
  changes.
- VERIFY:
  `uv run pytest tests/business/test_data_processing_analysis_flow.py tests/api/test_data_processing_analysis_contracts.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Current job state uses model store. Do not broaden that coupling during
  MinIO migration.
- ROLLBACK: Revert provider wiring to local regularized dataset adapter.

## 7. API Controller

- WHERE: `backend/api/analysis.py`, possible `backend/api/samples.py`,
  router registration in `backend/main.py`.
- WHY: Frontend needs sample file URL data and existing dataset/artifact URLs
  should stream MinIO-backed content through the backend.
- HOW:
  - keep existing analysis dataset/artifact/sidecar URLs stable
  - add `GET /api/samples`
  - add `GET /api/samples/{sample_id}`
  - add `GET /api/samples/{sample_id}/download`
  - return sample metadata with `download_url`
  - support backend-proxy download first; presigned URL can be a later mode
- EXPECTED_RESULT: Frontend can render sample download links without knowing
  MinIO keys.
- VERIFY:
  `uv run pytest tests/api/test_data_processing_analysis_contracts.py tests/api/test_sample_files_contracts.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Do not expose raw bucket/key as a user-editable parameter.
- ROLLBACK: Remove sample routes; existing analysis routes stay unchanged.

## 8. Docker / Settings / Startup

- WHERE: `docker-compose.dev.yml`, `.env.example`, `backend/core/config.py`,
  `backend/infrastructure/factories/provider_factory.py`,
  `scripts/start-project.sh`.
- WHY: User expects the dev startup script to mean all required runtime
  infrastructure is fully ready.
- HOW:
  - add MinIO service and persistent volume
  - add bucket/sample bootstrap step or `minio-init` service
  - add object storage Settings
  - make Provider Factory select MinIO adapters when
    `OBJECT_STORAGE_BACKEND=minio`
  - make startup wait for MinIO health and bucket readiness
  - keep `MARKETMIND_KEEP_INFRA=1` behavior if implemented
- EXPECTED_RESULT: `./scripts/start-project.sh` starts Postgres, Redis, MinIO,
  backend, worker, and frontend only after all readiness gates pass.
- VERIFY:
  `docker compose -f docker-compose.dev.yml ps`
  `uv run python -m backend.core.runtime_checks check-minio`
  `./scripts/start-project.sh`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: MinIO credentials in `.env.example` must be dev-only and not treated as
  production secrets.
- ROLLBACK: Set `OBJECT_STORAGE_BACKEND=local` and remove MinIO from startup
  readiness gate.

## 9. Architecture Lint / Runtime Check / Full Verification

- WHERE: `tests/test_architecture_imports.py`,
  `backend/core/runtime_checks.py`, project root.
- WHY: Enforce that MinIO/S3 SDK usage stays in Infrastructure and runtime
  readiness detects missing object storage.
- HOW:
  - block MinIO/S3 SDK imports from API, business, ability, and provider layers
  - add runtime checks for object storage config, bucket write/read/delete, and
    sample presence
  - run affected and full quality gates
- EXPECTED_RESULT: Architecture boundaries and runtime readiness are machine
  checked.
- VERIFY:
  - `make lint`
  - `make format`
  - `make lint`
  - `uv run pytest tests/test_architecture_imports.py tests/core/test_runtime_checks.py`
  - `make check`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Live MinIO checks should fail loudly in dev startup, but CI may need a
  sandbox/fake profile.
- ROLLBACK: Keep runtime check command but skip live check unless MinIO backend
  is enabled.

## 10. Cleanup And Handoff

- WHERE: docs, old local storage usage, generated local files.
- WHY: Avoid two competing runtime storage stories.
- HOW:
  - document local adapter as fallback/test-only
  - avoid new writes to `data/projects/...` when MinIO backend is enabled
  - remove dead imports and stale storage wording
  - update frontend docs if sample download API is added
- EXPECTED_RESULT: Future agents know MinIO is the unified runtime blob store.
- VERIFY:
  `rg -n "Local.*Adapter|data/projects|OBJECT_STORAGE_BACKEND|MinIO|miniio" docs backend tests`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Existing local data may remain on disk from prior runs. Do not delete
  it automatically; treat cleanup as explicit operator action.
- ROLLBACK: Revert docs and provider wiring to the previous local-only story.
