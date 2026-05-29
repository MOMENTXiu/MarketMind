.PHONY: setup lint format fix test typecheck build check verify hooks clean \
	backend-lint backend-format backend-format-check backend-fix backend-test \
	frontend-setup frontend-build \
	infra-up infra-down infra-reset infra-logs infra-up-prod infra-down-prod \
	db-migrate db-downgrade db-revision db-migrate-prod \
	status-prod health deploy-readme

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

# ─── 部署模式（Production） ───

infra-up-prod:
	docker compose -f scripts/deploy/docker-compose.infra.yml --env-file .env.production up -d

infra-down-prod:
	docker compose -f scripts/deploy/docker-compose.infra.yml --env-file .env.production down

infra-logs-prod:
	docker compose -f scripts/deploy/docker-compose.infra.yml --env-file .env.production logs -f

db-migrate-prod:
	uv run alembic upgrade head

status-prod:
	@echo "=== MarketMind API ==="
	@systemctl is-active marketmind-api 2>/dev/null || echo "marketmind-api: not running"
	@echo ""
	@echo "=== MarketMind Workers ==="
	@systemctl list-units 'marketmind-worker@*' --no-pager --no-legend 2>/dev/null || echo "No workers found"
	@echo ""
	@echo "=== Docker Infra ==="
	@docker compose -f scripts/deploy/docker-compose.infra.yml ps 2>/dev/null || echo "Infra not running"

health:
	@curl -s http://localhost:8000/api/health/ 2>/dev/null | python3 -m json.tool || echo "Backend not reachable"

deploy-readme:
	@echo ""
	@echo "MarketMind 两机器部署指南（学校实训环境）"
	@echo "=========================================="
	@echo ""
	@echo "前置条件："
	@echo "  1. 两台 Linux 机器在同一内网"
	@echo "  2. 代码已通过 git clone 或 scp 放到两台机器上"
	@echo ""
	@echo "部署步骤："
	@echo ""
	@echo "  机器 02（后端+Infra）："
	@echo "    cd /opt/marketmind"
	@echo "    sudo ./scripts/deploy/install-backend.sh"
	@echo ""
	@echo "  机器 01（前端）："
	@echo "    cd /opt/marketmind"
	@echo "    sudo ./scripts/deploy/install-frontend.sh"
	@echo ""
	@echo "部署完成后："
	@echo "  前端访问: http://<01_IP>/"
	@echo "  API 访问: http://<01_IP>/api/"
	@echo "  后端直连: http://<02_IP>:8000/api/"
	@echo ""
	@echo "配置文件位置："
	@echo "  生产环境变量: /opt/marketmind/.env.production"
	@echo "  Nginx 配置:   /etc/nginx/sites-available/marketmind"
	@echo "  systemd API:  /etc/systemd/system/marketmind-api.service"
	@echo "  systemd Worker: /etc/systemd/system/marketmind-worker@.service"
	@echo ""
