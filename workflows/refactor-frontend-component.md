---
description: Guide to refactoring a legacy frontend component into the new feature-based architecture.
---

This workflow guides you through the process of refactoring a legacy component (typically found in `src/components`) into the new `src/features` architecture.

## 1. Preparation

First, identify the target component and its logical feature owner.

1.  **Select Component**: Identify the file to refactor (e.g., `src/web/src/components/TheatreStage.jsx`).
2.  **Identify Feature**: Determine which feature it belongs to:
    *   `editor` (Core editing experience)
    *   `library` (Asset management)
    *   `auth` (User management)
    *   `settings` (Configuration)
3.  **Verify Destination**: Ensure the directory exists.
    ```bash
    mkdir -p src/web/src/features/<feature_name>/components
    mkdir -p src/web/src/features/<feature_name>/hooks
    ```

## 2. Analysis & Extraction

Before moving the file, analyze its content.

1.  **Check for "God Mode"**: Does the component handle data fetching?
    *   **Yes**: Extract fetching logic to a custom hook in `src/features/<feature_name>/hooks/use<ComponentName>Data.js`.
2.  **Check for Inline Styles**: Run `grep "style="{{"` on the file.
    *   **Action**: Convert static styles to CSS classes or utility classes.
3.  **Check for Hardcoded Colors**: Run `grep "#"`.
    *   **Action**: Replace with `var(--color-*)`.

## 3. The Move

1.  **Move the File**:
    ```bash
    mv src/web/src/components/OldComponent.jsx src/web/src/features/<feature_name>/components/OldComponent.jsx
    ```
    *(Ideally, rename it to something more specific if needed).*

2.  **Update Imports**:
    *   Update the component's internal imports (relative paths will break).
    *   Update all consumers of this component to point to the new location.
    *   *Tip*: Use `grep -r "OldComponent" src/web/src` to find usages.

## 4. Cleanup

1.  **Extract Sub-Components**: If the file is > 200 lines, look for render functions (e.g., `renderToolbar()`) and extract them into separate files in the same directory.
2.  **Verify Tests**: Ensure existing tests are moved and updated.
    ```bash
    mv src/web/src/components/__tests__/OldComponent.test.jsx src/web/src/features/<feature_name>/components/__tests__/
    ```
    *Update import paths in the test file.*

## 5. Verification

1.  Run the application and verify the component still works.
2.  Run strict architecture checks:
    *   [ ] No `style={{}}` (static).
    *   [ ] No Hardcoded colors.
    *   [ ] File size < 200 lines (or significantly reduced).
