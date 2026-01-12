#!/usr/bin/env python3
## @DOC
# ### Documentation Generator
# This script is the core of the Agent Kernel's self-documenting capabilities.
# It performs three main functions:
# 1. **Inline Doc Extraction**: Scans for `## @DOC` blocks.
# 2. **Doxygen Gen**: Generates API docs if `doxygen` is present.
# 3. **Submodule Scanning**: Detects if running as a submodule and documents siblings.

import argparse
import shutil
import subprocess
import os
import re
from pathlib import Path

# Configuration
# Default to current directory script is in -> parent -> parent (assuming bin/document.py)
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECT_ROOT = SCRIPT_DIR.parent
DOCS_DIR = DEFAULT_PROJECT_ROOT / "docs"
GEN_DOCS_DIR = DOCS_DIR / "gen"
GEN_IMAGES_DIR = GEN_DOCS_DIR / "images"

# Ensure gen directory exists
GEN_DOCS_DIR.mkdir(parents=True, exist_ok=True)
GEN_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Regex patterns
DOC_BLOCK_START = re.compile(r"^\s*## @DOC\s*(.*)$")
DIAGRAM_LINK = re.compile(
    r"(\s*(?:#|//)\s*See architecture:\s*)(\[.*?\]\(.*?\))(\s*<!--\s*@diagram:\s*(.*?)\s*-->)"
)


def clean_gen_dir():
    """
    Cleans the generated docs directory, preserving the 'doxygen' cache if desired,
    but for now we clean everything to ensure freshness.
    """
    if GEN_DOCS_DIR.exists():
        print(f"Cleaning generated docs directory: {GEN_DOCS_DIR}")
        # Remove all contents but keep the directory
        for item in GEN_DOCS_DIR.iterdir():
            if item.is_dir():
                # Maybe preserve doxygen if heavy? For now, clean it.
                shutil.rmtree(item)
            else:
                item.unlink()

    GEN_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    GEN_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def get_project_context():
    """
    Detects if we are running as a submodule and identifies the root project context.

    Returns:
        tuple: (project_root_path, is_submodule, superproject_root_path)
    """
    try:
        # Check if we are in a git repository
        subprocess.check_call(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=DEFAULT_PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Check if we are a submodule
        superproject_root = subprocess.check_output(
            ["git", "rev-parse", "--show-superproject-working-tree"],
            cwd=DEFAULT_PROJECT_ROOT,
            universal_newlines=True,
        ).strip()

        if superproject_root:
            return DEFAULT_PROJECT_ROOT, True, Path(superproject_root)

    except subprocess.CalledProcessError:
        pass

    return DEFAULT_PROJECT_ROOT, False, None


def extract_documentation(root_dir):
    """
    Scans the repository for `## @DOC` blocks and aggregates them.

    Returns:
        dict: A dictionary mapping filenames to their extracted documentation.
    """
    extracted_docs = {}

    for root, _, files in os.walk(root_dir):
        if (
            ".git" in root
            or "__pycache__" in root
            or "node_modules" in root
            or "docs" in root  # Exclude the entire docs folder from scanning
        ):
            continue

        for file in files:
            if not file.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".md")):
                continue

            # Skip generated spec to avoid loop
            if "DESIGN_SPEC" in file:
                continue

            file_path = Path(root) / file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue

            current_doc_block = []
            capturing = False

            for line in lines:
                match = DOC_BLOCK_START.match(line)
                if match:
                    capturing = True
                    continue

                if capturing:
                    stripped = line.strip()
                    clean_line = line

                    if file.endswith(".py") or file.endswith(".sh"):
                        if stripped.startswith("#"):
                            # Only strip ONE hash and a following space if present
                            # to preserve Markdown headers (e.g. ### Header)
                            clean_line = line.strip()
                            if clean_line.startswith("# "):
                                clean_line = clean_line[2:]
                            elif clean_line.startswith("#"):
                                clean_line = clean_line[1:]
                        else:
                            # Allow empty lines in doc blocks
                            if stripped:
                                capturing = False
                    elif file.endswith((".js", ".jsx", ".ts", ".tsx")):
                        if stripped.startswith("//"):
                            clean_line = line.strip()
                            if clean_line.startswith("// "):
                                clean_line = clean_line[3:]
                            elif clean_line.startswith("//"):
                                clean_line = clean_line[2:]
                        else:
                            if stripped:
                                capturing = False

                    if capturing:
                        # Fix relative links
                        def fix_link(match):
                            link_text = match.group(1)
                            link_url = match.group(2)

                            if link_url.startswith(("http", "https", "#", "mailto:")):
                                return match.group(0)

                            try:
                                source_dir = file_path.parent
                                abs_target = (source_dir / link_url).resolve()
                                # Relative to GEN_DOCS_DIR
                                new_rel = os.path.relpath(abs_target, GEN_DOCS_DIR)
                                return f"{link_text}({new_rel})"
                            except (ValueError, FileNotFoundError):
                                return match.group(0)

                        clean_line = re.sub(
                            r"(!?\[.*?\])\((.*?)\)", fix_link, clean_line
                        )
                        current_doc_block.append(clean_line)

            if current_doc_block:
                rel_path = file_path.relative_to(root_dir)
                extracted_docs[str(rel_path)] = "\n".join(current_doc_block)

    return extracted_docs


