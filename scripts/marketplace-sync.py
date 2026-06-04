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
  marketplace-sync.py --check-hosts              # report installed host drift + fix cmds
  marketplace-sync.py --all --check-hosts        # catalog sync + host drift in one pass
  marketplace-sync.py --check                    # read-only: exit 3 if ANY surface drifts
  marketplace-sync.py --install-cron             # install launchd daily drift-check (macOS)
  marketplace-sync.py --uninstall-cron           # remove launchd plist

Exit codes:
  0  changes proposed (and written with --write)
  1  shape problem (bad JSON, missing file, plugin not found)
  2  no changes (every surface already in sync)
  3  --check mode: at least one surface is drifted (catalog, README, .agents, or hosts)
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import subprocess
import sys
import xml.sax.saxutils
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = TOOLKIT_ROOT / ".claude-plugin" / "marketplace.json"
AGENTS_MARKETPLACE = TOOLKIT_ROOT / ".agents" / "plugins" / "marketplace.json"
README = TOOLKIT_ROOT / "README.md"

CLAUDE_MARKETPLACE_KEY = "rosslabs-ai-toolkit"
CODEX_MARKETPLACE_KEY = "ross-labs-local"


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


# ---------------------------------------------------------------------------
# Chunk 1: Semver comparison
# ---------------------------------------------------------------------------

def semver_lt(a: str | None, b: str | None) -> bool:
    """Return True if version a is strictly less than version b.

    Strips prerelease/build metadata (everything from the first '-' or '+')
    before comparing numeric parts.  This means "1.0.0-rc.1" and "1.0.0"
    compare equal on their release portion, so neither direction of a
    release/prerelease pair is considered stale — the safer choice vs.
    emitting a downgrade command.

    Design choice: strip suffix rather than returning UNRESOLVABLE, because
    the common case is a toolkit version that has moved from a prerelease to
    the identical release (e.g. "1.0.0-rc.1" → "1.0.0").  Treating them as
    equal suppresses the false "update" in both directions.  Operators that
    need strict prerelease ordering must use a different tool.

    Non-numeric segments (after stripping) are treated as 0 (safe degradation
    for git SHAs). Missing parts are 0.  Returns False on any None input —
    None is not considered stale.
    """
    if a is None or b is None:
        return False

    # Strip prerelease / build-metadata suffixes before any comparison
    a_release = re.sub(r"[-+].*$", "", str(a))
    b_release = re.sub(r"[-+].*$", "", str(b))

    if a_release == b_release:
        return False

    def parse(v: str) -> list[int]:
        parts = []
        for seg in v.split("."):
            try:
                parts.append(int(seg))
            except (ValueError, TypeError):
                parts.append(0)
        return parts

    pa, pb = parse(a_release), parse(b_release)
    # Pad to equal length
    maxlen = max(len(pa), len(pb))
    pa += [0] * (maxlen - len(pa))
    pb += [0] * (maxlen - len(pb))
    return pa < pb


# ---------------------------------------------------------------------------
# Chunk 1: Claude installed_plugins.json parsing
# ---------------------------------------------------------------------------

def parse_claude_installed(data: dict, marketplace_key: str) -> dict[str, list[dict]]:
    """Parse installed_plugins.json and return toolkit plugins keyed by plugin name.

    Args:
        data: parsed JSON dict from installed_plugins.json
        marketplace_key: e.g. "rosslabs-ai-toolkit"

    Returns:
        {plugin_name: [{scope, version, projectPath?}, ...]}
    """
    result: dict[str, list[dict]] = {}
    suffix = f"@{marketplace_key}"
    for key, installs in data.get("plugins", {}).items():
        if not key.endswith(suffix):
            continue
        name = key[: -len(suffix)]
        entries = []
        for inst in (installs or []):
            entry: dict = {"scope": inst.get("scope", ""), "version": inst.get("version", "")}
            if inst.get("projectPath"):
                entry["projectPath"] = inst["projectPath"]
            entries.append(entry)
        if entries:
            result[name] = entries
    return result


