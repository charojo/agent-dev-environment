#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

# Project root relative to this script
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Patterns that indicate absolute project paths
# We look for the common patterns that appeared: /home/chacker/projects/papeterie-engine
# and also the file:/// scheme followed by an absolute linux path.
PATTERNS = [
    re.compile(r"file:///home/[\w.-]+/"),
    re.compile(rf"{re.escape(str(PROJECT_ROOT))}"),
    # Common user home pattern in case project root detection is slightly off in some envs
    re.compile(r"/home/[\w.-]+/projects/[\w.-]+"),
]

# Binary extensions to skip
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".mp4",
    ".db",
}


def get_git_files(root_dir):
    """Get list of files tracked by git or untracked but not ignored."""
    try:
        # --cached: tracked files
        # --others: untracked files
        # --exclude-standard: use standard ignore rules (.gitignore, etc.)
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error running git ls-files: {e}")
        # Fallback to empty list if not a git repo or git fails
        return []


def is_binary(file_path):
    return file_path.suffix.lower() in BINARY_EXTENSIONS


def check_file(file_path):
    offending_lines = []
    try:
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pattern in PATTERNS:
                    if pattern.search(line):
                        offending_lines.append((i, line.strip()))
                        break
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return offending_lines


def main():
    root_dir = PROJECT_ROOT
    errors = 0

    print(f"Scanning for absolute paths in {root_dir} (respecting .gitignore)...")

    files_to_check = get_git_files(root_dir)

    for rel_path_str in files_to_check:
        file_path = root_dir / rel_path_str

        if file_path.is_dir():
            continue

        # Skip this script itself
        if file_path.name in ["enforce_relative_paths.py", "ADE_enforce_relative_paths.py"]:
            continue

        if is_binary(file_path):
            continue

        problems = check_file(file_path)
        if problems:
            errors += 1
            print(f"\n❌ Absolute path(s) found in {rel_path_str}:")
            for line_num, content in problems:
                print(f"  L{line_num}: {content}")

    if errors > 0:
        print(f"\nTotal: {errors} files found with absolute paths.")
        print("Please use relative paths instead (e.g., ../src/ or assets/diagrams/).")
        sys.exit(1)
    else:
        print("✅ No absolute paths found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