def write_design_spec(docs, output_file, project_name):
    """Writes the aggregated documentation to a markdown file."""
    if not docs:
        print(f"No inline documentation found for {project_name}.")
        return

    print(f"Writing design spec to {output_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Automated Design Specification: {project_name}\n\n")
        f.write(
            "> **Note**: This document is auto-generated from `## @DOC` blocks in the source code. \n\n"
        )

        for filename, content in sorted(docs.items()):
            f.write(f"## [{filename}](../{filename})\n\n")
            f.write(content)
            f.write("\n\n---\n\n")

    print(f"Success ✅: {output_file}")


def generate_pdf(input_file, output_file):
    """Generates a PDF from a markdown file using pandoc."""
    if not shutil.which("pandoc"):
        print("Warning ⚠️ : 'pandoc' not found. PDF generation skipped.")
        return

    if not input_file.exists():
        print(f"Error ❌: {input_file} not found.")
        return

    print(f"Generating PDF for {input_file.name}...")

    cmd = [
        "pandoc",
        input_file.name,
        "-o",
        str(output_file),
        "--from",
        "gfm",
        "--standalone",
        "--variable",
        "geometry:margin=1in",
    ]

    if shutil.which("wkhtmltopdf"):
        cmd.append("--pdf-engine=wkhtmltopdf")
        # Let Pandoc infer title from H1 to avoid duplicates
        # cmd.extend(["--metadata", f"title={input_file.stem.replace('_', ' ')}"])
        cmd.append("--pdf-engine-opt=--enable-local-file-access")
    elif not shutil.which("pdflatex"):
        print(
            "Warning: No standard PDF engine (wkhtmltopdf, pdflatex) found. Pandoc might fail."
        )

    try:
        subprocess.run(cmd, check=True, cwd=input_file.parent)
        print(f"Success ✅: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error ❌: Failed to generate PDF for {input_file.name}. {e}")


