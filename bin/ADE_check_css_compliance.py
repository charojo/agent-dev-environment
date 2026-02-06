#!/usr/bin/env python3
"""
CSS Compliance Checker.

Scans JSX components for design system violations:
- Hardcoded rgba() colors
- Hardcoded hex colors
- Excessive inline styles
- btn-icon hover overrides
"""

import argparse
import re
import sys
from pathlib import Path

# Allowed exceptions (documented acceptable hardcoded colors)
ALLOWED_PATTERNS = [
    r"rgba\(0,\s*0,\s*0,\s*0\)",  # Transparent
    r"rgba\(255,\s*255,\s*255,\s*0\)",  # Transparent white
]

# Components allowed to have more inline styles (canvas overlays, etc.)
INLINE_STYLE_EXCEPTIONS = [
    "TheatreStage.jsx",  # Canvas overlay - needs refactoring
]

# Valid background tokens (strict)
VALID_BG_TOKENS = {
    "bg-bg-base",
    "bg-bg-surface",
    "bg-bg-elevated",
    "bg-bg-base-raw",
    "bg-primary",
    "bg-danger",
    "bg-transparent",
    "bg-accent",
}

# Tokens that are explicitly allowed to have opacity modifiers (uncommon, but sometimes needed)
ALLOWED_OPACITY_TOKENS = {"bg-black", "bg-white"}


def find_hardcoded_colors(file_path: Path) -> list[tuple[int, str, str]]:
    """Find hardcoded color values in a file."""
    issues = []
    content = file_path.read_text()
    lines = content.split("\n")

    # Patterns for hardcoded colors
    rgba_pattern = re.compile(r"rgba?\([^)]+\)")
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,6}\b")

    for i, line in enumerate(lines, 1):
        # Skip comments and imports
        if line.strip().startswith("//") or line.strip().startswith("import"):
            continue

        # Check for rgba
        for match in rgba_pattern.finditer(line):
            color = match.group()
            # Skip allowed patterns
            if any(re.match(p, color) for p in ALLOWED_PATTERNS):
                continue
            issues.append((i, "rgba", color))

        # Check for hex (only in style contexts)
        if "style" in line.lower() or "color" in line.lower():
            for match in hex_pattern.finditer(line):
                color = match.group()
                issues.append((i, "hex", color))

    return issues


def count_inline_styles(file_path: Path) -> int:
    """Count style={{ occurrences in a file."""
    content = file_path.read_text()
    return len(re.findall(r"style=\{\{", content))


def find_btn_icon_overrides(file_path: Path) -> list[tuple[int, str]]:
    """Find btn-icon elements with inline style overrides."""
    issues = []
    content = file_path.read_text()
    lines = content.split("\n")

    in_btn_icon = False
    brace_count = 0

    for i, line in enumerate(lines, 1):
        if 'className="btn-icon"' in line or "className='btn-icon'" in line:
            in_btn_icon = True
            brace_count = 0

        if in_btn_icon:
            brace_count += line.count("{") - line.count("}")

            # Check for problematic overrides
            if re.search(r"(background|backgroundColor)\s*:", line):
                issues.append((i, f"btn-icon background override: {line.strip()[:60]}"))
            if re.search(r"color\s*:\s*['\"]?(#|rgba?|white|black)", line):
                issues.append((i, f"btn-icon color override: {line.strip()[:60]}"))

            if brace_count <= 0:
                in_btn_icon = False

    return issues


