#!/bin/bash
# Unified Validation Script for Papeterie Engine
# Supports 4 workflow tiers: fast, medium, full, exhaustive
set -eo pipefail

# Store the project root directory
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

# Ensure Environment
./agent_env/bin/ensure_env.sh

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

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# Help
# ============================================
show_help() {
    cat <<EOF
${BLUE}Papeterie Engine Validation${NC}

${YELLOW}Usage:${NC} ./scripts/validate.sh [tier] [options]

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
mkdir -p logs
# Preserve .testmondata if it exists
find logs/ -maxdepth 1 -type f ! -name ".testmondata" -delete
LOG_FILE="logs/validate.log"
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

echo -e "${BLUE}Papeterie Validation${NC} - Tier: ${TIER}" | tee "$LOG_FILE"
echo "Started at $(date)" | tee -a "$LOG_FILE"

if [ "$INITIAL_CLEAN" = true ]; then
    echo -e "${YELLOW}Initial run or clean environment detected: This may take 1-3 minutes...${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}Note: We are building the test/coverage metadata for the first time.${NC}" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

# Centralized Test Selection Logic
if [[ "$TIER" == "fast" || "$TIER" == "medium" ]]; then
    if [[ ! -f "$TESTMON_DATAFILE" ]]; then
        echo -e "${YELLOW}Initial run detected: Building testmon coverage database...${NC}" | tee -a "$LOG_FILE"
        echo -e "${BLUE}Note: This initial scan may take 1-3 minutes depending on your environment.${NC}" | tee -a "$LOG_FILE"
        INITIALIZING=true
        PYTEST_SELECTION="--testmon"
    else
        # Check if tests are newer than data
        test_changes=$(find tests/ -name "*.py" -newer "$TESTMON_DATAFILE" 2>/dev/null | wc -l)
        if [[ "$test_changes" -gt 0 ]]; then
            echo -e "${YELLOW}New test files detected, will refresh testmon...${NC}" | tee -a "$LOG_FILE"
            REFRESHING=true
            PYTEST_SELECTION="--testmon"
        else
            echo "Selection: $([[ "$TIER" == "fast" ]] && echo "LOC-only" || echo "File-level") (testmon)" | tee -a "$LOG_FILE"
            PYTEST_SELECTION="--testmon --testmon-forceselect"
        fi
    fi
    # Always exclude E2E from non-full tiers
    PYTEST_SELECTION="$PYTEST_SELECTION -m \"not e2e\""
elif [[ "$TIER" == "full" ]]; then
    echo "Selection: All tests" | tee -a "$LOG_FILE"
    PYTEST_SELECTION=""
elif [[ "$TIER" == "exhaustive" ]]; then
    echo "Selection: All tests (parallel)" | tee -a "$LOG_FILE"
    PYTEST_SELECTION="-n auto"
fi

# ============================================
# Phase 1: Auto-fix (medium, full, exhaustive)
# ============================================
run_auto_fix() {
    if [ "$SKIP_FIX" = true ] || [ "$TIER" = "fast" ] || [ "$E2E_ONLY" = true ]; then
        echo -e "${YELLOW}Skipping auto-fix${NC}" | tee -a "$LOG_FILE"
        return
    fi
    
    echo -e "${BLUE}=== Auto-fix ===${NC}" | tee -a "$LOG_FILE"
    local start=$(date +%s)
    
    echo "Fixing Backend..." | tee -a "$LOG_FILE"
    uv run ruff check --fix . 2>&1 | tee -a "$LOG_FILE" || true
    uv run ruff format . 2>&1 | tee -a "$LOG_FILE" || true
    
    echo "Fixing Frontend..." | tee -a "$LOG_FILE"
    cd src/web
    npm run lint -- --fix 2>&1 | tee -a "../../$LOG_FILE" || true
    cd "$ROOT_DIR"
    
    local end=$(date +%s)
    FIX_DURATION=$((end - start))
    echo "TIMING_METRIC: AutoFix=${FIX_DURATION}s" >> "$LOG_FILE"
}

run_backend_tests() {
    if [ "$E2E_ONLY" = true ]; then
        echo -e "${YELLOW}Skipping backend (E2E only mode)${NC}" | tee -a "$LOG_FILE"
        return
    fi
    
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}=== Backend Tests (Python) ===${NC}" | tee -a "$LOG_FILE"
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
        pytest_args="$pytest_args --cov=src --cov-report=term-missing"
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
    echo "Command: uv run pytest $pytest_args" | tee -a "$LOG_FILE"
    echo "----------------------------------------" | tee -a "$LOG_FILE"
    
    # We use eval to handle markers correctly in the variable
    eval "uv run pytest $pytest_args 2>&1" | tee "$output_tmp" | tee -a "$LOG_FILE"
    
    echo "----------------------------------------" | tee -a "$LOG_FILE"
    echo "Backend unit tests completed." | tee -a "$LOG_FILE"

    local output
    output=$(cat "$output_tmp")
    rm -f "$output_tmp"
    
    # Check if run succeeded
    if [[ "$INITIALIZING" == "true" && ! -s "$output_tmp" ]]; then
         echo -e "${RED}Initialization failed.${NC}" | tee -a "$LOG_FILE"
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
    if [ "$E2E_ONLY" = true ]; then
        echo -e "${YELLOW}Skipping frontend (E2E only mode)${NC}" | tee -a "$LOG_FILE"
        return
    fi
    
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}=== Frontend Tests (Vitest) ===${NC}" | tee -a "$LOG_FILE"
    local start=$(date +%s)
    
    cd src/web
    
    local vitest_args=""
    
    case "$TIER" in
        fast)
            # LOC-based selection if map exists
            echo "Selection: LOC-only" | tee -a "../../$LOG_FILE"
            if [ -f ".vitest-loc-map.json" ]; then
                local loc_tests=$(node scripts/select-tests-by-loc.js 2>/dev/null | grep -v "^#" | tr '\n' ' ')
                if [ -n "$loc_tests" ]; then
                    echo "Found tests for changed LOC: $loc_tests" | tee -a "../../$LOG_FILE"
                    vitest_args="$loc_tests"
                else
                    echo "No tests found, falling back to --changed" | tee -a "../../$LOG_FILE"
                    vitest_args="--changed"
                fi
            else
                echo "LOC map not found, using --changed" | tee -a "../../$LOG_FILE"
                vitest_args="--changed"
            fi
            ;;
        medium)
            echo "Selection: File-level (--changed)" | tee -a "../../$LOG_FILE"
            vitest_args="--changed"
            ;;
        full|exhaustive)
            echo "Selection: All tests" | tee -a "../../$LOG_FILE"
            if [ "$TIER" = "full" ] || [ "$TIER" = "exhaustive" ]; then
                vitest_args="--coverage"
            fi
            ;;
    esac
    
    # Run tests with real-time feedback
    local output_tmp="../../logs/frontend_output.tmp"
    echo "Executing: npm run test:run -- $vitest_args" | tee -a "../../$LOG_FILE"
    
    # Use script to maintain TTY for vitest colors/progress if possible, or just tee
    eval "npm run test:run -- $vitest_args 2>&1" | tee "$output_tmp" | tee -a "../../$LOG_FILE"
    
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
        echo "" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}Skipping E2E tests${NC}" | tee -a "$LOG_FILE"
        return
    fi
    
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}=== E2E Tests (Playwright) ===${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}Starting servers and running browser tests (this may take 1-2 minutes)...${NC}" | tee -a "$LOG_FILE"
    local start=$(date +%s)
    
    local output
    output=$(uv run pytest -s --timeout=300 tests/validation/test_e2e_wrapper.py 2>&1) || true
    echo "$output" | tee -a "$LOG_FILE"
    
    if [[ "$output" == *"Timed out"* ]]; then
        echo -e "${RED}E2E wrapper timed out. Check logs/backend_e2e.log and logs/frontend_e2e.log for server errors.${NC}" | tee -a "$LOG_FILE"
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
    
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}=== VALIDATION SUMMARY ===${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    
    # Tier description
    local tier_desc
    case "$TIER" in
        fast) tier_desc="Fast (LOC-only)" ;;
        medium) tier_desc="Medium (file-level)" ;;
        full) tier_desc="Full (all tests)" ;;
        exhaustive) tier_desc="Exhaustive (max coverage)" ;;
    esac
    echo "Tier:        $tier_desc" | tee -a "$LOG_FILE"
    
    # Status indicators
    local backend_status="${GREEN}✓${NC}"
    if [ "${BACKEND_FAILED:-0}" -gt 0 ]; then backend_status="${RED}✗${NC}"; fi
    
    local frontend_status="${GREEN}✓${NC}"
    if [ "${FRONTEND_FAILED:-0}" -gt 0 ]; then frontend_status="${RED}✗${NC}"; fi
    
    local e2e_status="${GREEN}✓${NC}"
    if [ "${E2E_FAILED:-0}" -gt 0 ]; then e2e_status="${RED}✗${NC}"; fi
    
    # Results
    if [ "$E2E_ONLY" = false ]; then
        if [ "$TIER" = "fast" ] || [ "$TIER" = "medium" ]; then
            echo -e "Backend:     $backend_status ${BACKEND_PASSED:-0} passed, ${BACKEND_SKIPPED:-0} skipped, ${BACKEND_DESELECTED:-0} deselected (${BACKEND_DURATION}s)" | tee -a "$LOG_FILE"
        else
            echo -e "Backend:     $backend_status ${BACKEND_PASSED:-0} passed, ${BACKEND_SKIPPED:-0} skipped (${BACKEND_DURATION}s)" | tee -a "$LOG_FILE"
        fi
        echo -e "Frontend:    $frontend_status ${FRONTEND_PASSED:-0} passed (${FRONTEND_DURATION}s)" | tee -a "$LOG_FILE"
    fi
    
    if [ "$INCLUDE_E2E" = true ] || [ "$E2E_ONLY" = true ]; then
        echo -e "E2E:         $e2e_status ${E2E_PASSED:-0} passed (${E2E_DURATION}s)" | tee -a "$LOG_FILE"
    else
        echo "E2E:         skipped" | tee -a "$LOG_FILE"
    fi
    
    if [ "$FIX_DURATION" -gt 0 ]; then
        echo "AutoFix:     ${FIX_DURATION}s" | tee -a "$LOG_FILE"
    fi
    
    echo "" | tee -a "$LOG_FILE"

    # Append detailed logs from wrappers so analyze.sh can find them
    if [ -f "logs/static_analysis.log" ]; then
        echo "" >> "$LOG_FILE" 
        echo "Appending Static Analysis logs..." >> "$LOG_FILE"
        cat logs/static_analysis.log >> "$LOG_FILE"
    fi

    # Record Total Time for analyze.sh
    echo "TIMING_METRIC: Total=${total_duration}s" >> "$LOG_FILE"

    # Run Analysis (LOC metrics, coverage summary, etc.)
    # Only run in full/exhaustive or if verbose, to keep fast mode fast? 
    # User asked for it, so let's run it unless fast mode?
    # Actually, analyze.sh is fast (just reading logs/counting lines).
    
    echo "" | tee -a "$LOG_FILE"
    echo "Running Validation Analysis..." | tee -a "$LOG_FILE"
    ./agent_env/bin/analyze.sh "$LOG_FILE" | tee -a "$LOG_FILE" || true

    # Overall status (Original print_summary does return 0/1, we should preserve that)
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
print_summary

exit $?
