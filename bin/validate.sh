#!/bin/bash
## @DOC
# ### Validation Workflow
# This script orchestrates the project's validation process across multiple tiers.
# It handles environment checks, auto-formatting, unit tests, and E2E validation.
#
# **Workflow Tiers:**
# - **Fast**: Change-based testing (testmon), skipping linting and E2E.
# - **Medium**: File-level testing with auto-formatting enabled.
# - **Full**: Comprehensive validation including E2E and coverage reporting.
# - **Exhaustive**: Maximum coverage, mutation testing, and parallel execution.
#
# See architecture: [validate_workflow.svg](../docs/assets/diagrams/validate_workflow.svg) <!-- @diagram: validate_workflow.svg -->

set -eo pipefail


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"


# Store the project root directory
if [ -d "agent_env" ]; then
    ROOT_DIR="$(pwd)"
    AGENT_DIR="agent_env"
elif [ -d ".agent" ]; then
    ROOT_DIR="$(pwd)"
    AGENT_DIR=".agent"
elif [[ "$(basename "$(dirname "$0")")" == "bin" ]]; then
    ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    # Try to deduce AGENT_DIR
    if [ -d "$ROOT_DIR/agent_env" ]; then
        AGENT_DIR="agent_env"
    elif [ -d "$ROOT_DIR/.agent" ]; then
        AGENT_DIR=".agent"
    fi
else
    ROOT_DIR="$(pwd)"
fi
cd "$ROOT_DIR"


# Ensure Environment
# Check for First Run or explicit configuration
if [[ "$1" != "--help" && "$1" != "-h" ]]; then
    # If AGENT_DIR is empty, it's likely the main repo itself.
    # We check for .agent_setup_complete in current dir as fallback.
    SETUP_COMPLETE_FILE="${AGENT_DIR:+$AGENT_DIR/}.agent_setup_complete"
    
    if [[ ! -f "$SETUP_COMPLETE_FILE" ]] || [[ "$1" == "--configure" ]]; then
        if [ -f "$SCRIPT_DIR/configure.py" ]; then
            echo -e "${YELLOW}Running initial configuration...${NC}"
            uv run python "$SCRIPT_DIR/configure.py" --interactive
        fi
    fi
fi

if [ -f "./agent_env/bin/ADE_ensure_env.sh" ]; then
    ./agent_env/bin/ADE_ensure_env.sh
elif [ -f "./.agent/bin/ADE_ensure_env.sh" ]; then
    ./.agent/bin/ADE_ensure_env.sh
elif [ -f "./bin/ADE_ensure_env.sh" ]; then
    ./bin/ADE_ensure_env.sh
else
    # Fallback or error if not found
    echo "Error: ADE_ensure_env.sh not found."
    exit 1
fi

# ============================================
# Configuration
# ============================================
TIER=""          # fast | medium | full | exhaustive
INCLUDE_LIVE=false   # Include $ tests (API calls)
INCLUDE_E2E=false    # E2E tests
SKIP_FIX=false       # Skip auto-formatting
PARALLEL=false       # Parallel test execution
VERBOSE=false        # Detailed output
E2E_FILTER=""        # Filter for specific E2E test
INITIALIZING=false   # Internal flag for missing coverage
PYTEST_SELECTION=""  # Centralized selection args
RUN_CONFIG_TESTS=false # Run configuration validation tests
UPDATE_SNAPSHOTS=false # Flag to update E2E snapshots

# Colors
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

# ============================================
# Utilities
# ============================================

## @fn strip_ansi
# Removes ANSI escape codes from stdin.
strip_ansi() {
    sed 's/\x1b\[[0-9;]*[a-zA-Z]//g'
}

## @fn log_msg
# Logs a message to stdout (with color) and to the log file (without color).
# Usage: log_msg "${BLUE}Message${NC}"
log_msg() {
    local msg="$1"
    echo -e "$msg"
    echo -e "$msg" | strip_ansi >> "$LOG_FILE"
}