def generate_doxygen(project_path, output_dir, project_name):
    """
    Generates Doxygen documentation for the given project path.
    """
    if not shutil.which("doxygen"):
        print("Warning ⚠️ : 'doxygen' not found. Doxygen generation skipped.")
        return

    print(f"Generating Doxygen for {project_name}...")

    doxy_output = output_dir / "doxygen" / project_name
    doxy_output.mkdir(parents=True, exist_ok=True)

    # Create a temporary Doxyfile
    doxyfile_content = f"""
    PROJECT_NAME           = "{project_name}"
    OUTPUT_DIRECTORY       = "{doxy_output}"
    INPUT                  = "{project_path}"
    RECURSIVE              = YES
    FILE_PATTERNS          = *.py *.js *.jsx *.ts *.tsx *.md *.sh
    GENERATE_HTML          = YES
    GENERATE_LATEX         = NO
    WARN_IF_UNDOCUMENTED   = NO
    QUIET                  = YES
    
    # Graphics & UML
    HAVE_DOT               = YES
    UML_LOOK               = YES
    CALL_GRAPH             = YES
    CALLER_GRAPH           = YES
    GRAPHICAL_HIERARCHY    = YES
    DIRECTORY_GRAPH        = YES
    INTERACTIVE_SVG        = YES
    """

    doxyfile_path = doxy_output / "Doxyfile"
    with open(doxyfile_path, "w") as f:
        f.write(doxyfile_content)

    try:
        subprocess.run(["doxygen", str(doxyfile_path)], check=True, cwd=doxy_output)
        print(f"Success ✅: Doxygen generated in {doxy_output}/html")
    except subprocess.CalledProcessError as e:
        print(f"Error ❌: Doxygen generation failed for {project_name}. {e}")


def generate_typedoc(project_path, output_dir, project_name):
    """
    Generates TypeDoc documentation for TypeScript files.
    """
    # Check if there are any .ts or .tsx files
    ts_files = list(project_path.rglob("*.ts")) + list(project_path.rglob("*.tsx"))
    if not ts_files:
        return

    typedoc_bin = shutil.which("typedoc")
    if not typedoc_bin:
        # Check local node_modules
        local_bin = project_path / "node_modules" / ".bin" / "typedoc"
        if local_bin.exists():
            typedoc_bin = str(local_bin)
        else:
            # Check agent-dev-environment root node_modules
            root_bin = DEFAULT_PROJECT_ROOT / "node_modules" / ".bin" / "typedoc"
            if root_bin.exists():
                typedoc_bin = str(root_bin)

    if not typedoc_bin:
        print(
            f"Warning ⚠️ : 'typedoc' not found for {project_name}. Falling back to Doxygen."
        )
        return

    print(f"Generating TypeDoc for {project_name}...")
    td_output = output_dir / "typedoc" / project_name
    td_output.mkdir(parents=True, exist_ok=True)

    cmd = [
        typedoc_bin,
        "--out",
        str(td_output),
        "--exclude",
        "**/node_modules/**",
        "--hideGenerator",
        "--skipErrorChecking",
    ]

    # If no tsconfig.json, use 'expand' or list files
    if not (project_path / "tsconfig.json").exists():
        # Passing all TS files as entry points is safer if no tsconfig
        cmd.extend([str(f) for f in ts_files])
    else:
        cmd.extend(["--entryPointStrategy", "expand", str(project_path)])

    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        print(f"Success ✅: TypeDoc generated in {td_output}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        print(f"Error ❌: TypeDoc generation failed for {project_name}. {stderr}")


def update_diagram_links(root_dir):
    """
    Scans for `@diagram: filename.svg` tags and ensures the preceding Markdown link points to it.
    """
    print("Scanning for diagram links to update...")
    updates_made = 0

    for root, _, files in os.walk(root_dir):
        if ".git" in root or "node_modules" in root or "docs/gen" in root:
            continue

        for file in files:
            if not file.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".md")):
                continue

            file_path = Path(root) / file

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue

            def replace_link(match):
                prefix = match.group(1)
                current_link = match.group(2)
                suffix = match.group(3)
                diagram_filename = match.group(4)

                possible_locs = [
                    # Check manual assets
                    DOCS_DIR / "assets" / "diagrams" / diagram_filename,
                    DOCS_DIR / "assets" / "images" / diagram_filename,
                    # Check generated images
                    GEN_IMAGES_DIR / diagram_filename,
                ]

                found_loc = None
                for loc in possible_locs:
                    if loc.exists():
                        found_loc = loc
                        break

                # If path is .dot, check if .svg exists near it
                if not found_loc and diagram_filename.endswith(".svg"):
                    dot_name = diagram_filename.replace(".svg", ".dot")
                    if (DOCS_DIR / "assets" / "diagrams" / dot_name).exists():
                        # We found the source, but maybe SVG isn't generated yet?
                        # Assume it will be in images/ ?
                        pass

                if found_loc:
                    try:
                        rel_link = os.path.relpath(found_loc, file_path.parent)
                        new_link = f"[{diagram_filename}]({rel_link})"
                        # If the user used custom text, we might want to preserve it.
                        # But current regex captures the whole link `[...](...)`.
                        # Let's try to preserve title if possible.

                        # Extract title from current_link
                        title_match = re.match(r"\[(.*?)\]", current_link)
                        if title_match:
                            title = title_match.group(1)
                            new_link = f"[{title}]({rel_link})"

                        if current_link != new_link:
                            nonlocal updates_made
                            updates_made += 1
                            return f"{prefix}{new_link}{suffix}"
                    except ValueError:
                        pass

                return match.group(0)

            new_content = DIAGRAM_LINK.sub(replace_link, content)

            if new_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated diagram links in {file_path.relative_to(root_dir)}")

    if updates_made == 0:
        print("No diagram links needed updating.")
    else:
        print(f"Updated {updates_made} diagram links.")


