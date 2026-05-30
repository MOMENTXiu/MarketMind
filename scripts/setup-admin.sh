#!/bin/bash

# MarketMind Admin Setup Script
# Interactively prompts for admin email/password, writes to .env,
# and bootstraps the admin role in the database.
#
# Usage: ./scripts/setup-admin.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env"

# ── Banner ───────────────────────────────────────────────────────────────────

clear 2>/dev/null || true
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                              ║${NC}"
echo -e "${CYAN}║        MarketMind Admin Console Setup        ║${NC}"
echo -e "${CYAN}║                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  This script will create an admin user for the"
echo -e "  Admin Console at ${CYAN}http://localhost:5173/admin${NC}"
echo ""

# ── Check if .env exists ─────────────────────────────────────────────────────

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}  No .env file found. Creating from .env.example...${NC}"
    if [ -f "$ROOT_DIR/.env.example" ]; then
        cp "$ROOT_DIR/.env.example" "$ENV_FILE"
        echo -e "${GREEN}  Created .env from .env.example${NC}"
    else
        touch "$ENV_FILE"
        echo -e "${GREEN}  Created empty .env${NC}"
    fi
    echo ""
fi

# ── Load existing values ─────────────────────────────────────────────────────

set -a
source "$ENV_FILE" 2>/dev/null || true
set +a

EXISTING_EMAIL="${ADMIN_EMAIL:-}"
EXISTING_PASSWORD="${ADMIN_PASSWORD:-}"
EXISTING_DISPLAY="${ADMIN_DISPLAY_NAME:-Admin}"

# ── Step 1: Admin Email ──────────────────────────────────────────────────────

echo -e "${BOLD}Step 1/3 — Admin Email${NC}"
echo -e "  This user must already be registered in MarketMind."
echo -e "  If not, register at ${CYAN}http://localhost:5173/register${NC} first."
echo ""

if [ -n "$EXISTING_EMAIL" ]; then
    echo -e "  Current value: ${CYAN}${EXISTING_EMAIL}${NC}"
    read -r -p "  Press Enter to keep, or type a new email: " INPUT_EMAIL
    ADMIN_EMAIL="${INPUT_EMAIL:-$EXISTING_EMAIL}"
else
    read -r -p "  Admin email: " ADMIN_EMAIL
    while [ -z "$ADMIN_EMAIL" ]; do
        echo -e "  ${RED}Email cannot be empty.${NC}"
        read -r -p "  Admin email: " ADMIN_EMAIL
    done
fi

echo ""

# ── Step 2: Admin Password ───────────────────────────────────────────────────

echo -e "${BOLD}Step 2/3 — Admin Password${NC}"
echo -e "  This is the login password for the admin account."
echo -e "  ${YELLOW}Password will be stored in .env — keep this file secure.${NC}"
echo ""

if [ -n "$EXISTING_PASSWORD" ]; then
    echo -e "  Current value: ${CYAN}(already set)${NC}"
    read -r -s -p "  Press Enter to keep, or type a new password: " INPUT_PASSWORD
    echo ""
    ADMIN_PASSWORD="${INPUT_PASSWORD:-$EXISTING_PASSWORD}"
else
    read -r -s -p "  Admin password: " ADMIN_PASSWORD
    echo ""
    while [ -z "$ADMIN_PASSWORD" ]; do
        echo -e "  ${RED}Password cannot be empty.${NC}"
        read -r -s -p "  Admin password: " ADMIN_PASSWORD
        echo ""
    done
    # Confirm
    read -r -s -p "  Confirm password: " CONFIRM_PASSWORD
    echo ""
    while [ "$ADMIN_PASSWORD" != "$CONFIRM_PASSWORD" ]; do
        echo -e "  ${RED}Passwords do not match.${NC}"
        read -r -s -p "  Admin password: " ADMIN_PASSWORD
        echo ""
        read -r -s -p "  Confirm password: " CONFIRM_PASSWORD
        echo ""
    done
fi

echo ""

# ── Step 3: Display Name ─────────────────────────────────────────────────────

echo -e "${BOLD}Step 3/3 — Display Name${NC}"
echo -e "  Optional display name shown in the UI."
echo ""

read -r -p "  Display name [${EXISTING_DISPLAY}]: " INPUT_DISPLAY
ADMIN_DISPLAY_NAME="${INPUT_DISPLAY:-$EXISTING_DISPLAY}"

echo ""
echo -e "${CYAN}──────────────────────────────────────────────${NC}"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────

echo -e "${BOLD}Confirm admin settings:${NC}"
echo ""
echo -e "  Email:        ${CYAN}${ADMIN_EMAIL}${NC}"
echo -e "  Display Name: ${CYAN}${ADMIN_DISPLAY_NAME}${NC}"
echo -e "  Password:     ${CYAN}(hidden)${NC}"
echo ""

read -r -p "  Write to .env and bootstrap? [Y/n] " CONFIRM
if [ "$CONFIRM" = "n" ] || [ "$CONFIRM" = "N" ]; then
    echo -e "${YELLOW}  Cancelled.${NC}"
    exit 0
fi

echo ""

# ── Write to .env ────────────────────────────────────────────────────────────

echo -e "${BLUE}Writing to .env...${NC}"

# Remove existing admin lines, then append new ones
if grep -q "^ADMIN_EMAIL=" "$ENV_FILE" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/^ADMIN_EMAIL=/d' "$ENV_FILE"
        sed -i '' '/^ADMIN_PASSWORD=/d' "$ENV_FILE"
        sed -i '' '/^ADMIN_DISPLAY_NAME=/d' "$ENV_FILE"
        sed -i '' '/^ADMIN_CONSOLE_URL=/d' "$ENV_FILE"
    else
        sed -i '/^ADMIN_EMAIL=/d' "$ENV_FILE"
        sed -i '/^ADMIN_PASSWORD=/d' "$ENV_FILE"
        sed -i '/^ADMIN_DISPLAY_NAME=/d' "$ENV_FILE"
        sed -i '/^ADMIN_CONSOLE_URL=/d' "$ENV_FILE"
    fi
fi

{
    echo ""
    echo "# ── Admin Console (set by setup-admin.sh) ─────────────────────────────"
    echo "ADMIN_EMAIL=${ADMIN_EMAIL}"
    echo "ADMIN_PASSWORD=${ADMIN_PASSWORD}"
    echo "ADMIN_DISPLAY_NAME=${ADMIN_DISPLAY_NAME}"
    echo "ADMIN_CONSOLE_URL=http://localhost:5173/admin"
} >> "$ENV_FILE"

echo -e "${GREEN}  .env updated${NC}"
echo ""

# ── Bootstrap admin role ─────────────────────────────────────────────────────

echo -e "${BLUE}Bootstrapping admin role in database...${NC}"
echo -e "  Promoting ${CYAN}${ADMIN_EMAIL}${NC} to admin..."

ADMIN_BOOTSTRAP_EMAIL="$ADMIN_EMAIL" uv run python -m backend.scripts.bootstrap_admin 2>&1 || {
    echo ""
    echo -e "${RED}  Bootstrap failed — user may not be registered yet.${NC}"
    echo -e "${YELLOW}  Credentials are saved in .env. Run this script again after registering:${NC}"
    echo -e "    1. Start app:  ${CYAN}./scripts/start-project.sh${NC}"
    echo -e "    2. Register:   ${CYAN}http://localhost:5173/register${NC}"
    echo -e "       Email:      ${CYAN}${ADMIN_EMAIL}${NC}"
    echo -e "       Password:   ${CYAN}(the one you just set)${NC}"
    echo -e "    3. Re-run:     ${CYAN}./scripts/setup-admin.sh${NC}"
    echo ""
    exit 1
}

echo -e "${GREEN}  Admin role assigned${NC}"
echo ""

# ── Done ─────────────────────────────────────────────────────────────────────

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      Admin setup complete!                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Admin Console:${NC}  ${CYAN}http://localhost:5173/admin${NC}"
echo -e "  ${BOLD}Email:${NC}         ${CYAN}${ADMIN_EMAIL}${NC}"
echo -e "  ${BOLD}Password:${NC}       ${CYAN}(saved in .env)${NC}"
echo -e "  ${BOLD}Role:${NC}           ${CYAN}admin${NC}"
echo ""
echo -e "  ${YELLOW}Start the app:  ./scripts/start-project.sh${NC}"
echo ""
