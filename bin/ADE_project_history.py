#!/usr/bin/env python3
## @DOC
# ### Project Analysis & History
# This tool analyzes the codebase to generate statistical reports. It works in two modes:
# 1. **History Mode**: Traverses git-history to generate a time-series report.
# 2. **Local Mode**: Analyzes the current filesystem state (replaces the old analyze_project.py).
#
# **Key Features:**
# - Git history traversal.
# - Incremental history updates.
# - Local filesystem analysis.
# - Language-specific metrics (LOC, TODOs, FIXMEs).
# - Configuration health reporting.

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure we can import config_utils from the same directory
sys.path.append(str(Path(__file__).parent))
try:
    import ADE_config_utils as config_utils
except ImportError:
    pass


def run_git_command(args, cwd):
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # print(f"Error running git command: {e}", file=sys.stderr)
        return None


def get_commits(cwd, limit=None, since_commit=None, date_start=None):
    """Get a list of commits (hash, date, author, subject)."""
    args = ["log", "--pretty=format:%H|%ad|%an|%s", "--date=short"]

    if date_start:
        # Convert YYYYMMDD to YYYY-MM-DD if needed
        if len(date_start) == 8 and date_start.isdigit():
            date_start = f"{date_start[:4]}-{date_start[4:6]}-{date_start[6:]}"
        args.append(f"--since={date_start}")

    if since_commit:
        # Get commits from since_commit..HEAD
        args.append(f"{since_commit}..HEAD")

    output = run_git_command(args, cwd)
    if not output:
        return []

    commits = []
    seen_dates = set()
    for line in output.split("\n"):
        parts = line.split("|", 3)
        if len(parts) == 4:
            commit_date = parts[1]
            # ONLY TAKE THE LATEST COMMIT PER DAY
            # Since git log is newest first, the first time we see a date, it's the latest for that day.
            if commit_date not in seen_dates:
                commits.append(
                    {
                        "hash": parts[0],
                        "date": commit_date,
                        "author": parts[2],
                        "subject": parts[3],
                    }
                )
                seen_dates.add(commit_date)

    if limit:
        commits = commits[:limit]

    return commits


def get_files_at_commit(cwd, commit_hash):
    """Get a list of files present at a specific commit."""
    output = run_git_command(["ls-tree", "-r", "--name-only", commit_hash], cwd)
    if not output:
        return []
    return output.split("\n")


def get_file_content_git(cwd, commit_hash, file_path):
    """Get the content of a file at a specific commit."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{file_path}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="ignore",
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except Exception:
        return ""


def analyze_content(content):
    """Analyze the content of a file."""
    lines = content.splitlines()
    loc = 0
    todos = 0
    fixmes = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        loc += 1
        if "TO" + "DO" in line:
            todos += 1
        if "FIX" + "ME" in line:
            fixmes += 1

    return loc, todos, fixmes


def is_test_file(file_path):
    """Check if a file looks like a test file."""
    fp = file_path.lower()
    basename = os.path.basename(fp)
    parts = set(fp.split(os.sep))
    return (
        not parts.isdisjoint({"test", "tests", "__tests__"})
        or basename.startswith("test_")
        or basename.endswith("_test.py")
        or any(
            basename.endswith(ext)
            for ext in [
                ".test.js",
                ".test.jsx",
                ".test.ts",
                ".test.tsx",
                ".spec.js",
                ".spec.jsx",
                ".spec.ts",
                ".spec.tsx",
            ]
        )
    )


def count_lines_file(file_path):
    """Reads a local file and counts lines/markers."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return analyze_content(f.read())
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0, 0, 0


# --- Local Analysis Logic (Migration from ADE_analyze_project.py) ---


