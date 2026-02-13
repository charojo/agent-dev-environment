---
description: Validate, stage, review, and commit changes
---

1. Pre-check Status
   See what will be validated.
   // turbo
   git status -s

2. Run Validation
   Ensure the codebase is stable.
   // turbo
   ./agent_env/bin/validate.sh --full

3. Stage Changes
   Stage all changes (Review output of Step 1 first!).
   // turbo
   git add .

4. Review Staged Changes
   Final review before committing.
   // turbo
   git diff --cached --stat

5. Commit
   Commit with a clear message (e.g., "Fixing: description" or "Feat: description").
   git commit -m "message"