def load_claude_installed(marketplace_key: str = CLAUDE_MARKETPLACE_KEY) -> dict[str, list[dict]] | None:
    """Load and parse ~/.claude/plugins/installed_plugins.json.

    Returns None with a printed warning if the file is absent or malformed.
    """
    p = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not p.exists():
        print(f"  (skip Claude host check — {p} not found)")
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  (skip Claude host check — could not read {p}: {e})")
        return None
    return parse_claude_installed(data, marketplace_key)


# ---------------------------------------------------------------------------
# Chunk 1: Codex plugin list parsing
# ---------------------------------------------------------------------------

def parse_codex_plugin_list(output: str, marketplace_key: str) -> dict[str, dict]:
    """Parse `codex plugin list` stdout and return installed plugins for marketplace_key.

    The output format is:
      Marketplace `<key>`
      <path>
      <blank>
      PLUGIN  STATUS  VERSION  PATH
      <rows...>
      <blank>
      Marketplace `<next>`
      ...

    Returns:
        {plugin_name: {version, status}} for installed entries (not "not installed").
    """
    result: dict[str, dict] = {}
    if not output.strip():
        return result

    in_target = False
    header_seen = False
    suffix = f"@{marketplace_key}"

    for line in output.splitlines():
        # Detect marketplace section header
        mkt_match = re.match(r"^Marketplace\s+`([^`]+)`", line)
        if mkt_match:
            in_target = mkt_match.group(1) == marketplace_key
            header_seen = False
            continue

        if not in_target:
            continue

        # Skip the file-path line (starts with /) and blank lines
        if not line.strip() or line.strip().startswith("/"):
            continue

        # Detect header row (PLUGIN STATUS VERSION PATH)
        if re.match(r"^\s*PLUGIN\s+STATUS", line, re.IGNORECASE):
            header_seen = True
            continue

        if not header_seen:
            continue

        # Parse data rows — split on 2+ spaces to handle multi-word STATUS
        # Format: <name>  <status>  <version>  <path>
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 2:
            continue

        full_name = parts[0]  # e.g. "build-loop@ross-labs-local"
        status = parts[1] if len(parts) > 1 else ""
        version = parts[2] if len(parts) > 2 else ""

        # Only installed entries have a version and don't say "not installed"
        if "not installed" in status.lower():
            continue
        if not version:
            continue

        # Strip marketplace suffix from plugin name
        if full_name.endswith(suffix):
            name = full_name[: -len(suffix)]
        else:
            name = full_name

        result[name] = {"version": version, "status": status}

    return result