# ============================================
# Help
# ============================================
## @fn show_help
# Displays usage information and tier details.
show_help() {
    cat <<EOF
${BLUE}Validation Suite${NC}

${YELLOW}Usage:${NC} ./bin/validate.sh [tier] [options]

${YELLOW}Tiers:${NC}
  --${GREEN}screen${NC} System Health + Crash Smoke Test (15s)
  --${GREEN}fast${NC}   Screen + Unit tests for CHANGED code + Auto-fix (40s)
  --${BLUE}frontend${NC} Auto-fix + All Frontend Unit Tests (20s)
  --${YELLOW}e2e${NC}    Screen + Auto-fix + Full E2E Suite (35s)
  --${BLUE}full${NC}   E2E + All Unit Tests + Coverage (75s)
  --${RED}exhaustive${NC} Full + Parallel Execution + Mutation Testing (5m)

${YELLOW}Options:${NC}
  --live         Include \$ tests (Gemini API calls)
  --e2e-select   Filter specific E2E test by name or number
  --skip-e2e     Skip E2E tests (useful for debugging)
  --update-snapshots Update E2E visual snapshots
  --no-fix       Skip auto-formatting
  --parallel     Parallelize tests (auto in exhaustive)
  --configure    Run interactive configuration wizard
  --config-tests Run configuration validation tests (RESETS REPO)
  --verbose, -v  Detailed output
  --help, -h     Show this help

${YELLOW}Examples:${NC}
  ./bin/validate.sh --fast         # Fast: quick changeset check
  ./bin/validate.sh --full         # Full: pre-commit validation
  ./bin/validate.sh --exhaustive   # Exhaustive: pre-merge
  ./bin/validate.sh --full --live  # Full + API tests

${YELLOW}Notes:${NC}
  - \$ tests are marked "live" (Gemini API calls)
  - Fast tier skips unchanged code (testmon)
  - Use --full for CI/pre-merge validation
EOF
}

# ============================================
# Argument Parsing
# ============================================
START_ARGS=$#
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h) show_help; exit 0 ;;
        --full) TIER="full"; shift ;;
        --exhaustive) TIER="exhaustive"; shift ;;
        --fast) TIER="fast"; shift ;;
        --screen) TIER="screen"; shift ;;
        --frontend) TIER="frontend"; shift ;;
        --live) INCLUDE_LIVE=true; shift ;;
        --debug) VERBOSE=true; PARALLEL=false; shift ;;
        --e2e) TIER="e2e"; shift ;;
        --e2e-select)
            E2E_FILTER="$2"
            shift # past argument
            shift # past value
            ;;
        --configure) 
             # Handled early, but consume arg
             shift
             ;;
        --config-tests) RUN_CONFIG_TESTS=true; shift ;;
        --no-fix) SKIP_FIX=true; shift ;;
        --parallel) PARALLEL=true; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        --skip-e2e) SKIP_E2E_FLAG=true; shift ;;
        --update-snapshots) UPDATE_SNAPSHOTS=true; shift ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; show_help; exit 1 ;;
    esac
done
    
if [ $START_ARGS -eq 0 ]; then
    show_help
    exit 0
fi

# Configuration Tests Warning
if [ "$RUN_CONFIG_TESTS" = true ]; then
    echo -e "${RED}WARNING: --config-tests will RESET your repository to a pristine state.${NC}"
    echo -e "${YELLOW}This includes stashing your current work and cleaning the environment multiple times.${NC}"
    read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Auto-enable features based on tier
case "$TIER" in
    fast)
        # Fast: change-based tests with auto-fix
        TIER="fast"
        ;;
    screen)
        # Smoke only: skip everything except Phase 0/0.5
        INCLUDE_E2E=false # Full E2E suite skipped, but Phase 0.5 handles smoke
        ;;
    frontend)
        # Frontend: auto-fix, frontend tests only
        INCLUDE_E2E=false
        ;;
    e2e)
        # E2E: auto-fix, E2E tests only
        INCLUDE_E2E=true
        ;;
    full)
        # Complete: auto-fix, E2E, all tests
        INCLUDE_E2E=true
        ;;
    exhaustive)
        # Maximum: auto-fix, E2E, parallel
        INCLUDE_E2E=true
        PARALLEL=true
        ;;
esac

# Override E2E if explicitly skipped
if [ "$SKIP_E2E_FLAG" = true ]; then
    INCLUDE_E2E=false
fi

# ============================================
# Setup
# ============================================

