# Backend Architecture Construction Checklist

本清单用于后续 `/backend` 架构迁移。当前阶段只创建文档，不迁移业务代码。

执行规则：

- 必须从第一个未完成任务开始。
- 每次只执行一个内聚任务。
- 未建立行为保护前，不允许移动或重写业务代码。
- 所有任务必须保持公开 API、状态码、响应字段、文件路径副作用、前端依赖行为等价。
- Business Flow 只用于复杂生命周期；当前仅 `ProjectAnalysisFlow` 符合条件。

## 1. 测试锚点

### [ ] Add API smoke tests for current public contracts

- WHERE: `tests/api/test_current_api_contracts.py` or project-approved equivalent test path.
- WHY: Current project has no tests, while frontend depends on concrete response shapes and status/error behavior.
- HOW: Use FastAPI `TestClient` or async HTTP client to cover `/`, `/api/health/`, project CRUD, upload validation, reanalyze validation, customers response shape, recommendation endpoints, `/api/voice/tts/`, `/api/ai-voice/broadcast/`, and audio lookup. Use fixtures/fakes for external LLM/TTS/file effects where needed.
- EXPECTED_RESULT: Tests document current route paths, methods, status codes, response fields, and FastAPI `detail` error shape.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Tests may reveal existing inactive or inconsistent routes; do not fix unrelated behavior in this task.
- ROLLBACK: Remove only the newly added test file if the test design is invalid; do not change backend behavior.

### [ ] Add project analysis behavior anchor tests

- WHERE: `tests/business/test_project_analysis_current_behavior.py`.
- WHY: Upload/reanalysis currently triggers a background lifecycle that writes files, updates statuses, builds a model, and handles failure state.
- HOW: Create fixture project data and monkeypatch concrete services or providers to avoid real external TTS. Assert status transitions `处理中 -> 已完成` and failure `失败 + error_message`, output path fields, and cache invalidation call.
- EXPECTED_RESULT: Current analysis behavior is executable and protected before extracting Business Flow.
- VERIFY: `uv run pytest tests/business/test_project_analysis_current_behavior.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Current analysis function has multiple filesystem side effects; fixture isolation must avoid writing outside temp directories.
- ROLLBACK: Remove test fixtures and test file if isolation is incorrect.

### [ ] Add frontend-dependent API matrix contract tests

- WHERE: `tests/api/test_frontend_api_matrix_contracts.py`.
- WHY: Frontend uses specific fields such as `success`, `data.id`, `status`, `results`, `audio_url`, `recommends`, `downstream`, and FastAPI `detail`.
- HOW: Encode the API Matrix from `docs/architecture/architecture-change.md` into response shape assertions for active internal frontend calls. Mark external LLM calls out of backend scope.
- EXPECTED_RESULT: Frontend-dependent fields are locked before controller thinning.
- VERIFY: `uv run pytest tests/api/test_frontend_api_matrix_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Tests can become over-specified if they assert data values instead of schema/field presence.
- ROLLBACK: Relax assertions to public fields only; do not modify frontend or backend behavior.

## 2. Provider Interface

### [ ] Define internal error model

- WHERE: `backend/core/errors.py`.
- WHY: External Adapter errors must not leak SDK exceptions into business logic, and controllers need a stable internal error mapping layer.
- HOW: Add typed internal errors: `MarketMindError`, `ValidationError`, `NotFoundError`, `ProviderError`, `InfrastructureError`, `PipelineExecutionError`, `BusinessFlowError`. Do not wire them into existing routes yet.
- EXPECTED_RESULT: Internal error classes exist and can be imported by provider, ability, pipeline, and adapter layers.
- VERIFY: `uv run python -m py_compile backend/core/errors.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Naming may collide with Pydantic/FastAPI `ValidationError`; use explicit imports in future tasks.
- ROLLBACK: Delete `backend/core/errors.py` if no other task depends on it.

### [ ] Define project repository provider interface

- WHERE: `backend/providers/project_repository_provider.py`.
- WHY: `backend/api/projects.py` and `analysis_service.py` currently import global JSON storage directly.
- HOW: Add a capability-named Protocol or ABC for project metadata operations: `create_project`, `get_project`, `list_projects`, `update_project`, `delete_project`, `count_projects`. Use existing `Project` model and narrow DTOs where needed.
- EXPECTED_RESULT: Business code can depend on `ProjectRepositoryProvider` instead of `ProjectStorage`.
- VERIFY: `uv run python -m py_compile backend/providers/project_repository_provider.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Interface may accidentally expose filesystem path methods; keep project file paths in `ProjectFileStorageProvider`.
- ROLLBACK: Remove the provider interface file if design is rejected before wiring.

