---
description: Cleanup system files, caches, and logs
---
1. Remove Python caches
// turbo
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +

2. Remove Node caches and artifacts
// turbo
if [ -d "src/web" ]; then rm -rf src/web/coverage src/web/dist; fi
# Optional: rm -rf src/web/node_modules/.vite

3. Remove Logs
// turbo
rm -f logs/*.log
