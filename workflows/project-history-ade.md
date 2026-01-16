---
description: Analyze project evolution and statistics over time
---

# Project History Analysis

This workflow allows you to analyze the evolution of the project by traversing the git history.
It generates a report containing statistics for each commit, including Lines of Code (LOC) per language, and counts of TODO/FIXME markers.

## Prerequisites

- The `agent_env` must be configured.
- You must be inside a git repository.

## Usage

### History Analysis

Run the script to analyze git history:

```bash
# Analyze the last 10 commits
python3 agent_env/bin/ADE_project_history.py --limit 10

# Analyze history incrementally (append new commits to existing report)
python3 agent_env/bin/ADE_project_history.py --output history_report.md --incremental

# Analyze everything since a specific commit
python3 agent_env/bin/ADE_project_history.py --since <commit-hash>
```

### Local Snapshot

Run the script to analyze the *current* state of the filesystem (ignoring git history):

```bash
python3 agent_env/bin/ADE_project_history.py --analyze-local
```

## Options

- `--analyze-local`: Analyze current filesystem state instead of history.
- `--incremental`: Append new commits to an existing output file (requires `--output`).
- `--since <HASH>`: Analyze commits starting after the specified hash.
- `--limit <N>`: Limit the analysis to the most recent N commits.
- `--reverse`: Analyze in reverse chronological order (oldest first).
- `--output <FILE>`: Save the Markdown report to the specified file.

## Output Format

The output is a Markdown table with the following columns:

- **Date**: Commit date (YYYY-MM-DD)
- **Commit**: Short commit hash
- **Author**: Commit author
- **Total LOC**: Total lines of code tracked
- **Py LOC**: Python lines of code
- **TS/JS LOC**: TypeScript and JavaScript lines of code
- **MD LOC**: Markdown lines of code
- **Tests**: Number of test files detected
- **TODOs**: Count of "TODO" markers
- **NEEDS_FIX**: Count of "FIXME" markers

## Charts

When running in history mode with `--output`, the script automatically generates SVG charts for:
1. **Lines of Code over Time**: Visualizes the growth of the codebase by language.
2. **Technical Debt Markers**: visualizes the trend of `TODO` and `FIXME` counts.

These charts are saved in a `_assets` directory next to the output report and linked within the Markdown.

## Example Report

| Date | Commit | Author | Total LOC | Py LOC | TS/JS LOC | MD LOC | Tests | TODOs | NEEDS_FIX |
|---|---|---|---|---|---|---|---|---|---|
| 2024-01-15 | `a1b2c3d` | Alice Dev | 1500 | 800 | 400 | 300 | 12 | 5 | 2 |
| 2024-01-14 | `x9y8z7w` | Bob Engineer | 1450 | 780 | 390 | 280 | 11 | 4 | 2 |
