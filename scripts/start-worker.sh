#!/bin/bash

# MarketMind Retail Analysis Worker Startup Script

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MarketMind Retail Analysis Worker${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT_DIR"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is not installed${NC}"
    exit 1
fi

if [ "${MARKETMIND_SKIP_DEP_SYNC:-0}" != "1" ]; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    uv sync
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
    echo ""
fi

export REDIS_ENABLED="${REDIS_ENABLED:-true}"
export TASK_QUEUE_BACKEND="${TASK_QUEUE_BACKEND:-redis}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export ANALYSIS_QUEUE_NAME="${ANALYSIS_QUEUE_NAME:-retail-analysis}"
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo -e "${YELLOW}Starting RQ worker...${NC}"
echo -e "Queue: ${BLUE}${ANALYSIS_QUEUE_NAME}${NC}"
echo -e "Redis: ${BLUE}${REDIS_URL}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the worker${NC}"
echo ""

uv run rq worker "$ANALYSIS_QUEUE_NAME" --url "$REDIS_URL"