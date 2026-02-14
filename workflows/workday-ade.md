---
description: Start a turbo workday session to work on design tasks and run validation
---

---
task: turbo-all
mode: autonomous
review_policy: always_proceed
terminal_policy: turbo
---

Directive: Autonomous Mode Enabled "You are in autonomous execution mode. Do not wait for user confirmation between cycles. Your objective is to exhaust the task list in architecture_review.md. Every time validate.sh passes, immediately proceed to the next item. If you encounter a token limit error, save your current state to RECOVERY.md and exit."

1. **Review Design Requirements**:
   - Read files in `docs`.
   - Identify the next unimplemented recommendation or feature.

2. **Implement Changes**:
   - Perform the necessary code changes for *one* task/milestone.
   - Use your tools to list files, read code, and write changes.

3. **Validate**:
   ```bash
   ./agent_env/bin/validate.sh --exhaustive
   ```

4. **Repeat**:
   - If validation fails, fix the errors and re-run validation.
   - When validation passes, update the progress in the files in docs and replace any implemented code snippets with paths to the files they were added, and then run operations in .agents/workflows/commit_ade. 
   - Continue this loop by returning to step 1 until user intervenes or tokens are exhausted.