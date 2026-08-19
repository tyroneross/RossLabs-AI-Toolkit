#!/usr/bin/env python3
"""
marketplace-sync: reconcile every distribution surface to a plugin's true version.

Four surfaces drift independently and must describe the same state:
  1. .claude-plugin/marketplace.json   — drives Claude Code installs
  2. .agents/plugins/marketplace.json   — drives Codex / cross-agent installs
  3. README.md                          — drives GitHub discovery
  4. plugins/README.md                  — drives plugin-index discovery

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
  marketplace-sync.py --act                      # reconcile+commit+push+refresh (dedicated worktree)
  marketplace-sync.py --install-cron             # install launchd daily --act run (macOS)
  marketplace-sync.py --uninstall-cron           # remove launchd plist

Exit codes:
  0  changes proposed (and written with --write); --act: acted or already clean
  1  shape problem (bad JSON, missing file, plugin not found); --act: push/refresh failure
  2  no changes (every surface already in sync)
  3  --check mode: at least one surface is drifted (catalog, docs, hosts, etc.)
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import difflib
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import xml.sax.saxutils
from pathlib import Path

# Absolute fallbacks for `gh` when PATH is minimal (e.g. under launchd, where
# the job inherits /usr/bin:/bin and Homebrew's bin dir is absent). Without
# this, external_version() raises FileNotFoundError on a bare `gh` invocation
# and silently falls back to the lagging local mirror for every plugin.
_GH_FALLBACKS = ("/opt/homebrew/bin/gh", "/usr/local/bin/gh")


def gh_bin() -> str | None:
    """Resolve the `gh` executable robustly. Returns an absolute path or None.

    Order: PATH (shutil.which) → known Homebrew/usr-local locations. Returns
    None when gh is unavailable so external_version() can fail open (skip the
    external read, fall back to the local mirror) rather than crash.
    """
    found = shutil.which("gh")
    if found:
        return found
    for cand in _GH_FALLBACKS:
        if os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    return None

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = TOOLKIT_ROOT / ".claude-plugin" / "marketplace.json"
AGENTS_MARKETPLACE = TOOLKIT_ROOT / ".agents" / "plugins" / "marketplace.json"
README = TOOLKIT_ROOT / "README.md"
PLUGINS_README = TOOLKIT_ROOT / "plugins" / "README.md"

CLAUDE_MARKETPLACE_KEY = "rosslabs-ai-toolkit"
CODEX_MARKETPLACE_KEY = "ross-labs-local"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
CODEX_PLUGIN_CACHE = Path.home() / ".codex" / "plugins" / "cache"


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
    gh = gh_bin()
    if gh is None:
        # gh unavailable (e.g. minimal launchd PATH) — fail open so the caller
        # falls back to the local mirror instead of crashing.
        print("  (gh not found — skipping external version read, using local mirror)")
        return None
    path = source.get("path", "").strip("/")
    candidates: list[str] = []
    if path:
        candidates += [f"{path}/.claude-plugin/plugin.json", f"{path}/plugin.json"]
    candidates += [".claude-plugin/plugin.json", "plugin.json"]
    for c in candidates:
        try:
            out = subprocess.run(
                [gh, "api", f"repos/{repo}/contents/{c}"],
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


def local_version(name: str, subpath: str = "") -> str | None:
    """Version from the in-repo mirror plugins/<name>/.

    When the marketplace entry declares a `source.path` (a monorepo sub-dir,
    e.g. agent-astronomer / agent-builder ship the plugin under `plugin/`), the
    mirror symlink points at the repo ROOT but the plugin.json lives in that
    sub-dir. `subpath` (the entry's source.path) is checked first so those
    plugins resolve locally; the repo-root locations remain the fallback for
    standard single-plugin repos.
    """
    sub = subpath.strip("/")
    rels: list[str] = []
    if sub:
        rels += [
            f"plugins/{name}/{sub}/.claude-plugin/plugin.json",
            f"plugins/{name}/{sub}/plugin.json",
        ]
    rels += [f"plugins/{name}/.claude-plugin/plugin.json", f"plugins/{name}/plugin.json"]
    for rel in rels:
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
    subpath = src.get("path", "") if isinstance(src, dict) else ""
    if prefer == "local":
        v = local_version(name, subpath)
        return (v, "local") if v else (external_version(src), "external")
    v = external_version(src)
    if v:
        return v, "external"
    v = local_version(name, subpath)
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

# plugins/README table-row regex: | name | [repo](url) | description | version |
PLUGIN_INDEX_ROW_RE = re.compile(
    r"^(\|\s*([A-Za-z0-9_\-]+)\s*\|\s*\[[^\]]+\]\([^)]+\)\s*\|\s*[^|]*\|\s*)([^|\s]+)(\s*\|\s*)$",
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


def apply_plugin_index_readme(text: str, versions: dict[str, str], changes: list[str]) -> str:
    def replacer(m: re.Match) -> str:
        name = m.group(2)
        new_v = versions.get(name)
        old_v = m.group(3).strip()
        if new_v and new_v != old_v:
            changes.append(f"plugins/README.md: {name} version {old_v} → {new_v}")
            return f"{m.group(1)}{new_v}{m.group(4)}"
        return m.group(0)
    return PLUGIN_INDEX_ROW_RE.sub(replacer, text)


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
# Chunk 1: Codex install-state parsing
# ---------------------------------------------------------------------------

def newest_cached_version(plugin_dir: Path) -> str:
    """Return the newest cached version directory for one Codex plugin.

    Codex 0.130.0 no longer exposes `codex plugin list`; installed/enabled
    state lives in ~/.codex/config.toml and cached plugin copies live under
    ~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/.
    """
    if not plugin_dir.is_dir():
        return ""
    versions = [p.name for p in plugin_dir.iterdir() if p.is_dir()]
    if not versions:
        return ""
    best = versions[0]
    for candidate in versions[1:]:
        if semver_lt(best, candidate):
            best = candidate
    return best


def parse_codex_config_plugins(
    data: dict,
    marketplace_key: str,
    cache_root: Path | None = None,
) -> dict[str, dict]:
    """Parse Codex config.toml plugin entries for one marketplace.

    Returns:
        {plugin_name: {version, status}} for configured entries. `version` is
        resolved from the cache when cache_root is provided; empty means the
        plugin is configured but no cached version could be found.
    """
    result: dict[str, dict] = {}
    suffix = f"@{marketplace_key}"
    plugins = data.get("plugins", {})
    if not isinstance(plugins, dict):
        return result

    for key, meta in plugins.items():
        if not isinstance(key, str) or not key.endswith(suffix):
            continue
        name = key[: -len(suffix)]
        enabled = bool(meta.get("enabled", True)) if isinstance(meta, dict) else True
        version = ""
        if cache_root is not None:
            version = newest_cached_version(cache_root / marketplace_key / name)
        result[name] = {
            "version": version,
            "status": "enabled" if enabled else "disabled",
        }
    return result


def load_codex_installed(
    marketplace_key: str = CODEX_MARKETPLACE_KEY,
    config_path: Path = CODEX_CONFIG,
    cache_root: Path = CODEX_PLUGIN_CACHE,
) -> dict[str, dict] | None:
    """Load Codex plugin state from config.toml + plugin cache.

    Returns None with a printed warning if Codex config is absent or malformed.
    """
    if not config_path.exists():
        print(f"  (skip Codex host check — {config_path} not found)")
        return None
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as e:
        print(f"  (skip Codex host check — could not read {config_path}: {e})")
        return None
    return parse_codex_config_plugins(data, marketplace_key, cache_root)


# ---------------------------------------------------------------------------
# Chunk 1: Legacy Codex plugin list parsing
# ---------------------------------------------------------------------------

def parse_codex_plugin_list(output: str, marketplace_key: str) -> dict[str, dict]:
    """Parse legacy `codex plugin list` stdout for marketplace_key.

    Current Codex CLI (verified at 0.130.0) removed this command. Keep this
    parser for backward compatibility with older fixture output; live checks use
    load_codex_installed().

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


def codex_remediate_cmd(name: str, marketplace_key: str) -> str:
    """Emit the current Codex marketplace refresh command.

    Codex 0.130.0 exposes marketplace-level add/upgrade/remove commands, not
    per-plugin add/remove/update commands. One marketplace upgrade refreshes all
    configured plugins from that marketplace.
    """
    return f"codex plugin marketplace upgrade {marketplace_key}"


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
        src = entry.get("source", {})
        subpath = src.get("path", "") if isinstance(src, dict) else ""
        v = entry.get("version") or local_version(name, subpath)
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
    codex_installed = load_codex_installed()
    if codex_installed is not None:
        codex_drift = find_codex_drift(codex_installed, truth)
        if not codex_drift:
            print("  All Codex installs up to date.")
        else:
            print("  Note: Codex refreshes plugins at marketplace scope.")
            printed_cmds: set[str] = set()
            for item in codex_drift:
                name = item["name"]
                inst_v = item["installed_version"]
                truth_v = item["truth_version"]
                print(f"  STALE Codex {name}: {inst_v} → {truth_v}")
                cmd = codex_remediate_cmd(name, CODEX_MARKETPLACE_KEY)
                if cmd not in printed_cmds:
                    print(f"    Fix: {cmd}")
                    printed_cmds.add(cmd)
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
        plugins_rd_before = PLUGINS_README.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as e:
        print(f"marketplace-sync: ERROR reading catalog — {e}", file=sys.stderr)
        return 1

    changes: list[str] = []

    apply_manifest(MARKETPLACE, ".claude-plugin/marketplace.json", versions, changes)
    apply_manifest(AGENTS_MARKETPLACE, ".agents/plugins/marketplace.json", versions, changes)
    apply_readme(rd_before, versions, changes)
    apply_plugin_index_readme(plugins_rd_before, versions, changes)

    if changes:
        print("\nCatalog/doc surface drifts:")
        for c in changes:
            print(f"  DRIFT {c}")
        all_drifts.extend(changes)
    else:
        print("\nCatalog/doc surfaces: clean")

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
# Chunk 6: --act mode (cron-driven self-healing reconcile)
# ---------------------------------------------------------------------------
#
# --check (the prior cron mode) only DETECTS drift (exit 3). It never acts, so
# the catalog drifted for days unnoticed. --act closes the loop: it reconciles,
# commits, pushes, and refreshes the local plugin cache — all in a DEDICATED
# main-pinned worktree, never the developer's checkout (whose branch may be a
# feature branch a human/agent has checked out). Committing there would land on
# the wrong branch.
#
# Flow:
#   1. Resolve the canonical repo (script's git toplevel) + its origin URL.
#   2. Ensure a dedicated worktree exists, pinned to a `main`-tracking branch.
#   3. git fetch origin; git reset --hard origin/main (worktree only).
#   4. Run the worktree's OWN copy of this script with --all --write
#      --source external (its TOOLKIT_ROOT resolves to the worktree, so the
#      reconcile edits the worktree's surfaces, not the developer checkout).
#   5. If the worktree is now dirty: commit (message lists bumps) + push origin main.
#   6. Refresh the local Claude plugin-cache marketplace clone (ff-only).
#
# Exit codes (act mode): 0 acted-or-clean, non-zero on push/refresh failure.

ACT_WORKTREE = Path.home() / ".cache" / "marketplace-sync" / "act-worktree"
ACT_LOCKFILE = Path.home() / ".cache" / "marketplace-sync" / "act.lock"
PLUGIN_CACHE_MARKETPLACE = (
    Path.home() / ".claude" / "plugins" / "marketplaces" / "rosslabs-ai-toolkit"
)


@contextlib.contextmanager
def _act_lock(lockfile: Path = ACT_LOCKFILE):
    """Hold an exclusive non-blocking flock for the whole act flow so two
    concurrent runs (e.g. a manual run racing the cron) can't reset/commit over
    each other in the shared worktree. A second runner exits cleanly (code 0)
    rather than corrupting state."""
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lockfile, "w")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            _log("another act run holds the lock — exiting cleanly (no-op).")
            fh.close()
            raise SystemExit(0)
        yield
    finally:
        with contextlib.suppress(Exception):
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()


