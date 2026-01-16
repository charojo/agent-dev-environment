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
TIER=$(grep "Tier: \*\*" "$LOG_FILE" | sed -n 's/.*Tier: \*\*\([^*]*\)\*\*.*/\1/p' | tr -d ' ')
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
    # Coverage match: TOTAL followed by numbers and ending with % (avoids Token Analysis TOTAL)
    grep "^TOTAL" "$file" | grep "%" | tail -1 | awk '{print $NF}' | sed 's/%//' | awk '{printf "%.0f", $1}' || true
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
    
    # Extract passed, failed, skipped
    local passed=$(echo "$line" | grep -oE "[0-9]+ passed" | head -1)
    local failed=$(echo "$line" | grep -oE "[0-9]+ failed" | head -1)
    local skipped=$(echo "$line" | grep -oE "[0-9]+ skipped" | head -1)

    local res="$passed"
    if [[ -n "$failed" && "$failed" != "0 failed" ]]; then
        res="❌ $failed, $res"
    fi
    if [[ -n "$skipped" ]]; then
        res="$res, $skipped"
    fi
    echo "$res"
}

# Extract backend test summary (pytest format: "===== 134 passed, 2 skipped... =====")
extract_backend_tests() {
    local file="$1"
    # Look for pytest summary line ONLY in the Backend Tests section
    local raw_line=$(sed -n '/## Backend Tests/,/## Frontend Tests/p' "$file" | strip_colors | \
        grep -E '[0-9]+ (passed|skipped|deselected|failed|error).* in [0-9.]+s' | tail -1 || true)
    
    # Clean up the line (remove == and leading/trailing whitespace)
    echo "$raw_line" | sed 's/=//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Extract compliance checks
check_compliance() {
    local file="$1"
    local section_name="$2"
    local search_str="$3"

    # Extract the static analysis section
    local static_section=$(sed -n '/### Static Analysis/,/TIMING_METRIC/p' "$file")

    if echo "$static_section" | grep -qi "$search_str"; then
        # Look for the icon in a larger window (top 100 lines of section)
        local results=$(echo "$static_section" | grep -iA 100 "$search_str")
        if echo "$results" | grep -q "✅"; then
             echo "Passed"
        elif echo "$results" | grep -q "⚠️"; then
             echo "Warning"
        else
             echo "Failed"
        fi
    else
        if [[ "$TIER" == "fast" ]]; then
             echo "Skipped"
        else
             echo "Failed"
        fi
    fi
}
extract_e2e_tests() {
    local file="$1"
    # Extract just the E2E section to avoid false positives from Backend section
    local e2e_section=$(sed -n '/## E2E Tests/,/## Validation Summary/p' "$file")
    
    # Detect critical failures first
    if echo "$e2e_section" | grep -qE "FAILED|Timed out|failed|Error"; then
        # Check if there are still some passing tests reported
        local passed=$(echo "$e2e_section" | strip_colors | grep -oE "[0-9]+ passed" | head -1 || true)
        if [[ -n "$passed" && "$passed" != "0 passed" ]]; then
             echo "✗ Partial ($passed)"
        else
             echo "✗ Failed"
        fi
        return
    fi

    # Try to find Playwright specific output first: "  9 passed (19.7s)"
    local playwright_line=$(echo "$e2e_section" | strip_colors | grep -E '^[[:space:]]+[0-9]+ passed \([0-9.]+s\)' | tail -1 || true)
    
    if [[ -n "$playwright_line" ]]; then
        echo "$playwright_line"
    else
        # Fallback to Pytest output, but AVOID the "1 passed" from the wrapper itself
        # Wrapper is usually "1 passed" or "0 passed"
        local pytest_line=$(echo "$e2e_section" | strip_colors | grep -E "[0-9]+ passed [a-z0-9(). ]*s" | tail -1 || true)
        if [[ "$pytest_line" == "1 passed"* ]]; then
            # If it's just 1 passed, it might be the wrapper. Check if anything else failed.
            echo "✓ Subsystem OK"
        else
            echo "${pytest_line:-Unknown}"
        fi
    fi
}

# Extract static analysis counts
extract_contrast_tests() {
    local file="$1"
    # Extract from the contrast header until the next script header or TIMING_METRIC
    local section=$(sed -n '/--- agent_env\/bin\/ADE_check_contrast.py ---/,/--- agent_env\/bin\/\|TIMING_METRIC/p' "$file")
    echo "$section" | grep "^| " | grep -v "Theme" | grep -v ":---" | wc -l || echo "0"
}

extract_css_tests() {
    local file="$1"
    # Find the CSS report section
    local section=$(sed -n '/--- agent_env\/bin\/ADE_check_css_compliance.py ---/,/TIMING_METRIC/p' "$file")
    # Sum up the counts from the summary lines
    local count=$(echo "$section" | grep -E "Files with issues:|Hardcoded color occurrences:|Components exceeding inline style threshold:|btn-icon override violations:" | awk -F': ' '{sum += $2} END {print sum}')
    echo "${count:-0}"
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

# Get test summaries
FRONTEND_COUNTS=$(extract_frontend_tests "$LOG_FILE")
BACKEND_STATUS=$(extract_backend_tests "$LOG_FILE")
E2E_STATUS=$(extract_e2e_tests "$LOG_FILE")

# If E2E was skipped, ignore any falsely matched passed count
if grep -qE "Skipping E2E tests|No E2E tests found" "$LOG_FILE"; then
    E2E_STATUS=""
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
STATIC_TIME=$(grep "TIMING_METRIC: Static=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)
TOTAL_TIME=$(grep "TIMING_METRIC: Total=" "$LOG_FILE" | cut -d'=' -f2 | tail -1)

# Defaults if missing
: ${AUTOFIX_TIME:="-"}
: ${BACKEND_TIME:="-"}
: ${FRONTEND_TIME:="-"}
: ${E2E_TIME:="-"}
: ${STATIC_TIME:="-"}


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
    if [[ "$FRONTEND_COUNTS" == *"❌"* || "$FRONTEND_COUNTS" == *"failed"* ]]; then
        FE_ICON="❌"
    else
        FE_ICON="✅"
    fi
    echo "| Frontend | $FE_ICON $FRONTEND_COUNTS | $FRONTEND_COV_DISPLAY | ${FRONTEND_TIME} |"
else
    # Check if skipped
    if grep -q "Skipping frontend" "$LOG_FILE"; then
         echo "| Frontend | ⚪ Skipped | - | - |"
    else
         # Might be fast mode or failed
         if [[ "$TIER" == "fast" || "$TIER" == "medium" ]]; then
             echo "| Frontend | ⚪ Skipped (Fast/Medium) | - | ${FRONTEND_TIME} |"
         else
             echo "| Frontend | ❌ No Results | - | ${FRONTEND_TIME} |"
         fi
    fi
fi

# 2. E2E
E2E_COV_DISPLAY="${E2E_COV:--}"
if [[ -n "$E2E_COV" ]]; then
    E2E_COV_DISPLAY="${E2E_COV}%"
fi
if [[ -n "$E2E_STATUS" ]]; then
    if [[ "$E2E_STATUS" == *"✗"* || "$E2E_STATUS" == *"failed"* || "$E2E_STATUS" == *"Failed"* ]]; then
        E2E_ICON="❌"
    else
        E2E_ICON="✅"
    fi
    # If the status already has an icon from extract_e2e_tests, we don't want to double up or mismatch
    # extract_e2e_tests returns things like "✗ Partial (8 passed)" or "  8 passed (23.5s)"
    # Clean it up: remove any leading icon if we are adding our own
    E2E_CLEAN_STATUS=$(echo "$E2E_STATUS" | sed 's/^[✗✓✅❌][[:space:]]*//')
    echo "| E2E | $E2E_ICON $E2E_CLEAN_STATUS | $E2E_COV_DISPLAY | ${E2E_TIME} |"
else
    if grep -qE "Skipping E2E tests|No E2E tests found" "$LOG_FILE"; then
         echo "| E2E | ⚪ Skipped | - | - |"
    else
         echo "| E2E | ❌ Not Run/Failed | - | ${E2E_TIME} |"
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

if [[ -n "$BACKEND_STATUS" ]]; then
    if [[ "$BACKEND_STATUS" == *"failed"* || "$BACKEND_STATUS" == *"error"* ]]; then
        BE_ICON="❌"
    else
        BE_ICON="✅"
    fi
    echo "| Backend | $BE_ICON $BACKEND_STATUS | $BACKEND_COV_DISPLAY | ${BACKEND_TIME} |"
else
    if grep -q "Skipping backend" "$LOG_FILE"; then
         echo "| Backend | ⚪ Skipped | - | - |"
    else
         echo "| Backend | ❌ No Results | - | ${BACKEND_TIME} |"
    fi
fi

# 4. Static Checks
# Map status to icon
get_icon() {
    case "$1" in
        "Passed") echo "✅" ;;
        "Warning") echo "⚠️" ;;
        "Failed") echo "❌" ;;
        "Skipped") echo "⚪" ;;
        *) echo "⚪" ;;
    esac
}
C_ICON=$(get_icon "$CONTRAST_STATUS")
CSS_ICON=$(get_icon "$CSS_STATUS")
P_ICON=$(get_icon "$PATH_STATUS")

