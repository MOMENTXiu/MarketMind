#!/bin/bash

# MarketMind Backend Startup Script
# This script sets up the environment and starts the FastAPI backend server

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MarketMind Backend Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT_DIR"

# Check Python version
echo -e "${YELLOW}[1/6] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.13"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION${NC}"
    echo -e "${YELLOW}Hint: This project requires Python 3.13.9${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version $PYTHON_VERSION is compatible${NC}"
echo ""

# Check if uv is installed
echo -e "${YELLOW}[2/6] Checking uv package manager...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is not installed${NC}"
    echo -e "${YELLOW}Please install uv: https://github.com/astral-sh/uv${NC}"
    echo -e "${YELLOW}Quick install: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ uv is installed${NC}"
echo ""

# Start Docker infrastructure when running the backend directly
if [ "${MARKETMIND_SKIP_INFRA:-0}" != "1" ]; then
    echo -e "${YELLOW}[infra] Ensuring Docker infrastructure is running...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
        exit 1
    fi

    docker compose -f docker-compose.dev.yml up -d postgres redis

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
    echo ""
fi

# Install/sync Python dependencies
echo -e "${YELLOW}[3/6] Installing Python dependencies...${NC}"
if ! uv sync; then
    echo -e "${RED}Error: Failed to sync Python dependencies${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Create necessary directories
echo -e "${YELLOW}[4/6] Creating required directories...${NC}"
mkdir -p outputs/charts
mkdir -p outputs/reports
mkdir -p data/projects
echo -e "${GREEN}✓ Directories created:${NC}"
echo "  - outputs/charts"
echo "  - outputs/reports"
echo "  - data/projects"
echo ""

# Check if .env file exists (optional)
echo -e "${YELLOW}[5/6] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Notice: No .env file found. Using default configuration.${NC}"
    echo -e "${YELLOW}You can create a .env file to override default settings.${NC}"
else
    echo -e "${GREEN}✓ .env file found${NC}"
fi
export REDIS_ENABLED="${REDIS_ENABLED:-true}"
export TASK_QUEUE_BACKEND="${TASK_QUEUE_BACKEND:-redis}"
echo ""

# Apply database migrations
echo -e "${YELLOW}[db] Applying database migrations...${NC}"
uv run alembic upgrade head
echo -e "${GREEN}✓ Database schema is ready${NC}"
echo ""

# Start the backend server
echo -e "${YELLOW}[6/6] Starting FastAPI backend server...${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Backend Server Starting${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "API Base URL: ${BLUE}http://localhost:8000/api${NC}"
echo -e "API Docs: ${BLUE}http://localhost:8000/api/docs${NC}"
echo -e "Health Check: ${BLUE}http://localhost:8000/api/health${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run the server
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
