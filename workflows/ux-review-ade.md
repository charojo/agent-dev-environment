---
description: Perform a UX and Accessibility Review of the application
---

This review ensures that the application views remain accessible, navigable, and consistent with design standards.

## 1. Schema-Driven Field Accessibility
Every input field generated dynamically from `layer-schema.yaml` must be accessible.
- **Labeling**: Every input must have a visible `<label>` or an `aria-label`. 
- **Validation**: `grep -L "aria-label" src/web/src/components/PropertyField.jsx` (Should return nothing).

## 2. Semantic HTML & Keyboard Navigation
Avoid "div-soup." Use the correct HTML elements to ensure keyboard users can navigate the engine.
- **Interactive Elements**: Use `<button>` for actions and `<a>` for navigation.
- **Anti-pattern Check**: Run `grep -r "onClick" src/web/src/components/ | grep "div"`. 
- **Requirement**: Replace any `div onClick` with a semantic `<button type="button">`.

## 3. The "Selection Bridge" & Focus
When an object is selected on the Stage (the canvas), the focus must be handled correctly in the UI.
- **Visual Cues**: Focusable elements must have a visible ring using `--color-primary-glow`.
- **Sync**: Ensure that selecting a layer updates the focus in the `LayerPanel` for immediate keyboard interaction.

## 4. Responsive Scaling
The UI must adapt to various screen sizes and user font settings.
- **Units**: Use `rem` for all `font-size` and `padding` instead of `px`.
- **Audit**: `grep "px" src/web/src/components/*.jsx | grep "font-size"` should yield zero results.

## 5. Contrast & Visual Hierarchy
- **Text Contrast**: Normal text must maintain a 4.5:1 ratio against backgrounds (WCAG AA).
- **Themes**: Verify that both light and dark variants (if applicable) respect the `--color-text-muted` contrast requirements.

## 6. Layout Safety (Interactive Areas)
Verify that critical actions are safe to use.
- **On-Screen**: Actions must never be pushed off-screen.
- **Separation**: Critical actions (Search vs Cancel) must be separated by at least `8px`.
- **Viewport**: No critical interactive element should be clipped.

## 7. Summary Report
Produce a brief report of findings:
- [ ] All schema-generated inputs are labeled.
- [ ] No semantic anti-patterns (`div onClick`) found.
- [ ] Focus styles are visible and use design tokens.
- [ ] Font sizes use `rem` for scaling.
- [ ] Contrast standards pass via automated check.
- [ ] Layout safety verified (no off-screen actions, clear separation).