import argparse
import re
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Parse validation logs for failures.")
    parser.add_argument("log_file", type=Path, help="Path to the validation log file")
    return parser.parse_args()


def extract_backend_failures(content):
    failures = []
    # Pattern for short summary info: FAILED tests/... - ErrorType: ...
    # But sometimes we want the detailed FAILURES section.
    # Let's try to grab from "FAILURES" section first if it exists.

    if "FAILURES" in content:
        # Regex to find "________________ test_name ________________"
        # and capture the error message that follows eventually
        # This is hard to robustly regex multiline.
        # Fallback to short test summary info which is cleaner.
        pass

    # Look for "FAILED test_path::test_name - ErrorType: message"
    summary_pattern = re.compile(r"FAILED\s+(.*?)::(.*?)\s+-\s+(.*)")
    for match in summary_pattern.finditer(content):
        test_file, test_name, error_msg = match.groups()
        failures.append(
            {
                "category": "Backend",
                "test": f"{test_name} ({test_file})",
                "error": error_msg.strip(),
            }
        )

    return failures


def extract_frontend_failures(content):
    failures = []
    # Vitest output:
    # stderr | path/to/test.js > Test Suite > Test Name > ...
    # [time] [Component] Error message

    # Or "FAIL type"

    # Pattern for stderr capture
    stderr_pattern = re.compile(r"stderr\s+\|\s+(.*?)\n(.*?)(?=\n|stderr|✓|×)", re.DOTALL)
    for match in stderr_pattern.finditer(content):
        test_path = match.group(1).strip()
        error_chunk = match.group(2).strip()

        # Clean up error chunk - take first non-empty line usually
        error_lines = [line.strip() for line in error_chunk.split("\n") if line.strip()]
        error_msg = error_lines[0] if error_lines else "Unknown error"

        # Limit error length
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."

        failures.append({"category": "Frontend", "test": test_path, "error": error_msg})

    return failures


def extract_e2e_failures(content):
    failures = []
    # Playwright output:
    # 1) x [chromium] > path/to/test.spec.js:line:col > Suite > Test Name
    # 2) Error message

    # Simple grep for "x [chromium]" or similar?
    # The log file has: "  ✓   1 [chromium] ..." for pass.
    # Failures might look different.

    # Also check for "Timed out"
    if "E2E wrapper timed out" in content:
        failures.append(
            {
                "category": "E2E",
                "test": "Global Wrapper",
                "error": "Timed out waiting for server/tests",
            }
        )

    # Pattern: ✕  1 [chromium] › path/to/file.js:line:col › ...
    # or just look for "failed" in the summary lines

    # Attempt to capture failed lines
    # Playwright list reporter:
    #   x  1 [chromium] › ...
    # (Note: it might be an 'x' or unicode cross)

    failed_lines = re.findall(r"^\s*[xX✕]\s+.*?\[chromium\].*?›\s+(.*)", content, re.MULTILINE)
    for line in failed_lines:
        parts = line.split("›")
        test_name = parts[-1].strip() if parts else "Unknown Test"
        failures.append({"category": "E2E", "test": test_name, "error": "See logs for details"})

    return failures


def main():
    args = parse_args()
    if not args.log_file.exists():
        print(f"Error: Log file {args.log_file} not found.")
        return

    content = args.log_file.read_text(encoding="utf-8")

    all_failures = []

    # Split content by sections to avoid overlapping matches?
    # Actually, simpler to just search whole file but be careful with regex

    all_failures.extend(extract_backend_failures(content))
    all_failures.extend(extract_frontend_failures(content))
    all_failures.extend(extract_e2e_failures(content))

    if not all_failures:
        return

    # Markdown output to stdout (for log file)
    print("\n## Failure Summary")
    print("| Category | Test | Error |")
    print("| :--- | :--- | :--- |")

    for fail in all_failures:
        # Escape pipes in markdown table
        test_sanitized = fail["test"].replace("|", "\\|")
        error_sanitized = fail["error"].replace("|", "\\|")
        print(f"| {fail['category']} | {test_sanitized} | {error_sanitized} |")
    print("")

    # ASCII output to stderr (for terminal)
    import sys

    # Calculate column widths
    cat_width = max(len("Category"), max(len(f["category"]) for f in all_failures))
    test_width = max(len("Test"), max(len(f["test"]) for f in all_failures))
    # Cap error width to avoid huge tables, say 80 chars
    err_width = min(80, max(len("Error"), max(len(f["error"]) for f in all_failures)))

    # Header
    header = (
        f"| {str('Category').ljust(cat_width)} | "
        f"{str('Test').ljust(test_width)} | "
        f"{str('Error').ljust(err_width)} |"
    )
    separator = f"| {'-' * cat_width} | {'-' * test_width} | {'-' * err_width} |"

    print("\n=== Failure Summary (ASCII) ===", file=sys.stderr)
    print(separator, file=sys.stderr)
    print(header, file=sys.stderr)
    print(separator, file=sys.stderr)

    for fail in all_failures:
        cat = fail["category"].ljust(cat_width)
        test = fail["test"].ljust(test_width)
        err = fail["error"]
        if len(err) > err_width:
            err = err[: err_width - 3] + "..."
        err = err.ljust(err_width)

        print(f"| {cat} | {test} | {err} |", file=sys.stderr)

    print(separator, file=sys.stderr)
    print("", file=sys.stderr)


if __name__ == "__main__":
    main()
