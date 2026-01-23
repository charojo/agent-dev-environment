---
description: Guide the requirements and issues management process.
---

This workflow helps you manage `docs/REQUIREMENTS.md` and `docs/ISSUES.md`.

1. **Verify Documentation Existence**:
   - Ensure `docs/REQUIREMENTS.md` and `docs/ISSUES.md` exist.
   - If not, they should have been created by `configure.py`.

2. **Analysis Loop**:
   - Read the user's request.
   - If the user is proposing a **New Feature**:
     - Draft a new entry in `docs/REQUIREMENTS.md`.
     - Assign it a generic ID (e.g., REQ-XXX) until finalized.
   - If the user is reporting a **Bug/Issue**:
     - Check `docs/REQUIREMENTS.md` for the relevant requirement.
     - Log a new issue in `docs/ISSUES.md` linking to that requirement.

3. **Implementation**:
   - Implement the changes.
   - Update the `Status` and `Test Coverage` columns in `REQUIREMENTS.md` as you complete work.
   - Mark issues as [FIXED] in `ISSUES.md`.

4. **Validation**:
   - Ensure that every new requirement has a corresponding test case.
   - ensure that every fixed issue has a regression test if applicable.
