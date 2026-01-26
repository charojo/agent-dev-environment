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

Run the analysis script directly from the bin directory (or your PATH if configured):

```bash
# Analyze the entire history
python3 agent_env/bin/ADE_project_history.py
```

## Options

- `--limit <N>`: Limit the analysis to the most recent N commits.
- `--reverse`: Analyze in reverse chronological order (oldest first).
- `--since <HASH>`: Analyze commits since this hash.
- `--incremental`: Append new commits to existing `history.md`.
- `--analyze-local`: Analyze the current filesystem state (Local Mode).

## Output Format

The output is a Markdown table with the following columns:

- **Date**: Commit date (YYYY-MM-DD)
- **Commit**: Short commit hash
- **Author**: Commit author
- **Total LOC**: Total lines of code tracked
- **Py LOC**: Python lines of code
- **TS/JS LOC**: TypeScript and JavaScript lines of code
- **MD LOC**: Markdown lines of code
- **CSS LOC**: CSS lines of code
- **SH LOC**: Shell script lines of code
- **JSON LOC**: JSON data lines of code
- **Tests**: Number of test files detected
- **TODOs**: Count of "TODO" markers
- **NEEDS_FIX**: Count of "FIXME" markers

## Example Report

| Date | Commit | Author | Total LOC | Py LOC | TS/JS LOC | MD LOC | CSS LOC | SH LOC | JSON LOC | Tests | TODOs | NEEDS_FIX |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-01-15 | `a1b2c3d` | Alice Dev | 1500 | 800 | 400 | 300 | 100 | 20 | 50 | 12 | 5 | 2 |
| 2024-01-14 | `x9y8z7w` | Bob Engineer | 1450 | 780 | 390 | 280 | 90 | 15 | 45 | 11 | 4 | 2 |