# ============================================
# Setup
# ============================================
mkdir -p logs
# Preserve .testmondata if it exists
# Preserve .testmondata and .coverage if they exist
find logs/ -maxdepth 1 -type f ! -name ".testmondata" ! -name ".coverage" ! -name ".gitkeep" -delete
LOG_FILE="logs/validation_summary_log.md"
export TESTMON_DATAFILE="logs/.testmondata"
export COVERAGE_FILE="logs/.coverage"

# Timing
TOTAL_START=$(date +%s)
PHASE0_DURATION=0
FIX_DURATION=0
BACKEND_DURATION=0
FRONTEND_DURATION=0
E2E_DURATION=0
STATIC_DURATION=0

# Results
BACKEND_PASSED=0
BACKEND_FAILED=0
BACKEND_SKIPPED=0
BACKEND_DESELECTED=0
FRONTEND_PASSED=0
FRONTEND_FAILED=0
E2E_PASSED=0
E2E_FAILED=0

# Check for initial run or clean environment BEFORE tier specific logic
if [[ ! -f "$TESTMON_DATAFILE" ]] || [[ ! -f "$COVERAGE_FILE" ]]; then
    INITIALIZING=true
fi

# Initialize Log File with Markdown Header
echo "# Validation Report" > "$LOG_FILE"
log_msg "Date: $(date)"
log_msg "Tier: **${TIER}**"
log_msg ""

# Echo to stdout as well (formatted for terminal)
echo -e "${BLUE}Validation Suite${NC} - Tier: ${TIER}"

# Centralized Test Selection Logic
# Load Configuration via config_utils.py
CONFIG_UTILS=""
if [ -f "agent_env/bin/ADE_config_utils.py" ]; then
    CONFIG_UTILS="agent_env/bin/ADE_config_utils.py"
elif [ -f ".agent/bin/ADE_config_utils.py" ]; then
    CONFIG_UTILS=".agent/bin/ADE_config_utils.py"
fi

# Load Configuration via ADE_config_utils.py
PYTEST_SELECTION=""
if [ -n "$CONFIG_UTILS" ]; then
    # We use python to get the marker string e.g. -m "not processing"
    PYTEST_SELECTION="$PYTEST_SELECTION $(uv run python "$CONFIG_UTILS" get-markers)"

    # Also check if python is enabled? If python is disabled, we shouldn't run backend tests at all.
    PYTHON_ENABLED=$(uv run python "$CONFIG_UTILS" get languages.python.enabled)
    JS_ENABLED=$(uv run python "$CONFIG_UTILS" get languages.typescript.enabled)
fi

# Fallback if config_utils missing or returns empty (assume enabled)
if [ -z "$PYTHON_ENABLED" ]; then PYTHON_ENABLED="true"; fi
if [ -z "$JS_ENABLED" ]; then JS_ENABLED="true"; fi

if [ "$INITIALIZING" = true ]; then
    log_msg "${YELLOW}Initial run or clean environment detected: This may take 1-3 minutes...${NC}"
    log_msg "${BLUE}Note: We are building the test/coverage metadata for the first time.${NC}"
    log_msg ""
    echo "> **Note:** Initial run detected. Building coverage data..." >> "$LOG_FILE"
    PYTEST_SELECTION="$PYTEST_SELECTION --testmon -v"
fi

if [[ "$TIER" == "fast" ]]; then
    # Check if tests are newer than data
    test_changes=$(find tests/ -name "*.py" -newer "$TESTMON_DATAFILE" 2>/dev/null | wc -l)
    if [[ "$test_changes" -gt 0 ]]; then
        log_msg "${YELLOW}🔄 New test files detected: Refreshing testmon database...${NC}"
        INITIALIZING=true
    else
        log_msg "Selection: LOC-change-only based testing (testmon)"
        PYTEST_SELECTION="$PYTEST_SELECTION --testmon-forceselect"
    fi

    # Always exclude E2E from non-full tiers
    PYTEST_SELECTION="$PYTEST_SELECTION -m \"not e2e\""
fi

# Parallel override
if [ "$PARALLEL" = true ]; then
    PYTEST_SELECTION="$PYTEST_SELECTION -n auto"
fi

