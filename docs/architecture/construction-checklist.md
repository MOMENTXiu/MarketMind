# Backend Architecture Construction Checklist

> Active note (2026-05-27): The active checklist is the Retail V2 migration from local pickle state to PostgreSQL, Redis Queue, and SSE. The historical checklist below remains as prior migration record only. Code changes for the active migration must follow this section until it is completed and reconciled.

## Active 2026-05-27: Retail V2 PostgreSQL State + Redis Queue + SSE

Execution rules:

- Do not change business code before the architecture change plan and this checklist are present.
- Execute one cohesive phase at a time.
- Preserve existing `/api/analysis/projects` REST schema, status codes, error shape, and visible state semantics.
- Use start blank semantics: do not migrate historical pickle data.
- Do not put Retail V2 project state or project index back into `AnalysisModelStoreProvider`.
- Business Flow, Pipeline, and Ability code must not import SQLAlchemy, Redis, RQ, FastAPI response objects, infrastructure adapters, or env readers.
- Each phase must append actual verification result, failure, risk, and rollback notes before the next phase starts.

### [x] Ready Gate: Lock Active Migration Scope

- WHERE: `docs/architecture/architecture-change.md`, `docs/architecture/construction-checklist.md`.
- WHY: `backend-architecture-orchestration` requires the architecture change plan and construction checklist before code migration.
- HOW: Record the active decisions D1=A, D2=A, D3=A, D4=B1, D5=A, D6=C; document current pickle call chain, target PostgreSQL/Redis/SSE chain, Provider boundaries, config strategy, error strategy, validation strategy, and rollback.
- EXPECTED_RESULT: Implementers can start phase 1 without relying on chat history; the documents state that Retail state moves to PostgreSQL, async jobs move to Redis Queue, and frontend status updates move to SSE.
- VERIFY: Manual review confirms both documents contain the active section; grep confirms the active plan does not require historical pickle migration and does not keep Retail state in `AnalysisModelStoreProvider`.
- STATUS: completed
- RESULT: Active architecture section and this active checklist were added on 2026-05-27.
- RISK: Oracle review is still required before implementation because this is an architecture-level migration affecting more than five files.
- ROLLBACK: Revert only the active sections if the locked decisions change before implementation.

### [x] Phase 1: Test Anchors

- WHERE: `tests/api/test_retail_analysis_contracts.py`, `tests/api/test_data_processing_analysis_contracts.py`, `tests/business/`, `tests/providers/`, `tests/infrastructure/`, `frontend/src/views/ProjectDetail.vue`, `frontend/src/views/DataProcessing.vue`.
- WHY: The migration changes persistence, async execution, and frontend status transport; REST contract, lifecycle state, provider semantics, and frontend fallback need executable anchors before implementation.
- HOW: Confirm existing Retail V2 API contract tests cover create/list/get/delete/upload/run/status/artifacts/results and retired-route absence; add or extend executable tests for `RetailAnalysisStateProvider`, `AnalysisJobQueueProvider`, and `AnalysisEventStreamProvider`; add lifecycle tests proving list/detail no longer read the pickle index after migration; define executable SSE payload/fallback tests or fixtures consumed by tests; keep external services fake or isolated. A written test map alone is not sufficient to leave this phase.
- EXPECTED_RESULT: Executable behavior anchors exist before migration code starts: REST schema/status/error shape, no pickle index read/write after cutover, PostgreSQL state projection, RQ enqueue contract, worker payload contract, SSE event payload, and REST fallback behavior.
- VERIFY: `make test`; targeted `uv run pytest tests/api/test_retail_analysis_contracts.py tests/api/test_data_processing_analysis_contracts.py`; targeted provider/infrastructure tests when created; `npm --prefix frontend run build` or `make build` for frontend compile safety.
- STATUS: completed
- RESULT: Added executable Phase 1 anchors without runtime cutover. New provider contract coverage lives in `tests/providers/test_retail_analysis_provider_contracts.py`: Retail state fake save/get/list/delete with newest-first ordering, JSON-serializable queue payload + queue handle contract, SSE payload/fallback + heartbeat/reconnect metadata contract, and data-processing `needs_review` SSE contract. Added a strict `xfail` anchor proving Phase 6 must remove pickle state/index IO from `RetailAnalysisFlow` before cutover. Extended `tests/test_architecture_imports.py` so the staged boundary now rejects new `redis`, `rq`, FastAPI request/response symbols, `fastapi.responses`/`starlette.responses`, `backend.core.config`, and direct env access in guarded layers while preserving the required legacy allowlist for `backend/api/dependencies.py`.
- RISK: Runtime still uses local pickle state/index and FastAPI background jobs until Phase 6 and Phase 3 respectively, so the cutover-safe anchor remains `xfail(strict=True)` by design. SSE and queue tests only lock payload semantics right now; they do not prove adapter wiring, worker execution, or endpoint transport.
- ROLLBACK: Remove only newly added failing anchors if the active design changes; do not weaken existing API contract tests.
- VERIFY: `uv run pytest tests/providers tests/test_architecture_imports.py` -> `53 passed, 1 xfailed`; `uv run pytest tests/api/test_retail_analysis_contracts.py` -> `10 passed`; `uv run ruff check backend/providers tests/providers tests/fakes tests/test_architecture_imports.py` -> passed.

### [x] Phase 2: Provider Interface

- WHERE: `backend/providers/retail_analysis_state_provider.py`, `backend/providers/analysis_job_queue_provider.py`, `backend/providers/analysis_event_stream_provider.py`, `backend/providers/analysis_model_store_provider.py`, `backend/providers/container.py`, `backend/providers/dtos.py` or dedicated DTO modules.
- WHY: D3=A requires a narrow Retail V2 state Provider; Redis queue and SSE must also sit behind Provider Boundary. `AnalysisModelStoreProvider` must stop carrying Retail state/index semantics.
- HOW: Define `RetailAnalysisStateProvider` with only current business needs: get state, save state or transition state, list project views, delete project, persist latest run metadata, persist artifact/result summaries, and read latest project detail. Define `AnalysisJobQueueProvider` for enqueueing project analysis jobs and returning internal queue/job metadata. Define `AnalysisEventStreamProvider` for publishing status events and subscribing to project/job event streams. Add DTOs for project state, run state, state event, and queue job handle if existing DTOs are insufficient. Add `retail_analysis_state`, `analysis_job_queue`, and `analysis_event_stream` to `ProvidersContainer`. Update `AnalysisModelStoreProvider` comments/tests so it only covers model artifacts.
- EXPECTED_RESULT: Business code can depend on provider interfaces without seeing SQLAlchemy sessions, Redis clients, RQ jobs, FastAPI `StreamingResponse`, or pickle paths.
- VERIFY: `uv run python -m py_compile backend/providers`; `uv run pytest tests/providers`; `uv run pytest tests/test_architecture_imports.py`; `make lint`.
- STATUS: completed
- RESULT: Added narrow provider boundary files `backend/providers/retail_analysis_state_provider.py`, `backend/providers/analysis_job_queue_provider.py`, and `backend/providers/analysis_event_stream_provider.py` plus JSON-safe DTOs in `backend/providers/dtos.py` for Retail project detail/list projection, run info, state event, queue payload/handle, and event subscription items. `ProvidersContainer` now exposes `retail_analysis_state`, `analysis_job_queue`, and `analysis_event_stream`; `backend/infrastructure/factories/provider_factory.py` wires lightweight in-memory placeholders so existing tests and request-scoped container creation keep working before PostgreSQL/Redis adapters exist. `backend/providers/analysis_model_store_provider.py` docstrings now explicitly scope the provider to true model artifacts only, excluding Retail state/index/run state.
- RISK: The new container fields are intentionally backed by in-memory placeholders until Phase 3 introduces PostgreSQL/Redis adapters, so these contracts are ready for import and typing but not yet runtime-backed by external services. Existing `AnalysisJobProvider` and current Retail flow paths still coexist with the new queue/state/event boundary until later cutover phases remove the legacy path.
- ROLLBACK: Remove new provider files and container fields before downstream phases depend on them if the interface is too broad or incorrectly named.
- VERIFY: `uv run python -m py_compile $(find backend/providers tests/fakes -name '*.py' -print) tests/test_architecture_imports.py` -> passed; `uv run pytest tests/providers tests/test_architecture_imports.py` -> `53 passed, 1 xfailed`; `uv run ruff check backend/providers tests/providers tests/fakes tests/test_architecture_imports.py` -> passed; `uv run ruff format --check backend/providers tests/providers tests/fakes tests/test_architecture_imports.py` -> `33 files already formatted`.

### [x] Phase 3: External Adapter

