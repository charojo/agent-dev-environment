#!/usr/bin/env python3
# ## @DOC
# ### Ade Update Workflow Docs
# Updates workflow documentation references in README or specified files.


import argparse
import re
import subprocess
import sys
import os
from pathlib import Path
from ADE_ownership import is_repo_owned_by_current_user

def get_project_root():
    """Returns the project root directory."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], universal_newlines=True
        ).strip()
        return Path(root)
    except subprocess.CalledProcessError:
        # Fallback to current script's grandparent if not in a git repo
        return Path(__file__).resolve().parent.parent.parent

def get_workflows(workflows_dir):
    """Scans the workflows directory and extracts descriptions."""
    workflows = []
    if not workflows_dir.exists():
        return workflows

    for workflow_file in workflows_dir.rglob("*.md"):
        # Ignore hidden files/dirs EXCEPT the workflows_dir itself if it happens to be hidden
        rel_to_workflows = workflow_file.relative_to(workflows_dir)
        if any(part.startswith(".") for part in rel_to_workflows.parts):
            continue
            
        cmd_name = f"/{workflow_file.stem}"
        description = "No description provided."

        try:
            content = workflow_file.read_text()
            # Extract description from frontmatter
            match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
            if match:
                description = match.group(1).strip()
        except Exception as e:
            print(f"Error reading {workflow_file}: {e}")

        workflows.append((cmd_name, description))

    return sorted(workflows)


def update_docs(target_file, workflows):
    """Updates the workflows section in the target file."""
    if not target_file.exists():
        print(f"Error: {target_file} does not exist. Skipping.")
        return False
        
    if not is_repo_owned_by_current_user(target_file):
        print(f"Skipping {target_file} (repository not owned by current user).")
        return False

    content = target_file.read_text()

    start_marker = "<!-- WORKFLOWS_START -->"
    end_marker = "<!-- WORKFLOWS_END -->"

    if start_marker not in content or end_marker not in content:
        # If markers are missing but it's README.md, maybe we should warn
        # If it's a specific target, we definitely skip
        print(f"Markers not found in {target_file}. Skipping.")
        return False

    new_section = f"{start_marker}\n"
    new_section += "| Command | Description |\n"
    new_section += "| :--- | :--- |\n"

    for cmd, desc in workflows:
        new_section += f"| `{cmd}` | {desc} |\n"

    new_section += f"{end_marker}"

    # Replace the section
    pattern = re.compile(
        f"{re.escape(start_marker)}.*{re.escape(end_marker)}", re.DOTALL
    )
    new_content = pattern.sub(new_section, content)

    if new_content != content:
        target_file.write_text(new_content)
        print(f"Updated {target_file} with {len(workflows)} workflows.")
        return True
    else:
        print(f"No changes needed for {target_file}.")
        return False


def main(argv=None):
    project_root = get_project_root()
    
    parser = argparse.ArgumentParser(description="Update workflow documentation references.")
    parser.add_argument(
        "--target",
        help="Target markdown file to update (relative to project root)",
        default="README.md"
    )
    parser.add_argument(
        "--workflows-dir",
        help="Directory containing workflow files",
        default=".agent/workflows"
    )
    args = parser.parse_args(argv)

    target_path = project_root / args.target
    workflows_path = project_root / args.workflows_dir
    
    workflows = get_workflows(workflows_path)
    if not workflows:
        print(f"No workflows found in {workflows_path}")
        return

    update_docs(target_path, workflows)


if __name__ == "__main__":
    main()
