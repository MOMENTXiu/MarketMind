# Data Processing Pipeline Integration Design

> Status: **implemented**. Backend runtime code has been extracted and migrated
> according to this design. The document remains accurate as an architecture
> reference.
> Source snapshot: `origin/add-analysis-2` at `59440f7`.
> Source archive location on `main`: `analysis/data-processing-pipeline/`.

## Goal

Make the new data-processing chain the primary backend analysis lifecycle:

```text
raw data upload
  -> regularization
  -> analysis2 universal analysis
  -> final result / figures / tables / summary
```

The current backend has a Retail V2-specific path:

```text
/api/analysis
  -> RetailAnalysisFlow
  -> RetailDatasetPreparationPipeline
  -> Retail feature / segmentation / association / recommendation / marketer / report pipelines
  -> backend/abilities/retail/*
  -> RetailDatasetProvider / AnalysisArtifactProvider / AnalysisModelStoreProvider
  -> local adapters under data/projects/{project_id}/analysis/...
```

The new chain supersedes that Retail-specific lifecycle. Existing backend
modules may be reused when they fit the new design, but no old API schema,
status shape, route naming, or Retail-only internal stage layout is a
compatibility requirement. The copied folders are reference implementations and
fixtures; backend runtime code must not import them directly.

## Copied Source Roles

| Source directory | Role | Runtime decision |
| --- | --- | --- |
| `analysis/data-processing-pipeline/regularization/` | Data Regularization Engine. Reads arbitrary CSV/XLS/XLSX, infers field mapping, normalizes types and business fields, outputs `dataset.csv`, `capability.json`, mapping, quality, manifest, preview rows. | Extract into backend Ability Atoms and an External Adapter-backed provider. Do not run `run_regularization.py` from API code. |
| `analysis/data-processing-pipeline/analysis2/` | Universal Analysis Engine. Reads normalized `dataset.csv` + `capability.json`, runs modules by capability, emits figures, CSVs, PKLs, and summary JSON. | Extract module logic into backend abilities and pipelines. Keep capability-driven skip/degrade semantics. |
| `analysis/data-processing-pipeline/analysis/` | Original fixed retail analysis board. It is a domain benchmark and algorithm blueprint for the earlier Retail V2 implementation. | Keep as reference. Do not make it part of the default upload pipeline. Use it to compare quality or port stronger methods into backend abilities. |

## Current Chain Assessment

The user-proposed chain is correct with one clarification:

```text
原始数据上传 -> regularization 正则化 -> analysis2 通用分析 -> 最终结果
```

`analysis/` is not the default middle step. It is a fixed-dataset analysis
baseline. `analysis2/` is the generalized downstream analysis module.

The current `regularization` to `analysis2` link is file-based and offline:

- `regularization.save_all(...)` writes `outputs/{dataset}/dataset.csv` and
  `outputs/{dataset}/capability.json`.
- `analysis2/config_3.py` reads from
  `analysis2/data/regularized/{dataset}/dataset.csv` and `capability.json`.
- In the source branch, `order_1` and `order_2` normalized files are identical
  between `regularization/outputs/*` and `analysis2/data/regularized/*`.

Therefore the migration target is not to preserve that manual copy step, but to
replace it with provider-managed project-scoped refs:

```text
data/projects/{project_id}/analysis/
  datasets/
    raw_upload
    normalized_dataset.csv
    capability.json
    schema_mapping.json
    quality_report.json
  artifacts/
    csvs/
    figures/
    summaries/
  models/
```

## Target Layering

### API Controller

Replace the Retail V2 API surface with a chain-native API. Controllers should
own request parsing, file upload reading, response schema shaping, and internal
error mapping only. They should not preserve old response fields just because
the previous Retail V2 API exposed them.

Suggested route shape:

- `POST /api/analysis/jobs` creates an analysis job and accepts upload metadata.
- `POST /api/analysis/jobs/{job_id}/raw-dataset` uploads raw data.
- `POST /api/analysis/jobs/{job_id}/regularize` runs or re-runs
  regularization.
- `POST /api/analysis/jobs/{job_id}/run` runs universal analysis from the
  regularized dataset and capability profile.
