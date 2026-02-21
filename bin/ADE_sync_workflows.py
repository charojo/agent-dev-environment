#!/usr/bin/env python3
import os
import shutil
import re
from pathlib import Path

def find_project_root():
    """Finds the project root by looking for '.agent' and 'upstream' directories."""
    curr = Path(__file__).resolve().parent
    while curr.parent != curr:
        if (curr / ".agent").exists() and (curr / "upstream").exists():
            return curr
        curr = curr.parent
    # Fallback to a sensible default if not found
    return Path(__file__).resolve().parent.parent.parent

REPO_ROOT = find_project_root()
ROOT_WORKFLOW_DIR = REPO_ROOT / ".agent" / "workflows"

def get_suffix(upstream_name):
    """Maps upstream folder names to their workflow suffixes."""
    if upstream_name == "agent_env":
        return "ade"
    if upstream_name == "openclaw":
        return "ocw"
    
    # Fallback to consonants if not hardcoded
    consonants = "".join([c for c in upstream_name if c.lower() not in "aeiou-_ "])
    return consonants[:4].lower() if consonants else upstream_name[:3].lower()

def has_description(file_path):
    """Checks if the markdown file has a description in its YAML frontmatter."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for description: ... within the first --- block
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if not frontmatter_match:
            return False
            
        frontmatter = frontmatter_match.group(1)
        # Check for description that isn't just whitespace
        return bool(re.search(r'^description:\s*\S+', frontmatter, re.MULTILINE))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def sync_workflows():
    if not ROOT_WORKFLOW_DIR.exists():
        print(f"Creating root workflow directory: {ROOT_WORKFLOW_DIR}")
        ROOT_WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)

    upstream_base = REPO_ROOT / "upstream"
    if not upstream_base.exists():
        print(f"No upstream directory found at {upstream_base}")
        return

    synced_count = 0
    skipped_count = 0

    print(f"Project root: {REPO_ROOT}")
    print(f"Syncing workflows to {ROOT_WORKFLOW_DIR}...")

    # Iterate through all directories in upstream/
    for upstream_dir in sorted(upstream_base.iterdir()):
        if not upstream_dir.is_dir():
            continue
        
        upstream_name = upstream_dir.name
        suffix = get_suffix(upstream_name)
        
        # Potential source directories in the upstream folder - now searching recursively
        possible_sources = []
        for p in upstream_dir.rglob("workflows"):
            if p.is_dir():
                # Skip node_modules and hidden directories (except .agent)
                if "node_modules" in p.parts or any(part.startswith(".") and part != ".agent" for part in p.parts):
                    continue
                possible_sources.append(p)
        for p in upstream_dir.rglob(".agent/workflows"):
            if p.is_dir():
                if "node_modules" in p.parts:
                    continue
                possible_sources.append(p)
        
        for source_dir in possible_sources:
            if not source_dir.exists():
                continue
                
            print(f"\nChecking upstream: {upstream_name} ({source_dir})")
            
            for src_path in source_dir.glob("*.md"):
                filename = src_path.name
                base_name = filename[:-3] if filename.endswith(".md") else filename
                
                # If the file already ends with the suffix (with _ or -), keep it as is
                if base_name.endswith(f"_{suffix}") or base_name.endswith(f"-{suffix}"):
                    target_filename = filename
                else:
                    target_filename = f"{base_name}_{suffix}.md"
                
                dest_path = ROOT_WORKFLOW_DIR / target_filename
                
                # Case 1: Target doesn't exist -> Copy with description check
                if not dest_path.exists():
                    if not has_description(src_path):
                        print(f"  SKIP: {filename} is missing 'description'")
                        skipped_count += 1
                        continue
                    print(f"  NEW:  {filename} -> {target_filename}")
                    shutil.copy2(src_path, dest_path)
                    synced_count += 1
                    continue
                
                # Case 2: Both exist -> Compare timestamps
                src_mtime = src_path.stat().st_mtime
                dest_mtime = dest_path.stat().st_mtime
                
                if src_mtime > dest_mtime + 1:
                    if not has_description(src_path):
                        print(f"  SKIP: {filename} exists but source is missing description")
                        skipped_count += 1
                        continue
                    print(f"  UPDATE: {filename} -> {target_filename} [Source is newer]")
                    shutil.copy2(src_path, dest_path)
                    synced_count += 1
                elif dest_mtime > src_mtime + 1:
                    print(f"  REVERSE SYNC: {target_filename} -> {filename} [Target is newer]")
                    shutil.copy2(dest_path, src_path)
                    synced_count += 1

    print(f"\nSync complete. {synced_count} files synced, {skipped_count} skips.")

if __name__ == "__main__":
    sync_workflows()
