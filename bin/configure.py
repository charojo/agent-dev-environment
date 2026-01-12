#!/usr/bin/env python3
## @DOC
# ### Setup Wizard
# This script provides an interactive configuration wizard for the project.
# It assists in enabling/disabling languages, features, and managing Python extras.
#
# **Key Functions:**
# - **Interactive Wizard**: Step-by-step configuration for users.
# - **Dependency Safe-check**: Alerts if disabling a feature would remove installed packages.
# - **Shell Integration**: Optionally adds the project's `bin` directory to the user's `PATH`.

"""
Interactive Configuration Script for Agent Development Environment.

Features:
- Wizard-style setup for first run.
- Detecting changes in configuration.
- Safe dependency management (prompting before removal).
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Try helpfully importing toml library
try:
    import tomllib as toml
except ImportError:
    try:
        import tomli as toml
    except ImportError:
        print("Error: 'tomli' (or python 3.11+) is required.", file=sys.stderr)
        sys.exit(1)

# We use tomli_w or just naive string replacement for writing?
# For robust editing, preserving comments is hard with standard libs.
# Since we are an agent environment, maybe we just use simple line rewriting
# or specific key replacement if we want to change config.
# For now, the prompt implies "easy for user to quickly specify options".
# We will implement a simple parser for enabling/disabling known keys.


def get_config_path(root_dir):
    # Priority 1: Check Project Root
    if (root_dir.parent / "config.toml").exists():
        return root_dir.parent / "config.toml"

    # Priority 2: Return Project Root path even if missing (to create it)
    return root_dir.parent / "config.toml"


def load_config(root_dir):
    config_path = get_config_path(root_dir)

    # Initialize from template if missing
    if not config_path.exists():
        template_path = root_dir / "config/templates/config.toml"
        if template_path.exists():
            print(f"✨ Initializing {config_path} from template...")
            shutil.copy2(template_path, config_path)
        else:
            return {}

    with open(config_path, "rb") as f:
        return toml.load(f)


def save_lines(root_dir, lines):
    config_path = get_config_path(root_dir)
    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def toggle_config_in_file(root_dir, key_path, value):
    """
    Naive regex-based toggler to preserve comments.
    Assumes keys are somewhat unique or structured: [section] ... key = val
    This is fragile but suffices for this controlled environment.
    key_path: languages.python.enabled
    """
    is_template_init = False

    config_path = get_config_path(root_dir)

    # Auto-init if missing
    if not config_path.exists():
        load_config(root_dir)  # Triggers template copy

    if not config_path.exists():
        return

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse path
    parts = key_path.split(".")
    section = parts[0]
    if len(parts) > 2:
        # e.g. languages.python.enabled -> section [languages.python]
        section = f"{parts[0]}.{parts[1]}"
        key = parts[2]
    else:
        # features.processing -> [features.processing] (likely)
        # or [section] key
        # In our config.toml structure:
        # [languages.python] -> enabled = true
        section = f"{parts[0]}.{parts[1]}"
        key = parts[-1]

    new_lines = []
    in_section = False

    # Value to string
    val_str = "true" if value else "false"

    for line in lines:
        stripped = line.strip()
        # Handle section headers
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1]
            if current_section == section:
                in_section = True
            else:
                in_section = False

        # Handle key replacement with indentation preservation
        if in_section and stripped.startswith(f"{key} ="):
            # Calculate indentation
            indent = line[: line.find(key)]
            new_lines.append(f"{indent}{key} = {val_str}\n")
        else:
            new_lines.append(line)

    save_lines(root_dir, new_lines)


def wizard(root_dir):
    """
    Runs the interactive configuration wizard.

    @param root_dir The project root directory.
    """
    print("\n🚀  Welcome to the Agent Development Environment Setup!  🚀\n")
    print("This wizard will help you configure the environment for your project.\n")

    config = load_config(root_dir)

    # 1. Languages
    languages = config.get("languages", {})
    for lang, cfg in languages.items():
        enabled = cfg.get("enabled", False)
        desc = cfg.get("description", "")
        print(f"LANGUAGE: {lang} (Currently: {'Enabled' if enabled else 'Disabled'})")
        if desc:
            print(f"  Description: {desc}")
        choice = input(f"  Enable {lang}? [Y/n]: ").strip().lower()
        if choice == "" or choice == "y":
            toggle_config_in_file(root_dir, f"languages.{lang}.enabled", True)
        elif choice == "n":
            toggle_config_in_file(root_dir, f"languages.{lang}.enabled", False)

    print("")

    # 2. Features
    features = config.get("features", {})
    for feat, cfg in features.items():
        enabled = cfg.get("enabled", False)
        desc = cfg.get("description", "")
        print(f"FEATURE: {feat} (Currently: {'Enabled' if enabled else 'Disabled'})")
        if desc:
            print(f"  Description: {desc}")
        choice = input(f"  Enable {feat}? [Y/n]: ").strip().lower()
        if choice == "" or choice == "y":
            toggle_config_in_file(root_dir, f"features.{feat}.enabled", True)
        elif choice == "n":
            toggle_config_in_file(root_dir, f"features.{feat}.enabled", False)

    # 3. Shell Config
    configure_shell_env(root_dir)

    # 4. Workflows
    ensure_ade_workflows(root_dir)

    # Mark setup as complete
    (root_dir / ".agent_setup_complete").touch()
    print("\n✅  Configuration complete!\n")


def get_installed_extras(root_dir):
    """
    Returns a set of currently installed extra names.
    This is best-effort. We can parse 'uv pip freeze' or checking .venv/pyvenv.cfg?
    Actually, uv doesn't explicitly store 'installed extras' metadata easily
    accessible without parsing.
    Faster way: Check if the marker-dependent packages are present?
    Or: We store the last applied extras in a file .agent_last_extras
    """
    state_file = root_dir / ".agent_last_installed_extras"
    if state_file.exists():
        return set(state_file.read_text().strip().split())
    return set()


def save_installed_extras(root_dir, extras):
    state_file = root_dir / ".agent_last_installed_extras"
    state_file.write_text(" ".join(sorted(list(extras))))


def check_diff(root_dir):
    """
    Checks for potential dependency removals based on the current configuration.

    @param root_dir The project root directory.
    @return list of removed extras.
    """
    """
    Checks if current config implies REMOVING libraries compared to what is installed.
    """
    current_installed = get_installed_extras(root_dir)

    # Get target extras from config
    config = load_config(root_dir)
    target_extras = set()
    features = config.get("features", {})
    for feat, cfg in features.items():
        if cfg.get("enabled", False):
            extra = cfg.get("extra")
            if extra:
                target_extras.add(extra)

    # Calculate removed
    removed = current_installed - target_extras

    if removed:
        print(
            "\n⚠️  WARNING: The current configuration disables features that rely on these extras:"
        )
        for r in removed:
            print(f"  - {r}")
        print("\nUpdating the environment will REMOVE these dependencies.")
        return list(removed)

    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true", help="Run setup wizard")
    parser.add_argument("--enable-lang", action="append", help="Enable a language")
    parser.add_argument("--disable-lang", action="append", help="Disable a language")
    parser.add_argument("--enable-feature", action="append", help="Enable a feature")
    parser.add_argument("--disable-feature", action="append", help="Disable a feature")
    parser.add_argument("--non-interactive", action="store_true", help="Bypass prompts")
    parser.add_argument("--check-diff", action="store_true", help="Check for dependency removals")
    parser.add_argument(
        "--confirm-removal",
        action="store_true",
        help="Exit 0 if safe or confirmed, 1 if aborted",
    )

    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent

    # Quiet mode or non-interactive bypass
    is_quiet = args.non_interactive or (hasattr(args, "quiet") and args.quiet)

    # Determine if we should run the wizard
    should_run_wizard = args.interactive or (
        not args.enable_lang
        and not args.disable_lang
        and not args.enable_feature
        and not args.disable_feature
        and not args.check_diff
        and not args.non_interactive
    )

    if should_run_wizard:
        wizard(root_dir)
        ensure_docs_gen_ignored(root_dir)
        ensure_ade_workflows(root_dir)
        sys.exit(0)

    if not is_quiet:
        print(f"Applying configuration changes to {root_dir}/config.toml...")

    # Non-interactive configuration
    if args.enable_lang:
        for lang in args.enable_lang:
            toggle_config_in_file(root_dir, f"languages.{lang}.enabled", True)
    if args.disable_lang:
        for lang in args.disable_lang:
            toggle_config_in_file(root_dir, f"languages.{lang}.enabled", False)
    if args.enable_feature:
        for feat in args.enable_feature:
            toggle_config_in_file(root_dir, f"features.{feat}.enabled", True)
    if args.disable_feature:
        for feat in args.disable_feature:
            toggle_config_in_file(root_dir, f"features.{feat}.enabled", False)

    # Always ensure docs/gen is ignored whenever configuration is updated
    ensure_docs_gen_ignored(root_dir)
    ensure_ade_workflows(root_dir)

    if args.check_diff:
        removed = check_diff(root_dir)
        if removed:
            # We are just checking, so return code indicating change?
            # Or print details suitable for caller.
            # If we want to use this in a script:
            # validate.sh calls this. If output not empty, validate prompts.
            pass
        sys.exit(0)

    # Helper command to just dump extras for ensure_env to use AND SAVE state
    # But ensure_env handles the actual installation.
    # We need a hook that runs AFTER ensure_env to update the .agent_last_installed_extras?
    # Or ensure_env calls a python script to save state.


def configure_shell_env(root_dir):
    """
    Helps the user add the agent/bin directory to their PATH.
    """
    bin_dir = (root_dir / "bin").resolve()
    print("\n--- Shell Configuration ---")
    print(
        f"Adding '{bin_dir}' to your PATH allows you to run 'validate.sh' and other tools directly."
    )

    choice = (
        input("Do you want to add the Agent Environment bin directory to your PATH? [y/N]: ")
        .strip()
        .lower()
    )
    if choice != "y":
        return

    # Detect shell
    shell = os.environ.get("SHELL", "")
    rc_file = None

    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "bash" in shell:
        rc_file = Path.home() / ".bashrc"
    else:
        print(f"Could not detect supported shell (bash/zsh). Current SHELL: {shell}")
        print("Please manually add the following to your shell configuration:")
        print(f"  export PATH=$PATH:{bin_dir}")
        return

    # Check if already in rc file
    export_line = f"export PATH=$PATH:{bin_dir}"

    if rc_file.exists():
        content = rc_file.read_text()
        if str(bin_dir) in content:
            print(f"Looks like {bin_dir} is already referenced in {rc_file}. Skipping.")
            return

    # Append
    print(f"Appending to {rc_file}...")
    try:
        with open(rc_file, "a") as f:
            f.write(f"\n# Agent Development Environment\n{export_line}\n")
        print("✅ Added to config.")
        print(f"👉 Please run: source {rc_file}")
    except Exception as e:
        print(f"Error writing to {rc_file}: {e}")


def ensure_ade_workflows(root_dir):
    """
    Links ADE workflows to .agent/workflows with an 'ade-' prefix.
    """
    project_root = root_dir.parent
    agent_workflows_dir = project_root / ".agent" / "workflows"
    source_workflows_dir = root_dir / "workflows"

    if not source_workflows_dir.exists():
        return

    if not agent_workflows_dir.exists():
        print(f"Creating {agent_workflows_dir}...")
        agent_workflows_dir.mkdir(parents=True, exist_ok=True)

    for workflow_file in source_workflows_dir.glob("*.md"):
        target_name = workflow_file.name
        target_path = agent_workflows_dir / target_name

        # Relative link
        # From .agent/workflows/xxx-ade.md to ../../agent_env/workflows/xxx-ade.md
        rel_source = os.path.relpath(workflow_file, agent_workflows_dir)

        if target_path.exists() or target_path.is_symlink():
            if target_path.is_symlink() and os.readlink(target_path) == rel_source:
                continue
            target_path.unlink()

        print(f"Linking {target_name} -> {workflow_file.name}")
        target_path.symlink_to(rel_source)


def ensure_docs_gen_ignored(root_dir):
    """
    Ensures that the docs/gen directory is present in the project's .gitignore.
    """
    project_root = root_dir.parent
    agent_dir_entry = ".agent/\n"
    gitignore_path = project_root / ".gitignore"

    ignore_entry = "docs/gen/\n"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        needs_write = False
        if "docs/gen/" not in content:
            content += f"\n# Automated Doc Generation\n{ignore_entry}"
            needs_write = True
        if ".agent/" not in content:
            content += f"\n# Agent Metadata\n{agent_dir_entry}"
            needs_write = True

        if needs_write:
            print("Updating .gitignore...")
            gitignore_path.write_text(content)
    else:
        print("Creating .gitignore...")
        gitignore_path.write_text(
            f"# Automated Doc Generation\n{ignore_entry}\n# Agent Metadata\n{agent_dir_entry}"
        )


if __name__ == "__main__":
    main()