# ============================================
# Phase 0: System Health & Compliance
# ============================================
## @fn run_system_checks
# Performs critical startup and compliance checks.
run_system_checks() {
    if [ "$TIER" = "e2e" ] || [ "$TIER" = "exhaustive" ] || [ "$TIER" = "frontend" ]; then
        return
    fi

    echo -e "${BLUE}=== Phase 0: System Health & Compliance ===${NC}"
    echo "## Phase 0: System Health & Compliance" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    log_msg "Verifying System Startup..."
    if [ -f "bin/check_startup.py" ]; then
        uv run python bin/check_startup.py 2>&1 | strip_ansi >> "$LOG_FILE"
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            log_msg "${RED}CRITICAL: System health checks failed!${NC}"
            exit 1
        fi
    fi

    log_msg "Checking CSS Compliance..."
    if [ -f "bin/check_css_compliance.py" ]; then
        uv run python bin/check_css_compliance.py 2>&1 | strip_ansi >> "$LOG_FILE"
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            log_msg "${RED}CRITICAL: CSS compliance failed!${NC}"
            exit 1
        fi
    fi
    
    local end=$(date +%s)
    PHASE0_DURATION=$((end - start))
    echo "TIMING_METRIC: Phase0=${PHASE0_DURATION}s" >> "$LOG_FILE"
}

# ============================================
# Phase 0.5: Smoke Test (Fast E2E)
# ============================================
## @fn run_smoke_test
# Runs a lightweight E2E smoke test to detect frontend crashes.
run_smoke_test() {
    if [ "$TIER" = "e2e" ] || [ "$TIER" = "exhaustive" ] || [ "$TIER" = "frontend" ]; then
        return
    fi
    
    echo -e "${BLUE}=== Phase 0.5: Smoke Test (Crash Detection) ===${NC}"
    echo "## Phase 0.5: Smoke Test" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    if [ -f "bin/run_smoke_test.sh" ]; then
        log_msg "Executing Smoke Test (Real-time output below)..."
        ./bin/run_smoke_test.sh 2>&1 | tee >(strip_ansi >> "$LOG_FILE")
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            log_msg "${RED}CRITICAL: Frontend smoke test failed! Runtime crash detected.${NC}"
            log_msg "Check logs/frontend_e2e.log and logs/backend_e2e.log for details."
            exit 1
        fi
    fi
    
    local end=$(date +%s)
    PHASE05_DURATION=$((end - start))
    echo "TIMING_METRIC: Phase0.5=${PHASE05_DURATION}s" >> "$LOG_FILE"
}


# ============================================
# Phase 1: Auto-fix (fast, full, exhaustive)
# ============================================
## @fn run_auto_fix
# Runs ruff and npm lint to automatically fix formatting and linting issues.
run_auto_fix() {
    if [ "$SKIP_FIX" = true ]; then
        echo -e "${YELLOW}Skipping auto-fix${NC}"
        return
    fi
    
    echo -e "${BLUE}=== Auto-fix ===${NC}"
    echo "## Auto-fix" >> "$LOG_FILE"
    echo "\`\`\`bash" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    log_msg "Fixing Backend..."
    uv run ruff check --fix . 2>&1 | strip_ansi >> "$LOG_FILE" || true
    uv run ruff format . 2>&1 | strip_ansi >> "$LOG_FILE" || true
    
    if [ -d "src/web" ]; then
        log_msg "Fixing Frontend..."
        cd src/web
        npm run lint -- --fix 2>&1 | strip_ansi >> "../../$LOG_FILE" || true
        cd "$ROOT_DIR"
    fi
    
    echo "\`\`\`" >> "$LOG_FILE"
    
    local end=$(date +%s)
    FIX_DURATION=$((end - start))
    echo "TIMING_METRIC: AutoFix=${FIX_DURATION}s" >> "$LOG_FILE"
}

