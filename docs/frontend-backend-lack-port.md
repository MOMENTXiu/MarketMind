# Frontend Backend Lack-port

Status: active audit, 2026-05-27.

This document records frontend surfaces that are visible in Vue but are not fully backed by a documented backend API in `docs/backend-api.md`.

## Connected By Documented API

| Frontend surface | Current API | Status |
| --- | --- | --- |
| Service status | `GET /api/health/` | Connected. |
| Project list/create/delete/detail/run | `/api/analysis/projects...` | Connected. |
| Retail dataset upload | `POST /api/analysis/projects/{project_id}/dataset` | Connected. |
| Retail recommendations | `GET /api/analysis/projects/{project_id}/recommendations` | Connected. |
| Retail marketer insights | `GET /api/analysis/projects/{project_id}/marketer-insights` | Connected. |
| Data Processing job flow | `/api/analysis/jobs...` | Connected. |
| Text-only AI suggestions | `POST /api/analysis/customer-suggestions` | Connected. |

## Lack-port Items

| ID | Frontend surface | Current frontend behavior | Backend API doc status | Category | Decision |
| --- | --- | --- | --- | --- | --- |
| LP-001 | `ProjectDetail.vue` association rule grid | Reads legacy `project.results.association_rules`; current Retail V2 project detail does not document this field. | Missing. Retail artifacts are documented only as refs, not payloads. | Missing read model | Add a read-only artifact payload endpoint and use the existing `retail_item_association_rules.csv` artifact. |
| LP-002 | `ProjectDetail.vue` cluster customer list | Synthesizes customer rows from recommendation customer IDs with zero RFM metrics. | Missing. No documented Retail customer list endpoint. | Missing read model | Use the existing `retail_customer_segments.csv` artifact through the same payload endpoint. |
| LP-003 | `CustomerAnalysis.vue` purchased item list | Always empty. | Missing. No documented customer purchase history endpoint. | Missing domain read model | Defer. Requires a customer detail/read-model API or a clean-sales payload policy. |
| LP-004 | `ProjectDetail.vue` realtime association recalculation | Shows "Retail V2 暂无实时关联重算结果". | Missing. Retired `/api/association` must remain absent. | Missing command endpoint | Defer. Requires explicit API contract and business semantics. |
| LP-005 | `ProjectDetail.vue` forecast chart | Reads legacy `project.results.prediction_data`. | Missing for Retail V2. | Stale frontend expectation | Defer. Either remove the chart or add a forecast artifact/read model in a separate phase. |
| LP-006 | `ProductRecommend.vue` upstream/downstream relation graph | Uses recommendations as downstream only; no true item relation API. | Missing. Existing recommendations endpoint is customer/item recommendation, not association graph. | Missing read model | Defer after LP-001; can derive from artifact payload or add dedicated item-relations endpoint. |

## Phase 1 Scope

Implement LP-001 and LP-002 only.

Reason:

- They reuse existing Retail V2 analysis artifacts already produced by backend pipelines.
- They do not revive retired `/api/association`, `/api/recommend`, or `/api/projects` routes.
- They need only a read-only Provider method and one new public route under `/api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload`.

Out of scope for Phase 1:

- Approval endpoint for Data Processing `needs_review`.
- Realtime association recalculation.
- Customer purchase history.
- Forecast chart backend semantics.
- Item relation graph command/search API.
