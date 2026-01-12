## @DOC
# ### Project Analysis
# This tool provides high-level metrics about the codebase, including Lines of Code (LOC),
# T-O-D-O/F-I-X-M-E counts, and language distribution. It is utilized by `validate.sh`
# to generate health reports.
#
# **Key Features:**
# - Language-specific extension filtering.
# - Directory exclusion (e.g., `.venv`, `node_modules`).
# - Markdown and plain-text report generation.

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure we can import config_utils from the same directory
sys.path.append(str(Path(__file__).parent))
try:
    import ADE_config_utils as config_utils
except ImportError:
    # If running from a different context, try to find it
    pass

# Configuration
# Configuration
# Determine PROJECT_ROOT by looking for config.toml, up to 3 levels up
CURRENT_DIR = Path(__file__).parent
POSSIBLE_ROOTS = [
    Path.cwd(),  # Prioritize current directory (set by validate.sh)
    CURRENT_DIR.parent.parent,  # project root (if agent_env is submodule)
    CURRENT_DIR.parent,  # agent_env
]

PROJECT_ROOT = CURRENT_DIR.parent  # Fallback
# First pass: Look for config.toml (strongest signal)
found = False
for p in POSSIBLE_ROOTS:
    if (p / "config.toml").exists():
        PROJECT_ROOT = p
        found = True
        break

# Second pass: Look for .git if config.toml not found
if not found:
    for p in POSSIBLE_ROOTS:
        if (p / ".git").exists():
            PROJECT_ROOT = p
            break

SRC_DIR = PROJECT_ROOT / "src"


def count_lines(file_path):
    """
    Count lines of code, stripping empty lines and comments (basic).

    @param file_path Path to the file to analyze.
    @return tuple (code_lines, todos, fixmes)
    """
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
                if "TO" + "DO" in stripped:
                    todos += 1
                if "FIX" + "ME" in stripped:
                    fixmes += 1
                continue

            code_lines += 1
            if "TO" + "DO" in line:
                todos += 1
            if "FIX" + "ME" in line:
                fixmes += 1

        return code_lines, todos, fixmes
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, 0, 0


def analyze_directory(directory, extension):
    """
    Recursively analyzes a directory for files of a specific extension.

    @param directory The directory to scan.
    @param extension The file extension to match.
    @return tuple (file_count, total_loc, total_todos, total_fixmes)
    """
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


def print_text_table(results, sorted_langs, metrics, keys):
    # Dynamic Headers
    header = f"{'Metric':<20}"
    for lang in sorted_langs:
        header += f"{lang.capitalize():<15}"
    header += f"{'Total':<15}"

    print(header)
    print("-" * len(header))

    for metric, key in zip(metrics, keys):
        row = f"{metric:<20}"
        total_val = 0
        for lang in sorted_langs:
            val = results[lang][key]
            total_val += val
            row += f"{val:<15}"
        row += f"{total_val:<15}"
        print(row)

    print("-" * 75)


def print_markdown_table(results, sorted_langs, metrics, keys):
    # Dynamic Headers
    # | Metric | Lang1 | Lang2 | Total |
    header = "| Metric | " + " | ".join([lang.capitalize() for lang in sorted_langs]) + " | Total |"
    divider = "| :--- | " + " | ".join([":---" for _ in sorted_langs]) + " | :--- |"

    print(header)
    print(divider)

    for metric, key in zip(metrics, keys):
        row = f"| {metric} | "
        total_val = 0
        for lang in sorted_langs:
            val = results[lang][key]
            total_val += val
            row += f"{val} | "
        row += f"{total_val} |"
        print(row)


