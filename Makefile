.PHONY: setup lint format fix test typecheck build check verify hooks clean backend-lint backend-format backend-format-check backend-fix backend-test frontend-setup frontend-build

setup:
	uv sync
	cd frontend && npm ci

backend-lint:
	uv run ruff check .

backend-format:
	uv run ruff format .

backend-format-check:
	uv run ruff format --check .

backend-fix:
	uv run ruff check . --fix
	uv run ruff format .

backend-test:
	uv run pytest

frontend-setup:
	cd frontend && npm ci

frontend-build:
	cd frontend && npm run build

lint: backend-lint

format: backend-format

fix: backend-fix

test: backend-test

typecheck:
	@echo "No confirmed typecheck command; configure this target before claiming type checks passed."

build: frontend-build

check:
	$(MAKE) backend-lint
	$(MAKE) backend-format-check
	$(MAKE) backend-test
	$(MAKE) frontend-build

verify:
	$(MAKE) check
	$(MAKE) hooks

hooks:
	pre-commit run --all-files

clean:
	@echo "No confirmed clean command; customize this target if generated files need cleanup."
