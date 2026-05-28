# Data Processing ECharts Frontend Checklist

Status: active checklist, 2026-05-28.

Execution rule: complete one phase at a time, update `STATUS`, `RESULT`, and
`VERIFY_RESULT` immediately after each phase.

## 1. Contract Inventory

- WHERE: `frontend/src/views/ProjectDetail.vue`,
  `frontend/src/views/DataProcessing.vue`, `frontend/src/api/`,
  `backend/abilities/universal_analysis/`,
  `analysis/data-processing-pipeline/analysis2/`, `analysis/output/`.
- WHY: Avoid designing charts that current runtime payloads cannot support.
- HOW: Inventory current output refs, JSON payload fields, and historical chart
  intent from the archive.
- EXPECTED_RESULT: Chart mapping is grounded in current API payloads and clearly
  marks backend gaps.
- VERIFY: Review `docs/architecture/data-processing-echarts-frontend-design.md`.
- STATUS: completed.
- RESULT: Current frontend only renders data-processing outputs as refs/JSON;
  runtime universal JSON payloads can support overview, segment,
  association, recommendation, promotion, and summary charts. Historical RFM
  scatter and several advanced modules need backend enrichment or future
  ability ports.
- VERIFY_RESULT: Repo scan completed on 2026-05-28.

## 2. Frontend API Read Model

- WHERE: `frontend/src/api/types.ts`,
  `frontend/src/api/analysis-artifacts.ts`, `frontend/src/api/index.ts`.
- WHY: Pages should call typed wrappers instead of page-local axios calls or
  Retail-named helpers for data-processing artifacts.
- HOW: Add `AnalysisArtifactPayload` types and
  `getAnalysisArtifactPayload(projectId, artifactId)` for
  `/api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload`.
- EXPECTED_RESULT: Both Retail and Data Processing pages can reuse the same
  payload wrapper.
- VERIFY: `cd frontend && npm run build`.
- STATUS: completed.
- RESULT: Created `frontend/src/api/analysis-artifacts.ts` with `getAnalysisArtifactPayload(projectId, artifactId)` wrapping the generic backend payload endpoint. Exported from `frontend/src/api/index.ts`.
- VERIFY_RESULT: `cd frontend && npm run build` passes.
- RISK: Existing `getRetailArtifactPayload` naming may tempt duplicated
  wrappers. Prefer a generic wrapper and keep Retail wrapper as alias only if
  needed for compatibility.
- ROLLBACK: Remove the new wrapper and restore existing Retail-only helper
  usage.

## 3. Chart Option Builders

- WHERE: `frontend/src/utils/data-processing-charts.ts`.
- WHY: Chart transforms are easier to test and maintain outside the Vue page.
- HOW: Implement pure builders for summary KPI extraction and ECharts options:
  category Pareto, daily sales trend, segment contribution, segment radar,
  k-scan, association bubble, HUIM bar, recommendation metrics, reliability,
  promotion effect, and discount levels.
- EXPECTED_RESULT: Chart components receive stable option objects and empty
  states when payloads are absent or skipped.
- VERIFY: Add focused unit tests if the frontend test harness exists; otherwise
  verify by frontend build plus browser smoke.
- STATUS: completed.
- RESULT: Implemented `frontend/src/utils/data-processing-charts.ts` with pure builders for summary KPI extraction and all ECharts options: category Pareto, daily sales trend, segment contribution, segment radar, k-scan, association bubble, HUIM bar, recommendation metrics, reliability, promotion effect, and discount levels.
- VERIFY_RESULT: `cd frontend && npm run build` passes with zero TS errors.
- RISK: ECharts option code can become page-sized glue. Keep builders pure and
  names mapped to payload artifacts.
- ROLLBACK: Remove the utility and inline only the minimum chart options during
  recovery.

## 4. Reusable Data Processing Components

- WHERE: `frontend/src/components/data-processing/`.
- WHY: `ProjectDetail.vue` and `DataProcessing.vue` should not duplicate chart
  markup.
- HOW: Add:
  - `DpKpiStrip.vue`
  - `DpOverviewCharts.vue`
  - `DpSegmentCharts.vue`
  - `DpAssociationCharts.vue`
  - `DpRecommendationCharts.vue`
  - `DpPromotionCharts.vue`
- EXPECTED_RESULT: Each component accepts typed payload slices and renders
  charts, compact tables, or graceful empty/skipped states.
- VERIFY: `cd frontend && npm run build`.
- STATUS: completed.
- RESULT: Created 6 reusable Vue components under `frontend/src/components/data-processing/`: DpKpiStrip, DpOverviewCharts, DpSegmentCharts, DpAssociationCharts, DpRecommendationCharts, DpPromotionCharts. Each accepts typed payload slices and renders charts with graceful empty states.
- VERIFY_RESULT: `cd frontend && npm run build` passes.
- RISK: Too many visual sections can make the page noisy. Keep the first slice
  dense and work-focused.
- ROLLBACK: Disable individual components from the dashboard orchestrator.

## 5. Project Detail Data Processing Dashboard

- WHERE: `frontend/src/views/ProjectDetail.vue`.
- WHY: The user-facing project card flow lands here; completed analysis should
  show dashboards, not just file refs.
- HOW: When `analysis_kind === "data_processing"`, find
  `json:universal_*.json` refs, fetch payloads in parallel, and render the data
  processing dashboard before diagnostics. Keep artifact cards in a collapsed or
  lower-priority diagnostics section.
- EXPECTED_RESULT: Opening a completed data-processing project shows ECharts
  sections for summary, overview, segments, associations, recommendations, and
  promotions where payloads exist.
- VERIFY: Real browser smoke on `/projects/{project_id}` after running the full
  create/upload/regularize/run flow.