def run_codex_plugin_list() -> str | None:
    """Run `codex plugin list` and return stdout, or None if codex is absent/fails."""
    try:
        out = subprocess.run(
            ["codex", "plugin", "list"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            print(f"  (skip Codex host check — codex plugin list returned {out.returncode})")
            return None
        return out.stdout
    except FileNotFoundError:
        print("  (skip Codex host check — codex CLI not found)")
        return None
    except subprocess.TimeoutExpired:
        print("  (skip Codex host check — codex plugin list timed out)")
        return None


# ---------------------------------------------------------------------------
# Chunk 1: Drift finders
# ---------------------------------------------------------------------------

def find_claude_drift(
    installed: dict[str, list[dict]],
    truth: dict[str, str],
) -> list[dict]:
    """Return list of stale Claude installs.

    Each item: {name, scope, installed_version, truth_version, project_path?}
    Only reports plugins present in truth map (ignores non-toolkit installs).
    """
    drift = []
    for name, entries in installed.items():
        truth_v = truth.get(name)
        if truth_v is None:
            continue  # not a toolkit plugin we're tracking
        for entry in entries:
            inst_v = entry.get("version", "")
            if not inst_v:
                continue  # missing version field — skip rather than emit a spurious update
            if semver_lt(inst_v, truth_v):
                item: dict = {
                    "name": name,
                    "scope": entry.get("scope", ""),
                    "installed_version": inst_v,
                    "truth_version": truth_v,
                }
                if entry.get("projectPath"):
                    item["projectPath"] = entry["projectPath"]
                drift.append(item)
    return drift


def find_codex_drift(
    installed: dict[str, dict],
    truth: dict[str, str],
) -> list[dict]:
    """Return list of stale Codex installs.

    Each item: {name, installed_version, truth_version, status}
    Only reports plugins present in truth map.
    """
    drift = []
    for name, info in installed.items():
        truth_v = truth.get(name)
        if truth_v is None:
            continue
        inst_v = info.get("version", "")
        if semver_lt(inst_v, truth_v):
            drift.append({
                "name": name,
                "installed_version": inst_v,
                "truth_version": truth_v,
                "status": info.get("status", ""),
            })
    return drift


# ---------------------------------------------------------------------------
# Chunk 1: Remediation command generators
# ---------------------------------------------------------------------------

def claude_update_cmd(name: str, scope: str) -> str:
    """Emit the exact `claude plugin update` command for a stale install."""
    return f"claude plugin update {name}@{CLAUDE_MARKETPLACE_KEY} --scope {scope}"


def codex_remediate_cmds(name: str, marketplace_key: str) -> tuple[str, str]:
    """Emit remove + add commands (Codex has no update command)."""
    key = f"{name}@{marketplace_key}"
    return f"codex plugin remove {key}", f"codex plugin add {key}"


# ---------------------------------------------------------------------------
# Chunk 1: catalog truth from local file (no network)
# ---------------------------------------------------------------------------

def catalog_versions_local() -> dict[str, str]:
    """Read version for every plugin from .claude-plugin/marketplace.json (local catalog only).

    Used by --check-hosts when running standalone, so no gh API calls are made.
    Falls back to local mirror when catalog entry lacks a version field.
    """
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    for entry in data.get("plugins", []):
        name = entry.get("name")
        if not name:
            continue
        v = entry.get("version") or local_version(name)
        if v:
            versions[name] = v
    return versions


# ---------------------------------------------------------------------------
# Chunk 1: --check-hosts reporting
# ---------------------------------------------------------------------------

def check_hosts(truth: dict[str, str]) -> list[str]:
    """Compare each toolkit plugin's installed version vs truth across Claude + Codex.

    Returns a list of drift summary lines (one per stale scope/install).
    Never auto-runs any host commands — report only.
    """
    drift_lines: list[str] = []

    # --- Claude ---
    print("\n--- Claude host installs ---")
    claude_installed = load_claude_installed()
    if claude_installed is not None:
        claude_drift = find_claude_drift(claude_installed, truth)
        if not claude_drift:
            print("  All Claude installs up to date.")
        else:
            for item in claude_drift:
                scope = item["scope"]
                name = item["name"]
                inst_v = item["installed_version"]
                truth_v = item["truth_version"]
                cmd = claude_update_cmd(name, scope)
                line = (
                    f"STALE Claude [{scope}] {name}: {inst_v} → {truth_v}"
                    f"\n    Fix: {cmd}"
                    f"\n    Note: restart Claude Code after update"
                )
                if item.get("projectPath"):
                    line += f"\n    Project: {item['projectPath']}"
                print(f"  {line}")
                drift_lines.append(f"Claude [{scope}] {name}: {inst_v} → {truth_v}")

    # --- Codex ---
    print("\n--- Codex host installs ---")
    codex_output = run_codex_plugin_list()
    if codex_output is not None:
        codex_installed = parse_codex_plugin_list(codex_output, CODEX_MARKETPLACE_KEY)
        codex_drift = find_codex_drift(codex_installed, truth)
        if not codex_drift:
            print("  All Codex installs up to date.")
        else:
            print("  Note: Codex has NO `plugin update` command — must remove then re-add.")
            for item in codex_drift:
                name = item["name"]
                inst_v = item["installed_version"]
                truth_v = item["truth_version"]
                remove_cmd, add_cmd = codex_remediate_cmds(name, CODEX_MARKETPLACE_KEY)
                print(f"  STALE Codex {name}: {inst_v} → {truth_v}")
                print(f"    Fix: {remove_cmd}")
                print(f"         {add_cmd}")
                drift_lines.append(f"Codex {name}: {inst_v} → {truth_v}")

    return drift_lines


# ---------------------------------------------------------------------------
# Chunk 2: --check mode (CI/cron read-only)
# ---------------------------------------------------------------------------

def check_all_surfaces(prefer: str) -> int:
    """Read-only check of all surfaces + host drift.

    Prints one line per drift. Returns 3 if any drift found, 2 if clean.
    Never modifies files.
    """
    all_drifts: list[str] = []

    # Catalog surfaces
    try:
        versions = build_version_map(prefer)
        mk_before = MARKETPLACE.read_text(encoding="utf-8")
        ag_before = AGENTS_MARKETPLACE.read_text(encoding="utf-8")
        rd_before = README.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as e:
        print(f"marketplace-sync: ERROR reading catalog — {e}", file=sys.stderr)
        return 1

    changes: list[str] = []

    apply_manifest(MARKETPLACE, ".claude-plugin/marketplace.json", versions, changes)
    apply_manifest(AGENTS_MARKETPLACE, ".agents/plugins/marketplace.json", versions, changes)
    apply_readme(rd_before, versions, changes)

    if changes:
        print("\nCatalog/README surface drifts:")
        for c in changes:
            print(f"  DRIFT {c}")
        all_drifts.extend(changes)
    else:
        print("\nCatalog surfaces: clean")

    # Host drift
    host_drifts = check_hosts(versions)
    all_drifts.extend(host_drifts)

    # package.json / plugin.json drift (Chunk 3)
    pkg_drifts = scan_package_json_drift(TOOLKIT_ROOT / "plugins")
    drifted = [r for r in pkg_drifts if r["drifted"]]
    if drifted:
        print("\npackage.json ↔ plugin.json drifts:")
        for item in drifted:
            line = (
                f"  DRIFT {item['name']}: package.json={item['package_json_version']} "
                f"vs plugin.json={item['plugin_json_version']}"
            )
            print(line)
            all_drifts.append(line.strip())
    else:
        print("\npackage.json ↔ plugin.json: clean")

    # Mirror-on-main hygiene (Chunk 5)
    off_main = report_mirror_branch_hygiene()
    for r in off_main:
        all_drifts.append(f"Mirror {r['name']} off-main (branch={r['branch'] or r['error']})")

    if all_drifts:
        print(f"\n{len(all_drifts)} drift(s) found — exit 3")
        return 3
    print("\nAll surfaces clean — exit 2")
    return 2


# ---------------------------------------------------------------------------
# Chunk 3: package.json ↔ plugin.json drift detection
# ---------------------------------------------------------------------------

def scan_package_json_drift(plugins_dir: Path) -> list[dict]:
    """For each plugins/<name>/ mirror with both package.json and plugin.json,
    report version mismatch.

    Returns list of dicts: {name, package_json_version, plugin_json_version, drifted}
    """
    results = []
    if not plugins_dir.is_dir():
        return results

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        name = plugin_dir.name

        pj_path = plugin_dir / "package.json"
        # plugin.json can be at .claude-plugin/plugin.json or plugin.json (root)
        plj_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plj_path.exists():
            plj_path = plugin_dir / "plugin.json"

        if not pj_path.exists() or not plj_path.exists():
            continue

        try:
            pj_v = json.loads(pj_path.read_text(encoding="utf-8")).get("version", "")
        except (json.JSONDecodeError, OSError):
            pj_v = ""
        try:
            plj_v = json.loads(plj_path.read_text(encoding="utf-8")).get("version", "")
        except (json.JSONDecodeError, OSError):
            plj_v = ""

        results.append({
            "name": name,
            "package_json_version": pj_v,
            "plugin_json_version": plj_v,
            "drifted": pj_v != plj_v,
        })

    return results


def detect_pkg_plugin_drift_from_pairs(pairs: list[dict]) -> list[dict]:
    """Filter a list of {name, package_json_version, plugin_json_version} dicts
    to only those with a mismatch, adding drifted=True.

    This is the pure comparison logic, testable without touching the filesystem.
    """
    result = []
    for item in pairs:
        pj_v = item.get("package_json_version", "")
        plj_v = item.get("plugin_json_version", "")
        if pj_v != plj_v:
            result.append({**item, "drifted": True})
    return result


def report_package_json_drift() -> list[dict]:
    """Scan and print package.json ↔ plugin.json drift. Returns drifted items."""
    results = scan_package_json_drift(TOOLKIT_ROOT / "plugins")
    drifted = [r for r in results if r["drifted"]]

    print(f"\n--- package.json ↔ plugin.json drift ({len(results)} mirrors checked) ---")
    if not drifted:
        print("  All mirrors in sync.")
    else:
        for item in drifted:
            print(
                f"  DRIFT {item['name']:<22} "
                f"package.json={item['package_json_version']}  "
                f"plugin.json={item['plugin_json_version']}"
            )
    return drifted


# ---------------------------------------------------------------------------
# Chunk 5: mirror-on-main invariant
# ---------------------------------------------------------------------------
#
# Rule: every plugin mirror under plugins/<name>/ (symlink or directory) MUST
# resolve to a git working tree whose current branch is `main`. The marketplace
# distributes whatever the mirror reflects, so any drift (e.g. a source repo
# worktree gets temporarily checked out on a feature branch) silently mis-ships
# the wrong version. This check makes that drift impossible to ignore.
#
# Detection is read-only: `git -C <target> branch --show-current`. A non-git
# target, missing target, or detached HEAD records an `error` field and is
# treated as off-main. Plain directories (rare; e.g. .claude-code-debugger
# stub-dirs that used to be tracked) are skipped — they have no source repo.


def scan_mirror_branches(plugins_dir: Path) -> list[dict]:
    """For each entry under plugins_dir, resolve symlink target + git branch.

    Returns list of dicts:
      {name, target_path, branch, on_main, error}
    - target_path: absolute path the symlink resolves to (or the dir itself if not a symlink)
    - branch: current branch name, or '' on error/detached HEAD
    - on_main: True iff branch == 'main'
    - error: human-readable reason when branch lookup fails, else ''
    """
    results: list[dict] = []
    if not plugins_dir.is_dir():
        return results

    for entry in sorted(plugins_dir.iterdir()):
        # Skip hidden + non-symlink-non-dir entries (README.md, .DS_Store, .bookmark stub, etc.)
        if entry.name.startswith("."):
            continue
        if not (entry.is_symlink() or entry.is_dir()):
            continue
        # Skip plain dirs that aren't mirrors (no .claude-plugin/plugin.json AND not a symlink)
        if not entry.is_symlink():
            if not (entry / ".claude-plugin" / "plugin.json").exists() and not (entry / "plugin.json").exists():
                continue

        try:
            target = entry.resolve(strict=True)
        except (FileNotFoundError, RuntimeError) as e:
            results.append({
                "name": entry.name,
                "target_path": str(entry),
                "branch": "",
                "on_main": False,
                "error": f"resolve failed: {e}",
            })
            continue

        # Need a git repo at the target
        git_dir = target / ".git"
        if not (git_dir.is_dir() or git_dir.is_file()):  # .git can be a file for worktrees
            results.append({
                "name": entry.name,
                "target_path": str(target),
                "branch": "",
                "on_main": False,
                "error": "target is not a git working tree",
            })
            continue

        try:
            out = subprocess.run(
                ["git", "-C", str(target), "branch", "--show-current"],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            results.append({
                "name": entry.name,
                "target_path": str(target),
                "branch": "",
                "on_main": False,
                "error": f"git branch failed: {e}",
            })
            continue

        if out.returncode != 0:
            results.append({
                "name": entry.name,
                "target_path": str(target),
                "branch": "",
                "on_main": False,
                "error": f"git returned {out.returncode}: {out.stderr.strip()}",
            })
            continue

        branch = out.stdout.strip()
        results.append({
            "name": entry.name,
            "target_path": str(target),
            "branch": branch,
            "on_main": branch == "main",
            "error": "" if branch else "detached HEAD or empty branch",
        })

    return results


def find_off_main_mirrors(records: list[dict]) -> list[dict]:
    """Filter scan_mirror_branches output to only off-main entries.

    Pure function — testable without touching the filesystem.
    """
    return [r for r in records if not r.get("on_main")]


def mirror_fix_command(name: str, current_target: str) -> str:
    """Emit a fix hint for an off-main mirror. The actual main target depends
    on the operator's setup; we surface what we know and let them point it.
    """
    return (
        f"# Mirror {name} is off-main. Point it at a main-tracking working tree:\n"
        f"#   1. Find or create a worktree on main: git -C <source-repo> worktree add ../<source-repo>-main main\n"
        f"#   2. Re-link:  ln -sfn <path-to-main-worktree> plugins/{name}\n"
        f"#   Current target: {current_target}"
    )


def report_mirror_branch_hygiene() -> list[dict]:
    """Print mirror-on-main report. Returns list of off-main records (empty == clean)."""
    records = scan_mirror_branches(TOOLKIT_ROOT / "plugins")
    off_main = find_off_main_mirrors(records)

    print(f"\n--- Mirror branch hygiene ({len(records)} mirrors checked) ---")
    if not off_main:
        print("  All mirrors on main.")
        return []
    for r in off_main:
        label = r["branch"] or r["error"] or "<unknown>"
        print(f"  OFF-MAIN {r['name']:<22} branch={label}")
        print("  " + mirror_fix_command(r["name"], r["target_path"]).replace("\n", "\n  "))
    return off_main


# ---------------------------------------------------------------------------
# Chunk 4: launchd cron installation / removal
# ---------------------------------------------------------------------------

LAUNCHD_LABEL = "ai.rosslabs.marketplace-sync"
LAUNCHD_PLIST_DEST = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"

LAUNCHD_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
        <string>--all</string>
        <string>--check</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{log_dir}/marketplace-sync.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/marketplace-sync.err</string>

    <!-- Only run when the user is logged in (LaunchAgent, not LaunchDaemon) -->
    <!-- The job exits 2 (clean) or 3 (drift found). Check the log file for details. -->
</dict>
</plist>
"""


def install_cron() -> int:
    """Write the launchd plist and load it. Does NOT activate silently — user
    must call --install-cron explicitly. Prints what it's doing.

    Idempotent: unloads any previously-loaded job before writing + loading, so
    re-running --install-cron succeeds cleanly (unload failure is silently
    ignored — the job may simply not be loaded yet).
    """
    python = xml.sax.saxutils.escape(sys.executable)
    script = xml.sax.saxutils.escape(str(Path(__file__).resolve()))
    log_dir = xml.sax.saxutils.escape(str(Path.home() / "Library" / "Logs"))
    plist_content = LAUNCHD_PLIST_TEMPLATE.format(
        label=LAUNCHD_LABEL,
        python=python,
        script=script,
        log_dir=log_dir,
    )

    agents_dir = LAUNCHD_PLIST_DEST.parent
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Unload any existing job before overwriting (ignore failure — not loaded is OK)
    try:
        subprocess.run(
            ["launchctl", "unload", str(LAUNCHD_PLIST_DEST)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    LAUNCHD_PLIST_DEST.write_text(plist_content, encoding="utf-8")
    print(f"Wrote plist: {LAUNCHD_PLIST_DEST}")

    try:
        r = subprocess.run(
            ["launchctl", "load", str(LAUNCHD_PLIST_DEST)],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print(f"launchctl load succeeded.")
        else:
            print(f"launchctl load returned {r.returncode}: {r.stderr.strip()}")
            print("The plist file is written; you can load it manually:")
            print(f"  launchctl load {LAUNCHD_PLIST_DEST}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Could not run launchctl: {e}")
        print(f"Load manually: launchctl load {LAUNCHD_PLIST_DEST}")

    print(
        f"\nDaily check runs at 09:00. Logs at:\n"
        f"  {log_dir}/marketplace-sync.log\n"
        f"  {log_dir}/marketplace-sync.err\n"
        f"\nTo uninstall: marketplace-sync.py --uninstall-cron"
    )
    return 0


def uninstall_cron() -> int:
    """Unload and remove the launchd plist."""
    if not LAUNCHD_PLIST_DEST.exists():
        print(f"Plist not found: {LAUNCHD_PLIST_DEST} — nothing to remove.")
        return 0

    try:
        r = subprocess.run(
            ["launchctl", "unload", str(LAUNCHD_PLIST_DEST)],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print("launchctl unload succeeded.")
        else:
            print(f"launchctl unload returned {r.returncode}: {r.stderr.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Could not run launchctl unload: {e}")

    LAUNCHD_PLIST_DEST.unlink(missing_ok=True)
    print(f"Removed: {LAUNCHD_PLIST_DEST}")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Reconcile marketplace + README to true plugin versions")
    ap.add_argument("child_path", nargs="?", help="Single plugin dir (local mirror mode)")
    ap.add_argument("--all", action="store_true", help="Reconcile every plugin across all surfaces")
    ap.add_argument("--source", choices=["external", "local"], default="external",
                    help="Version source of truth (default: external repo via gh)")
    ap.add_argument("--write", action="store_true", help="Apply changes (default: dry-run)")
    ap.add_argument("--check-hosts", action="store_true",
                    help="Compare installed host plugin versions vs source-of-truth; emit fix cmds")
    ap.add_argument("--check", action="store_true",
                    help="Read-only: exit 3 if ANY surface drifts (catalog/README/.agents/hosts). For CI/cron.")
    ap.add_argument("--install-cron", action="store_true",
                    help="Install launchd plist to run --all --check daily at 09:00 (macOS only)")
    ap.add_argument("--uninstall-cron", action="store_true",
                    help="Remove the launchd plist installed by --install-cron")
    args = ap.parse_args(argv)

    # Cron management — no other files needed
    if args.install_cron:
        return install_cron()
    if args.uninstall_cron:
        return uninstall_cron()

    # --check mode: read-only, CI-safe, exit 3 on any drift
    if args.check:
        for p in (MARKETPLACE, AGENTS_MARKETPLACE, README):
            if not p.exists():
                die(f"expected file not found: {p}")
        return check_all_surfaces(args.source)

    for p in (MARKETPLACE, AGENTS_MARKETPLACE, README):
        if not p.exists():
            die(f"expected file not found: {p}")

    if args.all:
        versions = build_version_map(args.source)
    elif args.check_hosts:
        # --check-hosts standalone: read truth from local catalog (no gh calls needed)
        versions = catalog_versions_local()
        check_hosts(versions)
        report_package_json_drift()
        report_mirror_branch_hygiene()
        return 0
    elif args.child_path:
        child = Path(args.child_path).expanduser().resolve() / ".claude-plugin" / "plugin.json"
        if not child.exists():
            die(f"child plugin.json not found: {child}")
        pj = json.loads(child.read_text(encoding="utf-8"))
        if not pj.get("name"):
            die("child plugin.json missing 'name'")
        versions = {pj["name"]: pj.get("version")}
    else:
        die("provide a plugin path, --all, --check, --check-hosts, --install-cron, or --uninstall-cron")

    changes: list[str] = []
    mk_before = MARKETPLACE.read_text(encoding="utf-8")
    ag_before = AGENTS_MARKETPLACE.read_text(encoding="utf-8")
    rd_before = README.read_text(encoding="utf-8")

    mk_after = apply_manifest(MARKETPLACE, ".claude-plugin/marketplace.json", versions, changes)
    ag_after = apply_manifest(AGENTS_MARKETPLACE, ".agents/plugins/marketplace.json", versions, changes)
    rd_after = apply_readme(rd_before, versions, changes)

    # --check-hosts: report host install drift (summarized under --all too)
    if args.check_hosts or args.all:
        check_hosts(versions)
        report_package_json_drift()
        report_mirror_branch_hygiene()

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
