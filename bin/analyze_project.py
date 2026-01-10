#!/usr/bin/env python3
import os
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"


def count_lines(file_path):
    """Count lines of code, stripping empty lines and comments (basic)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        code_lines = 0
        todos = 0
        fixmes = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("//"):
                if "TODO" in stripped:
                    todos += 1
                if "FIXME" in stripped:
                    fixmes += 1
                continue

            code_lines += 1
            if "TODO" in line:
                todos += 1
            if "FIXME" in line:
                fixmes += 1

        return code_lines, todos, fixmes
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, 0, 0


def analyze_directory(directory, extension):
    total_loc = 0
    total_todos = 0
    total_fixmes = 0
    file_count = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                path = Path(root) / file
                loc, todos, fixmes = count_lines(path)
                total_loc += loc
                total_todos += todos
                total_fixmes += fixmes
                file_count += 1

    return file_count, total_loc, total_todos, total_fixmes


def main():
    print("=== Papeterie Engine Health Report ===")
    print(f"Root: {PROJECT_ROOT}\n")

    # Python Analysis
    py_files, py_loc, py_todos, py_fixmes = analyze_directory(SRC_DIR, ".py")

    # JavaScript/JSX Analysis
    web_dir = SRC_DIR / "web" / "src"
    js_files, js_loc, js_todos, js_fixmes = analyze_directory(web_dir, ".js")
    jsx_files, jsx_loc, jsx_todos, jsx_fixmes = analyze_directory(web_dir, ".jsx")

    total_js_files = js_files + jsx_files
    total_js_loc = js_loc + jsx_loc
    total_js_todos = js_todos + jsx_todos
    total_js_fixmes = js_fixmes + jsx_fixmes

    # Table Output
    print(f"{'Metric':<20} {'Backend':<15} {'Frontend':<15} {'Total':<15}")
    print(f"{'-' * 20} {'-' * 15} {'-' * 15} {'-' * 15}")
    print(f"{'Files':<20} {py_files:<15} {total_js_files:<15} {py_files + total_js_files:<15}")
    print(f"{'LOC':<20} {py_loc:<15} {total_js_loc:<15} {py_loc + total_js_loc:<15}")
    print(f"{'TODOs':<20} {py_todos:<15} {total_js_todos:<15} {py_todos + total_js_todos:<15}")
    print(f"{'FIXMEs':<20} {py_fixmes:<15} {total_js_fixmes:<15} {py_fixmes + total_js_fixmes:<15}")
    print("-" * 68)


if __name__ == "__main__":
    main()
