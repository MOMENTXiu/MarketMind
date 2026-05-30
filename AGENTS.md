# Agent Guide

## Project Baseline
- Purpose: open-source
- Detected stacks: node, python, vue3-vite
- Package managers: python=uv (selected by --python-manager uv); node=npm (selected by --node-manager npm)
- Layout: split-frontend-backend
- Quality gate: full
- Hooks: full
- CI: split-frontend-backend

## Scaffold Files
- `.gitignore`: managed blocks use the `harness` marker prefix.
- `.gitattributes`: normalizes text and binary handling.
- `.editorconfig`: records editor whitespace defaults.
- `.env.example`: committed template only; do not write secrets.
- `Makefile`: stable command entry point for humans and agents.
- `.pre-commit-config.yaml`: generated as the commit-time hygiene and stack hook policy.
- CI workflow: configured to call the repository check entry point.

## Commands
- Setup: `make setup`
- Lint: `make lint`
- Format: `make format`
- Fix: `make fix`
- Test: `make test`
- Typecheck: `make typecheck`
- Build: `make build`
- Check: `make check`
- Verify: `make verify`
- Hooks: `make hooks`
- Clean: `make clean`

## Task Completion Rule
After each coding task, run the project quality loop:

1. Run `make lint`.
2. Fix lint issues with minimal changes, using `make fix` only when safe.
3. Run `make lint` again.
4. Run `make format`.
5. Run `make lint` again after formatting.
6. Run `make typecheck`, `make test`, or `make build` when the change affects those areas.
7. Run `make check` or `make verify` before handoff when commands are configured.
8. Report any placeholder target instead of claiming verification passed.

## Commit Rule
Before commit:

1. Run the quality loop above.
2. `make hooks` runs `pre-commit run --all-files`.
3. If hooks modify files, inspect the diff, rerun `make lint`, and rerun `make hooks`.
4. Do not commit while lint, format, check, or hooks are failing.
5. Use Conventional Commits; agentic scopes such as `agent`, `prompt`, or `arch` are allowed when accurate.