## @fn run_backend_tests
# Executes pytest with the appropriate selection logic based on the current tier.
run_backend_tests() {
    if [ "$PYTHON_ENABLED" != "true" ]; then
        log_msg "${YELLOW}Python disabled in config. Skipping backend tests.${NC}"
        return
    fi

    if [ "$TIER" = "screen" ] || [ "$TIER" = "e2e" ] || [ "$TIER" = "exhaustive" ] || [ "$TIER" = "frontend" ]; then
        log_msg "${YELLOW}Skipping backend (tier: $TIER)${NC}"
        return
    fi
    
    log_msg ""
    echo -e "${BLUE}=== Backend Tests (Python) ===${NC}"
    echo "## Backend Tests (Python)" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    local pytest_args="-v --timeout=300"
    
    # Add verbosity
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -vv -s"
    fi

    # Selection already computed upfront
    # CRITICAL: Ignore tests/validation and environment submodules/directories
    # to prevent double-execution, deadlocks, and infinite recursion in projects.
    # --ignore=tests/validation 
    pytest_args="$pytest_args $PYTEST_SELECTION --ignore=.agent --ignore=agent_env"
    
    # Add marker for live tests
    if [ "$INCLUDE_LIVE" = false ]; then
        pytest_args="$pytest_args -m \"not live\""
    fi
    
    # Add coverage for full/exhaustive
    if [ "$TIER" = "full" ] || [ "$TIER" = "exhaustive" ]; then
        if [ -d "src" ]; then
            pytest_args="$pytest_args --cov=src --cov-report=term-missing"
        fi
    fi
           
    # Run tests with streaming output
    local output_tmp="logs/backend_output.tmp"
    log_msg "Command: uv run pytest $pytest_args"
    echo "\`\`\`bash" >> "$LOG_FILE"
    echo "Command: uv run pytest $pytest_args" >> "$LOG_FILE"
    echo "----------------------------------------" >> "$LOG_FILE"
    
    # Execute: Raw -> Console (via tee), Raw -> Temp File
    eval "uv run pytest $pytest_args 2>&1" | tee "$output_tmp"
    local exit_code=${PIPESTATUS[0]}
    
    # Pytest returns 5 if no tests are collected. We treat this as success for validation.
    if [ $exit_code -eq 5 ]; then
        exit_code=0
    fi
    
    # Append Stripped -> Log File
    cat "$output_tmp" | strip_ansi >> "$LOG_FILE"
    
    # Explicitly append coverage report if we ran coverage
    if [[ "$TIER" == "full" || "$TIER" == "exhaustive" ]] && [[ -f "$COVERAGE_FILE" ]]; then
        echo "" >> "$LOG_FILE"
        echo "Explicit Coverage Report:" >> "$LOG_FILE"
        uv run coverage report --data-file="$COVERAGE_FILE" | strip_ansi >> "$LOG_FILE"
    fi

    echo "----------------------------------------" >> "$LOG_FILE"
    echo "\`\`\`" >> "$LOG_FILE"
    log_msg "Backend unit tests completed."
    
    local output
    output=$(cat "$output_tmp")
    
    # Check if run succeeded
    if [[ "$INITIALIZING" == "true" && ! -s "$output_tmp" ]]; then
         log_msg "${RED}Initialization failed.${NC}"
    fi
    rm -f "$output_tmp"

    # Parse results - handle empty grep results
    BACKEND_PASSED=$(echo "$output" | grep -oP '\d+(?= passed)' | tail -1 || echo 0)
    BACKEND_PASSED=${BACKEND_PASSED:-0}
    BACKEND_FAILED=$(echo "$output" | grep -oP '\d+(?= failed)' | tail -1 || echo 0)
    BACKEND_FAILED=${BACKEND_FAILED:-0}
    BACKEND_SKIPPED=$(echo "$output" | grep -oP '\d+(?= skipped)' | tail -1 || echo 0)
    BACKEND_SKIPPED=${BACKEND_SKIPPED:-0}
    BACKEND_DESELECTED=$(echo "$output" | grep -oP '\d+(?= deselected)' | tail -1 || echo 0)
    BACKEND_DESELECTED=${BACKEND_DESELECTED:-0}
    
    local end=$(date +%s)
    BACKEND_DURATION=$((end - start))
    echo "TIMING_METRIC: Backend=${BACKEND_DURATION}s" >> "$LOG_FILE"

    return $exit_code
}

