#!/usr/bin/env bash
# init.sh — session-init bootstrap for a long-running agent harness.
# Run at the start of every session before any new work.
# Exits non-zero on any check failure; agent should abort and report.

set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "── Session init: $(date -u +%Y-%m-%dT%H:%M:%SZ) ──"

# 1. Progress log
if [[ -f claude-progress.txt ]]; then
  echo
  echo "── claude-progress.txt — last 60 lines ──"
  tail -n 60 claude-progress.txt
else
  echo "⚠️  No claude-progress.txt found. Create one before proceeding (see SKILL.md)."
  exit 1
fi

# 2. Feature list
if [[ -f feature-list.json ]]; then
  echo
  echo "── feature-list.json — in-progress and blocked features ──"
  if command -v jq >/dev/null; then
    jq '.features[] | select(.status == "in-progress" or .status == "blocked") | {id, title, status, owner, blocked_on}' feature-list.json
  else
    echo "(jq not installed — showing raw file)"
    cat feature-list.json
  fi
else
  echo "⚠️  No feature-list.json found. Create one before proceeding (see SKILL.md)."
  exit 1
fi

# 3. Git state
echo
echo "── git log -10 ──"
git log --oneline -10

echo
echo "── git status ──"
git status --short

# 4. Tests
echo
echo "── e2e tests (configurable per project) ──"
if [[ -f package.json ]] && grep -q '"test:e2e"' package.json; then
  echo "Running: pnpm test:e2e"
  if pnpm test:e2e; then
    echo "✓ e2e green"
  else
    echo "✗ e2e RED — abort. Fix tests before any new work."
    exit 1
  fi
elif [[ -f Makefile ]] && grep -q '^test:' Makefile; then
  if make test; then
    echo "✓ make test green"
  else
    echo "✗ make test RED — abort."
    exit 1
  fi
else
  echo "(no test command configured — skipping)"
fi

# 5. Dev server smoke (optional; agent decides whether to start)
echo
echo "── init complete. Coding agent may proceed. ──"