## Agent Notes
- Do not invent commands; use actual Makefile targets, package scripts, wrappers, or project config.
- Treat echo-only Makefile targets as placeholders, not proof that verification passed.
- Use package managers detected by repo setup unless project files change.
- Current `make check` includes backend Ruff lint, backend Ruff format check, backend pytest, and frontend `npm run build`.
- Current backend test baseline is 306 passing pytest tests plus 6 skipped optional/live-infra tests across API contracts (Retail V2 + data-processing chain-native + text-only customer suggestions), controller thinness, Retail V2 flows/pipelines, data-processing regularization/universal analysis abilities, provider adapters, DB infrastructure smoke tests, runtime checks, and architecture import rules.
- JWT auth system is active: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`, `/api/auth/sse-ticket`. Access tokens are HS256 JWTs with 60-minute expiry. `get_current_user_or_enforce` is the standard auth dependency on all `/api/analysis` endpoints.
- `AUTH_ENFORCE_ANALYSIS_AUTH=False` (in `backend/core/config.py`) allows anonymous access as a staged-rollout flag. When flipped to `True`, all analysis endpoints require a valid Bearer token.
- API-layer modules (`backend/api/*`) must not import `backend.core.config` directly. `backend/api/dependencies.py` is the single API-layer entry point for `Settings` type and `get_settings()` — other API modules import from there.
- All analysis endpoints now validate project ownership via `owner_user_id` (string UUID). Repository adapters (`JsonProjectRepositoryAdapter`, `PostgresProjectRepositoryAdapter`) and `RetailAnalysisStateProvider` implementations filter by owner. Legacy projects with `owner_user_id=None` remain accessible to any authenticated user.
- SSE event streams (`/api/analysis/projects/{id}/events`, `/api/analysis/jobs/{id}/events`) use ticket-based auth: frontend calls `createEventSourceWithTicket()` which hits `/api/auth/sse-ticket` to mint a short-lived ticket, then passes it as `event_token` query param to the `EventSource`.
- `OBJECT_STORAGE_BACKEND` default is `"minio"` (`backend/core/config.py`). Local dev uses the MinIO container from `docker-compose.dev.yml` (localhost:9000). Install `minio` package via `uv add minio` if missing.
- Infrastructure health endpoint: `GET /api/health/` returns `{ status, components: { backend, postgres, redis, minio } }` with per-component `status`, `latency_ms`, and `detail`. Probed by `CompositeInfrastructureHealthAdapter` wired into `ProvidersContainer.health`.
- Current implemented backend architecture baseline is `API Controller -> Business Pipeline/Flow -> Ability Atom -> Provider Interface -> Infrastructure Adapter`.
- Key architecture paths: `backend/business/pipelines/`, `backend/business/flows/`, `backend/abilities/`, `backend/providers/`, `backend/infrastructure/`, `backend/core/runtime_checks.py`, and MinIO adapters under `backend/infrastructure/adapters/minio_*.py`.
- Analysis V2 / Retail V2 implemented work is tracked in `docs/archive/analysis-v2-integration-design.md` and `docs/archive/analysis-v2-integration-checklist.md`; `analysis/` is an algorithm blueprint/reference directory, not a backend runtime entry.
- Data-processing pipeline (`原始数据上传 -> regularization -> analysis2 -> outputs`) is **implemented** in backend runtime. It lives alongside Retail V2; both share the provider/adapter boundary. The design and checklist remain in `docs/archive/data-processing-pipeline-integration-design.md` and `docs/archive/data-processing-pipeline-integration-checklist.md` for reference.
- `analysis/data-processing-pipeline/` is an archived source/reference snapshot from `add-analysis-2`, containing `analysis/`, `analysis2/`, and `regularization/`; backend runtime must not import from this archive directly.
- The future data-processing target is allowed to replace the current Retail V2 API/state contract; do not add compatibility wrappers unless the user explicitly asks.
- Retail V2 API contract anchor is `tests/api/test_retail_analysis_contracts.py`; it guards `/api/analysis` project schema/status/artifact/list/delete behavior plus retired old-route absence.
- Chain-native data-processing API contract anchor is `tests/api/test_data_processing_analysis_contracts.py`; it guards `/api/analysis/jobs` create/upload/regularize/run/status/outputs behavior plus dataset and sidecar read routes.
- Retail V2 state runtime is PostgreSQL-backed through `RetailAnalysisStateProvider`; Retail V2 async execution uses Redis/RQ through `AnalysisJobQueueProvider`; Retail/Data Processing status updates use SSE through `AnalysisEventStreamProvider` with REST snapshots as fallback.
- `AnalysisModelStoreProvider` is for true model artifacts only; do not reintroduce Retail project state, project index, or run state there.
- `/api/projects`, `/api/recommend`, and `/api/association` are retired; frontend project/recommendation views must use `/api/analysis` endpoints and graceful Retail V2 empty states.
- Frontend API boundary is `frontend/src/api/`; pages must call typed wrappers there instead of page-local axios calls. Data Processing frontend entry is `frontend/src/views/DataProcessing.vue` on `/data-processing` and `/data-processing/jobs/:jobId`.
- Project Intro page at `/project-intro` (`frontend/src/views/ProjectIntro.vue`) is a PPT-style full-screen scroll-snap presentation with 7 slides (Hero → What → Why → Workflow → Architecture two-col → Capability Map → Result → CTA). Uses CSS `scroll-snap-type: y mandatory`. No JS navigation — pure scroll. Architecture slide uses row-based two-column grid mapping layers to tech stacks. Workflow slide has CSV→01→...→06→Done flow with CSS border-scan and traveling-dot animations.
- Frontend business pages must route LLM text generation through `POST /api/analysis/customer-suggestions`; do not reintroduce browser direct `/chat/completions` or `/models` calls.
- `analysis/code_files` and `analysis/data-processing-pipeline` are excluded from Ruff lint/format because they are reference blueprint/archive directories, not backend runtime code.
- Legacy `backend/api/{projects,recommend,association,prediction,clustering}.py`, old project/recommend/association business flow/pipelines, and `backend/services/*` were deleted after import search; do not reintroduce compatibility wrappers.
- ECharts 5 tree-shaking requires explicit imports for every chart type AND its coordinate system. Radar charts need **both** `RadarChart` from `echarts/charts` (renders data polygons) AND `RadarComponent` from `echarts/components` (renders axes/indicators). Missing one silently produces an incomplete chart — axes show but no data polygons appear, or vice versa.
- Frontend DP diagnostic charts use a two-layer transform: `backend ability → JSON artifact → API payload → frontend chart transform → ECharts option`. When adding a new ability that outputs JSON for chart rendering, verify the output data shape matches the frontend `build*Option` function's expectations (array vs dict, field names, value types).
- Frontend report visual system uses `src/components/report/ReportSectionCard.vue` (outer shell), `ReportSectionHeader.vue` (icon+title+desc+badge slot), `ReportPanel.vue` (inner content card), and `ReportBadge.vue` (info/success/warning/danger/neutral tones). Design tokens live in `report-tokens.css` as `:root` CSS variables (`--r-section-radius`, `--r-panel-bg`, `--r-chart-height`, etc.). All 7 DP diagnostic modules must use these shells — do not introduce new `.section-block`/`.chart-card` scoped styles.
- Frontend DP diagnostic detail page uses `lucide-vue-next` icons (not `@element-plus/icons-vue`). Other pages (ProjectList, DataProcessing, CustomerAnalysis, etc.) still use Element Plus icons and are not yet migrated.
- Admin Console is implemented at `/admin/*` (frontend) and `/api/admin/*` (backend). Four modules: Status (`/admin/status`), Settings (`/admin/settings`), Logs (`/admin/logs`), Users (`/admin/users`). Only users with `role='admin'` (DB column) can access.
- Admin auth flow: JWT proves identity via `ResolveCurrentUserPipeline`, **DB `users.role` column is the authorization truth source** — never trust JWT `role` claim alone. `require_admin_user` dependency (in `backend/api/admin/dependencies.py`) enforces this.
- Admin architecture follows the same five-layer pattern (API → Pipeline → Ability → Provider → Adapter). Admin-specific paths: `backend/api/admin/`, `backend/business/pipelines/admin_*.py`, `backend/abilities/admin/`, `backend/providers/admin_*.py`, `backend/providers/settings_inspection_provider.py`, `backend/providers/alert_provider.py`, `backend/providers/log_query_provider.py`, `backend/infrastructure/adapters/env_settings_inspection_adapter.py`, `backend/infrastructure/adapters/bark_alert_adapter.py`, `backend/infrastructure/adapters/jsonl_log_query_adapter.py`, `backend/infrastructure/adapters/postgres_admin_user_adapter.py`.
- New providers in `ProvidersContainer`: `settings_inspection`, `alert`, `log_query`, `admin_users`. All can be `None` when not configured (handled as optional in `runtime_checks.py`).
- `users.role` migration is `alembic/versions/0004_add_user_role.py` (`String(32)`, `server_default="user"`, indexed). Admin bootstrap: `ADMIN_BOOTSTRAP_EMAIL=admin@example.com uv run python -m backend.scripts.bootstrap_admin`.
- Settings API redacts secrets: API keys, passwords, device keys are never returned in plaintext — only `*Configured` boolean fields. Settings are read-only from environment variables via `EnvSettingsInspectionAdapter`.
- `FileTelemetryAdapter` writes `TelemetryEnvelopeDTO` JSONL to `logs/telemetry/events.jsonl`. `JsonlLogQueryAdapter` reads and queries this file for the admin logs page.
- `AdminUserProvider` is separate from `UserDirectoryProvider` — the former handles admin list/count/role/status operations, the latter handles auth registration/login/current-user resolution.
- Admin test baseline: `tests/admin/test_admin_auth.py` (auth contracts), `tests/admin/test_admin_settings_contracts.py` (secret redaction), `tests/admin/test_admin_logs_contracts.py` (envelope/query/export), `tests/admin/test_admin_users_contracts.py` (security constraints).
- Current backend test baseline is 345 passing (up from 306) plus 6 skipped.
- Do not bypass `.editorconfig`, `.gitignore`, pre-commit, or CI rules.
- Expand this file only when a stable convention is confirmed by project files or user decision.
