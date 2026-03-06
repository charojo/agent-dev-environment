---
description: Validate, stage, review, and commit changes
---

// turbo-all

1. Pre-check Branch & Status
   Verify you're on the correct branch and see what files changed.
   ```bash
   git branch --show-current && echo "---" && git status -s
   ```

2. Review Unstaged Changes
   Scan for oddities: debug files, corrupted names, files that shouldn't be committed.
   Look for `test_db.js`, `.env`, `node_modules/`, stale directories with their own `.git`.
   ```bash
   git status --short | grep '^??' | head -20
   ```

3. Stage Changes
   Stage intentionally — prefer targeted `git add <paths>` over `git add .` for large changesets.
   For routine commits, `git add .` is acceptable. For big features, stage by logical group.
   ```bash
   git add .
   ```

4. Review Staged Changes
   Final review of what will be committed. Check the file count and line stats.
   ```bash
   git diff --cached --stat | tail -5
   ```

5. Commit
   Use conventional commit format: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`.
   ```bash
   git commit -m "feat: description of changes"
   ```

6. Push
   Push to remote. Use `--set-upstream` if this is a new branch.
   ```bash
   git push
   ```