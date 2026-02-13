#!/usr/bin/env python3
import os
import shutil
import re
from pathlib import Path

# Paths are relative to the script location for portability
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent.parent
SOURCE_DIR = REPO_ROOT / ".agent" / "workflows"
DEST_DIR = REPO_ROOT / "agent_env" / "workflows"

def has_description(file_path):
    """Checks if the markdown file has a description in its YAML frontmatter."""
    try:
        with open(file_path, "r") as f:
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
    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return

    if not DEST_DIR.exists():
        print(f"Creating destination directory: {DEST_DIR}")
        DEST_DIR.mkdir(parents=True)

    # Get all .md files from both directories
    src_files = {f.name: f for f in SOURCE_DIR.glob("*.md")}
    dest_files = {f.name: f for f in DEST_DIR.glob("*.md")}
    all_filenames = set(src_files.keys()) | set(dest_files.keys())

    synced_count = 0
    skipped_count = 0

    print(f"Syncing workflows between {SOURCE_DIR} and {DEST_DIR}...")

    for filename in sorted(all_filenames):
        src_path = SOURCE_DIR / filename
        dest_path = DEST_DIR / filename
        
        src_exists = src_path.exists()
        dest_exists = dest_path.exists()

        # CASE 1: Only in Source -> Sync to Dest
        if src_exists and not dest_exists:
            if not has_description(src_path):
                print(f"SKIP: {filename} is missing 'description' (skipping sync to agent_env).")
                skipped_count += 1
                continue
            print(f"SYNC: {filename} (.agent -> agent_env) [New file]")
            shutil.copy2(src_path, dest_path)
            synced_count += 1
            continue

        # CASE 2: Only in Dest -> Sync to Source
        if dest_exists and not src_exists:
            print(f"SYNC: {filename} (agent_env -> .agent) [New file]")
            shutil.copy2(dest_path, src_path)
            synced_count += 1
            continue

        # CASE 3: Both exist -> Compare timestamps
        src_mtime = src_path.stat().st_mtime
        dest_mtime = dest_path.stat().st_mtime
        
        # Allow 1 second difference for filesystem variations
        if src_mtime > dest_mtime + 1:
            if not has_description(src_path):
                print(f"SKIP: {filename} is missing 'description' (skipping update to agent_env).")
                skipped_count += 1
                continue
            print(f"SYNC: {filename} (.agent -> agent_env) [Newer]")
            shutil.copy2(src_path, dest_path)
            synced_count += 1
        elif dest_mtime > src_mtime + 1:
            print(f"SYNC: {filename} (agent_env -> .agent) [Newer]")
            shutil.copy2(dest_path, src_path)
            synced_count += 1

    print(f"\nSync complete. {synced_count} files synced, {skipped_count} skips due to missing descriptions.")

if __name__ == "__main__":
    sync_workflows()