def _log(msg: str) -> None:
    """Stdout line (captured to the launchd .log)."""
    print(f"[act] {msg}", flush=True)


# Absolute fallbacks for `git` when PATH is minimal (launchd: /usr/bin:/bin,
# Homebrew bin absent). Mirrors gh_bin() so _run_git resolves git robustly.
_GIT_FALLBACKS = ("/usr/bin/git", "/opt/homebrew/bin/git", "/usr/local/bin/git")


def git_bin() -> str:
    """Resolve the `git` executable. Returns an absolute path when one is found,
    else the bare string 'git' (so the call still fails cleanly via _run_git's
    127 path rather than this resolver raising)."""
    found = shutil.which("git")
    if found:
        return found
    for cand in _GIT_FALLBACKS:
        if os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    return "git"


def _run_git(args: list[str], cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a git command, capturing output. Never raises — on a missing git
    binary or timeout it returns a synthetic returncode=127 result so callers
    can inspect returncode uniformly instead of catching exceptions (fail-clean
    under launchd's minimal PATH). The git binary is resolved absolutely via
    git_bin() so a minimal launchd PATH can't fail a bare `git` lookup."""
    git = git_bin()
    try:
        return subprocess.run(
            [git, *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args=[git, *args], returncode=127, stdout="", stderr=str(e))


def canonical_repo_root() -> Path:
    """The git toplevel of the checkout this script lives in (the canonical repo)."""
    r = _run_git(["rev-parse", "--show-toplevel"], cwd=Path(__file__).resolve().parent)
    if r.returncode != 0:
        die(f"could not resolve git toplevel for {__file__}: {r.stderr.strip()}")
    return Path(r.stdout.strip())


def origin_url(repo: Path) -> str | None:
    """Return the origin fetch URL for a repo, or None."""
    r = _run_git(["remote", "get-url", "origin"], cwd=repo)
    return r.stdout.strip() if r.returncode == 0 else None


ACT_BRANCH = "marketplace-sync-act"


def _worktree_is_valid(worktree: Path, repo: Path) -> bool:
    """A reused act worktree is trusted ONLY if it is genuinely OUR dedicated
    worktree: git toplevel == worktree path, on the dedicated branch, and
    sharing the canonical repo's origin URL. Guards against a stale/symlinked
    worktree pointing at the developer checkout (which would commit on the
    wrong branch — the exact failure act mode exists to prevent)."""
    if not (worktree / ".git").exists():
        return False
    top = _run_git(["rev-parse", "--show-toplevel"], cwd=worktree)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != worktree.resolve():
        return False
    branch = _run_git(["branch", "--show-current"], cwd=worktree)
    if branch.returncode != 0 or branch.stdout.strip() != ACT_BRANCH:
        return False
    wt_origin = origin_url(worktree)
    repo_origin = origin_url(repo)
    return bool(wt_origin) and wt_origin == repo_origin


def ensure_act_worktree(repo: Path, worktree: Path = ACT_WORKTREE) -> Path:
    """Ensure a VALID dedicated worktree exists at `worktree`, on the dedicated
    `marketplace-sync-act` branch tracking origin/main.

    Every run re-validates an existing worktree (toplevel/branch/origin); an
    invalid or absent one is (re)created. The dedicated branch name never
    collides with a human's `main` checkout in the canonical repo.
    """
    worktree.parent.mkdir(parents=True, exist_ok=True)
    if _worktree_is_valid(worktree, repo):
        return worktree
    # Remove an invalid worktree registration + dir, then recreate cleanly.
    _run_git(["worktree", "remove", "--force", str(worktree)], cwd=repo)
    _run_git(["worktree", "prune"], cwd=repo)
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
    # Fetch first so origin/main exists for the new worktree.
    _run_git(["fetch", "origin", "main"], cwd=repo)
    r = _run_git(
        ["worktree", "add", "--force", "-B", ACT_BRANCH, str(worktree), "origin/main"],
        cwd=repo,
    )
    if r.returncode != 0:
        die(f"failed to create act worktree at {worktree}: {r.stderr.strip()}")
    if not _worktree_is_valid(worktree, repo):
        die(f"act worktree at {worktree} failed validation after creation — refusing to act")
    return worktree


# The only surfaces the reconcile is allowed to change — staged explicitly so a
# commit can never capture untracked residue (e.g. a __pycache__ dir or a
# half-written file from a crashed prior run).
ACT_SURFACE_FILES = (
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    "README.md",
    "plugins/README.md",
)


def sync_worktree_to_main(worktree: Path) -> None:
    """fetch origin + hard-reset + clean the worktree to a pristine origin/main
    (discards any prior act-run residue, tracked OR untracked, so each run
    starts from a clean canonical main)."""
    f = _run_git(["fetch", "origin", "main"], cwd=worktree)
    if f.returncode != 0:
        die(f"git fetch origin main failed: {f.stderr.strip()}", code=1)
    rs = _run_git(["reset", "--hard", "origin/main"], cwd=worktree)
    if rs.returncode != 0:
        die(f"git reset --hard origin/main failed: {rs.stderr.strip()}", code=1)
    # reset --hard leaves untracked files; clean removes them so staging residue
    # cannot leak into the commit.
    cl = _run_git(["clean", "-ffd"], cwd=worktree)
    if cl.returncode != 0:
        die(f"git clean -ffd failed: {cl.stderr.strip()}", code=1)
    _log(f"worktree reset+clean to origin/main @ {rs.stdout.strip() or 'ok'}")


def worktree_is_dirty(worktree: Path) -> bool:
    """True if the worktree has staged/unstaged changes after reconcile.

    Fails CLOSED: a non-zero `git status` (treated as an error) returns True so
    the caller does not silently assume 'clean' and skip a needed commit. The
    explicit-file staging downstream still bounds what actually gets committed.
    """
    r = _run_git(["status", "--porcelain"], cwd=worktree)
    if r.returncode != 0:
        _log(f"git status failed ({r.returncode}) — treating worktree as dirty (fail-closed)")
        return True
    return bool(r.stdout.strip())


def commit_message_for(changed: list[str]) -> str:
    """Build a clear commit message listing the catalog bumps."""
    body = "\n".join(f"  - {c}" for c in changed) if changed else "  (surface reconcile)"
    return (
        "chore(marketplace): auto-sync catalog to external plugin versions\n\n"
        "Reconciled by the marketplace-sync --act cron. Changes:\n"
        f"{body}\n"
    )


def reconcile_in_worktree(worktree: Path) -> tuple[int, str]:
    """Run the worktree's own copy of this script with --all --write
    --source external. Returns (returncode, combined_output).

    Running the worktree's copy (not this file) makes TOOLKIT_ROOT resolve to
    the worktree, so the reconcile edits the worktree's surfaces.
    """
    script = worktree / "scripts" / "marketplace-sync.py"
    if not script.exists():
        die(f"worktree script missing: {script}", code=1)
    try:
        r = subprocess.run(
            [sys.executable, str(script), "--all", "--write", "--source", "external"],
            cwd=str(worktree), capture_output=True, text=True, timeout=300,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        # Fail clean (nonzero) instead of escaping as a traceback under launchd.
        return 1, f"reconcile subprocess failed: {e}"
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def refresh_plugin_cache(cache: Path = PLUGIN_CACHE_MARKETPLACE) -> bool:
    """Fast-forward-only update the local plugin-cache marketplace clone so
    /plugin shows fresh labels. Never force. Returns True on success (or clean
    skip when the cache is absent — that's not a failure)."""
    if not (cache / ".git").exists():
        _log(f"plugin cache not present at {cache} — skipping refresh (ok)")
        return True
    f = _run_git(["fetch", "origin", "main"], cwd=cache)
    if f.returncode != 0:
        _log(f"plugin-cache fetch failed: {f.stderr.strip()}")
        return False
    m = _run_git(["merge", "--ff-only", "origin/main"], cwd=cache)
    if m.returncode != 0:
        _log(f"plugin-cache ff-only merge failed (cache diverged?): {m.stderr.strip()}")
        return False
    _log(f"plugin cache refreshed: {m.stdout.strip()}")
    return True


# ---------------------------------------------------------------------------
# Local repo registry generation (private — build-loop-memory only)
# ---------------------------------------------------------------------------
# The registry inventories private local projects and absolute machine paths, so
# it must NEVER land in this PUBLIC toolkit. It is generated into the private
# build-loop-memory repo and committed there only when its remote is private.

MEMORY_REPO = Path.home() / "dev" / "git-folder" / "build-loop-memory"
REGISTRY_DIR = MEMORY_REPO / "registry"
REGISTRY_FILES = ("REGISTRY.md", "registry.json", "PLUGINS.md", "plugins.json")
# One pointer line into the memory index (the repo's index convention is INDEX.md,
# not MEMORY.md — verified from the repo). The registry files are generated
# artifacts, not memories, so they are referenced, not written via memory_writer.
MEMORY_INDEX = MEMORY_REPO / "INDEX.md"
REGISTRY_INDEX_POINTER = (
    "- [`registry/REGISTRY.md`](registry/REGISTRY.md) — generated local app/repo "
    "registry (scan of `~/dev/git-folder`, refreshed by the marketplace-sync "
    "`--act` cron). Generated artifact — do not hand-edit."
)


def _load_plugin_registry_module():
    """Import the colocated plugin_registry.py (same importlib dance)."""
    import importlib.util

    mod_path = Path(__file__).resolve().parent / "plugin_registry.py"
    if not mod_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("plugin_registry", str(mod_path))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_repo_registry_module():
    """Import the colocated repo_registry.py via importlib (hyphenated sibling
    filenames make a normal import awkward; this script is itself hyphenated)."""
    import importlib.util

    mod_path = Path(__file__).resolve().parent / "repo_registry.py"
    if not mod_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("repo_registry", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def remote_is_private(repo: Path) -> bool | None:
    """True if the repo's GitHub remote is private, False if public, None if it
    can't be determined (no remote, gh unavailable, gh error). Used as the push
    gate: never push the registry to a public — or unknown — remote."""
    if not (repo / ".git").exists():
        return None
    if origin_url(repo) is None:
        return None  # no remote at all → commit locally only
    gh = gh_bin()
    if gh is None:
        return None  # can't verify visibility → treat as unknown, don't push
    try:
        r = subprocess.run(
            [gh, "repo", "view", "--json", "visibility"],
            cwd=str(repo), capture_output=True, text=True, timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    try:
        vis = json.loads(r.stdout).get("visibility", "")
    except (json.JSONDecodeError, ValueError):
        return None
    return vis.upper() == "PRIVATE"


def regenerate_registry() -> tuple[bool, str]:
    """Regenerate the local repo registry into the PRIVATE build-loop-memory repo
    and, if it changed, commit it there. Pushes only when the memory remote is
    verified private. Returns (ok, summary_line).

    This is wrapped by the caller in a try/except so a registry failure can log +
    continue and never fail the catalog sync. It also defends itself internally so
    a missing memory repo / missing module degrades cleanly.
    """
    if not MEMORY_REPO.exists():
        return True, f"memory repo absent ({MEMORY_REPO}) — registry skipped (ok)"
    mod = _load_repo_registry_module()
    if mod is None:
        return False, "repo_registry.py not found alongside marketplace-sync.py"

    # PRIVACY PRE-WRITE GUARD: the registry inventories private paths. If the
    # memory repo's remote is verified PUBLIC, refuse to even WRITE it there — a
    # public clone must never receive the inventory, not even as a local commit.
    # (None == unknown/no-remote → allowed: the user's contract is "commit
    # locally always, push only if private"; only a CONFIRMED public remote
    # blocks the write.)
    if remote_is_private(MEMORY_REPO) is False:
        return False, (
            f"REFUSING to write registry: {MEMORY_REPO} has a PUBLIC remote — "
            "private inventory must never land in a public repo"
        )

    # Add the index pointer once (idempotent) — but ONLY if INDEX.md has no
    # unrelated pending edits (otherwise our path-scoped commit of INDEX.md would
    # sweep those edits in). When INDEX.md is already dirty, skip the pointer this
    # run; the registry files still commit cleanly on their own.
    index_is_committable = _index_pointer_safe_to_add()

    summary = mod.generate(out_dir=REGISTRY_DIR, write=True)
    _log(f"registry: scanned {summary['count']} repos → {summary['md_path']}")

    # Plugin-level index, same pass, same privacy guard (already cleared above).
    # Repo-level answers "what is on this machine"; this answers "what do we
    # publish, to which hosts, and is it current" -- which is the question the
    # catalog actually depends on. Failure here must not fail the catalog sync.
    pmod = _load_plugin_registry_module()
    if pmod is None:
        _log("plugin index: plugin_registry.py not found — skipped")
    else:
        try:
            pidx = pmod.build_index()
            (REGISTRY_DIR / pmod.MD_NAME).write_text(
                pmod.render_md(pidx), encoding="utf-8")
            (REGISTRY_DIR / pmod.JSON_NAME).write_text(
                json.dumps(pidx, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            behind = [x["name"] for x in pidx["plugins"]
                      if x.get("publish_state") == "local-behind-published"]
            _log(f"plugin index: {pidx['count']} plugins → {REGISTRY_DIR / pmod.MD_NAME}")
            if behind:
                _log(f"plugin index: LOCAL MAIN BEHIND PUBLISHED for {behind}")
        except Exception as exc:  # noqa: BLE001 — advisory, never fails the sync
            _log(f"plugin index: failed ({exc}) — continuing")

    # build-loop-memory is a live, frequently-dirty repo. We must commit ONLY our
    # own files and never sweep in unrelated working-tree changes (the 30+ dirty
    # JSONL files the memory repo routinely carries). Strategy: figure out which
    # of OUR files actually changed vs HEAD, then path-scope both `add` and
    # `commit` to exactly those files. A path-scoped `git commit -- <paths>`
    # commits only those paths regardless of what else is staged in the index.
    our_files = [f"registry/{f}" for f in REGISTRY_FILES]
    if index_is_committable and MEMORY_INDEX.exists():
        our_files.append("INDEX.md")
    our_files = [rel for rel in our_files if (MEMORY_REPO / rel).exists()]

    changed: list[str] = []
    for rel in our_files:
        # `diff --quiet HEAD -- rel` exits 1 when the file differs from HEAD
        # (tracked-and-modified OR untracked-but-now-present after add). Use
        # status to catch the untracked case (a brand-new registry dir).
        st = _run_git(["status", "--porcelain", "--", rel], cwd=MEMORY_REPO)
        if (st.stdout or "").strip():
            changed.append(rel)
    if not changed:
        return True, "registry unchanged — nothing to commit in build-loop-memory"

    for rel in changed:
        _run_git(["add", "--", rel], cwd=MEMORY_REPO)

    msg = (
        "registry: refresh local repo registry\n\n"
        f"Generated by marketplace-sync --act ({summary['count']} repos scanned "
        f"under {summary['root']}). Generated artifact — do not hand-edit."
    )
    # Path-scoped commit: ONLY our files land, even if the memory repo has other
    # staged/dirty changes from a concurrent process or the user.
    cm = _run_git(["commit", "-m", msg, "--", *changed], cwd=MEMORY_REPO)
    if cm.returncode != 0:
        return False, f"registry commit failed: {cm.stderr.strip()}"
    staged = changed
    head = _run_git(["rev-parse", "HEAD"], cwd=MEMORY_REPO).stdout.strip()
    _log(f"registry: committed {head[:10]} in build-loop-memory ({len(staged)} file(s))")

    priv = remote_is_private(MEMORY_REPO)
    if priv is True:
        push = _run_git(["push", "origin", "HEAD"], cwd=MEMORY_REPO)
        if push.returncode != 0:
            return False, f"registry committed but push failed: {push.stderr.strip()}"
        return True, f"registry committed {head[:10]} and pushed (remote private)"
    if priv is False:
        return True, (
            f"registry committed {head[:10]} locally; remote is PUBLIC — "
            "NOT pushing (privacy gate)"
        )
    return True, (
        f"registry committed {head[:10]} locally; remote visibility unknown "
        "(no remote / gh unavailable) — NOT pushing"
    )


def _index_pointer_safe_to_add() -> bool:
    """Add the registry pointer to build-loop-memory/INDEX.md exactly once, but
    ONLY when doing so is safe to path-scope-commit. Returns True if INDEX.md may
    be included in the registry commit, False if it must be left out.

    The hazard: a path-scoped `git commit -- INDEX.md` commits the WHOLE current
    INDEX.md. If INDEX.md already carries unrelated pending edits, committing it
    would sweep those in. So:
      - INDEX.md missing                       → False (nothing to commit)
      - pointer already present AND INDEX clean → True  (idempotent, safe)
      - pointer already present BUT INDEX dirty → False (unrelated edits pending)
      - pointer absent AND INDEX clean          → write pointer, return True
      - pointer absent BUT INDEX already dirty   → leave INDEX untouched, False
    """
    if not MEMORY_INDEX.exists():
        return False
    # Is INDEX.md modified relative to HEAD right now (before we touch it)?
    st = _run_git(["status", "--porcelain", "--", "INDEX.md"], cwd=MEMORY_REPO)
    index_already_dirty = bool((st.stdout or "").strip())

    try:
        text = MEMORY_INDEX.read_text(encoding="utf-8")
    except OSError:
        return False

    if "registry/REGISTRY.md" in text:
        # Pointer present already. Safe to (re)commit only if INDEX is otherwise
        # clean — if it's dirty, those edits aren't ours, so leave it out.
        return not index_already_dirty

    if index_already_dirty:
        # Pointer absent but INDEX has unrelated pending edits — do NOT add the
        # pointer this run (we'd have to commit the unrelated edits with it).
        return False

    # Pointer absent and INDEX clean → add it; INDEX is now safe to commit
    # (its only change vs HEAD is our pointer block).
    sep = "" if text.endswith("\n") else "\n"
    block = (
        f"{sep}\n## Local Repo Registry\n\n"
        "Generated inventory of local projects under `~/dev/git-folder` "
        "(branch, last commit, dirty state, version). Private — never committed "
        "to a public repo.\n\n"
        f"{REGISTRY_INDEX_POINTER}\n"
    )
    try:
        MEMORY_INDEX.write_text(text + block, encoding="utf-8")
    except OSError:
        return False
    return True


def act_mode() -> int:
    """Reconcile → commit → push → refresh, in a dedicated main-pinned worktree.

    Whole flow is serialized under an flock so concurrent runs can't clobber the
    shared worktree. Returns 0 on success (acted or already clean), non-zero on
    push/refresh failure (so launchd surfaces it in the .err and the operator
    notices).
    """
    with _act_lock():
        repo = canonical_repo_root()
        url = origin_url(repo)
        _log(f"canonical repo: {repo} (origin={url})")
        worktree = ensure_act_worktree(repo)
        sync_worktree_to_main(worktree)

        rc, out = reconcile_in_worktree(worktree)
        # Surface the reconcile output (proposed/applied changes) into the log.
        for line in out.splitlines():
            _log(line)
        if rc not in (0, 2):
            die(f"reconcile failed (exit {rc}) — see log above", code=1)

        if not worktree_is_dirty(worktree):
            _log("no catalog changes — surfaces already in sync.")
            # Still refresh the cache so a prior unpushed origin advance lands locally.
            cache_ok = refresh_plugin_cache()
            # Registry still refreshes nightly even when the catalog is clean.
            reg_ok = _run_registry_step()
            return _act_exit(cache_ok, reg_ok)

        # Stage ONLY the known reconcile surfaces (never `-A`) so a commit can
        # never capture untracked residue. Skip surfaces that don't exist.
        staged_any = False
        for rel in ACT_SURFACE_FILES:
            if (worktree / rel).exists():
                a = _run_git(["add", "--", rel], cwd=worktree)
                if a.returncode != 0:
                    die(f"git add {rel} failed: {a.stderr.strip()}", code=1)
                staged_any = True
        # Verify something is actually staged before committing.
        diff_cached = _run_git(["diff", "--cached", "--name-only"], cwd=worktree)
        if diff_cached.returncode != 0:
            die(f"git diff --cached failed: {diff_cached.stderr.strip()}", code=1)
        if not staged_any or not diff_cached.stdout.strip():
            _log("worktree dirty but no surface file staged — nothing to commit.")
            cache_ok = refresh_plugin_cache()
            reg_ok = _run_registry_step()
            return _act_exit(cache_ok, reg_ok)

        # Change list = the staged surface files (derived from git, not stdout-parsing).
        changed = diff_cached.stdout.strip().splitlines()
        msg = commit_message_for(changed)
        cm = _run_git(["commit", "-m", msg], cwd=worktree)
        if cm.returncode != 0:
            die(f"git commit failed: {cm.stderr.strip()}", code=1)
        head = _run_git(["rev-parse", "HEAD"], cwd=worktree).stdout.strip()
        _log(f"committed {head[:10]}: {len(changed)} surface(s) — {', '.join(changed)}")

        push = _run_git(["push", "origin", "HEAD:main"], cwd=worktree)
        if push.returncode != 0:
            die(f"git push origin main FAILED: {push.stderr.strip()}", code=1)
        _log(f"pushed to origin/main: {push.stderr.strip() or 'ok'}")

        cache_ok = refresh_plugin_cache()
        if not cache_ok:
            _log("plugin-cache refresh failed after push — origin is updated but local cache is stale")
        reg_ok = _run_registry_step()
        _log("act run complete.")
        return _act_exit(cache_ok, reg_ok)


def _run_registry_step() -> bool:
    """Generate + commit the local repo registry, fully isolated from the catalog
    sync. A registry failure logs and returns False; it NEVER raises out of the
    act flow (so it can't fail the catalog sync). Returns True on success."""
    try:
        ok, summary = regenerate_registry()
    except Exception as e:  # defensive: registry must not crash the cron
        _log(f"registry step crashed (ignored — catalog sync unaffected): {e}")
        return False
    _log(f"registry: {summary}")
    return ok


def _act_exit(cache_ok: bool, registry_ok: bool) -> int:
    """Final act exit code.

    Two distinct contracts compose here:
      - CATALOG (cache refresh): a cache-refresh failure is fatal ON ITS OWN, and
        always was — before this change it called die(). origin may have been
        pushed but the local cache is stale, which the operator must see. So
        `cache_ok == False` → exit 1 regardless of the registry.
      - REGISTRY: must NEVER fail the catalog sync. A registry failure alone is
        non-fatal → exit 0 (logged). The registry only affects the exit code when
        the catalog ALSO failed (both-fail → 1), which is what the user's
        "nonzero only if both fail" invariant constrains: the registry never
        UPGRADES a healthy catalog run to a failure.
    """
    if not cache_ok:
        return 1  # catalog/cache failure is fatal on its own (incl. both-fail)
    return 0  # catalog ok → exit 0 even if the registry failed (logged)


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
        <string>--act</string>
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
    <!-- Act mode: reconciles + commits + pushes + refreshes the plugin cache. -->
    <!-- Exit 0 = acted-or-clean, non-zero = push/refresh failure (see .err). -->
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
        f"\nDaily --act run (reconcile + commit + push + cache refresh) at 09:00. Logs at:\n"
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
                    help="Read-only: exit 3 if ANY surface drifts (catalog/docs/hosts). For CI/cron.")
    ap.add_argument("--act", action="store_true",
                    help="Self-healing cron mode: reconcile + commit + push + refresh plugin cache, "
                         "in a dedicated main-pinned worktree (never the dev checkout).")
    ap.add_argument("--install-cron", action="store_true",
                    help="Install launchd plist to run --act daily at 09:00 (macOS only)")
    ap.add_argument("--uninstall-cron", action="store_true",
                    help="Remove the launchd plist installed by --install-cron")
    args = ap.parse_args(argv)

    # Cron management — no other files needed
    if args.install_cron:
        return install_cron()
    if args.uninstall_cron:
        return uninstall_cron()

    # --act mode: reconcile + commit + push + refresh, in a dedicated worktree
    if args.act:
        return act_mode()

    # --check mode: read-only, CI-safe, exit 3 on any drift
    if args.check:
        for p in (MARKETPLACE, AGENTS_MARKETPLACE, README, PLUGINS_README):
            if not p.exists():
                die(f"expected file not found: {p}")
        return check_all_surfaces(args.source)

    for p in (MARKETPLACE, AGENTS_MARKETPLACE, README, PLUGINS_README):
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
    plugins_rd_before = PLUGINS_README.read_text(encoding="utf-8")

    mk_after = apply_manifest(MARKETPLACE, ".claude-plugin/marketplace.json", versions, changes)
    ag_after = apply_manifest(AGENTS_MARKETPLACE, ".agents/plugins/marketplace.json", versions, changes)
    rd_after = apply_readme(rd_before, versions, changes)
    plugins_rd_after = apply_plugin_index_readme(plugins_rd_before, versions, changes)

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
                        ("README.md", rd_before, rd_after),
                        ("plugins/README.md", plugins_rd_before, plugins_rd_after)):
        d = diff_block(label, b, a)
        if d:
            print(f"--- {label} diff ---")
            print(d)

    if args.write:
        MARKETPLACE.write_text(mk_after, encoding="utf-8")
        AGENTS_MARKETPLACE.write_text(ag_after, encoding="utf-8")
        README.write_text(rd_after, encoding="utf-8")
        PLUGINS_README.write_text(plugins_rd_after, encoding="utf-8")
        print("\nApplied (--write).")
    else:
        print("\nDry-run only. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