def run_local_analysis(target_repo_root, ade_root, args):
    """Analyzes the current filesystem (Local Mode)."""

    # Run validation if requested
    validation_metrics = {}
    if args.validate:
        print("Running full validation suite (validate.sh --full)...", file=sys.stderr)
        try:
            # We run validate.sh --full and capture its output
            validate_bin = ade_root / "agent_env" / "bin" / "validate.sh"
            if not validate_bin.exists():
                validate_bin = ade_root / "bin" / "validate.sh"

            result = subprocess.run(
                [str(validate_bin), "--full"],
                cwd=target_repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout

            # Parse metrics from "=== Detailed Metrics (ASCII) ==="
            # Frontend   | 325 passed           | 60%        | 6s
            # Backend    | 138 passed...        | 82%        | 18s
            # TOTAL                               71.00% code coverage in 87s

            frontend_match = re.search(r"Frontend\s*\|[^|]*\|\s*([\d.]+)%", output)
            backend_match = re.search(r"Backend\s*\|[^|]*\|\s*([\d.]+)%", output)
            total_match = re.search(r"TOTAL\s*([\d.]+)%", output)

            if frontend_match:
                validation_metrics["Frontend"] = frontend_match.group(1)
            if backend_match:
                validation_metrics["Backend"] = backend_match.group(1)
            if total_match:
                validation_metrics["Total"] = total_match.group(1)

        except Exception as e:
            print(f"Error running validation: {e}", file=sys.stderr)

    # Check config
    try:
        config = config_utils.load_config(target_repo_root)
    except NameError:
        config = {}

    languages_config = config.get("languages", {})
    if "markdown" not in languages_config:
        languages_config["markdown"] = {"enabled": True, "extensions": [".md"]}
    if "css" not in languages_config:
        languages_config["css"] = {"enabled": True, "extensions": [".css"]}
    if "shell" not in languages_config:
        languages_config["shell"] = {"enabled": True, "extensions": [".sh"]}
    if "json" not in languages_config:
        languages_config["json"] = {"enabled": True, "extensions": [".json"]}

    results = {}
    enabled_extensions = {}

    # Initialize
    for lang_name, lang_cfg in languages_config.items():
        if lang_cfg.get("enabled", True):
            results[lang_name] = {"files": 0, "loc": 0, "todos": 0, "fixmes": 0}
            for ext in lang_cfg.get("extensions", []):
                enabled_extensions[ext] = lang_name

    # Use git ls-files to respect .gitignore
    try:
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
        git_files = subprocess.check_output(cmd, cwd=target_repo_root, text=True).splitlines()
    except subprocess.CalledProcessError:
        # Fallback to os.walk if not a git repo (unlikely here but safe)
        git_files = []
        for root, _, files in os.walk(target_repo_root):
            for file in files:
                git_files.append(os.path.relpath(os.path.join(root, file), target_repo_root))

    for file_rel_path in git_files:
        file_path = target_repo_root / file_rel_path
        filename = os.path.basename(file_rel_path)

        # Skip common lock files
        if filename in [
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "poetry.lock",
        ]:
            continue

        _, ext = os.path.splitext(file_rel_path)

        if ext in enabled_extensions:
            lang = enabled_extensions[ext]
            loc, todos, fixmes = count_lines_file(file_path)

            results[lang]["files"] += 1
            results[lang]["loc"] += loc
            results[lang]["todos"] += todos
            results[lang]["fixmes"] += fixmes

    # Output
    sorted_langs = sorted(results.keys())
    metrics = ["Files", "LOC", "T-O-D-Os", "F-I-X-M-Es"]
    keys = ["files", "loc", "todos", "fixmes"]

    if args.markdown:
        print_markdown_table_local(results, sorted_langs, metrics, keys)
    elif args.dual:
        print_markdown_table_local(results, sorted_langs, metrics, keys)
        print("\n=== Codebase Health Summary (ASCII) ===", file=sys.stderr)
        # We need to manually print to stderr for the dual mode ASCII part
        print_text_table_to_stream(sys.stderr, results, sorted_langs, metrics, keys)
    else:
        print_text_table_to_stream(sys.stdout, results, sorted_langs, metrics, keys)

    # Config Results
    results_file = ade_root / "logs" / "config_test_results.json"
    print_config_results(results_file, markdown=args.markdown or args.dual)

    # If we have validation metrics, print them
    if validation_metrics and args.markdown:
        print("\n### Execution Coverage (Latest)")
        print("| Tier | Coverage % | Status |")
        print("| :--- | :--- | :--- |")
        for tier, cov in validation_metrics.items():
            print(f"| {tier} | {cov}% | Verified via validate.sh |")


def print_markdown_table_local(results, sorted_langs, metrics, keys):
    def format_lang(lang):
        if lang == "css":
            return "CSS"
        if lang == "json":
            return "JSON"
        return lang.title()

    header = (
        "| Metric | "
        + " | ".join([format_lang(lang) for lang in sorted_langs])
        + " | Total |"
    )
    divider = "| :--- | " + " | ".join([":---" for _ in sorted_langs]) + " | :--- |"
    print(header)
    print(divider)
    for metric, key in zip(metrics, keys):
        row = f"| {metric} | "
        total_val = 0
        for lang in sorted_langs:
            val = results[lang][key]
            total_val += val
            row += f"{val} | "
        row += f"{total_val} |"
        print(row)


def print_text_table_to_stream(stream, results, sorted_langs, metrics, keys):
    def format_lang(lang):
        if lang == "css":
            return "CSS"
        if lang == "json":
            return "JSON"
        return lang.title()

    header = f"{'Metric':<20}"
    for lang in sorted_langs:
        col_name = format_lang(lang)
        header += f"{col_name:<15}"
    header += f"{'Total':<15}"
    print(header, file=stream)
    print("-" * len(header), file=stream)
    for metric, key in zip(metrics, keys):
        row = f"{metric:<20}"
        total_val = 0
        for lang in sorted_langs:
            val = results[lang][key]
            total_val += val
            row += f"{val:<15}"
        row += f"{total_val:<15}"
        print(row, file=stream)
    print("-" * 75, file=stream)


def print_config_results(results_file, markdown=False):
    if not results_file.exists():
        return
    try:
        with open(results_file, "r") as f:
            report = json.load(f)

        if markdown:
            print("\n### Configuration Test Results")
            print("| Config | Status | Total Size | Venv | Node |")
            print("| :--- | :--- | :--- | :--- | :--- |")
            for r in report:
                print(
                    f"| {r['config']} | {r['status']} | {r['total_size']} | "
                    f"{r['venv_size']} | {r['node_modules_size']} |"
                )
        else:
            print("\n=== Configuration Test Results ===")
            header = f"{'Config':<20} | {'Status':<6} | {'Total':<10} | {'Venv':<10} | {'Node':<10}"
            print(header)
            print("-" * len(header))
            for r in report:
                print(
                    f"{r['config']:<20} | {r['status']:<6} | "
                    f"{r['total_size']:<10} | {r['venv_size']:<10} | "
                    f"{r['node_modules_size']:<10}"
                )
            print("-" * 70)
    except Exception as e:
        print(f"Error reading config results: {e}", file=sys.stderr)


# --- History Logic ---


def parse_existing_history(file_path):
    """
    Parses the existing markdown report to find the most recent commit hash.
    Assumes format: | Date | Commit | ...
    """
    if not os.path.exists(file_path):
        return None

    last_commit = None
    with open(file_path, "r") as f:
        for line in f:
            m = re.search(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*`([^`]+)`", line)
            if m:
                last_commit = m.group(1)
                break
    return last_commit


def parse_requirements_content(content):
    """Counts total and open requirements from markdown content."""
    total = 0
    open_reqs = 0
    # Look for table rows starting with | **REQ-
    lines = content.splitlines()
    for line in lines:
        if re.search(r"\|\s*\*\*REQ-\d+\*\*", line):
            total += 1
            # Check Status column (index 2 usually)
            parts = [p.strip() for p in line.split("|")]
            if len(parts) > 3:
                status = parts[3].lower()
                # Open if Planned, Partial, Designed, or In Progress
                if any(
                    s in status
                    for s in ["planned", "partial", "designed", "in progress"]
                ):
                    open_reqs += 1
    return open_reqs, total


def parse_issues_content(content):
    """Counts total and open issues from markdown content."""
    total = 0
    open_issues = 0
    # Look for table rows starting with
    # | **CR- / **HP- / **LP- / **DS- / **DX- / **DEF- / **SEC- / **TASK- / **TECH-
    lines = content.splitlines()
    for line in lines:
        if re.search(r"\|\s*\*\*(?:CR|HP|LP|DS|DX|DEF|SEC|TASK|TECH)-", line):
            total += 1
            # Check Status column
            parts = [p.strip().lower() for p in line.split("|")]
            # Search for status in columns 2-5
            is_closed = any(
                any(s in col for s in ["fixed", "resolved", "done", "complete", "✅"])
                for col in parts[2:6]
            )
            if not is_closed:
                open_issues += 1
    return open_issues, total


def parse_data_row(line):
    """Parses a markdown table row into a data dictionary."""
    parts = [p.strip() for p in line.split("|")]
    # Expected: ['', Date, Commit, Author, Total, Py, TS, MD, CSS, SH, JSON, TestFiles, TestLOC, TP,
    # TT, TS, TODOs, FIXMEs, Req, Iss, '']
    if len(parts) < 20:
        return None

    try:
        # Extract date and commit
        date = parts[1]
        commit = parts[2].replace("`", "")
        author = parts[3]
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            return None

        # Helper to split "Open / Total"
        def split_stat(s):
            vals = s.split("/")
            if len(vals) == 2:
                return int(vals[0].strip()), int(vals[1].strip())
            return int(vals[0].strip()), 0

        return {
            "date": date,
            "commit": commit,
            "author": author,
            "loc_total": int(parts[4]),
            "loc_py": int(parts[5]),
            "loc_ts": int(parts[6]),
            "loc_md": int(parts[7]),
            "loc_css": int(parts[8]),
            "loc_sh": int(parts[9]),
            "loc_json": int(parts[10]),
            "test_files": int(parts[11]),
            "test_loc_total": int(parts[12]),
            "test_loc_py": int(parts[13]),
            "test_loc_ts": int(parts[14]),
            "test_loc_sh": int(parts[15]),
            "todos": split_stat(parts[16])[0],
            "md_todos": split_stat(parts[16])[1],
            "fixmes": split_stat(parts[17])[0],
            "md_fixmes": split_stat(parts[17])[1],
            "open_reqs": split_stat(parts[18])[0],
            "total_reqs": split_stat(parts[18])[1],
            "open_issues": split_stat(parts[19])[0],
            "total_issues": split_stat(parts[19])[1],
        }
    except (ValueError, IndexError):
        return None