def print_config_results(results_file, markdown=False):
    if not results_file.exists():
        return

    try:
        with open(results_file, "r") as f:
            report = json.load(f)

        if markdown:
            print("\n### Configuration Test Results")
            print("| Config | Status | Total Size | Venv | Node |")
            print("| :--- | :--- | :--- | :--- | :--- |")
            for r in report:
                print(
                    f"| {r['config']} | {r['status']} | {r['total_size']} | {r['venv_size']} | {r['node_modules_size']} |"
                )
        else:
            print("\n=== Configuration Test Results ===")
            header = f"{'Config':<20} | {'Status':<6} | {'Total':<10} | {'Venv':<10} | {'Node':<10}"
            print(header)
            print("-" * len(header))
            for r in report:
                print(
                    f"{r['config']:<20} | {r['status']:<6} | {r['total_size']:<10} | {r['venv_size']:<10} | {r['node_modules_size']:<10}"
                )
    except Exception as e:
        print(f"Error reading config results: {e}")


def main():
    parser = argparse.ArgumentParser(description="Analyze project statistics.")
    parser.add_argument("--markdown", action="store_true", help="Output in Markdown format")
    parser.add_argument(
        "--dual",
        action="store_true",
        help="Output Markdown to stdout and ASCII to stderr",
    )
    args = parser.parse_args()

    if not args.markdown:
        print("=== Codebase Health Report ===")
        print(f"Root: {PROJECT_ROOT}\n")

    # Load Config
    try:
        config = config_utils.load_config(PROJECT_ROOT)
    except NameError:
        config = {}  # Fallback if import failed

    languages_config = config.get("languages", {})

    # Defaults if config is missing/empty
    if not languages_config:
        languages_config = {
            "python": {"enabled": True, "extensions": [".py"]},
            "typescript": {
                "enabled": True,
                "extensions": [".ts", ".tsx", ".js", ".jsx"],
            },
            "markdown": {"enabled": True, "extensions": [".md"]},
        }

    if "markdown" not in languages_config:
        languages_config["markdown"] = {"enabled": True, "extensions": [".md"]}

    # Combined Analysis - scan whole project except ignored dirs
    exclude_dirs = {
        ".venv",
        "node_modules",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "logs",
        "build",
        "dist",
        "site-packages",
        ".ruff_cache",
        ".coverage",
        "docs",
    }

    # Data structure to hold results: { "python": {files: 0, loc: 0, ...} }
    results = {}

    # Initialize results based on enabled languages
    enabled_extensions = {}  # .py -> "python"

    for lang_name, lang_cfg in languages_config.items():
        if lang_cfg.get("enabled", True):
            results[lang_name] = {"files": 0, "loc": 0, "todos": 0, "fixmes": 0}
            for ext in lang_cfg.get("extensions", []):
                enabled_extensions[ext] = lang_name

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            file_path = Path(root) / file
            _, ext = os.path.splitext(file)

            if ext in enabled_extensions:
                lang = enabled_extensions[ext]
                loc, todos, fixmes = count_lines(file_path)

                results[lang]["files"] += 1
                results[lang]["loc"] += loc
                results[lang]["todos"] += todos
                results[lang]["fixmes"] += fixmes

    # Output
    sorted_langs = sorted(results.keys())
    metrics = ["Files", "LOC", "T-O-D-Os", "F-I-X-M-Es"]
    keys = ["files", "loc", "todos", "fixmes"]

    if args.markdown:
        print_markdown_table(results, sorted_langs, metrics, keys)
    elif args.dual:
        # Print Markdown to stdout
        print_markdown_table(results, sorted_langs, metrics, keys)
        # Print ASCII to stderr
        print("\n=== Codebase Health Summary (ASCII) ===", file=sys.stderr)
        # Redirect print_text_table to stderr
        from contextlib import redirect_stdout

        with redirect_stdout(sys.stderr):
            print_text_table(results, sorted_langs, metrics, keys)
    else:
        print_text_table(results, sorted_langs, metrics, keys)

    # Add Config Results if they exist
    results_file = PROJECT_ROOT / "logs" / "config_test_results.json"
    print_config_results(results_file, markdown=args.markdown or args.dual)


if __name__ == "__main__":
    main()
