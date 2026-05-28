#!/bin/bash

# MarketMind Project Startup Script
# This script starts both frontend and backend servers concurrently

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

BACKEND_PID=""
WORKER_PID=""
FRONTEND_PID=""
INFRA_STARTED=0

kill_process_tree() {
    local pid="$1"
    local name="$2"
    local child

    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
        return 0
    fi

    for child in $(pgrep -P "$pid" 2>/dev/null || true); do
        kill_process_tree "$child" "$name"
    done

    kill "$pid" >/dev/null 2>&1 || true
}

kill_process_tree_force() {
    local pid="$1"
    local child

    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
        return 0
    fi

    for child in $(pgrep -P "$pid" 2>/dev/null || true); do
        kill_process_tree_force "$child"
    done

    kill -9 "$pid" >/dev/null 2>&1 || true
}

stop_process_tree() {
    local pid="$1"
    local name="$2"

    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
        return 0
    fi

    echo -e "${YELLOW}Stopping ${name} (PID: ${pid})...${NC}"
    kill_process_tree "$pid" "$name"
    sleep 1

    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}${name} did not exit after SIGTERM; forcing shutdown...${NC}"
        kill_process_tree_force "$pid"
    fi
}

report_port_if_busy() {
    local port="$1"
    local name="$2"

    if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/tmp/marketmind-port-cleanup.log 2>/dev/null; then
        echo -e "${YELLOW}Warning: ${name} port ${port} is still in use:${NC}"
        cat /tmp/marketmind-port-cleanup.log
    fi
    rm -f /tmp/marketmind-port-cleanup.log
}

# Cleanup function to kill child processes on exit
cleanup() {
    local exit_code=$?
    trap - SIGINT SIGTERM EXIT
    echo ""
    echo -e "${YELLOW}Shutting down MarketMind...${NC}"

    stop_process_tree "$FRONTEND_PID" "frontend server"
    stop_process_tree "$WORKER_PID" "Retail analysis worker"
    stop_process_tree "$BACKEND_PID" "backend server"
    wait "$FRONTEND_PID" "$WORKER_PID" "$BACKEND_PID" >/dev/null 2>&1 || true

    report_port_if_busy "5173" "Frontend"
    report_port_if_busy "8000" "Backend API"
    report_port_if_busy "9000" "MinIO API"
    report_port_if_busy "9001" "MinIO Console"

    if [ "$INFRA_STARTED" = "1" ] && [ "${MARKETMIND_KEEP_INFRA:-0}" != "1" ]; then
        echo -e "${YELLOW}Stopping Docker infrastructure...${NC}"
        docker compose -f docker-compose.dev.yml stop postgres redis minio minio-init >/dev/null 2>&1 || true
    fi

    echo -e "${GREEN}✓ MarketMind environment cleaned up${NC}"
    exit "$exit_code"
}

# Set trap to cleanup on script exit
trap cleanup EXIT
trap 'exit 130' SIGINT
trap 'exit 143' SIGTERM

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                        ║${NC}"
echo -e "${CYAN}║         MarketMind Project             ║${NC}"
echo -e "${CYAN}║      Full Stack Startup Script         ║${NC}"
echo -e "${CYAN}║                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT_DIR"

# Check if startup scripts exist
echo -e "${YELLOW}[1/5] Checking startup scripts...${NC}"
if [ ! -f "$SCRIPT_DIR/start-backend.sh" ]; then
    echo -e "${RED}Error: start-backend.sh not found${NC}"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/start-frontend.sh" ]; then
    echo -e "${RED}Error: start-frontend.sh not found${NC}"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/start-worker.sh" ]; then
    echo -e "${RED}Error: start-worker.sh not found${NC}"
    exit 1
fi

# Make sure scripts are executable
chmod +x "$SCRIPT_DIR/start-backend.sh"
chmod +x "$SCRIPT_DIR/start-frontend.sh"
chmod +x "$SCRIPT_DIR/start-worker.sh"
echo -e "${GREEN}✓ Startup scripts ready${NC}"
echo ""