# ============================================
# Phase 3: Frontend Tests
# ============================================
run_frontend_tests() {
    if [ "$JS_ENABLED" != "true" ]; then
        log_msg "${YELLOW}JavaScript disabled in config. Skipping frontend tests.${NC}"
        return
    fi
    
    if [ "$TIER" = "screen" ] || [ "$TIER" = "e2e" ] || [ "$TIER" = "exhaustive" ]; then
        log_msg "${YELLOW}Skipping frontend (tier: $TIER)${NC}"
        return
    fi
    
    if [ ! -d "src/web" ]; then
        log_msg "${YELLOW}src/web not found, skipping frontend tests.${NC}"
        return
    fi
    
    echo "## Frontend Tests" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    cd src/web
    
    # 0. Clean up any previous orphan processes
    npm run test:clean > /dev/null 2>&1 || true
    
    local vitest_args=""
    
    case "$TIER" in
        fast)
            # LOC-based selection if map exists
            echo "Selection: LOC-only"
            if [ -f ".vitest-loc-map.json" ]; then
                local loc_tests=$(node scripts/select-tests-by-loc.js 2>/dev/null | grep -v "^#" | tr '\n' ' ')
                if [ -n "$loc_tests" ]; then
                    echo "Found tests for changed LOC: $loc_tests"
                    vitest_args="$loc_tests"
                else
                    echo "No tests found, falling back to --changed"
                    vitest_args="--changed"
                fi
            else
                echo "LOC map not found, using --changed"
                vitest_args="--changed"
            fi
            ;;
        full|exhaustive)
            echo "Selection: All tests"
            if [ "$TIER" = "full" ] || [ "$TIER" = "exhaustive" ]; then
                vitest_args="--coverage"
            # Attempt to ensure coverage runs if we are full but skipping E2E
            elif [ "$TIER" = "full" ] && [ "$INCLUDE_E2E" = false ]; then
                 vitest_args="--coverage"
            fi
            ;;
        frontend)
            echo "Selection: All tests"
            # No coverage to keep it fast
            vitest_args=""
            ;;
    esac

    # Add verbosity for initial runs
    if [[ "$INITIALIZING" == "true" || "$VERBOSE" == "true" ]]; then
        vitest_args="$vitest_args --reporter=verbose"
    fi
    
    # Run tests with real-time feedback
    local output_tmp="../../logs/frontend_output.tmp"
    echo "Executing: npm run test:run -- $vitest_args"
    
    echo "\`\`\`bash" >> "../../$LOG_FILE"
    
    # Execute: Raw -> Console (via tee), Raw -> Temp File
    eval "npm run test:run -- $vitest_args 2>&1" | tee "$output_tmp"
    local exit_code=${PIPESTATUS[0]}

    # Append Stripped -> Log File
    cat "$output_tmp" | strip_ansi >> "../../$LOG_FILE"
    
    echo "\`\`\`" >> "../../$LOG_FILE"
    
    local output
    output=$(cat "$output_tmp")
    rm -f "$output_tmp"
    
    # Parse results
    FRONTEND_PASSED=$(echo "$output" | grep -oP '\d+(?= passed)' | tail -1 || echo 0)
    FRONTEND_FAILED=$(echo "$output" | grep -oP '\d+(?= failed)' | tail -1 || echo 0)
    
    cd "$ROOT_DIR"
    
    local end=$(date +%s)
    FRONTEND_DURATION=$((end - start))
    echo "TIMING_METRIC: Frontend=${FRONTEND_DURATION}s" >> "$LOG_FILE"

    return $exit_code
}

