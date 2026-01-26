---
description: Guide the requirements and issues management process.
---

This workflow helps you manage `docs/REQUIREMENTS.md` and `docs/ISSUES.md`.

1. **Verify Documentation Existence**:
   - Ensure `docs/REQUIREMENTS.md` and `docs/ISSUES.md` exist.
   - If not, they should have been created by `configure.py`.

2. **Analysis Loop**:
   - Read the user's request.
   - **Check Design Docs**: Search `docs/design/` for any existing specs relevant to the request.
   - If the user is proposing a **New Feature**:
     - Draft a new entry in `docs/REQUIREMENTS.md`.
     - Assign it a generic ID (e.g., REQ-XXX) until finalized.
     - Fill the `Design Source` column with the relevant design doc or "None".
   - If the user is reporting a **Bug/Issue**:
     - Check `docs/REQUIREMENTS.md` for the relevant requirement.
     - Log a new issue in `docs/ISSUES.md` linking to that requirement.

3. **Implementation**:
   - Implement the changes (BDD style - write tests first).
   - Update the `Status` column in `REQUIREMENTS.md`.
   - **Update Test Coverage**: You MUST populate the `Test Coverage` column with the specific path to the test file (e.g., `tests/test_foo.py`).
   - Mark issues as [FIXED] in `ISSUES.md`.

4. **Validation**:
   - Ensure that every new requirement has a corresponding test case.
   - ensure that every fixed issue has a regression test if applicable.
