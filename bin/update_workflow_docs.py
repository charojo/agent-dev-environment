#!/usr/bin/env python3
import re
from pathlib import Path

WORKFLOWS_DIR = Path("workflows")
DOCS_FILE = Path("docs/HOWTO_UseAgentDev.md")


def get_workflows():
    workflows = []
    if not WORKFLOWS_DIR.exists():
        return workflows

    for workflow_file in WORKFLOWS_DIR.rglob("*.md"):
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


def update_docs():
    workflows = get_workflows()

    if not DOCS_FILE.exists():
        print(f"Error: {DOCS_FILE} does not exist. Please create it first.")
        return

    content = DOCS_FILE.read_text()

    start_marker = "<!-- WORKFLOWS_START -->"
    end_marker = "<!-- WORKFLOWS_END -->"

    if start_marker not in content or end_marker not in content:
        print(f"Error: Markers not found in {DOCS_FILE}")
        return

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

    DOCS_FILE.write_text(new_content)
    print(f"Updated {DOCS_FILE} with {len(workflows)} workflows.")


if __name__ == "__main__":
    update_docs()
