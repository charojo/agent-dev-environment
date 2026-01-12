#!/usr/bin/env python3
## @DOC
# ### Diagram Compilation
# This tool automates the process of converting Graphviz DOT files into visual
# diagrams (SVG/PNG). It also triggers source code link updates to ensure
# documentation always points to the latest generated assets.
#
# See architecture: [validate_workflow.svg](../docs/assets/images/validate_workflow.svg) <!-- @diagram: validate_workflow.svg -->

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


def compile_dot_to_file(dot_file, fmt="png", dpi=300):
    """
    Compiles a Graphviz DOT file into the specified format.

    @param dot_file Path to the input .dot file.
    @param fmt Output format (e.g., 'png', 'svg').
    @param dpi Resolution for raster output.
    """
    """Compiles a single .dot file to the specified format using Graphviz."""
    out_file = dot_file.with_suffix(f".{fmt}")
    print(f"Compiling {dot_file} -> {out_file} ({fmt.upper()}, {dpi} DPI)...")

    cmd = ["dot", f"-T{fmt}"]
    if fmt == "png":
        cmd.append(f"-Gdpi={dpi}")

    cmd.extend(["-Gbgcolor=white", str(dot_file), "-o", str(out_file)])

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("  Success ✅")
    except subprocess.CalledProcessError as e:
        print(f"  Error ❌: {e.stderr}")
    except FileNotFoundError:
        print("  Error ❌: 'dot' command not found. Please install Graphviz.")
        sys.exit(1)


def main():
    # bin/generate_diagrams.py -> bin -> root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    print(f"Project Root: {project_root}")

    dot_files = find_dot_files(project_root)

    if not dot_files:
        print("No .dot files found.")
        return

    print(f"Found {len(dot_files)} .dot files.")
    for dot_file in dot_files:
        # Generate scalable SVG (Default)
        compile_dot_to_file(dot_file, fmt="svg")

        # PNG is now optional/skipped by default to save space
        # compile_dot_to_file(dot_file, fmt="png", dpi=150)

    # Update diagram links in source code
    print("\nUpdating diagram links in source code...")
    try:
        # Import document module dynamically or assume it's in the same dir
        sys.path.append(str(script_path.parent))
        import document

        document.update_diagram_links(project_root)

        # Also run doc extraction while we are at it?
        # The user requested "generate_diagrams also updates links into the source code"
        # It didn't explicitly ask for doc extraction here, but it's part of the same "self-documenting" workflow.
        # But let's stick to the prompt: "generate_diagrams also updates links".
        # I'll adhere to the plan which said "Integrate bin/document.py to trigger link updates".
    except ImportError:
        print("Warning: Could not import 'document' module. Link updates skipped.")
    except Exception as e:
        print(f"Warning: Failed to update diagram links: {e}")


if __name__ == "__main__":
    main()
