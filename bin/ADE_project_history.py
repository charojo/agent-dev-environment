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
        result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # print(f"Error running git command: {e}", file=sys.stderr)
        return None


def get_commits(cwd, limit=None, since_commit=None):
    """Get a list of commits (hash, date, author, subject)."""
    args = ["log", "--pretty=format:%H|%ad|%an|%s", "--date=short"]

    if since_commit:
        # Get commits from since_commit..HEAD using proper git syntax
        # We want to include everything AFTER since_commit
        args.append(f"{since_commit}..HEAD")

    if limit:
        args.extend(["-n", str(limit)])

    output = run_git_command(args, cwd)
    if not output:
        return []

    commits = []
    for line in output.split("\n"):
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                {"hash": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]}
            )
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
    parts = fp.split(os.sep)
    return (
        "test" in parts
        or "tests" in parts
        or fp.startswith("test_")
        or fp.endswith("_test.py")
        or any(
            fp.endswith(ext)
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


def run_local_analysis(root_dir, args):
    """Analyzes the current filesystem (Local Mode)."""
    exclude_dirs = {
        ".venv",
        "node_modules",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "logs",
        "build",
        "dist",
        "site-packages",
        ".ruff_cache",
        ".coverage",
        "docs",
    }

    # Check config
    try:
        config = config_utils.load_config(root_dir)
    except NameError:
        config = {}

    languages_config = config.get("languages", {})
    if not languages_config:
        languages_config = {
            "python": {"enabled": True, "extensions": [".py"]},
            "typescript": {"enabled": True, "extensions": [".ts", ".tsx", ".js", ".jsx"]},
            "markdown": {"enabled": True, "extensions": [".md"]},
        }
    if "markdown" not in languages_config:
        languages_config["markdown"] = {"enabled": True, "extensions": [".md"]}

    results = {}
    enabled_extensions = {}

    # Initialize
    for lang_name, lang_cfg in languages_config.items():
        if lang_cfg.get("enabled", True):
            results[lang_name] = {"files": 0, "loc": 0, "todos": 0, "fixmes": 0}
            for ext in lang_cfg.get("extensions", []):
                enabled_extensions[ext] = lang_name

    # Walk
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            file_path = Path(root) / file
            _, ext = os.path.splitext(file)

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
    results_file = root_dir / "logs" / "config_test_results.json"
    print_config_results(results_file, markdown=args.markdown or args.dual)


def print_markdown_table_local(results, sorted_langs, metrics, keys):
    header = "| Metric | " + " | ".join([lang.capitalize() for lang in sorted_langs]) + " | Total |"
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
    header = f"{'Metric':<20}"
    for lang in sorted_langs:
        header += f"{lang.capitalize():<15}"
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
                    f"| {r['config']} | {r['status']} | {r['total_size']} | {r['venv_size']} | {r['node_modules_size']} |"
                )
        else:
            print("\n=== Configuration Test Results ===")
            header = f"{'Config':<20} | {'Status':<6} | {'Total':<10} | {'Venv':<10} | {'Node':<10}"
            print(header)
            print("-" * len(header))
            for r in report:
                print(
                    f"{r['config']:<20} | {r['status']:<6} | {r['total_size']:<10} | {r['venv_size']:<10} | {r['node_modules_size']:<10}"
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
        # We look for the FIRST data row since we output essentially reverse chronological usually?
        # Actually our script appends or rewrites.
        # If we append to history, we need to know the TOP of the history if it's descending.
        # But usually history log is descending (newest top).
        # Let's read line by line.
        for line in f:
            # Matches: | YYYY-MM-DD | `hash` | ...
            m = re.search(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*`([^`]+)`", line)
            if m:
                # If we assume the file is sorted newest-first, the first match is the latest commit tracked.
                # However, if we append new commits to the file, we might be prepending or rewriting.
                # If the user asks for incremental, we likely want to catch up from the *newest known* commit to HEAD.
                last_commit = m.group(1)
                # We can stop at the first one found if the list is ordered Newest -> Oldest
                break
    return last_commit


def run_history_analysis(root_dir, args):
    cwd = root_dir
    since_commit = args.since

    existing_content = []

    # Incremental Logic
    if args.incremental and args.output and os.path.exists(args.output):
        print(f"Incremental mode: Checking {args.output} for last commit...", file=sys.stderr)
        last_tracked = parse_existing_history(args.output)
        if last_tracked:
            print(f"Found last tracked commit: {last_tracked}", file=sys.stderr)
            # If we tried to assume that last_commit is part of history, we use it as 'since'
            # Note: git log range is exclusive of the 'since' commit usually (since..HEAD)
            since_commit = last_tracked

            # Read existing content to preserve it (excluding header if we rewrite)
            # Actually, simpler to just read the whole file, strip header, and append to new rows
            with open(args.output, "r") as f:
                existing_content = f.readlines()
        else:
            print(
                "No existing history found in output file. Running full analysis.", file=sys.stderr
            )

    commits = get_commits(cwd, args.limit, since_commit)

    # If using 'since', the commits returned are new ones.
    # If we are strictly prepending new data to old data, we need to sort commits Newest -> Oldest (default log).

    if not commits:
        print("No new commits to analyze.", file=sys.stderr)
        # If output exists, just exit? Or should we touch it?
        return

    print(f"Found {len(commits)} commits to process...", file=sys.stderr)

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
            "loc_python": 0,
            "loc_typescript": 0,
            "loc_markdown": 0,
            "loc_total": 0,
            "test_files": 0,
        }

        for file_path in files:
            ext = os.path.splitext(file_path)[1]
            if ext not in lang_map:
                continue

            content = get_file_content_git(cwd, commit["hash"], file_path)
            loc, todos, fixmes = analyze_content(content)

            stats["todos"] += todos
            stats["fixmes"] += fixmes
            stats["loc_total"] += loc

            lang = lang_map[ext]
            if lang == "python":
                stats["loc_python"] += loc
            elif lang in ["typescript", "javascript"]:
                stats["loc_typescript"] += loc
            elif lang == "markdown":
                stats["loc_markdown"] += loc

            if is_test_file(file_path):
                stats["test_files"] += 1

        history_data.append(stats)

    print("\nAnalysis complete.", file=sys.stderr)

    # Generate Report Rows
    new_rows = []
    for row in history_data:
        new_rows.append(
            f"| {row['date']} | `{row['commit']}` | {row['author']} | "
            f"{row['loc_total']} | {row['loc_python']} | {row['loc_typescript']} | {row['loc_markdown']} | "
            f"{row['test_files']} | {row['todos']} | {row['fixmes']} |"
        )

    # COMBINING
    final_output = []
    if not existing_content:
        final_output.append("# Project History Analysis")
        final_output.append(f"Generated on {datetime.now().isoformat()}")
        final_output.append("")
        final_output.append(
            "| Date | Commit | Author | Total LOC | Py LOC | TS/JS LOC | MD LOC | Tests | TODOs | NEEDS_FIX |"
        )
        final_output.append("|---|---|---|---|---|---|---|---|---|---|")
        final_output.extend(new_rows)
    else:
        # We need to insert new rows after the header.
        # Assuming header ends at line starting with |---|
        # We assume existing_content is Lines.

        # Heuristic: Find the separator line
        sep_index = -1
        for i, line in enumerate(existing_content):
            if line.strip().startswith("|---"):
                sep_index = i
                break

        if sep_index != -1:
            # Header is up to sep_index
            final_output.extend(link.strip() for link in existing_content[: sep_index + 1])
            # Insert NEW rows (assuming they are newer than what is in file)
            final_output.extend(new_rows)
            # Append old rows
            final_output.extend(link.strip() for link in existing_content[sep_index + 1 :])
        else:
            # Could not find table structure, just append?
            final_output.extend(link.strip() for link in existing_content)
            final_output.extend(new_rows)

    # Sort data for graphing (Oldest -> Newest)
    # If final_output generation relies on the existing + new mix, we need to reconstruct the full dataset for the graph.
    # Parsing the lines we just generated is one way.

    # Let's parse the final report lines back into data structures for the graph
    graph_data = []

    # Regex to parse the table rows
    # | Date | Commit | Author | Total LOC | Py LOC | TS/JS LOC | MD LOC | Tests | TODOs | NEEDS_FIX |
    row_regex = re.compile(
        r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
    )

    for line in final_output:
        m = row_regex.search(line)
        if m:
            graph_data.append(
                {
                    "date": m.group(1),
                    "loc_total": int(m.group(4)),
                    "loc_py": int(m.group(5)),
                    "loc_ts": int(m.group(6)),
                    "todos": int(m.group(9)),
                    "fixmes": int(m.group(10)),
                }
            )

    # Sort by date ascending for the chart
    graph_data.sort(key=lambda x: x["date"])

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

            # Title
            svg.append(
                f'<text x="{self.width / 2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="20" font-weight="bold">{self.title}</text>'
            )

            # Axes
            plot_bottom = self.height - self.padding
            plot_top = self.padding
            plot_left = self.padding
            plot_right = self.width - self.padding

            svg.append(
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" stroke="black" stroke-width="2"/>'
            )  # X Axis
            svg.append(
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_left}" y2="{plot_top}" stroke="black" stroke-width="2"/>'
            )  # Y Axis

            # Y Labels (5 steps)
            for i in range(6):
                val = min_val + (max_val - min_val) * (i / 5)
                y = get_y(val)
                svg.append(
                    f'<line x1="{plot_left - 5}" y1="{y}" x2="{plot_left}" y2="{y}" stroke="black"/>'
                )
                svg.append(
                    f'<text x="{plot_left - 10}" y="{y + 5}" text-anchor="end" font-family="sans-serif" font-size="12">{int(val)}</text>'
                )
                svg.append(
                    f'<line x1="{plot_left}" y1="{y}" x2="{plot_right}" y2="{y}" stroke="#ddd" stroke-dasharray="4"/>'
                )  # Grid

            # X Labels (Sampled if too many) - Simplified logic
            count = len(self.x_labels)
            step = max(1, count // 10)
            for i in range(0, count, step):
                x = get_x(i, count)
                svg.append(
                    f'<line x1="{x}" y1="{plot_bottom}" x2="{x}" y2="{plot_bottom + 5}" stroke="black"/>'
                )
                svg.append(
                    f'<text x="{x}" y="{plot_bottom + 10}" text-anchor="start" font-family="sans-serif" font-size="10" transform="rotate(45, {x}, {plot_bottom + 10})">{self.x_labels[i]}</text>'
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
                    f'<text x="{legend_x + 15}" y="{ly + 10}" font-family="sans-serif" font-size="12">{line["label"]}</text>'
                )

            # Lines
            for line in self.lines:
                points = []
                data = line["data"]
                for i, val in enumerate(data):
                    x = get_x(i, len(data))
                    y = get_y(val)
                    points.append(f"{x},{y}")

                polyline = f'<polyline points="{" ".join(points)}" fill="none" stroke="{line["color"]}" stroke-width="2"/>'
                svg.append(polyline)

            svg.append("</svg>")
            return "\n".join(svg)

    # Assets Setup
    assets_dir = None
    if args.output:
        assets_dir = Path(args.output).parent / (Path(args.output).stem + "_assets")
        assets_dir.mkdir(exist_ok=True)

    def generate_chart(title, generator_func, filename_base, mermaid_def):
        """Generates a chart using SVG generator, falling back to mermaid block if needed."""
        if assets_dir:
            output_svg = assets_dir / f"{filename_base}.svg"

            try:
                svg_content = generator_func()
                with open(output_svg, "w") as f:
                    f.write(svg_content)

                # Relativize path for the link
                rel_path = os.path.relpath(output_svg, Path(args.output).parent)
                return f"![{title}]({rel_path})"
            except Exception as e:
                print(f"Failed to generate SVG for {filename_base}: {e}", file=sys.stderr)
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
        avg_lines_per_day = loc_growth / days

        summary_section = [
            "## Summary",
            f"- **Analysis Period**: {start_date_str} to {end_date_str} ({days} days)",
            f"- **Total Growth**: {loc_growth:+,} LOC",
            f"- **Avg Metrics**: {avg_lines_per_day:+.2f} Lines/Day",
        ]
        charts.extend(summary_section)
        charts.append("")  # Spacer

        # LOC Chart

        charts.append("## Project Growth")

        dates = [d["date"] for d in graph_data]
        py_data = [d["loc_py"] for d in graph_data]
        ts_data = [d["loc_ts"] for d in graph_data]
        total_data = [d["loc_total"] for d in graph_data]

        # Mermaid Fallback Definition
        loc_def = "xychart-beta\n"
        loc_def += '    title "Lines of Code over Time"\n'
        loc_def += f"    x-axis {json.dumps(dates)}\n"
        loc_def += '    y-axis "LOC"\n'
        loc_def += f'    line {json.dumps(total_data)} "Total"\n'
        loc_def += f'    line {json.dumps(py_data)} "Python"\n'
        loc_def += f'    line {json.dumps(ts_data)} "TS/JS"'

        def make_loc_svg():
            chart = SimpleSVGChart("Lines of Code over Time")
            chart.set_x_labels(dates)
            chart.add_line(total_data, "Total", "#2196F3")  # Blue
            chart.add_line(py_data, "Python", "#4CAF50")  # Green
            chart.add_line(ts_data, "TS/JS", "#ff9800")  # Orange
            return chart.generate()

        charts.append(
            generate_chart("Lines of Code over Time", make_loc_svg, "loc_history", loc_def)
        )

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
            chart.add_line(todo_data, "TODOs", "#e91e63")  # Pink
            chart.add_line(fixme_data, "FIXMEs", "#f44336")  # Red
            return chart.generate()

        charts.append(
            generate_chart("Technical Debt Markers", make_debt_svg, "debt_history", debt_def)
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

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


def main():
    parser = argparse.ArgumentParser(description="Analyze project statistics/history.")
    # subparsers = parser.add_subparsers(dest="mode", help="Mode of operation")

    # History Args
    parser.add_argument(
        "--history", action="store_true", help="Run in history mode (default if no other mode)"
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of commits")
    parser.add_argument("--reverse", action="store_true", help="Oldest to Newest")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--since", help="Analyze commits since this hash")
    parser.add_argument(
        "--incremental", action="store_true", help="Append new commits to existing output file"
    )

    # Local Args
    parser.add_argument(
        "--analyze-local", action="store_true", help="Analyze current filesystem state"
    )
    parser.add_argument("--markdown", action="store_true", help="Output Markdown (Local mode)")
    parser.add_argument(
        "--dual",
        action="store_true",
        help="Output Markdown to stdout and ASCII to stderr (Local mode)",
    )

    args = parser.parse_args()

    # Determine Root
    cwd = Path.cwd()
    project_root = cwd
    try:
        root_output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
        project_root = Path(root_output)
    except Exception:
        pass  # Fallback to cwd

    check_configuration(project_root)
    check_submodule_status(project_root)

    if args.analyze_local:
        run_local_analysis(project_root, args)
    else:
        # Default to history
        run_history_analysis(project_root, args)


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
                f"ℹ️  Submodule Check: agent_env is at {actual_hash[:7]} (Superproject expects {expected_hash[:7]}).",
                file=sys.stderr,
            )
            print("   Assuming local development mode. No changes made.", file=sys.stderr)
            print("", file=sys.stderr)

    except Exception:
        pass


if __name__ == "__main__":
    # We can't easily call check_configuration here without parsing args first to find root.
    # But main() determines root. So we should call it inside main.
    # Let's actually move the call inside main() or just patch main to call it.
    pass
    main()
