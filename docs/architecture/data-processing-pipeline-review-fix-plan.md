# Data Processing Pipeline Review Fix Plan

> Created: 2026-05-26
> Scope: fix review findings in the implemented chain-native data-processing runtime.
> Target chain: raw upload -> regularization -> universal analysis -> outputs / charts / tables / summary.

## Review Conclusion

The new backend implementation is close to the intended architecture, but it is
not ready to commit as-is. The focused tests pass, but they do not exercise the
real local `regularized_dataset` adapter or the asynchronous execution path used
by production wiring.

Do not commit the current code until the fixes below are implemented and the
tests are expanded to cover real adapter behavior.

## Current Runtime Shape

```text
API Controller
  backend/api/analysis.py
    POST /api/analysis/jobs
    POST /api/analysis/jobs/{job_id}/raw-dataset
    POST /api/analysis/jobs/{job_id}/regularize
    POST /api/analysis/jobs/{job_id}/run
    GET  /api/analysis/jobs/{job_id}
    GET  /api/analysis/jobs/{job_id}/outputs

Business Flow
  backend/business/flows/data_processing_analysis_flow.py
    job state machine
    regularization stage
    universal analysis stages
    output ref aggregation

Business Pipelines
  backend/business/pipelines/dataset_regularization_pipeline.py
  backend/business/pipelines/universal_*_pipeline.py

Ability Atoms
  backend/abilities/regularization/*
  backend/abilities/universal_analysis/*

Provider Boundary
  backend/providers/regularized_dataset_provider.py
  backend/providers/container.py
  backend/providers/dtos.py

Infrastructure Adapter
  backend/infrastructure/adapters/local_regularized_dataset_adapter.py
```

The layering is directionally correct:

```text
API Controller -> Business Flow -> Business Pipeline -> Ability Atom
  -> Provider Interface -> Infrastructure Adapter
```

The defects are mostly contract and lifecycle issues at the API / Flow /
Adapter boundary.

## Findings To Fix

### P1: Output URLs Point To Missing API Routes

- WHERE:
  - `backend/infrastructure/adapters/local_regularized_dataset_adapter.py`
  - `backend/api/analysis.py`
- WHY:
  - `LocalRegularizedDatasetAdapter` returns refs with URLs like:
    - `/api/analysis/jobs/{job_id}/datasets/{ref_id}`
    - `/api/analysis/jobs/{job_id}/sidecars/{ref_id}`
  - `backend/api/analysis.py` does not implement these chain-native read
    routes.
  - The existing dataset read route is still the Retail V2 route:
    `/api/analysis/projects/{project_id}/datasets/{dataset_id}`.
- IMPACT:
  - API responses expose output refs that cannot be dereferenced.
  - Frontend cannot reliably fetch normalized datasets, sidecars, charts,
    tables, or summaries through the returned URLs.
- FIX:
  - Add chain-native read routes:
    - `GET /api/analysis/jobs/{job_id}/datasets/{dataset_id}?project_id=...`
    - `GET /api/analysis/jobs/{job_id}/sidecars/{sidecar_id}?project_id=...`
  - Keep route handlers thin:
    - validate query/path input;
    - call `DataProcessingAnalysisFlow`;
    - return `_success(...)` or mapped internal errors.
  - Add flow methods:
    - `get_dataset_ref(project_id, job_id, dataset_id)`
    - `get_sidecar_ref(project_id, job_id, sidecar_id)`
    - optionally `load_sidecar(project_id, job_id, sidecar_id)` if the API
      should return JSON payloads, not only refs.
  - Do not expose local filesystem paths.
  - Continue returning opaque refs, not absolute storage paths.

### P1: Run Can Start Before Regularization Is Complete

- WHERE:
  - `backend/business/flows/data_processing_analysis_flow.py`
- WHY:
  - `run_analysis()` sets job status to `processing` and schedules analysis
    without checking that `dataset_regularization` has completed.
  - If no normalized dataset exists, the background handler fails later in
    `_execute_analysis()`.
  - The caller receives a successful response for a job that was not runnable.
- IMPACT:
  - API status semantics are misleading.
  - UI may show a run as accepted even though it should be blocked.
  - Failures are delayed into background state mutation, making the user action
    harder to understand.
