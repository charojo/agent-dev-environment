#!/bin/bash
## @DOC
# ### Environment Sync
# This script ensures that the development environment is consistent and all 
# required dependencies are installed.
#
# It performs:
# 1. **Python Sync**: Uses `uv sync` to manage virtual environments and extras.
# 2. **Web Sync**: Runs `npm install` in `src/web` if applicable.
# 3. **Tool Checks**: Verifies the presence of `pandoc`, `graphviz`, and `doxygen`.
# 4. **Auto-installation**: Attempts to install missing system tools using `apt` if possible.

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# If we are in agent_env or .agent, the root is one level up
if [[ "$(basename "$PROJECT_ROOT")" == "agent_env" ]] || [[ "$(basename "$PROJECT_ROOT")" == ".agent" ]]; then
    PROJECT_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"
fi

cd "$PROJECT_ROOT"

echo -e "${BLUE}Checking environment health...${NC}"

# Check for VIRTUAL_ENV mismatch (project was moved)
if [ -n "$VIRTUAL_ENV" ]; then
    CURRENT_VENV_PATH="$(cd .venv 2>/dev/null && pwd || true)"
    if [ -n "$CURRENT_VENV_PATH" ] && [ "$VIRTUAL_ENV" != "$CURRENT_VENV_PATH" ]; then
        echo -e "${YELLOW}⚠ Warning: VIRTUAL_ENV mismatch detected.${NC}"
        echo -e "  Current session: $VIRTUAL_ENV"
        echo -e "  Project environment: $CURRENT_VENV_PATH"
        echo -e "  The project may have been moved. Recreating .venv to fix internal paths..."
        rm -rf .venv
    fi
fi

# 1. Check Python environment (.venv)
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}.venv not found. Initializing Python environment...${NC}"
    
    EXTRAS=""
    EXTRAS=""
    if [ -f "$SCRIPT_DIR/ADE_config_utils.py" ]; then
        RAW_EXTRAS=$(uv run python "$SCRIPT_DIR/ADE_config_utils.py" get-extras)
        for extra in $RAW_EXTRAS; do
             EXTRAS="$EXTRAS --extra $extra"
        done
    fi
    
    uv sync $EXTRAS
    # uv pip install -e . # Removed since we use workspace/uv sync
    echo -e "${GREEN}Python environment initialized.${NC}"
else
    # Check if pyproject.toml is newer than .venv
    # Check if pyproject.toml is newer than .venv
    # OR if we have changed configuration in config.toml (which isn't tracked by make/file time easily)
    # For robust usage, we should just run sync if flags change.
    # But for now, we'll just run sync.
    
    EXTRAS=""
    
    if [ -f "$SCRIPT_DIR/ADE_config_utils.py" ]; then
        # Get space-separated list of extras: e.g. "processing renderer"
        RAW_EXTRAS=$(uv run python "$SCRIPT_DIR/ADE_config_utils.py" get-extras)
        for extra in $RAW_EXTRAS; do
             EXTRAS="$EXTRAS --extra $extra"
        done
        if [ -n "$EXTRAS" ]; then
            echo -e "${BLUE}Detected enabled extras:${NC} $RAW_EXTRAS"
        fi
    fi

    # Determine if we need to sync
    SYNC_NEEDED=false
    if [ "pyproject.toml" -nt ".venv" ] || [ "config.toml" -nt ".venv" ]; then
        SYNC_NEEDED=true
    fi
    
    # Check if extras have changed since last sync
    LAST_EXTRAS_FILE=".venv/.last_extras"
    if [ -f "$LAST_EXTRAS_FILE" ]; then
        LAST_EXTRAS=$(cat "$LAST_EXTRAS_FILE")
        if [ "$LAST_EXTRAS" != "$RAW_EXTRAS" ]; then
            SYNC_NEEDED=true
        fi
    else
        SYNC_NEEDED=true
    fi

    if [ "$SYNC_NEEDED" = true ]; then
        echo -e "${YELLOW}Syncing Python dependencies (with extras: ${RAW_EXTRAS:-none})...${NC}"
        if uv sync $EXTRAS; then
            echo "$RAW_EXTRAS" > "$LAST_EXTRAS_FILE"
            echo -e "${GREEN}Python dependencies synced.${NC}"
        else
            echo -e "${RED}Python sync failed.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Python environment is up to date.${NC}"
    fi
fi