def run_history_analysis(target_repo_root, ade_root, args):
    cwd = target_repo_root
    since_commit = args.since

    existing_content = []

    # Use specified output path or default to docs/HISTORY.md in target repo
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = target_repo_root / "docs" / "HISTORY.md"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Intelligent Merging Logic
    daily_data = {}
    if os.path.exists(output_path) and not args.refresh:
        print(f"Loading existing data from {output_path}...", file=sys.stderr)
        with open(output_path, "r") as f:
            for line in f:
                row_data = parse_data_row(line)
                if row_data:
                    # We store the latest record per day found in the file
                    if row_data["date"] not in daily_data:
                        daily_data[row_data["date"]] = row_data

        if daily_data:
            earliest = min(daily_data.keys())
            latest = max(daily_data.keys())
            print(f"Found {len(daily_data)} days already tracked ({earliest} to {latest}).", file=sys.stderr)

    # Determine what to fetch
    fetch_since = args.date_start
    if not fetch_since and daily_data:
        # Default to the latest tracked date if no specific start given
        fetch_since = max(daily_data.keys())

    commits = get_commits(cwd, args.limit, since_commit=None, date_start=fetch_since)

    # Filter out redundant commits (Don't repull)
    # Exception: Allow updating today's entry
    today_str = datetime.now().strftime("%Y-%m-%d")
    final_commits_to_process = []
    for c in commits:
        if c["date"] not in daily_data:
            final_commits_to_process.append(c)
        elif c["date"] == today_str:
            # Check if hash is different (latest commit of the day might have changed)
            if c["hash"][:7] != daily_data[today_str]["commit"]:
                final_commits_to_process.append(c)

    if not final_commits_to_process:
        print("Everything up to date. Refreshing report and charts...", file=sys.stderr)
        if not daily_data:
            return
    else:
        print(f"Found {len(final_commits_to_process)} commits missing from history. Processing...", file=sys.stderr)

    commits = final_commits_to_process

    # If no new commits, we skip the analysis loop but still regenerate plots/report
    # from the daily_data we loaded or collected.

    if args.reverse:
        commits.reverse()

    history_data = []
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".md": "markdown",
        ".css": "css",
        ".sh": "shell",
        ".json": "json",
    }

    processed_count = 0
    for commit in commits:
        processed_count += 1
        print(
            f"[{processed_count}/{len(commits)}] Processing {commit['hash'][:7]}...",
            file=sys.stderr,
            end="\r",
        )

        files = get_files_at_commit(cwd, commit["hash"])
        stats = {
            "commit": commit["hash"][:7],
            "date": commit["date"],
            "author": commit["author"],
            "todos": 0,
            "fixmes": 0,
            "md_todos": 0,
            "md_fixmes": 0,
            # Source code LOC (non-test)
            "loc_py": 0,
            "loc_ts": 0,
            "loc_md": 0,
            "loc_css": 0,
            "loc_sh": 0,
            "loc_json": 0,
            "loc_total": 0,
            # Test code LOC
            "test_loc_py": 0,
            "test_loc_ts": 0,
            "test_loc_sh": 0,
            "test_loc_total": 0,
            "test_files": 0,
            "open_reqs": 0,
            "total_reqs": 0,
            "open_issues": 0,
            "total_issues": 0,
        }

        for file_path in files:
            # Special Handling for Requirements and Issues
            if file_path == "docs/REQUIREMENTS.md":
                content = get_file_content_git(cwd, commit["hash"], file_path)
                stats["open_reqs"], stats["total_reqs"] = parse_requirements_content(
                    content
                )
            elif file_path == "docs/ISSUES.md":
                content = get_file_content_git(cwd, commit["hash"], file_path)
                stats["open_issues"], stats["total_issues"] = parse_issues_content(
                    content
                )

            ext = os.path.splitext(file_path)[1]
            if ext not in lang_map:
                continue

            content = get_file_content_git(cwd, commit["hash"], file_path)
            loc, todos, fixmes = analyze_content(content)

            lang = lang_map[ext]
            if lang == "markdown":
                stats["md_todos"] += todos
                stats["md_fixmes"] += fixmes
            else:
                stats["todos"] += todos
                stats["fixmes"] += fixmes
            is_test = is_test_file(file_path)

            if is_test:
                stats["test_files"] += 1
                stats["test_loc_total"] += loc
                if lang == "python":
                    stats["test_loc_py"] += loc
                elif lang in ["typescript", "javascript"]:
                    stats["test_loc_ts"] += loc
                elif lang == "shell":
                    stats["test_loc_sh"] += loc
            else:
                # Non-test source code
                stats["loc_total"] += loc
                if lang == "python":
                    stats["loc_py"] += loc
                elif lang in ["typescript", "javascript"]:
                    stats["loc_ts"] += loc
                elif lang == "markdown":
                    stats["loc_md"] += loc
                elif lang == "css":
                    stats["loc_css"] += loc
                elif lang == "shell":
                    stats["loc_sh"] += loc
                elif lang == "json":
                    filename = os.path.basename(file_path)
                    if filename not in [
                        "package-lock.json",
                        "pnpm-lock.yaml",
                        "yarn.lock",
                        "poetry.lock",
                    ]:
                        stats["loc_json"] += loc

        daily_data[stats["date"]] = stats

    print("\nAnalysis complete.", file=sys.stderr)

    # Generate Unified Graph Data and Report Rows
    # Report rows should be ALL data, sorted Newest -> Oldest
    report_rows = sorted(daily_data.values(), key=lambda x: x["date"], reverse=True)
    
    # Graph data can be filtered if a specific date-start was requested for this run
    graph_data = sorted(daily_data.values(), key=lambda x: x["date"])
    if args.date_start:
        plot_start = args.date_start
        if len(plot_start) == 8 and plot_start.isdigit():
            plot_start = f"{plot_start[:4]}-{plot_start[4:6]}-{plot_start[6:]}"
        graph_data = [d for d in graph_data if d["date"] >= plot_start]

    new_rows = []
    for row in report_rows:
        # Table Includes BOTH (C / M)
        todo_str = f"{row['todos']} / {row['md_todos']}"
        fixme_str = f"{row['fixmes']} / {row['md_fixmes']}"
        req_str = f"{row['open_reqs']} / {row['total_reqs']}"
        iss_str = f"{row['open_issues']} / {row['total_issues']}"
        new_rows.append(
            f"| {row['date']} | `{row['commit']}` | {row['author']} | "
            f"{row['loc_total']} | {row['loc_py']} | {row['loc_ts']} | "
            f"{row['loc_md']} | {row['loc_css']} | {row['loc_sh']} | {row['loc_json']} | "
            f"{row['test_files']} | {row['test_loc_total']} | {row['test_loc_py']} | "
            f"{row['test_loc_ts']} | {row['test_loc_sh']} | {todo_str} | {fixme_str} | "
            f"{req_str} | {iss_str} |"
        )

    # COMBINING
    final_output = [
        "# Project History Analysis",
        f"Generated on {datetime.now().isoformat()}",
        "",
        "| Date | Commit | Author | Total | Py | TS/JS | MD | CSS | SH | JSON | Tests | T-LOC | Py-T | TS-T | SH-T | TODO (C/M) | FIXME (C/M) | Req | Iss |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    final_output.extend(new_rows)

    # graph_data is already built and sorted above

    # Generate Charts
    charts = []

    # SVG Generator Class (Embedded to avoid dependencies)
    class SimpleSVGChart:
        def __init__(self, title, width=800, height=400):
            self.title = title
            self.width = width
            self.height = height
            self.padding = 80
            self.lines = []
            self.x_labels = []

        def add_line(self, data, label, color):
            self.lines.append({"data": data, "label": label, "color": color})

        def set_x_labels(self, labels):
            self.x_labels = labels

        def generate(self):
            # Calculate ranges
            all_values = [v for line in self.lines for v in line["data"]]
            if not all_values:
                return ""
            max_val = max(all_values)
            min_val = 0  # Always start at 0 for context

            # Helper for scaling
            def get_y(val):
                if max_val == min_val:
                    return self.height - self.padding
                ratio = (val - min_val) / (max_val - min_val)
                plot_height = self.height - (2 * self.padding)
                return self.height - self.padding - (ratio * plot_height)

            def get_x(idx, count):
                plot_width = self.width - (2 * self.padding)
                if count <= 1:
                    return self.padding + (plot_width / 2)
                step = plot_width / (count - 1)
                return self.padding + (idx * step)

            svg = [
                f'<svg width="{self.width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg">'
            ]

            # Background
            svg.append('<rect width="100%" height="100%" fill="white" />')

            def escape_xml(s):
                """Basic XML escaping for special characters."""
                return (
                    str(s)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&apos;")
                )

            # Title
            svg.append(
                f'<text x="{self.width / 2}" y="30" text-anchor="middle" '
                f'font-family="sans-serif" font-size="20" font-weight="bold">'
                f"{escape_xml(self.title)}</text>"
            )

            # Axes
            plot_bottom = self.height - self.padding
            plot_top = self.padding
            plot_left = self.padding
            plot_right = self.width - self.padding

            svg.append(
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" '
                f'y2="{plot_bottom}" stroke="black" stroke-width="2"/>'
            )  # X Axis
            svg.append(
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_left}" '
                f'y2="{plot_top}" stroke="black" stroke-width="2"/>'
            )  # Y Axis

            # Y Labels (5 steps)
            for i in range(6):
                val = min_val + (max_val - min_val) * (i / 5)
                y = get_y(val)
                svg.append(
                    f'<line x1="{plot_left - 5}" y1="{y}" x2="{plot_left}" '
                    f'y2="{y}" stroke="black"/>'
                )
                svg.append(
                    f'<text x="{plot_left - 10}" y="{y + 5}" text-anchor="end" '
                    f'font-family="sans-serif" font-size="12">{escape_xml(int(val))}</text>'
                )
                svg.append(
                    f'<line x1="{plot_left}" y1="{y}" x2="{plot_right}" y2="{y}" '
                    f'stroke="#ddd" stroke-dasharray="4"/>'
                )  # Grid

            # X Labels (Sampled if too many) - Simplified logic
            count = len(self.x_labels)
            step = max(1, count // 10)
            for i in range(0, count, step):
                x = get_x(i, count)
                svg.append(
                    f'<line x1="{x}" y1="{plot_bottom}" x2="{x}" '
                    f'y2="{plot_bottom + 5}" stroke="black"/>'
                )
                svg.append(
                    f'<text x="{x}" y="{plot_bottom + 10}" text-anchor="start" '
                    f'font-family="sans-serif" font-size="10" '
                    f'transform="rotate(45, {x}, {plot_bottom + 10})">'
                    f"{escape_xml(self.x_labels[i])}</text>"
                )

            # Legend
            legend_x = plot_right - 150
            legend_y = plot_top
            for i, line in enumerate(self.lines):
                ly = legend_y + (i * 20)
                svg.append(
                    f'<rect x="{legend_x}" y="{ly}" width="10" height="10" fill="{line["color"]}"/>'
                )
                svg.append(
                    f'<text x="{legend_x + 15}" y="{ly + 10}" '
                    f'font-family="sans-serif" font-size="12">{escape_xml(line["label"])}</text>'
                )

            # Lines
            for line in self.lines:
                points = []
                data = line["data"]
                for i, val in enumerate(data):
                    x = get_x(i, len(data))
                    y = get_y(val)
                    points.append(f"{x},{y}")

                polyline = (
                    f'<polyline points="{" ".join(points)}" fill="none" '
                    f'stroke="{line["color"]}" stroke-width="2"/>'
                )
                svg.append(polyline)

            svg.append("</svg>")
            return "\n".join(svg)

    # Assets Setup
    assets_dir = output_path.parent / "history_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    def generate_chart(title, generator_func, filename_base, mermaid_def):
        """Generates a chart using SVG generator, falling back to mermaid block if needed."""
        if assets_dir:
            output_svg = assets_dir / f"{filename_base}.svg"

            try:
                svg_content = generator_func()
                with open(output_svg, "w") as f:
                    f.write(svg_content)

                # Relativize path for the link
                rel_path = os.path.relpath(output_svg, output_path.parent)
                return f"![{title}]({rel_path})"
            except Exception as e:
                print(
                    f"Failed to generate SVG for {filename_base}: {e}", file=sys.stderr
                )
                return f"```mermaid\n{mermaid_def}\n```"
        else:
            return f"```mermaid\n{mermaid_def}\n```"

    if graph_data:
        # --- SUMMARY METRICS ---
        start_date_str = graph_data[0]["date"]
        end_date_str = graph_data[-1]["date"]
        start_loc = graph_data[0]["loc_total"]
        end_loc = graph_data[-1]["loc_total"]

        d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
        d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
        days = (d2 - d1).days

        # If days is 0 (same day), avoid division by zero
        days = max(1, days)

        loc_growth = end_loc - start_loc

        # --- SUMMARY TABLES ---
        latest = graph_data[-1]

        def calc_cov(test, source):
            total = test + source
            if total == 0:
                return 0.0
            return (test / total) * 100.0

        py_ratio = calc_cov(latest["test_loc_py"], latest["loc_py"])
        ts_ratio = calc_cov(latest["test_loc_ts"], latest["loc_ts"])
        sh_ratio = calc_cov(latest["test_loc_sh"], latest["loc_sh"])
        total_ratio = calc_cov(latest["test_loc_total"], latest["loc_total"])

        summary_section = [
            "## Summary",
            f"- **Analysis Period**: {start_date_str} to {end_date_str} ({days} days)",
            f"- **Total Growth**: {loc_growth:+,} LOC",
            "",
        ]

        # 1. Execution Coverage (MOVED TO TOP)
        val_summary = ade_root / "logs" / "validation_summary_log.md"
        if val_summary.exists():
            try:
                with open(val_summary, "r") as f:
                    content = f.read()
                    # Parse Coverage
                    m_cov = re.search(r"TOTAL\s*([\d.]+)%", content)
                    # Parse Timings
                    timings = []
                    for line in content.splitlines():
                        if "TIMING_METRIC:" in line:
                            # TIMING_METRIC: Backend=18s
                            m_time = re.search(
                                r"TIMING_METRIC:\s*([^=]+)=([\d.]+)s", line
                            )
                            if m_time:
                                timings.append((m_time.group(1), m_time.group(2)))

                    if m_cov:
                        summary_section.extend(
                            [
                                "### Execution Coverage (Latest)",
                                "| Type | Coverage % | Source |",
                                "| :--- | :--- | :--- |",
                                f"| **Overall** | **{m_cov.group(1)}%** | `validate.sh --full` |",
                                "",
                                "> [!TIP]",
                                "> Dynamic execution coverage measures which lines of code "
                                "were actually run during tests.",
                                "",
                            ]
                        )

                    if timings:
                        summary_section.extend(
                            [
                                "### Verification Timings",
                                "| Phase | Duration |",
                                "| :--- | :--- |",
                            ]
                        )
                        for phase, duration in timings:
                            if phase != "Total":  # Put total last or separately
                                summary_section.append(f"| {phase} | {duration}s |")

                        # Find Total
                        total_time = next(
                            (d for p, d in timings if p == "Total"), "N/A"
                        )
                        summary_section.extend(
                            [f"| **Total** | **{total_time}s** |", ""]
                        )
            except Exception:
                pass

        # 2. Test Density Analysis
        summary_section.extend(
            [
                "### Test Density Analysis (Latest)",
                "| Language | Source LOC | Test LOC | Density % |",
                "| :--- | :--- | :--- | :--- |",
                f"| Python | {latest['loc_py']:,} | {latest['test_loc_py']:,} | {py_ratio:.1f}% |",
                f"| TS/JS | {latest['loc_ts']:,} | {latest['test_loc_ts']:,} | {ts_ratio:.1f}% |",
                f"| Shell | {latest['loc_sh']:,} | {latest['test_loc_sh']:,} | {sh_ratio:.1f}% |",
                f"| **Total** | **{latest['loc_total']:,}** | **{latest['test_loc_total']:,}** | "
                f"**{total_ratio:.1f}%** |",
                "",
                "> [!NOTE]",
                "> **Test Density** is a static LOC ratio (Test Code / Production Code).",
                "",
            ]
        )

        # 3. Technical Debt
        summary_section.extend(
            [
                "### Technical Debt (Latest)",
                "| Category | Progress / Count | Status |",
                "| :--- | :--- | :--- |",
                f"| Requirements | {latest['total_reqs'] - latest['open_reqs']} / "
                f"{latest['total_reqs']} | {latest['open_reqs']} Pending |",
                f"| Issues | {latest['total_issues'] - latest['open_issues']} / "
                f"{latest['total_issues']} | {latest['open_issues']} Open |",
                f"| TODOs | {latest['todos']} | {latest['todos']} code markers shown in graph |",
                f"| FIXMEs | {latest['fixmes']} | {latest['fixmes']} code markers shown in graph |",
                "> [!NOTE]",
                "> Markdown markers (TODO/FIXME) excluded from debt chart. Requirements and Issues "
                "tracked via `REQUIREMENTS.md` and `ISSUES.md` respectively.",
                "",
            ]
        )
        charts.extend(summary_section)
        charts.append("")  # Spacer

        # LOC Chart

        charts.append("## Core Source Growth")

        dates = [d["date"] for d in graph_data]
        py_data = [d["loc_py"] for d in graph_data]
        ts_data = [d["loc_ts"] for d in graph_data]
        css_data = [d["loc_css"] for d in graph_data]
        sh_data = [d["loc_sh"] for d in graph_data]
        # Core Total (Py + TS/JS + CSS + Shell)
        core_total_data = [d["loc_py"] + d["loc_ts"] + d["loc_css"] + d["loc_sh"] for d in graph_data]

        # Mermaid Fallback Definition
        loc_def = "xychart-beta\n"
        loc_def += '    title "Core Source Lines of Code over Time"\n'
        loc_def += f"    x-axis {json.dumps(dates)}\n"
        loc_def += '    y-axis "LOC"\n'
        loc_def += f'    line {json.dumps(core_total_data)} "Total (Core)"\n'
        loc_def += f'    line {json.dumps(py_data)} "Python"\n'
        loc_def += f'    line {json.dumps(ts_data)} "TS/JS"\n'
        loc_def += f'    line {json.dumps(css_data)} "CSS"\n'
        loc_def += f'    line {json.dumps(sh_data)} "Shell"'

        def make_loc_svg():
            chart = SimpleSVGChart("Core Source Lines of Code over Time")
            chart.set_x_labels(dates)
            chart.add_line(core_total_data, "Total (Core)", "#2196F3")  # Blue
            chart.add_line(py_data, "Python", "#4CAF50")  # Green
            chart.add_line(ts_data, "TS/JS", "#ff9800")  # Orange
            chart.add_line(css_data, "CSS", "#9c27b0")  # Purple
            chart.add_line(sh_data, "Shell", "#795548")  # Brown
            return chart.generate()

        charts.append(
            generate_chart(
                "Core Source Lines of Code over Time", make_loc_svg, "loc_history", loc_def
            )
        )

        # Non-Source Line Growth Chart
        charts.append("\n## Non-Source Line Growth")

        md_data = [d["loc_md"] for d in graph_data]
        json_data = [d["loc_json"] for d in graph_data]
        test_total_data = [d["test_loc_total"] for d in graph_data]

        non_source_def = "xychart-beta\n"
        non_source_def += '    title "Non-Source & Test Growth (not included in core source lines)"\n'
        non_source_def += f"    x-axis {json.dumps(dates)}\n"
        non_source_def += '    y-axis "LOC"\n'
        non_source_def += f'    line {json.dumps(md_data)} "Markdown"\n'
        non_source_def += f'    line {json.dumps(json_data)} "JSON"\n'
        non_source_def += f'    line {json.dumps(test_total_data)} "Test Total"'

        def make_non_source_svg():
            chart = SimpleSVGChart("Non-Source & Test Growth (not included in core source lines)")
            chart.set_x_labels(dates)
            chart.add_line(md_data, "Markdown", "#607d8b")  # Blue Grey
            chart.add_line(json_data, "JSON", "#9e9e9e")  # Grey
            chart.add_line(test_total_data, "Test Total", "#f44336")  # Red
            return chart.generate()

        charts.append(
            generate_chart(
                "Non-Source & Test Growth",
                make_non_source_svg,
                "non_source_history",
                non_source_def,
            )
        )

        # Remove Test Code Growth chart from here as it's merged into Non-Source Growth

        # Debt Chart
        charts.append("\n## Technical Debt")

        todo_data = [d["todos"] for d in graph_data]
        fixme_data = [d["fixmes"] for d in graph_data]

        debt_def = "xychart-beta\n"
        debt_def += '    title "Technical Debt Markers"\n'
        debt_def += f"    x-axis {json.dumps(dates)}\n"
        debt_def += '    y-axis "Count"\n'
        debt_def += f'    line {json.dumps(todo_data)} "TODOs"\n'
        debt_def += f'    line {json.dumps(fixme_data)} "FIXMEs"'

        def make_debt_svg():
            chart = SimpleSVGChart("Technical Debt Markers")
            chart.set_x_labels(dates)
            chart.add_line(todo_data, "TODOs", "#2196F3")  # Blue
            chart.add_line(fixme_data, "FIXMEs", "#f44336")  # Red
            return chart.generate()

        charts.append(
            generate_chart(
                "Technical Debt Markers", make_debt_svg, "debt_history", debt_def
            )
        )

        charts.append("\n## Commit History")

    # Insert charts before the table
    # We find where the table starts (after the header info)
    # Existing structure: Title, Date, Empty line, Table Header...

    # We want to place charts after "Generated on ..."
    insert_idx = 2
    for line in reversed(charts):
        final_output.insert(insert_idx, line)

    report = "\n".join(final_output) + "\n"

    with open(output_path, "w") as f:
        f.write(report)
    print(f"Report written to {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Analyze project statistics/history.")
    # subparsers = parser.add_subparsers(dest="mode", help="Mode of operation")

    # History Args
    parser.add_argument(
        "--history",
        action="store_true",
        help="Run in history mode (default if no other mode)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of commits"
    )
    parser.add_argument("--reverse", action="store_true", help="Oldest to Newest")
    parser.add_argument("--since", help="Analyze commits since this hash")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Depublicated by default; always merges new commits with existing output file unless --refresh is used",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore existing report and re-analyze entire history",
    )
    parser.add_argument(
        "--date-start",
        help="Start date for analysis (YYYYMMDD or YYYY-MM-DD)",
    )

    # Local Args
    parser.add_argument(
        "--analyze-local", action="store_true", help="Analyze current filesystem state"
    )
    parser.add_argument(
        "--markdown", action="store_true", help="Output Markdown (Local mode)"
    )
    parser.add_argument(
        "--dual",
        action="store_true",
        help="Output Markdown to stdout and ASCII to stderr (Local mode)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validate.sh --full and include results in report",
    )
    parser.add_argument(
        "--path",
        help="Path to the repository/directory to analyze (e.g. a submodule)",
    )
    parser.add_argument(
        "--output",
        help="Path to save the HISTORY.md report",
    )

    args = parser.parse_args()

    # Determine ADE Root (where the tool is installed)
    # This script is in agent_env/bin/
    ade_root = Path(__file__).resolve().parent.parent.parent

    # Determine Target Path and Target Repo Root
    target_path = Path(args.path or os.getcwd()).resolve()
    target_repo_root = target_path
    try:
        root_output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=target_path,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        target_repo_root = Path(root_output)
    except Exception:
        pass  # Fallback to target_path

    check_configuration(ade_root)

    if args.analyze_local:
        run_local_analysis(target_repo_root, ade_root, args)
    else:
        # Default to history
        run_history_analysis(target_repo_root, ade_root, args)


