import argparse
import subprocess
import sys
from pathlib import Path
import re
import hashlib
import shutil


# Global set to track valid files
VALID_FILES = set()

# Regex to find mermaid blocks.
# We want to find:
# 1. Existing wrapped blocks: <details>...<summary>Mermaid Source</summary>...```mermaid\n(.*?)\n```...</details>...![...](...)
# 2. Raw blocks: ```mermaid...```
MERMAID_REGEX = re.compile(
    r"(<details>.*?<summary>Mermaid Source</summary>.*?```mermaid\n(.*?)\n```.*?</details>(?:\s*!\[.*?\]\(.*?\)(?:\s*\[.*?\]\(.*?\))?)?)|(```mermaid\n(.*?)\n```)",
    re.DOTALL,
)

# Regex to find caption comments like <!-- caption: My Beautiful Diagram -->
CAPTION_REGEX = re.compile(r"<!--\s*caption:\s*(.*?)\s*-->", re.IGNORECASE)

# Regex to find existing figure blocks
FIGURE_REGEX = re.compile(
    r"figure (\d+): (.*?)\n\n"
    r"!\[figure \d+: .*?\]\((.*?)\)\n"
    r"\[figure \d+: .*? source\]\((.*?)\)",
    re.IGNORECASE
)

def sanitize_name(text):
    """Sanitizes text for use in a filename."""
    if not text:
        return ""
    # Remove non-alphanumeric chars, replace spaces with underscores, lowercase
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", s)

def extract_caption(content, md_content=None, match_start=0):
    """
    Extracts a caption from mermaid code or preceding markdown comment.
    """
    # 1. Try Mermaid frontmatter title
    title_match = re.search(r"^\s*---\s*\n.*?title:\s*(.*?)\n.*?---\s*", content, re.DOTALL)
    if title_match:
        return title_match.group(1).strip()
    
    # 2. Try Graphviz label
    label_match = re.search(r'label\s*=\s*"(.*?)"', content)
    if label_match:
        return label_match.group(1).strip()

    # 3. Try preceding comment in Markdown
    if md_content and match_start > 0:
        # Search backwards from the match start for a caption comment
        prefix = md_content[:match_start].strip()
        lines = prefix.split("\n")
        if lines:
            last_line = lines[-1].strip()
            caption_match = CAPTION_REGEX.search(last_line)
            if caption_match:
                return caption_match.group(1).strip()

    return "diagram"

