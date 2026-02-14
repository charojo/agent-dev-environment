---
description: Perform a basic security review of the project
---
1. Check for committed secrets (Basic Grep)
// turbo
grep -r "API_KEY" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude=.env || echo "No explicit API_KEY strings found in source."

2. Verify .env permissions (Recommended setup is one level above root)
// turbo
ls -l .env ../.env 2>/dev/null || echo ".env not found in root or parent directory"

3. List installed python dependencies for review
// turbo
uv pip list

4. List installed node dependencies for review
// turbo
if [ -d "src/web" ]; then cd src/web && npm list --depth=0; else echo "No web project found in src/web"; fi
