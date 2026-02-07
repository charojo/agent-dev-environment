---
description: Triage and fix regression issues in an iterative loop
---

# 1. State Analysis & Transparency Log
- **Action**: Read `regression_analysis.md` and `logs/validation_summary_log`.
- **Transparency**: Generate a "Thought Artifact" named `Current_State_Analysis`.
- **Requirement**: List every error found in the log and cross-reference it with the existing FIXME list.

# 2. Conditional Triage (The "No Fixed Tasks" Branch)
- **Condition**: If NO issues in `regression_analysis.md` are marked "FIXED":
    - **Action**: Categorize all new errors from the log.
    - **Action**: Append them as numbered FIXME items to `regression_analysis.md`.
    - **Transparency**: Output a "Triage Report" Artifact. 
    - **STOP**: Do not proceed to fixing.

# 3. Environment Preparation (Backend Management)
- **Condition**: If an unfixed FIXME exists:
    - **Action**: Check if `start_dev` is running (e.g., `pgrep -f start_dev`).
    - **Action**: If running, restart it to ensure a clean state for the specific fix.
    - **Action**: If not running, start it using `./agent_env/bin/start_dev`.

# 4. Single-Task Execution
- **Action**: Select the HIGHEST priority unfixed FIXME.
- **Action**: Implement the fix for ONLY this task.
- **Transparency**: Create a "Code Change Plan" Artifact before editing files.

# 5. Verification & Documentation
- **Action**: Run `./agent_env/bin/validate.sh --exhaustive`.
- **Action**: If validation passes, update the specific FIXME status to "FIXED [timestamp]".
- **Action**: If validation fails, revert changes and mark the FIXME as "FAILED [error log]".