---
description: Review CSS compliance and design system usage before merging
---

This workflow validates that CSS follows the design system conventions. Run before merging UI changes.

## 1. Check for Hardcoded Colors in JSX

Run these grep searches to find hardcoded colors in React components:

```bash
# Find hardcoded rgba() values
grep -r "rgba(" src/web/src/components/*.jsx --include="*.jsx" | grep -v node_modules

# Find hardcoded hex colors (excluding CSS files)
grep -rE "#[0-9a-fA-F]{3,6}" src/web/src/components/*.jsx --include="*.jsx" | grep -v node_modules
```

**Expected**: All colors should use `var(--color-*)` CSS variables from `index.css`.

## 2. Audit Inline Style Usage

Count components with excessive inline styles:

```bash
# Count style={{ occurrences per file
for f in src/web/src/components/*.jsx; do
  count=$(grep -c "style={{" "$f" 2>/dev/null || echo 0)
  if [ "$count" -gt 15 ]; then
    echo "⚠️  $f has $count inline styles (consider refactoring)"
  fi
done
```

**Threshold**: Components with >15 inline styles should be reviewed for CSS class extraction.

## 3. Validate btn-icon Consistency

Check that `.btn-icon` buttons don't override hover behavior:

```bash
# Find btn-icon buttons with inline background/color overrides
grep -A5 'className="btn-icon"' src/web/src/components/*.jsx | grep -E "(background|color):"
```

**Expected**: `btn-icon` should not have inline `background:` or `color:` overrides (hover won't work properly).

## 4. Run Automated Checks

// turbo
../bin/check_css_compliance.py

// turbo
../bin/check_contrast.py

## 5. Cross-Reference Design Tokens

Verify new components use existing tokens from `index.css`:

| Token Category | Variables |
|----------------|-----------|
| Backgrounds | `--color-bg-base`, `--color-bg-surface`, `--color-bg-elevated`, `--color-bg-surface-glass` |
| Text | `--color-text-main`, `--color-text-muted`, `--color-text-subtle` |
| Borders | `--color-border`, `--color-border-muted` |
| Accent | `--color-primary`, `--color-primary-glow` |
| Danger | `--color-danger`, `--color-danger-muted` |

## 6. Summary Report

After completing the checks, produce a brief summary:

- [ ] No hardcoded colors found (or justified exceptions documented)
- [ ] Inline style count reasonable (<15 per component)
- [ ] btn-icon hover effects preserved
- [ ] Contrast standards pass
- [ ] New components use existing design tokens