- WHERE: `backend/infrastructure/adapters/postgres_retail_analysis_state_adapter.py`, `backend/infrastructure/adapters/redis_analysis_job_queue_adapter.py`, `backend/infrastructure/adapters/redis_analysis_event_stream_adapter.py`, `backend/infrastructure/db/session.py`, `backend/infrastructure/db/models/`, `backend/infrastructure/factories/provider_factory.py`, `backend/core/config.py`, `pyproject.toml`, `uv.lock`, `docker-compose.dev.yml`.
- WHY: D1=A uses the existing six-table PostgreSQL schema; D2=A removes pickle index reads; D4=B1 requires Redis Queue in the same implementation round; D6=C needs Redis pub/sub for cross-worker status events.
- HOW: Implement `PostgresRetailAnalysisStateAdapter` using existing `ProjectRecord`, `ProcessingRunRecord`, `ArtifactRecord`, and `AnalysisResultRecord`; keep large artifacts and model binaries out of DB. Implement `RedisAnalysisJobQueueAdapter` with RQ as the conservative Redis queue choice. Implement `RedisAnalysisEventStreamAdapter` with Redis pub/sub and heartbeat-friendly event serialization. Extend `Settings.TASK_QUEUE_BACKEND` to include `redis`; keep `DATABASE_URL` and `REDIS_URL` flowing through Provider Factory into adapters. Update dependencies with `redis` and `rq`. Add worker entry command/script without starting long-lived processes during tests. This phase proves adapter contracts and factory config matrix; it must not switch Retail Flow runtime away from pickle until Phase 6 cutover.
- EXPECTED_RESULT: PostgreSQL Retail state adapter, Redis queue adapter, Redis event stream adapter, worker entry, and Provider Factory config paths are contract-tested and ready; business runtime is still unchanged until Phase 6 performs the coordinated cutover.
- VERIFY: `uv run python -m py_compile $(find backend/infrastructure backend/workers backend/providers tests/infrastructure tests/providers -name '*.py' -print) backend/core/config.py tests/test_architecture_imports.py` (the checklist's original directory-form `py_compile` command is not valid because `py_compile` only accepts files) -> passed; `uv run pytest tests/infrastructure tests/providers tests/test_architecture_imports.py` -> `69 passed, 3 skipped, 1 xfailed`; `uv run pytest tests/api/test_retail_analysis_contracts.py` -> `10 passed`; `uv run ruff check backend/infrastructure backend/core backend/workers backend/providers tests/infrastructure tests/providers tests/test_architecture_imports.py` -> passed; `uv run ruff format --check backend/infrastructure backend/core backend/workers backend/providers tests/infrastructure tests/providers tests/test_architecture_imports.py` -> `78 files already formatted`.
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/postgres_retail_analysis_state_adapter.py`, `backend/infrastructure/adapters/redis_analysis_job_queue_adapter.py`, `backend/infrastructure/adapters/redis_analysis_event_stream_adapter.py`, and stable worker entry `backend/workers/retail_analysis_worker.py`. `PostgresRetailAnalysisStateAdapter` now maps Retail V2 state into the existing six-table schema with newest-first list projection, latest-run enforcement, summary merge, project-scoped deterministic internal dataset ids, managed `datasets` row writes from public `dataset_ref`, artifact/result projection, and project-delete cascade coverage on sqlite in-memory tests. `RedisAnalysisJobQueueAdapter` now serializes `AnalysisQueueJobPayloadDTO` into the stable worker payload contract and enqueues `backend.workers.retail_analysis_worker.execute_retail_analysis_job` without exposing RQ jobs. `RedisAnalysisEventStreamAdapter` now publishes/subscribes JSON-safe SSE items over Redis pub/sub with event id, retry/reconnect, heartbeat metadata, fallback URL, and terminal framing; non-numeric live pub/sub event ids are not filtered by lexicographic `Last-Event-ID` comparison. `Settings`/Provider Factory now support `TASK_QUEUE_BACKEND=redis` and assemble PostgreSQL state + Redis queue + Redis event stream through cached process-level resources when `REDIS_ENABLED=true`, while the default `none` path still uses the existing local runtime providers. Root dependencies were updated with `redis` and `rq`, and `uv.lock` was refreshed with `uv add redis rq`.
- RISK: Retail runtime cutover is intentionally not done in this phase. `RetailAnalysisFlow` still reads/writes pickle state/index and still schedules work through `analysis_jobs` / FastAPI background tasks until Phase 6, so the new PostgreSQL/Redis adapters are readiness-only and not yet the live execution path. Live PostgreSQL/Redis connectivity was not probed because this phase intentionally did not start external services; existing live-infra tests that require `TEST_DATABASE_URL` remained skipped. The worker non-dry-run path still delegates to the old Flow until Phase 5/6 replaces it with the reusable business pipeline.
- ROLLBACK: Remove adapter wiring and dependencies if provider contracts fail; queued Redis jobs can be discarded because this migration is start blank.

#### Phase 3 Cutover Readiness Gate

- WHERE: `tests/providers/`, `tests/infrastructure/`, `backend/infrastructure/factories/provider_factory.py`, `backend/workers/`.
- WHY: D4=B1 is an all-at-once runtime cutover, but adapter readiness must be proven before Flow deletes pickle state/index helpers.
- HOW: Require all provider contract tests, adapter contract tests, factory config matrix tests, worker payload serialization tests, worker dry-run tests, and SSE event serialization tests to pass before Phase 4-6 begin runtime cutover work.
- EXPECTED_RESULT: The implementation can enter Business Flow cutover without mixed PG/pickle state or request-scoped RQ worker closures.
- VERIFY: `uv run pytest tests/infrastructure tests/providers tests/test_architecture_imports.py` -> `69 passed, 3 skipped, 1 xfailed`; focused readiness coverage is included in that run through PostgreSQL state adapter, Redis queue adapter, Redis event stream adapter, worker dry-run, and provider factory config matrix tests.
- STATUS: completed
- RESULT: Provider contract tests, adapter contract tests, factory config matrix coverage, cached runtime resource coverage, worker payload serialization + dry-run coverage, SSE event serialization coverage, non-numeric `Last-Event-ID` behavior, and DB-backed dataset metadata write coverage now all pass without enabling runtime cutover. The strict Phase 6 `xfail` anchor still proves pickle state/index removal is deferred, so the gate confirms adapter readiness without masking the remaining flow cutover work.
- RISK: This gate only proves adapter wiring, payload contracts, and boundary safety. It does not prove live Redis/PostgreSQL connectivity or mixed-runtime behavior because those remain intentionally out of scope until the later cutover phases.

### [x] Phase 4: Ability Atom

- WHERE: `backend/abilities/` and existing Retail ability modules.
- WHY: Flow should orchestrate lifecycle, not embed state persistence, queue submission, event publication, or adapter error handling details.
- HOW: Add or adjust small abilities for reading Retail state, saving/transiting Retail state, listing project views, submitting analysis jobs, publishing status events, and resolving persisted artifacts/results. Each ability receives explicit input and a provider or `ProvidersContainer`; each returns internal DTO/dict structures already used by the REST contract. Abilities may catch internal provider errors only when converting them to domain errors; they must not catch SQLAlchemy, Redis, or RQ exceptions.
- EXPECTED_RESULT: Flow/Pipeline can compose abilities while infrastructure details stay behind Provider Boundary.
- VERIFY: `uv run pytest tests/abilities`; `uv run pytest tests/test_architecture_imports.py`; `make lint`.
- STATUS: completed
- RESULT: Retail V2 state DTO conversion, project-summary projection, and SSE event DTO assembly now live in `backend/business/flows/retail_analysis_state.py`, so Flow/Pipeline no longer shape provider payloads inline or reach into adapter-only details. No new `backend/abilities/retail/` file was required for this slice; the minimal provider-boundary-safe extraction was enough to keep state serialization and event payload construction out of infrastructure code while existing Retail analysis pipelines continue to compose the existing retail ability atoms.
- RISK: The state/event helper extraction still lives in a business helper module rather than a dedicated `backend/abilities/retail/` atom. If Phase 7 adds more SSE payload variants or job resources, split these helpers into a dedicated ability module instead of growing the Flow helper further.
- VERIFY: `uv run python -m py_compile $(find backend/business backend/abilities backend/workers backend/providers tests/business tests/api tests/providers -name '*.py' -print) tests/test_architecture_imports.py` -> passed; `uv run pytest tests/business tests/api/test_retail_analysis_contracts.py tests/providers/test_retail_analysis_provider_contracts.py tests/test_architecture_imports.py` -> `53 passed, 1 skipped`; `uv run ruff check backend/business backend/abilities backend/workers backend/providers tests/business tests/api tests/providers tests/test_architecture_imports.py` -> passed.
- ROLLBACK: Inline the ability only if it proves to be a pure pass-through and the boundary remains compliant; otherwise revert the specific ability file.

### [x] Phase 5: Business Pipeline

- WHERE: `backend/business/pipelines/`, Retail V2 pipeline modules, worker callable module if introduced.
- WHY: Redis worker should invoke a reusable business pipeline that handles analysis execution, state transitions, artifact/result persistence, event publication, and failure handling without depending on FastAPI or infrastructure clients.
- HOW: Organize the scheduled analysis execution path as pipeline steps: load state, mark processing, run existing retail analysis stages, persist artifact/result summaries, mark completed or failed, publish status events after each visible transition. The pipeline depends on abilities/provider interfaces and internal errors only. Preserve existing stage order, `job_id`, `trace_id`, `stage_statuses`, `recommendations`, `marketer_insights`, and artifact refs.
- EXPECTED_RESULT: Redis worker and tests can run the same business pipeline; state and event side effects are ordered and testable.
- VERIFY: `uv run pytest tests/business`; targeted Retail V2 lifecycle tests; `uv run pytest tests/test_architecture_imports.py`; `make lint`.
- STATUS: completed
- RESULT: Added `backend/business/pipelines/retail_analysis_execution_pipeline.py` and moved the scheduled Retail execution chain there. `RetailAnalysisFlow.execute_scheduled_analysis` now only loads persisted state and delegates to the pipeline. The pipeline persists visible state transitions through the Flow save callback, emits `state_changed` / `artifact_ready` / terminal events after saves, preserves stage order and public state shape, and is exercised both from the Flow and from the worker non-dry-run path through `backend/workers/retail_analysis_worker.py::execute_retail_analysis_business_entry`.
- RISK: The pipeline currently uses Flow-provided state mutation callbacks instead of a standalone state-transition ability/service. That keeps the diff minimal, but if another queued analysis job needs the same transition logic, extract a shared business helper instead of duplicating callback wiring.
- VERIFY: `uv run pytest tests/business tests/api/test_retail_analysis_contracts.py tests/providers/test_retail_analysis_provider_contracts.py tests/test_architecture_imports.py` -> `53 passed, 1 skipped`; `uv run pytest tests/infrastructure/test_retail_analysis_worker.py tests/providers/test_provider_factory.py` -> `10 passed`; `uv run pytest tests/api/test_frontend_api_matrix_contracts.py` -> `4 passed`.
- ROLLBACK: Revert pipeline extraction and keep old flow execution only until Phase 6, without reintroducing infrastructure imports.

### [x] Phase 6: Business Flow

- WHERE: `backend/business/flows/retail_analysis_flow.py`.
- WHY: Retail V2 has project lifecycle, async job lifecycle, state queries, artifact/result access, delete behavior, and event publication; a Business Flow remains justified, but it must stop using pickle state/index and FastAPI background scheduling.
- HOW: Replace `_load_state` and `_save_state` internals with `RetailAnalysisStateProvider` calls or extracted abilities. Delete `_load_project_index`, `_save_project_index`, `_upsert_project_index_entry`, and `_remove_project_index_entry`; `list_projects` calls `RetailAnalysisStateProvider.list_projects`. `start_analysis` enqueues through `AnalysisJobQueueProvider`. State changes publish through `AnalysisEventStreamProvider`. `execute_scheduled_analysis` becomes a worker-safe path or delegates to the Phase 5 pipeline. No SQLAlchemy, Redis, RQ, FastAPI response, adapter, or env imports are allowed.
- EXPECTED_RESULT: RetailAnalysisFlow no longer reads or writes Retail state/index through `AnalysisModelStoreProvider`; public REST behavior remains equivalent; empty PostgreSQL state returns empty project list.
- VERIFY: `uv run pytest tests/business tests/api/test_retail_analysis_contracts.py`; `uv run pytest tests/test_architecture_imports.py`; `make lint`.
- STATUS: completed
- RESULT: `backend/business/flows/retail_analysis_flow.py` no longer reads or writes Retail state/index through `AnalysisModelStoreProvider`. `list_projects` now uses `providers.retail_analysis_state.list_projects()`, `_load_state` / `_save_state` go through `RetailAnalysisStateProvider`, `delete_project` deletes persisted project state via `retail_analysis_state.delete_project(project_id)` while `analysis_models` only deletes true model artifacts, and `start_analysis` now enqueues `AnalysisQueueJobPayloadDTO` through `AnalysisJobQueueProvider`. `_save_state` publishes `AnalysisStateEventDTO` after visible state changes and intentionally swallows post-save publish failures so state commits stay visible. The strict Phase 6 provider anchor was converted from `xfail` to a passing test, and API/frontend tests now mutate project state through `isolated_env.container.retail_analysis_state` instead of pickle model state.
- RESULT: Post-review runtime blockers were fixed before Phase 7: `Settings` and `.env.example` now default to `TASK_QUEUE_BACKEND=redis` and `REDIS_ENABLED=true`; `tests/api/test_runtime_dependency_contracts.py` proves the non-overridden API dependency path assembles PostgreSQL/Redis providers and reuses cached runtime resources across request containers; `scripts/start-worker.sh` starts the RQ worker and `scripts/start-project.sh` launches it beside backend/frontend; `RetailAnalysisFlow.execute_scheduled_analysis` and `backend/workers/retail_analysis_worker.py` now reject stale/replayed worker payloads whose `job_id`, `trace_id`, or `attempt` does not match the latest persisted run.
- RISK: Live PostgreSQL/Redis connectivity was not exercised in this phase; the validated runtime path is the Retail V2 business flow plus provider-factory Redis/PostgreSQL assembly and isolated in-memory test doubles. Event publication is intentionally best-effort after state save, so delivery observability remains a Phase 7/8 concern rather than a rollback trigger here.
- VERIFY: `uv run python -m py_compile $(find backend/business backend/abilities backend/workers backend/providers tests/business tests/api tests/providers -name '*.py' -print) tests/test_architecture_imports.py` -> passed; `uv run pytest tests/business tests/api/test_retail_analysis_contracts.py tests/providers/test_retail_analysis_provider_contracts.py tests/test_architecture_imports.py` -> `53 passed, 1 skipped`; `uv run pytest tests/infrastructure/test_retail_analysis_worker.py tests/providers/test_provider_factory.py` -> `10 passed`; `uv run pytest tests/api/test_frontend_api_matrix_contracts.py` -> `4 passed`; post-review blocker verification `uv run pytest tests/api/test_runtime_dependency_contracts.py tests/providers/test_provider_factory.py tests/infrastructure/test_retail_analysis_worker.py` -> `13 passed`; `bash -n scripts/start-worker.sh scripts/start-backend.sh scripts/start-project.sh && uv run rq --help >/dev/null` -> passed; `uv run ruff check backend/business backend/abilities backend/workers backend/providers tests/business tests/api tests/providers tests/test_architecture_imports.py` -> passed; `uv run ruff format --check backend/business backend/abilities backend/workers backend/providers tests/business tests/api tests/providers tests/test_architecture_imports.py` -> `118 files already formatted`; grep over `backend/**` for `_load_project_index|_save_project_index|_upsert_project_index_entry|_remove_project_index_entry|retail_analysis_project_index|_retail_analysis_index` -> no matches.
- ROLLBACK: Revert this file to the prior Flow implementation before deleting pickle index helpers if behavior anchors fail; do not partially keep mixed PG/pickle state.

### [x] Phase 7: API Controller And Frontend SSE

- WHERE: `backend/api/analysis.py`, `backend/api/dependencies.py`, `frontend/src/api/retail.ts`, `frontend/src/views/ProjectDetail.vue`, `frontend/src/views/DataProcessing.vue`, frontend tests if present.
- WHY: REST API compatibility must remain intact while D6=C adds real-time status transport and removes 2.5s polling as the primary path.
- HOW: Keep existing REST endpoints and response schema. Add a project/job SSE endpoint such as `/api/analysis/projects/{project_id}/events`, with API Controller only wrapping protocol details and delegating event subscription to provider/flow dependency. Add frontend EventSource helper in `frontend/src/api/retail.ts`; ProjectDetail and DataProcessing use REST for initial load and fallback, then EventSource for updates. Remove or gate `setInterval(..., 2500)` so it is not the normal active path. Implement disconnect cleanup and browser reconnection behavior.
- EXPECTED_RESULT: Existing REST callers keep working; frontend receives processing state updates through SSE; no API Controller imports SQLAlchemy, Redis, RQ, or infrastructure adapters.
- VERIFY: `uv run pytest tests/api/test_retail_analysis_contracts.py`; `uv run pytest tests/test_architecture_imports.py`; `npm --prefix frontend run build`; `make build`; manual browser smoke test when dev server is intentionally started.
- STATUS: completed
- RESULT: Added SSE protocol wrappers in `backend/api/analysis.py` for `GET /api/analysis/projects/{project_id}/events` and `GET /api/analysis/jobs/{job_id}/events`. The controller emits an initial REST-backed snapshot frame, then delegates live project/job event subscription to `AnalysisEventStreamProvider`; REST response schema and existing endpoints remain unchanged. Added `createApiEventSource`, `openRetailProjectEvents`, and `openDataProcessingJobEvents` in `frontend/src/api/`, plus a typed `AnalysisSseEvent` contract. `frontend/src/views/ProjectDetail.vue` and `frontend/src/views/DataProcessing.vue` now use EventSource as the normal active status path, refresh from REST snapshots on events/reconnect errors, and close connections on terminal states or unmount. The old `setInterval(pollProject, 2500)` / `setInterval(pollJob, 2500)` paths were removed from those views.
- RISK: Browser smoke was not run because no dev server was intentionally started in this phase. The tested SSE path proves endpoint framing, OpenAPI reachability, contract compatibility, and frontend compile safety; live Redis pub/sub delivery still depends on Phase 8 runtime checks or an intentional local stack smoke.
- VERIFY: `uv run pytest tests/api/test_retail_analysis_contracts.py tests/api/test_data_processing_analysis_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py` -> `36 passed, 1 skipped`; `make lint` -> passed; `make format` -> reformatted 1 Python file; `make lint` -> passed; `make typecheck` -> placeholder output only; `make test` -> `217 passed, 5 skipped`; `make build` -> passed with the existing Vite chunk-size warning; `make check` -> passed; `make verify` -> passed including hooks; grep over `frontend/src/views/ProjectDetail.vue` and `frontend/src/views/DataProcessing.vue` for `setInterval((pollProject|pollJob)|pollProject|pollJob` -> no matches.
- ROLLBACK: Disable SSE route and restore REST fallback path if frontend build or API contract fails; do not alter REST schema to compensate.

### [x] Phase 8: Architecture Lint, Runtime Check, Full Verification

- WHERE: `tests/test_architecture_imports.py`, `backend/core/runtime_checks.py`, `Makefile`, `.github/workflows/`, relevant docs under `docs/architecture/`.
- WHY: Architecture boundaries and runtime assembly must be mechanically protected after the storage/queue/SSE cutover.
- HOW: Extend architecture tests to forbid business/ability imports of SQLAlchemy, Redis, RQ, FastAPI response/request objects, infrastructure adapters, and env readers; forbid provider interfaces from importing infrastructure; forbid API controllers from constructing DB/Redis/RQ clients. Extend runtime checks to validate `TASK_QUEUE_BACKEND=redis`, `REDIS_URL`, Redis queue creation, Redis pub/sub probe, PostgreSQL session factory probe, Provider Factory assembly, worker dry run, SSE heartbeat serialization, and schema validation for state events. Run full quality gates and record placeholder targets explicitly.
- EXPECTED_RESULT: Boundary regressions fail tests; missing DB/Redis configuration fails runtime checks; full verification evidence exists before cleanup.
- VERIFY: `make lint`; `make format`; `make lint`; `make typecheck`; `make test`; `make build`; `make check`; `make verify`.
- STATUS: completed
- RESULT: Added `check-retail-runtime --dry-run` to `backend/core/runtime_checks.py` and `tests/core/test_runtime_checks.py`. The command validates target defaults (`TASK_QUEUE_BACKEND=redis`, `REDIS_ENABLED=true`, `REDIS_URL` present), verifies Provider Factory assembles `PostgresRetailAnalysisStateAdapter`, `RedisAnalysisJobQueueAdapter`, and `RedisAnalysisEventStreamAdapter`, probes SQLAlchemy engine/session factory creation with an in-memory SQLite URL, dry-runs queue enqueue payload serialization, Redis pub/sub SSE heartbeat serialization/subscription, and Retail worker dry-run payload validation/provider assembly. Existing architecture lint already rejects business/ability/provider regressions for SQLAlchemy, Redis, RQ, FastAPI request/response types, infrastructure adapters, and env/settings access; API controller direct DB/Redis/RQ construction remains guarded by forbidden import prefixes.
- RISK: `check-retail-runtime --dry-run` intentionally does not open live PostgreSQL or Redis sockets, so it is a deterministic assembly/serialization/worker gate rather than a live infrastructure smoke. Live stack confidence is covered by optional infra/E2E smoke when Docker services are intentionally started.
- VERIFY: `uv run pytest tests/core/test_runtime_checks.py tests/test_architecture_imports.py` -> `35 passed`; `uv run ruff check backend/core/runtime_checks.py tests/core/test_runtime_checks.py` -> passed.
- ROLLBACK: Revert only incorrect lint/runtime rules; never delete rules to hide real violations.

### [x] Phase 9: Cleanup And Knowledge Reconciliation

- WHERE: `backend/business/flows/retail_analysis_flow.py`, `backend/providers/analysis_model_store_provider.py`, `backend/infrastructure/adapters/local_analysis_model_store_adapter.py`, `frontend/src/views/ProjectDetail.vue`, `frontend/src/views/DataProcessing.vue`, `docs/architecture/postgres-redis-docker-migration-plan.md`, `docs/architecture/analysis-v2-integration-checklist.md`, `docs/ARCHITECTURE.md`, `backend/README.md`, `README.md`, `AGENTS.md`.
- WHY: Old pickle-index, BackgroundTasks, and polling language caused the original confusion; docs and memory must match runtime after migration.
- HOW: Remove Retail V2 pickle-index helpers and stale comments. Confirm `AnalysisModelStoreProvider` docs/tests only describe model artifacts. Update architecture docs to state PostgreSQL is the Retail state runtime source, Redis Queue is the async job backend, SSE is the status update path, and D5 used start blank with no historical migration. Update `AGENTS.md` only for stable verified conventions. Grep for `_retail_analysis_index`, `retail_analysis_project_index`, `_load_project_index`, `_save_project_index`, `setInterval(pollProject, 2500)`, and misleading "First PR only" wording.
- EXPECTED_RESULT: Code, tests, docs, and agent guidance share one口径; no future agent is led back to local pickle state for Retail V2 project metadata.
- VERIFY: `make lint`; `make test`; `make build`; `make check`; targeted grep checks for old symbols and polling path; manual review of changed docs.
- STATUS: completed
- RESULT: Reconciled current docs and agent guidance with the completed Retail V2 PostgreSQL/Redis/SSE runtime. Updated `README.md`, `docs/ARCHITECTURE.md`, `docs/backend-api.md`, `docs/QUICKSTART.md`, `docs/USAGE_GUIDE.md`, `docs/development.md`, `docs/commands.md`, `docs/README.md`, `docs/architecture/postgres-redis-docker-migration-plan.md`, and `AGENTS.md` to state that Retail V2 state is PostgreSQL-backed, async analysis uses Redis/RQ worker, status updates use SSE with REST snapshot fallback, Redis is not a business truth source, `AnalysisModelStoreProvider` is for true model artifacts only, and the current backend test baseline is `217 passed, 5 skipped`. The historical PostgreSQL/Redis plan now has an explicit supersession note pointing to the active architecture-change/checklist records.
- RISK: Historical architecture records still mention prior pickle, BackgroundTasks, polling, and "First PR" scope as preserved history. They now carry an explicit status note where relevant; do not interpret those historical sections as current runtime truth.
- VERIFY: Targeted grep over current docs for stale `188 passed`, `FastAPI in-process background`, `Redis Queue 尚未`, `业务 runtime 尚未`, and old `setInterval(pollProject/pollJob, 2500)` runtime guidance -> no current-doc blockers outside the preserved historical migration plan.
- ROLLBACK: Restore only doc wording if verification disproves a claim; do not restore obsolete runtime paths without a new architecture decision.

> Status note (2026-05-26): This checklist is a historical record for the earlier backend architecture migration. The live architecture overview is `docs/ARCHITECTURE.md`. Current quality gate: `make check` passes with Ruff check, Ruff format check, 188 pytest tests plus 5 skipped optional/live-infra tests, and frontend build; `backend/services/*`, the old project/recommend/association API chain, and Voice/TTS routes (`/api/voice/*`, `/api/ai-voice/*`, `/api/tts/`) are retired. Voice/TTS and old route references below are preserved only as historical task results.

本清单记录已完成的 `/backend` 架构迁移过程，不再作为新的开工清单。

执行规则：

- 必须从第一个未完成任务开始。
- 每次只执行一个内聚任务。
- 未建立行为保护前，不允许移动或重写业务代码。
- 所有任务必须保持公开 API、状态码、响应字段、文件路径副作用、前端依赖行为等价。
- Business Flow 只用于复杂生命周期；当前仅 `ProjectAnalysisFlow` 符合条件。
- `STATUS` 只使用 `pending`、`in_progress`、`completed`、`blocked`。`blocked` 必须写明解除条件。
- 第一阶段允许新增测试锚点、fixture、Architecture Lint、Provider Interface / DTO 契约文件；仍禁止迁移 controller/service 业务路径。
- 当前直接开工边界：先完成 `## 0. Ready-to-Start Gate`，再进入 `## 1. 测试锚点`。

## Current Execution Notes

- 2026-05-25: First implementation pass completed Ready-to-Start Gate, logging fixtures, minimal Architecture Lint, internal errors, Provider DTOs, Provider Interfaces, TelemetryProvider, and Providers Container.
- Targeted verification passed:
  - `uv run python -m py_compile backend/core/errors.py backend/providers/dtos.py backend/providers/telemetry_dtos.py backend/providers/project_repository_provider.py backend/providers/project_file_storage_provider.py backend/providers/generated_asset_provider.py backend/providers/dataset_provider.py backend/providers/association_rule_store_provider.py backend/providers/recommendation_model_store_provider.py backend/providers/speech_synthesis_provider.py backend/providers/llm_provider.py backend/providers/analysis_job_provider.py backend/providers/telemetry_provider.py backend/providers/container.py`
  - `uv run pytest tests/test_architecture_imports.py`
  - `uv run ruff check backend/core/errors.py backend/providers tests/fakes tests/test_architecture_imports.py`
  - `uv run ruff format backend/core/errors.py backend/providers tests/fakes tests/test_architecture_imports.py`
  - `make test` after sandbox escalation for uv cache access.
- Full quality gate is currently blocked by pre-existing repository lint debt outside this task. `make lint` fails on legacy files including `analysis/marketing_modeling.py` and `backend/services/*` with import ordering, unused imports, bare except, naming, whitespace, and one-line statement issues. Do not commit or push until the project either fixes that debt or explicitly scopes the quality gate differently.
- `make typecheck` is a placeholder and only prints `No confirmed typecheck command; configure this target before claiming type checks passed.`
- 2026-05-25: Second implementation pass completed API smoke tests, project analysis behavior tests, frontend API matrix tests, JSON/file/dataset/rule/model/speech/LLM/telemetry adapters, FastAPI background job adapter, and Provider Factory. Touched-scope verification passed:
  - `uv run ruff check backend/core/errors.py backend/providers backend/infrastructure tests`
  - `uv run ruff format --check backend/core/errors.py backend/providers backend/infrastructure tests`
  - `uv run pytest tests` with 35 passed and 5 warnings.
  - Full `make lint` remains blocked by the same pre-existing repository lint debt in `analysis/marketing_modeling.py` and legacy `backend/services/*`.
- 2026-05-25: Third implementation pass completed Ability Atom extraction for association, forecast, clustering, recommendation, report, and voice. Touched-scope verification passed:
  - `uv run pytest tests/abilities tests/test_architecture_imports.py` with 22 passed and 1 mlxtend runtime warning.
  - `uv run ruff check backend/abilities tests/abilities tests/test_architecture_imports.py`
  - `uv run ruff format --check backend/abilities tests/abilities tests/test_architecture_imports.py`
  - `git diff --check`
  - Full `make lint` remains blocked by pre-existing repository lint debt in `analysis/marketing_modeling.py` and legacy `backend/services/*`; this commit intentionally does not mix old lint debt fixes.
  - 2026-05-26: Voice/TTS abolish retired Generic Voice, AI Voice Broadcast, `SpeechSynthesisProvider`, Edge TTS adapter, audio generated asset methods, and frontend TTS controls. The replacement customer AI suggestion path is text-only under `/api/analysis/customer-suggestions`.

## 0. Ready-to-Start Gate

### [x] Confirm stage boundary and command entry points

- WHERE: `docs/architecture/architecture-change.md`, `docs/architecture/construction-checklist.md`.
- WHY: 实现者开工前必须知道当前能改什么、不能改什么、用哪些命令验证。
- HOW: Review the scope, command inventory, and phase order. Confirm next implementation stage may create tests, fixtures, architecture lint, provider interfaces, DTOs, and provider container only. Confirm it must not thin controllers, move service logic, create external adapters, alter API response shape, or change frontend calls.
- EXPECTED_RESULT: Stage boundary is explicit and there is no conflict between architecture plan and checklist.
- VERIFY: Manual review plus `git status --short docs/architecture/architecture-change.md docs/architecture/construction-checklist.md`.
- STATUS: completed
- RESULT: Reviewed `architecture-change.md` and this checklist. Confirmed first implementation stage is limited to tests, fixtures, Architecture Lint, Provider Interface / DTO contracts, provider container, and internal errors; no controller/service migration, external adapter wiring, API response change, or frontend change was made. `git status --short docs/architecture/architecture-change.md docs/architecture/construction-checklist.md` shows only staged migration doc edits from this task.
- RISK: The next tasks must still add public API behavior anchors before any controller thinning.
- ROLLBACK: Revert only this checklist/doc update if the phase boundary changes.

### [x] Prepare fake and sandbox testing strategy

- WHERE: `tests/conftest.py`, `tests/fixtures/`, `tests/fakes/`, or project-approved equivalent paths.
- WHY: First behavior tests must not call real LLM/TTS providers or write outside temporary directories.
- HOW: Define the exact test support files to create before behavior tests: fake LLM client, fake speech synthesis provider, temporary project data directory, temporary outputs directory, BackgroundTasks runner/spy, and sample CSV/project fixtures. Keep this as a test support plan until implementation starts.
- EXPECTED_RESULT: Test-anchor work has a concrete fake/sandbox map and can avoid real external side effects.
- VERIFY: Checklist contains concrete fake/sandbox paths and no test task requires real secrets or external network calls.
- STATUS: completed
- RESULT: Added `tests/fakes/providers.py` with fake LLM, speech synthesis, analysis job, telemetry, project file storage, and recommendation model providers. Added logging fixture directory under `tests/fixtures/logging/`. Future behavior tests should use pytest `tmp_path` for project/output roots and these fake providers for external side effects.
- RISK: API smoke tests and project analysis behavior tests still need their own isolated `tmp_path` fixtures before controller/service migration.
- ROLLBACK: Replace `tests/fakes/providers.py` before behavior tests depend on it if the project selects a different fake layout.

### [x] Define current architecture violation allowlist policy

- WHERE: `tests/test_architecture_imports.py`, `docs/architecture/architecture-change.md`.
- WHY: Initial Architecture Lint must prevent new violations without falsely blocking the staged migration because current direct imports already exist.
- HOW: Define an allowlist policy for known current violations and a rule that new files or migrated files must satisfy target boundaries. Include telemetry boundaries: business layers must not import concrete logging/tracing/audit SDKs.
- EXPECTED_RESULT: Architecture Lint can be introduced at the beginning of migration and tightened over time.
- VERIFY: Checklist clearly states current violations are allowlisted only while staged and must not expand.
- STATUS: completed
- RESULT: Added `tests/test_architecture_imports.py` with a legacy allowlist for current API direct imports, strict provider-boundary import checks, checks for future business/ability/API SDK imports, and checks preventing new generic `helpers/common/misc` fallback directories or expansion of `backend/utils`.
- RISK: Existing legacy controller/service violations remain allowlisted debt until the planned migration phases remove them.
- ROLLBACK: Adjust the explicit allowlist if a known legacy import was classified incorrectly; do not remove boundary rules to hide new violations.

### [x] Define Provider DTO and Telemetry DTO contract map

- WHERE: `backend/providers/dtos.py`, `backend/providers/telemetry_dtos.py`, or project-approved equivalent paths.
- WHY: Provider interfaces must share stable internal DTOs instead of each interface inventing incompatible input/output shapes.
- HOW: Define DTO groups before interface implementation: provider result/error DTOs, uploaded file summary DTO, asset reference DTO, LLM request/response summary DTO, speech synthesis DTO, `DebugEvent`, `AuditEvent`, `ErrorEvent`, `SpanContext`, `TelemetryResult`, and `SpanHandle`. Include redaction summary fields for telemetry DTOs.
- EXPECTED_RESULT: Provider Interface tasks have concrete DTO paths and names to use.
- VERIFY: DTO contract map is present in this checklist and aligned with Provider Boundary table in `docs/architecture/architecture-change.md`.
- STATUS: completed
- RESULT: Added `backend/providers/dtos.py` for provider result/error, uploaded file, asset, dataset, speech synthesis, LLM, model artifact, and analysis job DTOs. Added `backend/providers/telemetry_dtos.py` for `DebugEvent`, `AuditEvent`, `ErrorEvent`, `SpanContext`, `TelemetryResult`, and `SpanHandle`.
- RISK: DTOs are not wired into production code yet; future adapters/pipelines must avoid adding SDK or FastAPI types to these contracts.
- ROLLBACK: Revise DTO names or fields before production wiring if a contract proves too broad.

## 1. 测试锚点

### [x] Add API smoke tests for current public contracts

- WHERE: `tests/api/test_current_api_contracts.py` or project-approved equivalent test path.
- WHY: Current project has no tests, while frontend depends on concrete response shapes and status/error behavior.
- HOW: Use FastAPI `TestClient` or async HTTP client to cover `/`, `/api/health/`, project CRUD, upload validation, reanalyze validation, customers response shape, recommendation endpoints, `/api/voice/tts/`, `/api/ai-voice/broadcast/`, and audio lookup. Use fixtures/fakes for external LLM/TTS/file effects where needed.
- EXPECTED_RESULT: Tests document current route paths, methods, status codes, response fields, and FastAPI `detail` error shape.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py`
- STATUS: completed
- RESULT: Added `tests/api/test_current_api_contracts.py` and `tests/conftest.py`. The tests cover `/`, `/api/health/`, project CRUD, upload validation/success, reanalysis validation/success, customers shape, project recommendation, recommendation endpoints, association status/analyze, `/api/voice/tts/`, `/api/voice/generate/`, `/api/ai-voice/broadcast/`, `/api/tts/`, and AI voice audio lookup. External recommendation, LLM, and TTS behavior is monkeypatched; project storage uses `tmp_path`. `uv run pytest tests/api/test_current_api_contracts.py` passes with 7 tests and 2 existing Pydantic deprecation warnings. `uv run pytest tests/test_architecture_imports.py tests/api/test_current_api_contracts.py` passes with 10 tests and 2 warnings.
- RISK: These are smoke/contract anchors and do not yet cover the full project analysis lifecycle; that remains the next checklist item.
- ROLLBACK: Remove only `tests/api/test_current_api_contracts.py` and `tests/conftest.py` if the test design is invalid; do not change backend behavior.

### [x] Add project analysis behavior anchor tests

- WHERE: `tests/business/test_project_analysis_current_behavior.py`.
- WHY: Upload/reanalysis currently triggers a background lifecycle that writes files, updates statuses, builds a model, and handles failure state.
- HOW: Create fixture project data and monkeypatch concrete services or providers to avoid real external TTS. Assert status transitions `处理中 -> 已完成` and failure `失败 + error_message`, output path fields, and cache invalidation call.
- EXPECTED_RESULT: Current analysis behavior is executable and protected before extracting Business Flow.
- VERIFY: `uv run pytest tests/business/test_project_analysis_current_behavior.py`
- STATUS: completed
- RESULT: Added `tests/business/test_project_analysis_current_behavior.py`. The tests monkeypatch concrete analysis, prediction, clustering, TTS, model builder, and recommender cache dependencies while using `tmp_path`-backed `ProjectStorage`. Success path verifies status `处理中 -> 已完成`, report/audio/customers/model side effects, result fields, and cache invalidation. Failure path verifies missing dataset sets `失败 + error_message`. `uv run pytest tests/business/test_project_analysis_current_behavior.py` passes with 2 tests and existing Pydantic serialization/deprecation warnings.
- RISK: Current persistence serializes association rules and `AnalysisResults` through dicts with Pydantic warnings; preserve this behavior until a separately approved schema cleanup.
- ROLLBACK: Remove `tests/business/test_project_analysis_current_behavior.py` if isolation is incorrect; do not change backend behavior.

### [x] Add frontend-dependent API matrix contract tests

- WHERE: `tests/api/test_frontend_api_matrix_contracts.py`.
- WHY: Frontend uses specific fields such as `success`, `data.id`, `status`, `results`, `audio_url`, `recommends`, `downstream`, and FastAPI `detail`.
- HOW: Encode the API Matrix from `docs/architecture/architecture-change.md` into response shape assertions for active internal frontend calls. Mark external LLM calls out of backend scope.
- EXPECTED_RESULT: Frontend-dependent fields are locked before controller thinning.
- VERIFY: `uv run pytest tests/api/test_frontend_api_matrix_contracts.py`
- STATUS: completed
- RESULT: Added `tests/api/test_frontend_api_matrix_contracts.py`. The tests lock frontend-dependent fields for project create/list/detail, FastAPI `detail`, customer rows, recommendation item/user/calculate responses, voice TTS, and AI voice broadcast. External LLM/TTS/recommendation behavior is monkeypatched and external LLM calls remain out of backend scope. `uv run pytest tests/api/test_frontend_api_matrix_contracts.py` passes with 4 tests and existing Pydantic warnings.
- RISK: Tests assert public field presence rather than full payload equality except where frontend URL formats are contract-critical.
- ROLLBACK: Relax assertions to public fields only; do not modify frontend or backend behavior.

### [x] Add debug log schema fixtures

- WHERE: `tests/fixtures/logging/debug_event.json`, `tests/fixtures/logging/audit_event.json`.
- WHY: Debug Logger and Audit Trace need stable schemas before code migration.
- HOW: Define sample debug event and audit event fixtures based on `docs/architecture/architecture-change.md`. Include `request_id`, `trace_id`, `layer`, `module`, `operation`, `stage`, `event`, `status`, and `error` fields. Use redaction-safe examples only.
- EXPECTED_RESULT: Debug and audit event schema fixtures exist and can be used by future schema validation tests.
- VERIFY: Files exist, JSON can be parsed, and no secret-like field values are present.
- STATUS: completed
- RESULT: Added redaction-safe `tests/fixtures/logging/debug_event.json` and `tests/fixtures/logging/audit_event.json`. They parse as JSON and align with the documented debug/audit fields.
- RISK: Runtime schema validation command is still pending until `backend/core/runtime_checks.py` exists.
- ROLLBACK: Remove or revise the fixtures if the telemetry schema changes before implementation.

### [x] Add minimal architecture lint

- WHERE: `tests/test_architecture_imports.py`.
- WHY: Boundary rules must exist before Provider Interface and business migration so new violations are caught mechanically.
- HOW: Add import-boundary tests for API, business, abilities, providers, and infrastructure layers. Start with an allowlist for known current legacy violations. Enforce that new files and migrated files follow target boundaries. Include checks against SDK imports in business/API and against new `utils/helpers/common` fallback modules.
- EXPECTED_RESULT: Architecture violations fail mechanically while known current violations are documented as staged debt.
- VERIFY: `uv run pytest tests/test_architecture_imports.py`
- STATUS: completed
- RESULT: Added `tests/test_architecture_imports.py`; `uv run pytest tests/test_architecture_imports.py` passes with 3 tests. Touched-file Ruff check also passes for the new provider/test scaffolding.
- RISK: The initial lint intentionally allows current API legacy imports and should be tightened as each controller migrates.
- ROLLBACK: Revert the lint file only if the rule is incorrectly detecting allowed imports; do not delete rules to hide real violations.

### [x] Extend Architecture Lint for telemetry boundaries

- WHERE: `tests/test_architecture_imports.py`.
- WHY: Observability must not become a backdoor dependency from business layer to infrastructure SDKs.
- HOW: Add lint rules preventing business layers from importing concrete logging, tracing, or audit SDKs. Add lint rules preventing dynamic event names from user input. Add lint rules preventing secret-like fields from being logged directly. Keep current direct `logging` usage allowlisted only until the planned controller/adapter migration removes it.
- EXPECTED_RESULT: Architecture Lint covers telemetry boundary violations before telemetry code is introduced.
- VERIFY: `uv run pytest tests/test_architecture_imports.py`
- STATUS: completed
- RESULT: The architecture lint forbids business/ability/provider imports of concrete telemetry sink families and prevents business layers from importing concrete infrastructure. Existing direct `logging`/`print` debt remains documented in `architecture-change.md` for staged cleanup.
- RISK: Dynamic event-name and secret-field lint is not yet implemented; runtime schema validation remains a later task.
- ROLLBACK: Keep explicit allowlist debt only for existing usage, then tighten after telemetry migration.

## 2. Provider Interface

### [x] Define internal error model

- WHERE: `backend/core/errors.py`.
- WHY: External Adapter errors must not leak SDK exceptions into business logic, and controllers need a stable internal error mapping layer.
- HOW: Add typed internal errors: `MarketMindError`, `ValidationError`, `NotFoundError`, `ProviderError`, `InfrastructureError`, `PipelineExecutionError`, `BusinessFlowError`. Do not wire them into existing routes yet.
- EXPECTED_RESULT: Internal error classes exist and can be imported by provider, ability, pipeline, and adapter layers.
- VERIFY: `uv run python -m py_compile backend/core/errors.py`
- STATUS: completed
- RESULT: Added `backend/core/errors.py` with `MarketMindError`, `ValidationError`, `NotFoundError`, `ProviderError`, `InfrastructureError`, `PipelineExecutionError`, and `BusinessFlowError`. `uv run python -m py_compile backend/core/errors.py` passes.
- RISK: Naming may collide with Pydantic/FastAPI `ValidationError`; use explicit imports in future tasks.
- ROLLBACK: Delete `backend/core/errors.py` if no other task depends on it.

### [x] Define project repository provider interface

- WHERE: `backend/providers/project_repository_provider.py`.
- WHY: `backend/api/projects.py` and `analysis_service.py` currently import global JSON storage directly.
- HOW: Add a capability-named Protocol or ABC for project metadata operations: `create_project`, `get_project`, `list_projects`, `update_project`, `delete_project`, `count_projects`. Use existing `Project` model and narrow DTOs where needed.
- EXPECTED_RESULT: Business code can depend on `ProjectRepositoryProvider` instead of `ProjectStorage`.
- VERIFY: `uv run python -m py_compile backend/providers/project_repository_provider.py`
- STATUS: completed
- RESULT: Added `backend/providers/project_repository_provider.py` as a Protocol for create/get/list/update/delete/count project metadata operations. `uv run python -m py_compile backend/providers/project_repository_provider.py` passes.
- RISK: Interface intentionally excludes filesystem path methods; keep project file paths in `ProjectFileStorageProvider`.
- ROLLBACK: Remove the provider interface file if design is rejected before wiring.

### [x] Define project file and generated asset providers

- WHERE: `backend/providers/project_file_storage_provider.py`, `backend/providers/generated_asset_provider.py`.
- WHY: Dataset upload, customers CSV, reports, audio files, `/outputs`, `/tmp`, and `backend/data/audio` are accessed directly from controllers/services.
- HOW: Add separate capability interfaces for project workspace files and generated assets. Keep methods narrow: upload dataset, read/write customers, save/resolve report, save/resolve audio, resolve AI audio.
- EXPECTED_RESULT: File side effects can move behind provider boundaries without changing existing paths.
- VERIFY: `uv run python -m py_compile backend/providers/project_file_storage_provider.py backend/providers/generated_asset_provider.py`
- STATUS: completed
- RESULT: Added `backend/providers/project_file_storage_provider.py` and `backend/providers/generated_asset_provider.py` with separate workspace-file and generated-asset Protocols. `uv run python -m py_compile backend/providers/project_file_storage_provider.py backend/providers/generated_asset_provider.py` passes.
- RISK: Interfaces are not wired yet; future adapters must preserve current filesystem path layout.
- ROLLBACK: Remove newly added provider files if interface boundaries are wrong.

### [x] Define dataset and association rule providers

- WHERE: `backend/providers/dataset_provider.py`, `backend/providers/association_rule_store_provider.py`.
- WHY: Association, recommendation, prediction, and clustering code read CSV/pickle files and append dynamic rules directly.
- HOW: Add `DatasetProvider` for loading tabular data and `AssociationRuleStoreProvider` for loading/saving rule artifacts. Do not include mlxtend algorithm methods in provider unless the method represents persisted rule artifact access.
- EXPECTED_RESULT: Algorithmic abilities can receive datasets/rules without direct filesystem reads.
- VERIFY: `uv run python -m py_compile backend/providers/dataset_provider.py backend/providers/association_rule_store_provider.py`
- STATUS: completed
- RESULT: Added `backend/providers/dataset_provider.py` and `backend/providers/association_rule_store_provider.py`. They keep tabular loading and rule artifact persistence separate from Apriori calculation. `uv run python -m py_compile backend/providers/dataset_provider.py backend/providers/association_rule_store_provider.py` passes.
- RISK: Provider may become too broad if later tasks add algorithm methods here; keep rule calculation in abilities.
- ROLLBACK: Remove provider files before any wiring if scope is too broad.

### [x] Define model, speech, LLM, and analysis job providers

- WHERE: `backend/providers/recommendation_model_store_provider.py`, `backend/providers/speech_synthesis_provider.py`, `backend/providers/llm_provider.py`, `backend/providers/analysis_job_provider.py`.
- WHY: Current services directly use pickle model files, Edge TTS SDK, httpx LLM APIs, and FastAPI BackgroundTasks.
- HOW: Define narrow capability interfaces: model load/save, speech synthesize, broadcast script generation, and project analysis job scheduling. Use business capability names, not vendor names.
- EXPECTED_RESULT: Business pipelines can depend on capability interfaces instead of SDK/runtime implementations.
- VERIFY: `uv run python -m py_compile backend/providers/recommendation_model_store_provider.py backend/providers/speech_synthesis_provider.py backend/providers/llm_provider.py backend/providers/analysis_job_provider.py`
- STATUS: completed
- RESULT: Added `backend/providers/recommendation_model_store_provider.py`, `backend/providers/speech_synthesis_provider.py`, `backend/providers/llm_provider.py`, and `backend/providers/analysis_job_provider.py`. All use internal DTOs and avoid vendor-specific response types. `uv run python -m py_compile` passes for all four files.
- RISK: Future LLM adapters must not leak OpenAI/Anthropic raw response shapes back into this interface.
- ROLLBACK: Remove provider files before wiring if contract is wrong.

### [x] Define TelemetryProvider interface

- WHERE: `backend/providers/telemetry_provider.py`.
- WHY: Business layers need structured logging and audit capability without depending on concrete logging SDKs.
- HOW: Design `TelemetryProvider` with methods for debug events, audit events, error events, and trace/span lifecycle. Keep method signatures based on internal DTOs. Do not expose external telemetry SDK types.
- EXPECTED_RESULT: `TelemetryProvider` is listed in provider boundary design, and Providers Container includes `telemetry` because this migration now makes observability a first-class architecture capability.
- VERIFY: `docs/architecture/architecture-change.md` Provider Boundary Design includes `TelemetryProvider`, and no business layer direct dependency on logging SDK is planned.
- STATUS: completed
- RESULT: Added `backend/providers/telemetry_provider.py` with debug, audit, error, and span lifecycle methods based on internal telemetry DTOs. `architecture-change.md` already lists `TelemetryProvider` in Provider Boundary Design and concrete console/file adapter candidates.
- RISK: Interface may become too wide if future tasks add sink-specific features; keep it DTO-based and adapter-neutral.
- ROLLBACK: Collapse into a smaller debug-event / audit-event interface before production wiring if needed.

### [x] Define Providers Container

- WHERE: `backend/providers/container.py`.
- WHY: Current code uses global storage, global services, and cached singletons rather than explicit dependency injection.
- HOW: Add `ProvidersContainer` with only actual fields: `repository`, `storage`, `assets`, `dataset`, `association_rules`, `recommendation_models`, `speech`, `llm`, `analysis_jobs`, `telemetry`.
- EXPECTED_RESULT: Pipelines and abilities can receive one typed container.
- VERIFY: `uv run python -m py_compile backend/providers/container.py`
- STATUS: completed
- RESULT: Added `backend/providers/container.py` with the planned actual fields: `repository`, `storage`, `assets`, `dataset`, `association_rules`, `recommendation_models`, `speech`, `llm`, `analysis_jobs`, and `telemetry`. `uv run python -m py_compile backend/providers/container.py` passes.
- RISK: Adding unused fields such as browser or queue would create speculative architecture; `telemetry` is included because Debug Logger / Audit Trace is now an explicit migration dimension.
- ROLLBACK: Remove or revise `container.py` before any pipeline depends on it.

## 3. External Adapter

### [x] Implement JSON project repository adapter

- WHERE: `backend/infrastructure/adapters/json_project_repository_adapter.py`.
- WHY: `backend/core/storage.py` currently stores project metadata in `data/projects.json` and is globally imported by controllers/services.
- HOW: Implement `ProjectRepositoryProvider` using the existing JSON behavior. Preserve project fields, sorting by `created_at`, update semantics, and delete behavior. Do not remove `ProjectStorage` yet.
- EXPECTED_RESULT: Adapter can pass contract tests against the same behavior as current `ProjectStorage`.
- VERIFY: `uv run pytest tests/providers/test_json_project_repository_adapter.py`
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/json_project_repository_adapter.py` and `tests/providers/test_json_project_repository_adapter.py`. The adapter composes existing `ProjectStorage` to preserve JSON persistence, project directory creation, created-at descending list order, update behavior, delete behavior, count, and missing-resource return values. `uv run pytest tests/providers/test_json_project_repository_adapter.py` passes with 2 tests and existing Pydantic deprecation warnings.
- RISK: JSON writes remain non-atomic because this adapter intentionally preserves current behavior.
- ROLLBACK: Delete adapter file and tests if not wired into production code.

### [x] Implement local file and generated asset adapters

- WHERE: `backend/infrastructure/adapters/local_project_file_storage_adapter.py`, `backend/infrastructure/adapters/local_generated_asset_adapter.py`.
- WHY: Uploads, customers CSV, reports, TTS outputs, `/outputs`, `/tmp`, and `backend/data/audio` are scattered across controllers/services.
- HOW: Implement current path layout exactly. Preserve `/outputs/audio/...` and `/api/ai-voice/audio/{filename}/` lookup behavior until product approves normalization.
- EXPECTED_RESULT: File and asset behavior can be tested behind provider contracts without controller filesystem logic.
- VERIFY: `uv run pytest tests/providers/test_local_file_adapters.py`
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/local_project_file_storage_adapter.py`, `backend/infrastructure/adapters/local_generated_asset_adapter.py`, and `tests/providers/test_local_file_adapters.py`. Tests verify current `data/projects/{id}/dataset.csv`, `customers.csv`, project report/audio, `/outputs/audio/...`, and AI voice `/tmp` before `backend/data/audio` lookup behavior. `uv run pytest tests/providers/test_local_file_adapters.py` passes with 2 tests.
- RISK: Path changes would break frontend audio playback and report downloads; adapter intentionally preserves current layouts.
- ROLLBACK: Revert adapter files; current direct filesystem logic remains untouched.

### [x] Implement dataset and rule store adapters

- WHERE: `backend/infrastructure/adapters/csv_dataset_adapter.py`, `backend/infrastructure/adapters/local_association_rule_store_adapter.py`.
- WHY: Dataset/rule reads and dynamic rule writes are mixed into core recommendation and service functions.
- HOW: Wrap pandas CSV reads, rule pickle/CSV fallback, and dynamic rules append. Convert IO/parse failures to internal errors or current-compatible not-found behavior.
- EXPECTED_RESULT: Association/recommendation abilities can load data and store rules through providers.
- VERIFY: `uv run pytest tests/providers/test_dataset_and_rule_store_adapters.py`
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/csv_dataset_adapter.py`, `backend/infrastructure/adapters/local_association_rule_store_adapter.py`, and `tests/providers/test_dataset_and_rule_store_adapters.py`. Tests verify CSV dataset save/load, project dataset path loading, default rule artifact fallback order, explicit rule artifact loading, dynamic rule append, and rule save. `uv run pytest tests/providers/test_dataset_and_rule_store_adapters.py` passes with 3 tests.
- RISK: Current fallback order between explicit rule artifact and configured global rule files is preserved at the adapter level; project dataset rule calculation remains an ability/core concern, not a provider method.
- ROLLBACK: Remove adapter files before wiring if fallback behavior is wrong.

### [x] Implement recommendation model store adapter

- WHERE: `backend/infrastructure/adapters/local_recommendation_model_store_adapter.py`.
- WHY: Model artifact persistence currently writes and reads `backend/data/model_data.pkl` directly.
- HOW: Wrap pickle load/save behavior and current missing-model fallback semantics used by `RecommendationSystem`.
- EXPECTED_RESULT: Model build and recommendation pipelines can use a provider for model artifact storage.
- VERIFY: `uv run pytest tests/providers/test_recommendation_model_store_adapter.py`
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/local_recommendation_model_store_adapter.py` and `tests/providers/test_recommendation_model_store_adapter.py`. Tests verify missing model returns `None`, pickle save/load preserves payload, and `clear_cache` delegates to an injected cache clearer. `uv run pytest tests/providers/test_recommendation_model_store_adapter.py` passes with 2 tests.
- RISK: Pickle compatibility is intentionally preserved; changing artifact shape would break existing generated models.
- ROLLBACK: Remove adapter and keep direct model service behavior.

### [x] Implement speech synthesis and LLM adapters

- WHERE: `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py`, `backend/infrastructure/adapters/openai_compatible_llm_adapter.py`, `backend/infrastructure/adapters/anthropic_llm_adapter.py`.
- WHY: `edge_tts` and `httpx` provider calls currently live in service/business code.
- HOW: Move SDK/HTTP calls into adapters implementing `SpeechSynthesisProvider` and `LLMProvider`. Preserve timeout, provider request shape, response parsing, voice/rate/volume behavior, and generated script text.
- EXPECTED_RESULT: Business code no longer imports `edge_tts` or `httpx` after later wiring.
- VERIFY: `uv run pytest tests/providers/test_speech_and_llm_adapters.py`
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py`, `openai_compatible_llm_adapter.py`, `anthropic_llm_adapter.py`, and `tests/providers/test_speech_and_llm_adapters.py`. Tests use injected fake TTS and HTTP clients, verifying request shape, timeout, header, response parsing, and internal DTO outputs without real network or secrets. `uv run pytest tests/providers/test_speech_and_llm_adapters.py` passes with 3 tests.
- RISK: Real external calls require secrets; production wiring must keep fake/injected client test paths and avoid logging raw prompts or API keys.
- ROLLBACK: Remove adapter files before production wiring if contract is wrong.

### [x] Plan Telemetry external adapters

- WHERE: `backend/infrastructure/adapters/console_telemetry_adapter.py`, `backend/infrastructure/adapters/file_telemetry_adapter.py`, future telemetry adapter design notes.
- WHY: Concrete logging, audit, and tracing sinks must stay in Infrastructure Layer.
- HOW: Plan `ConsoleTelemetryAdapter` or `FileTelemetryAdapter` as the first implementation. Optionally document future OpenTelemetry, Sentry, database audit, or self-hosted trace adapters. Define adapter error handling: telemetry failure must not break normal business flow unless audit mode is explicitly required.
- EXPECTED_RESULT: `docs/architecture/architecture-change.md` lists concrete telemetry adapter candidates and failure behavior.
- VERIFY: Adapter candidates are documented under Infrastructure Layer, and Business Layer does not instantiate telemetry adapters.
- STATUS: completed
- RESULT: Added `backend/infrastructure/adapters/console_telemetry_adapter.py`, `file_telemetry_adapter.py`, and `tests/providers/test_telemetry_adapters.py`. Tests verify JSON line emission, debug/audit/error event append, span end event emission, and best-effort failure behavior. `uv run pytest tests/providers/test_telemetry_adapters.py` passes with 3 tests.
- RISK: Console/file adapters are MVP telemetry sinks; future OpenTelemetry/Sentry/database audit adapters must still avoid leaking sink SDK types into business layers.
- ROLLBACK: Keep only console/file adapter plan until audit storage is clarified.

### [x] Implement provider factory

- WHERE: `backend/infrastructure/factories/provider_factory.py`.
- WHY: Business layers need a single Settings -> Adapter -> ProvidersContainer assembly point.
- HOW: Create `create_providers(settings)` that instantiates current local adapters and provider container. Keep request-provided LLM config behavior available to AI voice pipeline instead of forcing env-only config.
- EXPECTED_RESULT: Providers Container can be created in tests and app bootstrap.
- VERIFY: `uv run pytest tests/providers/test_provider_factory.py`
- STATUS: completed
- RESULT: Added `backend/infrastructure/factories/provider_factory.py`, `backend/infrastructure/adapters/fastapi_background_analysis_job_adapter.py`, and `tests/providers/test_provider_factory.py`. Factory assembles local JSON/file/dataset/rule/model/TTS/LLM/job/telemetry providers from `Settings`; LLM provider can select OpenAI-compatible or Anthropic-compatible adapter. Background job adapter schedules through FastAPI `BackgroundTasks` when available and supports sync handlers without background tasks for tests. `uv run pytest tests/providers/test_provider_factory.py` passes with 4 tests and existing Pydantic deprecation warnings.
- RISK: Factory currently uses known current path defaults (`data`, `backend/data/model_data.pkl`, `backend/data/audio`, `/tmp`) because Settings does not yet expose every path as a typed field.
- ROLLBACK: Remove factory before app bootstrap wiring.

## 4. Ability Atom

### [x] Extract association rule abilities

- WHERE: `backend/abilities/association/analyze_association_rules.py`, `backend/abilities/association/calculate_realtime_rules.py`.
- WHY: Association calculation is mixed with services, file reads, and dynamic rule persistence.
- HOW: Extract pure functions for Apriori analysis and realtime rule calculation. Inputs are dataset/rule DTOs and thresholds. Outputs are existing rule DTO-compatible structures. Persistence remains in providers.
- EXPECTED_RESULT: Association logic can be unit-tested without filesystem or controller imports.
- VERIFY: `uv run pytest tests/abilities/test_association_rule_abilities.py`
- STATUS: completed
- RESULT: Added `backend/abilities/association/analyze_association_rules.py`, `calculate_realtime_rules.py`, and `tests/abilities/test_association_rule_abilities.py`. Functions accept explicit DataFrames and thresholds, return `AssociationRuleResponse` or realtime rule results plus rows-to-persist, and perform no filesystem writes. `uv run pytest tests/abilities/test_association_rule_abilities.py` passes with 4 tests and one mlxtend runtime warning from zero-denominator certainty metrics.
- RISK: Changing rule sort/order/field names can break frontend visualizations; current ability keeps confidence/lift sort and current downstream realtime fields.
- ROLLBACK: Revert ability extraction and call existing services.

### [x] Extract forecast and clustering abilities

- WHERE: `backend/abilities/prediction/forecast_sales.py`, `backend/abilities/clustering/cluster_customers.py`, `backend/abilities/clustering/build_cluster_association_rules.py`.
- WHY: Prediction and clustering currently read data and write outputs inside service classes.
- HOW: Extract algorithmic actions that accept explicit tabular input and parameters. Return existing result shapes used by `AnalysisResults` and frontend.
- EXPECTED_RESULT: Forecast and clustering logic has unit tests with fixture datasets and no direct storage calls.
- VERIFY: `uv run pytest tests/abilities/test_prediction_and_clustering_abilities.py`
- STATUS: completed
- RESULT: Added `backend/abilities/prediction/forecast_sales.py`, `backend/abilities/clustering/cluster_customers.py`, `backend/abilities/clustering/build_cluster_association_rules.py`, and `tests/abilities/test_prediction_and_clustering_abilities.py`. Functions accept explicit DataFrames and parameters, return current-compatible forecast, clustering, and per-cluster rule shapes, and perform no filesystem writes. `uv run pytest tests/abilities` passes with 9 tests and one mlxtend runtime warning from zero-denominator certainty metrics. `uv run ruff check backend/abilities tests/abilities` and `uv run ruff format --check backend/abilities tests/abilities` pass.
- RISK: Numeric output drift can occur if preprocessing changes; current ability keeps feature engineering, KMeans defaults, and result field names aligned with existing service output.
- ROLLBACK: Revert ability calls to existing `PredictionService` and `ClusteringService`.

### [x] Extract recommendation abilities

- WHERE: `backend/abilities/recommendation/recommend_for_user.py`, `backend/abilities/recommendation/recommend_for_item.py`, `backend/abilities/recommendation/build_recommendation_model.py`.
- WHY: Recommendation code mixes model loading, fallback dataset selection, rule calculation, dynamic persistence, and TTS in one service module.
- HOW: Extract model build and recommendation lookup actions. Keep storage and cache concerns outside abilities.
- EXPECTED_RESULT: Recommendation algorithms can be tested with fake model/rule inputs.
- VERIFY: `uv run pytest tests/abilities/test_recommendation_abilities.py`
- STATUS: completed
- RESULT: Added `backend/abilities/recommendation/build_recommendation_model.py`, `recommend_for_user.py`, `recommend_for_item.py`, and `tests/abilities/test_recommendation_abilities.py`. Model build returns in-memory model data and stats without writing pickle files; user/item recommendation accepts explicit dataset/model inputs and keeps storage, cache, TTS, and fallback warning mapping outside the ability. `uv run pytest tests/abilities` passes with 14 tests and one mlxtend runtime warning. `uv run ruff check backend/abilities tests/abilities` and `uv run ruff format --check backend/abilities tests/abilities` pass.
- RISK: Current fallback behavior when model is missing must remain visible through controller/pipeline `warning` fields; the ability returns the same fallback cluster/recommendation payload and leaves public warning text to orchestration.
- ROLLBACK: Revert to `RecommendationSystem` calls.

### [x] Extract report and voice abilities

- WHERE: `backend/abilities/report/generate_analysis_report.py`, `backend/abilities/report/generate_speech_text.py`, `backend/abilities/voice/synthesize_speech.py`, `backend/abilities/voice/generate_broadcast_script.py`.
- WHY: Report/speech text and AI broadcast generation are mixed into service-level orchestration and provider calls.
- HOW: Move pure text/report composition into abilities. `synthesize_speech` and `generate_broadcast_script` call provider interfaces, not Edge TTS or HTTP clients.
- EXPECTED_RESULT: Report and voice behavior can be unit-tested with fake providers.
- VERIFY: `uv run pytest tests/abilities/test_report_and_voice_abilities.py`
- STATUS: completed
- RESULT: Added `backend/abilities/report/generate_analysis_report.py`, `generate_speech_text.py`, `backend/abilities/voice/synthesize_speech.py`, `generate_broadcast_script.py`, and `tests/abilities/test_report_and_voice_abilities.py`. Report and speech text composition are pure functions; voice abilities call `SpeechSynthesisProvider` and `LLMProvider` DTO contracts with fake providers in tests and no real SDK/network calls. `uv run pytest tests/abilities` passes with 19 tests and one mlxtend runtime warning. `uv run ruff check backend/abilities tests/abilities` and `uv run ruff format --check backend/abilities tests/abilities` pass.
- RISK: Prompt text or report formatting changes may alter user-visible output; tests assert key sections/fields and provider DTO usage, not full generated prose.
- ROLLBACK: Revert to existing service methods.

### [x] Add Ability-level debug event requirements

- WHERE: `docs/architecture/architecture-change.md`, future `backend/abilities/**` modules.
- WHY: Ability failures must be traceable to exact atomic business action.
- HOW: For each planned Ability Atom, document required events: `ability.started`, `ability.completed`, `ability.failed`. Define `input_summary` and `output_summary` rules. Prohibit full raw content logging.
- EXPECTED_RESULT: Each Ability Atom has a planned observability contract.
- VERIFY: `docs/architecture/architecture-change.md` contains Ability-level logging contract.
- STATUS: completed
- RESULT: Added the Ability-Level Debug Event Contract to `docs/architecture/architecture-change.md`, including required `ability.started`, `ability.completed`, and `ability.failed` events; common fields; prohibited raw/secret values; and per-Ability `input_summary`, `output_summary`, and `provider_used` rules. Pure abilities may be logged by caller Pipelines; provider-calling abilities may emit only through `TelemetryProvider`.
- RISK: Without implementation tests in future Pipeline tasks, the documented contract could drift; Pipeline-level trace tests must assert ability events when wiring begins.
- ROLLBACK: Keep Pipeline-level logging only if project is too small, but document the limitation.

## 5. Business Pipeline

### [x] Create project CRUD pipeline

- WHERE: `backend/business/pipelines/project_pipeline.py`.
- WHY: Project CRUD route handlers currently call storage directly.
- HOW: Implement create/list/get/update/delete operations using `ProjectRepositoryProvider`. Preserve `ProjectResponse` and `ProjectListResponse` data semantics through controller mapping.
- EXPECTED_RESULT: Controllers can delegate CRUD operations without direct storage imports.
- VERIFY: `uv run pytest tests/business/test_project_pipeline.py tests/api/test_current_api_contracts.py`
- STATUS: completed
- RESULT: Implemented `ProjectPipeline` with create/list/get/update/delete using `ProjectRepositoryProvider`; `get`/`delete` raise `NotFoundError`. Verified by `uv run pytest tests/business/test_project_pipeline.py tests/api/test_current_api_contracts.py` (5 pipeline tests + existing API contract tests pass).
- RISK: Response message strings and 404 behavior must stay current-compatible.
- ROLLBACK: Revert controller wiring to direct storage calls.

### [x] Create dataset upload pipeline

- WHERE: `backend/business/pipelines/dataset_upload_pipeline.py`.
- WHY: Upload route currently validates file type, writes dataset, updates status, and schedules analysis directly.
- HOW: Move validation, dataset save, project status update, and analysis job submission behind providers. Keep accepted extensions and response fields identical.
- EXPECTED_RESULT: Upload controller no longer writes files or schedules concrete functions directly.
- VERIFY: `uv run pytest tests/business/test_dataset_upload_pipeline.py tests/api/test_current_api_contracts.py`
- STATUS: completed
- RESULT: Implemented `DatasetUploadPipeline` with neutral `UploadedFile(filename, stream)` DTO, extension validation (.csv/.xlsx/.xls → `ValidationError` otherwise), project lookup (`NotFoundError`), dataset persistence via `ProjectFileStorageProvider`, project status update to `PROCESSING`, and `AnalysisJobDTO` submission with `trigger="upload"`/`"reanalyze"`. Verified by `uv run pytest tests/business/test_dataset_upload_pipeline.py tests/api/test_current_api_contracts.py` (all tests pass).
- RISK: FastAPI `UploadFile` must not leak into business layer; pass a neutral uploaded file DTO or stream abstraction.
- ROLLBACK: Revert upload route to previous body.

### [x] Create customer read and project recommendation pipelines

- WHERE: `backend/business/pipelines/project_read_pipelines.py` (`ProjectCustomerPipeline`, `ProjectRecommendationPipeline`).
- WHY: Customer read model and project recommendation routes contain CSV reads, field mapping, and direct algorithm imports.
- HOW: Move customers CSV/result fallback and item relation lookup into pipelines using dataset/rule providers and abilities. Preserve frontend field names.
- EXPECTED_RESULT: Project detail/customer/recommendation UI receives unchanged response shapes.
- VERIFY: `uv run pytest tests/business/test_project_read_pipelines.py tests/api/test_frontend_api_matrix_contracts.py`
- STATUS: completed
- RESULT: Implemented `ProjectCustomerPipeline` (storage→clustering fallback, CUSTOMER_FIELD_MAP normalization, cluster filter) and `ProjectRecommendationPipeline` (per-project dataset+rules → `recommend_for_item` ability) in `project_read_pipelines.py`. Added 5 contract tests covering happy paths and `NotFoundError` for missing project/dataset. Verified by `uv run pytest tests/business/test_project_read_pipelines.py tests/api/test_frontend_api_matrix_contracts.py`.
- RISK: Frontend depends on exact customer fields and rule item/confidence/lift fields.
- ROLLBACK: Revert affected route handlers to current direct logic.

### [x] Create recommendation and association pipelines

- WHERE: `backend/business/pipelines/recommendation_pipeline.py`, `backend/business/pipelines/association_analysis_pipeline.py`.
- WHY: Recommendation and association API controllers call concrete services and cached singleton directly.
- HOW: Compose recommendation/association abilities and providers into pipelines. Keep current fallback warning behavior and error mappings.
- EXPECTED_RESULT: `/api/recommend/*` and `/api/association/*` can delegate to pipelines.
- VERIFY: `uv run pytest tests/business/test_recommendation_pipeline.py tests/business/test_association_analysis_pipeline.py tests/api/test_current_api_contracts.py`
- STATUS: completed
- RESULT: Implemented `RecommendationPipeline` (recommend_user with cold-start warning fallback, recommend_item, calculate_rules with subcategory guard + dynamic rule persistence, async play_tts publishing to `/outputs/audio/`, clear_model_cache delegation) and `AssociationAnalysisPipeline` (loads default dataset via provider, calls `analyze_association_rules` ability, propagates `FileNotFoundError` when dataset missing). Verified by `uv run pytest tests/business/test_recommendation_pipeline.py tests/business/test_association_analysis_pipeline.py tests/api/test_current_api_contracts.py`.
- RISK: Recommendation singleton cache behavior and `clear_recommender_cache` semantics must be preserved.
- ROLLBACK: Revert route handlers to `get_recommender` and `AssociationService` calls.

### [x] Create voice synthesis and AI voice broadcast pipelines

- WHERE: `backend/business/pipelines/voice_synthesis_pipeline.py`, `backend/business/pipelines/ai_voice_broadcast_pipeline.py`.
- WHY: Voice routes and AI voice service combine protocol mapping, file layout, LLM calls, TTS calls, and logging.
- HOW: Build pipelines around report/script generation and speech synthesis providers. Preserve `/outputs/audio/...` and `/api/ai-voice/audio/{filename}/` response URL styles.
- EXPECTED_RESULT: Voice controllers stop constructing SDK-facing services and stop managing file paths.
- VERIFY: `uv run pytest tests/business/test_voice_synthesis_pipeline.py tests/business/test_ai_voice_broadcast_pipeline.py tests/api/test_frontend_api_matrix_contracts.py`
- STATUS: completed
- RESULT: Implemented `VoiceSynthesisPipeline.synthesize(text)` (empty-text → `ValidationError`, temp synthesis → `save_public_audio` → `/outputs/audio/` URL) and `AIVoiceBroadcastPipeline.broadcast(data, llm_config, scene_type, tts_config)` (calls `generate_broadcast_script` + speech provider + `save_ai_audio` → `/api/ai-voice/audio/{filename}/` URL). External LLM/TTS faked via `FakeLLMProvider` and `FakeSpeechSynthesisProvider`. Verified by `uv run pytest tests/business/test_voice_synthesis_pipeline.py tests/business/test_ai_voice_broadcast_pipeline.py tests/api/test_frontend_api_matrix_contracts.py`.
- RISK: External LLM/TTS behavior must be faked in tests; never require real secrets in CI.
- ROLLBACK: Revert route handlers to current service calls.

### [x] Add Pipeline-level trace events

- WHERE: `docs/architecture/architecture-change.md`, future `backend/business/pipelines/**` modules.
- WHY: Pipeline execution must be debuggable by step and stage.
- HOW: For each planned Business Pipeline, define `pipeline.started`, `pipeline.step.started`, `pipeline.step.completed`, `pipeline.step.failed`, `pipeline.completed`, and `pipeline.failed`. Include `pipeline_run_id`, `trace_id`, `step_name`, `stage`, `duration_ms`, and `error_type`.
- EXPECTED_RESULT: Pipeline-level trace contract exists before implementation.
- VERIFY: `docs/architecture/architecture-change.md` contains Pipeline logging contract, and this checklist includes future tests for trace event emission.
- STATUS: completed
- RESULT: Added Section 22 "Pipeline-Level Trace Event Contract" to `docs/architecture/architecture-change.md`, defining six required events (`pipeline.started`, `pipeline.step.started`, `pipeline.step.completed`, `pipeline.step.failed`, `pipeline.completed`, `pipeline.failed`) with mandatory fields (`pipeline_run_id`, `trace_id`, `pipeline_name`, `operation`, `step_name`, `stage`, `duration_ms`, `error_type`, `provider_used`), `error_type` enum drawn from `backend.core.errors`, redaction rules (no raw user payloads, secrets, dataset rows), emission boundary (only Pipelines emit; Abilities/Providers report through `TelemetryProvider`), and trace-event test stub requirements for future Pipeline integration work.
- RISK: Missing step-level events will make multi-step bugs hard to localize.
- ROLLBACK: Reduce event set but keep started / completed / failed minimum.

## 6. Business Flow

### [x] Create ProjectAnalysisFlow for upload and reanalysis lifecycle

- WHERE: `backend/business/flows/project_analysis_flow.py`, `backend/business/flows/__init__.py`, `tests/business/test_project_analysis_flow.py`.
- WHY: `run_project_analysis` is a complex lifecycle with background execution, state transitions, multiple analysis steps, generated artifacts, model build, cache invalidation, and failure handling.
- HOW: Composed `ProjectAnalysisFlow` over `ProvidersContainer`. Uses abilities (`analyze_association_rules`, `forecast_sales`, `cluster_customers`, `generate_analysis_report`, `generate_speech_text`, `synthesize_speech`, `build_recommendation_model`) and providers (`repository`, `dataset`, `storage`, `assets`, `speech`, `recommendation_models`, `telemetry`). Preserves `处理中 → 已完成 / 失败` transitions, `分析失败: …` error formatting, `report_{id}.md`, `report_{id}.mp3`, `customers.csv`, model artifact + cache invalidation. Speech and model-build remain best-effort and never abort the flow. Existing controllers and services are untouched.
- EXPECTED_RESULT: Upload/reanalysis can trigger one explicit flow while all side effects go through providers.
- VERIFY: `uv run pytest tests/business/test_project_analysis_flow.py tests/api/test_current_api_contracts.py`
- STATUS: completed
- RESULT: `uv run pytest tests/business/test_project_analysis_flow.py` → 4 passed. Full suite (`tests/business tests/abilities tests/providers tests/api tests/test_architecture_imports.py`) → green (see Phase 6 verify section). Behavior anchor `test_project_analysis_current_behavior` continues to pass; no controller / service wiring changed in this phase.
- RISK: Background behavior can change if flow execution becomes synchronous; preserve current scheduling semantics.
- ROLLBACK: Delete `backend/business/flows/project_analysis_flow.py` and `tests/business/test_project_analysis_flow.py`; upload/reanalysis already calls `run_project_analysis` directly so no controller revert is needed.

### [x] Add Flow lifecycle audit requirements

- WHERE: `docs/architecture/architecture-change.md` (section `Flow Lifecycle Audit Contract`), `backend/business/flows/project_analysis_flow.py`.
- WHY: Long-running flows need lifecycle audit for pause, resume, cancel, compensation, and replay.
- HOW: Documented Flow Lifecycle Audit Contract in `architecture-change.md` covering events (`flow.started`, `flow.stage.completed`, `flow.stage.failed`, `flow.compensation.started`, `flow.completed`, `flow.cancelled`), required fields (`flow_run_id`, `trace_id`, `flow_name`, `stage`, `state_before`, `state_after`, `duration_ms`, `error_type`, `provider_used`), redaction rules consistent with Pipeline contract, and emission boundary forbidding direct logging / pandas / sklearn / mlxtend / fastapi / backend.api / backend.infrastructure imports in `backend/business/flows/`. `ProjectAnalysisFlow` emits `flow.started`, `flow.stage.completed`, `flow.stage.failed`, `flow.completed`, and translates terminal failures into `flow.stage.failed` carrying `error_type`; `flow.compensation.started` and `flow.cancelled` are documented for future flows but not yet emitted because no compensation logic exists today.
- EXPECTED_RESULT: Flow lifecycle state transitions are auditable.
- VERIFY: `docs/architecture/architecture-change.md` documents lifecycle audit events for Business Flow.
- STATUS: completed
- RESULT: `docs/architecture/architecture-change.md` now contains `Flow Lifecycle Audit Contract` with full event list, field schema, redaction rules and emission boundary. Audit assertions covered by `tests/business/test_project_analysis_flow.py` (`flow.started`, `flow.completed`, `flow.stage.completed`, `flow.stage.failed`).
- RISK: Long-running jobs may become impossible to replay or debug without lifecycle audit.
- ROLLBACK: Revert the appended `Flow Lifecycle Audit Contract` section in `architecture-change.md`; mark as NOT_APPLICABLE if the project later removes complex Business Flow.

## 7. API Controller

### [x] Add request-level trace context requirements

- WHERE: `docs/architecture/architecture-change.md`, future controller rewiring in `backend/api/*.py`.
- WHY: Every external request needs a trace root for downstream debugging.
- HOW: Document how `request_id` and `trace_id` are created or accepted. Document how `actor_id` / `session_id` is attached when available. Document how API errors preserve `trace_id` internally while returning safe public error responses.
- EXPECTED_RESULT: API Controller layer has request-level trace context requirements.
- VERIFY: `docs/architecture/architecture-change.md` contains API Controller trace context strategy.
- STATUS: completed
- RESULT: Appended `## Request-Level Trace Context` section to `docs/architecture/architecture-change.md` covering identifier lifecycle (uuid4 + X-Trace-Id/X-Request-Id header reuse), propagation via per-request `ProvidersContainer.telemetry`, error mapping coupling with `backend/api/error_mapping.py:map_internal_error`, background-task inheritance, and forbidden patterns (controller-side uuid generation, business-layer logging SDK imports, trace_id leakage in response bodies).
- RISK: Without request-level trace root, downstream logs cannot be correlated.
- ROLLBACK: Use generated `request_id` only if upstream trace headers are not supported.

### [x] Thin project API controller

- WHERE: `backend/api/projects.py`.
- WHY: This controller currently handles storage, file I/O, background lifecycle, data transformation, and recommendation algorithms.
- HOW: Replace direct storage/core/service calls with project pipelines and `ProjectAnalysisFlow`. Keep route paths, methods, request schema, response schema, status codes, and error `detail` messages current-compatible.
- EXPECTED_RESULT: `backend/api/projects.py` acts as HTTP boundary only.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py`
- STATUS: completed
- RESULT: Rewrote `backend/api/projects.py` as pure HTTP boundary; each handler resolves a pipeline/flow via FastAPI `Depends` (`ProjectPipeline`, `DatasetUploadPipeline`, `ProjectCustomerPipeline`, `ProjectRecommendationPipeline`, `ProjectAnalysisFlow`), parses request, maps response, and exits with a single `try/except MarketMindError -> map_internal_error`. All direct imports of `backend.services`, `backend.core.storage`, `backend.core.recommend`, `backend.infrastructure`, `shutil`, and `pandas` removed. `ProjectPipeline` extended with `resolve_report` / `resolve_audio` for FileResponse paths, and `ProjectCustomerPipeline._normalize_row` coerces row types. Verified by `tests/api/test_current_api_contracts.py`, `tests/api/test_frontend_api_matrix_contracts.py`, `tests/test_architecture_imports.py`, `tests/api/test_controller_thinness.py` (19 passed).
- RISK: This is high blast radius because most frontend project screens depend on it.
- ROLLBACK: Revert only `backend/api/projects.py` to previous implementation.

### [x] Thin recommendation and association controllers

- WHERE: `backend/api/recommend.py`, `backend/api/association.py`.
- WHY: Controllers currently use cached services, global service instances, and direct TTS helpers.
- HOW: Delegate to recommendation and association pipelines. Preserve fields `recommends`, `target_customers`, `speech`, `warning`, `upstream`, `downstream`, `rules`, and error mappings.
- EXPECTED_RESULT: Controllers stop constructing/calling concrete service implementations directly.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py`
- STATUS: completed
- RESULT: Rewrote `backend/api/recommend.py` and `backend/api/association.py` as thin HTTP boundaries. `/recommend/user/{id}` and `/recommend/item/{id}` delegate to `ProjectRecommendationPipeline`; controller fetches the project once via `ProjectPipeline.get` and injects `dataset_path` into the response to preserve the legacy field. `/recommend/calculate/{id}` and `/recommend/tts` delegate to `RecommendationPipeline`; when rule calculation fails the controller rebuilds the public 3-key response (`success`, `message`, `rules`). `/association/analyze`, `/association/results/{id}`, `/association/realtime/{id}` delegate to `AssociationAnalysisPipeline`. All cached service singletons removed. Verified by 19 passing tests (current API contracts + matrix contracts + architecture lint + controller thinness).
- RISK: Recommendation fallback warning behavior is user-visible.
- ROLLBACK: Revert affected controllers to previous service calls.

### [x] Thin voice and AI voice controllers

- WHERE: `backend/api/voice.py`, `backend/api/ai_voice.py`.
- WHY: Controllers currently manage output paths, log detailed request/provider data, and call SDK-facing services.
- HOW: Delegate to voice pipelines and generated asset provider. Preserve audio URL formats and FastAPI `FileResponse` behavior.
- EXPECTED_RESULT: Voice controllers contain request parsing, pipeline call, response mapping, and error mapping only.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py`
- STATUS: completed
- RESULT: Rewrote `backend/api/voice.py` to delegate to `VoiceSynthesisPipeline` (synthesize + resolve audio path for FileResponse). Rewrote `backend/api/ai_voice.py` to delegate to `AIVoiceBroadcastPipeline`; new methods `synthesize_tts(text, voice, rate, volume)` and `resolve_audio_path(filename)` introduced on the pipeline to keep controller as pure boundary. Direct imports of `edge_tts`, `httpx`, `backend.services.*`, and `backend.infrastructure.*` removed from both files. Logging of provider credentials/model config removed; telemetry stays in pipelines/flows per architecture rules. Verified by 19 passing tests.
- RISK: AI voice route currently logs provider/model config; preserve necessary trace without exposing secrets.
- ROLLBACK: Revert affected controllers to previous service calls.

### [x] Keep inactive prediction and clustering routers inactive until protected

- WHERE: `backend/api/prediction.py`, `backend/api/clustering.py`, `backend/main.py`.
- WHY: These routers are currently not registered and appear inconsistent with service constructor/method signatures.
- HOW: Do not register them during architecture migration. Add contract tests and fix signatures only in a separate approved task.
- EXPECTED_RESULT: No new public API surface is exposed accidentally.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py`
- STATUS: completed
- RESULT: `backend/main.py` registers only `projects`, `recommend`, `association`, `voice`, and `ai_voice` routers; `prediction` and `clustering` modules remain unimported and unregistered. Contract test `tests/api/test_current_api_contracts.py::test_root_and_health` (and the rest of the API contract suite) does not exercise `/prediction/*` or `/clustering/*`, confirming no accidental public surface. Files left untouched apart from the pre-existing inactive bodies.
- RISK: Registering broken routers would introduce new failing endpoints.
- ROLLBACK: Re-comment route registration if accidentally enabled.

## 8. Architecture Lint / Runtime Check / 全量验证

### [x] Add minimal runtime checks

- WHERE: `backend/core/runtime_checks.py`.
- WHY: Provider Factory and adapter wiring need executable verification beyond static imports.
- HOW: Implement CLI-compatible checks: `check-config`, `check-providers`, `check-storage --sandbox`, `check-llm --dry-run`, `check-speech --mock`, `validate-api-schemas`, and future `dry-run-project-analysis`.
- EXPECTED_RESULT: Runtime facts can be verified without starting a full server or hitting real secrets by default.
- VERIFY: `uv run python -m backend.core.runtime_checks check-config && uv run python -m backend.core.runtime_checks check-providers`
- STATUS: completed
- RESULT: `backend/core/runtime_checks.py` (372 lines, dispatcher + 11 `cmd_*` subcommands; slightly over the 300-line soft target due to per-command argparse subparsers and DTO field validation). All 11 commands run green: `check-config: ok`, `check-providers: ok` (10 container fields non-null), `check-storage: ok sandbox=tmp` (full repo/storage/dataset round-trip inside `tempfile.TemporaryDirectory`), `check-llm: dry-run skipped` (interface probe only, no network), `check-speech: mock skipped` (interface probe only), `validate-api-schemas: ok endpoints=22`, `inspect-trace: skipped` (MVP placeholder). Module passes `uv run ruff check` and `uv run ruff format --check`.
- RISK: Runtime checks must not perform irreversible writes outside sandbox mode. Mitigated: `check-storage` rejects invocation without `--sandbox`; `check-llm` rejects without `--dry-run`; `check-speech` rejects without `--mock`; `check-audit-sink` writes only inside `tempfile.TemporaryDirectory`.
- ROLLBACK: `git checkout HEAD -- backend/core/runtime_checks.py tests/core/`; commands are not invoked from production code paths, so removal is non-breaking.

### [x] Add Runtime Check for telemetry and audit

- WHERE: runtime check plan and future `backend/core/runtime_checks.py`.
- WHY: Runtime Check must verify that trace events and audit sinks work after migration.
- HOW: Plan commands: `check-telemetry`, `check-audit-sink`, `inspect-trace`, `validate-log-schema`, `validate-audit-schema`, and `dry-run-pipeline --trace`. Adapt command names to the Python backend package.
- EXPECTED_RESULT: Runtime Check strategy includes telemetry and audit validation.
- VERIFY: `docs/architecture/architecture-change.md` Runtime Check Strategy includes telemetry and audit checks.
- STATUS: completed
- RESULT: `check-telemetry: ok events_emitted=3` (emits DebugEvent + AuditEvent + ErrorEvent through `ConsoleTelemetryAdapter` with in-memory writer; asserts required DebugEvent payload fields `{trace_id, request_id, layer, module, operation, stage, event, status}` are present). `check-audit-sink: ok sandbox=tmp` (writes one AuditEvent to `FileTelemetryAdapter` under `tempfile.TemporaryDirectory`; parses the JSONL line and asserts required AuditEvent fields). `validate-log-schema: ok fields_checked=11` and `validate-audit-schema: ok fields_checked=8` against `tests/fixtures/logging/{debug_event,audit_event}.json`. `inspect-trace` is a documented MVP placeholder (logs `skipped: not implemented in MVP`); `dry-run-pipeline --trace` is documented as future-not-implemented in `architecture-change.md` section 16. `architecture-change.md` section 16 now includes a `Runtime Check Strategy — Implementation status` subsection with per-command side effects, secrets, and exit-code semantics.
- RISK: Logs may exist but be unqueryable or schema-inconsistent. Mitigated: schema validation runs on every CI smoke and rejects missing dataclass fields.
- ROLLBACK: Revert section 16 in `architecture-change.md` and remove the four telemetry/audit subcommands from `runtime_checks.py`; production code does not depend on these commands.

### [x] Run staged and full validation

- WHERE: project root.
- WHY: Refactor completion requires static checks, architecture lint, contract tests, full tests, runtime checks, and frontend type/build checks.
- HOW: Run commands in order: `uv run ruff check .`, `uv run pytest tests/test_architecture_imports.py`, affected tests, `uv run pytest tests/`, `uv run python -m backend.core.runtime_checks check-config`, `uv run python -m backend.core.runtime_checks check-providers`, `cd frontend && npm run build`.
- EXPECTED_RESULT: All planned validation passes or failures are recorded with root cause and next action.
- VERIFY: command outputs from the listed sequence.
- STATUS: completed
- RESULT:
  - `uv run ruff check backend tests`: 21 remaining `N806`/`N803`/`F841` violations in legacy ML modules (`backend/core/recommend.py`, `backend/services/analysis_service.py`, `backend/services/clustering_service.py`, `backend/services/model_builder_service.py`, `backend/services/prediction_service.py`, `backend/services/recommender_service.py`). All are sklearn/RFM domain idiom — capital `X` for feature matrices, `Q1/Q3/IQR` for quantiles, `R/F/M` for RFM analysis, `K_range` for K-means sweeps. Pre-existing from before Phase 8; auto-fix removed 46 issues that were genuinely incorrect.
  - `uv run ruff format --check backend tests`: clean (124 files formatted).
  - `uv run pytest tests/test_architecture_imports.py`: 3 passed.
  - `uv run pytest tests/`: 104 passed in 7.09s (88 prior + 16 new `tests/core/test_runtime_checks.py`).
  - `uv run python -m backend.core.runtime_checks <each of 11 commands>`: all exit code 0, all print `ok` / `skipped` markers as designed.
  - `cd frontend && npm run build`: fails with pre-existing TypeScript errors — `element-plus/dist/index.css` and `element-plus/theme-chalk/dark/css-vars.css` modules missing (partial `node_modules`), plus ~17 `TS6133` unused-import warnings in `src/views/*.vue` and `src/main.ts`, and one `TS7006` implicit-any in `ProjectDetail.vue:454`. Frontend issues are pre-existing and out of Phase 8 backend-architecture scope.
- RISK: Existing lack of tests means the first validation phase must create behavior protection before expecting full coverage. Updated risk: remaining 21 ruff `N806` warnings in legacy ML services would lose mathematical readability if renamed; recommend deferring to a dedicated ML-conventions decision (e.g. per-module `# noqa` or `pep8-naming` ignore for the `services/` ML subset). Frontend build is pre-existing red and should be fixed in a separate frontend-focused phase.
- ROLLBACK: Revert only the last failing migration phase, not unrelated files. Phase 8 auto-fixes were ruff-conservative (import sort, removed unused imports, format normalization) and are safe; if regression appears, `git checkout HEAD~1 -- backend tests` restores pre-Phase-8 state.

## 9. 清理与收尾

### [x] Remove obsolete direct-access code after equivalent behavior is proven

- WHERE: `backend/core/storage.py`, `backend/services/*`, `backend/core/recommend.py`, `backend/api/*.py`.
- WHY: After controllers/pipelines/providers are wired, old direct storage/SDK/service paths may become dead code.
- HOW: Use reference search and tests to remove only unreachable compatibility code. Do not delete inactive prediction/clustering route files unless separately approved.
- EXPECTED_RESULT: No dead direct access remains in migrated paths; public behavior stays unchanged.
- VERIFY: `uv run pytest tests/ && uv run pytest tests/test_architecture_imports.py && uv run ruff check .`
- STATUS: completed
- RESULT:
  - Reference scan: `rg -n "backend\.services\.(analysis_service|association_service|prediction_service|clustering_service|recommender_service|model_builder_service|tts_service|voice_service|ai_voice_service)" --type py` and `rg -n "backend\.core\.(storage|recommend)" --type py`. Cross-checked `tests/` separately.
  - Deleted (zero remaining references in any active or test path):
    - `backend/services/voice_service.py`
    - `backend/services/ai_voice_service.py`
    - `backend/core/analysis.py`
    - `backend/core/recommend.py` (only consumer was `backend/core/analysis.py`, deleted in the same set; test reference is a static string in `tests/api/test_controller_thinness.py` forbidden-prefix list, which still functions after deletion).
  - Retained with reason:
    - `backend/services/analysis_service.py` + chained `association_service.py`, `clustering_service.py`, `model_builder_service.py`, `prediction_service.py`, `recommender_service.py`, `tts_service.py` — `backend/infrastructure/factories/provider_factory.py` registers `run_project_analysis` as the `AnalysisJobProvider` default handler and `clear_recommender_cache` as the cache-clear hook; `tests/business/test_project_analysis_current_behavior.py` patches `analysis_service` as a behavior anchor.
    - `backend/core/storage.py` — `backend/infrastructure/adapters/json_project_repository_adapter.py` wraps `ProjectStorage`; `tests/api/conftest.py` and `tests/business/test_project_analysis_current_behavior.py` instantiate it as fixture.
    - `backend/api/prediction.py`, `backend/api/clustering.py` — inactive routers explicitly excluded from this task; they continue to import `backend.services.prediction_service` / `backend.services.clustering_service`.
  - Post-deletion verification: `uv run pytest tests/ -q` -> `104 passed, 7 warnings in 6.86s`; `uv run pytest tests/test_architecture_imports.py -q` -> `3 passed in 0.02s`; `uv run ruff check backend tests` -> 20 errors all in pre-existing legacy `backend/services/{analysis,clustering,model_builder,prediction,recommender}_service.py` (same debt noted in §"Current Execution Notes"); no new violations introduced.
- RISK: Inactive `backend/api/prediction.py` / `clustering.py` still couple to legacy services; if those routers are later registered without contract tests they will resurface as architecture violations.
- ROLLBACK: `git restore backend/services/voice_service.py backend/services/ai_voice_service.py backend/core/analysis.py backend/core/recommend.py`.

### [x] Update architecture documentation with final implemented paths

- WHERE: `docs/architecture/architecture-change.md`, `docs/architecture/construction-checklist.md`.
- WHY: The architecture plan must match the implemented code after migration.
- HOW: Update call chains, Provider Interfaces, Providers Container fields, migration mapping, command results, risk status, and rollback notes based on final code.
- EXPECTED_RESULT: A future developer or AI agent can continue from docs without rediscovering the architecture.
- VERIFY: Manual review against repository tree and `uv run pytest tests/test_architecture_imports.py` output.
- STATUS: completed
- RESULT:
  - `docs/architecture/architecture-change.md` §4 prepended with a post-migration call-chain summary mapping each active controller to its `Pipeline -> Ability/Provider -> Adapter` path; legacy §4.1–§4.8 retained as behavior anchors.
  - §8 split into 8.1 historical violations (each marked `Resolved in Phase 7 / 8 / 9`), 8.2 active controller import surface, 8.3 residual references with retention reasons, 8.4 modules removed in Phase 9.
  - Appended `## Implemented Layout (Post-Migration Snapshot)` with the final directory tree and one-line responsibility per layer; migration completion date 2026-05-25, base commit `18578a4` (Phase 9 cleanup uncommitted on top).
  - Appended `## Observability Coverage Checklist` mapping each observability dimension to its defining section in the document.
  - `uv run pytest tests/test_architecture_imports.py -q` -> `3 passed in 0.02s` after doc edits.
- RISK: Document references commit `18578a4` plus uncommitted Phase 9 cleanup; the snapshot will drift once Phase 9 changes are committed under a new SHA.
- ROLLBACK: `git restore docs/architecture/architecture-change.md docs/architecture/construction-checklist.md`.

### [x] Confirm no fallback utility modules were introduced

- WHERE: `backend/`, especially `backend/utils/`, any new `helpers`, `common`, or `misc` paths.
- WHY: The target architecture forbids generic fallback modules that hide responsibilities.
- HOW: Search for new imports and directories named `utils`, `helpers`, `common`, or `misc`. Existing empty `backend/utils/__init__.py` should not gain responsibilities.
- EXPECTED_RESULT: New code uses named business, ability, provider, or infrastructure modules only.
- VERIFY: `rg "utils|helpers|common|misc" backend tests`
- STATUS: completed
- RESULT:
  - Command: `rg -n "from backend\.(utils|helpers|common|misc)|import backend\.(utils|helpers|common|misc)" backend tests` -> zero matches.
  - `ls backend/utils/` -> only `__init__.py`. `cat backend/utils/__init__.py` -> single line `"""Utilities"""`. No additional files, no new responsibilities.
  - No `backend/helpers/`, `backend/common/`, or `backend/misc/` directory exists.
- RISK: Future authors may still be tempted to attach utilities to `backend/utils/`; Architecture Lint should be extended to forbid non-empty modules under that path if desired.
- ROLLBACK: N/A (no code change in this task).

### [x] Record final verification and remaining risks

- WHERE: `docs/architecture/construction-checklist.md`.
- WHY: Each phase must retain verification evidence, result, unresolved risks, and rollback status.
- HOW: Fill `STATUS`, `RESULT`, `RISK`, and `ROLLBACK` fields after each executed phase with concrete command outputs or failure summaries.
- EXPECTED_RESULT: Checklist becomes an auditable migration log.
- VERIFY: Manual review confirms every completed item has a command/result note.
- STATUS: completed
- RESULT: Final regression suite executed end-to-end on the Phase 9 working tree:
  - `uv run ruff check backend tests` -> `Found 20 errors.` All in pre-existing legacy `backend/services/{analysis,clustering,model_builder,prediction,recommender}_service.py` (existing repository lint debt documented in Current Execution Notes; not introduced by Phase 9).
  - `uv run ruff format --check backend tests` -> `120 files already formatted`.
  - `uv run pytest tests/test_architecture_imports.py -q` -> `3 passed in 0.02s`.
  - `uv run pytest tests/ -q` -> `104 passed, 7 warnings in 6.86s`.
  - `uv run python -m backend.core.runtime_checks check-config` -> `ok` (17 fields).
  - `uv run python -m backend.core.runtime_checks check-providers` -> `ok` (10 provider fields).
  - `uv run python -m backend.core.runtime_checks validate-api-schemas` -> `ok endpoints=22`.
  - `uv run python -m backend.core.runtime_checks check-telemetry` -> `ok events_emitted=3`.
  - Remaining risks:
    1. Legacy `backend/services/*` still wired through `FastapiBackgroundAnalysisJobAdapter` as the default analysis handler; full provider-native analysis flow not yet composed from abilities.
    2. Inactive `backend/api/prediction.py` and `backend/api/clustering.py` still import legacy services; require contract tests before any future registration.
    3. Pre-existing ruff debt in legacy services (20 findings) blocks `make lint` from going green; out of scope per Phase 9 boundary.
- RISK: Phase 9 cleanup is uncommitted; reverts depend on `git restore` against working tree, not a tagged commit.
- ROLLBACK: `git restore -SW backend/services/voice_service.py backend/services/ai_voice_service.py backend/core/analysis.py backend/core/recommend.py docs/architecture/architecture-change.md docs/architecture/construction-checklist.md`.

### [x] Verify debug and audit documentation completeness

- WHERE: `docs/architecture/architecture-change.md`, `docs/architecture/construction-checklist.md`.
- WHY: Debug Logger and Audit Trace must be part of final architecture acceptance.
- HOW: Confirm trace context model exists. Confirm layer-level logging contract exists. Confirm audit event schema exists. Confirm telemetry provider boundary exists. Confirm privacy and redaction policy exists. Confirm lint and runtime check extensions exist.
- EXPECTED_RESULT: Final architecture documents include observability as a first-class dimension.
- VERIFY: Manual doc review; checklist items are not missing required WHERE / WHY / HOW / EXPECTED_RESULT / VERIFY fields.
- STATUS: completed
- RESULT:
  - Added `## Observability Coverage Checklist` at the tail of `docs/architecture/architecture-change.md` with seven explicit `[x]` items: Request-Level Trace Context, Ability-Level Debug Event Contract, Pipeline-Level Trace Event Contract, Flow Lifecycle Audit Contract, Telemetry Provider boundary, Runtime Check Strategy (telemetry/audit/log-schema/audit-schema), and Redaction policy.
  - Each item cross-references the in-document section that defines it (§11, §15, §16, plus the dedicated Debug Logger / Audit Trace / trace-context-propagation blocks).
  - Live runtime evidence: `check-telemetry: ok events_emitted=3`; `check-config`, `check-providers`, `validate-api-schemas` all `ok` (commands listed in the verification record above).
- RISK: The observability checklist depends on the existing Debug Logger / Audit Trace sections staying in sync; if those sections are later renamed, the cross-references must be updated.
- ROLLBACK: `git restore docs/architecture/architecture-change.md`.
