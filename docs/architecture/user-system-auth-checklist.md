# User System And Owner Isolation Integrated Checklist

Status: active checklist, 2026-05-29.

Execution rule: complete one phase at a time and record verification
immediately. Do not weaken architecture lint, runtime checks, or owner-scope
tests to make a phase pass. Do not implement a later phase before the current
phase has a clear result and rollback state.

## 1. Test Anchors

- WHERE: `tests/api/test_auth_contracts.py`, new
  `tests/api/test_analysis_owner_isolation_contracts.py`,
  `tests/api/test_retail_analysis_contracts.py`,
  `tests/api/test_data_processing_analysis_contracts.py`,
  `tests/api/test_project_data_processing_entry_contracts.py`,
  `tests/abilities/auth/`, `tests/providers/`, `tests/infrastructure/`,
  `tests/test_architecture_imports.py`.
- WHY: Auth and owner isolation change public access semantics. Tests must pin
  behavior before controller, flow, provider, and frontend wiring move.
- HOW:
  - keep existing register/login/me/SSE-ticket tests and extend missing bad-token
    and expired-token cases
  - add cross-user API tests for user A and user B across project list/detail,
    delete, upload, regularize, run, artifacts, datasets, sidecars, outputs, and
    SSE ticket minting
  - update public SSE stream tests so missing ticket, invalid ticket, wrong user,
    wrong resource, expired ticket, and reused ticket fail
  - add provider contract tests for owner-scoped get/list/delete/resolve methods
  - add Alembic/schema tests for `users`, `sse_tickets`, and
    `projects.owner_user_id`
  - add lint tests for auth import, API provider leak, public SSE stream, and
    owner-scope signature regressions
- EXPECTED_RESULT: Tests describe the target behavior and identify current gaps
  without requiring frontend guards as a security boundary.
- VERIFY:
  `uv run pytest tests/api/test_auth_contracts.py tests/api/test_analysis_owner_isolation_contracts.py tests/api/test_retail_analysis_contracts.py tests/api/test_data_processing_analysis_contracts.py tests/api/test_project_data_processing_entry_contracts.py tests/abilities/auth tests/providers tests/infrastructure tests/test_architecture_imports.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Broad cross-user tests can become hard to diagnose if they combine too
  many behaviors in one assertion. Keep cases small and fixture-driven.
- ROLLBACK: Remove only the newly added failing target tests if scope is
  cancelled before implementation starts; keep existing auth contract tests.

## 2. Provider Interface

- WHERE: `backend/providers/`, especially `container.py`,
  `user_directory_provider.py`, `password_hasher_provider.py`,
  `auth_token_provider.py`, `sse_ticket_provider.py`,
  `project_repository_provider.py`, `retail_analysis_state_provider.py`,
  `regularized_dataset_provider.py`, `analysis_artifact_provider.py`,
  auth DTO modules, and `tests/fakes/providers.py`.
- WHY: Business layers must depend on narrow provider contracts. Owner scope must
  be a required part of owned-resource access, not an optional controller filter.
- HOW:
  - ensure `ProvidersContainer` has non-optional auth provider fields for enabled
    auth profiles or has explicit profile-level guards that fail fast
  - make fake providers match real provider signatures
  - align project repository and Retail state provider protocols with concrete
    adapters using `owner_user_id` or `AuthenticatedUserContext`
  - define a narrow SSE ticket provider contract for mint, verify, consume, and
    expiry checks
  - keep Data Processing resource access owner-aware through project/job provider
    boundaries rather than client-supplied owner values
- EXPECTED_RESULT: Business code can only reach users, tickets, projects, jobs,
  artifacts, datasets, sidecars, and outputs through provider contracts that
  include server-derived owner context.
- VERIFY:
  `uv run pytest tests/providers tests/abilities/auth/test_assert_project_access.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Leaving `user_directory=None` or `sse_ticket=None` in active profiles
  causes runtime auth endpoints to fail after route wiring.
- ROLLBACK: Revert provider signature changes and fake-provider updates together;
  do not keep mismatched protocols and adapters.

## 3. External Adapter And Alembic