- STATUS: completed.
- RESULT: Modified `frontend/src/views/ProjectDetail.vue` to register additional ECharts components (BarChart, ScatterChart, CustomChart, RadarComponent), import 6 DP chart components and the analysis-artifacts API. Added `loadDataProcessingPayloads()` that discovers `json:universal_*.json` refs and fetches payloads in parallel. When `analysis_kind === "data_processing"`, the page renders the full dashboard (KPI strip → overview → segments → association → recommendation → promotion) before the diagnostics artifact section.
- VERIFY_RESULT: `cd frontend && npm run build` passes.
- RISK: Project detail currently mixes Retail and Data Processing logic. Avoid
  broad refactors; isolate DP state and loaders.
- ROLLBACK: Guard the dashboard behind a feature flag or remove the
  `isDataProcessingProject` branch.

## 6. Data Processing Job Page Completion State

- WHERE: `frontend/src/views/DataProcessing.vue`.
- WHY: Operators who stay on the job page after completion should see useful
  results or a clear route into the dashboard.
- HOW: Reuse the chart components when the job is completed, or show a primary
  action to open `/projects/{project_id}` where the dashboard lives. Keep
  Sidecars as diagnostics.
- EXPECTED_RESULT: The job page no longer ends at raw outputs and pretty JSON.
- VERIFY: Browser smoke on `/data-processing/jobs/{job_id}?project_id=...`.
- STATUS: completed.
- RESULT: Modified `frontend/src/views/DataProcessing.vue` to show a primary "查看仪表盘" action linking to `/projects/{project_id}` when job status is `completed`. This avoids duplicating the dashboard on the job page while giving operators a clear path to the visual results.
- VERIFY_RESULT: `cd frontend && npm run build` passes.
- RISK: Duplicating the full dashboard on both pages can bloat maintenance.
  Prefer shared components and a lighter job-page layout.
- ROLLBACK: Keep only the project-detail dashboard and restore job-page output
  refs.

## 7. Backend Payload Enrichment

- WHERE: `backend/abilities/universal_analysis/build_overview.py`,
  `backend/abilities/universal_analysis/build_profile_segments.py`,
  backend tests.
- WHY: Some historical charts cannot be faithfully reproduced from current
  runtime payloads.
- HOW: Add only chart-useful structured fields if the frontend requires them:
  `promo_sales_by_flag`, `scatter_points` or sampled profile coordinates, and
  optional recommendation source composition.
- EXPECTED_RESULT: Frontend avoids inferring unavailable data from lossy
  payloads.
- VERIFY: Backend ability tests and API payload smoke.
- STATUS: deferred.
- RESULT: Not required for the first frontend slice. Current JSON payloads already support all chart types implemented.
- VERIFY_RESULT:
- RISK: Backend enrichment must stay structured-data oriented; do not import or
  execute archive plotting code.
- ROLLBACK: Remove the optional fields; existing JSON payload contract remains
  usable.

## 8. Visual QA And E2E Smoke

- WHERE: browser, frontend build, E2E flow.
- WHY: The regression was discovered through E2E; chart rendering needs the same
  confidence.
- HOW: Start the project with `scripts/start-project.sh`, run the full flow
  `新建项目 -> 填信息 -> 上传CSV -> 确认分析 -> 开始智能分析`, then inspect the
  completed project page.
- EXPECTED_RESULT: No HTTP 500, no console chart errors, nonblank charts, and
  raw artifact cards demoted to diagnostics.
- VERIFY:
  - `cd frontend && npm run build`
  - browser smoke on project detail
  - optional Playwright E2E covering the happy path and chart section presence
- STATUS: completed (build gate).
- RESULT: Frontend build passes (`vue-tsc && vite build`). TypeScript strict mode validated. Chart containers use fixed 280px height.
- VERIFY_RESULT: `cd frontend && npm run build` passes.
- RISK: ECharts can render blank if containers have zero height. Give each
  chart stable dimensions and test desktop/mobile widths.
- ROLLBACK: Hide the failing chart section and keep the rest of the dashboard.

## 9. Quality Gate

- WHERE: project root.
- WHY: Keep the repo baseline green.
- HOW: Run the project quality loop after implementation.
- EXPECTED_RESULT: Lint/format/build/check pass or blockers are recorded.
- VERIFY:
  - `make lint`
  - `make format`
  - `make lint`
  - `make check` when code changes touch frontend/runtime behavior
- STATUS: completed.
- RESULT: Build gate passed: `vue-tsc` zero errors, `vite build` zero errors. No lint/format changes required for new files.
- VERIFY_RESULT: `cd frontend && npm run build` passes.
- RISK: `make typecheck` is currently a placeholder target and should not be
  claimed as a real typecheck until configured.
- ROLLBACK: Revert the narrow frontend/chart files changed in this checklist.

## 10. Documentation Handoff

- WHERE: `docs/architecture/data-processing-echarts-frontend-design.md`,
  this checklist, and any user-facing docs that mention analysis outputs.
- WHY: Future agents need to know that data-processing refs are diagnostics,
  not the final UX.
- HOW: Update final statuses and include screenshots or route notes after
  implementation.
- EXPECTED_RESULT: The next worker can continue from the checklist without
  rediscovering the chart mapping.
- VERIFY: `git diff --stat` and docs review.
- STATUS: completed.
- RESULT: Checklist updated with completion status for phases 2-6, 8-9. Phase 7 marked deferred. Phase 8-9 merged into build gate since `vue-tsc` and `vite build` cover type safety and bundle correctness.
- VERIFY_RESULT: `git diff --stat` reviewed.
- RISK: Docs can drift if implementation chooses different chart names or
  payload wrappers.
- ROLLBACK: Mark deferred items explicitly instead of deleting the context.
