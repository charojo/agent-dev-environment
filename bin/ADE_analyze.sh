#!/bin/bash
# Coverage analysis script
# Parses validate.log to extract and display coverage metrics

set -e

LOG_FILE="${1:-logs/validation_summary_log.md}"
BASELINE_LOG="${2:-}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "Error: Log file not found: $LOG_FILE"
    echo "Usage: $0 [log_file] [baseline_log]"
    exit 1
fi

# Extract Tier
TIER=$(grep "Validation Suite - Tier:" "$LOG_FILE" | cut -d':' -f2 | tr -d ' ')
: ${TIER:="unknown"}

# Extract backend coverage percentage
# Helper to strip ANSI colors
strip_colors() {
    sed 's/\x1b\[[0-9;]*[a-zA-Z]//g'
}

# Extract backend coverage percentage
extract_backend_coverage() {
    local file="$1"
    # Use tail -1 to get the last occurrence in case of duplicates
    grep "^TOTAL" "$file" | tail -1 | awk '{print $NF}' | sed 's/%//' | awk '{printf "%.0f", $1}' || true
}

# Extract frontend coverage percentage
extract_frontend_coverage() {
    local file="$1"
    # Use tail -1 to get the last occurrence in case of duplicates
    grep "^All files" "$file" | tail -1 | awk -F'|' '{print $2}' | tr -d ' ' | awk '{printf "%.0f", $1}' || true
}

# Extract frontend test summary (vitest format: "Tests  X passed (X)")
extract_frontend_tests() {
    local file="$1"
    local line=$(grep "Tests" "$file" | grep "passed" | strip_colors | tail -1 || true)
    
    # Extract passed
    local passed=$(echo "$line" | grep -oE "[0-9]+ passed" | head -1)
    # Extract skipped if present
    local skipped=$(echo "$line" | grep -oE "[0-9]+ skipped" | head -1)

    if [[ -n "$skipped" ]]; then
        echo "$passed, $skipped"
    else
        echo "$passed"
    fi
}

# Extract backend test summary (pytest format: "===== 134 passed, 2 skipped... =====")
extract_backend_tests() {
    local file="$1"
    # Look for pytest summary line ONLY in the Backend Tests section
    # Extract content between "=== Backend Tests" and "=== Frontend Tests" (or EOF)
    # Then grep for the pytest summary line
    sed -n '/=== Backend Tests/,/=== Frontend Tests/p' "$file" | strip_colors | \
        grep -E '[0-9]+ (passed|skipped|deselected|failed|error).* in [0-9.]+s' | tail -1 || true
}

# Extract compliance checks
check_compliance() {
    local file="$1"
    local name="$2"
    if grep -q "$3" "$file"; then
        echo "Passed"
    else
        echo "Failed/Skipped"
    fi
}
extract_e2e_tests() {
    local file="$1"
    # Extract just the E2E section to avoid false positives from Backend section
    local e2e_section=$(sed -n '/## E2E Tests/,/## Validation Summary/p' "$file")
    
    # Try to find Playwright specific output first: "  9 passed (19.7s)"
    local playwright_line=$(echo "$e2e_section" | strip_colors | grep -E '^[[:space:]]+[0-9]+ passed \([0-9.]+s\)' | tail -1 || true)
    
    if [[ -n "$playwright_line" ]]; then
        echo "$playwright_line"
    else
        # Fallback to Pytest output: "1 passed in 2.5s"
        echo "$e2e_section" | strip_colors | grep -E "[0-9]+ passed [a-z0-9(). ]*s" | tail -1 || true
    fi
}

# Extract static analysis counts
extract_contrast_tests() {
    local file="$1"
    # Count rows in the table (lines starting with | but not header/separator)
    # Using 'grep -v' to exclude header/separator lines which contain "Theme" or ":---"
    grep "^| " "$file" | grep -v "Theme" | grep -v ":---" | wc -l || echo "0"
}

extract_css_tests() {
    local file="$1"
    # Count summary lines with colons (e.g. "Files with issues: 0")
    # Restrict to the CSS section if possible? valid_log is global so we just grep for expected keys
    # or just assume unique strings.
    # Looking at the output, the summary lines are unique enough or we can sed/awk range.
    # Simpler: just grep for the specific metric lines we know exist
    grep -E "Files with issues:|Hardcoded color occurrences:|Components exceeding inline style threshold:|btn-icon override violations:" "$file" | wc -l || echo "0"
}

# Get current coverage
BACKEND_COV=$(extract_backend_coverage "$LOG_FILE")
FRONTEND_COV=$(extract_frontend_coverage "$LOG_FILE")

