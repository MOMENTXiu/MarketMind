#!/bin/bash

# MarketMind Project Startup Script
# Starts backend, worker, and frontend directly.
# Run ./scripts/deploy-project.sh first to prepare infrastructure and dependencies.

set -e

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

    if [ "${MARKETMIND_KEEP_INFRA:-0}" != "1" ]; then
        echo -e "${YELLOW}Stopping Docker infrastructure...${NC}"
        docker compose -f docker-compose.dev.yml stop postgres redis minio minio-init >/dev/null 2>&1 || true
    fi

    echo -e "${GREEN}MarketMind environment cleaned up${NC}"
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

# Check required runtime tools
echo -e "${YELLOW}[1/3] Checking runtime tools...${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' package manager is not installed${NC}"
    echo -e "${YELLOW}Install with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi
echo -e "${GREEN}  uv found${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}  Node.js found${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}  npm found${NC}"

if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}  curl found${NC}"
echo ""

# Verify Docker infrastructure is ready
echo -e "${YELLOW}[2/3] Verifying infrastructure readiness...${NC}"

check_service_running() {
    local service_name="$1"
    local status
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "marketmind-${service_name}-dev" 2>/dev/null || true)"
    if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
        echo -e "${GREEN}  ${service_name} is ${status}${NC}"
        return 0
    fi
    return 1
}

wait_for_infra() {
    local service_name="$1"
    local max_attempts="${2:-30}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        local status
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

INFRA_READY=true
for svc in postgres redis minio; do
    if ! check_service_running "$svc"; then
        INFRA_READY=false
    fi
done

if [ "$INFRA_READY" != "true" ]; then
    echo ""
    echo -e "${YELLOW}  Docker infrastructure not running, starting it...${NC}"
    docker compose -f docker-compose.dev.yml up -d postgres redis minio minio-init
    for svc in postgres redis minio; do
        wait_for_infra "$svc"
    done
fi

echo -e "${BLUE}  Ensuring sample files in MinIO...${NC}"
uv run python scripts/init-samples-to-minio.py >/dev/null 2>&1 || true
echo -e "${GREEN}  Sample files ready${NC}"
echo ""

# Ensure ports are free
echo -e "${YELLOW}Checking application ports...${NC}"

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
echo -e "${GREEN}  All ports are free${NC}"
echo ""

# Set runtime environment
export REDIS_ENABLED="true"
export TASK_QUEUE_BACKEND="redis"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind}"
export ANALYSIS_QUEUE_NAME="${ANALYSIS_QUEUE_NAME:-retail-analysis}"
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Create log directory
mkdir -p logs

# Helper: ensure process is still alive
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
            echo -e "${GREEN}  ${name} is ready (${url})${NC}"
            return 0
        fi
        echo -e "${YELLOW}  Waiting for ${name} (${attempt}/${max_attempts})...${NC}"
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
            echo -e "${GREEN}  Retail analysis worker is ready (${ANALYSIS_QUEUE_NAME})${NC}"
            return 0
        fi
        echo -e "${YELLOW}  Waiting for Retail analysis worker (${attempt}/${max_attempts})...${NC}"
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${RED}Error: Retail analysis worker did not become ready${NC}"
    echo -e "${YELLOW}Last worker log lines:${NC}"
    tail -n 80 "$log_file" 2>/dev/null || true
    exit 1
}

# Start servers
echo -e "${YELLOW}[3/3] Starting servers...${NC}"
echo ""

# Start backend in background
echo -e "${BLUE}Starting backend server...${NC}"
uv run python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}  Backend server launching (PID: $BACKEND_PID)${NC}"
echo -e "${CYAN}  Backend logs: logs/backend.log${NC}"
wait_for_http "Backend API" "http://127.0.0.1:8000/api/health/" "$BACKEND_PID" "logs/backend.log"

# Start Retail analysis worker in background
echo -e "${BLUE}Starting Retail analysis worker...${NC}"
uv run python -m rq.cli worker "$ANALYSIS_QUEUE_NAME" --url "$REDIS_URL" > logs/worker.log 2>&1 &
WORKER_PID=$!
echo -e "${GREEN}  Retail analysis worker launching (PID: $WORKER_PID)${NC}"
echo -e "${CYAN}  Worker logs: logs/worker.log${NC}"
wait_for_worker "$WORKER_PID" "logs/worker.log"

# Start frontend in background
echo -e "${BLUE}Starting frontend server...${NC}"
cd frontend
npm run dev -- --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"
echo -e "${GREEN}  Frontend server launching (PID: $FRONTEND_PID)${NC}"
echo -e "${CYAN}  Frontend logs: logs/frontend.log${NC}"
wait_for_http "Frontend" "http://127.0.0.1:5173" "$FRONTEND_PID" "logs/frontend.log"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MarketMind is fully ready!         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Access Points:${NC}"
echo -e "  Frontend:     ${BLUE}http://localhost:5173${NC}"
echo -e "  Admin Console:${BLUE}http://localhost:5173/admin${NC}"
echo -e "  Backend API:  ${BLUE}http://localhost:8000/api${NC}"
echo -e "  API Docs:     ${BLUE}http://localhost:8000/api/docs${NC}"
echo -e "  Postgres:     ${BLUE}localhost:5432${NC}"
echo -e "  Redis:        ${BLUE}localhost:6379${NC}"
echo -e "  MinIO API:    ${BLUE}http://localhost:9000${NC}"
echo -e "  MinIO Console:${BLUE}http://localhost:9001${NC}"
echo ""

ADMIN_EMAIL="${ADMIN_BOOTSTRAP_EMAIL:-}"
if [ -n "$ADMIN_EMAIL" ]; then
    echo -e "${GREEN}Admin credentials (if bootstrapped):${NC}"
    echo -e "  Email: ${CYAN}${ADMIN_EMAIL}${NC}"
    echo -e "  Role:  ${CYAN}admin${NC}"
    echo -e "  URL:   ${CYAN}http://localhost:5173/admin${NC}"
else
    echo -e "${YELLOW}Tip: Set ADMIN_BOOTSTRAP_EMAIL in deploy-project.sh to bootstrap an admin user.${NC}"
fi
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

# Wait for background processes
wait
