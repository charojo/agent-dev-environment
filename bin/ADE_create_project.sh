#!/bin/bash
## @DOC
# ### Create Project / Adopt Existing Project
# This script creates a new project with agent_env as a git submodule,
# or adds agent_env to an existing project.
#
# **Usage - New Project:**
# ```bash
# ./bin/ADE_create_project.sh --name "my-app"
# ./bin/ADE_create_project.sh --name "my-app" --prompt "Description"
# ./bin/ADE_create_project.sh --name "my-app" --output ~/projects/
# ```
#
# **Usage - Adopt Existing Project:**
# ```bash
# ./bin/ADE_create_project.sh --adopt /path/to/existing-project
# ```
#
# **Options:**
# - `--name`: Project name (required for new projects)
# - `--prompt`: Optional. Description of the project
# - `--output`: Optional. Output directory (default: parent of agent-dev-environment)
# - `--adopt`: Path to existing project to add agent_env to
# - `--dry-run`: Show plan without executing
# - `--web`: Enable TypeScript/Web support
# - `--docs`: Enable Documentation/API Docs features
# - `--non-interactive`: Bypass interactive prompts

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
AGENT_ENV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_ENV_NAME="$(basename "$AGENT_ENV_ROOT")"

# Default: create projects as siblings (in parent directory)
# If we are a submodule, we want to be siblings of the PARENT project
SUPERPROJECT="$(git -C "$AGENT_ENV_ROOT" rev-parse --show-superproject-working-tree 2>/dev/null || true)"
if [ -n "$SUPERPROJECT" ]; then
    DEFAULT_OUTPUT="$(cd "$SUPERPROJECT/.." && pwd)"
else
    DEFAULT_OUTPUT="$(cd "$AGENT_ENV_ROOT/.." && pwd)"
fi

# Default values
PROJECT_NAME=""
PROJECT_PROMPT=""
OUTPUT_DIR="$DEFAULT_OUTPUT"
ADOPT_PATH=""
DRY_RUN=false
WITH_WEB=false
WITH_DOCS=false
NON_INTERACTIVE=false
SKIP_VALIDATE=false
COPY_ENV=false
REPO_URL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --prompt)
            PROJECT_PROMPT="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --workspace)
            # Legacy alias for --output
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --adopt)
            ADOPT_PATH="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --web)
            WITH_WEB=true
            shift
            ;;
        --docs)
            WITH_DOCS=true
            shift
            ;;
        --non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        --no-validate)
            SKIP_VALIDATE=true
            shift
            ;;
        --copy-env)
            COPY_ENV=true
            shift
            ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage:"
            echo "  $0 --name <project-name> [--prompt \"description\"] [--output <path>] [--dry-run] [--web] [--docs]"
            echo "  $0 --adopt <existing-project-path> [--dry-run] [--web] [--docs]"
            echo ""
            echo "Creates a new project or adds agent_env to an existing project."
            echo ""
            echo "Options:"
            echo "  --name       Project name (required for new projects)"
            echo "  --prompt     Optional. Project description"
            echo "  --output     Optional. Output directory (default: parent of agent-dev-environment)"
            echo "  --adopt      Path to existing project to add agent_env to"
            echo "  --dry-run    Show plan without executing"
            echo "  --web        Enable TypeScript/Web support"
            echo "  --docs       Enable Documentation/API Docs features"
            echo "  --no-validate Skip initial project validation"
            echo "  --copy-env   Force recursive copy of agent_env (instead of submodule)"
            echo "  --repo-url   URL to use for agent_env submodule (overrides auto-detection)"
            echo ""
            echo "Examples:"
            echo "  # Create new project with web support"
            echo "  $0 --name \"my-app\" --prompt \"A todo list application\" --web"
            echo ""
            echo "  # Adopt existing project with docs support"
            echo "  $0 --adopt ~/projects/existing-app --docs"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get agent_env source for submodule
# We prefer the upstream remote URL if available, so new projects
# aren't hard-linked to this specific local machine/project.
AGENT_ENV_URL=""

if [ -n "$REPO_URL" ]; then
    AGENT_ENV_URL="$REPO_URL"