def find_background_violations(file_path: Path) -> list[tuple[int, str]]:
    """
    Find background class violations.
    - Disallow opacity modifiers on structural tokens (e.g. bg-bg-base/50)
    - Suggest standard tokens
    """
    issues = []
    content = file_path.read_text()
    lines = content.split("\n")

    # Regex to find class names like 'bg-foo' or 'bg-foo/50'
    # Captures: 1=full_class, 2=base_name, 3=opacity_part (optional)
    bg_pattern = re.compile(r"\b(bg-([a-z0-9-]+)(/[a-z0-9]+)?)\b")

    for i, line in enumerate(lines, 1):
        # Skip comments/imports
        if line.strip().startswith("//") or line.strip().startswith("import"):
            continue

        for match in bg_pattern.finditer(line):
            full_class = match.group(1)
            base_name = f"bg-{match.group(2)}"
            opacity = match.group(3)

            # Check for opacity violations
            if opacity and base_name not in ALLOWED_OPACITY_TOKENS:
                # If it's a structural token ensuring contrast, opacity breaks it
                if base_name in VALID_BG_TOKENS or "bg-bg-" in base_name:
                    issues.append(
                        (
                            i,
                            f"Opacity modifier forbidden on structural token: {full_class}",
                        )
                    )

            # Check for non-standard backgrounds (soft check)
            # if base_name not in VALID_BG_TOKENS and base_name not in ALLOWED_OPACITY_TOKENS:
            #     # Optional: Strict mode could flag this
            #     pass

    return issues


def clean_unused_comments(index_css_path: Path):
    """Remove comments marking unused/removed CSS."""
    if not index_css_path.exists():
        return

    content = index_css_path.read_text()
    # Pattern: /* UNUSED REMOVED: ... */ with optional surrounding whitespace
    # We want to remove the whole line if it's just this comment, or just the comment if inline

    # Simple approach: Remove lines that contain ONLY this comment type
    lines = content.split("\n")
    new_lines = []
    cleaned_count = 0

    unused_pattern = re.compile(r"^\s*/\*\s*UNUSED REMOVED:.*?\*/\s*$")

    for line in lines:
        if unused_pattern.match(line):
            cleaned_count += 1
            continue  # Skip this line
        new_lines.append(line)

    if cleaned_count > 0:
        index_css_path.write_text("\n".join(new_lines))
        print(f"🧹 Removed {cleaned_count} unused CSS comment lines from index.css")
    else:
        print("✨ No unused CSS comments found.")