- `GET /api/analysis/jobs/{job_id}` returns job state, stage status, quality,
  capability, output refs, and result summary.
- `GET /api/analysis/jobs/{job_id}/outputs` lists figures, tables, model refs,
  summaries, and reports.
- `GET /api/analysis/outputs/{ref_id}` resolves opaque output refs.

These names are recommendations. The API contract should be defined by new
tests before implementation, not constrained by the current `/api/analysis`
project routes.

### Business Orchestration Layer

The target lifecycle is complex enough to remain a Business Flow:

```text
UniversalAnalysisFlow
  -> DatasetRegularizationPipeline
  -> UniversalOverviewPipeline
  -> UniversalProfileSegmentationPipeline
  -> UniversalAssociationPipeline
  -> UniversalRecommendationPipeline
  -> UniversalPromotionPipeline
  -> UniversalReportPipeline or result aggregation step
```

Default recommendation: introduce a new `DataProcessingAnalysisFlow` or
`UniversalAnalysisFlow`, make it the target flow, and then delete or fold the
Retail-specific flow after its useful abilities/providers are ported. Avoid
parallel long-term support paths.

### Ability Layer

Extract pure functions from `regularization/engine/*` and `analysis2/mod_*` into
small backend abilities. Initial ability groups:

```text
backend/abilities/regularization/
  read_source_table.py
  profile_source_schema.py
  infer_schema_mapping.py
  normalize_field_types.py
  normalize_business_fields.py
  check_data_quality.py
  check_analysis_capability.py

backend/abilities/universal_analysis/
  build_overview.py
  build_profile_segments.py
  mine_universal_associations.py
  rank_universal_recommendations.py
  estimate_universal_promotion_effect.py
  build_universal_summary.py
```

Ability rules:

- no direct file writes;
- no FastAPI imports;
- no provider factory or adapter imports;
- external side effects only through Provider interfaces when truly necessary;
- plotting can return figure bytes / structured figure payloads, not write to
  `analysis2/outputs`.

### Provider Boundary

Add narrow Provider interfaces instead of widening `RetailDatasetProvider`
around a universal concern.

Proposed providers:

| Provider | Purpose |
| --- | --- |
| `RegularizedDatasetProvider` | Save/load raw upload, normalized dataset, mapping, quality, capability, manifest, and preview rows behind opaque project-scoped refs. |
| `UniversalAnalysisArtifactProvider` or extend `AnalysisArtifactProvider` | Save analysis2-style tables, figures, JSON summaries, Markdown reports as project artifacts. Prefer extending existing `AnalysisArtifactProvider` only if current methods stay sufficient. |
| `UniversalAnalysisModelStoreProvider` or use `AnalysisModelStoreProvider` | Save segmentation/recommendation models when universal analysis needs model persistence. Existing model store may be sufficient. |

The current `AnalysisArtifactProvider` and `AnalysisModelStoreProvider` are
already good project-scoped boundaries. The main gap is a generic regularized
dataset boundary and DTOs for capability/mapping/quality metadata.

### Infrastructure Layer

Implement adapters that own filesystem and pandas IO:

```text
backend/infrastructure/adapters/local_regularized_dataset_adapter.py
backend/infrastructure/adapters/universal_analysis_artifact_adapter.py  # only if needed
```

Adapter responsibilities:

- read uploaded files with encoding/sheet/header detection;
- persist standard dataset and JSON sidecars under `data/projects/{id}/analysis`;
- reject path traversal and unsafe identifiers;
- convert pandas/IO exceptions to internal errors;
- return opaque refs without local paths.

### Provider Factory

`backend/infrastructure/factories/provider_factory.py` should assemble the new
provider fields from `Settings`. Business code must not create adapters or read
env.

## Current Direct-Dependency Risks In Source Engines

The copied engines are useful but not runtime-safe as-is:

- `regularization/engine/pipeline.py` directly reads/writes files via pandas and
  `os`.
- `regularization/run_regularization.py` is a CLI driver with stdout side
  effects and fixed `outputs/`.
- `analysis2/config_3.py` hard-codes `DATASETS`, `REG_DIR`, and `OUT_ROOT`.
- `analysis2/analysis_engine.py` imports modules directly, writes summary files,
  and catches broad exceptions for console output.