- WHERE: `alembic/versions/`, `backend/infrastructure/db/models/__init__.py`,
  `backend/infrastructure/db/models/project.py`,
  `backend/infrastructure/db/models/user.py`,
  `backend/infrastructure/db/models/sse_ticket.py`,
  `backend/infrastructure/adapters/postgres_user_directory_adapter.py`,
  `backend/infrastructure/adapters/postgres_sse_ticket_adapter.py`,
  `backend/infrastructure/adapters/postgres_project_repository_adapter.py`,
  `backend/infrastructure/adapters/json_project_repository_adapter.py`,
  `backend/infrastructure/adapters/postgres_retail_analysis_state_adapter.py`,
  `backend/infrastructure/factories/provider_factory.py`,
  `tests/infrastructure/db/`.
- WHY: Schema, ORM registry, adapter queries, and provider factory wiring must be
  consistent before owner isolation can be trusted.
- HOW:
  - add an Alembic migration for `users`, `sse_tickets`, nullable then non-null
    `projects.owner_user_id`, FK, unique constraints, and owner indexes
  - create or document a deterministic legacy/system owner user for existing
    project backfill
  - import `UserRecord` and `SseTicketRecord` in the SQLAlchemy model registry
  - add `owner_user_id` to `ProjectRecord` and DTO conversions
  - update Postgres project and Retail state adapters so get/list/delete/save
    paths include owner scope
  - update JSON/local adapters or retire them from auth-enabled profiles if they
    cannot satisfy owner-scoped contracts
  - wire Postgres user directory and SSE ticket providers in Provider Factory for
    auth-enabled dev/runtime profiles
  - convert DB/token/hash exceptions to internal errors at adapter boundaries
- EXPECTED_RESULT: Alembic, ORM metadata, provider factory, and concrete adapters
  agree on users, SSE tickets, and project ownership. Cross-user project reads
  cannot succeed by project id alone.
- VERIFY:
  `uv run pytest tests/infrastructure/db tests/infrastructure tests/providers`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Editing the initial migration instead of adding a new migration can break
  existing deployments and migration roundtrip tests.
- ROLLBACK: Downgrade only the new Alembic revision and switch Provider Factory
  back to fake/local auth providers while preserving source changes for review.

## 4. Ability Atom

- WHERE: `backend/abilities/auth/`, related auth ability tests.
- WHY: User registration, credential verification, current-user resolution,
  ticket issue/verify, and owner assertions should stay small and unit-testable.
- HOW:
  - keep or complete ability atoms for email normalization, register user,
    authenticate user, resolve current user, issue token, issue SSE ticket,
    verify/consume SSE ticket, and resolve owned project
  - make abilities accept explicit DTOs and provider interfaces only
  - ensure ticket verification checks resource type, resource id, project id,
    job id, stream type, user binding, expiry, and reuse/consume semantics
  - return internal errors for duplicate email, invalid credentials, disabled
    user, invalid token, expired token, invalid ticket, and owner mismatch
- EXPECTED_RESULT: Auth abilities have no HTTP, SQLAlchemy, adapter, settings,
  env, JWT-library, or password-library imports and all edge cases are covered
  by unit tests.
- VERIFY:
  `uv run pytest tests/abilities/auth`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Putting flow orchestration or DB lookups directly in abilities would
  collapse the architecture boundary.
- ROLLBACK: Revert ability changes without touching provider contracts or tests.

## 5. Business Pipeline

- WHERE: `backend/business/pipelines/register_user_pipeline.py`,
  `backend/business/pipelines/login_user_pipeline.py`,
  `backend/business/pipelines/resolve_current_user_pipeline.py`,
  `backend/business/pipelines/issue_sse_ticket_pipeline.py`, new or updated
  `backend/business/pipelines/verify_sse_ticket_pipeline.py`, related business
  tests.
- WHY: Auth workflows and SSE ticket verification require orchestration across
  ability atoms and providers while staying outside API controllers.
- HOW:
  - ensure register/login/current-user pipelines return public-safe DTOs and do
    not expose password hashes or raw token claims
  - add or connect a verify-SSE-ticket pipeline for analysis stream endpoints
  - make issue-ticket pipeline verify owner access before minting tickets
  - keep staged auth enforcement explicit through settings/dependency behavior,
    not hidden in individual endpoints
