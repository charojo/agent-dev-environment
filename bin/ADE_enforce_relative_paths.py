#!/usr/bin/env python3
# ## @DOC
# ### Ade Enforce Relative Paths
# Enforces relative paths in documentation.


import argparse
import fnmatch
import re
import subprocess
import sys
import os
from pathlib import Path
from ADE_ownership import is_repo_owned_by_current_user

# Patterns indicating absolute project paths that should be relative.
# We catch the file:/// scheme followed by an absolute linux path or the project root.
PATTERNS = [
    re.compile(r"file:///home/[\w.-]+/"),
    # Common user home pattern in case project root detection is slightly off in some envs
]
# Binary extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", 
    ".zip", ".tar", ".gz", ".mp4", ".db",
}

# Files to always exclude
DEFAULT_EXCLUDES = [
    ".gitmodules",
    "ADE_enforce_relative_paths.py",
    "enforce_relative_paths.py",
    "full_config.yaml",
]


def get_project_root():
    """Returns the project root directory."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], universal_newlines=True
        ).strip()
        return Path(root)
    except subprocess.CalledProcessError:
        return Path(__file__).resolve().parent.parent.parent


def get_git_files(root_dir):
    """Get list of files tracked by git or untracked but not ignored."""
    try:
        # Tracked files (recursively through submodules)
        tracked = subprocess.run(
            ["git", "ls-files", "--cached", "--recurse-submodules"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        
        # Untracked files (root level only, as --recurse-submodules + --others is buggy in some git versions)
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        
        return list(set(tracked + untracked))
    except subprocess.CalledProcessError as e:
        print(f"Error running git ls-files: {e}")
        return []


def is_binary(file_path):
    return file_path.suffix.lower() in BINARY_EXTENSIONS


def check_file(file_path, patterns):
    offending_lines = []
    try:
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pattern in patterns:
                    if pattern.search(line):
                        offending_lines.append((i, line.strip()))
                        break
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return offending_lines


def main():
    parser = argparse.ArgumentParser(description="Enforce relative paths in project files.")
    parser.add_argument(
        "--exclude",
        action="append",
        help="Glob pattern to exclude (can be specified multiple times)",
        default=[]
    )
    args = parser.parse_args()

    root_dir = get_project_root()
    errors = 0

    # Add project root to patterns dynamically
    patterns = PATTERNS + [re.compile(rf"{re.escape(str(root_dir))}")]

    # Combine excludes
    all_excludes = DEFAULT_EXCLUDES + args.exclude

    print(f"Scanning for absolute paths in {root_dir} (respecting .gitignore)...")

    files_to_check = get_git_files(root_dir)

    for rel_path_str in files_to_check:
        file_path = root_dir / rel_path_str

        # Skip repositories not owned by the current user
        if not is_repo_owned_by_current_user(file_path):
            continue

        if file_path.is_dir():
            continue

        # Check excludes
        if any(fnmatch.fnmatch(rel_path_str, ex) or fnmatch.fnmatch(file_path.name, ex) for ex in all_excludes):
            continue

        if is_binary(file_path):
            continue

        problems = check_file(file_path, patterns)
        if problems:
            errors += 1
            print(f"\n❌ Absolute path(s) found in {rel_path_str}:")
            for line_num, content in problems:
                print(f"  L{line_num}: {content}")

    if errors > 0:
        print(f"\nTotal: {errors} files found with absolute paths.")
        print("Please use relative paths instead.")
        sys.exit(1)
    else:
        print("✅ No absolute paths found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