# ============================================
# Phase 4: E2E Tests
# ============================================
run_e2e_tests() {
    if [ "$UPDATE_SNAPSHOTS" = true ]; then
        export UPDATE_SNAPSHOTS=true
        INCLUDE_E2E=true
        log_msg "${YELLOW}Snapshot update mode enabled.${NC}"
    fi

    if [ "$INCLUDE_E2E" = false ]; then
        log_msg ""
        log_msg "${YELLOW}Skipping E2E tests${NC}"
        echo "> **E2E Tests Skipped**" >> "$LOG_FILE"
        return
    fi

    if [ -n "$E2E_FILTER" ]; then
        export E2E_FILTER
        log_msg "E2E Filter: $E2E_FILTER"
    fi

    if [ ! -d "src/web" ] && [ ! -d "tests/e2e" ]; then
        log_msg "${YELLOW}No E2E tests found (src/web or tests/e2e), skipping.${NC}"
        return
    fi
    if [ "$TIER" != "e2e" ] && [ "$TIER" != "full" ] && [ "$TIER" != "exhaustive" ]; then
        if [ -z "$E2E_FILTER" ]; then
            export E2E_SKIP_SMOKE=true
        fi
    fi

    echo -e "${BLUE}Starting servers and running browser tests (this may take 1-2 minutes)...${NC}"
    
    echo "## E2E Tests" >> "$LOG_FILE"
    echo "\`\`\`bash" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    local output_tmp="logs/e2e_output.tmp"
    log_msg "Command: uv run pytest -s --timeout=300 tests/validation/test_e2e_wrapper.py"
    
    # Execute: Raw -> Console (via tee), Raw -> Temp File
    eval "uv run pytest -s --timeout=300 tests/validation/test_e2e_wrapper.py 2>&1" | tee "$output_tmp"
    local exit_code=${PIPESTATUS[0]}
    
    # Append Stripped -> Log File
    cat "$output_tmp" | strip_ansi >> "$LOG_FILE"
    
    local output
    output=$(cat "$output_tmp")
    rm -f "$output_tmp"
    
    echo "\`\`\`" >> "$LOG_FILE"
    
    if [[ "$output" == *"Timed out"* ]]; then
        echo -e "${RED}E2E wrapper timed out. Check logs/backend_e2e.log and logs/frontend_e2e.log for server errors.${NC}"
        echo "> **Error:** E2E wrapper timed out." >> "$LOG_FILE"
    fi
    
    # Parse results
    E2E_PASSED=$(echo "$output" | grep -oP '\d+ passed' | grep -oP '\d+' | tail -1 || echo 0)
    E2E_FAILED=$(echo "$output" | grep -oP '\d+ failed' | grep -oP '\d+' | tail -1 || echo 0)
    
    local end=$(date +%s)
    E2E_DURATION=$((end - start))
    echo "TIMING_METRIC: E2E=${E2E_DURATION}s" >> "$LOG_FILE"

    return $exit_code
}

# ============================================
# Phase 5: Static Analysis
# ============================================
run_static_analysis() {
    if [ "$TIER" = "fast" ] || [ "$TIER" = "screen" ] || [ "$TIER" = "e2e" ] || [ "$TIER" = "frontend" ]; then
        return
    fi

    echo -e "${BLUE}=== Static Analysis & Lint Checks ===${NC}"
    echo "## Static Analysis & Lint Checks" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    # Clear old log if exists
    rm -f logs/static_analysis.log
    
    # Run all non-E2E validation tests
    # test_static_analysis.py, test_linters.py, etc.
    if [ -d "tests/validation" ]; then
        uv run pytest -q tests/validation --ignore=tests/validation/test_e2e_wrapper.py >> "$LOG_FILE" 2>&1 || true
    fi
    
    local end=$(date +%s)
    STATIC_DURATION=$((end - start))
    echo "TIMING_METRIC: Static=${STATIC_DURATION}s" >> "$LOG_FILE"
}

# ============================================
# Phase 6: Subsystems (Matrix, Tokens, etc.)
# ============================================
run_subsystems() {
    if [ "$TIER" != "full" ] && [ "$TIER" != "exhaustive" ]; then
        return
    fi

    echo -e "${BLUE}=== Subsystems (Matrix & Tokens) ===${NC}"
    echo "## Subsystems" >> "$LOG_FILE"

    # 1. Coverage Matrix
    if [ "$PYTHON_ENABLED" = "true" ] || [ "$JS_ENABLED" = "true" ]; then
        log_msg "Generating Coverage Matrix..."
        echo "### Coverage Matrix" >> "$LOG_FILE"
        echo "\`\`\`" >> "$LOG_FILE"
        node agent_env/bin/ADE_unified_matrix.js 2>&1 | strip_ansi >> "$LOG_FILE" || true
        echo "\`\`\`" >> "$LOG_FILE"
    fi

    # 2. Token Analysis
    if [ -f "logs/token_ledger.csv" ]; then
        log_msg "Analyzing Token Usage..."
        echo "### Token Analysis" >> "$LOG_FILE"
        echo "\`\`\`" >> "$LOG_FILE"
        uv run python agent_env/bin/ADE_analyze_tokens.py 2>&1 | strip_ansi >> "$LOG_FILE" || true
        echo "\`\`\`" >> "$LOG_FILE"
    fi
}

