#!/usr/bin/env bash
set -euo pipefail

# Simple helper to capture development issues into the canonical backlog
MSG="$*"
if [ -z "${MSG// /}" ]; then
  echo "Usage: $0 <short issue description>" >&2
  exit 1
fi

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-git")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "no-commit")

mkdir -p docs
BACKLOG_FILE="docs/BACKLOG.md"

if [ ! -f "$BACKLOG_FILE" ]; then
  echo "# Project Backlog" > "$BACKLOG_FILE"
  echo "" >> "$BACKLOG_FILE"
fi

{
  echo "### $TS - $BRANCH ($COMMIT)"
  echo "- ISSUE: $MSG"
  echo ""
} >> "$BACKLOG_FILE"

echo "Appended issue to $BACKLOG_FILE"
