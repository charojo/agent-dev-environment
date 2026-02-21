#!/usr/bin/env python3
## @DOC
# ### Diagram Compilation
# This tool automates the process of converting Graphviz DOT and Mermaid blocks
# into visual diagrams (SVG). It ensures that diagrams in documentation are
# always up-to-date and formatted professionally with stable figure captions.
#
# See architecture: [validate_workflow.svg](../docs/assets/diagrams/validate_workflow.svg)
# <!-- @diagram: validate_workflow.svg -->

"""
Automated Diagram Generator for Papeterie Engine.
Scans the repository for *.dot files and Markdown diagram blocks, 
compiling them to *.svg using Graphviz and Mermaid-CLI.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import re
import os
from ADE_ownership import is_repo_owned_by_current_user

# --- REGEX PATTERNS ---
# Matches either an existing figure block or a raw mermaid/dot block
MERMAID_REGEX = re.compile(
    r"(?P<existing>figure \d+: .*?\n\n(?:!\[.*?\]\(.*?\)\n+|\[.*?\]\(.*?\)\n+|<details>.*?<summary>Mermaid Source</summary>.*?```mermaid\n(?P<inner_content_wrapped>.*?)\n```.*?</details>|[\s\n]+)+)|(```mermaid\n(?P<inner_content_raw>.*?)\n```)",
    re.DOTALL,
)

DOT_REGEX = re.compile(
    r"(?P<existing>figure \d+: .*?\n\n(?:!\[.*?\]\(.*?\)\n+|\[.*?\]\(.*?\)\n+|<details>.*?<summary>Graphviz Source</summary>.*?```dot\n(?P<inner_content_wrapped>.*?)\n```.*?</details>|[\s\n]+)+)|(```dot\n(?P<inner_content_raw>.*?)\n```)",
    re.DOTALL,
)


# Regex to find caption comments like <!-- caption: My Beautiful Diagram -->
CAPTION_REGEX = re.compile(r"<!--\s*caption:\s*(.*?)\s*-->", re.IGNORECASE)

def sanitize_name(text):
    """Sanitizes text for use in a filename."""
    if not text:
        return "diagram"
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", s)

def extract_caption(content, md_content=None, match_start=0):
    """Extracts a caption from code or preceding markdown comment."""
    # 1. Try frontmatter title
    title_match = re.search(r"^\s*---\s*\n.*?title:\s*(.*?)\n.*?---\s*", content, re.DOTALL)
    if title_match:
        return title_match.group(1).strip()
    
    # 2. Try Graphviz label
    label_match = re.search(r'label\s*=\s*"(.*?)"', content)
    if label_match:
        return label_match.group(1).strip()

    # 3. Try preceding comment in Markdown
    if md_content and match_start > 0:
        prefix = md_content[:match_start].strip()
        lines = prefix.split("\n")
        if lines:
            last_line = lines[-1].strip()
            caption_match = CAPTION_REGEX.search(last_line)
            if caption_match:
                return caption_match.group(1).strip()

    return "diagram"

def compile_dot_to_svg(dot_code, output_path):
    """Compiles Graphviz DOT code to SVG."""
    dot_source_path = output_path.with_suffix(".dot")
    dot_source_path.write_text(dot_code)
    
    cmd = ["dot", "-Tsvg", "-Gbgcolor=white", str(dot_source_path), "-o", str(output_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def compile_mermaid_to_svg(mermaid_code, output_path):
    """Compiles mermaid code to SVG using mmdc."""
    mmd_file = output_path.with_suffix(".mmd")
    mmd_file.write_text(mermaid_code)
    
    cmd = ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", str(mmd_file), "-o", str(output_path), "-b", "white"]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def process_markdown_file(md_file, project_root):
    """Scans a Markdown file for diagram blocks and compiles them."""
    if not is_repo_owned_by_current_user(md_file):
        return False

    content = md_file.read_text(encoding="utf-8")
    diagrams_dir = project_root / "docs" / "assets" / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    
    new_content_fragments = []
    last_idx = 0
    file_changed = False
    diagram_count = 0
    
    # Combined search for both Mermaid and DOT
    matches = []
    for m in MERMAID_REGEX.finditer(content):
        matches.append(("mermaid", m))
    for m in DOT_REGEX.finditer(content):
        matches.append(("dot", m))
    matches.sort(key=lambda x: x[1].start())

    for mtype, match in matches:
        if match.start() < last_idx:
            continue
            
        diagram_count += 1
        is_wrapped = match.group("existing") is not None
        inner_content = match.group("inner_content_wrapped") if is_wrapped else match.group("inner_content_raw")
        inner_content = inner_content.strip()
        
        caption = extract_caption(inner_content, content, match.start())
        caption_slug = sanitize_name(caption)
        
        name_base = f"{md_file.stem}_{diagram_count}_{caption_slug}"
        output_path = diagrams_dir / f"{name_base}.svg"
        src_ext = ".mmd" if mtype == "mermaid" else ".dot"
        src_path = diagrams_dir / f"{name_base}{src_ext}"
        
        # Compile if changed or missing
        if not output_path.exists() or not src_path.exists() or src_path.read_text().strip() != inner_content:
            print(f"  Compiling {mtype} diagram: {name_base}...")
            if mtype == "mermaid":
                compile_mermaid_to_svg(inner_content, output_path)
            else:
                compile_dot_to_svg(inner_content, output_path)
            src_path.write_text(inner_content)

        rel_svg = os.path.relpath(output_path, md_file.parent)
        
        source_label = "Mermaid Source" if mtype == "mermaid" else "Graphviz Source"
        block_tag = mtype
        
        # Construct the stable, idempotent replacement
        # Layout: Caption -> Image -> Source Block
        replacement = (
            f"figure {diagram_count}: {caption}\n\n"
            f"![figure {diagram_count}: {caption}]({rel_svg})\n\n"
            f"<details>\n<summary>{source_label}</summary>\n\n"
            f"```{block_tag}\n"
            f"{inner_content}\n"
            f"```\n\n"
            f"</details>\n"
        )
        
        # IDEMPOTENCY FIX: Clean up any redundant figure lines immediately preceding the match
        prefix_text = content[last_idx:match.start()]
        cleaned_prefix = re.sub(r"figure \d+: .*?\n+", "", prefix_text)
        if cleaned_prefix != prefix_text:
            file_changed = True
            
        new_content_fragments.append(cleaned_prefix)
        new_content_fragments.append(replacement)
        
        if match.group(0).strip() != replacement.strip():
            file_changed = True
            
        last_idx = match.end()

    new_content_fragments.append(content[last_idx:])
    
    if file_changed:
        md_file.write_text("".join(new_content_fragments), encoding="utf-8")
        print(f"  Updated {md_file.name} (idempotent)")
        return True
    return False

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate diagrams and update Markdown links.")
    parser.add_argument("directory", nargs="?", help="Directory to scan")
    args = parser.parse_args(argv)

    if args.directory:
        project_root = Path(args.directory).resolve()
    else:
        try:
            root_str = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
            project_root = Path(root_str)
        except subprocess.CalledProcessError:
            project_root = Path.cwd()

    print(f"Project Root: {project_root}")

    # 1. Process Standalone .dot files
    dot_files = list(project_root.rglob("*.dot"))
    for dot_file in dot_files:
        if "node_modules" in str(dot_file) or ".git" in str(dot_file) or "docs/assets/diagrams" in str(dot_file):
            continue
        print(f"Compiling standalone DOT: {dot_file.name}")
        compile_dot_to_svg(dot_file.read_text(), dot_file.with_suffix(".svg"))

    # 2. Process Markdown Diagram Blocks
    md_files = list(project_root.rglob("*.md"))
    for md_file in md_files:
        if "node_modules" in str(md_file) or ".git" in str(md_file):
            continue
        if not md_file.exists():
            continue
        process_markdown_file(md_file, project_root)

    # 3. Update diagram links in source code
    print("\nUpdating diagram links in source code...")
    try:
        import ADE_document as document
        document.update_diagram_links(project_root)
    except (ImportError, Exception) as e:
        print(f"Warning: Failed to update diagram links: {e}")

if __name__ == "__main__":
    main()