### [ ] Define project file and generated asset providers

- WHERE: `backend/providers/project_file_storage_provider.py`, `backend/providers/generated_asset_provider.py`.
- WHY: Dataset upload, customers CSV, reports, audio files, `/outputs`, `/tmp`, and `backend/data/audio` are accessed directly from controllers/services.
- HOW: Add separate capability interfaces for project workspace files and generated assets. Keep methods narrow: upload dataset, read/write customers, save/resolve report, save/resolve audio, resolve AI audio.
- EXPECTED_RESULT: File side effects can move behind provider boundaries without changing existing paths.
- VERIFY: `uv run python -m py_compile backend/providers/project_file_storage_provider.py backend/providers/generated_asset_provider.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Combining metadata repository and file storage into one provider would recreate a broad storage abstraction.
- ROLLBACK: Remove newly added provider files if interface boundaries are wrong.

### [ ] Define dataset and association rule providers

- WHERE: `backend/providers/dataset_provider.py`, `backend/providers/association_rule_store_provider.py`.
- WHY: Association, recommendation, prediction, and clustering code read CSV/pickle files and append dynamic rules directly.
- HOW: Add `DatasetProvider` for loading tabular data and `AssociationRuleStoreProvider` for loading/saving rule artifacts. Do not include mlxtend algorithm methods in provider unless the method represents persisted rule artifact access.
- EXPECTED_RESULT: Algorithmic abilities can receive datasets/rules without direct filesystem reads.
- VERIFY: `uv run python -m py_compile backend/providers/dataset_provider.py backend/providers/association_rule_store_provider.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Provider may become too broad if it mixes data loading with rule calculation.
- ROLLBACK: Remove provider files before any wiring if scope is too broad.

### [ ] Define model, speech, LLM, and analysis job providers

- WHERE: `backend/providers/recommendation_model_store_provider.py`, `backend/providers/speech_synthesis_provider.py`, `backend/providers/llm_provider.py`, `backend/providers/analysis_job_provider.py`.
- WHY: Current services directly use pickle model files, Edge TTS SDK, httpx LLM APIs, and FastAPI BackgroundTasks.
- HOW: Define narrow capability interfaces: model load/save, speech synthesize, broadcast script generation, and project analysis job scheduling. Use business capability names, not vendor names.
- EXPECTED_RESULT: Business pipelines can depend on capability interfaces instead of SDK/runtime implementations.
- VERIFY: `uv run python -m py_compile backend/providers/recommendation_model_store_provider.py backend/providers/speech_synthesis_provider.py backend/providers/llm_provider.py backend/providers/analysis_job_provider.py`
- STATUS: pending
- RESULT: Not started.
- RISK: LLM interface may accidentally bind OpenAI/Anthropic response shapes; return internal DTOs only.
- ROLLBACK: Remove provider files before wiring if contract is wrong.

### [ ] Define Providers Container

