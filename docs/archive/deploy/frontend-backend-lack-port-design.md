# Frontend Backend Lack-port Architecture Design

Status: active design, 2026-05-27.

## Current Call Chain

Current documented Retail V2 API path:

```text
Vue page -> frontend/src/api/retail.ts -> /api/analysis/projects...
  -> backend/api/analysis.py
  -> RetailAnalysisFlow
  -> Retail pipelines
  -> AnalysisArtifactProvider / AnalysisModelStoreProvider / RetailDatasetProvider
  -> Local adapters
```

The backend already persists Retail V2 result tables as artifact refs:

- `table:retail_item_association_rules.csv`
- `table:retail_customer_segments.csv`
- `table:retail_segment_profile.csv`
- `table:retail_recommendations.csv`

The current public artifact endpoint returns only ref metadata:

```text
GET /api/analysis/projects/{project_id}/artifacts/{artifact_id}
```

Frontend pages therefore cannot render artifact-backed tables without either stale legacy `project.results` fields or page-local fake derivation.

## Direct Access Points

| Current file | Current access | Target |
| --- | --- | --- |
| `frontend/src/views/ProjectDetail.vue` | Legacy `project.results.association_rules` and synthetic customer rows | Fetch artifact payload through typed API wrapper. |
| `backend/infrastructure/adapters/local_analysis_artifact_adapter.py` | Writes table/json/markdown artifacts and resolves refs only | Add read-only payload loading inside the adapter. |
| `backend/providers/analysis_artifact_provider.py` | Provider exposes save/resolve only | Add read-only `load_payload` provider method. |
| `backend/business/flows/retail_analysis_flow.py` | Lists refs and resolves metadata | Add read-only artifact payload flow method. |
| `backend/api/analysis.py` | Controller exposes metadata endpoint | Add payload endpoint that maps flow result into the standard envelope. |

## Target Architecture

```text
API Controller
  -> RetailAnalysisFlow
  -> AnalysisArtifactProvider.load_payload(...)
  -> LocalAnalysisArtifactAdapter
```

This remains a read-only Retail V2 read model path. No new Business Pipeline or Business Flow lifecycle is required because the operation does not run analysis, mutate state, schedule jobs, or call external systems.

## Provider Boundary

Add:

```text
AnalysisArtifactProvider.load_payload(project_id, artifact_id)
```

Return a provider DTO that contains:

- public artifact ref metadata
- `payload_type`
- `rows` for table artifacts
- `payload` for JSON artifacts
- `content` for Markdown artifacts

Do not expose local filesystem paths, pandas objects, or raw SDK/client objects.

## API Contract

Add:

```text
GET /api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload
```

Success shape:

```json
{
  "success": true,
  "data": {
    "project_id": "...",
    "artifact": {},
    "payload_type": "table|json|markdown",
    "rows": [],
    "payload": null,
    "content": null
  }
}
```

404 when the project or artifact does not exist.

400 when the artifact type is unsupported for payload reads, such as figures.

## Behavior Anchors

- Existing artifact metadata endpoint must keep returning metadata only.
- Retired routes `/api/projects`, `/api/recommend`, and `/api/association` remain absent.
- Artifact payload response must not include local path markers such as `/Users/`, `data/projects`, or `outputs/`.
- Table rows must be JSON-safe; NaN and infinities become `null`.

## Validation Strategy

- API contract test for artifact payload shape and path-free rows.
- Frontend build after typed wrapper and page connection.
- `make lint`, `make format`, `make lint`, `make check`.
- Browser smoke: project detail page renders without app console errors.

## Rollback

Phase 1 rollback is file-scoped:

- Remove the new artifact payload provider DTO/method.
- Remove `LocalAnalysisArtifactAdapter.load_payload`.
- Remove `RetailAnalysisFlow.get_artifact_payload`.
- Remove `GET /api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload`.
- Revert frontend to previous fallback behavior.

No data migration is required because the endpoint reads existing artifacts only.
