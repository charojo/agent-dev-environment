#!/usr/bin/env python3
"""
Automated Diagram Generator for Papeterie Engine.
Scans the repository for *.dot files and compiles them to *.png using Graphviz.
"""

import subprocess
import sys
from pathlib import Path


def find_dot_files(root_dir):
    """Recursively find all .dot files in the repository."""
    return list(Path(root_dir).rglob("*.dot"))


def compile_dot_to_png(dot_file):
    """Compiles a single .dot file to .png using the 'dot' command."""
    png_file = dot_file.with_suffix(".png")
    print(f"Compiling {dot_file} -> {png_file}...")

    try:
        subprocess.run(
            ["dot", "-Tpng", "-Gbgcolor=white", str(dot_file), "-o", str(png_file)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("  Success ✅")
    except subprocess.CalledProcessError as e:
        print(f"  Error ❌: {e.stderr}")
    except FileNotFoundError:
        print("  Error ❌: 'dot' command not found. Please install Graphviz.")
        sys.exit(1)


def main():
    # Assume script is run from agent_env/bin/
    # We find the project root relative to this script
    script_path = Path(__file__).resolve()
    # agent_env/bin/generate_diagrams.py -> agent_env/bin -> agent_env -> root
    project_root = script_path.parent.parent.parent

    print(f"Project Root: {project_root}")

    dot_files = find_dot_files(project_root)

    if not dot_files:
        print("No .dot files found.")
        return

    print(f"Found {len(dot_files)} .dot files.")
    for dot_file in dot_files:
        compile_dot_to_png(dot_file)


if __name__ == "__main__":
    main()
