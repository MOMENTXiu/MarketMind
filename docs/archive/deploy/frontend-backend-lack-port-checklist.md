# Frontend Backend Lack-port Construction Checklist

Status: active checklist, 2026-05-27.

Execution rule: complete one phase at a time and record verification immediately.

## 1. Test Anchors

- WHERE: `tests/api/test_retail_analysis_contracts.py`, `tests/api/test_frontend_api_matrix_contracts.py`.
- WHY: The new endpoint changes public Retail V2 read surface and must keep artifact metadata behavior intact.
- HOW: Add API tests for artifact payload shape, path-free response, unsupported artifact types, and frontend-used table rows.
- EXPECTED_RESULT: Tests fail before implementation and pass after provider/flow/controller wiring.
- VERIFY: `uv run pytest tests/api/test_retail_analysis_contracts.py tests/api/test_frontend_api_matrix_contracts.py`.
- STATUS: completed.
- RESULT: Added artifact payload contract coverage in `tests/api/test_retail_analysis_contracts.py`.
- VERIFY_RESULT: `uv run pytest tests/api/test_retail_analysis_contracts.py::test_artifact_payload_endpoint_returns_path_free_rows tests/api/test_retail_analysis_contracts.py::test_unsupported_artifact_payload_returns_error` passed with 2 tests and existing Pydantic warnings.

## 2. Provider Interface

- WHERE: `backend/providers/dtos.py`, `backend/providers/analysis_artifact_provider.py`.
- WHY: Business flow must not read local artifact files directly.
- HOW: Add `AnalysisArtifactPayloadDTO` and `AnalysisArtifactProvider.load_payload`.
- EXPECTED_RESULT: Provider boundary exposes a read-only artifact payload capability.
- VERIFY: `uv run python -m py_compile backend/providers/dtos.py backend/providers/analysis_artifact_provider.py`.
- STATUS: completed.
- RESULT: Added `AnalysisArtifactPayloadDTO` and `AnalysisArtifactProvider.load_payload`.
- VERIFY_RESULT: `uv run python -m py_compile backend/providers/dtos.py backend/providers/analysis_artifact_provider.py` passed.

## 3. External Adapter

- WHERE: `backend/infrastructure/adapters/local_analysis_artifact_adapter.py`, `tests/fakes/providers.py`.
- WHY: Local CSV/JSON/Markdown reads belong in infrastructure, not the API controller or business flow.
- HOW: Implement `load_payload` for table/json/markdown artifacts and update fake provider.
- EXPECTED_RESULT: Adapter returns JSON-safe DTOs without local paths.
- VERIFY: targeted API tests plus `uv run ruff check backend/infrastructure/adapters/local_analysis_artifact_adapter.py tests/fakes/providers.py`.
- STATUS: completed.
- RESULT: Implemented `LocalAnalysisArtifactAdapter.load_payload` for table/json/markdown payloads and updated the fake provider.
- VERIFY_RESULT: Targeted artifact payload API tests passed.

## 4. Ability Atom

- WHERE: none.
- WHY: The phase is a read-only artifact payload lookup, not a new business computation.
- HOW: No new Ability Atom.
- EXPECTED_RESULT: No speculative ability file.
- VERIFY: Architecture import tests remain green.
- STATUS: completed.
- RESULT: No Ability Atom was added because this phase is a read-only artifact lookup.
- VERIFY_RESULT: No new ability files.

## 5. Business Pipeline

- WHERE: none.
- WHY: No multi-step business SOP is introduced.
- HOW: No new Business Pipeline.
- EXPECTED_RESULT: No pass-through pipeline.
- VERIFY: Architecture import tests remain green.
- STATUS: completed.
- RESULT: No Business Pipeline was added because this phase is not a multi-step business SOP.
- VERIFY_RESULT: No new pipeline files.

## 6. Business Flow

- WHERE: `backend/business/flows/retail_analysis_flow.py`.
- WHY: Retail project state and artifact refs are owned by the existing Retail Analysis Flow.
- HOW: Add `get_artifact_payload(project_id, artifact_id)` that validates project state, ensures the artifact ref exists, calls provider payload loading, and maps not-found/unsupported errors.
- EXPECTED_RESULT: Flow exposes a read-only artifact payload method without direct filesystem access.
- VERIFY: API contract tests.
- STATUS: completed.
- RESULT: Added `RetailAnalysisFlow.get_artifact_payload` with state/ref validation and provider delegation.
- VERIFY_RESULT: Targeted artifact payload API tests passed.

## 7. API Controller

- WHERE: `backend/api/analysis.py`, `docs/backend-api.md`.
- WHY: Frontend needs a documented public route to read table payloads.
- HOW: Add `GET /projects/{project_id}/artifacts/{artifact_id:path}/payload` and document the response.
- EXPECTED_RESULT: Frontend can fetch table rows through `/api/analysis`.
- VERIFY: `curl`/API tests for the new endpoint.
- STATUS: completed.
- RESULT: Added `GET /api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload` and documented it in `docs/backend-api.md`.
- VERIFY_RESULT: Targeted artifact payload API tests passed.

## 8. Frontend Connection

- WHERE: `frontend/src/api/retail.ts`, `frontend/src/api/types.ts`, `frontend/src/views/ProjectDetail.vue`.
- WHY: Existing UI uses legacy result fields or synthetic rows.
- HOW: Add typed wrapper and use `retail_item_association_rules.csv` / `retail_customer_segments.csv` payloads when available, retaining graceful empty states.
- EXPECTED_RESULT: Project detail reads real backend artifact rows instead of stale legacy fields for LP-001 and LP-002.
- VERIFY: `cd frontend && npm run build`, Chrome smoke on `/projects/{id}`.
- STATUS: completed.
- RESULT: Added `getRetailArtifactPayload` and connected `ProjectDetail.vue` association rules and cluster customer rows to Retail V2 artifact payloads.
- VERIFY_RESULT: `cd frontend && npm run build` passed with the existing large chunk warning.

## 9. Architecture Lint / Runtime Check / Full Verification

- WHERE: project root.
- WHY: Confirm the change respects layer boundaries and does not break the current baseline.
- HOW: Run lint/format/check and inspect browser console.
- EXPECTED_RESULT: Quality gate passes or any residual risk is recorded.
- VERIFY: `make lint`, `make format`, `make lint`, `make check`.
- STATUS: completed.
- RESULT: Full quality gate and browser smoke passed for Phase 1.
- VERIFY_RESULT: `make lint` passed, `make format` reformatted 1 file, rerun `make lint` passed, `make check` passed with 190 passed / 5 skipped and the existing frontend chunk warning. Chrome smoke on `/projects` and a real `/projects/{id}` detail route showed `系统正常`, project detail content, association section, and no app-side console errors.

## 10. Cleanup

- WHERE: docs and git diff.
- WHY: Keep the handoff precise.
- HOW: Update statuses above with command results and leave deferred LP items in `docs/frontend-backend-lack-port.md`.
- EXPECTED_RESULT: Future agents can continue LP-003 onward without rediscovery.
- VERIFY: `git diff --stat`.
- STATUS: completed.
- RESULT: Deferred LP-003 through LP-006 remain recorded in `docs/frontend-backend-lack-port.md`; Phase 1 files are visible in `git diff --stat`.
- VERIFY_RESULT: `git diff --stat` reviewed during handoff.