- FIX:
  - Add preflight validation inside `run_analysis()` before setting status:
    - job belongs to project;
    - regularization stage status is `completed`;
    - job status is not `needs_review`;
    - normalized dataset ref resolves to a `normalized_dataset` ref.
  - If regularization is missing, raise `ValidationError`.
  - If regularization needs review, raise `ValidationError` with a message that
    tells the caller to resolve/re-run regularization first.
  - Keep background execution for actual analysis stages only.

### P2: Opaque Ref Resolution Is Not Actually Opaque

- WHERE:
  - `backend/infrastructure/adapters/local_regularized_dataset_adapter.py`
  - `tests/providers/test_regularized_dataset_adapter.py`
- WHY:
  - `resolve_dataset_ref(project_id, job_id, ref_id)` ignores `ref_id`.
  - When `raw_upload` and `dataset.csv` both exist, it returns the first
    existing dataset, currently `raw_upload`.
  - `resolve_sidecar_ref(project_id, job_id, ref_id)` ignores `ref_id` and
    returns the first JSON sidecar.
  - `list_sidecars()` creates fresh random IDs on every call, so listed refs are
    not stable.
- IMPACT:
  - A caller can request one ref and receive another.
  - Returned URLs are not durable.
  - Tests can pass while real output retrieval is nondeterministic.
- FIX:
  - Make ref IDs deterministic and reversible for local storage:
    - `raw-upload`
    - `normalized-dataset`
    - `sidecar:{sidecar_type}`
  - Or persist a small manifest that maps generated UUID refs to files.
  - Prefer deterministic IDs for this local adapter because the underlying
    files are singletons per project/job/type.
  - Update:
    - `save_raw_upload()`
    - `save_normalized_dataset()`
    - `save_sidecar()`
    - `resolve_dataset_ref()`
    - `resolve_sidecar_ref()`
    - `list_sidecars()`
  - Reject unknown dataset IDs instead of falling back to the first file.
  - Reject unknown sidecar IDs instead of falling back to the first JSON file.

### P2: Tests Mask Production Wiring

- WHERE:
  - `tests/api/conftest.py`
  - `tests/fakes/providers.py`
  - `tests/api/test_data_processing_analysis_contracts.py`
  - `tests/business/test_data_processing_analysis_flow.py`
  - `tests/providers/test_regularized_dataset_adapter.py`
- WHY:
  - API tests use `FakeRegularizedDatasetProvider`, not
    `LocalRegularizedDatasetAdapter`.
  - API job scheduling fixture records jobs but does not execute the submitted
    handler.
  - Fake provider `resolve_dataset_ref()` and `resolve_sidecar_ref()` also
    return refs even when nothing exists.
- IMPACT:
  - Contract tests do not prove returned refs can be resolved.
  - Contract tests do not catch run-before-regularization behavior.
  - Adapter bugs can survive because fake semantics are looser than production.
- FIX:
  - Add at least one API contract test using `LocalRegularizedDatasetAdapter`.
  - Add a test job provider that executes the submitted handler synchronously.
  - Tighten `FakeRegularizedDatasetProvider`:
    - return `None` when requested refs are absent;
    - use deterministic IDs aligned with the real adapter.
  - Add tests for:
    - `POST /run` before upload -> 400/422 style error;
    - `POST /run` after upload but before regularize -> validation error;
    - `POST /run` when regularization is `needs_review` -> validation error;
    - `GET returned sidecar URL` returns the requested sidecar/ref;
    - `GET returned dataset URL` returns the requested dataset/ref.

## Target Behavior

### State Transitions

```text
create job
  -> queued

upload raw dataset
  -> queued
  -> output_refs includes raw-upload

regularize
  -> dataset_regularization: processing
  -> completed:
       job.status = queued
       output_refs includes normalized-dataset and sidecars
  -> needs_review:
       job.status = needs_review
       run is blocked until review resolution exists
  -> failed:
       job.status = failed

run analysis
  requires dataset_regularization completed
  -> processing
  -> completed / failed
```

### Ref Semantics

Opaque refs should be stable within one `{project_id, job_id}` namespace.

```text
dataset ref ids:
  raw-upload
  normalized-dataset

sidecar ref ids:
  sidecar:schema_mapping
  sidecar:schema_mapping_detail
  sidecar:field_profile
  sidecar:quality_report
  sidecar:capability
  sidecar:manifest
  sidecar:preview_rows
```

