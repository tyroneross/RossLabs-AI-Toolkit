#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 Tyrone Ross, Jr <46267523+tyroneross@users.noreply.github.com>
# SPDX-License-Identifier: Apache-2.0
"""Plugin-level index across every agent host — Claude Code, Codex, AGENTS.md.

WHY THIS EXISTS SEPARATELY FROM repo_registry.py
------------------------------------------------
`repo_registry.py` answers "what repos are on this machine". That is the wrong
grain for a catalog: a repo may ship zero plugins, or one plugin exposed to
three different hosts under three different manifests. This answers "what
PLUGINS exist, what does each expose, to which host, and is what people can
install actually current".

WHAT IT READS, AND WHY THAT ORDER
---------------------------------
Roster comes from the declared marketplace manifest, never from a directory
scan. A scan of ~/dev/git-folder makes the published catalog depend on whatever
happens to be cloned next to it — observed 2026-08-18, when a sync silently
dropped two shipped plugins and added two sibling repos that were never meant
to publish.

Versions come from each plugin's LOCAL MAIN, not its working tree. The working
tree is whatever branch is checked out, possibly dirty, possibly mid-refactor.
A catalog must publish what main declares.

Publish state compares main against origin/main reading THE SAME FILE at both
refs. Probing candidate filenames per-ref compares different files and invents
phantom versions.

Usage:
    python3 scripts/plugin_registry.py                 # write the index
    python3 scripts/plugin_registry.py --check         # exit 1 if stale
    python3 scripts/plugin_registry.py --json          # emit to stdout
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_REPO = Path.home() / "dev" / "git-folder" / "build-loop-memory"
OUT_DIR = MEMORY_REPO / "registry"
MD_NAME = "PLUGINS.md"
JSON_NAME = "plugins.json"

MANIFESTS = (
    TOOLKIT_ROOT / ".claude-plugin" / "marketplace.json",
    TOOLKIT_ROOT / ".agents" / "plugins" / "marketplace.json",
)

#: How each host declares a plugin. A repo can satisfy several at once — that
#: is the point: one plugin, multiple agent surfaces, and the index must show
#: which hosts actually see it rather than assuming Claude Code is the only one.
HOST_MARKERS: dict[str, tuple[str, ...]] = {
    "claude-code": (".claude-plugin/plugin.json", "plugin.json"),
    "codex": (".codex-plugin/plugin.json", "plugins/codex/.codex-plugin/plugin.json",
               "codex-skills", ".codex-plugin"),
    "agents-standard": ("AGENTS.md", ".agents/plugins/marketplace.json", ".agents"),
}

#: Component dirs counted per plugin, per host convention.
#: A release tag looks like v1.2.3, 1.2.3, or plugin-v1.2.3 — optionally with a
#: prerelease suffix. Anything else (archive/*, backup-*, dated snapshots) is
#: not a published version and must never be reported as one.
RELEASE_TAG = re.compile(r"[A-Za-z-]*v?\d+\.\d+(\.\d+)?([-.+][0-9A-Za-z.-]+)?")

COMPONENT_DIRS = ("skills", "agents", "commands", "hooks")


def _git(args: list[str], cwd: Path, timeout: int = 20) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(cwd), *args],
                             capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _read_json_at_ref(repo: Path, ref: str, rel: str) -> dict | None:
    raw = _git(["show", f"{ref}:{rel}"], repo)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def load_roster() -> list[dict]:
    """Declared plugins, merged across manifests. Manifest is the authority."""
    seen: dict[str, dict] = {}
    for man in MANIFESTS:
        if not man.is_file():
            continue
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in data.get("plugins", []):
            name = entry.get("name")
            if not name:
                continue
            rec = seen.setdefault(name, {"name": name, "declared_in": []})
            rec["declared_in"].append(man.name if man.parent.name != "plugins"
                                      else ".agents/plugins/marketplace.json")
            rec.setdefault("description", entry.get("description"))
            rec.setdefault("source", entry.get("source"))
            if entry.get("version"):
                rec.setdefault("manifest_version", entry["version"])
    return sorted(seen.values(), key=lambda r: r["name"])


def resolve_checkout(name: str) -> Path | None:
    """Local checkout for a declared plugin, via the plugins/<name> symlink.

    The symlink is the DECLARED link between catalog entry and local repo. It is
    not a directory scan: a repo with no symlink is not in the catalog, and a
    symlink with no manifest entry is not published.
    """
    p = TOOLKIT_ROOT / "plugins" / name
    if p.exists():
        return p.resolve()
    sib = Path.home() / "dev" / "git-folder" / name
    return sib.resolve() if (sib / ".git").exists() else None


def detect_hosts(repo: Path, subpath: str = "") -> dict[str, bool]:
    base = repo / subpath.strip("/") if subpath else repo
    out = {}
    for host, markers in HOST_MARKERS.items():
        out[host] = any((base / m).exists() for m in markers)
    return out


def count_components(repo: Path, subpath: str = "") -> dict[str, int]:
    base = repo / subpath.strip("/") if subpath else repo
    counts: dict[str, int] = {}
    for d in COMPONENT_DIRS:
        p = base / d
        if not p.is_dir():
            counts[d] = 0
            continue
        if d == "skills":
            counts[d] = len(list(p.glob("**/SKILL.md")))
        else:
            counts[d] = len([f for f in p.glob("*.md")]) or len(
                [f for f in p.iterdir() if f.is_file()])
    return counts


def publish_status(repo: Path, subpath: str = "") -> dict:
    """main version, pushed version, last push, and drift — same file at both refs."""
    sub = subpath.strip("/")
    candidates = []
    if sub:
        candidates += [f"{sub}/.claude-plugin/plugin.json", f"{sub}/plugin.json"]
    candidates += [".claude-plugin/plugin.json", "plugin.json", "package.json"]

    main_ref = next((r for r in ("main", "master")
                     if _git(["rev-parse", "--verify", "--quiet", r], repo)), None)
    remote_ref = (f"origin/{main_ref}"
                  if main_ref and _git(["rev-parse", "--verify", "--quiet",
                                        f"origin/{main_ref}"], repo) else None)

    out: dict = {
        "main_ref": main_ref, "main_version": None, "version_source": None,
        "pushed_version": None, "last_pushed_at": None, "last_pushed_subject": None,
        "unpushed_commits": None, "unpulled_commits": None, "publish_state": "unknown",
    }
    if not main_ref:
        out["publish_state"] = "no-main"
        return out

    for rel in candidates:
        doc = _read_json_at_ref(repo, main_ref, rel)
        if doc and doc.get("version"):
            out["main_version"], out["version_source"] = doc["version"], rel
            break

    if remote_ref:
        if out["version_source"]:
            doc = _read_json_at_ref(repo, remote_ref, out["version_source"])
            out["pushed_version"] = (doc or {}).get("version")
            # A file that EXISTS upstream but declares no version is a
            # deliberate choice, not a missing push. bookmark's own commit says
            # so: "omit plugin version -- auto-SHA updates (track via
            # package.json + metadata + tag)". Conflating the two labelled 16 of
            # 18 plugins "version unpushed", which was false and would have
            # trained anyone reading this table to ignore the column.
            out["pushed_manifest_present"] = doc is not None
            out["upstream_omits_version"] = doc is not None and "version" not in doc
            # Fall back ONLY when the manifest is PRESENT upstream and
            # deliberately omits a version. If the manifest is absent entirely,
            # falling back to package.json or a tag compares a different source
            # than main used and invents a published version that never shipped
            # — the exact defect this whole function exists to avoid.
            if out["pushed_version"] is None and out.get("upstream_omits_version"):
                # Those plugins track the published version by TAG, not in the
                # manifest. The tag reachable from origin/main is therefore the
                # real "what can people install" answer for them.
                # Only RELEASE-shaped tags. `git describe --abbrev=0` returns
                # the nearest tag of any kind, and navgator's nearest was
                # `archive/pre-closeout-2026-07-14/main-before-maintenance`,
                # which it happily reported as a published version.
                tags = _git(["tag", "--merged", remote_ref, "--sort=-v:refname"], repo)
                tag = next(
                    (t for t in (tags or "").splitlines()
                     if RELEASE_TAG.fullmatch(t.strip())), None
                )
                if tag:
                    # Tags vary: v0.3.2, plugin-v0.3.1, 0.9.0. Strip everything
                    # before the first digit rather than assuming a "v" prefix,
                    # or agent-builder reports a version of "plugin-v0.3.1".
                    m = re.search(r"\d.*$", tag)
                    out["pushed_version"] = m.group(0) if m else tag
                    out["pushed_version_source"] = f"git tag ({tag})"
                else:
                    pkg = _read_json_at_ref(repo, remote_ref, "package.json")
                    if pkg and pkg.get("version"):
                        out["pushed_version"] = pkg["version"]
                        out["pushed_version_source"] = "package.json"
        last = _git(["log", "-1", "--format=%cI%x09%s", remote_ref], repo)
        if last and "\t" in last:
            out["last_pushed_at"], out["last_pushed_subject"] = last.split("\t", 1)
        counts = _git(["rev-list", "--left-right", "--count",
                       f"{remote_ref}...{main_ref}"], repo)
        if counts and len(counts.split()) == 2:
            behind, ahead = counts.split()
            out["unpulled_commits"], out["unpushed_commits"] = int(behind), int(ahead)

    lv, pv = out["main_version"], out["pushed_version"]
    if not remote_ref:
        out["publish_state"] = "local-only"
    elif lv is None:
        out["publish_state"] = "unversioned"
    elif pv is None and out.get("upstream_omits_version"):
        out["publish_state"] = "upstream-unversioned"
    elif pv is None:
        out["publish_state"] = "version-unpushed"
    elif lv == pv:
        out["publish_state"] = ("published" if not out.get("unpushed_commits")
                                else "commits-unpushed")
    elif _semver(pv) > _semver(lv):
        out["publish_state"] = "local-behind-published"
    else:
        out["publish_state"] = "version-unpushed"
    return out


def _semver(v: str) -> tuple:
    parts, key = str(v).replace("-", ".").replace("+", ".").split("."), []
    for part in parts[:4]:
        key.append(int(part) if part.isdigit() else 0)
    return tuple(key)


def build_index() -> dict:
    rows = []
    for entry in load_roster():
        name = entry["name"]
        src = entry.get("source") or {}
        subpath = src.get("path", "") if isinstance(src, dict) else ""
        repo = resolve_checkout(name)
        row = {
            **entry,
            "checkout": str(repo) if repo else None,
            "hosts": detect_hosts(repo, subpath) if repo else {},
            "components": count_components(repo, subpath) if repo else {},
            **(publish_status(repo, subpath) if repo else
               {"publish_state": "no-local-checkout"}),
        }
        row["manifest_matches_main"] = (
            row.get("manifest_version") == row.get("main_version")
            if row.get("manifest_version") and row.get("main_version") else None
        )
        rows.append(row)
    return {
        "_note": ("GENERATED — do not hand-edit. Roster comes from the declared "
                  "marketplace manifest, versions from each plugin's local main, "
                  "publish state from origin/main reading the same file."),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": str(Path(__file__).resolve()),
        "count": len(rows),
        "plugins": rows,
    }


STATE_MARK = {
    "published": "✅ published",
    "commits-unpushed": "⚠️ commits unpushed",
    "version-unpushed": "⚠️ version unpushed",
    "local-behind-published": "❌ local behind published",
    "unversioned": "— unversioned",
    "upstream-unversioned": "— upstream omits version (by design)",
    "local-only": "— local only",
    "no-local-checkout": "❌ no local checkout",
    "no-main": "❌ no main branch",
    "unknown": "? unknown",
}


def render_md(index: dict) -> str:
    L = [
        "<!-- GENERATED — do not hand-edit. Regenerate:",
        "     python3 RossLabs-AI-Toolkit/scripts/plugin_registry.py -->",
        "",
        "# Plugin Index — all hosts",
        "",
        "Every plugin the marketplace declares, which agent hosts can see it, and "
        "whether what people can install is current.",
        "",
        f"- Generated: `{index['generated_at']}`",
        f"- Plugins: **{index['count']}**",
        "",
        "`main` is the version each plugin's local main branch declares. `pushed` "
        "is what origin/main declares, read from the same file. A gap between "
        "them means the catalog advertises something nobody can install yet.",
        "",
        "| Plugin | main | pushed | last push | state | Claude | Codex | AGENTS | skills |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in index["plugins"]:
        h = p.get("hosts", {})
        c = p.get("components", {})
        yes = lambda b: "●" if b else "·"  # noqa: E731
        pushed_at = (p.get("last_pushed_at") or "—")[:10]
        L.append(
            f"| `{p['name']}` | {p.get('main_version') or '—'} | "
            f"{p.get('pushed_version') or '—'} | {pushed_at} | "
            f"{STATE_MARK.get(p.get('publish_state'), p.get('publish_state'))} | "
            f"{yes(h.get('claude-code'))} | {yes(h.get('codex'))} | "
            f"{yes(h.get('agents-standard'))} | {c.get('skills', 0)} |"
        )
    drift = [p for p in index["plugins"] if p.get("manifest_matches_main") is False]
    if drift:
        L += ["", "## Manifest drift", "",
              "The marketplace manifest and the plugin's own main disagree. The "
              "manifest is what people install; main is what exists.", ""]
        for p in drift:
            L.append(f"- `{p['name']}` — manifest `{p.get('manifest_version')}` "
                     f"vs main `{p.get('main_version')}`")
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the written index differs from a fresh scan")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout")
    args = ap.parse_args(argv)

    index = build_index()
    if args.json:
        print(json.dumps(index, indent=2))
        return 0

    md_path, json_path = OUT_DIR / MD_NAME, OUT_DIR / JSON_NAME
    md, blob = render_md(index), json.dumps(index, indent=2, sort_keys=True) + "\n"

    if args.check:
        if not md_path.exists():
            print(f"plugin_registry: {md_path} missing — run without --check",
                  file=sys.stderr)
            return 1
        # generated_at always differs; compare the plugin rows only.
        try:
            old = json.loads(json_path.read_text(encoding="utf-8")).get("plugins")
        except (OSError, json.JSONDecodeError):
            old = None
        if old != index["plugins"]:
            print("plugin_registry: index is STALE — regenerate", file=sys.stderr)
            return 1
        print(f"plugin index up to date ({index['count']} plugins)")
        return 0

    if not OUT_DIR.is_dir():
        print(f"plugin_registry: {OUT_DIR} not found — is build-loop-memory cloned?",
              file=sys.stderr)
        return 2
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(blob, encoding="utf-8")
    print(f"plugin index written: {md_path} ({index['count']} plugins)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