def process_project(
    project_path, output_dir, project_name=None, generate_pdf_flag=False
):
    """
    Process a single project directory: extract docs, write spec, generate PDF.
    """
    if project_name is None:
        project_name = project_path.name

    print(f"\n--- Processing Project: {project_name} ---")

    # 1. Extract Documentation
    docs = extract_documentation(project_path)

    # 2. Write Design Spec
    prefix = f"{project_name}_"
    spec_file = output_dir / f"{prefix}DESIGN_SPEC.md"
    write_design_spec(docs, spec_file, project_name)

    # 3. Generate PDF
    if generate_pdf_flag:
        pdf_file = output_dir / f"{prefix}DESIGN_SPEC.pdf"
        generate_pdf(spec_file, pdf_file)

    # Cleanup legacy file if exists
    legacy_spec = DOCS_DIR / "DESIGN_SPEC.md"
    if legacy_spec.exists():
        print(f"Removing legacy spec file: {legacy_spec}")
        legacy_spec.unlink()

    # 4. Generate Structure Map
    # Ensure it goes to images subfolder
    structure_file = GEN_IMAGES_DIR / f"{prefix}structure.svg"
    generate_structure_map(project_path, structure_file, docs)

    # 5. Generate Doxygen
    generate_doxygen(project_path, output_dir, project_name)

    # 6. Generate TypeDoc (specialized for TS/JS)
    generate_typedoc(project_path, output_dir, project_name)


