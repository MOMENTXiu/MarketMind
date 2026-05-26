# Data Processing Pipeline Integration Checklist

> Status note (2026-05-26): Data Processing runtime is implemented and exposed through `/api/analysis/jobs...`; the frontend entry is `/data-processing`. Use `docs/ARCHITECTURE.md`, `docs/backend-api.md`, and `docs/frontend-api-integration-plan.md` for current operation. This checklist remains as migration history.
>
> Target chain:
>
> ```text
> 原始数据上传
>   -> regularization 正则化
>   -> analysis2 通用分析
>   -> 最终结果 / 图表 / 表格 / summary
> ```
>
> New API and state contracts may replace the existing Retail V2 `/api/analysis`
> contract. Do not add compatibility wrappers unless the user explicitly asks
> for one.

## Overall Status

As of 2026-05-26, Phases A through G are completed. The data-processing chain
is fully implemented in backend runtime alongside Retail V2. Two items remain
pending:

- Retire RetailAnalysisFlow after replacement (requires product decision).
- Prune copied generated artifacts from `analysis/data-processing-pipeline/`.
## Current Baseline

- Source archive copied from `origin/add-analysis-2@59440f7` to
  `analysis/data-processing-pipeline/`.
- `regularization/` is the Data Regularization Engine.
- `analysis2/` is the Universal Analysis Engine.
- `analysis/` is the original fixed retail analysis board and should be treated
  as a benchmark/reference, not the default runtime chain.
- Current backend runtime has Retail-specific `/api/analysis`,
  `RetailAnalysisFlow`, retail pipelines, retail abilities, and project-scoped
  artifact/model providers.
- Target backend runtime should replace Retail-specific lifecycle with a
  chain-native data-processing lifecycle.

## 0. Ready-to-Start Gate

### [x] Archive source pipeline directories

- WHERE: `analysis/data-processing-pipeline/`.
- WHY: Keep the new source material available on `main` without making copied
  scripts part of backend runtime.
- HOW: Copy `analysis/`, `analysis2/`, and `regularization/` from
  `origin/add-analysis-2`.
- EXPECTED_RESULT: All three source directories exist under
  `analysis/data-processing-pipeline/`.
- VERIFY: `find analysis/data-processing-pipeline -maxdepth 2 -type d | sort`
- STATUS: completed
- RESULT: Source archive has been copied into the target directory.
- RISK: Large generated artifacts are included because the source branch
  contains them; decide later whether to keep them as fixtures or prune them.
- ROLLBACK: Delete `analysis/data-processing-pipeline/`.

### [x] Define new target chain and non-compatibility rule

- WHERE:
  `docs/architecture/data-processing-pipeline-integration-design.md`,
  this checklist.
- WHY: The migration should follow the new regularization -> universal analysis
  lifecycle, not preserve old Retail V2 API semantics by default.
- HOW: Document the new target chain, source roles, target layering, provider
  boundaries, API replacement direction, and rollback strategy.
- EXPECTED_RESULT: Future agents know that old `/api/analysis` shapes are not a
  required compatibility boundary.
- VERIFY:
  `rg -n "compatibility|chain-native|regularization|analysis2" docs/architecture/data-processing-pipeline-integration-*.md`
- STATUS: completed
- RESULT: Design and checklist state that the new chain can replace old API and
  state contracts.
- RISK: Frontend expectations must be redefined when API replacement begins.
- ROLLBACK: Revert these docs if the product decision changes back to
  compatibility-first migration.

## 1. 测试锚点

### [x] Add chain-native API contract tests

- WHERE: `tests/api/test_data_processing_analysis_contracts.py`.
- WHY: New public API behavior must be defined before replacing old
  `/api/analysis` semantics.
- HOW: Add tests for job create, raw upload, regularize, run, status, output
  listing, output ref resolution, `needs_review`, skipped capability stages, and
  error payloads.
- EXPECTED_RESULT: Tests describe the new chain-native API contract without
  preserving old Retail V2 response fields unless deliberately retained.
