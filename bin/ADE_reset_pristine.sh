#!/bin/bash
# ## @DOC
# ### Ade Reset Pristine
# Resets the environment to a pristine state.


# Pristine Reset Script
# RESETS THE REPOSITORY TO A FRESH STATE.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
NON_INTERACTIVE=false
FORCE_LOCAL=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -y|--yes|--non-interactive) NON_INTERACTIVE=true ;;
        --force) FORCE_LOCAL=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ "$NON_INTERACTIVE" = false ]; then
    echo -e "${RED}WARNING: NUCLEAR RESET${NC}"
    echo -e "${YELLOW}This script will:${NC}"
    echo "1. Discard ALL local changes to tracked files."
    echo "2. Delete ALL untracked files (.env, .venv, node_modules, etc)."
    if [ "$FORCE_LOCAL" = false ]; then
        echo "3. Convert this repo to a SHALLOW CLONE (depth 1, no history)."
    fi
    echo ""
    echo -e "${RED}Make sure you have a backup of your .env if not stashed!${NC}"
    echo ""
    read -p "Are you absolutely sure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Check for uncommitted changes
STASHED=false
if [[ -n $(git status -s) ]]; then
    if [ "$NON_INTERACTIVE" = false ]; then
        read -p "Uncommitted changes detected. Stash and restore? (Y/n) " -n 1 -r
        echo
        SHOULD_STASH=$REPLY
    else
        # In non-interactive mode, we only stash if NOT forced local (which is usually for internal testing)
        # Actually, let's just default to "n" in non-interactive unless we want to be safe.
        # But if the caller (test_configurations.py) already stashed, we don't want to double stash.
        SHOULD_STASH="n"
    fi

    if [[ $SHOULD_STASH =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Stashing changes...${NC}"
        if git stash push --include-untracked -m "Auto-stash by reset_pristine"; then
             STASHED=true
        else
             echo -e "${RED}Stash failed. Proceeding anyway (work might be lost).${NC}"
        fi
    fi
fi

if [ "$FORCE_LOCAL" = true ]; then
    echo -e "${BLUE}Performing local nuclear wipe...${NC}"
    # Explicitly remove heavy hitters to avoid any git clean issues
    rm -rf .venv node_modules build dist *.egg-info
    git checkout .
    git clean -xfd
else
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo -e "${BLUE}Converting to shallow clone (branch: $BRANCH)...${NC}"
    # Ensure we are online and have an origin
    if git remote | grep -q 'origin'; then
        if git fetch --depth 1 origin "$BRANCH" 2>/dev/null; then
             git reset --hard FETCH_HEAD
        else
             echo "Fetch failed, continuing with local hard reset."
             git reset --hard "origin/$BRANCH" 2>/dev/null || git reset --hard HEAD
        fi
    else
        git reset --hard HEAD
    fi
    git reflog expire --expire=now --all
    git gc --prune=now
    git clean -xfd
fi

if [ "$STASHED" = true ]; then
    echo -e "${BLUE}Restoring stashed changes...${NC}"
    git stash pop || echo -e "${RED}Stash pop failed. Manual restoration required.${NC}"
fi

echo -e "${GREEN}Repository reset complete.${NC}"