echo "| Contrast | $C_ICON $CONTRAST_COUNT tests ($CONTRAST_STATUS) | - | - |"
echo "| CSS | $CSS_ICON $CSS_COUNT checks ($CSS_STATUS) | - | - |"
echo "| Paths | $P_ICON $PATH_COUNT check ($PATH_STATUS) | - | - |"

# Subsystems
if grep -q "Unified Matrix generated" "$LOG_FILE"; then
    echo "| Matrix | ✅ Generated | - | - |"
fi
if grep -q "Analyzing logs/token_ledger.csv" "$LOG_FILE"; then
    echo "| Tokens | ✅ Analyzed | - | - |"
fi

if [[ "$AUTOFIX_TIME" != "-" ]]; then
    echo "| Auto-Fix | ✅ Done | - | ${AUTOFIX_TIME} |"
fi

# 5. Total (Bottom)
if [[ -n "$TOTAL_COV" ]]; then
    printf "  %-12s %24s %s code coverage in %s\n" "TOTAL" "" "${TOTAL_COV}%" "${TOTAL_TIME}"
    printf "  %-12s %24s %10s %8s\n" "------------" "------------------------" "--------" "--------"
fi

##############################################
# ASCII Output to Stderr (for Terminal)
##############################################
# Print a clean ASCII summary to stderr so it appears in the console
# even when stdout is redirected to the log file.
{
    echo ""
    echo "=== Detailed Metrics (ASCII) ==="
    printf "%-10s | %-20s | %-10s | %-10s\n" "Metric" "Tests" "Coverage" "Time"
    echo "-----------|----------------------|------------|-----------"
    
    # Frontend output
    F_COV="${FRONTEND_COV_DISPLAY}"
    F_TESTS="${FRONTEND_COUNTS:-No Results}"
    if [[ "$TIER" == "fast" || "$TIER" == "medium" ]] && [[ -z "$FRONTEND_COUNTS" ]]; then
         F_TESTS="Skipped"
    fi
     printf "%-10s | %-20s | %-10s | %-10s\n" "Frontend" "$F_TESTS" "$F_COV" "$FRONTEND_TIME"

    # E2E output
    E_COV="${E2E_COV_DISPLAY}"
    E_TESTS="Not Run/Failed"
    if [[ -n "$E2E_STATUS" ]]; then
         E_TESTS=$(echo "$E2E_STATUS" | sed 's/^[✗✓✅❌][[:space:]]*//')
    elif grep -qE "Skipping E2E tests|No E2E tests found" "$LOG_FILE"; then
         E_TESTS="Skipped"
    fi
    printf "%-10s | %-20s | %-10s | %-10s\n" "E2E" "$E_TESTS" "$E_COV" "$E2E_TIME"

    # Backend output
    B_COV="${BACKEND_COV_DISPLAY}"
    B_TESTS="0 passed"
    if [[ -n "$BACKEND_STATUS" ]]; then
        B_TESTS="$BACKEND_STATUS"
    elif grep -q "Skipping backend" "$LOG_FILE"; then
         B_TESTS="Skipped"
    fi
    printf "%-10s | %-20s | %-10s | %-10s\n" "Backend" "$B_TESTS" "$B_COV" "$BACKEND_TIME"

    # Auto-Fix
    if [[ "$AUTOFIX_TIME" != "-" ]]; then
        printf "%-10s | %-20s | %-10s | %-10s\n" "Auto-Fix" "Done" "-" "$AUTOFIX_TIME"
    fi
    
    echo "---------------------------------------------------------"
    if [[ -n "$TOTAL_COV" ]]; then
        printf "%-10s %24s %s code coverage in %s\n" "TOTAL" "" "${TOTAL_COV}%" "${TOTAL_TIME}"
    else
        printf "%-10s %24s %s in %s\n" "TOTAL" "" "-" "${TOTAL_TIME}"
    fi
    echo ""
} >&2


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