# Check system requirements
echo -e "${YELLOW}[2/5] Checking system requirements...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' package manager is not installed${NC}"
    echo -e "${YELLOW}Install with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ uv package manager found${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js ${NODE_VERSION} found${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✓ npm ${NPM_VERSION} found${NC}"

# Check curl
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ curl found${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"
echo ""

# Full-stack startup must use the production-like runtime. Force these values so
# stale shell env or a local .env rollback cannot silently switch state to memory.
export REDIS_ENABLED="true"
export TASK_QUEUE_BACKEND="redis"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind}"
export ANALYSIS_QUEUE_NAME="${ANALYSIS_QUEUE_NAME:-retail-analysis}"

ensure_process_alive() {
    local pid="$1"
    local name="$2"
    local log_file="$3"

    if kill -0 "$pid" 2>/dev/null; then
        return 0
    fi

    echo -e "${RED}Error: ${name} exited before becoming ready${NC}"
    echo -e "${YELLOW}Last ${name} log lines:${NC}"
    tail -n 80 "$log_file" 2>/dev/null || true
    exit 1
}

wait_for_http() {
    local name="$1"
    local url="$2"
    local pid="$3"
    local log_file="$4"
    local max_attempts="${5:-60}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        ensure_process_alive "$pid" "$name" "$log_file"
        if curl -fsS "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ ${name} is ready (${url})${NC}"
            return 0
        fi
        echo -e "${YELLOW}Waiting for ${name} (${attempt}/${max_attempts})...${NC}"
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${RED}Error: ${name} did not become ready at ${url}${NC}"
    echo -e "${YELLOW}Last ${name} log lines:${NC}"
    tail -n 80 "$log_file" 2>/dev/null || true
    exit 1
}

wait_for_worker() {
    local pid="$1"
    local log_file="$2"
    local max_attempts="${3:-60}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        ensure_process_alive "$pid" "Retail analysis worker" "$log_file"
        if grep -q "Listening on ${ANALYSIS_QUEUE_NAME}" "$log_file" 2>/dev/null; then
            echo -e "${GREEN}✓ Retail analysis worker is ready (${ANALYSIS_QUEUE_NAME})${NC}"
            return 0
        fi
        echo -e "${YELLOW}Waiting for Retail analysis worker (${attempt}/${max_attempts})...${NC}"
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${RED}Error: Retail analysis worker did not become ready${NC}"
    echo -e "${YELLOW}Last worker log lines:${NC}"
    tail -n 80 "$log_file" 2>/dev/null || true
    exit 1
}

ensure_port_free() {
    local port="$1"
    local name="$2"

    if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/tmp/marketmind-port-check.log 2>/dev/null; then
        echo -e "${RED}Error: ${name} port ${port} is already in use${NC}"
        echo -e "${YELLOW}Existing listener:${NC}"
        cat /tmp/marketmind-port-check.log
        rm -f /tmp/marketmind-port-check.log
        exit 1
    fi
    rm -f /tmp/marketmind-port-check.log
}

ensure_port_free "8000" "Backend API"
ensure_port_free "5173" "Frontend"
ensure_port_free "9000" "MinIO API"
ensure_port_free "9001" "MinIO Console"

# Start infrastructure
echo -e "${YELLOW}[3/5] Starting Docker infrastructure...${NC}"
docker compose -f docker-compose.dev.yml up -d postgres redis minio minio-init
INFRA_STARTED=1