def compile_dot_to_file(dot_file, output_dir, file_num, fmt="svg", dpi=300):
    """
    Compiles a Graphviz DOT file into the specified format in docs/assets/diagrams.
    """
    with open(dot_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    caption = extract_caption(content)
    caption_slug = sanitize_name(caption)
    
    name = f"{dot_file.stem}_{file_num}_{caption_slug}.{fmt}"
    out_file = output_dir / name
    
    print(f"Compiling {dot_file} -> {out_file} ({fmt.upper()}, {dpi} DPI)...")
    
    VALID_FILES.add(out_file.resolve())

    cmd = ["dot", f"-T{fmt}"]
    if fmt == "png":
        cmd.append(f"-Gdpi={dpi}")

    cmd.extend(["-Gbgcolor=white", str(dot_file), "-o", str(out_file)])

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("  Success ✅")
        return out_file, caption
    except subprocess.CalledProcessError as e:
        print(f"  Error ❌: {e.stderr}")
        return None, None
    except FileNotFoundError:
        print("  Error ❌: 'dot' command not found. Please install Graphviz.")
        sys.exit(1)

def find_md_files(root_dir):
    """Recursively find all .md files in the repository."""
    return list(Path(root_dir).rglob("*.md"))

def compile_dot_to_svg(dot_code, output_path, caption="diagram"):
    """Compiles Graphviz DOT code to SVG."""
    # Write DOT code to a sibling .dot file
    dot_source_path = output_path.with_suffix(".dot")
    with open(dot_source_path, "w", encoding="utf-8") as f:
        f.write(dot_code)
    
    # Track files
    VALID_FILES.add(output_path.resolve())
    VALID_FILES.add(dot_source_path.resolve())
    
    print(f"Compiling DOT -> {output_path}...")
    
    cmd = ["dot", "-Tsvg", "-Gbgcolor=white", str(dot_source_path), "-o", str(output_path)]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("  Success ✅")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error ❌: DOT compilation failed. {e.stderr}")
        return False
    except FileNotFoundError:
        print("  Error ❌: 'dot' command not found. Please install Graphviz.")
        return False

def compile_mermaid_to_svg(mermaid_code, output_path):
    """Compiles mermaid code to SVG using mmdc (via npx)."""
    # Create temp mmd file if it doesn't exist (already created by caller usually)
    mmd_file = output_path.with_suffix(".mmd")
    with open(mmd_file, "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    
    # Track files
    VALID_FILES.add(output_path.resolve())
    VALID_FILES.add(mmd_file.resolve())
    
    print(f"Compiling Mermaid -> {output_path}...")
    
    # Command to run mmdc via npx
    cmd = ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", str(mmd_file), "-o", str(output_path), "-b", "white"]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("  Success ✅")
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        print(f"  Error ❌: Mermaid compilation failed. {stderr.strip()}")
        return False
    except FileNotFoundError:
        print("  Error ❌: 'npx' command not found. Please install Node.js/npm.")
        return False

def process_markdown_diagrams(project_root, check_only=False):
    """Scans all MD files for mermaid blocks AND existing figure links and compiles/renames them."""
    print("\nProcessing Markdown diagrams...")
    md_files = find_md_files(project_root)
    
    diagrams_dir = project_root / "docs" / "assets" / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_update = []

    for md_file in md_files:
        # Skip node_modules and hidden dirs
        if "node_modules" in str(md_file) or "/." in str(md_file):
            continue
            
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content_fragments = []
        last_idx = 0
        file_changed = False
        diagram_count = 0
        
        # Combine searches: We first find all mermaid blocks and all existing figure blocks.
        # We need to process them in the order they appear to maintain diagram_count.
        
        # Collect all matches with their type and start position
        matches = []
        for m in MERMAID_REGEX.finditer(content):
            matches.append(("mermaid", m))
        for m in FIGURE_REGEX.finditer(content):
            matches.append(("figure", m))
            
        # Sort by start index
        matches.sort(key=lambda x: x[1].start())
        
        for mtype, match in matches:
            # Avoid overlapping matches (if any)
            if match.start() < last_idx:
                continue

            diagram_count += 1
            block_content = ""
            caption = "diagram"
            found_mmd_path = None

            if mtype == "mermaid":
                found_wrapped = bool(match.group(1))
                found_content = match.group(2) if found_wrapped else match.group(4)
                if not found_content:
                    continue
                block_content = found_content.strip()
                caption = extract_caption(block_content, content, match.start())
                source_ext = ".mmd"
            else:
                # figure
                caption = match.group(2).strip()
                rel_src_path = match.group(4).strip()
                src_source_path = (md_file.parent / rel_src_path).resolve()
                if src_source_path.exists():
                    with open(src_source_path, "r", encoding="utf-8") as f:
                        block_content = f.read().strip()
                    found_src_path = src_source_path
                    source_ext = src_source_path.suffix.lower()
                    if source_ext not in [".mmd", ".dot"]:
                        # If it's something else, we ignore it for auto-regeneration but keep it valid
                        VALID_FILES.add(src_source_path.resolve())
                        # Also track the linked image
                        rel_img_path = match.group(3).strip()
                        img_path = (md_file.parent / rel_img_path).resolve()
                        VALID_FILES.add(img_path.resolve())
                        continue
                else:
                    print(f"  Warning: Could not find diagram source at {rel_src_path} for {md_file.name}")
                    continue

            caption_slug = sanitize_name(caption)
            
            # Compile and Save
            name_base = f"{md_file.stem}_{diagram_count}_{caption_slug}"
            output_path = diagrams_dir / f"{name_base}.svg" 
            src_path = diagrams_dir / f"{name_base}{source_ext}"
            
            # Track valid files
            VALID_FILES.add(output_path.resolve())
            VALID_FILES.add(src_path.resolve())

            # Check if we actually need to change anything
            needed_recompile = False
            if not output_path.exists():
                needed_recompile = True
            
            # Save source if content changed or name changed
            if not src_path.exists() or src_path.read_text().strip() != block_content:
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(block_content)
                needed_recompile = True

            if needed_recompile and not check_only:
                if source_ext == ".mmd":
                    compile_mermaid_to_svg(block_content, output_path)
                elif source_ext == ".dot":
                    compile_dot_to_svg(block_content, output_path, caption)
            
            try:
                rel_svg_path = output_path.relative_to(md_file.parent)
                rel_src_path = src_path.relative_to(md_file.parent)
            except ValueError:
                rel_svg_path = output_path
                rel_src_path = src_path

            replacement = (
                f"figure {diagram_count}: {caption}\n\n"
                f"![figure {diagram_count}: {caption}]({rel_svg_path})\n"
                f"[figure {diagram_count}: {caption} source]({rel_src_path})"
            )
            
            # Calculate what we matched
            matched_text = match.group(0)
            
            # Append text before match
            new_content_fragments.append(content[last_idx:match.start()])
            
            # Check if replacement is different (idempotency check)
            if matched_text.strip() != replacement.strip():
                new_content_fragments.append(replacement)
                file_changed = True
            else:
                new_content_fragments.append(matched_text)
                
            last_idx = match.end()
            
        new_content_fragments.append(content[last_idx:])
        final_content = "".join(new_content_fragments)
        
        if file_changed:
            if check_only:
                print(f"  ❌ {md_file.name} needs updating.")
                files_to_update.append(md_file)
            else:
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(final_content)
                print(f"  Updated {md_file.name} with links to external diagrams.")

    if check_only and files_to_update:
        print(f"\n❌ Found {len(files_to_update)} files needing updates. Run without --check to fix.")
        sys.exit(1)
    elif check_only:
        print("\n✅ All diagrams up to date.")

def cleanup_unused_diagrams(project_root):
    """Removes SVG/MMD files in docs/assets/diagrams/ that are not in VALID_FILES."""
    print("\nCleaning up unused diagrams...")
    diagrams_dir = project_root / "docs" / "assets" / "diagrams"
    if not diagrams_dir.exists():
        return
        
    all_files = list(diagrams_dir.glob("*"))
    deleted_count = 0
    
    for file_path in all_files:
        # Only clean SVG and MMD files
        if file_path.suffix not in [".svg", ".mmd"]:
            continue
            
        if file_path.resolve() not in VALID_FILES:
            print(f"  Deleting unused file: {file_path.name}")
            file_path.unlink()
            deleted_count += 1
            
    if deleted_count == 0:
        print("  No unused diagrams found.")
    else:
        print(f"  Deleted {deleted_count} unused files.")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate diagrams from DOT and Mermaid files.")
    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory to scan (defaults to git root or current dir)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files need updating without modifying them",
    )
    args = parser.parse_args(argv)

    if args.directory:
        project_root = Path(args.directory).resolve()
    else:
        try:
            root_str = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], universal_newlines=True
            ).strip()
            project_root = Path(root_str)
        except subprocess.CalledProcessError:
            project_root = Path.cwd()

    print(f"Project Root: {project_root}")

    diagrams_dir = project_root / "docs" / "assets" / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    # Process diagrams in MD files
    process_markdown_diagrams(project_root, check_only=args.check)
    
    # 3. Cleanup
    if not args.check:
        cleanup_unused_diagrams(project_root)

    # 4. Update links
    if not args.check:
        print("\nUpdating diagram links in source code...")
        try:
            import ADE_document as document
            document.update_diagram_links(project_root)
        except ImportError:
            print("Warning: Could not import 'document' module. Link updates skipped.")
        except Exception as e:
            print(f"Warning: Failed to update diagram links: {e}")

if __name__ == "__main__":
    main()