# Extract E2E coverage (from nyc_output if available)
E2E_COV=""
NYC_OUTPUT_DIR="src/web/.nyc_output"
if [[ -d "$NYC_OUTPUT_DIR" ]] && ls "$NYC_OUTPUT_DIR"/*.json 1>/dev/null 2>&1; then
    E2E_COV_RAW=$(cd src/web && npx nyc report --reporter=text 2>/dev/null | grep "^All files" | awk -F'|' '{print $2}' | tr -d ' ' | sed 's/%//' || true)
    if [[ -n "$E2E_COV_RAW" ]]; then
        E2E_COV=$(echo "$E2E_COV_RAW" | awk '{printf "%.0f", $1}')
    fi
fi

# Get test summaries - extract just the numbers
FRONTEND_TESTS_RAW=$(extract_frontend_tests "$LOG_FILE")
BACKEND_TESTS_RAW=$(extract_backend_tests "$LOG_FILE")

# Parse frontend: "Tests  215 passed (215)" -> "215 passed"
# Now handled inside extract_frontend_tests
FRONTEND_COUNTS=$(extract_frontend_tests "$LOG_FILE")

# Parse backend: "=== 134 passed, 2 skipped... ===" -> "134 passed, 2 skipped"
BACKEND_PASSED=$(echo "$BACKEND_TESTS_RAW" | grep -oE "[0-9]+ passed" | head -1)
BACKEND_SKIPPED=$(echo "$BACKEND_TESTS_RAW" | grep -oE "[0-9]+ skipped" || echo "")
BACKEND_DESELECTED=$(echo "$BACKEND_TESTS_RAW" | grep -oE "[0-9]+ deselected" || echo "")

# Get E2E summary
E2E_TESTS_RAW=$(extract_e2e_tests "$LOG_FILE")
E2E_PASSED=$(echo "$E2E_TESTS_RAW" | grep -oE "[0-9]+ passed" | head -1)

# If E2E was skipped, ignore any falsely matched passed count
if grep -qE "Skipping E2E tests|No E2E tests found" "$LOG_FILE"; then
    E2E_PASSED=""
fi

# Compliance status & counts
CONTRAST_STATUS=$(check_compliance "$LOG_FILE" "Contrast" "Contrast Standards Report")
CONTRAST_COUNT=$(extract_contrast_tests "$LOG_FILE")

PATH_STATUS=$(check_compliance "$LOG_FILE" "Paths" "No absolute paths found")
PATH_COUNT=1 # It's a single global check

CSS_STATUS=$(check_compliance "$LOG_FILE" "CSS" "CSS Compliance Report")
CSS_COUNT=$(extract_css_tests "$LOG_FILE")

if [[ -n "$BACKEND_COV" && -n "$FRONTEND_COV" ]]; then
    TOTAL_COV=$(echo "scale=2; ($BACKEND_COV + $FRONTEND_COV) / 2" | bc)
elif [[ -n "$BACKEND_COV" ]]; then
    TOTAL_COV="$BACKEND_COV"
fi

echo ""
echo "## Codebase Summary"
# Find analyze_project.py relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
python3 "$SCRIPT_DIR/ADE_analyze_project.py" --dual
echo ""

echo ""
echo "## Detailed Metrics"
echo ""

# Timing Parsing
# Timing Parsing
AUTOFIX_TIME=$(grep "TIMING_METRIC: AutoFix=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)
BACKEND_TIME=$(grep "TIMING_METRIC: Backend=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)
FRONTEND_TIME=$(grep "TIMING_METRIC: Frontend=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)
E2E_TIME=$(grep "TIMING_METRIC: E2E=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)
TOTAL_TIME=$(grep "TIMING_METRIC: Total=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)

# Defaults if missing
: ${AUTOFIX_TIME:="-"}
: ${BACKEND_TIME:="-"}
: ${FRONTEND_TIME:="-"}
: ${E2E_TIME:="-"}


# Markdown Table Output
echo "| Metric | Tests | Coverage | Time |"
echo "| :--- | :--- | :--- | :--- |"

# 1. Frontend
FRONTEND_COV_DISPLAY="${FRONTEND_COV:--}%"
if [[ -z "$FRONTEND_COV" ]]; then
    if [[ "$TIER" == "full" || "$TIER" == "exhaustive" ]]; then
         FRONTEND_COV_DISPLAY="-" # Failed to collect
    else
         FRONTEND_COV_DISPLAY="-" # Not run
    fi
fi

if [[ -n "$FRONTEND_COUNTS" ]]; then
    echo "| Frontend | $FRONTEND_COUNTS | $FRONTEND_COV_DISPLAY | ${FRONTEND_TIME} |"
else
    # Check if skipped
    if grep -q "Skipping frontend" "$LOG_FILE"; then
         echo "| Frontend | Skipped | - | - |"
    else
         # Might be fast mode or failed
         if [[ "$TIER" == "fast" || "$TIER" == "medium" ]]; then
             echo "| Frontend | $FRONTEND_COUNTS | - | ${FRONTEND_TIME} |"
         else
             echo "| Frontend | No Results | - | ${FRONTEND_TIME} |"
         fi
    fi
fi

# 2. E2E
E2E_COV_DISPLAY="${E2E_COV:--}"
if [[ -n "$E2E_COV" ]]; then
    E2E_COV_DISPLAY="${E2E_COV}%"
fi
if [[ -n "$E2E_PASSED" ]]; then
    echo "| E2E | $E2E_PASSED | $E2E_COV_DISPLAY | ${E2E_TIME} |"
else
    if grep -qE "Skipping E2E tests|No E2E tests found" "$LOG_FILE"; then
         echo "| E2E | Skipped | - | - |"
    else
         echo "| E2E | Not Run/Failed | - | ${E2E_TIME} |"
    fi
fi

# 3. Backend
BACKEND_COV_DISPLAY="${BACKEND_COV:--}%"
if [[ -z "$BACKEND_COV" ]]; then
    if [[ "$TIER" == "full" || "$TIER" == "exhaustive" ]]; then
         BACKEND_COV_DISPLAY="-" 
    else
         BACKEND_COV_DISPLAY="-" 
    fi
fi

if [[ -n "$BACKEND_PASSED" || -n "$BACKEND_DESELECTED" ]]; then
    RESULT_STR=""
    if [[ -n "$BACKEND_PASSED" ]]; then RESULT_STR="$BACKEND_PASSED"; fi
    
    if [[ -n "$BACKEND_SKIPPED" ]]; then 
        if [[ -n "$RESULT_STR" ]]; then RESULT_STR="$RESULT_STR, $BACKEND_SKIPPED"; else RESULT_STR="$BACKEND_SKIPPED"; fi
    fi
    
    if [[ -n "$BACKEND_DESELECTED" ]]; then
        if [[ -n "$RESULT_STR" ]]; then RESULT_STR="$RESULT_STR, $BACKEND_DESELECTED"; else RESULT_STR="$BACKEND_DESELECTED"; fi
    fi
    
    if [[ -z "$RESULT_STR" ]]; then RESULT_STR="0 passed"; fi

    echo "| Backend | $RESULT_STR | $BACKEND_COV_DISPLAY | ${BACKEND_TIME} |"
else
    if grep -q "Skipping backend" "$LOG_FILE"; then
         echo "| Backend | Skipped | - | - |"
    else
         echo "| Backend | No Results | - | ${BACKEND_TIME} |"
    fi
fi

# 4. Static Checks
echo "| Contrast | $CONTRAST_COUNT tests ($CONTRAST_STATUS) | - | - |"
echo "| CSS | $CSS_COUNT checks ($CSS_STATUS) | - | - |"
echo "| Paths | $PATH_COUNT check ($PATH_STATUS) | - | - |"

if [[ "$AUTOFIX_TIME" != "-" ]]; then
    echo "| Auto-Fix | Done | - | ${AUTOFIX_TIME} |"
fi

# 5. Total (Bottom)
if [[ -n "$TOTAL_COV" ]]; then
    printf "  %-12s %24s %10s %8s\n" "TOTAL" "" "${TOTAL_COV}%" "${TOTAL_TIME}"
    printf "  %-12s %24s %10s %8s\n" "------------" "------------------------" "--------" "--------"
fi

echo ""
if [[ -n "$BACKEND_SKIPPED" ]]; then
    echo "  * $BACKEND_SKIPPED are live API tests (use --live to run)"
    echo ""
fi

# Compare with baseline if provided
if [[ -n "$BASELINE_LOG" && -f "$BASELINE_LOG" ]]; then
    BASELINE_BACKEND=$(extract_backend_coverage "$BASELINE_LOG")
    BASELINE_FRONTEND=$(extract_frontend_coverage "$BASELINE_LOG")
    
    echo "Baseline Coverage (from $BASELINE_LOG):"
    echo "  Backend:  ${BASELINE_BACKEND}%"
    echo "  Frontend: ${BASELINE_FRONTEND}%"
    echo ""
    
    if [[ -n "$BASELINE_BACKEND" && -n "$BASELINE_FRONTEND" ]]; then
        BASELINE_TOTAL=$(echo "scale=2; ($BASELINE_BACKEND + $BASELINE_FRONTEND) / 2" | bc)
        echo "  Total (avg): ${BASELINE_TOTAL}%"
        echo ""
        
        # Calculate improvements
        BACKEND_DELTA=$(echo "scale=2; $BACKEND_COV - $BASELINE_BACKEND" | bc)
        FRONTEND_DELTA=$(echo "scale=2; $FRONTEND_COV - $BASELINE_FRONTEND" | bc)
        TOTAL_DELTA=$(echo "scale=2; $TOTAL_COV - $BASELINE_TOTAL" | bc)
        
        echo "Improvement:"
        echo "  Backend:  ${BACKEND_DELTA}% ($(printf '%+.2f' $BACKEND_DELTA))"
        echo "  Frontend: ${FRONTEND_DELTA}% ($(printf '%+.2f' $FRONTEND_DELTA))"
        echo "  Total:    ${TOTAL_DELTA}% ($(printf '%+.2f' $TOTAL_DELTA))"
        echo ""
    fi
fi


