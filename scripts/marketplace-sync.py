#!/usr/bin/env python3
"""
marketplace-sync: propose marketplace.json + README.md updates for a single child
plugin (C2, week-2 plan).

Reads the child plugin's `.claude-plugin/plugin.json` and emits a unified diff
of the changes that would land in the toolkit's `marketplace.json` and README.md.

Manual-invoke for now. A future GH Action could call this on a child plugin's
`v*` tag (out of scope for this iteration).

Usage:
  marketplace-sync.py <child-plugin-path> [--write]
  marketplace-sync.py /Users/tyroneross/dev/git-folder/RossLabs-AI-Toolkit/plugins/build-loop

Exit codes:
  0  success (diff printed; nothing written unless --write)
  1  child plugin or marketplace file shape problem
  2  no changes (everything already in sync)
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = TOOLKIT_ROOT / ".claude-plugin" / "marketplace.json"
README = TOOLKIT_ROOT / "README.md"


def die(msg: str, code: int = 1) -> None:
    print(f"marketplace-sync: ERROR — {msg}", file=sys.stderr)
    sys.exit(code)


def load_child(child_dir: Path) -> dict:
    pj = child_dir / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        die(f"child plugin.json not found: {pj}")
    try:
        return json.loads(pj.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"child plugin.json invalid JSON: {e}")


def update_marketplace(text: str, child: dict) -> tuple[str, list[str]]:
    """Return updated marketplace text and a list of changes applied."""
    data = json.loads(text)
    name = child.get("name")
    if not name:
        die("child plugin.json missing required field: name")

    target = None
    for entry in data.get("plugins", []):
        if entry.get("name") == name:
            target = entry
            break

    if target is None:
        die(f"plugin {name!r} not found in marketplace.json")

    changes: list[str] = []
    # Sync version
    if "version" in child and target.get("version") != child["version"]:
        changes.append(
            f"marketplace.json: {name}.version {target.get('version')!r} → {child['version']!r}"
        )
        target["version"] = child["version"]

    # Sync description (only if child has one — don't blank it out)
    if child.get("description") and target.get("description") != child["description"]:
        changes.append(f"marketplace.json: {name}.description updated")
        target["description"] = child["description"]

    # Re-render with same indent. The existing file uses 2-space indent and
    # trailing newline. ensure_ascii=False preserves em-dashes etc. so the
    # diff doesn't churn unrelated entries with — escapes.
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return out, changes


# README table-row regex. Matches:
#   | [name](url) | `version` | description |
# Capturing groups: 1=link-block, 2=name, 3=url, 4=version, 5=description.
README_ROW_RE = re.compile(
    r"^(\|\s*\[([A-Za-z0-9_\-]+)\]\(([^)]+)\)\s*\|\s*)`([^`]+)`(\s*\|\s*)([^|]*?)(\s*\|\s*)$",
    re.MULTILINE,
)


def update_readme(text: str, child: dict, sync_desc: bool) -> tuple[str, list[str]]:
    name = child["name"]
    new_version = child.get("version")
    new_desc = child.get("description")

    changes: list[str] = []
    found = False

    def replacer(m: re.Match) -> str:
        nonlocal found, changes
        row_name = m.group(2)
        if row_name != name:
            return m.group(0)
        found = True
        old_version = m.group(4)
        old_desc = m.group(6).strip()
        version_block = f"`{new_version}`" if new_version else f"`{old_version}`"
        # Description policy: README rows are often hand-authored editorial
        # prose richer than plugin.json.description. Default: leave alone.
        # Pass --sync-desc to force the README to match plugin.json.
        desc_block = old_desc
        if sync_desc and new_desc and new_desc.strip() != old_desc:
            desc_block = new_desc.strip()
            changes.append(f"README.md: {name} description updated (--sync-desc)")
        if new_version and new_version != old_version:
            changes.append(f"README.md: {name} version {old_version} → {new_version}")
        return f"{m.group(1)}{version_block}{m.group(5)}{desc_block}{m.group(7)}"

    new_text = README_ROW_RE.sub(replacer, text)
    if not found:
        # Don't fail hard — README may legitimately not list every plugin.
        # Surface it so the user can decide whether to add a row.
        changes.append(f"README.md: no table row found for {name!r} (skipped)")
    return new_text, changes


def diff_block(label: str, before: str, after: str) -> str:
    if before == after:
        return ""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"{label} (current)",
        tofile=f"{label} (proposed)",
        n=2,
    )
    return "".join(diff)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Sync marketplace.json + README.md to a child plugin")
    ap.add_argument("child_path", help="Path to a plugin directory (containing .claude-plugin/plugin.json)")
    ap.add_argument("--write", action="store_true", help="Apply changes to marketplace.json and README.md (default: dry-run)")
    ap.add_argument("--sync-desc", action="store_true", help="Also overwrite README's editorial description with plugin.json.description (default: leave README description alone)")
    args = ap.parse_args(argv)

    child_dir = Path(args.child_path).expanduser().resolve()
    if not child_dir.is_dir():
        die(f"not a directory: {child_dir}")

    if not MARKETPLACE.exists():
        die(f"marketplace.json not found at expected path: {MARKETPLACE}")
    if not README.exists():
        die(f"README.md not found at expected path: {README}")

    child = load_child(child_dir)

    mk_before = MARKETPLACE.read_text(encoding="utf-8")
    rd_before = README.read_text(encoding="utf-8")

    mk_after, mk_changes = update_marketplace(mk_before, child)
    rd_after, rd_changes = update_readme(rd_before, child, sync_desc=args.sync_desc)

    all_changes = mk_changes + rd_changes
    actionable = [c for c in all_changes if "no table row found" not in c]

    print(f"marketplace-sync: child plugin = {child.get('name')} v{child.get('version')}")
    print(f"  marketplace.json: {MARKETPLACE}")
    print(f"  README.md:        {README}")
    print()

    if not actionable:
        print("Already in sync. No changes proposed.")
        # Surface skipped rows as warnings
        for c in all_changes:
            if "no table row found" in c:
                print(f"  warning: {c}")
        return 2

    print("Proposed changes:")
    for c in all_changes:
        print(f"  - {c}")
    print()

    mk_diff = diff_block("marketplace.json", mk_before, mk_after)
    rd_diff = diff_block("README.md", rd_before, rd_after)
    if mk_diff:
        print("--- marketplace.json diff ---")
        print(mk_diff)
    if rd_diff:
        print("--- README.md diff ---")
        print(rd_diff)

    if args.write:
        MARKETPLACE.write_text(mk_after, encoding="utf-8")
        README.write_text(rd_after, encoding="utf-8")
        print("\nApplied (--write).")
    else:
        print("\nDry-run only. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