- EXPECTED_RESULT: API controllers can call one pipeline per auth concern, and
  SSE endpoints can verify tickets without direct provider or adapter access.
- VERIFY:
  `uv run pytest tests/business tests/api/test_auth_contracts.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Implementing ticket verification directly in controllers will make
  architecture lint harder and duplicate owner checks.
- ROLLBACK: Remove the verify pipeline wiring and keep SSE endpoints closed or
  REST-polling only until a correct pipeline exists.

## 6. Business Flow

- WHERE: `backend/business/flows/retail_analysis_flow.py`,
  `backend/business/flows/retail_analysis_state.py`,
  `backend/business/flows/data_processing_analysis_flow.py`,
  `backend/business/flows/data_processing_analysis_state.py`, worker enqueue and
  event/status call sites.
- WHY: Retail and Data Processing are long-lived owned resource lifecycles.
  Owner context must be enforced consistently across project, job, status,
  output, deletion, and async paths.
- HOW:
  - complete Retail flow owner-scoped adapter compatibility
  - update Data Processing flow public methods to accept
    `AuthenticatedUserContext` for create/upload/regularize/run/status/output
    operations
  - persist owner context in internal job state or trace metadata where useful,
    without exposing it in public views unless required
  - resolve owned project/job before reading raw datasets, normalized datasets,
    sidecars, outputs, or stream metadata
  - move any API-level direct provider cleanup into flow methods
  - return not-found semantics for cross-user project/job/resource access
- EXPECTED_RESULT: Data Processing and Retail flows cannot operate on another
  user's resources, including project-backed DP entry points and direct DP job
  routes.
- VERIFY:
  `uv run pytest tests/business/test_retail_analysis_flow.py tests/business/test_data_processing_analysis_flow.py tests/api/test_analysis_owner_isolation_contracts.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Updating API endpoints without updating all flow signatures can leave
  project-backed and direct DP routes with different security semantics.
- ROLLBACK: Revert flow signature changes and route wiring together; do not
  leave partially owner-aware flows active.

## 7. API Controller

- WHERE: `backend/api/auth.py`, `backend/api/auth_dependencies.py`,
  `backend/api/analysis.py`, `backend/api/error_mapping.py`, `backend/main.py`,
  `tests/api/`.
- WHY: The public protocol layer must bind authentication, call business
  orchestration, and expose consistent HTTP errors without doing provider work.
- HOW:
  - ensure auth router is registered under `/api`
  - require current user on all owned analysis endpoints once tests and staged
    rollout are ready
  - keep `AUTH_ENFORCE_ANALYSIS_AUTH` as a temporary rollout gate only
  - pass `AuthenticatedUserContext` into Retail and Data Processing flows
  - add `event_token` parsing to SSE endpoints and delegate verification to a
    business pipeline/flow before event subscription
  - remove API-layer `flow.providers.*` access
  - map unauthenticated to 401 and cross-user owned resources to 404
- EXPECTED_RESULT: Analysis API endpoints are authenticated, owner-scoped, and
  SSE streams are inaccessible without valid short-lived tickets.
- VERIFY:
  `uv run pytest tests/api/test_auth_contracts.py tests/api/test_analysis_owner_isolation_contracts.py tests/api/test_retail_analysis_contracts.py tests/api/test_data_processing_analysis_contracts.py tests/api/test_project_data_processing_entry_contracts.py`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Public SSE stream tests may still encode old behavior. Update tests to
  reflect ticket-gated streams before changing implementation.
- ROLLBACK: Temporarily disable strict auth enforcement while keeping auth routes
  and owner writes; do not expose SSE without either ticket verification or REST
  polling fallback.

## 8. Frontend

- WHERE: `frontend/src/api/auth.ts`, `frontend/src/api/client.ts`,
  `frontend/src/api/types.ts`, `frontend/src/router/index.ts`,
  `frontend/src/stores/auth.ts`, `frontend/src/views/Login.vue`,
  `frontend/src/views/Register.vue`, `frontend/src/api/retail.ts`,
  `frontend/src/api/data-processing.ts`, `frontend/src/views/ProjectDetail.vue`,
  `frontend/src/views/DataProcessing.vue`, navigation components if present.