- `analysis2/mod_*` modules write CSV/figures/PKLs through `config_3` helpers.

These are exactly the parts to split across Adapter, Ability, Pipeline, and Flow
instead of importing from the archive.

## Target State Machine

Recommended stage order:

```text
queued
  dataset_regularization: queued | processing | completed | failed | needs_review
  overview: queued | processing | completed | skipped | failed
  profile_segmentation: queued | processing | completed | skipped | failed
  association: queued | processing | completed | skipped | failed
  recommendation: queued | processing | completed | skipped | failed
  promotion: queued | processing | completed | skipped | failed
  summary: queued | processing | completed | failed
completed | failed
```

`needs_review` is needed because regularization marks mappings with
`need_review` when confidence is below the auto-adopt threshold. The first
implementation may avoid manual confirmation by requiring only auto-confirmed
mappings, but the state model should leave room for review.

## Behavior Anchors

Before migrating behavior, tests must define and protect the new contract:

- chain-native job creation, upload, regularization, run, status, and output
  listing contracts;
- upload rejects unsafe filenames, unsupported files, and unreadable datasets;
- output refs remain path-free and project/job-scoped;
- job state is project/job-scoped and persists through the chosen model/state
  store;
- capability-driven skip/degrade semantics from `analysis2`;
- regularization output schema: `dataset.csv`, `capability.json`,
  `schema_mapping.json`, `schema_mapping_detail.json`, `quality_report.json`,
  `manifest.json`, `preview_rows.json`;
- `needs_review` mapping state, if exposed, has explicit API semantics;
- no runtime writes to `analysis/data-processing-pipeline/**` or
  `analysis/output/**`.

## Migration Strategy

### Phase A: introduce documentation and archived source

**Completed.** Copied `analysis`, `analysis2`, and `regularization` into
`analysis/data-processing-pipeline/`; documented the target chain and migration
plan.

### Phase B: define new behavior

**Completed.** Added chain-native API contract tests
(`tests/api/test_data_processing_analysis_contracts.py`), regularization golden
tests (`tests/abilities/regularization/`), and universal analysis golden tests
(`tests/abilities/universal_analysis/`).

### Phase C: extract provider boundary

**Completed.** Added `RegularizedDatasetReferenceDTO`,
`RegularizationSidecarReferenceDTO`, and related DTOs to
`backend/providers/dtos.py`. Defined `RegularizedDatasetProvider` protocol in
`backend/providers/regularized_dataset_provider.py`. Wired it into
`ProvidersContainer`.

### Phase D: adapter extraction

**Completed.** Implemented `LocalRegularizedDatasetAdapter` in
`backend/infrastructure/adapters/local_regularized_dataset_adapter.py`. Added
`FakeRegularizedDatasetProvider` for tests. Wired adapter in
`backend/infrastructure/factories/provider_factory.py`.

### Phase E: ability extraction

**Completed.** Extracted 7 regularization abilities
(`backend/abilities/regularization/`) and 6+ universal analysis abilities
(`backend/abilities/universal_analysis/`) from the archive. Abilities return
pure data structures (no file writes, no FastAPI imports).

### Phase F: pipeline and flow composition

**Completed.** Added `DatasetRegularizationPipeline`, 6 universal analysis
pipelines, and `DataProcessingAnalysisFlow` with full state machine,
capability-driven skipping, and `needs_review` handling.

### Phase G: API replacement

**Completed.** Added chain-native routes under `/api/analysis/jobs` (create,
upload, regularize, run, status, outputs) alongside existing Retail V2 routes.
Retirement of Retail V2 internals is a future product decision, not yet executed.

## Rollback Strategy

Every stage should be reversible:

- archive-only copy rollback: delete `analysis/data-processing-pipeline/`;
- docs rollback: remove this design and checklist;
- provider/adapter rollback: remove new provider fields and factory wiring;
- ability/pipeline/flow rollback: remove new backend modules and tests;
- API rollback: revert route/schema changes to the previous committed state.

Do not keep compatibility wrappers as a default rollback strategy. Prefer small
commits and stage-level revertability.
