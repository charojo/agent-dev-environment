#!/bin/bash
# Pristine Reset Script for Papeterie Engine
# RESETS THE REPOSITORY TO A FRESH, SHALLOW CLONE STATE.
# 1. Converts repo to shallow (depth 1) to save space.
# 2. Deletes ALL untracked files (nuclear clean).

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}WARNNG: NUCLEAR SHALLOW RESET${NC}"
echo -e "${YELLOW}This script will:${NC}"
echo "1. Convert this repo to a SHALLOW CLONE (depth 1, no history)."
echo "2. Discard ALL local changes to tracked files."
echo "3. Delete ALL untracked files (.env, .venv, node_modules, etc)."
echo ""
echo -e "${RED}Make sure you have a backup of your .env!${NC}"
echo ""

read -p "Are you absolutely sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}Converting to shallow clone (branch: $BRANCH)...${NC}"

# Fetch depth 1
git fetch --depth 1 origin "$BRANCH"

# Reset to the fetched head
git reset --hard FETCH_HEAD

# Expire reflogs and prune to remove old history objects immediately
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo -e "${BLUE}Cleaning untracked files...${NC}"
git clean -xfd

echo ""
echo -e "${GREEN}Repository is now a pristine SHALLOW clone.${NC}"
echo "To get back to work:"
echo "1. Restore your .env file"
echo "2. Run: ./scripts/ensure_env.sh"
