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
# See architecture: [validate_workflow.svg](../docs/assets/images/validate_workflow.svg) <!-- @diagram: validate_workflow.svg -->

set -eo pipefail

# Store the project root directory
if [ -d "agent_env" ]; then
    ROOT_DIR="$(pwd)"
elif [ -d ".agent" ]; then
    ROOT_DIR="$(pwd)"
elif [[ "$(basename "$(dirname "$0")")" == "bin" ]]; then
    ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
else
    ROOT_DIR="$(pwd)"
fi
cd "$ROOT_DIR"

# Ensure Environment
# Check for First Run or explicit configuration
if [[ "$1" != "--help" && "$1" != "-h" ]]; then
    if [[ ! -f ".agent_setup_complete" ]] || [[ "$1" == "--configure" ]]; then
        if [ -f "$SCRIPT_DIR/configure.py" ]; then
            echo -e "${YELLOW}Running initial configuration...${NC}"
            uv run python "$SCRIPT_DIR/configure.py" --interactive
        fi
    fi
fi

if [ -f "./agent_env/bin/ensure_env.sh" ]; then
    ./agent_env/bin/ensure_env.sh
elif [ -f "./.agent/bin/ensure_env.sh" ]; then
    ./.agent/bin/ensure_env.sh
else
    ./bin/ensure_env.sh
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
E2E_ONLY=false       # Run ONLY E2E tests
INITIALIZING=false   # Internal flag for missing coverage
REFRESHING=false     # Internal flag for outdated coverage
PYTEST_SELECTION=""  # Centralized selection args
RUN_CONFIG_TESTS=false # Run configuration validation tests

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

${YELLOW}Tiers:${NC} (mutually exclusive)
  --fast         ${GREEN}Fast${NC} - LOC-only tests for changes (~5s)
  --medium       ${YELLOW}Medium${NC} - file-level coverage (~30s)
  --full         ${BLUE}Full${NC} - all tests except \$ tests (~90s)
  --exhaustive   ${RED}Exhaustive${NC} - mutation, parallel (~5m)

${YELLOW}Options:${NC}
  --live         Include \$ tests (Gemini API calls)
  --e2e-only     Run ONLY E2E tests
  --no-fix       Skip auto-formatting
  --parallel     Parallelize tests (auto in exhaustive)
  --configure    Run interactive configuration wizard
  --config-tests Run configuration validation tests (RESETS REPO)
  --verbose, -v  Detailed output
  --help, -h     Show this help

${YELLOW}Examples:${NC}
  ./scripts/validate.sh --fast         # Fast: quick changeset check
  ./scripts/validate.sh --medium       # Medium: file-level coverage
  ./scripts/validate.sh --full         # Full: pre-commit validation
  ./scripts/validate.sh --exhaustive   # Exhaustive: pre-merge
  ./scripts/validate.sh --full --live  # Full + API tests

${YELLOW}Tier Details:${NC}
  Fast:       LOC-only (testmon), no lint, no E2E
  Medium:     File-level, auto-fix, no E2E
  Full:       All tests (skip \$), E2E, auto-fix, coverage
  Exhaustive: All + mutation, parallel, multi-browser

${YELLOW}Notes:${NC}
  - \$ tests are marked "live" (Gemini API calls)
  - Fast tier skips unchanged code (testmon)
  - Use --full for CI/pre-merge validation
EOF
}

# ============================================
# Argument Parsing
# ============================================
for arg in "$@"; do
    case $arg in
        --help|-h) show_help; exit 0 ;;
        --medium) TIER="medium" ;;
        --full) TIER="full" ;;
        --exhaustive) TIER="exhaustive" ;;
        --fast) TIER="fast" ;;
        --live) INCLUDE_LIVE=true ;;
        --debug) VERBOSE=true; PARALLEL=false ;; # Debug mode implies verbose and sequential
        --e2e-only) E2E_ONLY=true; TIER="full" ;;
        --configure) 
             # Handled early, but consume arg
             ;;
        --config-tests) RUN_CONFIG_TESTS=true ;;
        --no-fix) SKIP_FIX=true ;;
        --parallel) PARALLEL=true ;;
        --verbose|-v) VERBOSE=true ;;
        *) echo -e "${RED}Unknown option: $arg${NC}"; show_help; exit 1 ;;
    esac
done
    
