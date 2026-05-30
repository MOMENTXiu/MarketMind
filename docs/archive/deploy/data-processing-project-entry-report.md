# Data Processing Project Entry Investigation Report

> Date: 2026-05-28
> Scope: investigate why the expected "My Projects -> New Project -> upload CSV -> automatic regularization -> analysis -> project card/detail" E2E path is not working.

## Expected Product Flow

The expected user path is:

1. User opens "我的项目".
2. User clicks "新建项目".
3. User fills project name and description.
4. User uploads CSV data.
5. User confirms analysis.
6. System runs data regularization first.
7. If regularization fails or needs review, the flow stops and shows the error/review state.
8. If regularization succeeds, system runs data processing analysis.
9. The final result appears as a project in "我的项目"; clicking the project card opens the result/detail view.

## Current Behavior

The current frontend has two separate lifecycles:

| UI surface | Current route | Backend API used | Actual lifecycle |
| --- | --- | --- | --- |
| "我的项目" / "新建项目" | `/projects`, `/projects/new`, `/projects/:id` | `/api/analysis/projects...` | Retail V2 project lifecycle |
| "数据处理" | `/data-processing`, `/data-processing/jobs/:jobId` | `/api/analysis/jobs...` | Data Processing Job lifecycle |

This means the implemented Data Processing chain is not the lifecycle behind "新建项目". It is exposed through a standalone page and separate job routes.

## Frontend Findings

### F1. "新建项目" still calls Retail V2 APIs

`frontend/src/views/ProjectCreate.vue` imports `createRetailProject`, `uploadRetailDataset`, and `runRetailAnalysis`, then calls them in sequence.

Evidence:

- `ProjectCreate.vue` imports Retail wrappers at lines 7-12.
- `createProject()` calls `createRetailProject()`, `uploadRetailDataset()`, and `runRetailAnalysis()` at lines 54-71.
- The upload validator says "Retail V2 仅支持 CSV 文件" at lines 40-43.

Impact:

- The expected Data Processing chain is not triggered from the main new-project flow.
- The flow skips `regularizeDataProcessingJob()` entirely.
- Any E2E test expecting `/api/analysis/jobs` from "新建项目" will fail.

### F2. Data Processing is a standalone page with a manual `project_id`

`frontend/src/views/DataProcessing.vue` is a separate workflow that asks for `project_id` and job name, then performs create/upload/regularize/run manually.

Evidence:

- It defaults `project_id` to `demo-project` when the route query has no project id at lines 43-45.
- `createJob()` requires both `project_id` and job name at lines 238-244.
- It navigates to `/data-processing/jobs/{job_id}?project_id=...` at line 251.
- Upload, regularize, and run are separate button handlers at lines 259-310.

Impact:

- Users must understand an internal job concept.
- The job is not naturally created from a project card.
- The result lives under a job route, not the project detail route.

### F3. Navigation advertises two competing primary entries

`frontend/src/App.vue` includes both "我的项目" and "数据处理" as top-level nav entries, and the header CTA points to `/projects/new`.

Evidence:

- "我的项目" nav link points to `/projects` at line 65.
- "数据处理" nav link points to `/data-processing` at line 66.
- Header "新建项目" button points to `/projects/new` at lines 78-83.

Impact:

- The UI communicates that Data Processing is a separate tool rather than the default project creation lifecycle.
- The CTA that users naturally choose still goes to the old Retail V2 flow.

### F4. "我的项目" only lists Retail projects

`frontend/src/views/ProjectList.vue` loads projects through `listRetailProjects()` and opens `/projects/{id}`.

Evidence:

- Imports `listRetailProjects` and `deleteRetailProject` at lines 6-12.
- `loadProjects()` calls `listRetailProjects()` at lines 21-25.
- Card click opens `/projects/{id}` at lines 37-39.

Impact:

- Data Processing jobs do not appear in "我的项目" unless the backend also writes a project state that this endpoint can list.
- Even if a Data Processing job completes successfully, it is invisible from the project card flow.

## Backend Findings

### B1. Data Processing backend chain exists and is exposed as jobs

The chain-native endpoints exist under `/api/analysis/jobs`.

Evidence:

- `DataProcessingJobCreate` requires `project_id` and `name` at `backend/api/analysis.py` lines 45-55.
- Job create/upload/regularize/run/get/events/output routes are defined in `backend/api/analysis.py` from lines 295 onward.
- `DataProcessingAnalysisFlow` has `create_job()`, `upload_raw_dataset()`, `regularize()`, and `run_analysis()` at `backend/business/flows/data_processing_analysis_flow.py` lines 56-163.