# ============================================
# Summary
# ============================================
print_summary() {
    local total_end=$(date +%s)
    local total_duration=$((total_end - TOTAL_START))
    
    log_msg ""
    echo "## Validation Summary" >> "$LOG_FILE"
    
    # Tier description
    local tier_desc
    case "$TIER" in
        fast) tier_desc="Fast (LOC-only)" ;;
        frontend) tier_desc="Frontend (unit tests)" ;;
        full) tier_desc="Full (all tests)" ;;
        exhaustive) tier_desc="Exhaustive (max coverage)" ;;
    esac
    echo "- **Tier**: $tier_desc" >> "$LOG_FILE"

    # Append detailed logs from wrappers so analyze.sh can find them
    if [ -f "logs/static_analysis.log" ]; then
        echo "" >> "$LOG_FILE" 
        echo "### Static Analysis" >> "$LOG_FILE"
        echo "\`\`\`" >> "$LOG_FILE"
        cat logs/static_analysis.log >> "$LOG_FILE"
        echo "\`\`\`" >> "$LOG_FILE"
    fi

    # Record Total Time for analyze.sh
    echo "TIMING_METRIC: Static=${STATIC_DURATION}s" >> "$LOG_FILE"
    echo "TIMING_METRIC: Total=${total_duration}s" >> "$LOG_FILE"

    # Run Analysis (LOC metrics, coverage summary, etc.)
    log_msg ""
    echo "Running Validation Analysis..."
    
    local ANALYZE_SCRIPT=""
    if [ -f "./agent_env/bin/ADE_analyze.sh" ]; then
        ANALYZE_SCRIPT="./agent_env/bin/ADE_analyze.sh"
    elif [ -f "./.agent/bin/ADE_analyze.sh" ]; then
        ANALYZE_SCRIPT="./.agent/bin/ADE_analyze.sh"
    fi

    # Show analysis in shell AND log
    # Show analysis: stdout (Markdown) -> Log File, stderr (ASCII) -> Console
    $ANALYZE_SCRIPT "$LOG_FILE" >> "$LOG_FILE"

    # Run Failure Analysis
    if [ -f "./agent_env/bin/ADE_analyze_failures.py" ]; then
        uv run python ./agent_env/bin/ADE_analyze_failures.py "$LOG_FILE" >> "$LOG_FILE"
    fi

    # Overall status
    local overall_failed=$((${BACKEND_FAILED:-0} + ${FRONTEND_FAILED:-0} + ${E2E_FAILED:-0}))
    if [ "$overall_failed" -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# ============================================
# Main Execution
# ============================================
# Fast Path for targeted E2E selection
if [ -n "$E2E_FILTER" ]; then
    log_msg "${BLUE}=== Fast Path: Targeted E2E Selection ===${NC}"
    INCLUDE_E2E=true
    run_system_checks || { echo -e "${RED}System health checks failed${NC}"; exit 1; }
    run_e2e_tests || { echo -e "${RED}E2E tests failed${NC}"; exit 1; }
    print_summary
    exit 0
fi

run_system_checks || { echo -e "${RED}System health checks failed${NC}"; exit 1; }
run_smoke_test || { echo -e "${RED}Frontend smoke test failed${NC}"; exit 1; }

# Early exit for screen tier
if [ "$TIER" = "screen" ]; then
    print_summary
    exit 0
fi

run_auto_fix || { echo -e "${RED}Auto-fix encountered issues${NC}"; exit 1; }
run_backend_tests || { echo -e "${RED}Backend tests failed${NC}"; exit 1; }
run_frontend_tests || { echo -e "${RED}Frontend tests failed${NC}"; exit 1; }
run_e2e_tests || { echo -e "${RED}E2E tests failed${NC}"; exit 1; }
run_static_analysis || { echo -e "${RED}Static analysis failed${NC}"; exit 1; }
run_subsystems || { echo -e "${RED}Subsystems failed${NC}"; exit 1; }

if [ "$RUN_CONFIG_TESTS" = true ]; then
    echo -e "${BLUE}=== Configuration Tests ===${NC}"
    echo "## Configuration Tests" >> "$LOG_FILE"
    echo "\`\`\`bash" >> "$LOG_FILE"
    python3 tests/test_configurations.py 2>&1 | tee -a "$LOG_FILE"
    echo "\`\`\`" >> "$LOG_FILE"
fi

print_summary

exit $?
