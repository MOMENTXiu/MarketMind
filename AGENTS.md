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
- Current backend test baseline is 104 pytest tests across API contracts, controller thinness, business pipelines, `ProjectAnalysisFlow`, ability atoms, provider adapters, runtime checks, and architecture import rules.
- The backend architecture baseline is `API Controller -> Business Pipeline/ProjectAnalysisFlow -> Ability Atom -> Provider Interface -> Infrastructure Adapter`.
- Key architecture paths: `backend/business/pipelines/`, `backend/business/flows/`, `backend/abilities/`, `backend/providers/`, `backend/infrastructure/`, and `backend/core/runtime_checks.py`.
- `backend/api/prediction.py` and `backend/api/clustering.py` are inactive routers; do not register or expose them without a separate protected task.
- `backend/services/*` contains legacy compatibility services that are still referenced by provider factory / flow paths; do not delete or rewrite them unless reference search and tests prove the path is unreachable.
- Do not bypass `.editorconfig`, `.gitignore`, pre-commit, or CI rules.
- Expand this file only when a stable convention is confirmed by project files or user decision.
