# User System And Owner Isolation Integrated Design

Status: active design, 2026-05-29.

## Scope And Completion Goal

Complete MarketMind's user system across the FastAPI backend and Vue 3
frontend. The remaining implementation must deliver:

- Login and registration pages.
- A Pinia auth store.
- Authorization and 401 handling in the shared axios client.
- Router guards for protected business pages.
- Alembic migration for `users`, `projects.owner_user_id`, and `sse_tickets`.
- Data Processing owner scope.
- SSE endpoint ticket verification.
- API-level cross-user isolation tests.
- Architecture lint rules for auth, SSE, and owner-scope regressions.

Backend work must follow the existing architecture contract:

```text
API Controller -> Business Flow / Pipeline -> Ability Atom -> Provider Interface -> External Adapter
```

Frontend work must keep `frontend/src/api/` as the only business API boundary.
Pages and stores call typed wrappers; they do not create page-local axios access
to backend business endpoints.

## Non-Goals

- Do not restore `/api/projects`, `/api/recommend`, or `/api/association`.
- Do not introduce RBAC, organizations, multi-user project sharing, OAuth,
  email verification, or password reset in this phase.
- Do not treat frontend guards or UI filtering as a security boundary.
- Do not put password hashing, token signing, session persistence, DB access,
  storage access, queue access, or env reads in API controllers, Business
  Flow/Pipeline, Ability Atom, or Provider Interface modules.
- Do not pass trusted `owner_user_id` from browser payloads. Owner identity is
  derived from backend authentication context only.

## Current Partial Implementation

The project has a partial backend auth skeleton and no connected frontend auth
experience.

### Frontend

| Area | Current state | Remaining gap |
| --- | --- | --- |
| Pinia | `pinia` is installed in `frontend/package.json` and bootstrapped in `frontend/src/main.ts`. | No `frontend/src/stores/auth.ts`, no auth store, no login-state consumers. |
| Shared API client | `frontend/src/api/client.ts` owns `apiClient`, envelope unwrap, direct request helper, and `createApiEventSource()`. | No Authorization request interceptor, centralized 401 handling, or token injection. |
| EventSource | `createApiEventSource()` opens native `EventSource` synchronously. Retail and Data Processing wrappers call it directly. | Native EventSource cannot carry Authorization headers; wrappers must request short-lived SSE tickets first. |
| Router | `frontend/src/router/index.ts` has public static routes only. | No `/login`, `/register`, `meta.requiresAuth`, `meta.guestOnly`, or `beforeEach` guard. |
| Views | Business pages call typed API wrappers. | Login/Register pages and auth-aware navigation/logout states are missing. |
| Legacy client | `frontend/src/utils/http.ts` exists but is not the active typed API boundary. | Do not add new auth behavior there unless all usages are intentionally consolidated. |

Protected frontend pages should include `/projects`, `/projects/new`,
`/projects/:id`, `/me/projects`, `/data-processing`,
`/data-processing/jobs/:jobId`, `/projects/:id/recommend`,
`/projects/:id/customer/:customerId`, and `/settings`. `/project-intro` may
remain public.

### Backend

| Area | Current state | Remaining gap |
| --- | --- | --- |
| Auth API | `backend/api/auth.py` has register, login, me, logout, and `/auth/sse-ticket` endpoints. | Route surface exists, but downstream provider factory and DB migration are incomplete. |
| Auth dependency | `backend/api/auth_dependencies.py` has bearer-token current-user helpers and staged `AUTH_ENFORCE_ANALYSIS_AUTH` support. | Analysis endpoints are only partially wired; strict enforcement still needs route coverage and tests. |
| Auth pipelines/abilities | Registration, login, current-user resolution, issue SSE ticket, and verify SSE ticket building blocks exist. | Verify-ticket path is not connected to analysis SSE endpoints. |
| Provider boundary | Auth provider protocols and optional `ProvidersContainer` fields exist. | Real user directory and SSE ticket providers are `None` in default factory assembly. |
| ORM models | `UserRecord` and `SseTicketRecord` exist. | They are not imported by `backend/infrastructure/db/models/__init__.py`, and Alembic does not create the tables. |
| Project ownership | Some provider protocols and Retail flow code are already owner-aware. | `ProjectRecord` lacks `owner_user_id`; Postgres and JSON adapters still do not fully match owner-scoped protocols. |
| Data Processing | Flow methods validate `project_id` and `job_id` relationship. | They do not receive `AuthenticatedUserContext` and do not enforce owner scope. |
| SSE | Analysis SSE endpoints stream directly from the event stream provider. | They do not require or verify short-lived tickets before subscription. |
| Tests | `tests/api/test_auth_contracts.py` and ability-level access tests exist. | API-level cross-user isolation tests and strict SSE ticket tests are missing. |
| Architecture lint | `tests/test_architecture_imports.py` guards core layering. | It does not yet cover auth crypto imports, API `flow.providers.*` access, public SSE streams, or owner-scope signatures. |