def check_configuration(project_root):
    """Checks if the agent environment is configured."""
    setup_marker = project_root / "agent_env" / ".agent_setup_complete"
    if not setup_marker.exists():
        print("⚠️  WARNING: Agent environment appears unconfigured.", file=sys.stderr)
        print("   Missing marker: agent_env/.agent_setup_complete", file=sys.stderr)
        print("   Please run: python3 agent_env/bin/configure.py", file=sys.stderr)
        print("", file=sys.stderr)


def check_submodule_status(project_root):
    """Checks if the submodule is in sync with the superproject expectation."""
    try:
        # Get expected hash from superproject
        # git ls-tree HEAD agent_env
        # Output format: 160000 commit <hash>\tagent_env
        cmd = ["git", "ls-tree", "HEAD", "agent_env"]
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            return

        parts = result.stdout.strip().split()
        if len(parts) < 3:
            return
        expected_hash = parts[2]

        # Get actual hash
        submodule_path = project_root / "agent_env"
        if not submodule_path.exists():
            return

        cmd_actual = ["git", "rev-parse", "HEAD"]
        result_actual = subprocess.run(
            cmd_actual, cwd=submodule_path, capture_output=True, text=True
        )
        if result_actual.returncode != 0:
            return
        actual_hash = result_actual.stdout.strip()

        if expected_hash != actual_hash:
            print(
                f"ℹ️  Submodule Check: agent_env is at {actual_hash[:7]} "
                f"(Superproject expects {expected_hash[:7]}).",
                file=sys.stderr,
            )
            print(
                "   Assuming local development mode. No changes made.", file=sys.stderr
            )
            print("", file=sys.stderr)

    except Exception:
        pass


if __name__ == "__main__":
    # We can't easily call check_configuration here without parsing args first to find root.
    # But main() determines root. So we should call it inside main.
    # Let's actually move the call inside main() or just patch main to call it.
    pass
    main()