if [ $# -eq 0 ]; then
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
        # Minimal: skip lint, skip E2E
        TIER="fast"
        ;;
    medium)
        # Balanced: auto-fix, skip E2E
        ;;
    full)
        # Complete: auto-fix, E2E
        INCLUDE_E2E=true
        ;;
    exhaustive)
        # Maximum: auto-fix, E2E, parallel
        INCLUDE_E2E=true
        PARALLEL=true
        ;;
esac

# ============================================
# Setup
# ============================================

# ============================================
# Setup
# ============================================
mkdir -p logs
# Preserve .testmondata if it exists
find logs/ -maxdepth 1 -type f ! -name ".testmondata" -delete
LOG_FILE="logs/validation_summary_log.md"
export TESTMON_DATAFILE="logs/.testmondata"

# Timing
TOTAL_START=$(date +%s)
FIX_DURATION=0
BACKEND_DURATION=0
FRONTEND_DURATION=0
E2E_DURATION=0

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
INITIAL_CLEAN=false
if [[ ! -f "$TESTMON_DATAFILE" ]] || [[ ! -f ".coverage" ]]; then
    INITIAL_CLEAN=true
fi

# Initialize Log File with Markdown Header
echo "# Validation Report" > "$LOG_FILE"
log_msg "Date: $(date)"
log_msg "Tier: **${TIER}**"
log_msg ""

# Echo to stdout as well (formatted for terminal)
echo -e "${BLUE}Validation Suite${NC} - Tier: ${TIER}"

if [ "$INITIAL_CLEAN" = true ]; then
    log_msg "${YELLOW}Initial run or clean environment detected: This may take 1-3 minutes...${NC}"
    log_msg "${BLUE}Note: We are building the test/coverage metadata for the first time.${NC}"
    echo "> **Note:** Initial run detected. Building metadata..." >> "$LOG_FILE"
fi

log_msg ""

# Centralized Test Selection Logic
# Load Configuration via config_utils.py
ENABLED_MARKERS=""
if [ -f "bin/config_utils.py" ]; then
    # We use python to get the marker string e.g. -m "not processing"
    ENABLED_MARKERS=$(uv run python bin/config_utils.py get-markers)
    # Also check if python is enabled? If python is disabled, we shouldn't run backend tests at all.
    PYTHON_ENABLED=$(uv run python bin/config_utils.py get languages.python.enabled)
    JS_ENABLED=$(uv run python bin/config_utils.py get languages.typescript.enabled)
fi

# Fallback if config_utils missing or returns empty (assume enabled)
if [ -z "$PYTHON_ENABLED" ]; then PYTHON_ENABLED="true"; fi
if [ -z "$JS_ENABLED" ]; then JS_ENABLED="true"; fi


if [[ "$TIER" == "fast" || "$TIER" == "medium" ]]; then
    if [[ ! -f "$TESTMON_DATAFILE" ]]; then
        log_msg "${YELLOW}Initial run detected: Building testmon coverage database...${NC}"
        log_msg "${BLUE}Note: This initial scan may take 1-3 minutes depending on your environment.${NC}"
        INITIALIZING=true
        PYTEST_SELECTION="--testmon"
    else
        # Check if tests are newer than data
        test_changes=$(find tests/ -name "*.py" -newer "$TESTMON_DATAFILE" 2>/dev/null | wc -l)
        if [[ "$test_changes" -gt 0 ]]; then
            log_msg "${YELLOW}New test files detected, will refresh testmon...${NC}"
            REFRESHING=true
            PYTEST_SELECTION="--testmon"
        else
            log_msg "Selection: $([[ "$TIER" == "fast" ]] && echo "LOC-only" || echo "File-level") (testmon)"
            PYTEST_SELECTION="--testmon --testmon-forceselect"
        fi
    fi
    # Always exclude E2E from non-full tiers
    PYTEST_SELECTION="$PYTEST_SELECTION -m \"not e2e\""
elif [[ "$TIER" == "full" ]]; then
    log_msg "Selection: All tests"
    PYTEST_SELECTION=""
elif [[ "$TIER" == "exhaustive" ]]; then
    log_msg "Selection: All tests (parallel)"
    PYTEST_SELECTION="-n auto"
fi