def scan_for_duplicate_css_rules(file_path: Path) -> list[str]:
    """
    Find duplicate CSS selectors in a file.
    Note: This is a simple-ish parser that assumes standard formatting.
    """
    issues = []
    content = file_path.read_text()

    # Remove comments to avoid false positives
    content_no_comments = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Split by '}' to find blocks
    # This is a heuristic: it finds "selector { body }"
    # We want to catch repeated selectors.

    # Regex to find selectors followed by {
    # Limitations: doesn't handle nested braces (media queries) perfectly yet
    # But checking scanning top-level or typical CSS structure

    selector_pattern = re.compile(r"([^{]+)\{")

    # We'll just track seen selectors in order
    # To be robust against media queries, we might need a better parser,
    # but let's try a line-based approach for simple "duplicate entires" first
    # or just regex finding "selector {" matches?

    # Let's try a regex that captures non-whitespace selectors
    # We strip whitespace to normalize
    # We strip whitespace to normalize
    matches = selector_pattern.findall(content_no_comments)

    # Filter and clean
    # We need to be careful about @media

    # We strip whitespace to normalize
    matches = selector_pattern.findall(content_no_comments)

    # Count occurrences
    from collections import Counter

    selector_counts = Counter(matches)

    for selector, count in selector_counts.items():
        if count > 1:
            # Basic check: if the selector appears twice, we flag it.
            # Ideally we'd track context (media query).
            pass

    # Let's look for EXACT textual duplicates of selectors in the file.
    # We will use a regex that finds `selector {` and check if `selector` appears multiple times.

    # Refined Regex: `^([.#][a-zA-Z0-9_-]+)\s*\{` (classes/ids at start of line)
    top_level_selector_re = re.compile(
        r"^\s*([.#a-zA-Z][a-zA-Z0-9_\s:>-]+)\s*\{", re.MULTILINE
    )

    found = []
    for match in top_level_selector_re.finditer(content_no_comments):
        sel = match.group(1).strip()
        found.append(sel)

    import collections

    counts = collections.Counter(found)

    for sel, count in counts.items():
        if count > 1:
            issues.append(f"Duplicate selector found: '{sel}' appeared {count} times")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Check CSS compliance")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    args = parser.parse_args()

    # Define source directories
    src_dir = Path("src/web/src")
    if not src_dir.exists():
        print(f"Error: {src_dir} not found")
        sys.exit(1)

    # Handle fixes first
    if args.fix:
        # 1. Clean unused comments
        index_css = src_dir / "index.css"
        clean_unused_comments(index_css)
        # Future: Auto-fix other things logic here

    report_lines = [
        "CSS Compliance Report",
        "====================",
        "",
    ]

    total_issues = 0
    color_issues = 0
    style_issues = 0
    override_issues = 0
    override_issues = 0
    bg_issues = 0
    css_dupe_issues = 0

    # 2. Check index.css for duplicates
    index_css = src_dir / "index.css"
    if index_css.exists():
        dupes = scan_for_duplicate_css_rules(index_css)
        if dupes:
            css_dupe_issues = len(dupes)
            report_lines.append(f"📄 {index_css.name}")
            report_lines.append(f"  Duplicate CSS Selectors ({len(dupes)}):")
            for d in dupes[:5]:
                report_lines.append(f"    {d}")
            if len(dupes) > 5:
                report_lines.append(f"    ... and {len(dupes) - 5} more")
            report_lines.append("")
            total_issues += 1

    for jsx_file in sorted(src_dir.rglob("*.jsx")):
        file_issues = []

        # Check hardcoded colors
        colors = find_hardcoded_colors(jsx_file)
        if colors:
            color_issues += len(colors)
            file_issues.append(f"  Hardcoded colors ({len(colors)}):")
            for line_no, color_type, color in colors[:5]:  # Show first 5
                file_issues.append(f"    L{line_no}: {color_type} - {color}")
            if len(colors) > 5:
                file_issues.append(f"    ... and {len(colors) - 5} more")

        # Check inline style count
        style_count = count_inline_styles(jsx_file)
        threshold = 30 if jsx_file.name in INLINE_STYLE_EXCEPTIONS else 15
        if style_count > threshold:
            style_issues += 1
            file_issues.append(
                f"  Excessive inline styles: {style_count} (threshold: {threshold})"
            )

        # Check btn-icon overrides
        overrides = find_btn_icon_overrides(jsx_file)
        if overrides:
            override_issues += len(overrides)
            file_issues.append(f"  btn-icon overrides ({len(overrides)}):")
            for line_no, desc in overrides[:3]:
                file_issues.append(f"    L{line_no}: {desc}")
            if len(overrides) > 3:
                file_issues.append(f"    ... and {len(overrides) - 3} more")

        # Check background violations
        bg_violations = find_background_violations(jsx_file)
        if bg_violations:
            bg_issues += len(bg_violations)
            file_issues.append(f"  Background/Contrast Risks ({len(bg_violations)}):")
            for line_no, desc in bg_violations[:3]:
                file_issues.append(f"    L{line_no}: {desc}")
            if len(bg_violations) > 3:
                file_issues.append(f"    ... and {len(bg_violations) - 3} more")

        if file_issues:
            total_issues += 1
            report_lines.append(f"📄 {jsx_file.name}")
            report_lines.extend(file_issues)
            report_lines.append("")

    # Summary
    report_lines.append("Summary")
    report_lines.append("-------")
    report_lines.append(f"Files with issues: {total_issues}")
    report_lines.append(f"Hardcoded color occurrences: {color_issues}")
    report_lines.append(f"Components exceeding inline style threshold: {style_issues}")
    report_lines.append(f"btn-icon override violations: {override_issues}")
    report_lines.append(f"Background/Contrast risks: {bg_issues}")
    report_lines.append("")

    report_lines.append(f"btn-icon override violations: {override_issues}")
    report_lines.append(f"Background/Contrast risks: {bg_issues}")
    report_lines.append(f"Duplicate CSS selector risks: {css_dupe_issues}")
    report_lines.append("")

    if (
        color_issues == 0
        and style_issues == 0
        and override_issues == 0
        and bg_issues == 0
        and css_dupe_issues == 0
    ):
        report_lines.append("✅ All checks passed!")
        exit_code = 0
    else:
        report_lines.append("⚠️  Issues found - validation failed")
        exit_code = 1

    report = "\n".join(report_lines)

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
