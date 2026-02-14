---
description: Update Open Source License Information
---

# License Compliance Update

This workflow updates the `licenses.json` file used by the application to display open source license credits. It aggregates license information from both frontend (npm) and backend (python) dependencies.

## Triggers
- When `package-lock.json` changes
- When `uv.lock` changes
- When `pyproject.toml` changes
- When `package.json` changes

## Steps

1. **Update Licenses**
   Run the update script which generates frontend and backend licenses and merges them.
   
   ```bash
   ./agent_env/bin/ADE_update_licenses.py
   ```
   
   // turbo
   
2. **Verify Output**
   Check if the output file exists.
   
   ```bash
   ls -l licenses.json src/web/src/features/settings/licenses.json 2>/dev/null || true
   ```

3. **Commit Changes**
   If there are changes, commit them.
   
   ```bash
   git add licenses/ licenses.json src/web/src/features/settings/licenses.json 2>/dev/null || true
   git commit -m "chore: update open source license credits"
   ```