Public refs may include:

```json
{
  "id": "normalized-dataset",
  "project_id": "project-id",
  "job_id": "job-id",
  "type": "normalized_dataset",
  "name": "dataset.csv",
  "url": "/api/analysis/jobs/job-id/datasets/normalized-dataset?project_id=project-id",
  "metadata": {}
}
```

Public refs must not include:

```text
absolute path
backend/data path
data/projects path
analysis/output path
```

## Implementation Checklist

### [x] Test Anchor: Tighten Real Adapter Contracts

- WHERE: `tests/providers/test_regularized_dataset_adapter.py`.
- WHY: The adapter is the production persistence boundary for normalized data
  and sidecars.
- HOW:
  - Assert deterministic dataset IDs.
  - Assert resolving `raw-upload` returns raw type.
  - Assert resolving `normalized-dataset` returns normalized type after both
    files exist.
  - Assert unknown dataset ref returns `None`.
  - Assert sidecar refs are stable across `save_sidecar()` and
    `list_sidecars()`.
  - Assert unknown sidecar ref returns `None`.
- EXPECTED_RESULT: Ref lookup is deterministic and file-type correct.
- VERIFY:
  - `uv run pytest tests/providers/test_regularized_dataset_adapter.py -q`

### [x] Test Anchor: Cover Lifecycle Preflight

- WHERE: `tests/business/test_data_processing_analysis_flow.py`.
- WHY: The flow owns the job lifecycle and must reject invalid run transitions
  before background scheduling.
- HOW:
  - Add tests for running before upload/regularization.
  - Add tests for running while regularization needs review.
  - Add tests that a completed regularization can schedule/run.
- EXPECTED_RESULT: Invalid transitions raise `ValidationError`; valid transition
  schedules exactly once.
- VERIFY:
  - `uv run pytest tests/business/test_data_processing_analysis_flow.py -q`

### [x] Test Anchor: Exercise Chain-Native API With Real Local Adapter

- WHERE:
  - `tests/api/conftest.py`
  - `tests/api/test_data_processing_analysis_contracts.py`
- WHY: Current API tests use fake storage and do not prove returned URLs are
  usable.
- HOW:
  - Add a fixture variant that uses `LocalRegularizedDatasetAdapter`.
  - Add a synchronous analysis job provider for API tests that need background
    handler execution.
  - Add contract tests for dataset/sidecar URL retrieval.
- EXPECTED_RESULT: API tests catch missing routes and bad ref resolution.
- VERIFY:
  - `uv run pytest tests/api/test_data_processing_analysis_contracts.py -q`

### [x] Provider Boundary: Stabilize Local Ref IDs

- WHERE: `backend/infrastructure/adapters/local_regularized_dataset_adapter.py`.
- WHY: Provider refs are public contract objects; they must be stable and
  resolvable.
- HOW:
  - Replace random dataset IDs with deterministic local IDs.
  - Replace random sidecar IDs with deterministic `sidecar:{sidecar_type}` IDs.
  - Make `resolve_dataset_ref()` switch on `ref_id`.
  - Make `resolve_sidecar_ref()` parse `sidecar:{sidecar_type}` and validate
    existence.
  - Make `list_sidecars()` return the same IDs every call.
  - Validate `sidecar_type` with the same safe-id rule as project/job IDs.
- EXPECTED_RESULT: Returned refs can be dereferenced exactly.
- VERIFY:
  - `uv run pytest tests/providers/test_regularized_dataset_adapter.py -q`

### [x] Business Flow: Add Run Preflight

- WHERE: `backend/business/flows/data_processing_analysis_flow.py`.
- WHY: Background analysis should only start from a valid regularized state.
- HOW:
  - Add a helper such as `_assert_ready_for_analysis(state, project_id, job_id)`.
  - Check `dataset_regularization` stage status.
  - Check job status is not `needs_review`.
  - Resolve `normalized-dataset` and assert `ref.type == "normalized_dataset"`.
  - Raise `ValidationError` before mutating status when preflight fails.
- EXPECTED_RESULT: Invalid run requests fail synchronously.
- VERIFY:
  - `uv run pytest tests/business/test_data_processing_analysis_flow.py -q`

