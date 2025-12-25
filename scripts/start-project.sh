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

# Cleanup function to kill child processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down MarketMind...${NC}"
    # Kill all child processes
    pkill -P $$ || true
    echo -e "${GREEN}✓ All servers stopped${NC}"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

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
echo -e "${YELLOW}[1/4] Checking startup scripts...${NC}"
if [ ! -f "$SCRIPT_DIR/start-backend.sh" ]; then
    echo -e "${RED}Error: start-backend.sh not found${NC}"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/start-frontend.sh" ]; then
    echo -e "${RED}Error: start-frontend.sh not found${NC}"
    exit 1
fi

# Make sure scripts are executable
chmod +x "$SCRIPT_DIR/start-backend.sh"
chmod +x "$SCRIPT_DIR/start-frontend.sh"
echo -e "${GREEN}✓ Startup scripts ready${NC}"
echo ""

# Check system requirements
echo -e "${YELLOW}[2/4] Checking system requirements...${NC}"

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
echo ""

# Pre-install dependencies
echo -e "${YELLOW}[3/4] Installing dependencies...${NC}"

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

# Create log directory
mkdir -p logs

# Start servers
echo -e "${YELLOW}[4/4] Starting servers...${NC}"
echo ""

# Start backend in background
echo -e "${BLUE}Starting backend server...${NC}"
"$SCRIPT_DIR/start-backend.sh" > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
echo -e "${CYAN}  Backend logs: logs/backend.log${NC}"

# Wait a bit for backend to start
sleep 3

# Start frontend in background
echo -e "${BLUE}Starting frontend server...${NC}"
"$SCRIPT_DIR/start-frontend.sh" > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend server started (PID: $FRONTEND_PID)${NC}"
echo -e "${CYAN}  Frontend logs: logs/frontend.log${NC}"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MarketMind is now running!         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Access Points:${NC}"
echo -e "  Frontend:    ${BLUE}http://localhost:5173${NC}"
echo -e "  Backend API: ${BLUE}http://localhost:8000/api${NC}"
echo -e "  API Docs:    ${BLUE}http://localhost:8000/api/docs${NC}"
echo ""
echo -e "${GREEN}Log Files:${NC}"
echo -e "  Backend:  ${CYAN}logs/backend.log${NC}"
echo -e "  Frontend: ${CYAN}logs/frontend.log${NC}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View backend logs:  ${CYAN}tail -f logs/backend.log${NC}"
echo -e "  View frontend logs: ${CYAN}tail -f logs/frontend.log${NC}"
echo -e "  Stop all servers:   ${CYAN}Press Ctrl+C${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Wait for background processes
wait