- WHERE: `backend/providers/container.py`.
- WHY: Current code uses global storage, global services, and cached singletons rather than explicit dependency injection.
- HOW: Add `ProvidersContainer` with only actual fields: `repository`, `storage`, `assets`, `dataset`, `association_rules`, `recommendation_models`, `speech`, `llm`, `analysis_jobs`.
- EXPECTED_RESULT: Pipelines and abilities can receive one typed container.
- VERIFY: `uv run python -m py_compile backend/providers/container.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Adding unused fields such as browser, queue, or telemetry would create speculative architecture.
- ROLLBACK: Remove or revise `container.py` before any pipeline depends on it.

## 3. External Adapter

### [ ] Implement JSON project repository adapter

- WHERE: `backend/infrastructure/adapters/json_project_repository_adapter.py`.
- WHY: `backend/core/storage.py` currently stores project metadata in `data/projects.json` and is globally imported by controllers/services.
- HOW: Implement `ProjectRepositoryProvider` using the existing JSON behavior. Preserve project fields, sorting by `created_at`, update semantics, and delete behavior. Do not remove `ProjectStorage` yet.
- EXPECTED_RESULT: Adapter can pass contract tests against the same behavior as current `ProjectStorage`.
- VERIFY: `uv run pytest tests/providers/test_json_project_repository_adapter.py`
- STATUS: pending
- RESULT: Not started.
- RISK: JSON writes are not atomic today; do not introduce different write semantics unless documented and tested.
- ROLLBACK: Delete adapter file and tests if not wired into production code.

### [ ] Implement local file and generated asset adapters

- WHERE: `backend/infrastructure/adapters/local_project_file_storage_adapter.py`, `backend/infrastructure/adapters/local_generated_asset_adapter.py`.
- WHY: Uploads, customers CSV, reports, TTS outputs, `/outputs`, `/tmp`, and `backend/data/audio` are scattered across controllers/services.
- HOW: Implement current path layout exactly. Preserve `/outputs/audio/...` and `/api/ai-voice/audio/{filename}/` lookup behavior until product approves normalization.
- EXPECTED_RESULT: File and asset behavior can be tested behind provider contracts without controller filesystem logic.
- VERIFY: `uv run pytest tests/providers/test_local_file_adapters.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Path changes would break frontend audio playback and report downloads.
- ROLLBACK: Revert adapter files; current direct filesystem logic remains untouched.

### [ ] Implement dataset and rule store adapters

- WHERE: `backend/infrastructure/adapters/csv_dataset_adapter.py`, `backend/infrastructure/adapters/local_association_rule_store_adapter.py`.
- WHY: Dataset/rule reads and dynamic rule writes are mixed into core recommendation and service functions.
- HOW: Wrap pandas CSV reads, rule pickle/CSV fallback, and dynamic rules append. Convert IO/parse failures to internal errors or current-compatible not-found behavior.
- EXPECTED_RESULT: Association/recommendation abilities can load data and store rules through providers.
- VERIFY: `uv run pytest tests/providers/test_dataset_and_rule_store_adapters.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Current fallback order between project dataset and global rule files must remain unchanged.
- ROLLBACK: Remove adapter files before wiring if fallback behavior is wrong.

### [ ] Implement recommendation model store adapter

- WHERE: `backend/infrastructure/adapters/local_recommendation_model_store_adapter.py`.
- WHY: Model artifact persistence currently writes and reads `backend/data/model_data.pkl` directly.
- HOW: Wrap pickle load/save behavior and current missing-model fallback semantics used by `RecommendationSystem`.
- EXPECTED_RESULT: Model build and recommendation pipelines can use a provider for model artifact storage.
- VERIFY: `uv run pytest tests/providers/test_recommendation_model_store_adapter.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Pickle compatibility must be preserved; changing artifact shape would break existing generated models.
- ROLLBACK: Remove adapter and keep direct model service behavior.

### [ ] Implement speech synthesis and LLM adapters

- WHERE: `backend/infrastructure/adapters/edge_tts_speech_synthesis_adapter.py`, `backend/infrastructure/adapters/openai_compatible_llm_adapter.py`, `backend/infrastructure/adapters/anthropic_llm_adapter.py`.
- WHY: `edge_tts` and `httpx` provider calls currently live in service/business code.
- HOW: Move SDK/HTTP calls into adapters implementing `SpeechSynthesisProvider` and `LLMProvider`. Preserve timeout, provider request shape, response parsing, voice/rate/volume behavior, and generated script text.
- EXPECTED_RESULT: Business code no longer imports `edge_tts` or `httpx` after later wiring.
- VERIFY: `uv run pytest tests/providers/test_speech_and_llm_adapters.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Real external calls require secrets; tests must use fake HTTP/TTS clients.
- ROLLBACK: Remove adapter files before production wiring if contract is wrong.

### [ ] Implement provider factory

- WHERE: `backend/infrastructure/factories/provider_factory.py`.
- WHY: Business layers need a single Settings -> Adapter -> ProvidersContainer assembly point.
- HOW: Create `create_providers(settings)` that instantiates current local adapters and provider container. Keep request-provided LLM config behavior available to AI voice pipeline instead of forcing env-only config.
- EXPECTED_RESULT: Providers Container can be created in tests and app bootstrap.
- VERIFY: `uv run pytest tests/providers/test_provider_factory.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Factory may read env outside `Settings`; prohibit that in architecture lint.
- ROLLBACK: Remove factory before app bootstrap wiring.

