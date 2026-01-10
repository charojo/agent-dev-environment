---
description: Perform a basic security review of the project
---
1. Check for committed secrets (Basic Grep)
// turbo
grep -r "API_KEY" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude=.env || echo "No explicit API_KEY strings found in source."

2. Verify .env permissions (Linux/Mac)
// turbo
ls -l .env

3. List installed python dependencies for review
// turbo
uv pip list

4. List installed node dependencies for review
// turbo
cd src/web && npm list --depth=0