# Append Feature Markers (e.g., "not processing") safely
if [ -n "$ENABLED_MARKERS" ]; then
    # If selection already has -m, we need to combine them carefully.
    # Pytest allows multiple -m but boolean logic is safer inside quotes? using multiple -m works as AND usually.
    # Actually, let's just append.
    PYTEST_SELECTION="$PYTEST_SELECTION $ENABLED_MARKERS"
fi


# ============================================
# Phase 1: Auto-fix (medium, full, exhaustive)
# ============================================
## @fn run_auto_fix
# Runs ruff and npm lint to automatically fix formatting and linting issues.
run_auto_fix() {
    if [ "$SKIP_FIX" = true ] || [ "$TIER" = "fast" ] || [ "$E2E_ONLY" = true ]; then
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

    if [ "$E2E_ONLY" = true ]; then
        log_msg "${YELLOW}Skipping backend (E2E only mode)${NC}"
        return
    fi
    
    log_msg ""
    echo -e "${BLUE}=== Backend Tests (Python) ===${NC}"
    echo "## Backend Tests (Python)" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    local pytest_args=""
    
    # Selection already computed upfront
    # CRITICAL: Ignore tests/validation to prevent double-execution and deadlocks
    pytest_args="$PYTEST_SELECTION --ignore=tests/validation"
    
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
    
    # Add verbosity
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -vv -s --timeout=300"
    elif [ "$TIER" != "exhaustive" ]; then
        pytest_args="$pytest_args -q --timeout=300"
    else
        pytest_args="$pytest_args --timeout=300"
    fi
    
    # Parallel override
    if [ "$PARALLEL" = true ] && [ "$TIER" != "exhaustive" ]; then
        pytest_args="$pytest_args -n auto"
    fi
    
    # Run tests with streaming output
    local output_tmp="logs/backend_output.tmp"
    log_msg "Command: uv run pytest $pytest_args"
    echo "\`\`\`bash" >> "$LOG_FILE"
    echo "Command: uv run pytest $pytest_args" >> "$LOG_FILE"
    echo "----------------------------------------" >> "$LOG_FILE"
    
    # We use eval to handle markers correctly in the variable
    eval "uv run pytest $pytest_args 2>&1" | tee "$output_tmp" | strip_ansi >> "$LOG_FILE"
    
    echo "----------------------------------------" >> "$LOG_FILE"
    echo "\`\`\`" >> "$LOG_FILE"
    log_msg "Backend unit tests completed."
    
    local output
    output=$(cat "$output_tmp")
    rm -f "$output_tmp"
    
    # Check if run succeeded
    if [[ "$INITIALIZING" == "true" && ! -s "$output_tmp" ]]; then
         log_msg "${RED}Initialization failed.${NC}"
    fi

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
}

# ============================================
# Phase 3: Frontend Tests
# ============================================
run_frontend_tests() {
    if [ "$JS_ENABLED" != "true" ]; then
        log_msg "${YELLOW}JavaScript disabled in config. Skipping frontend tests.${NC}"
        return
    fi
    
    if [ "$E2E_ONLY" = true ]; then
        log_msg "${YELLOW}Skipping frontend (E2E only mode)${NC}"
        return
    fi
    
    if [ ! -d "src/web" ]; then
        log_msg "${YELLOW}src/web not found, skipping frontend tests.${NC}"
        return
    fi
    
    echo "## Frontend Tests" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    cd src/web
    
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
        medium)
            echo "Selection: File-level (--changed)"
            vitest_args="--changed"
            ;;
        full|exhaustive)
            echo "Selection: All tests"
            if [ "$TIER" = "full" ] || [ "$TIER" = "exhaustive" ]; then
                vitest_args="--coverage"
            fi
            ;;
    esac
    
    # Run tests with real-time feedback
    local output_tmp="../../logs/frontend_output.tmp"
    echo "Executing: npm run test:run -- $vitest_args"
    
    echo "\`\`\`bash" >> "../../$LOG_FILE"
    
    # Use script to maintain TTY for vitest colors/progress if possible, or just tee
    eval "npm run test:run -- $vitest_args 2>&1" | tee "$output_tmp" | tee -a "../../$LOG_FILE"
    
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
}

