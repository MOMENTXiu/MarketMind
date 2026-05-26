.PHONY: setup lint format fix test typecheck build check verify hooks clean backend-lint backend-format backend-format-check backend-fix backend-test frontend-setup frontend-build infra-up infra-down infra-reset infra-logs db-migrate db-downgrade db-revision

DB_REVISION_MESSAGE ?= migration

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
	uv run python -m pytest

infra-up:
	docker compose -f docker-compose.dev.yml up -d

infra-down:
	docker compose -f docker-compose.dev.yml down

infra-reset:
	docker compose -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.dev.yml up -d

infra-logs:
	docker compose -f docker-compose.dev.yml logs -f postgres redis

db-migrate:
	uv run alembic upgrade head

db-downgrade:
	uv run alembic downgrade base

db-revision:
	uv run alembic revision --autogenerate -m "$(DB_REVISION_MESSAGE)"

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
	uv run pre-commit run --all-files

clean:
	@echo "No confirmed clean command; customize this target if generated files need cleanup."
