#!/usr/bin/env python3
"""
Configuration Utility for Agent Development Environment.

This script parses `config.toml` and allows shell scripts to query values
such as enabled languages, features, and their associated extras/markers.
"""

import sys
import argparse
from pathlib import Path

# Try importing tomllib (Python 3.11+) or tomli
try:
    import tomllib as toml
except ImportError:
    try:
        import tomli as toml
    except ImportError:
        print("Error: 'tomli' (or python 3.11+) is required.", file=sys.stderr)
        sys.exit(1)


def load_config(root_dir):
    config_path = root_dir / "config.toml"
    if not config_path.exists():
        # Fallback to agent_env/config.toml if in a submodule context
        if (root_dir / "agent_env" / "config.toml").exists():
            config_path = root_dir / "agent_env" / "config.toml"
        elif (root_dir / ".agent" / "config.toml").exists():
            config_path = root_dir / ".agent" / "config.toml"
        else:
            return {}

    try:
        with open(config_path, "rb") as f:
            return toml.load(f)
    except Exception as e:
        print(f"Error loading config.toml: {e}", file=sys.stderr)
        return {}


def get_value(config, path):
    """Retrieve a value from the config dict based on dot-notation path."""
    keys = path.split(".")
    curr = config
    for key in keys:
        if isinstance(curr, dict) and key in curr:
            curr = curr[key]
        else:
            return None
    return curr


def main():
    parser = argparse.ArgumentParser(description="Query config.toml")
    subparsers = parser.add_subparsers(dest="command")

    # Command: get <path>
    get_parser = subparsers.add_parser("get", help="Get a specific value")
    get_parser.add_argument(
        "path", help="Dot-notation path (e.g. languages.python.enabled)"
    )

    # Command: get-extras
    subparsers.add_parser(
        "get-extras", help="Get list of pip extras for enabled features"
    )

    # Command: get-markers
    subparsers.add_parser(
        "get-markers", help="Get pytest markers to EXCLUDE disabled features"
    )

    # Command: get-enabled-languages
    subparsers.add_parser(
        "get-enabled-languages", help="Get list of enabled language keys"
    )

    args = parser.parse_args()

    # Determine project root
    # Valid assumption: this script is in bin/, so root is one level up
    root_dir = Path(__file__).resolve().parent.parent
    config = load_config(root_dir)

    if args.command == "get":
        val = get_value(config, args.path)
        if val is None:
            sys.exit(1)

        # Output suitable for bash
        if isinstance(val, bool):
            print("true" if val else "false")
        elif isinstance(val, list):
            print(" ".join(str(v) for v in val))
        else:
            print(val)

    elif args.command == "get-extras":
        extras = []
        features = config.get("features", {})
        for feat_name, feat_cfg in features.items():
            if feat_cfg.get("enabled", False):
                extra_name = feat_cfg.get("extra")
                if extra_name:
                    extras.append(extra_name)
        print(" ".join(extras))

    elif args.command == "get-markers":
        # Strategy: construct a marker string that EXCLUDES disabled features.
        # e.g. -m "not processing and not renderer"
        # The consumer (validate.sh) will append this to its pytest args.
        terms = []
        features = config.get("features", {})
        for feat_name, feat_cfg in features.items():
            if not feat_cfg.get("enabled", False):
                marker = feat_cfg.get("marker")
                if marker:
                    terms.append(f"not {marker}")

        if terms:
            print(f'-m "{" and ".join(terms)}"')
        else:
            print("")

    elif args.command == "get-enabled-languages":
        langs = []
        languages = config.get("languages", {})
        for lang_name, lang_cfg in languages.items():
            if lang_cfg.get("enabled", False):
                langs.append(lang_name)
        print(" ".join(langs))


if __name__ == "__main__":
    main()