## 4. Ability Atom

### [ ] Extract association rule abilities

- WHERE: `backend/abilities/association/analyze_association_rules.py`, `backend/abilities/association/calculate_realtime_rules.py`.
- WHY: Association calculation is mixed with services, file reads, and dynamic rule persistence.
- HOW: Extract pure functions for Apriori analysis and realtime rule calculation. Inputs are dataset/rule DTOs and thresholds. Outputs are existing rule DTO-compatible structures. Persistence remains in providers.
- EXPECTED_RESULT: Association logic can be unit-tested without filesystem or controller imports.
- VERIFY: `uv run pytest tests/abilities/test_association_rule_abilities.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Changing rule sort/order/field names can break frontend visualizations.
- ROLLBACK: Revert ability extraction and call existing services.

### [ ] Extract forecast and clustering abilities

- WHERE: `backend/abilities/prediction/forecast_sales.py`, `backend/abilities/clustering/cluster_customers.py`, `backend/abilities/clustering/build_cluster_association_rules.py`.
- WHY: Prediction and clustering currently read data and write outputs inside service classes.
- HOW: Extract algorithmic actions that accept explicit tabular input and parameters. Return existing result shapes used by `AnalysisResults` and frontend.
- EXPECTED_RESULT: Forecast and clustering logic has unit tests with fixture datasets and no direct storage calls.
- VERIFY: `uv run pytest tests/abilities/test_prediction_and_clustering_abilities.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Numeric output drift can occur if preprocessing changes; keep preprocessing identical.
- ROLLBACK: Revert ability calls to existing `PredictionService` and `ClusteringService`.

### [ ] Extract recommendation abilities

- WHERE: `backend/abilities/recommendation/recommend_for_user.py`, `backend/abilities/recommendation/recommend_for_item.py`, `backend/abilities/recommendation/build_recommendation_model.py`.
- WHY: Recommendation code mixes model loading, fallback dataset selection, rule calculation, dynamic persistence, and TTS in one service module.
- HOW: Extract model build and recommendation lookup actions. Keep storage and cache concerns outside abilities.
- EXPECTED_RESULT: Recommendation algorithms can be tested with fake model/rule inputs.
- VERIFY: `uv run pytest tests/abilities/test_recommendation_abilities.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Current fallback behavior when model is missing must remain visible through `warning` fields.
- ROLLBACK: Revert to `RecommendationSystem` calls.

### [ ] Extract report and voice abilities

- WHERE: `backend/abilities/report/generate_analysis_report.py`, `backend/abilities/report/generate_speech_text.py`, `backend/abilities/voice/synthesize_speech.py`, `backend/abilities/voice/generate_broadcast_script.py`.
- WHY: Report/speech text and AI broadcast generation are mixed into service-level orchestration and provider calls.
- HOW: Move pure text/report composition into abilities. `synthesize_speech` and `generate_broadcast_script` call provider interfaces, not Edge TTS or HTTP clients.
- EXPECTED_RESULT: Report and voice behavior can be unit-tested with fake providers.
- VERIFY: `uv run pytest tests/abilities/test_report_and_voice_abilities.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Prompt text or report formatting changes may alter user-visible output; assert key sections/fields, not exact generated prose unless required.
- ROLLBACK: Revert to existing service methods.

## 5. Business Pipeline

### [ ] Create project CRUD pipeline

