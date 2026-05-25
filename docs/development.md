# Development

## Workflow

1. Create or update code in the relevant module.
2. Update docs when behavior or commands change.
3. Run `make lint`.
4. Fix lint issues with minimal changes.
5. Run `make lint` again.
6. Run `make format`.
7. Run `make lint` again after formatting.
8. Run `make check` or `make verify` when commands are configured.

Do not treat placeholder targets as successful verification.

## Quality Gate

Quality gate level: full

Setup scripts generate command entry points and hook configuration only. They do not run lint, format, test, build, pre-commit, or CI, and they cannot prove those commands pass.

Current configured checks:

- Backend lint: `uv run ruff check .`
- Backend format check: `uv run ruff format --check .`
- Backend tests: `uv run pytest`
- Frontend build/type validation: `cd frontend && npm run build`

The project currently has no test files, so `make test` / `make check` may fail until behavior-protection tests are added.

## Commit Convention

feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert, arch, prompt, agent

## Hooks

Hook level: full

Install hooks only after reviewing `.pre-commit-config.yaml`. Before commit, run `make hooks` when hooks are enabled. If hooks modify files, inspect the diff and rerun lint and hooks.