- WHY: Users need a complete session experience, and browser SSE limitations
  require a ticket flow coordinated through typed API wrappers.
- HOW:
  - add typed auth wrappers for register, login, me, logout, and issue SSE ticket
  - add Pinia auth store with user, access token, auth status, error, login,
    register, loadMe, logout, clearAuth, and redirect target behavior
  - install axios request/response interceptors without introducing router/store
    circular imports
  - add `/login` and `/register` views and routes
  - add route meta and guards for protected business pages and guest-only auth
    pages
  - change Retail and Data Processing SSE wrappers to request short-lived tickets
    before opening native EventSource
  - update pages that open SSE streams to await the new async wrapper and handle
    auth/ticket failures
  - keep business calls inside `frontend/src/api/` and avoid page-local axios
- EXPECTED_RESULT: Anonymous users are redirected from protected pages, logged-in
  users can access their resources, 401 clears auth state, and SSE streams open
  only through short-lived tickets.
- VERIFY:
  `npm --prefix frontend run build`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Token persistence in localStorage is an XSS tradeoff. Do not put the
  access token into EventSource URLs; use only short-lived SSE tickets there.
- ROLLBACK: Disable route guards and SSE auto-connect in frontend while backend
  owner isolation remains enabled.

## 9. Architecture Lint / Runtime Check / Full Verification

- WHERE: `tests/test_architecture_imports.py`, `backend/core/runtime_checks.py`,
  `backend/core/config.py`, `.env.example`, `Makefile`, project root.
- WHY: Auth, owner scope, and SSE ticketing need mechanical regression checks
  after implementation.
- HOW:
  - add lint rules for auth crypto/hash/JWT imports only in infrastructure
    adapters
  - add lint rule forbidding API controller `flow.providers.*` access
  - add lint rule or focused test ensuring analysis SSE endpoints verify tickets
    before subscribing
  - add lint or contract checks for owner-scoped provider and adapter signatures
  - add runtime checks for auth settings, auth provider non-null assembly, token
    roundtrip, and SSE ticket lifecycle
  - update `.env.example` with auth setting names and dev-only placeholder values
  - run the full project quality loop
- EXPECTED_RESULT: Cross-layer auth violations, missing provider wiring, public
  SSE regressions, and missing owner scope fail automatically.
- VERIFY:
  `make lint`
  `make format`
  `make lint`
  `make check`
  `uv run python -m backend.core.runtime_checks check-auth-config`
  `uv run python -m backend.core.runtime_checks check-providers`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Weakening lint/runtime checks to pass a phase would hide security
  regressions.
- ROLLBACK: Revert the offending implementation, not the lint rule, unless the
  rule is demonstrably wrong and replaced with an equivalent check.

## 10. Cleanup And Handoff

- WHERE: `docs/architecture/user-system-auth-design.md`,
  `docs/architecture/user-system-auth-checklist.md`, `AGENTS.md` only after a
  stable convention is confirmed, and user-facing docs only if commands or setup
  changed.
- WHY: Future agents need a clean record of what was implemented, how it was
  verified, and which rollout switches or risks remain.
- HOW:
  - record phase results, command outputs, known failures, and rollback state in
    this checklist
  - remove stale text that describes already completed work as missing
  - remove dead compatibility paths and unused auth helpers after tests prove
    they are unused
  - update `AGENTS.md` only with stable conventions confirmed by code and tests
  - keep non-goals explicit to prevent scope creep into RBAC/OAuth/org sharing
- EXPECTED_RESULT: Docs, code, tests, and runtime checks describe the same auth
  and owner-isolation system.
- VERIFY:
  `make verify`
- STATUS: pending.
- RESULT:
- VERIFY_RESULT:
- RISK: Premature docs updates can claim behavior not yet implemented.
- ROLLBACK: Revert only inaccurate documentation; keep architecture decisions
  that still match the verified code.
