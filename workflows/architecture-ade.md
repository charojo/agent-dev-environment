---
description: Architectural Changes and Big Feature Implementations
model: claude-3-5-sonnet
---
1. Start by analyzing the current architecture and codebase structure.
2. Create or update a design document in `docs/design/` outlining the proposed architectural changes.
3. Review the proposed changes with the user to ensure alignment with project goals.
4. Break down the implementation into smaller, manageable steps (using `task.md` or similar).
5. Proceed with implementation only after the design is approved.
6. Ensure that changes are backward compatible or that migration paths are documented.

## Frontend Checklist (Strict)

When proposing changes to the Frontend (`src/web`):

*   [ ] **Feature Isolation**: Does this code belong in a `src/features/<name>` directory? (Avoid polluting `src/components`).
*   [ ] **Dumb UI**: If creating a generic UI component (Button, Card), is it purely presentational and in `src/components/ui`?
*   [ ] **No God Components**: Is the new file under 200 lines of code? If not, plan the split immediately.
*   [ ] **Design System Compliance**: Are you using `var(--color-*)`? (No hex codes allowed).
*   [ ] **State Sanity**: If using `useEffect` for data fetching, are you using React Query instead?