# ============================================
# Phase 4: E2E Tests
# ============================================
run_e2e_tests() {
    if [ "$INCLUDE_E2E" = false ] && [ "$E2E_ONLY" = false ]; then
        log_msg ""
        log_msg "${YELLOW}Skipping E2E tests${NC}"
        echo "> **E2E Tests Skipped**" >> "$LOG_FILE"
        return
    fi

    if [ ! -d "src/web" ] && [ ! -d "tests/e2e" ]; then
        log_msg "${YELLOW}No E2E tests found (src/web or tests/e2e), skipping.${NC}"
        return
    fi
    echo -e "${BLUE}Starting servers and running browser tests (this may take 1-2 minutes)...${NC}"
    
    echo "## E2E Tests" >> "$LOG_FILE"
    echo "\`\`\`bash" >> "$LOG_FILE"
    
    local start=$(date +%s)
    
    local output
    output=$(uv run pytest -s --timeout=300 tests/validation/test_e2e_wrapper.py 2>&1) || true
    echo "$output" | strip_ansi >> "$LOG_FILE"
    
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
}

# ============================================
# Summary
# ============================================
print_summary() {
    local total_end=$(date +%s)
    local total_duration=$((total_end - TOTAL_START))
    
    log_msg ""
    echo -e "${BLUE}=== VALIDATION SUMMARY ===${NC}"
    echo "## Validation Summary" >> "$LOG_FILE"
    
    # Tier description
    local tier_desc
    case "$TIER" in
        fast) tier_desc="Fast (LOC-only)" ;;
        medium) tier_desc="Medium (file-level)" ;;
        full) tier_desc="Full (all tests)" ;;
        exhaustive) tier_desc="Exhaustive (max coverage)" ;;
    esac
    echo "- **Tier**: $tier_desc" >> "$LOG_FILE"
    
    # Status indicators
    local backend_status="${GREEN}✓${NC}"
    if [ "${BACKEND_FAILED:-0}" -gt 0 ]; then backend_status="${RED}✗${NC}"; fi
    
    local frontend_status="${GREEN}✓${NC}"
    if [ "${FRONTEND_FAILED:-0}" -gt 0 ]; then frontend_status="${RED}✗${NC}"; fi
    
    local e2e_status="${GREEN}✓${NC}"
    if [ "${E2E_FAILED:-0}" -gt 0 ]; then e2e_status="${RED}✗${NC}"; fi
    
    # Simple console output
    if [ "$E2E_ONLY" = false ]; then
        echo -e "Backend:     $backend_status ${BACKEND_PASSED:-0} passed"
        echo -e "Frontend:    $frontend_status ${FRONTEND_PASSED:-0} passed"
    fi
    if [ "$INCLUDE_E2E" = true ]; then
        echo -e "E2E:         $e2e_status ${E2E_PASSED:-0} passed"
    fi

    # Append detailed logs from wrappers so analyze.sh can find them
    if [ -f "logs/static_analysis.log" ]; then
        echo "" >> "$LOG_FILE" 
        echo "### Static Analysis" >> "$LOG_FILE"
        echo "\`\`\`" >> "$LOG_FILE"
        cat logs/static_analysis.log >> "$LOG_FILE"
        echo "\`\`\`" >> "$LOG_FILE"
    fi

    # Record Total Time for analyze.sh
    echo "TIMING_METRIC: Total=${total_duration}s" >> "$LOG_FILE"

    # Run Analysis (LOC metrics, coverage summary, etc.)
    log_msg ""
    echo "Running Validation Analysis..."
    
    local ANALYZE_SCRIPT="./bin/analyze.sh"
    if [ -f "./agent_env/bin/analyze.sh" ]; then
        ANALYZE_SCRIPT="./agent_env/bin/analyze.sh"
    elif [ -f "./.agent/bin/analyze.sh" ]; then
        ANALYZE_SCRIPT="./.agent/bin/analyze.sh"
    fi

    $ANALYZE_SCRIPT "$LOG_FILE" | strip_ansi >> "$LOG_FILE" || true

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
run_auto_fix
run_backend_tests
run_frontend_tests
run_e2e_tests

if [ "$RUN_CONFIG_TESTS" = true ]; then
    echo -e "${BLUE}=== Configuration Tests ===${NC}"
    echo "## Configuration Tests" >> "$LOG_FILE"
    echo "\`\`\`bash" >> "$LOG_FILE"
    python3 tests/test_configurations.py 2>&1 | tee -a "$LOG_FILE"
    echo "\`\`\`" >> "$LOG_FILE"
fi

print_summary

exit $?