## Target Runtime Flow

### Authenticated Analysis Request

```text
Browser page / Pinia auth store
  -> frontend/src/api typed wrapper
  -> apiClient adds Authorization: Bearer <access token>
  -> FastAPI API Controller gets AuthenticatedUserContext
  -> Retail/Data Processing Flow receives user context
  -> Flow/Pipeline calls owner-scoped Provider Interface
  -> Postgres/Storage Adapter enforces owner scope in query or project join
```

### SSE Stream

```text
Browser page
  -> frontend typed API requests /api/auth/sse-ticket with Authorization header
  -> IssueSseTicketPipeline verifies owner access and mints short-lived ticket
  -> native EventSource opens analysis events URL with event_token only
  -> API Controller passes event_token to VerifySseTicketPipeline
  -> ticket provider verifies user/resource/project/job/stream/expiry/consume rule
  -> API Controller subscribes to AnalysisEventStreamProvider only after success
```

Long-lived access tokens must not be placed in EventSource query strings.

## Backend Architecture

### API Controller Layer

Target files:

- `backend/api/auth.py`
- `backend/api/auth_dependencies.py`
- `backend/api/analysis.py`
- `backend/api/error_mapping.py`
- `backend/main.py`

Responsibilities:

- validate HTTP request schemas;
- bind current-user dependencies for protected endpoints;
- accept `event_token` query parameters for SSE endpoints;
- call exactly one Business Pipeline or Flow operation;
- map internal auth, owner, validation, and provider errors to HTTP responses;
- avoid direct DB/session/token/hash/adapter imports;
- avoid controller access to `flow.providers.*`.

Status-code policy:

- `401` for missing, malformed, expired, or invalid credentials.
- `404` for cross-user project/job/artifact/dataset/sidecar/model access where
  existence must not be disclosed.
- `403` for authenticated users known to be forbidden from non-enumerable
  actions.
- `409` for duplicate registration email.
- `422` for request schema errors.

### Business Orchestration Layer

Target files:

- `backend/business/pipelines/register_user_pipeline.py`
- `backend/business/pipelines/login_user_pipeline.py`
- `backend/business/pipelines/resolve_current_user_pipeline.py`
- `backend/business/pipelines/issue_sse_ticket_pipeline.py`
- `backend/business/pipelines/verify_sse_ticket_pipeline.py` or an equivalent
  flow method wrapping the existing verify ability
- `backend/business/flows/retail_analysis_flow.py`
- `backend/business/flows/data_processing_analysis_flow.py`

Business pipelines orchestrate auth ability atoms and providers. Data Processing
and Retail flows accept `AuthenticatedUserContext | None` only during staged
rollout; after `AUTH_ENFORCE_ANALYSIS_AUTH=true`, owned-resource operations
should require a non-null context.

Data Processing owner scope must be applied to:

- `create_job`
- `upload_raw_dataset`
- `regularize`
- `run_analysis`
- `get_dataset_ref`
- `get_sidecar_ref`
- `load_sidecar`
- `get_job`
- `list_outputs`
- project-backed dataset upload, regularize, run, status, outputs, and SSE

Worker payloads may include owner metadata for trace/log correlation, but
workers must not treat a user-supplied owner id as authority. The authoritative
check remains provider/adapters resolving the owned project or job.

### Ability Layer

Existing auth ability atoms should remain small and provider-driven:

- normalize email;
- register user;
- authenticate user;
- resolve current user;
- issue auth tokens;
- issue SSE ticket;
- verify SSE ticket;
- assert or resolve project access.

Ability atoms must not import FastAPI, SQLAlchemy sessions, auth DB models,
JWT/hash libraries, provider factory, settings readers, env, or infrastructure
adapters.

### Provider Boundary

Provider contracts should define narrow operations for:

- user directory;
- password hash/verify;
- token sign/verify;
- SSE ticket mint/verify/consume;
- owner-scoped project repository operations;
- owner-scoped Retail state operations;
- owner-scoped Data Processing job/output/dataset/sidecar resolution.

`ProvidersContainer` must not leave `user_directory` or `sse_ticket` as `None`
in any profile where auth routes, auth dependencies, or SSE ticket endpoints are
enabled. Test profiles may use fakes, but real dev/runtime profiles should wire
Postgres-backed providers.