- VERIFY: `uv run pytest tests/api/test_data_processing_analysis_contracts.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Add regularization behavior fixtures and golden tests

- WHERE: `tests/fixtures/data_processing/`,
  `tests/abilities/regularization/`.
- WHY: Regularization is the front door of the new chain and must protect field
  mapping, quality, capability, and degradation semantics before extraction.
- HOW: Use small CSV fixtures with English/Chinese columns, bad encodings,
  missing optional fields, generated order id, inferred promo, and
  `need_review` mapping cases.
- EXPECTED_RESULT: Golden tests cover normalized columns, mapping confidence,
  quality score, capability flags, and sidecar JSON shape.
- VERIFY: `uv run pytest tests/abilities/regularization -q`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Add universal analysis behavior fixtures and golden tests

- WHERE: `tests/fixtures/data_processing/`,
  `tests/abilities/universal_analysis/`.
- WHY: `analysis2` modules must preserve capability-driven run/skip/degrade
  behavior when ported into backend abilities.
- HOW: Add normalized dataset + capability fixtures for full capability,
  association skipped by basket structure, recommendation skipped by sparse
  repeat users, and promotion without confounders.
- EXPECTED_RESULT: Golden tests cover module summaries and expected skipped
  states without filesystem writes.
- VERIFY: `uv run pytest tests/abilities/universal_analysis -q`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 2. Provider Interface

### [x] Define regularized dataset DTOs

- WHERE: `backend/providers/dtos.py`.
- WHY: The business layer needs structured refs for raw uploads, normalized
  datasets, mapping, quality, capability, manifest, and previews.
- HOW: Add frozen DTOs such as `RegularizedDatasetReferenceDTO`,
  `RegularizationSidecarReferenceDTO`, `RegularizationCapabilityDTO`, and
  `RegularizationQualityDTO`.
- EXPECTED_RESULT: Provider methods can return typed project/job-scoped refs and
  metadata without exposing local paths.
- VERIFY: `uv run python -m py_compile backend/providers/dtos.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Define RegularizedDatasetProvider

- WHERE: `backend/providers/regularized_dataset_provider.py`,
  `backend/providers/container.py`.
- WHY: Reading raw uploads and persisting normalized datasets/sidecars is a
  storage boundary, not pipeline or ability logic.
- HOW: Define narrow methods for saving raw uploads, loading raw tables,
  saving/loading normalized datasets, saving/loading sidecars, and resolving
  refs. Add the provider to `ProvidersContainer`.
- EXPECTED_RESULT: Business orchestration can use regularized datasets without
  direct filesystem or pandas IO.
- VERIFY:
  `uv run python -m py_compile backend/providers/regularized_dataset_provider.py backend/providers/container.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 3. External Adapter

### [x] Implement LocalRegularizedDatasetAdapter

- WHERE:
  `backend/infrastructure/adapters/local_regularized_dataset_adapter.py`,
  `tests/providers/test_regularized_dataset_adapter.py`.
- WHY: The copied regularization engine currently writes local files directly;
  runtime persistence must be project/job scoped and path-safe.
- HOW: Port file reading, encoding/sheet/header handling, normalized dataset
  persistence, JSON sidecar persistence, ref resolution, and path validation
  into an adapter implementing `RegularizedDatasetProvider`.
- EXPECTED_RESULT: Adapter stores data below
  `data/projects/{project_id}/analysis/regularization/...` and returns opaque
  refs.
- VERIFY: `uv run pytest tests/providers/test_regularized_dataset_adapter.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Wire provider factory

- WHERE: `backend/infrastructure/factories/provider_factory.py`,
  `tests/providers/test_provider_factory.py`.
- WHY: Provider Factory is the only place that should create concrete adapters.
- HOW: Add `regularized_dataset=LocalRegularizedDatasetAdapter(...)` to
  `create_providers`; update fakes for tests.
- EXPECTED_RESULT: `ProvidersContainer` can be assembled with the new provider
  in real and test contexts.