- WHERE: `backend/business/pipelines/project_pipeline.py`.
- WHY: Project CRUD route handlers currently call storage directly.
- HOW: Implement create/list/get/update/delete operations using `ProjectRepositoryProvider`. Preserve `ProjectResponse` and `ProjectListResponse` data semantics through controller mapping.
- EXPECTED_RESULT: Controllers can delegate CRUD operations without direct storage imports.
- VERIFY: `uv run pytest tests/business/test_project_pipeline.py tests/api/test_current_api_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Response message strings and 404 behavior must stay current-compatible.
- ROLLBACK: Revert controller wiring to direct storage calls.

### [ ] Create dataset upload pipeline

- WHERE: `backend/business/pipelines/dataset_upload_pipeline.py`.
- WHY: Upload route currently validates file type, writes dataset, updates status, and schedules analysis directly.
- HOW: Move validation, dataset save, project status update, and analysis job submission behind providers. Keep accepted extensions and response fields identical.
- EXPECTED_RESULT: Upload controller no longer writes files or schedules concrete functions directly.
- VERIFY: `uv run pytest tests/business/test_dataset_upload_pipeline.py tests/api/test_current_api_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: FastAPI `UploadFile` must not leak into business layer; pass a neutral uploaded file DTO or stream abstraction.
- ROLLBACK: Revert upload route to previous body.

### [ ] Create customer read and project recommendation pipelines

