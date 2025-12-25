#!/bin/bash

# MarketMind Frontend Startup Script
# This script sets up the environment and starts the Vue3 frontend development server

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MarketMind Frontend Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT_DIR/frontend"

# Check Node.js version
echo -e "${YELLOW}[1/5] Checking Node.js version...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo -e "${YELLOW}Please install Node.js 18 or higher: https://nodejs.org/${NC}"
    exit 1
fi

NODE_VERSION=$(node --version | grep -oE '[0-9]+' | head -n1)
REQUIRED_NODE_VERSION=18

if [ "$NODE_VERSION" -lt "$REQUIRED_NODE_VERSION" ]; then
    echo -e "${RED}Error: Node.js $REQUIRED_NODE_VERSION or higher is required. Found: v$NODE_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js version v$NODE_VERSION is compatible${NC}"
echo ""

# Check if npm is installed
echo -e "${YELLOW}[2/5] Checking npm...${NC}"
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✓ npm version $NPM_VERSION is installed${NC}"
echo ""

# Check if node_modules exists, if not run initialization
echo -e "${YELLOW}[3/5] Checking dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found. Running initialization...${NC}"

    # Check if init-vue.sh exists
    if [ -f "init-vue.sh" ]; then
        echo -e "${YELLOW}Running init-vue.sh...${NC}"
        chmod +x init-vue.sh
        ./init-vue.sh
    else
        echo -e "${YELLOW}init-vue.sh not found. Installing dependencies manually...${NC}"
        npm install

        # Create environment files
        echo -e "${YELLOW}Creating environment files...${NC}"

        # Create .env.development
        cat > .env.development << EOF
# Development Environment Configuration
VITE_API_BASE_URL=http://localhost:8000/api
VITE_API_TIMEOUT=30000
EOF

        # Create .env.production
        cat > .env.production << EOF
# Production Environment Configuration
VITE_API_BASE_URL=/api
VITE_API_TIMEOUT=30000
EOF

        echo -e "${GREEN}✓ Environment files created${NC}"
    fi
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
fi
echo ""

# Verify environment files exist
echo -e "${YELLOW}[4/5] Checking environment configuration...${NC}"
if [ ! -f ".env.development" ]; then
    echo -e "${YELLOW}Creating .env.development...${NC}"
    cat > .env.development << EOF
# Development Environment Configuration
VITE_API_BASE_URL=http://localhost:8000/api
VITE_API_TIMEOUT=30000
EOF
fi

if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}Creating .env.production...${NC}"
    cat > .env.production << EOF
# Production Environment Configuration
VITE_API_BASE_URL=/api
VITE_API_TIMEOUT=30000
EOF
fi
echo -e "${GREEN}✓ Environment configuration ready${NC}"
echo ""

# Start the development server
echo -e "${YELLOW}[5/5] Starting Vite development server...${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Frontend Server Starting${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Development Server: ${BLUE}http://localhost:5173${NC}"
echo -e "Network Access: ${BLUE}http://<your-ip>:5173${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run the development server
npm run dev