- VERIFY: `uv run pytest tests/providers/test_provider_factory.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 4. Ability Atom

### [x] Extract regularization abilities

- WHERE: `backend/abilities/regularization/`,
  `tests/abilities/regularization/`.
- WHY: Mapping, normalization, quality, and capability logic should be pure
  business actions, not CLI or adapter code.
- HOW: Port and split logic from
  `analysis/data-processing-pipeline/regularization/engine/*` into small
  ability functions: schema profiling, schema mapping, type normalization,
  business normalization, quality checking, capability checking.
- EXPECTED_RESULT: Ability functions accept explicit dataframe/dict inputs and
  return structured data without reading/writing files.
- VERIFY: `uv run pytest tests/abilities/regularization -q`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Extract universal analysis abilities

- WHERE: `backend/abilities/universal_analysis/`,
  `tests/abilities/universal_analysis/`.
- WHY: `analysis2/mod_*` analysis logic must become reusable backend abilities
  with no hard-coded `DATASETS`, `REG_DIR`, or `OUT_ROOT`.
- HOW: Port overview, profile/segmentation, association/HUIM,
  recommendation, promotion/DML, and summary logic into small functions. Figure
  generation returns bytes or figure payloads; CSV/PKL writes are removed.
- EXPECTED_RESULT: Universal abilities run from normalized dataframe +
  capability input and return result objects for pipelines to persist.
- VERIFY: `uv run pytest tests/abilities/universal_analysis -q`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 5. Business Pipeline

### [x] Add DatasetRegularizationPipeline

- WHERE: `backend/business/pipelines/dataset_regularization_pipeline.py`,
  `tests/business/test_data_processing_pipelines.py`.
- WHY: Raw upload -> normalized dataset + sidecars is a business step combining
  provider IO and regularization abilities.
- HOW: Load raw upload through `RegularizedDatasetProvider`, run
  regularization abilities, persist normalized dataset and sidecars, return refs
  and quality/capability summaries.
- EXPECTED_RESULT: A single pipeline converts arbitrary raw data into standard
  schema artifacts.
- VERIFY:
  `uv run pytest tests/business/test_data_processing_pipelines.py::test_dataset_regularization_pipeline`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Add universal analysis pipelines

- WHERE: `backend/business/pipelines/universal_*_pipeline.py`,
  `tests/business/test_data_processing_pipelines.py`.
- WHY: Each analysis family needs orchestration around abilities, artifact
  persistence, skipped states, and model refs.
- HOW: Add overview, profile segmentation, association, recommendation,
  promotion, and summary pipelines. Use `AnalysisArtifactProvider` and
  `AnalysisModelStoreProvider` for outputs.
- EXPECTED_RESULT: Each pipeline can run or skip from normalized dataframe +
  capability input and returns structured refs/results.
- VERIFY: `uv run pytest tests/business/test_data_processing_pipelines.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 6. Business Flow

### [x] Add DataProcessingAnalysisFlow

- WHERE: `backend/business/flows/data_processing_analysis_flow.py`,
  `backend/business/flows/data_processing_analysis_state.py`,
  `tests/business/test_data_processing_analysis_flow.py`.
- WHY: The full lifecycle has multiple stages, long-running job state,
  capability-driven branches, possible `needs_review`, and output refs.
- HOW: Compose regularization and universal analysis pipelines. Persist job
  state, stage statuses, quality/capability summaries, output refs, skipped
  reasons, and errors.
- EXPECTED_RESULT: One flow owns the new chain from upload to final result.
- VERIFY: `uv run pytest tests/business/test_data_processing_analysis_flow.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Retire RetailAnalysisFlow after replacement

- WHERE: `backend/business/flows/retail_analysis_flow.py`,
  `backend/business/pipelines/retail_*`,
  `backend/abilities/retail/*`.
- WHY: The new target does not require long-term compatibility with old
  Retail-only lifecycle.
- HOW: After new flow tests and API contracts pass, delete or fold reused logic
  into regularization/universal analysis modules.
- EXPECTED_RESULT: Backend has one primary analysis lifecycle.
- VERIFY:
  `rg -n "RetailAnalysisFlow|RetailDatasetPreparationPipeline|retail_" backend tests`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 7. API Controller

### [x] Replace analysis API with chain-native contract

- WHERE: `backend/api/analysis.py`,
  `tests/api/test_data_processing_analysis_contracts.py`.
- WHY: Public API should express the new data-processing chain directly instead
  of preserving old Retail V2 project semantics.
- HOW: Implement job/upload/regularize/run/status/output routes according to
  the new contract tests. Controllers call `DataProcessingAnalysisFlow` only.
- EXPECTED_RESULT: API exposes raw upload -> regularization -> universal
  analysis -> output refs as the primary workflow.
- VERIFY: `uv run pytest tests/api/test_data_processing_analysis_contracts.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 8. Architecture Lint / Runtime Check / 全量验证

### [x] Extend Architecture Lint for data-processing source archive

- WHERE: `tests/test_architecture_imports.py`.
- WHY: Backend runtime must not import copied scripts from
  `analysis/data-processing-pipeline/**`.
- HOW: Add rules blocking backend imports from the archive and ensuring
  regularization/universal analysis abilities do not import adapters, FastAPI,
  or filesystem writers.
- EXPECTED_RESULT: Source archive remains reference-only.
- VERIFY: `uv run pytest tests/test_architecture_imports.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Add runtime checks for data-processing chain

- WHERE: `backend/core/runtime_checks.py`,
  `tests/core/test_runtime_checks.py`.
- WHY: Runtime checks should validate provider assembly and sandbox dry-run of
  the new chain.
- HOW: Add commands such as `check-data-processing --sample ... --sandbox`,
  `check-regularization-artifacts --sandbox`, and
  `check-universal-analysis --sample ... --sandbox`.
- EXPECTED_RESULT: Local/CI can verify the chain without writing real project
  data or relying on the source archive outputs.
- VERIFY: `uv run pytest tests/core/test_runtime_checks.py`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

### [x] Run full quality gate

- WHERE: repository root.
- WHY: Migration changes API, providers, adapters, abilities, pipelines, flow,
  runtime checks, and docs.
- HOW: Run the project quality loop from `AGENTS.md`.
- EXPECTED_RESULT: Lint, format, tests, build, and hooks are green or documented
  with explicit blocker.
- VERIFY: `make lint && make format && make lint && make check && make hooks`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:

## 9. 清理与收尾

### [ ] Remove copied generated artifacts if they are not needed as fixtures

- WHERE: `analysis/data-processing-pipeline/**/outputs/`,
  `analysis/data-processing-pipeline/analysis/output/`.
- WHY: The copied source contains generated CSV/PNG/PKL files. They may be too
  heavy for long-term source control unless intentionally used as fixtures.
- HOW: Decide keep-as-fixtures vs prune. If pruning, keep small representative
  fixtures under `tests/fixtures/data_processing/` and document the policy.
- EXPECTED_RESULT: Repository contains only useful reference/source/fixture
  artifacts.
- VERIFY:
  `find analysis/data-processing-pipeline -path '*output*' -o -path '*outputs*' | wc -l`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [x] Update project docs and agent baseline

- WHERE: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/QUICKSTART.md`,
  `docs/USAGE_GUIDE.md`.
- WHY: Once the new chain becomes runtime behavior, project docs must stop
  describing Retail V2 as the primary analysis lifecycle.
- HOW: Update architecture diagrams, API route summaries, quality baseline,
  runtime check commands, and source-archive policy.
- EXPECTED_RESULT: Future agents and humans see the new chain as the canonical
  backend path.
- VERIFY:
  `rg -n "RetailAnalysisFlow|Retail V2|data-processing|regularization|analysis2" AGENTS.md docs`
- STATUS: completed
- RESULT:
- RISK:
- ROLLBACK:
