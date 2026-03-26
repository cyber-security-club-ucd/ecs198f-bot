#!/usr/bin/env bash
# install.sh — Easy install script for ecs198f-bot using UV
# Usage: ./scripts/install.sh

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

info()    { echo -e "${BOLD}[ecs198f-bot]${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "${RED}✗${RESET}  $*" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── 1. Check Python ──────────────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install Python 3.12+ before running this script."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MIN_MAJOR=3; PY_MIN_MINOR=12
if python3 -c "import sys; sys.exit(0 if sys.version_info >= ($PY_MIN_MAJOR, $PY_MIN_MINOR) else 1)"; then
    success "Python $PY_VER detected"
else
    error "Python $PY_MIN_MAJOR.$PY_MIN_MINOR+ is required (found $PY_VER)"
fi

# ── 2. Install UV if missing ─────────────────────────────────────────────────
info "Checking for UV..."
if command -v uv &>/dev/null; then
    success "UV $(uv --version) already installed"
else
    warn "UV not found — installing via pip..."
    if command -v pip3 &>/dev/null; then
        pip3 install --quiet uv
    elif command -v pip &>/dev/null; then
        pip install --quiet uv
    else
        error "pip not found. Install pip or install UV manually: https://docs.astral.sh/uv/#installation"
    fi
    success "UV installed: $(uv --version)"
fi

# ── 3. Sync virtual environment ──────────────────────────────────────────────
info "Installing dependencies with UV..."
uv sync
success "Dependencies installed in .venv/"

# ── 4. Copy .env if not present ──────────────────────────────────────────────
info "Checking .env..."
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        warn ".env created from .env.example — please fill in your values before running the bot"
    else
        warn "No .env.example found. Create a .env file before running the bot."
    fi
else
    success ".env already exists"
fi

# ── 5. Print next steps ──────────────────────────────────────────────────────
echo ""
info "Installation complete!"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo "  1. Edit .env with your Discord bot token and Authentik credentials"
echo "  2. Start the stack:    docker compose up -d"
echo "  3. Or run locally:     .venv/bin/python main.py"
echo ""
echo -e "  ${BOLD}Run tests:${RESET}"
echo "  docker compose -f docker-compose.test.yml up -d --wait"
echo "  .venv/bin/python -m pytest"