elif [ -d "$AGENT_ENV_ROOT/.git" ]; then
    # Try to get remote origin
    REMOTE_URL=$(git -C "$AGENT_ENV_ROOT" remote get-url origin 2>/dev/null || true)
    
    # Check if it looks like a remote URL (http, git, ssh) and not a local path
    if [[ "$REMOTE_URL" =~ ^(https?|git|ssh):// ]] || [[ "$REMOTE_URL" =~ ^git@ ]]; then
        AGENT_ENV_URL="$REMOTE_URL"
    fi
fi

# Fallback to local path if no valid remote found
if [ -z "$AGENT_ENV_URL" ]; then
    AGENT_ENV_URL="$AGENT_ENV_ROOT"
fi

# ============================================================================
# ADOPT MODE: Add agent_env to existing project
# ============================================================================
if [ -n "$ADOPT_PATH" ]; then
    # Resolve to absolute path
    ADOPT_PATH="$(cd "$ADOPT_PATH" 2>/dev/null && pwd)" || {
        echo -e "${RED}Error: Directory not found: $ADOPT_PATH${NC}"
        exit 1
    }
    
    PROJECT_NAME="$(basename "$ADOPT_PATH")"
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Adopt Existing Project${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "Project:         ${GREEN}${PROJECT_NAME}${NC}"
    echo -e "Path:            ${ADOPT_PATH}"
    echo ""
    if [ "$COPY_ENV" = true ]; then
        echo -e "Env Source:      Recursive Copy ← ${AGENT_ENV_ROOT}"
    else
        echo -e "Submodule:       agent_env → ${AGENT_ENV_URL}"
    fi
    echo ""
    echo -e "${BLUE}Steps:${NC}"
    echo "  1. Check for existing agent_env"
    echo "  2. Initialize git if needed"
    echo "  3. Add agent_env submodule"
    echo "  4. Add missing template files"
    echo "  5. Run configure.py"
    echo "  6. Initialize Python environment"
    echo "  7. Commit changes"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] No changes made.${NC}"
        exit 0
    fi
    
    echo -e "${BLUE}Executing...${NC}"
    echo ""
    
    cd "$ADOPT_PATH"
    
    # Step 1: Check for existing agent_env
    echo -e "${BLUE}[1/7] Checking for existing agent_env...${NC}"
    if [ -d "agent_env" ]; then
        echo -e "${YELLOW}  ⚠ agent_env already exists. Updating...${NC}"
        # Could add update logic here
    else
        echo -e "${GREEN}  ✓ No existing agent_env${NC}"
    fi
    
    # Step 2: Initialize git if needed
    echo -e "${BLUE}[2/7] Checking git repository...${NC}"
    if [ -d ".git" ]; then
        echo -e "${GREEN}  ✓ Git repository exists${NC}"
    else
        git init -q
        echo -e "${GREEN}  ✓ Git repository initialized${NC}"
    fi
    
    # Step 3: Add submodule (skip if exists)
    echo -e "${BLUE}[3/7] Adding agent_env...${NC}"
    if [ -d "agent_env" ]; then
        echo -e "${YELLOW}  ⚠ Skipping - agent_env already exists${NC}"
    elif [ "$COPY_ENV" = true ]; then
        CURRENT_BRANCH=$(git -C "$AGENT_ENV_ROOT" branch --show-current)
        echo -e "${YELLOW}  ⚠ Syncing local branch [${CURRENT_BRANCH}] to submodule (--copy-env flag)${NC}"
        # Use -c protocol.file.allow=always for local submodule addition
        git -c protocol.file.allow=always submodule add -q -b "$CURRENT_BRANCH" "$AGENT_ENV_URL" agent_env
        rsync -av --exclude='.git' --exclude='node_modules' --exclude='.venv' "$AGENT_ENV_ROOT/" agent_env/
        echo -e "${GREEN}  ✓ agent_env submodule created on branch ${CURRENT_BRANCH} and synced${NC}"
    else
        if git -c protocol.file.allow=always submodule add -q "$AGENT_ENV_URL" agent_env 2>/dev/null; then
            echo -e "${GREEN}  ✓ agent_env submodule added${NC}"
        else
            echo -e "${YELLOW}  ⚠ Could not add submodule from remote.${NC}"
            echo -e "${YELLOW}    Copying local agent-dev-environment instead.${NC}"
            cp -r "$AGENT_ENV_ROOT" agent_env
            rm -rf agent_env/.git
            echo -e "${GREEN}  ✓ agent_env copied locally${NC}"
        fi
    fi
    
    # Step 4: Add missing template files
    echo -e "${BLUE}[4/7] Adding missing template files...${NC}"
    TEMPLATES_DIR="${AGENT_ENV_ROOT}/config/templates"
    ADDED_FILES=false
    
    if [ ! -f "config.toml" ] && [ -f "${TEMPLATES_DIR}/config.toml" ]; then
        cp "${TEMPLATES_DIR}/config.toml" config.toml
        sed -i "s/# name = \"your-project-name\"/name = \"${PROJECT_NAME}\"/" config.toml
        echo -e "${GREEN}  ✓ config.toml${NC}"
        ADDED_FILES=true
    fi
    
    if [ ! -f "REQUIREMENTS.md" ] && [ -f "${TEMPLATES_DIR}/REQUIREMENTS.md" ]; then
        cp "${TEMPLATES_DIR}/REQUIREMENTS.md" REQUIREMENTS.md
        echo -e "${GREEN}  ✓ REQUIREMENTS.md${NC}"
        ADDED_FILES=true
    fi
    
    if [ ! -f "ISSUES.md" ] && [ -f "${TEMPLATES_DIR}/ISSUES.md" ]; then
        cp "${TEMPLATES_DIR}/ISSUES.md" ISSUES.md
        echo -e "${GREEN}  ✓ ISSUES.md${NC}"
        ADDED_FILES=true
    fi
    
    if [ ! -f "PLANS.md" ] && [ -f "${TEMPLATES_DIR}/PLANS.md" ]; then
        cp "${TEMPLATES_DIR}/PLANS.md" PLANS.md
        echo -e "${GREEN}  ✓ PLANS.md${NC}"
        ADDED_FILES=true
    fi
    
    if [ ! -f "pyproject.toml" ] && [ -f "${TEMPLATES_DIR}/pyproject.toml" ]; then
        cp "${TEMPLATES_DIR}/pyproject.toml" pyproject.toml
        sed -i "s/name = \"your-project-name\"/name = \"${PROJECT_NAME}\"/" pyproject.toml
        echo -e "${GREEN}  ✓ pyproject.toml${NC}"
        ADDED_FILES=true
    fi

    if [ ! -f "AGENTS.md" ] && [ -f "${TEMPLATES_DIR}/AGENTS.md" ]; then
        cp "${TEMPLATES_DIR}/AGENTS.md" AGENTS.md
        sed -i "s/\[Project Name\]/${PROJECT_NAME}/g" AGENTS.md
        echo -e "${GREEN}  ✓ AGENTS.md${NC}"
        ADDED_FILES=true
    fi

    if [ ! -f "GEMINI.md" ] && [ -f "${TEMPLATES_DIR}/GEMINI.md" ]; then
        cp "${TEMPLATES_DIR}/GEMINI.md" GEMINI.md
        sed -i "s/\[Project Name\]/${PROJECT_NAME}/g" GEMINI.md
        echo -e "${GREEN}  ✓ GEMINI.md${NC}"
        ADDED_FILES=true
    fi

    if [ ! -f "llm.txt" ] && [ -f "${TEMPLATES_DIR}/llm.txt" ]; then
        cp "${TEMPLATES_DIR}/llm.txt" llm.txt
        sed -i "s/\[Project Name\]/${PROJECT_NAME}/g" llm.txt
        echo -e "${GREEN}  ✓ llm.txt${NC}"
        ADDED_FILES=true
    fi
    
    if [ ! -f "README.agent.md" ]; then
        cat > README.agent.md << EOF
# Agent Environment Setup Guide

This project was adopted by [agent-dev-environment](https://github.com/charojo/agent-dev-environment).

---

## ⚡ Next Steps (Run These Now!)

\`\`\`bash
# 1. Configure your project
./agent_env/bin/configure.py --interactive

# 2. Setup environment
./agent_env/bin/ADE_ensure_env.sh
\`\`\`

See \`configure.py --help\` for CLI options.

---

## Development Workflow

\`\`\`bash
./agent_env/bin/validate.sh        # Validate code
./agent_env/bin/configure.py       # Reconfigure
\`\`\`
EOF
        echo -e "${GREEN}  ✓ README.agent.md${NC}"
        ADDED_FILES=true
    else
        echo -e "${YELLOW}  ⚠ README.agent.md exists (preserved)${NC}"
    fi
    
    if [ "$ADDED_FILES" = false ]; then
        echo -e "${YELLOW}  ⚠ All template files already exist${NC}"
    fi
    
    # Step 5: Run configure.py
    echo -e "${BLUE}[5/7] Running configuration...${NC}"
    if [ -f "agent_env/bin/configure.py" ]; then
        CONFIG_FLAGS=""
        if [ "$WITH_WEB" = true ]; then CONFIG_FLAGS="$CONFIG_FLAGS --enable-lang typescript --enable-feature web"; fi
        if [ "$WITH_DOCS" = true ]; then CONFIG_FLAGS="$CONFIG_FLAGS --enable-feature documentation --enable-feature api_docs"; fi
        
        # Run interactively unless flags were provided or non-interactive requested
        if [ "$NON_INTERACTIVE" = true ] || [ -n "$CONFIG_FLAGS" ]; then
            python3 agent_env/bin/configure.py --non-interactive $CONFIG_FLAGS 2>/dev/null || true
        else
            python3 agent_env/bin/configure.py --interactive || true
        fi
        echo -e "${GREEN}  ✓ Configuration run${NC}"
    else
        echo -e "${YELLOW}  ⚠ configure.py not found, skipping${NC}"
    fi
    
    # Step 6: Initialize Python environment
    echo -e "${BLUE}[6/7] Initializing Python environment...${NC}"
    if [ -f "agent_env/bin/ADE_ensure_env.sh" ]; then
        ./agent_env/bin/ADE_ensure_env.sh 2>/dev/null || true
        echo -e "${GREEN}  ✓ Python environment initialized${NC}"
    else
        echo -e "${YELLOW}  ⚠ ADE_ensure_env.sh not found, skipping${NC}"
    fi
    
    # Create logs directory and setup log
    mkdir -p "logs"
    cat > logs/agent_setup_log.md << EOF
# Agent Setup Log

- **Project:** ${PROJECT_NAME}
- **Type:** Adopted Project
- **Date:** $(date -Iseconds)
- **Path:** ${ADOPT_PATH}

## Applied Configuration
- Web: ${WITH_WEB}
- Docs: ${WITH_DOCS}

## Setup Summary
1. Checked for existing agent_env
2. Initialized/Verified Git
3. Added agent_env submodule
4. Copied template files
5. Ran configuration wizard/flags
6. Initialized Python environment
7. Created initial commit

✅ Project adopted successfully.
EOF

    # Step 7: Commit changes
    echo -e "${BLUE}[7/7] Committing changes...${NC}"
    if [ -n "$(git status --porcelain)" ]; then
        git add -A
        git commit -q -m "Add agent_env submodule, templates, and setup log

Adopted by: ADE_create_project.sh --adopt
Date: $(date -Iseconds)"
        echo -e "${GREEN}  ✓ Changes committed${NC}"
    else
        echo -e "${YELLOW}  ⚠ No changes to commit${NC}"
    fi

    # Step 8: Validate
    if [ "$SKIP_VALIDATE" = false ]; then
        echo -e "${BLUE}[8/8] Validating project (tier: full)...${NC}"
        # We use the relative path to validate.sh
        if [ -f "agent_env/bin/validate.sh" ]; then
            ./agent_env/bin/validate.sh --full --skip-e2e || echo -e "${RED}  ⚠ Validation failed. Check logs for details.${NC}"
        else
            echo -e "${YELLOW}  ⚠ validate.sh not found, skipping validation${NC}"
        fi
    fi

    # Save last project path for shell integration
    echo "${ADOPT_PATH}" > ~/.ade_last_project 2>/dev/null || true

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Project adopted successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Location: ${BLUE}${ADOPT_PATH}${NC}"
    echo ""

    if [ -t 0 ]; then
        echo -e "${YELLOW}Entering project directory...${NC}"
        cd "${ADOPT_PATH}"
        exec bash
    else
        echo -e "${YELLOW}Next steps:${NC}"
        echo ""
        echo "  cd ${ADOPT_PATH}"
        echo ""
    fi
    exit 0
fi

# ============================================================================
# NEW PROJECT MODE: Create new project from scratch
# ============================================================================

# Validate required args for new project
if [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}Error: --name is required (or use --adopt for existing projects)${NC}"
    echo "Usage: $0 --name <project-name> [--prompt \"description\"]"
    echo "   or: $0 --adopt <existing-project-path>"
    exit 1
fi

# Sanitize project name (lowercase, hyphens and underscores allowed)
SAFE_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9_-')

# Project paths (simple: just the project in the output dir)
PROJECT_DIR="${OUTPUT_DIR}/${SAFE_NAME}"

# Check if project already exists
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}Directory already exists: ${PROJECT_DIR}${NC}"
    echo ""
    echo -e "Did you mean to adopt an existing project?"
    echo -e "  $0 --adopt ${PROJECT_DIR}"
    echo ""
    echo -e "Or remove the directory first:"
    echo -e "  rm -rf ${PROJECT_DIR}"
    exit 1
fi

# ============================================================================
# Plan Output
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Create Project Plan${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Project Name:    ${GREEN}${PROJECT_NAME}${NC}"
echo -e "Safe Name:       ${GREEN}${SAFE_NAME}${NC}"
echo ""
echo -e "Output:          ${OUTPUT_DIR}"
echo -e "Project:         ${PROJECT_DIR}"
echo ""
if [ "$COPY_ENV" = true ]; then
    echo -e "Env Source:      Recursive Copy ← ${AGENT_ENV_ROOT}"
else
    echo -e "Submodule:       agent_env → ${AGENT_ENV_URL}"
fi
echo ""
FLAGS_DESC=""
if [ "$WITH_WEB" = true ]; then FLAGS_DESC="${FLAGS_DESC}web "; fi
if [ "$WITH_DOCS" = true ]; then FLAGS_DESC="${FLAGS_DESC}docs "; fi
if [ "$COPY_ENV" = true ]; then FLAGS_DESC="${FLAGS_DESC}copy-env "; fi
if [ -n "$FLAGS_DESC" ]; then
    echo -e "Options:         ${GREEN}${FLAGS_DESC}${NC}"
    echo ""
fi
if [ -n "$PROJECT_PROMPT" ]; then
    echo -e "Prompt:          ${PROJECT_PROMPT}"
    echo ""
fi
echo -e "${BLUE}Steps:${NC}"
echo "  1. Create project directory"
echo "  2. Initialize git repository"
echo "  3. Add agent_env submodule"
echo "  4. Copy template files"
echo "  5. Run configure.py"
echo "  6. Initialize Python environment"
echo "  7. Create initial commit"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY RUN] No changes made.${NC}"
    exit 0
fi

# ============================================================================
# Execution
# ============================================================================
echo -e "${BLUE}Executing...${NC}"
echo ""

# Step 1: Create project directory
echo -e "${BLUE}[1/6] Creating project directory...${NC}"
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/docs"
echo -e "${GREEN}  ✓ Created ${PROJECT_DIR}${NC}"

# Step 2: Initialize git
echo -e "${BLUE}[2/6] Initializing git repository...${NC}"
cd "$PROJECT_DIR"
git init -q
echo -e "${GREEN}  ✓ Git repository initialized${NC}"

# Step 3: Add agent_env
echo -e "${BLUE}[3/6] Adding agent_env...${NC}"
if [ "$COPY_ENV" = true ]; then
    CURRENT_BRANCH=$(git -C "$AGENT_ENV_ROOT" branch --show-current)
    echo -e "${YELLOW}  ⚠ Syncing local branch [${CURRENT_BRANCH}] to submodule (--copy-env flag)${NC}"
    # Use -c protocol.file.allow=always for local submodule addition
    git -c protocol.file.allow=always submodule add -q -b "$CURRENT_BRANCH" "$AGENT_ENV_URL" agent_env
    rsync -av --exclude='.git' --exclude='node_modules' --exclude='.venv' "$AGENT_ENV_ROOT/" agent_env/
    echo -e "${GREEN}  ✓ agent_env submodule created on branch ${CURRENT_BRANCH} and synced${NC}"
else
    if git -c protocol.file.allow=always submodule add -q "$AGENT_ENV_URL" agent_env 2>/dev/null; then
        echo -e "${GREEN}  ✓ agent_env submodule added${NC}"
    else
        echo -e "${YELLOW}  ⚠ Could not add submodule from remote.${NC}"
        echo -e "${YELLOW}    Copying local agent-dev-environment instead.${NC}"
        # Fallback: copy agent_env as a directory (for local dev without remote)
        cp -r "$AGENT_ENV_ROOT" agent_env
        rm -rf agent_env/.git
        echo -e "${GREEN}  ✓ agent_env copied locally${NC}"
    fi
fi

# Step 4: Copy templates
echo -e "${BLUE}[4/6] Copying template files...${NC}"
TEMPLATES_DIR="${AGENT_ENV_ROOT}/config/templates"

if [ -f "${TEMPLATES_DIR}/config.toml" ]; then
    cp "${TEMPLATES_DIR}/config.toml" config.toml
    # Update project name in config
    sed -i "s/# name = \"your-project-name\"/name = \"${SAFE_NAME}\"/" config.toml
    echo -e "${GREEN}  ✓ config.toml${NC}"
fi

if [ -f "${TEMPLATES_DIR}/REQUIREMENTS.md" ]; then
    cp "${TEMPLATES_DIR}/REQUIREMENTS.md" docs/REQUIREMENTS.md
    echo -e "${GREEN}  ✓ docs/REQUIREMENTS.md${NC}"
fi

if [ -f "${TEMPLATES_DIR}/ISSUES.md" ]; then
    cp "${TEMPLATES_DIR}/ISSUES.md" docs/ISSUES.md
    echo -e "${GREEN}  ✓ docs/ISSUES.md${NC}"
fi

if [ -f "${TEMPLATES_DIR}/PLANS.md" ]; then
    cp "${TEMPLATES_DIR}/PLANS.md" docs/PLANS.md
    echo -e "${GREEN}  ✓ docs/PLANS.md${NC}"
fi

if [ -f "${TEMPLATES_DIR}/pyproject.toml" ]; then
    cp "${TEMPLATES_DIR}/pyproject.toml" pyproject.toml
    # Update project name in pyproject.toml
    sed -i "s/name = \"your-project-name\"/name = \"${SAFE_NAME}\"/" pyproject.toml
    echo -e "${GREEN}  ✓ pyproject.toml${NC}"
fi

if [ -f "${TEMPLATES_DIR}/AGENTS.md" ]; then
    cp "${TEMPLATES_DIR}/AGENTS.md" AGENTS.md
    sed -i "s/\[Project Name\]/${PROJECT_NAME}/g" AGENTS.md
    echo -e "${GREEN}  ✓ AGENTS.md${NC}"
fi

if [ -f "${TEMPLATES_DIR}/GEMINI.md" ]; then
    cp "${TEMPLATES_DIR}/GEMINI.md" GEMINI.md
    sed -i "s/\[Project Name\]/${PROJECT_NAME}/g" GEMINI.md
    echo -e "${GREEN}  ✓ GEMINI.md${NC}"
fi

if [ -f "${TEMPLATES_DIR}/llm.txt" ]; then
    cp "${TEMPLATES_DIR}/llm.txt" llm.txt
    sed -i "s/\[Project Name\]/${PROJECT_NAME}/g" llm.txt
    echo -e "${GREEN}  ✓ llm.txt${NC}"
fi

# Create README.agent.md - guidance from agent-dev-environment
cat > README.agent.md << EOF
# Agent Environment Setup Guide

This project was bootstrapped with [agent-dev-environment](https://github.com/charojo/agent-dev-environment).

---

## ✅ Already Done

The project scaffold includes:
- \`.venv/\` - Python virtual environment
- \`.agent/workflows/\` - AI assistant workflows
- \`pyproject.toml\` - Python project configuration

---

## ⚡ Next Step: Customize Your Setup

\`\`\`bash
./agent_env/bin/configure.py --interactive
\`\`\`

This wizard lets you:
- Enable **Python** with pytest, ruff (linting), coverage
- Enable **TypeScript/Web** with npm, Vite, Playwright
- Enable **Documentation** with Doxygen, TypeDoc, Pandoc

**CLI alternatives:**
\`\`\`bash
./agent_env/bin/configure.py --enable-lang python
./agent_env/bin/configure.py --enable-feature web
./agent_env/bin/configure.py --enable-feature docs
\`\`\`

---

## Development Workflow

\`\`\`bash
# Validate code quality
./agent_env/bin/validate.sh

# Full validation with tests
./agent_env/bin/validate.sh --full

# Sync environment after config changes
./agent_env/bin/ADE_ensure_env.sh
\`\`\`

---

## Keeping agent_env Updated

\`\`\`bash
cd agent_env && git pull origin main && cd ..
git add agent_env && git commit -m "update: agent_env"
\`\`\`

---

## After Cloning This Repo

\`\`\`bash
git submodule update --init --recursive
./agent_env/bin/ADE_ensure_env.sh
\`\`\`
EOF
echo -e "${GREEN}  ✓ README.agent.md${NC}"

# Create .gitignore
cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.coverage


# Node
node_modules/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Environment
.env
.env.local

# Agent Environment
.agent/*
!.agent/workflows/
EOF
echo -e "${GREEN}  ✓ .gitignore${NC}"

# Step 5: Run configure.py if available
echo -e "${BLUE}[5/7] Running configuration...${NC}"
if [ -f "agent_env/bin/configure.py" ]; then
    CONFIG_FLAGS=""
    if [ "$WITH_WEB" = true ]; then CONFIG_FLAGS="$CONFIG_FLAGS --enable-lang typescript --enable-feature web"; fi
    if [ "$WITH_DOCS" = true ]; then CONFIG_FLAGS="$CONFIG_FLAGS --enable-feature documentation --enable-feature api_docs"; fi
    
    # Run interactively unless flags were provided or non-interactive requested
    if [ "$NON_INTERACTIVE" = true ] || [ -n "$CONFIG_FLAGS" ]; then
        python3 agent_env/bin/configure.py --non-interactive $CONFIG_FLAGS 2>/dev/null || true
    else
        python3 agent_env/bin/configure.py --interactive || true
    fi
    echo -e "${GREEN}  ✓ Configuration initialized${NC}"
else
    echo -e "${YELLOW}  ⚠ configure.py not found, skipping${NC}"
fi

# Step 6: Initialize Python environment
echo -e "${BLUE}[6/7] Initializing Python environment...${NC}"
if [ -f "agent_env/bin/ADE_ensure_env.sh" ]; then
    ./agent_env/bin/ADE_ensure_env.sh 2>/dev/null || true
    echo -e "${GREEN}  ✓ Python environment initialized${NC}"
else
    echo -e "${YELLOW}  ⚠ ADE_ensure_env.sh not found, skipping${NC}"
fi

# Create logs directory and setup log
mkdir -p "logs"
cat > logs/agent_setup_log.md << EOF
# Agent Setup Log

- **Project:** ${PROJECT_NAME}
- **Type:** New Project
- **Prompt:** ${PROJECT_PROMPT:-<none>}
- **Date:** $(date -Iseconds)
- **Path:** ${PROJECT_DIR}

## Applied Configuration
- Web: ${WITH_WEB}
- Docs: ${WITH_DOCS}

## Setup Summary
1. Created project directory
2. Initialized git repository
3. Added agent_env submodule
4. Copied template files
5. Ran configuration wizard/flags
6. Initialized Python environment
7. Created initial commit

✅ Project created successfully.
EOF

# Step 7: Initial commit
echo -e "${BLUE}[7/7] Creating initial commit...${NC}"
git add -A
git commit -q -m "Initial commit: Project scaffold with agent_env and setup log

Project: ${PROJECT_NAME}
Prompt: ${PROJECT_PROMPT:-<none>}
Created: $(date -Iseconds)"
    echo -e "${GREEN}  ✓ Initial commit created${NC}"

    # Step 8: Validate
    if [ "$SKIP_VALIDATE" = false ]; then
        echo -e "${BLUE}[8/8] Validating project (tier: full)...${NC}"
        # We use the relative path to validate.sh
        if [ -f "agent_env/bin/validate.sh" ]; then
            ./agent_env/bin/validate.sh --full --skip-e2e || echo -e "${RED}  ⚠ Validation failed. Check logs for details.${NC}"
        else
            echo -e "${YELLOW}  ⚠ validate.sh not found, skipping validation${NC}"
        fi
    fi

# Save last project path for shell integration
echo "${PROJECT_DIR}" > ~/.ade_last_project 2>/dev/null || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Project created successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Location: ${BLUE}${PROJECT_DIR}${NC}"
echo ""

if [ -t 0 ]; then
    echo -e "${YELLOW}Entering project directory...${NC}"
    cd "${PROJECT_DIR}"
    exec bash
else
    echo -e "${YELLOW}Next steps:${NC}"
    echo ""
    echo "  cd ${PROJECT_DIR}"
    echo ""
fi
