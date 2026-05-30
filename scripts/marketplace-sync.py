#!/usr/bin/env python3
"""
marketplace-sync: reconcile every distribution surface to a plugin's true version.

Three surfaces drift independently and must describe the same state:
  1. .claude-plugin/marketplace.json   — drives Claude Code installs
  2. .agents/plugins/marketplace.json   — drives Codex / cross-agent installs
  3. README.md                          — drives GitHub discovery

Source of truth for a github-source plugin is its EXTERNAL repo's
`.claude-plugin/plugin.json` (that's what `claude plugin install` actually
clones), not the local mirror under `plugins/<name>/`, which lags. This tool
reads the external version via `gh api` and falls back to the local mirror only
when the network/gh is unavailable.

Usage:
  marketplace-sync.py --all [--write]            # reconcile every plugin
  marketplace-sync.py <child-plugin-path> [--write]   # single plugin (local mirror)
  marketplace-sync.py --all --source local       # force local-mirror sourcing

Exit codes:
  0  changes proposed (and written with --write)
  1  shape problem (bad JSON, missing file, plugin not found)
  2  no changes (every surface already in sync)
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = TOOLKIT_ROOT / ".claude-plugin" / "marketplace.json"
AGENTS_MARKETPLACE = TOOLKIT_ROOT / ".agents" / "plugins" / "marketplace.json"
README = TOOLKIT_ROOT / "README.md"


def die(msg: str, code: int = 1) -> None:
    print(f"marketplace-sync: ERROR — {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------------------
# Version sourcing
# ---------------------------------------------------------------------------

def external_version(source: dict) -> str | None:
    """Read version from the external github repo's plugin.json via gh api.

    Honors an optional `path` (monorepo sub-dir) on the source object. Returns
    None on any failure (gh missing, network error, file absent) so callers can
    fall back to the local mirror.
    """
    if not isinstance(source, dict) or source.get("source") != "github":
        return None
    repo = source.get("repo")
    if not repo:
        return None
    path = source.get("path", "").strip("/")
    candidates: list[str] = []
    if path:
        candidates += [f"{path}/.claude-plugin/plugin.json", f"{path}/plugin.json"]
    candidates += [".claude-plugin/plugin.json", "plugin.json"]
    for c in candidates:
        try:
            out = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{c}"],
                capture_output=True, text=True, timeout=20,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if out.returncode != 0:
            continue
        try:
            payload = json.loads(out.stdout)
            content = base64.b64decode(payload["content"]).decode("utf-8", "ignore")
            return json.loads(content).get("version")
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return None


def local_version(name: str) -> str | None:
    """Version from the in-repo mirror plugins/<name>/.claude-plugin/plugin.json."""
    for rel in (f"plugins/{name}/.claude-plugin/plugin.json", f"plugins/{name}/plugin.json"):
        pj = TOOLKIT_ROOT / rel
        if pj.exists():
            try:
                return json.loads(pj.read_text(encoding="utf-8")).get("version")
            except json.JSONDecodeError:
                return None
    return None


def resolve_version(entry: dict, prefer: str) -> tuple[str | None, str]:
    """Return (version, where) for a marketplace entry. prefer = 'external'|'local'."""
    name = entry.get("name", "")
    src = entry.get("source", {})
    if prefer == "local":
        v = local_version(name)
        return (v, "local") if v else (external_version(src), "external")
    v = external_version(src)
    if v:
        return v, "external"
    v = local_version(name)
    return (v, "local-fallback") if v else (None, "unresolved")


# ---------------------------------------------------------------------------
# Surface writers
# ---------------------------------------------------------------------------

def apply_manifest(path: Path, label: str, versions: dict[str, str], changes: list[str]) -> str:
    """Update existing per-plugin `version` fields in a marketplace manifest.

    Only touches entries that already declare `version` — never injects the
    field. The .agents (Codex) mirror deliberately carries `version` on a
    subset of entries; injecting it everywhere would restructure that surface.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("plugins", []):
        name = entry.get("name")
        new_v = versions.get(name)
        if new_v and "version" in entry and entry["version"] != new_v:
            changes.append(f"{label}: {name}.version {entry['version']!r} → {new_v!r}")
            entry["version"] = new_v
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# README table-row regex: | [name](url) | `version` | description |
README_ROW_RE = re.compile(
    r"^(\|\s*\[([A-Za-z0-9_\-]+)\]\(([^)]+)\)\s*\|\s*)`([^`]+)`(\s*\|\s*)([^|]*?)(\s*\|\s*)$",
    re.MULTILINE,
)


