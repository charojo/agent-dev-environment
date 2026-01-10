#!/bin/bash
# Environment Ensure Script for Papeterie Engine
# Ensures dependencies are installed for both Backend and Frontend.
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}Checking environment health...${NC}"

# 1. Check Python environment (.venv)
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}.venv not found. Initializing Python environment...${NC}"
    uv sync
    uv pip install -e .
    echo -e "${GREEN}Python environment initialized.${NC}"
else
    # Check if pyproject.toml is newer than .venv
    if [ "pyproject.toml" -nt ".venv" ]; then
        echo -e "${YELLOW}pyproject.toml updated. Syncing Python dependencies...${NC}"
        uv sync
        echo -e "${GREEN}Python dependencies synced.${NC}"
    else
        echo -e "${GREEN}Python environment is up to date.${NC}"
    fi
fi

# 2. Check Web environment (node_modules)
if [ ! -d "src/web/node_modules" ]; then
    echo -e "${YELLOW}node_modules not found in src/web. Initializing Web environment...${NC}"
    cd src/web && npm install
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}Web environment initialized.${NC}"
else
    # Check if package.json is newer than node_modules
    if [ "src/web/package.json" -nt "src/web/node_modules" ]; then
        echo -e "${YELLOW}src/web/package.json updated. Syncing Web dependencies...${NC}"
        cd src/web && npm install
        cd "$PROJECT_ROOT"
        echo -e "${GREEN}Web dependencies synced.${NC}"
    else
        echo -e "${GREEN}Web environment is up to date.${NC}"
    fi
fi

# 3. Check for .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found.${NC}"
    echo "Please create a .env file with your GEMINI_API_KEY as per docs/HOWTO_Develop.md"
fi

echo -e "${GREEN}Environment check complete!${NC}"