# 2. Check Web environment (node/npm) - OPTIONAL but recommended for TS/JS
JS_SUPPORT_ENABLED=$(uv run python "$SCRIPT_DIR/ADE_config_utils.py" get languages.typescript.enabled)
if [[ "$JS_SUPPORT_ENABLED" == "true" ]]; then
    if [ -d "src/web" ] || [ -f "package.json" ]; then
        echo -e "${BLUE}Checking Web environment (Node.js/npm)...${NC}"
        if ! command -v node &> /dev/null; then
            echo -e "${YELLOW}Warning: Node.js not found. Web environment setup skipped.${NC}"
        elif ! command -v npm &> /dev/null; then
            echo -e "${YELLOW}Warning: npm not found. Web environment setup skipped.${NC}"
        else
            echo -e "${GREEN}Node.js ($(node -v)) and npm ($(npm -v)) found.${NC}"
            
            # Sync if src/web exists (legacy structure)
            if [ -d "src/web" ]; then
                if [ ! -d "src/web/node_modules" ]; then
                    echo -e "${YELLOW}node_modules not found in src/web. Initializing...${NC}"
                    cd src/web && npm install
                    cd "$PROJECT_ROOT"
                    echo -e "${GREEN}Web environment initialized.${NC}"
                elif [ "src/web/package.json" -nt "src/web/node_modules" ]; then
                    echo -e "${YELLOW}src/web/package.json updated. Syncing...${NC}"
                    cd src/web && npm install
                    cd "$PROJECT_ROOT"
                    echo -e "${GREEN}Web dependencies synced.${NC}"
                fi
            fi

            # Root level package.json sync
            if [ -f "package.json" ]; then
                 if [ ! -d "node_modules" ]; then
                    echo -e "${YELLOW}node_modules not found in root. Initializing...${NC}"
                    npm install
                    echo -e "${GREEN}Root dependencies initialized.${NC}"
                elif [ "package.json" -nt "node_modules" ]; then
                    echo -e "${YELLOW}package.json updated. Syncing...${NC}"
                    npm install
                    echo -e "${GREEN}Root dependencies synced.${NC}"
                fi
            fi
        fi
    fi
else
    echo -e "${YELLOW}TypeScript/JS disabled in config. Skipping web sync.${NC}"
    if [ -d "node_modules" ]; then
        echo -e "${YELLOW}Removing node_modules as TypeScript is disabled...${NC}"
        rm -rf node_modules
    fi
    if [ -d "src/web/node_modules" ]; then
        echo -e "${YELLOW}Removing src/web/node_modules as TypeScript is disabled...${NC}"
        rm -rf src/web/node_modules
    fi
fi

# 3. Check for .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found.${NC}"
    echo "Please create a .env file if your project requires environment variables."
fi

# 5. Check for Advanced Documentation Tools (Doxygen, Graphviz)
DOCS_ENABLED="false"
DOCS_ENABLED="false"
if [ -f "$SCRIPT_DIR/ADE_config_utils.py" ]; then
    DOCS_ENABLED=$(uv run python "$SCRIPT_DIR/ADE_config_utils.py" get features.documentation.enabled)
fi

if [ "$DOCS_ENABLED" == "true" ]; then
    echo -e "${BLUE}Advanced Documentation enabled. Checking tools...${NC}"
    
    # Pandoc (logic moved inside feature check)
    echo -e "${BLUE}Checking for pandoc...${NC}"
    if ! command -v pandoc &> /dev/null; then
        echo -e "${YELLOW}pandoc not found. Attempting to install...${NC}"
        if [ "$(id -u)" -eq 0 ]; then
             apt-get update && apt-get install -y pandoc
        elif command -v sudo &> /dev/null; then
             sudo apt-get update && sudo apt-get install -y pandoc
        else
             echo -e "${YELLOW}Warning: pandoc not found and cannot install (no sudo or root). PDF generation will be disabled.${NC}"
        fi
    else
        echo -e "${GREEN}pandoc found.${NC}"
    fi

    # Graphviz
    if ! command -v dot &> /dev/null; then
        echo -e "${YELLOW}Graphviz (dot) not found. Installing...${NC}"
         if [ "$(id -u)" -eq 0 ]; then
             apt-get update && apt-get install -y graphviz
        elif command -v sudo &> /dev/null; then
             sudo apt-get update && sudo apt-get install -y graphviz
        else
             echo -e "${YELLOW}Warning: graphviz not found and cannot install using sudo. Diagrams will be skipped.${NC}"
        fi
    else
        echo -e "${GREEN}Graphviz found.${NC}"
    fi

    # Doxygen
    if ! command -v doxygen &> /dev/null; then
        echo -e "${YELLOW}Doxygen not found. Installing...${NC}"
         if [ "$(id -u)" -eq 0 ]; then
             apt-get update && apt-get install -y doxygen
        elif command -v sudo &> /dev/null; then
             sudo apt-get update && sudo apt-get install -y doxygen
        else
             echo -e "${YELLOW}Warning: doxygen not found and cannot install. API docs will be skipped.${NC}"
        fi
    else
        echo -e "${GREEN}Doxygen found.${NC}"
    fi

    # TypeDoc (for TypeScript)
    echo -e "${BLUE}Checking for TypeDoc (TypeScript documentation)...${NC}"
    if ! command -v typedoc &> /dev/null && ! [ -f "node_modules/.bin/typedoc" ]; then
         if [[ "$JS_SUPPORT_ENABLED" == "true" ]]; then
             echo -e "${YELLOW}typedoc not found. Attempting to install via npm...${NC}"
             if command -v npm &> /dev/null; then
                 npm install --no-save typedoc typescript
                 echo -e "${GREEN}typedoc/typescript installed locally.${NC}"
             else
                 echo -e "${YELLOW}Warning: npm not found, cannot install TypeDoc. TypeScript API docs will use Doxygen fallback.${NC}"
             fi
         fi
    else
        echo -e "${GREEN}TypeDoc found.$(command -v typedoc || echo " (local)") ${NC}"
    fi
fi

echo -e "${GREEN}Environment check complete!${NC}"