def generate_structure_map(project_path, output_file, docs):
    """
    Generates a visual structure map (SVG) of the project using Graphviz.
    """
    if not shutil.which("dot"):
        print("Warning ⚠️ : 'dot' (graphviz) not found. Structure map skipped.")
        return

    print(f"Generating structure map for {project_path.name}...")

    dot_content = ["digraph ProjectStructure {"]
    dot_content.append(
        '  node [shape=box, style=filled, fillcolor=white, fontname="Helvetica"];'
    )
    dot_content.append('  edge [color="#666666"];')
    dot_content.append('  bgcolor="transparent";')
    dot_content.append(f'  label="{project_path.name} Structure";')
    dot_content.append('  labelloc="t";')

    # Track created nodes to avoid duplicates and ensure connectivity
    nodes = set()
    edges = set()

    def get_node_id(path):
        return re.sub(r"[^a-zA-Z0-9]", "_", str(path.relative_to(project_path)))

    def format_tooltip(doc_content):
        # Extract first non-empty line as tooltip
        if not doc_content:
            return ""
        lines = doc_content.splitlines()
        for line in lines:
            if line.strip():
                # Escape quotes for DOT
                return line.strip().replace('"', '\\"')
        return ""

    for root, dirs, files in os.walk(project_path):
        current_path = Path(root)

        # Skip hidden/ignored dirs (refined list)
        if any(part.startswith(".") for part in current_path.parts) or any(
            part in ["node_modules", "venv", "env", "__pycache__", "dist", "build"]
            for part in current_path.parts
        ):
            continue

        # Add directory node
        if current_path != project_path:
            node_id = get_node_id(current_path)
            if node_id not in nodes:
                dot_content.append(
                    f'  {node_id} [label="{current_path.name}/", shape=folder, fillcolor="#E3F2FD"];'
                )
                nodes.add(node_id)

            # Add edge from parent
            parent_path = current_path.parent
            if parent_path != project_path:
                parent_id = get_node_id(parent_path)
                edge = f"  {parent_id} -> {node_id};"
                if edge not in edges:
                    dot_content.append(edge)
                    edges.add(edge)

        # Add file nodes (only if they are code/docs)
        for file in files:
            if not file.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".md")):
                continue

            file_path = current_path / file
            rel_path = file_path.relative_to(project_path)
            node_id = get_node_id(file_path)

            # Check for documentation
            tooltip = ""
            label_suffix = ""
            if str(rel_path) in docs:
                tooltip = format_tooltip(docs[str(rel_path)])
                label_suffix = " 📝"  # Indicate documented

            fillcolor = "#FFFFFF"
            if file.endswith(".py"):
                fillcolor = "#FFF3E0"  # Orange tint
            elif file.endswith(".js") or file.endswith(".ts"):
                fillcolor = "#FFF8E1"  # Yellow tint
            elif file.endswith(".sh"):
                fillcolor = "#ECEFF1"  # Grey tint

            dot_content.append(
                f'  {node_id} [label="{file}{label_suffix}", fillcolor="{fillcolor}", tooltip="{tooltip}"];'
            )

            # Edge from folder to file
            if current_path == project_path:
                # Top level files, maybe don't connect to a "root" node to keep graph clean?
                # Or connect to a root node represents the project?
                # Let's assume invisible root or just float?
                # Better: implicit root.
                pass
            else:
                parent_id = get_node_id(current_path)
                dot_content.append(f"  {parent_id} -> {node_id};")

    dot_content.append("}")

    # Write DOT
    dot_file = output_file.with_suffix(".dot")
    with open(dot_file, "w", encoding="utf-8") as f:
        f.write("\n".join(dot_content))

    # Render SVG
    try:
        subprocess.run(
            ["dot", "-Tsvg", str(dot_file), "-o", str(output_file)], check=True
        )
        print(f"Success ✅: Structure map -> {output_file}")
        # Clean up DOT? Maybe keep for debug.
    except subprocess.CalledProcessError as e:
        print(f"Error ❌: Failed to render structure map. {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation and update links."
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Generate PDF version of the design spec and other docs (requires pandoc).",
    )
    args = parser.parse_args()

    project_root, is_submodule, superproject_root = get_project_context()

    # Clean gen dir before starting
    clean_gen_dir()

    print(f"Execution Context: {'Submodule' if is_submodule else 'Standalone'}")
    print(f"Current Project Root: {project_root}")
    if is_submodule:
        print(f"Superproject Root: {superproject_root}")

    # Process local project (agent)
    # We use "AGENT" as the name for the local kernel to get AGENT_ prefixes
    process_project(project_root, GEN_DOCS_DIR, "AGENT", args.pdf)

    # If submodule, scan siblings
    if is_submodule and superproject_root:
        print("\nScanning siblings in superproject...")
        for item in superproject_root.iterdir():
            if item.is_dir() and item != project_root:
                # Exclude common non-project directories
                if item.name.startswith(".") or item.name in [
                    "node_modules",
                    "venv",
                    "env",
                ]:
                    continue

                # Check if it looks like a project (has src, package.json, or pyproject.toml ?)
                # For now, lax check: just document it.
                # Prefix with submodule name
                process_project(item, GEN_DOCS_DIR, f"{item.name}", args.pdf)

    # Update diagram links is generally project-wide or specific?
    # Keeping it to current project root for now to avoid messing with parent improperly
    update_diagram_links(project_root)


if __name__ == "__main__":
    main()