wait_for_service() {
    local service_name="$1"
    local max_attempts="${2:-30}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "marketmind-${service_name}-dev" 2>/dev/null || true)"
        if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
            echo -e "${GREEN}✓ ${service_name} is ${status}${NC}"
            return 0
        fi
        echo -e "${YELLOW}Waiting for ${service_name} (${attempt}/${max_attempts})...${NC}"
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

# Pre-install dependencies
echo -e "${YELLOW}[4/5] Installing dependencies...${NC}"

# Backend dependencies
echo -e "${BLUE}Installing backend dependencies...${NC}"
uv sync
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Frontend dependencies
echo -e "${BLUE}Installing frontend dependencies...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    if [ -f "init-vue.sh" ]; then
        chmod +x init-vue.sh
        ./init-vue.sh
    else
        npm install
    fi
fi
cd ..
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
echo ""

echo -e "${BLUE}Checking backend runtime wiring...${NC}"
uv run python -m backend.core.runtime_checks check-retail-runtime --dry-run
echo -e "${GREEN}✓ Backend runtime wiring is PostgreSQL/Redis ready${NC}"
echo ""

echo -e "${BLUE}Checking object storage readiness...${NC}"
uv run python -m backend.core.runtime_checks check-object-storage --sandbox || true
echo -e "${GREEN}✓ Object storage check completed${NC}"
echo ""

# Apply database migrations after dependencies are ready
echo -e "${BLUE}Applying database migrations...${NC}"
uv run python -m alembic upgrade head
echo -e "${GREEN}✓ Database schema is ready${NC}"
echo ""

# Create log directory
mkdir -p logs

# Start servers
echo -e "${YELLOW}[5/5] Starting servers...${NC}"
echo ""

# Start backend in background
echo -e "${BLUE}Starting backend server...${NC}"
MARKETMIND_SKIP_INFRA=1 "$SCRIPT_DIR/start-backend.sh" > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend server launching (PID: $BACKEND_PID)${NC}"
echo -e "${CYAN}  Backend logs: logs/backend.log${NC}"
wait_for_http "Backend API" "http://127.0.0.1:8000/api/health/" "$BACKEND_PID" "logs/backend.log"

# Start Retail analysis worker in background
echo -e "${BLUE}Starting Retail analysis worker...${NC}"
MARKETMIND_SKIP_DEP_SYNC=1 "$SCRIPT_DIR/start-worker.sh" > logs/worker.log 2>&1 &
WORKER_PID=$!
echo -e "${GREEN}✓ Retail analysis worker launching (PID: $WORKER_PID)${NC}"
echo -e "${CYAN}  Worker logs: logs/worker.log${NC}"
wait_for_worker "$WORKER_PID" "logs/worker.log"

# Start frontend in background
echo -e "${BLUE}Starting frontend server...${NC}"
"$SCRIPT_DIR/start-frontend.sh" > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend server launching (PID: $FRONTEND_PID)${NC}"
echo -e "${CYAN}  Frontend logs: logs/frontend.log${NC}"
wait_for_http "Frontend" "http://127.0.0.1:5173" "$FRONTEND_PID" "logs/frontend.log"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MarketMind is fully ready!         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Access Points:${NC}"
echo -e "  Frontend:     ${BLUE}http://localhost:5173${NC}"
echo -e "  Backend API:  ${BLUE}http://localhost:8000/api${NC}"
echo -e "  API Docs:     ${BLUE}http://localhost:8000/api/docs${NC}"
echo -e "  Postgres:     ${BLUE}localhost:5432${NC}"
echo -e "  Redis:        ${BLUE}localhost:6379${NC}"
echo -e "  MinIO API:    ${BLUE}http://localhost:9000${NC}"
echo -e "  MinIO Console:${BLUE}http://localhost:9001${NC}"
echo ""
echo -e "${GREEN}Log Files:${NC}"
echo -e "  Backend:  ${CYAN}logs/backend.log${NC}"
echo -e "  Worker:   ${CYAN}logs/worker.log${NC}"
echo -e "  Frontend: ${CYAN}logs/frontend.log${NC}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View backend logs:  ${CYAN}tail -f logs/backend.log${NC}"
echo -e "  View worker logs:   ${CYAN}tail -f logs/worker.log${NC}"
echo -e "  View frontend logs: ${CYAN}tail -f logs/frontend.log${NC}"
echo -e "  Stop all servers:   ${CYAN}Press Ctrl+C${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Wait for background processes
wait
