---
description: Review CSS compliance, design system usage, and run Safe CSS validation
---

This workflow consolidates CSS validation into a single process. It verifies that:
1.  **Safety**: Layouts are robust and colors/counts are within limits.
2.  **Compliance**: No hardcoded hex/rgb values, and inline styles are minimized.
3.  **Cleanliness**: Unused CSS classes are identified and removed.

## 1. Automated Validation (Safe CSS)

Run the master compliance script to check all rules (limits, hardcoded values, unused CSS).

// turbo
```bash
./agent_env/bin/ADE_check_css_compliance.py
```

To automatically remove unused CSS classes found by the script:
```bash
./agent_env/bin/ADE_check_css_compliance.py --fix
```

### Contrast & Background Validation
The workflow validates "common background look and feel" by flagging opacity modifiers on structural tokens (e.g. `bg-bg-base/50`).
Run this until it flags known issues like the Settings background or Contrast widget:
```bash
# Verify specific components are flagged
./scripts/check_css_compliance.py | grep -C 5 "SettingsMenu"
```

---

## 2. Manual Review Guidelines

Even with automation, brief usage of the codebase should be reviewed for architectural alignment.

### Zero-Tolerance for Hardcoded Colors
All colors must use `var(--color-*)` CSS variables defined in `index.css`.

### Atomic Inline Style Rule
Components should not exceed 15 inline style properties. If they do, refactor to `index.css` classes or Tailwind utilities.

### Schema-Driven UI Validation
Verify that `PropertyInspector` and other schema-driven views (defined via YAML) correctly inherit design tokens rather than applying bespoke styles.

### Utility-First & Component Check
*   **Utility-First**: Are new layout/spacing styles implemented using Tailwind/Utility classes rather than new custom CSS classes?
*   **Component Library**: Use standard `components/` structures (e.g., `DeleteConfirmationDialog`) instead of creating from scratch.

---

## 3. Summary Report for PRs

* [ ] **Automated Check Passed**: `check_css_compliance.py` returns success.
* [ ] **Unused CSS**: No unused classes remain (or have been auto-fixed).
* [ ] **Schema Compliance**: `PropertyInspector` uses standard design tokens.
* [ ] **A11y Standards**: Contrast checks pass for all new UI elements.
