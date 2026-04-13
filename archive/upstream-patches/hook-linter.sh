#!/usr/bin/env bash
# hook-linter.sh — catches the "conditional prompt hook" anti-pattern before a plugin ships.
#
# Usage:
#   bash hook-linter.sh <path/to/hooks.json> [<more hooks.json>...]
#
# Exits:
#   0 — no issues
#   1 — at least one warning or error found
#   2 — could not parse input
#
# Checks:
#   1. ERROR: prompt-type hook on PostToolUse or Stop — guaranteed to emit output on every matcher hit.
#   2. WARN:  prompt-type hook whose prompt contains conditional language
#             ("if...otherwise", "when...do", "if...do nothing", "suggest", "remind") — likely noisy.
#   3. WARN:  prompt-type hook on SessionStart — fires on every session; only OK if
#             the intent is always-visible output.
#
# Designed to be run in CI, from a pre-commit hook, or manually during plugin development.

set -u

if [ "$#" -lt 1 ]; then
  echo "usage: hook-linter.sh <hooks.json> [<hooks.json>...]" >&2
  exit 2
fi

exit_code=0

for target in "$@"; do
  if [ ! -f "$target" ]; then
    echo "ERROR: not a file: $target" >&2
    exit_code=1
    continue
  fi

  # Use python (always present on macOS/linux) for JSON parsing — jq may not be installed.
  python3 - "$target" <<'PY'
import json, re, sys

path = sys.argv[1]
try:
  with open(path) as f:
    data = json.load(f)
except Exception as e:
  print(f"ERROR: {path}: could not parse JSON: {e}", file=sys.stderr)
  sys.exit(2)

hooks = data.get("hooks", {})
if not isinstance(hooks, dict):
  print(f"ERROR: {path}: 'hooks' must be an object", file=sys.stderr)
  sys.exit(1)

conditional_patterns = [
  re.compile(r"\bif\b.+\botherwise\b", re.IGNORECASE | re.DOTALL),
  re.compile(r"\bwhen\b.+\bdo\b", re.IGNORECASE | re.DOTALL),
  re.compile(r"\bdo nothing\b", re.IGNORECASE),
  re.compile(r"\bonly if\b", re.IGNORECASE),
]
softer_smell = re.compile(r"\b(suggest|remind)\b", re.IGNORECASE)

DANGEROUS_EVENTS = {"PostToolUse", "Stop"}
FREQUENT_EVENTS = {"SessionStart"}

issues = 0
for event, matchers in hooks.items():
  if not isinstance(matchers, list):
    continue
  for m in matchers:
    for h in m.get("hooks", []) or []:
      if h.get("type") != "prompt":
        continue
      prompt = h.get("prompt", "") or ""
      matcher_str = m.get("matcher", "") or "*"
      loc = f"{path} :: {event} [matcher={matcher_str!r}]"

      if event in DANGEROUS_EVENTS:
        print(f"ERROR  {loc}: prompt-type hook on {event} will emit LLM output on every matcher hit. "
              f"Use a command-type hook with silent exit instead. "
              f"See plugin-dev hook-development SKILL.md > Anti-Patterns > 'The conditional prompt trap'.",
              file=sys.stderr)
        issues += 1
        continue

      hit_conditional = any(p.search(prompt) for p in conditional_patterns)
      if hit_conditional:
        print(f"WARN   {loc}: prompt contains conditional language "
              f"(if/otherwise, when/do, do nothing, only if). This will spam on every matcher hit. "
              f"Rewrite as a command-type hook that exits silently unless the condition applies.",
              file=sys.stderr)
        issues += 1
        continue

      if event in FREQUENT_EVENTS:
        print(f"WARN   {loc}: prompt-type hook on {event} fires on every session. "
              f"Only safe if always-visible LLM output is the explicit intent.",
              file=sys.stderr)
        issues += 1
        continue

      if softer_smell.search(prompt):
        print(f"INFO   {loc}: prompt contains 'suggest'/'remind' — check whether a silent command hook would be less noisy.",
              file=sys.stderr)

if issues == 0:
  print(f"OK     {path}: no anti-patterns detected.")
  sys.exit(0)
else:
  sys.exit(1)
PY
  sub=$?
  if [ "$sub" -ne 0 ]; then
    exit_code=1
  fi
done

exit "$exit_code"
