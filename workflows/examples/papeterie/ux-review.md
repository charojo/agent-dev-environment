---
description: Perform a UX and Accessibility Review of the application
---

1. **Check Contrast Ratios**:
   - Verify that all text has sufficient contrast against its background (WCAG AA requires 4.5:1 for normal text).
   - Check enabled buttons and interactive elements for visibility.
   - Use `view_file` on `index.css` to check theme color definitions if needed.

2. **Verify Semantic HTML**:
   - Ensure buttons are `<button>`, links are `<a>`.
   - Check that `<img>` tags have meaningful `alt` text.
   - Verify that inputs have associated labels (visible or `aria-label`).
   - Run `grep_search` for `div onClick` or similar anti-patterns.

3. **Keyboard Navigation**:
   - Verify `tabIndex` usage. Ensure focusable elements are reachable.
   - Check if focus styles are visible (outline/ring).

4. **Dynamic Font Scaling**:
   - Check if the UI adapts to font size changes (using `rem` instead of `px`).
   - Identify hardcoded `px` font sizes in components.

5. **Theme Compliance**:
   - Ensure no hardcoded hex colors are used for text or backgrounds.
   - All colors should use `var(--color-...)` variables.

6. **Summary**:
   - Produce a brief report of findings.
