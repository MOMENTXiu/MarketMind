#!/bin/bash

# MarketMind Project Deploy Script
# Prepares infrastructure, dependencies, runtime wiring, migrations, and seed data.
# Does NOT start long-running backend / worker / frontend servers.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                        ║${NC}"
echo -e "${CYAN}║      MarketMind Project Deploy         ║${NC}"
echo -e "${CYAN}║  Infra / Deps / Checks / Migrations    ║${NC}"
echo -e "${CYAN}║                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT_DIR"

# Check system requirements
echo -e "${YELLOW}[1/6] Checking system requirements...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo -e "${GREEN}  Python ${PYTHON_VERSION} found${NC}"

# Check uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' package manager is not installed${NC}"
    echo -e "${YELLOW}Install with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi
echo -e "${GREEN}  uv package manager found${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}  Node.js ${NODE_VERSION} found${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}  npm ${NPM_VERSION} found${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker found${NC}"

# Check curl (optional but recommended)
if ! command -v curl &> /dev/null; then
    echo -e "${YELLOW}  Warning: curl is not installed (will skip some readiness probes)${NC}"
else
    echo -e "${GREEN}  curl found${NC}"
fi
echo ""

# Export production-like local runtime defaults
echo -e "${YELLOW}[2/6] Setting local runtime defaults...${NC}"
export REDIS_ENABLED="true"
export TASK_QUEUE_BACKEND="redis"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind}"
export ANALYSIS_QUEUE_NAME="${ANALYSIS_QUEUE_NAME:-retail-analysis}"
echo -e "${GREEN}  REDIS_ENABLED=true${NC}"
echo -e "${GREEN}  TASK_QUEUE_BACKEND=redis${NC}"
echo -e "${GREEN}  REDIS_URL=${REDIS_URL}${NC}"
echo -e "${GREEN}  DATABASE_URL=${DATABASE_URL}${NC}"
echo -e "${GREEN}  ANALYSIS_QUEUE_NAME=${ANALYSIS_QUEUE_NAME}${NC}"
echo ""

# Start Docker infrastructure
echo -e "${YELLOW}[3/6] Starting Docker infrastructure...${NC}"
docker compose -f docker-compose.dev.yml up -d postgres redis minio minio-init

wait_for_service() {
    local service_name="$1"
    local max_attempts="${2:-30}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "marketmind-${service_name}-dev" 2>/dev/null || true)"
        if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
            echo -e "${GREEN}  ${service_name} is ${status}${NC}"
            return 0
        fi
        echo -e "${YELLOW}  Waiting for ${service_name} (${attempt}/${max_attempts})...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}Error: ${service_name} did not become healthy${NC}"
    docker compose -f docker-compose.dev.yml ps
    exit 1
}

wait_for_service "postgres"
wait_for_service "redis"
wait_for_service "minio"
echo ""

# Backend dependencies
echo -e "${YELLOW}[4/6] Installing backend dependencies...${NC}"
uv sync
echo -e "${GREEN}  Backend dependencies installed${NC}"
echo ""

# Frontend dependencies
echo -e "${YELLOW}[5/6] Installing frontend dependencies...${NC}"
cd frontend
npm install --registry https://registry.npmmirror.com/
cd "$ROOT_DIR"
echo -e "${GREEN}  Frontend dependencies installed${NC}"
echo ""

# Backend runtime checks
echo -e "${YELLOW}[6/6] Running runtime checks and migrations...${NC}"

echo -e "${BLUE}  Checking backend runtime wiring...${NC}"
uv run python -m backend.core.runtime_checks check-retail-runtime --dry-run
echo -e "${GREEN}  Backend runtime wiring is PostgreSQL/Redis ready${NC}"

echo -e "${BLUE}  Checking object storage readiness...${NC}"
uv run python -m backend.core.runtime_checks check-object-storage --sandbox || true
echo -e "${GREEN}  Object storage check completed${NC}"

echo -e "${BLUE}  Applying database migrations...${NC}"
uv run python -m alembic upgrade head
echo -e "${GREEN}  Database schema is ready${NC}"

echo -e "${BLUE}  Uploading sample files to MinIO...${NC}"
uv run python scripts/init-samples-to-minio.py || echo -e "${YELLOW}  Sample upload failed or skipped${NC}"
echo -e "${GREEN}  Sample files ready${NC}"

# Create required local directories
mkdir -p logs
mkdir -p outputs/charts
mkdir -p outputs/reports
mkdir -p data/projects
echo -e "${GREEN}  Local directories ready${NC}"
echo ""

# Stop Docker infrastructure — deploy is a one-time setup script
echo -e "${YELLOW}  Stopping Docker infrastructure (deploy is one-time)...${NC}"
docker compose -f docker-compose.dev.yml stop postgres redis minio minio-init >/dev/null 2>&1 || true
echo -e "${GREEN}  Docker infrastructure stopped${NC}"
echo ""

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   MarketMind deploy complete!          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Environment prepared. Infrastructure will be started by start-project.sh.${NC}"
echo ""
echo -e "${YELLOW}Setup admin user (after registration):${NC}"
echo -e "  ${CYAN}./scripts/setup-admin.sh${NC}"
echo ""
echo -e "${GREEN}Next step:${NC}"
echo -e "  ${CYAN}./scripts/start-project.sh${NC}"
echo ""