Provider Interface modules must not depend on infrastructure adapters, concrete
DB models, token/hash libraries, FastAPI objects, queue clients, storage clients,
or settings readers.

### Infrastructure Layer

Target files:

- `alembic/versions/`
- `backend/infrastructure/db/models/__init__.py`
- `backend/infrastructure/db/models/project.py`
- `backend/infrastructure/db/models/user.py`
- `backend/infrastructure/db/models/sse_ticket.py`
- `backend/infrastructure/adapters/postgres_user_directory_adapter.py`
- `backend/infrastructure/adapters/postgres_sse_ticket_adapter.py`
- `backend/infrastructure/adapters/postgres_project_repository_adapter.py`
- `backend/infrastructure/adapters/json_project_repository_adapter.py`
- `backend/infrastructure/adapters/postgres_retail_analysis_state_adapter.py`
- `backend/infrastructure/factories/provider_factory.py`

Infrastructure adapters own SQLAlchemy queries, DB constraints, token/hash
runtime calls, and external error conversion. Owned-resource reads must include
`owner_user_id` directly or join through `projects.owner_user_id` before any
blob, artifact, sidecar, model, or event stream reference is returned.

## Database And Migration

Add a new Alembic migration after `0001_initial_schema.py`.

### New Tables

`users`:

- `id` string/UUID primary key.
- `email` normalized, unique, non-null, indexed.
- `password_hash` non-null.
- `display_name` nullable.
- `status` non-null, indexed.
- `created_at`, `updated_at` non-null.
- `last_login_at`, `email_verified_at` nullable.

`sse_tickets`:

- `id` primary key.
- `ticket_hash` non-null, indexed.
- `user_id` non-null, indexed, FK to `users.id` when feasible.
- `resource_type`, `resource_id`, `project_id`, `job_id`, `stream_type`.
- `expires_at` non-null.
- `consumed_at` nullable.
- `created_at` non-null.

### Project Owner Column

Add to `projects`:

- `owner_user_id` FK to `users.id`, non-null after backfill.

Indexes:

- `(owner_user_id, id)`.
- `(owner_user_id, updated_at)`.

Migration order:

1. Create `users` and `sse_tickets`.
2. Import `UserRecord` and `SseTicketRecord` in the SQLAlchemy model registry.
3. Add nullable `projects.owner_user_id`.
4. Create a deterministic legacy/system owner user for existing projects.
5. Backfill existing project rows to that owner.
6. Add FK and owner indexes.
7. Enforce non-null `projects.owner_user_id`.
8. Update schema compatibility and Alembic roundtrip tests.

Child tables such as `datasets`, `uploaded_files`, `artifacts`,
`processing_runs`, and `analysis_results` should not duplicate owner in the
first phase. They inherit ownership through `project_id -> projects.owner_user_id`.
Every child read still needs an owner-scoped project resolution or join.

## Frontend Architecture

### Typed API

Add `frontend/src/api/auth.ts` for:

- register;
- login;
- me;
- logout if backend endpoint stays active;
- issue SSE ticket.

Add or extend auth DTOs in `frontend/src/api/types.ts`. Keep Retail,
Data Processing, and Suggestions wrappers on existing `/api/analysis*` routes.

### Pinia Auth Store

Add `frontend/src/stores/auth.ts`.

State:

- `user`;
- `accessToken`;
- `status` such as `idle`, `loading`, `authenticated`, `anonymous`;
- `authError`;
- `returnTo` or equivalent redirect target.

Actions:

- `register`;
- `login`;
- `loadMe`;
- `logout`;
- `clearAuth`;
- `setReturnTo`.

First phase token persistence may use a single localStorage key because no
refresh-cookie flow exists yet. This is a known XSS tradeoff and must not be
used for EventSource URLs. A later hardening phase can move refresh state to
httpOnly SameSite cookies.

### Axios Interceptors

Extend `frontend/src/api/client.ts`:

- request interceptor reads the auth store or a small token accessor and sets
  `Authorization: Bearer <token>`;
- response interceptor normalizes `401`, clears auth state, and redirects to
  `/login?redirect=<current route>` outside infinite loops;
- API error normalization remains centralized through `normalizeApiError`.

Avoid importing the router/store in a way that creates circular module loading.
If needed, use a small auth-token accessor module or install interceptors from
`main.ts` after Pinia/router creation.

### Router Guards

Add routes:

- `/login` with `meta.guestOnly`.
- `/register` with `meta.guestOnly`.

Add `meta.requiresAuth` to business pages. The guard should:

- allow public routes;
- redirect anonymous users from protected routes to login with a return target;
- redirect authenticated users away from login/register to the return target or
  `/projects`;
- avoid redirect loops when `loadMe` fails.

### SSE Ticket Flow

`createApiEventSource()` currently returns `EventSource` synchronously. The
target API should become either:

- an async helper that requests a ticket and then opens EventSource; or
- a lower-level URL builder plus typed wrappers that perform ticket requests.

Retail and Data Processing wrappers must pass resource metadata:

- Retail project events: `resource_type=project`, `resource_id=project_id`,
  `project_id=project_id`, `stream_type=retail-analysis`.
- Data Processing job events: `resource_type=job`, `resource_id=job_id`,
  `project_id=project_id`, `job_id=job_id`, `stream_type=data-processing`.

Pages that currently call SSE wrappers synchronously must `await` the new
wrapper and handle ticket failures as auth/session errors.

## API And Owner Isolation Rules

### Analysis API

All owned analysis endpoints must derive owner from current user or validated
SSE ticket. Request bodies and query strings must never provide trusted owner
identity.

Routes that need explicit audit during implementation:

- project create/list/detail/delete;
- Retail dataset upload/run/artifact/dataset/model/read-model endpoints;
- project-backed Data Processing upload/regularize/run/status/events;
- direct Data Processing job create/upload/regularize/run/status/events;
- outputs, datasets, sidecars;
- customer suggestions.

`customer-suggestions` has no project dimension, but still requires login for
user-level audit and future rate limiting.

### Cross-User Contract

For users A and B:

- B cannot see A's projects in list responses.
- B cannot read A's project or job by id.
- B cannot delete A's project.
- B cannot upload, regularize, or run analysis against A's project/job.
- B cannot read A's artifacts, models, datasets, sidecars, or outputs.
- B cannot mint a valid SSE ticket for A's project/job.
- B cannot reuse or tamper with A's SSE ticket.

Prefer `404` for cross-user owned-resource access to avoid existence leaks.

## Architecture Lint And Runtime Checks

Extend `tests/test_architecture_imports.py` with rules for:

- auth crypto/JWT/password libraries only in infrastructure adapters;
- API controllers must not call `flow.providers.*`;
- analysis SSE routes must pass through a verify-ticket dependency or pipeline;
- business/abilities/providers must not import FastAPI request/response,
  infrastructure adapters, SQLAlchemy sessions, DB auth models, settings
  readers, or env APIs;
- provider protocols and concrete adapters must keep owner-scoped signatures for
  owned resource access;
- retired routes remain absent.

Extend `backend/core/runtime_checks.py` with:

- auth config validation;
- provider factory completeness for user directory, password hasher, auth token,
  and SSE ticket providers;
- token sign/verify roundtrip check;
- SSE ticket mint/verify/consume sandbox check;
- optional owner-scoped project lookup probe against a fixture profile.

## Verification Strategy

Use behavior-protecting tests first, then implementation.

Backend anchors:

- `tests/api/test_auth_contracts.py` for auth API behavior.
- New `tests/api/test_analysis_owner_isolation_contracts.py` for cross-user
  Retail and Data Processing API isolation.
- Existing Retail and Data Processing contract tests updated for auth and SSE
  ticket expectations.
- Provider and adapter tests for owner-scoped protocols and Postgres queries.
- Alembic/schema tests updated for `users`, `sse_tickets`, and
  `projects.owner_user_id`.
- Architecture lint tests for auth/SSE/owner boundaries.

Frontend verification:

- `npm --prefix frontend run build`.
- Route guard and auth store tests if a frontend test harness is added.
- Manual smoke path: register -> login -> project list -> create/upload/run ->
  SSE status updates -> logout -> protected route redirects.

Project quality loop remains:

```bash
make lint
make format
make lint
make check
```

`make typecheck` is currently a placeholder in this repo baseline, so frontend
type verification should use the real frontend build path or `make check`.

## Rollback Strategy

- Keep owner data once written; do not drop `owner_user_id` during code rollback.
- Use staged `AUTH_ENFORCE_ANALYSIS_AUTH` only as a temporary rollout gate.
- If strict auth breaks analysis routes, disable enforcement while preserving
  owner writes for new resources.
- If migration fails, use Alembic downgrade for the new migration only; do not
  edit the initial schema in place.
- If frontend guards block valid users, temporarily disable route meta guards
  while backend owner isolation remains active.
- If SSE ticket rollout fails, close streams and fall back to REST polling rather
  than exposing long-lived access tokens in EventSource URLs.