### [x] Business Flow: Add Dataset And Sidecar Read Methods

- WHERE: `backend/business/flows/data_processing_analysis_flow.py`.
- WHY: API controllers should not call providers directly.
- HOW:
  - Add `get_dataset_ref(...)`.
  - Add `get_sidecar_ref(...)`.
  - Add `load_sidecar(...)` if API should return sidecar JSON.
  - Verify job belongs to project before resolving refs.
  - Raise `NotFoundError` for unknown refs.
- EXPECTED_RESULT: API can dereference output refs through the flow.
- VERIFY:
  - `uv run pytest tests/business/test_data_processing_analysis_flow.py -q`

### [x] API Controller: Add Chain-Native Output Routes

- WHERE: `backend/api/analysis.py`.
- WHY: Public refs currently point to unimplemented routes.
- HOW:
  - Add:
    - `GET /jobs/{job_id}/datasets/{dataset_id}`
    - `GET /jobs/{job_id}/sidecars/{sidecar_id:path}`
  - Use `project_id` query parameter until a project-scoped job route is
    introduced.
  - Return `_success(ref)` for refs, or `_success(payload)` for sidecar payloads
    if the frontend needs direct JSON.
  - Keep local path fields out of the response.
- EXPECTED_RESULT: Every returned `url` from local regularized dataset refs maps
  to an implemented API route.
- VERIFY:
  - `uv run pytest tests/api/test_data_processing_analysis_contracts.py -q`

### [x] Fake Provider: Match Real Provider Semantics

- WHERE: `tests/fakes/providers.py`.
- WHY: Fakes should protect production behavior, not make impossible states pass.
- HOW:
  - Align fake dataset IDs with real IDs.
  - Return `None` for absent refs.
  - Return normalized dataset only when it exists.
  - Return sidecars only when requested sidecar exists.
- EXPECTED_RESULT: Unit/business tests fail when flow code assumes missing data
  exists.
- VERIFY:
  - `uv run pytest tests/business/test_data_processing_analysis_flow.py tests/api/test_data_processing_analysis_contracts.py -q`

### [x] Runtime/Architecture Verification

- WHERE:
  - `backend/core/runtime_checks.py`
  - `tests/core/test_runtime_checks.py`
  - `tests/test_architecture_imports.py`
- WHY: The new chain should remain inside the established architecture boundary.
- HOW:
  - Confirm no runtime imports from `analysis/data-processing-pipeline/**`.
  - Confirm API remains thin and does not call infrastructure adapters directly.
  - Confirm adapter does not import business flow/pipeline modules.
- EXPECTED_RESULT: Architecture lint remains green after the fixes.
- VERIFY:
  - `uv run pytest tests/test_architecture_imports.py tests/core/test_runtime_checks.py -q`

### [x] Quality Gate

- WHERE: repository root.
- WHY: This is a backend runtime and public API contract change.
- HOW:
  - Run focused tests first.
  - Run full configured checks before commit.
- EXPECTED_RESULT: No regression in existing Retail V2 or data-processing tests.
- VERIFY:
  - `make lint`
  - `make format`
  - `make lint`
  - `make typecheck`
  - `make test`
  - `make check`
  - `make hooks`

## Suggested Work Order

1. Tighten adapter tests first; they should fail against the current
   implementation.
2. Fix `LocalRegularizedDatasetAdapter` deterministic ref behavior.
3. Add business flow preflight tests; they should fail against the current
   implementation.
4. Fix `DataProcessingAnalysisFlow.run_analysis()`.
5. Add flow/API dataset and sidecar retrieval tests.
6. Add chain-native read routes and flow methods.
7. Align fake provider semantics with the real adapter.
8. Run focused tests, then full quality gate.

## Commit Criteria

Commit only when all of these are true:

- Returned data-processing `output_refs[*].url` routes are implemented.
- Ref resolution returns the requested dataset/sidecar, or `NotFoundError` /
  `None` for unknown refs.
- `POST /api/analysis/jobs/{job_id}/run` cannot start before regularization is
  completed.
- `needs_review` blocks analysis until an explicit review-resolution behavior is
  added.
- At least one API contract test uses the real local regularized dataset
  adapter.
- Focused tests and project quality gate pass.

