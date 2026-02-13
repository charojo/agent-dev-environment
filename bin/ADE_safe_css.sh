#!/bin/bash
# ## @DOC
# ### Ade Safe Css
# Validates CSS files against Safe CSS standards.

# agent_env/bin/ADE_safe_css.sh
# "Turbo" workflow for safe CSS refactoring.
# 1. Checks system health (Backend + Frontend)
# 2. Runs Visual Regression Tests (Playwright)
# 3. Reports status

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Resolve Script Directory to call sibling scripts robustly
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")" # agent_env/bin -> agent_env -> root? 
# Actually, if agent_env is at root, then SCRIPT_DIR is <root>/agent_env/bin
# So dirname(SCRIPT_DIR) is <root>/agent_env
# dirname(dirname(SCRIPT_DIR)) is <root>
# Structure: <root>/agent_env/bin

# 1. Health Check
"$SCRIPT_DIR/ADE_check_health.sh"
HEALTH_STATUS=$?

if [ $HEALTH_STATUS -ne 0 ]; then
    echo -e "${RED}❌ System Health Check Failed. Aborting CSS validation.${NC}"
    exit 1
fi

echo ""
echo "🔍 Running CSS Compliance Checks..."
"$SCRIPT_DIR/ADE_check_css_compliance.py"
COMPLIANCE_STATUS=$?

if [ $COMPLIANCE_STATUS -ne 0 ]; then
    echo -e "${RED}❌ CSS Compliance Check Failed.${NC}"
    # We don't exit here immediately if we want to run visual tests too, 
    # but strictly "Safe CSS" implies compliance is required.
    # Let's run visual tests anyway to get full picture? 
    # Or fail fast? User said "Keep running it until it flags...". 
    # Usually safer to fail.
    exit 1
fi

echo ""
echo "🎨 Running Visual Regression Tests..."

# 2. Run Specific CSS Safety Tests in Project Root
# We assume the project adhering to this agent_env has src/web/e2e/css_safety.spec.js
# path might need to be configurable but for now we hardcode for this repo structure.

cd "$PROJECT_ROOT"

if [ ! -f "src/web/e2e/css_safety.spec.js" ]; then
    echo -e "${RED}❌ Could not find 'src/web/e2e/css_safety.spec.js'.${NC}"
    echo "This workflow requires the project to have the specific safety tests implemented."
    exit 1
fi

if cd src/web && npx playwright test e2e/css_safety.spec.js; then
    echo ""
    echo -e "${GREEN}✅ CSS Safety Checks PASSED.${NC}"
    echo "   No visual regressions detected."
    exit 0
else
    echo ""
    echo -e "${RED}❌ CSS Safety Checks FAILED.${NC}"
    echo "   Visual regressions or errors detected."
    echo "   Opening report..."
    echo "   Report available at: src/web/playwright-report/index.html"
    exit 1
fi