def apply_readme(text: str, versions: dict[str, str], changes: list[str]) -> str:
    def replacer(m: re.Match) -> str:
        name = m.group(2)
        new_v = versions.get(name)
        old_v = m.group(4)
        if new_v and new_v != old_v:
            changes.append(f"README.md: {name} version {old_v} → {new_v}")
            return f"{m.group(1)}`{new_v}`{m.group(5)}{m.group(6)}{m.group(7)}"
        return m.group(0)
    return README_ROW_RE.sub(replacer, text)


def diff_block(label: str, before: str, after: str) -> str:
    if before == after:
        return ""
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"{label} (current)", tofile=f"{label} (proposed)", n=2,
    ))


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def build_version_map(prefer: str) -> dict[str, str]:
    """Resolve the true version for every plugin in .claude-plugin/marketplace.json."""
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    print("Resolving source-of-truth versions:")
    for entry in data.get("plugins", []):
        name = entry.get("name")
        v, where = resolve_version(entry, prefer)
        if v is None:
            print(f"  ! {name:<22} UNRESOLVED — leaving as-is")
            continue
        versions[name] = v
        flag = "" if entry.get("version") == v else f"  (was {entry.get('version')})"
        print(f"  · {name:<22} {v:<10} [{where}]{flag}")
    return versions


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Reconcile marketplace + README to true plugin versions")
    ap.add_argument("child_path", nargs="?", help="Single plugin dir (local mirror mode)")
    ap.add_argument("--all", action="store_true", help="Reconcile every plugin across all surfaces")
    ap.add_argument("--source", choices=["external", "local"], default="external",
                    help="Version source of truth (default: external repo via gh)")
    ap.add_argument("--write", action="store_true", help="Apply changes (default: dry-run)")
    args = ap.parse_args(argv)

    for p in (MARKETPLACE, AGENTS_MARKETPLACE, README):
        if not p.exists():
            die(f"expected file not found: {p}")

    if args.all:
        versions = build_version_map(args.source)
    elif args.child_path:
        child = Path(args.child_path).expanduser().resolve() / ".claude-plugin" / "plugin.json"
        if not child.exists():
            die(f"child plugin.json not found: {child}")
        pj = json.loads(child.read_text(encoding="utf-8"))
        if not pj.get("name"):
            die("child plugin.json missing 'name'")
        versions = {pj["name"]: pj.get("version")}
    else:
        die("provide a plugin path or --all")

    changes: list[str] = []
    mk_before = MARKETPLACE.read_text(encoding="utf-8")
    ag_before = AGENTS_MARKETPLACE.read_text(encoding="utf-8")
    rd_before = README.read_text(encoding="utf-8")

    mk_after = apply_manifest(MARKETPLACE, ".claude-plugin/marketplace.json", versions, changes)
    ag_after = apply_manifest(AGENTS_MARKETPLACE, ".agents/plugins/marketplace.json", versions, changes)
    rd_after = apply_readme(rd_before, versions, changes)

    print()
    if not changes:
        print("Every surface already in sync. No changes.")
        return 2

    print("Proposed changes:")
    for c in changes:
        print(f"  - {c}")
    print()
    for label, b, a in (("marketplace.json", mk_before, mk_after),
                        (".agents marketplace.json", ag_before, ag_after),
                        ("README.md", rd_before, rd_after)):
        d = diff_block(label, b, a)
        if d:
            print(f"--- {label} diff ---")
            print(d)

    if args.write:
        MARKETPLACE.write_text(mk_after, encoding="utf-8")
        AGENTS_MARKETPLACE.write_text(ag_after, encoding="utf-8")
        README.write_text(rd_after, encoding="utf-8")
        print("\nApplied (--write).")
    else:
        print("\nDry-run only. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