Impact:

- The backend processing chain is available.
- The missing part is not the regularization/analysis chain itself; the missing part is project-entry integration.

### B2. Retail project state and Data Processing job state are separate models

Retail projects are stored and listed through `RetailAnalysisFlow`, while Data Processing jobs are stored as `data_processing_analysis_state` in `AnalysisModelStoreProvider`.

Evidence:

- Retail `create_project()` creates a project state with `id`, `name`, `status`, `stage_statuses`, `dataset_ref`, and `artifact_refs` at `backend/business/flows/retail_analysis_flow.py` lines 46-73.
- Retail `list_projects()` reads `retail_analysis_state.list_projects()` at lines 75-81.
- Data Processing uses `JOB_STATE_MODEL_TYPE = "data_processing_analysis_state"` at `data_processing_analysis_flow.py` line 40.
- Data Processing `create_job()` writes a job state but does not create or update a Retail project at lines 56-62.

Impact:

- A Data Processing job can run without being represented as a project card.
- `/api/analysis/projects` cannot list Data Processing jobs.
- `/api/analysis/projects/{id}` cannot load Data Processing job results unless a mapping layer is introduced.

### B3. Project endpoints still execute Retail V2, not Data Processing

The project endpoints call `RetailAnalysisFlow` only.

Evidence:

- `POST /api/analysis/projects` depends on `get_retail_analysis_flow` and calls `flow.create_project()` at `backend/api/analysis.py` lines 149-158.
- `POST /api/analysis/projects/{project_id}/dataset` calls `flow.upload_dataset()` at lines 184-198.
- `POST /api/analysis/projects/{project_id}/run` calls `flow.start_analysis()` at lines 201-210.

Impact:

- Frontend cannot get the expected behavior by only switching labels or routes.
- Either the project endpoints must be migrated to Data Processing, or the frontend must call job endpoints while creating/updating a project wrapper.

### B4. Data Processing has correct stop-on-review semantics, but the project flow does not use it

Data Processing regularization sets status to `needs_review` when regularization cannot safely proceed, otherwise it marks regularization complete and allows analysis.

Evidence:

- `regularize()` sets `dataset_regularization` to `needs_review` and job status `needs_review` at `data_processing_analysis_flow.py` lines 131-134.
- Otherwise it sets the regularization stage to `completed` and status to `queued` at lines 135-136.
- `run_analysis()` checks readiness through `_assert_ready_for_analysis()` before starting at lines 141-153.

Impact:

- The desired error/exit behavior exists for jobs.
- The main project-creation path never reaches this state machine.

## Root Cause

The issue is an integration mismatch:

1. The backend Data Processing chain was implemented as a new "job" resource.
2. The frontend wired that chain to a new standalone "数据处理" page.
3. The existing "我的项目 / 新建项目 / 项目详情" flow still uses Retail V2 project APIs.
4. There is no project-level bridge that maps Data Processing job status and outputs into the project list/detail contract.

So the current E2E fails because the product flow and the implemented API surface do not share the same resource model.

## Recommended Direction

Make Data Processing the default lifecycle behind project creation while preserving the existing project-card mental model.

Recommended resource model:

- Project remains the user-facing object.
- Data Processing Job becomes the internal execution object for a project.
- A project may store `analysis_kind: "data_processing"` and `job_id`.
- Project list/detail endpoints expose enough fields for the frontend to render the card, status, stages, quality, outputs, and detail tabs.

Recommended UX:

- Keep "我的项目" as the primary entry.
- Keep "新建项目" at `/projects/new`.
- Move the Data Processing create/upload/regularize/run orchestration into `ProjectCreate.vue`.
- Remove or demote `/data-processing` to an internal/debug route after project integration is complete.
- Clicking a project card should open `/projects/{project_id}` and show Data Processing status/results when the project is Data Processing-backed.

## Open Decisions Before Implementation

1. Should `/api/analysis/projects...` be replaced by Data Processing semantics immediately, or should it support both Retail V2 and Data Processing during a transition?
2. Should `/data-processing` remain as a debug/admin page, or be removed from top-level navigation?
3. Should project creation be a single backend endpoint that does create/upload/regularize/run, or should frontend orchestrate several backend calls after creating a project?

Recommended decision:

- Use project endpoints as the public product contract.
- Let frontend orchestrate a small number of typed API calls only if needed in the first slice.
- Add backend project-job mapping so project list/detail are truthful and stable.