- WHERE: `backend/business/pipelines/project_customer_pipeline.py`, `backend/business/pipelines/project_recommendation_pipeline.py`.
- WHY: Customer read model and project recommendation routes contain CSV reads, field mapping, and direct algorithm imports.
- HOW: Move customers CSV/result fallback and item relation lookup into pipelines using dataset/rule providers and abilities. Preserve frontend field names.
- EXPECTED_RESULT: Project detail/customer/recommendation UI receives unchanged response shapes.
- VERIFY: `uv run pytest tests/business/test_project_read_pipelines.py tests/api/test_frontend_api_matrix_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Frontend depends on exact customer fields and rule item/confidence/lift fields.
- ROLLBACK: Revert affected route handlers to current direct logic.

### [ ] Create recommendation and association pipelines

- WHERE: `backend/business/pipelines/recommendation_pipeline.py`, `backend/business/pipelines/association_analysis_pipeline.py`.
- WHY: Recommendation and association API controllers call concrete services and cached singleton directly.
- HOW: Compose recommendation/association abilities and providers into pipelines. Keep current fallback warning behavior and error mappings.
- EXPECTED_RESULT: `/api/recommend/*` and `/api/association/*` can delegate to pipelines.
- VERIFY: `uv run pytest tests/business/test_recommendation_and_association_pipelines.py tests/api/test_current_api_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Recommendation singleton cache behavior and `clear_recommender_cache` semantics must be preserved.
- ROLLBACK: Revert route handlers to `get_recommender` and `AssociationService` calls.

### [ ] Create voice synthesis and AI voice broadcast pipelines

- WHERE: `backend/business/pipelines/voice_synthesis_pipeline.py`, `backend/business/pipelines/ai_voice_broadcast_pipeline.py`.
- WHY: Voice routes and AI voice service combine protocol mapping, file layout, LLM calls, TTS calls, and logging.
- HOW: Build pipelines around report/script generation and speech synthesis providers. Preserve `/outputs/audio/...` and `/api/ai-voice/audio/{filename}/` response URL styles.
- EXPECTED_RESULT: Voice controllers stop constructing SDK-facing services and stop managing file paths.
- VERIFY: `uv run pytest tests/business/test_voice_pipelines.py tests/api/test_frontend_api_matrix_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: External LLM/TTS behavior must be faked in tests; never require real secrets in CI.
- ROLLBACK: Revert route handlers to current service calls.

## 6. Business Flow

### [ ] Create ProjectAnalysisFlow for upload and reanalysis lifecycle

- WHERE: `backend/business/flows/project_analysis_flow.py`.
- WHY: `run_project_analysis` is a complex lifecycle with background execution, state transitions, multiple analysis steps, generated artifacts, model build, cache invalidation, and failure handling.
- HOW: Compose pipelines/abilities/providers into `ProjectAnalysisFlow`. Preserve current status strings, output paths, `error_message`, report/audio/model generation, customers CSV, and cache invalidation. Do not create flows for simple one-step routes.
- EXPECTED_RESULT: Upload/reanalysis can trigger one explicit flow while all side effects go through providers.
- VERIFY: `uv run pytest tests/business/test_project_analysis_flow.py tests/api/test_current_api_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Background behavior can change if flow execution becomes synchronous; preserve current scheduling semantics.
- ROLLBACK: Revert upload/reanalysis to call `run_project_analysis` directly.

## 7. API Controller

### [ ] Thin project API controller

- WHERE: `backend/api/projects.py`.
- WHY: This controller currently handles storage, file I/O, background lifecycle, data transformation, and recommendation algorithms.
- HOW: Replace direct storage/core/service calls with project pipelines and `ProjectAnalysisFlow`. Keep route paths, methods, request schema, response schema, status codes, and error `detail` messages current-compatible.
- EXPECTED_RESULT: `backend/api/projects.py` acts as HTTP boundary only.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py`
- STATUS: pending
- RESULT: Not started.
- RISK: This is high blast radius because most frontend project screens depend on it.
- ROLLBACK: Revert only `backend/api/projects.py` to previous implementation.

### [ ] Thin recommendation and association controllers

- WHERE: `backend/api/recommend.py`, `backend/api/association.py`.
- WHY: Controllers currently use cached services, global service instances, and direct TTS helpers.
- HOW: Delegate to recommendation and association pipelines. Preserve fields `recommends`, `target_customers`, `speech`, `warning`, `upstream`, `downstream`, `rules`, and error mappings.
- EXPECTED_RESULT: Controllers stop constructing/calling concrete service implementations directly.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Recommendation fallback warning behavior is user-visible.
- ROLLBACK: Revert affected controllers to previous service calls.

### [ ] Thin voice and AI voice controllers

- WHERE: `backend/api/voice.py`, `backend/api/ai_voice.py`.
- WHY: Controllers currently manage output paths, log detailed request/provider data, and call SDK-facing services.
- HOW: Delegate to voice pipelines and generated asset provider. Preserve audio URL formats and FastAPI `FileResponse` behavior.
- EXPECTED_RESULT: Voice controllers contain request parsing, pipeline call, response mapping, and error mapping only.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py tests/api/test_frontend_api_matrix_contracts.py tests/test_architecture_imports.py`
- STATUS: pending
- RESULT: Not started.
- RISK: AI voice route currently logs provider/model config; preserve necessary trace without exposing secrets.
- ROLLBACK: Revert affected controllers to previous service calls.

### [ ] Keep inactive prediction and clustering routers inactive until protected

- WHERE: `backend/api/prediction.py`, `backend/api/clustering.py`, `backend/main.py`.
- WHY: These routers are currently not registered and appear inconsistent with service constructor/method signatures.
- HOW: Do not register them during architecture migration. Add contract tests and fix signatures only in a separate approved task.
- EXPECTED_RESULT: No new public API surface is exposed accidentally.
- VERIFY: `uv run pytest tests/api/test_current_api_contracts.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Registering broken routers would introduce new failing endpoints.
- ROLLBACK: Re-comment route registration if accidentally enabled.

## 8. Architecture Lint / Runtime Check / 全量验证

### [ ] Add minimal architecture lint

- WHERE: `tests/test_architecture_imports.py`.
- WHY: Current code has multiple cross-layer imports and there is no guard against regressions.
- HOW: Add import-boundary tests for API, business, abilities, providers, and infrastructure layers. Include checks against SDK imports in business/API and against new `utils/helpers/common` fallback modules.
- EXPECTED_RESULT: Architecture violations fail mechanically before migration continues.
- VERIFY: `uv run pytest tests/test_architecture_imports.py`
- STATUS: pending
- RESULT: Not started.
- RISK: Initial test may fail until planned phases finish; mark known current violations explicitly only while migration is staged.
- ROLLBACK: Revert lint file only if the rule is incorrectly detecting allowed imports; do not delete rules to hide real violations.

### [ ] Add minimal runtime checks

- WHERE: `backend/core/runtime_checks.py`.
- WHY: Provider Factory and adapter wiring need executable verification beyond static imports.
- HOW: Implement CLI-compatible checks: `check-config`, `check-providers`, `check-storage --sandbox`, `check-llm --dry-run`, `check-speech --mock`, `validate-api-schemas`, and future `dry-run-project-analysis`.
- EXPECTED_RESULT: Runtime facts can be verified without starting a full server or hitting real secrets by default.
- VERIFY: `uv run python -m backend.core.runtime_checks check-config && uv run python -m backend.core.runtime_checks check-providers`
- STATUS: pending
- RESULT: Not started.
- RISK: Runtime checks must not perform irreversible writes outside sandbox mode.
- ROLLBACK: Remove or disable only the incorrect check command; keep provider wiring tests.

### [ ] Run staged and full validation

- WHERE: project root.
- WHY: Refactor completion requires static checks, architecture lint, contract tests, full tests, runtime checks, and frontend type/build checks.
- HOW: Run commands in order: `uv run ruff check .`, `uv run pytest tests/test_architecture_imports.py`, affected tests, `uv run pytest tests/`, `uv run python -m backend.core.runtime_checks check-config`, `uv run python -m backend.core.runtime_checks check-providers`, `cd frontend && npm run build`.
- EXPECTED_RESULT: All planned validation passes or failures are recorded with root cause and next action.
- VERIFY: command outputs from the listed sequence.
- STATUS: pending
- RESULT: Not started.
- RISK: Existing lack of tests means the first validation phase must create behavior protection before expecting full coverage.
- ROLLBACK: Revert only the last failing migration phase, not unrelated files.

## 9. 清理与收尾

### [ ] Remove obsolete direct-access code after equivalent behavior is proven

- WHERE: `backend/core/storage.py`, `backend/services/*`, `backend/core/recommend.py`, `backend/api/*.py`.
- WHY: After controllers/pipelines/providers are wired, old direct storage/SDK/service paths may become dead code.
- HOW: Use reference search and tests to remove only unreachable compatibility code. Do not delete inactive prediction/clustering route files unless separately approved.
- EXPECTED_RESULT: No dead direct access remains in migrated paths; public behavior stays unchanged.
- VERIFY: `uv run pytest tests/ && uv run pytest tests/test_architecture_imports.py && uv run ruff check .`
- STATUS: pending
- RESULT: Not started.
- RISK: Removing fallback paths too early can break project recommendation and model loading.
- ROLLBACK: Restore removed code from version control for the affected file.

### [ ] Update architecture documentation with final implemented paths

- WHERE: `docs/architecture/architecture-change.md`, `docs/architecture/construction-checklist.md`.
- WHY: The architecture plan must match the implemented code after migration.
- HOW: Update call chains, Provider Interfaces, Providers Container fields, migration mapping, command results, risk status, and rollback notes based on final code.
- EXPECTED_RESULT: A future developer or AI agent can continue from docs without rediscovering the architecture.
- VERIFY: Manual review against repository tree and `uv run pytest tests/test_architecture_imports.py` output.
- STATUS: pending
- RESULT: Not started.
- RISK: Docs can drift if updated before final validation; update after command outputs are known.
- ROLLBACK: Revert doc edits that describe unimplemented behavior.

### [ ] Confirm no fallback utility modules were introduced

- WHERE: `backend/`, especially `backend/utils/`, any new `helpers`, `common`, or `misc` paths.
- WHY: The target architecture forbids generic fallback modules that hide responsibilities.
- HOW: Search for new imports and directories named `utils`, `helpers`, `common`, or `misc`. Existing empty `backend/utils/__init__.py` should not gain responsibilities.
- EXPECTED_RESULT: New code uses named business, ability, provider, or infrastructure modules only.
- VERIFY: `rg "utils|helpers|common|misc" backend tests`
- STATUS: pending
- RESULT: Not started.
- RISK: Over-broad grep can match text in docs/tests; inspect matches manually.
- ROLLBACK: Rename or move misplaced code into responsibility-specific modules.

### [ ] Record final verification and remaining risks

- WHERE: `docs/architecture/construction-checklist.md`.
- WHY: Each phase must retain verification evidence, result, unresolved risks, and rollback status.
- HOW: Fill `STATUS`, `RESULT`, `RISK`, and `ROLLBACK` fields after each executed phase with concrete command outputs or failure summaries.
- EXPECTED_RESULT: Checklist becomes an auditable migration log.
- VERIFY: Manual review confirms every completed item has a command/result note.
- STATUS: pending
- RESULT: Not started.
- RISK: Marking tasks complete without command evidence violates the migration gate.
- ROLLBACK: Reopen any item that lacks evidence.
