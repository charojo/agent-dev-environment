#!/usr/bin/env python3
"""
CSS Compliance Checker for Papeterie Engine.

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


def main():
    parser = argparse.ArgumentParser(description="Check CSS compliance")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--strict", action="store_true", help="Fail on any violation")
    args = parser.parse_args()

    components_dir = Path("src/web/src/components")
    if not components_dir.exists():
        print(f"Error: {components_dir} not found")
        sys.exit(1)

    report_lines = [
        "CSS Compliance Report",
        "====================",
        "",
    ]

    total_issues = 0
    color_issues = 0
    style_issues = 0
    override_issues = 0

    for jsx_file in sorted(components_dir.glob("*.jsx")):
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
            file_issues.append(f"  Excessive inline styles: {style_count} (threshold: {threshold})")

        # Check btn-icon overrides
        overrides = find_btn_icon_overrides(jsx_file)
        if overrides:
            override_issues += len(overrides)
            file_issues.append(f"  btn-icon overrides ({len(overrides)}):")
            for line_no, desc in overrides[:3]:
                file_issues.append(f"    L{line_no}: {desc}")
            if len(overrides) > 3:
                file_issues.append(f"    ... and {len(overrides) - 3} more")

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
    report_lines.append("")

    if color_issues == 0 and style_issues == 0 and override_issues == 0:
        report_lines.append("✅ All checks passed!")
        exit_code = 0
    else:
        report_lines.append("⚠️  Issues found - review recommended")
        exit_code = 1 if args.strict else 0

    report = "\n".join(report_lines)

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
