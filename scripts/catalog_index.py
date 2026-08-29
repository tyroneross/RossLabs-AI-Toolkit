#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 Tyrone Ross, Jr <46267523+tyroneross@users.noreply.github.com>
# SPDX-License-Identifier: Apache-2.0
"""Cross-host catalog of every plugin AND skill on this machine.

WHY THIS EXISTS ALONGSIDE ITS TWO SIBLINGS
------------------------------------------
`repo_registry.py`   answers "what repos are on this machine".
`plugin_registry.py` answers "what plugins does the marketplace declare".
Neither answers "what SKILLS exist, who owns each one, and is it current" —
and skills are the larger population (hundreds of sightings vs 18 plugins).
A marketplace manifest declares plugins; it never enumerates their skills.

ROSTER AUTHORITY, DELIBERATELY SPLIT BY KIND
--------------------------------------------
Plugins: the marketplace manifests are the roster, same rule as
plugin_registry.py — a directory scan makes the catalog depend on whatever
happens to be cloned nearby.

Skills: there is no manifest that enumerates them, so the filesystem IS the
roster. Every SKILL.md sighting is reported, not deduped, and each is labeled
canonical / plugin-cache / unmanaged so duplicate and orphaned copies stay
visible rather than collapsing into one row.

UNMANAGED IS THE POINT
----------------------
A skill whose nearest ancestor has no .git has no repo, no remote, and no
version — nothing can tell you whether it is current. `~/.codex/skills/`
holds 24 of these today. They are invisible to every other index on this
machine; surfacing them is the main reason this script exists.

Output lands in an untracked directory (`~/dev/git-folder/_catalog/`) by
convention: `~/dev/git-folder` is not a git repo, and underscore-prefixed
entries there are the established non-repo idiom (_archive, _reference,
_worktrees, _private-plugins).

Usage:
    python3 scripts/catalog_index.py            # write the catalog + append log
    python3 scripts/catalog_index.py --check     # exit 1 if stale, write nothing
    python3 scripts/catalog_index.py --json      # emit to stdout
    python3 scripts/catalog_index.py --fast      # skip per-file git dates
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
GIT_FOLDER = Path.home() / "dev" / "git-folder"
OUT_DIR = GIT_FOLDER / "_catalog"
MD_NAME = "CATALOG.md"
JSON_NAME = "catalog.json"
LOG_NAME = "log.jsonl"

MANIFESTS = (
    TOOLKIT_ROOT / ".claude-plugin" / "marketplace.json",
    TOOLKIT_ROOT / ".agents" / "plugins" / "marketplace.json",
)

#: Where skills live. `source` is reported verbatim so a row's provenance is
#: readable without re-deriving it from the path.
SKILL_ROOTS = [
    (Path.home() / ".claude" / "skills", "claude-global"),
    (Path.home() / ".codex" / "skills", "codex-global"),
    (Path.home() / ".claude" / "plugins" / "cache", "claude-plugin-cache"),
    (Path.home() / ".codex" / "plugins" / "cache", "codex-plugin-cache"),
    (GIT_FOLDER, "repo"),
]

#: Never walked. node_modules alone is ~10^5 files and holds no authored skill.
PRUNE = {
    "node_modules", ".git", ".next", "dist", "build", "__pycache__",
    ".venv", "venv", ".turbo", "coverage", ".pytest_cache", "_worktrees",
    ".astronomer", ".build-loop",
}

_repo_cache: dict[Path, dict | None] = {}


def _git(args: list[str], cwd: Path, timeout: int = 15) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def find_repo(path: Path) -> Path | None:
    """Nearest ancestor holding .git, or None — which means `unmanaged`."""
    for p in [path, *path.parents]:
        if (p / ".git").exists():
            return p
        if p == p.parent:
            break
    return None


def repo_facts(repo: Path) -> dict:
    """origin URL, browse link, dirty count, unpushed count — cached per repo."""
    if repo in _repo_cache:
        return _repo_cache[repo]
    origin = _git(["config", "--get", "remote.origin.url"], repo)
    link = None
    if origin:
        link = origin.removesuffix(".git")
        if link.startswith("git@github.com:"):
            link = "https://github.com/" + link[len("git@github.com:"):]
    status = _git(["status", "--porcelain"], repo)
    dirty = len([ln for ln in status.splitlines() if ln.strip()]) if status else 0
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo) or "?"
    unpushed = None
    if _git(["rev-parse", "--verify", "--quiet", f"origin/{branch}"], repo):
        cnt = _git(["rev-list", "--count", f"origin/{branch}..HEAD"], repo)
        unpushed = int(cnt) if cnt and cnt.isdigit() else None
    facts = {
        "repo_path": str(repo), "repo_name": repo.name, "origin": origin,
        "github": link, "branch": branch, "dirty": dirty, "unpushed": unpushed,
    }
    _repo_cache[repo] = facts
    return facts


def last_commit_iso(repo: Path, path: Path) -> str | None:
    """Last commit that touched this file. None means never committed."""
    return _git(["log", "-1", "--format=%cI", "--", str(path)], repo) or None


def status_for(facts: dict | None, committed: str | None, fast: bool) -> str:
    """One word a reader can act on.

    Under --fast no per-file git log runs, so `committed is None` carries no
    information. Reporting it as "uncommitted" would label every row with a
    defect it does not have — the first run did exactly that.
    """
    if facts is None:
        return "unmanaged"
    if committed is None and not fast:
        return "uncommitted"
    if facts["unpushed"]:
        return "unpushed"
    if facts["dirty"]:
        return "dirty"
    return "clean"


def classify(source: str, facts: dict | None) -> str:
    """authored = you maintain it. plugin-cache = an installed artifact.

    Cache copies outnumber authored skills roughly 2:1, so a single flat count
    is dominated by files nobody edits. The split is what makes the number
    actionable.
    """
    if "plugin-cache" in source:
        # Checked before the repo test on purpose. Codex's cache holds no .git,
        # so a repo-first order mislabels ~470 downloaded copies as "unmanaged"
        # and buries the ~50 hand-installed skills that genuinely are.
        return "plugin-cache"
    if facts is None:
        return "unmanaged"
    return "authored"


def _skill_dirs(root: Path):
    """Yield every directory under root that holds a SKILL.md.

    Top-level symlinked entries are resolved explicitly. os.walk(followlinks=
    False) skips them, and three of `~/.codex/skills/` are symlinks into their
    canonical repo — exactly the rows whose provenance matters most.
    """
    seen: set[Path] = set()
    try:
        children = sorted(root.iterdir())
    except OSError:
        children = []
    for child in children:
        if child.is_symlink() and child.is_dir():
            real = child.resolve()
            if (real / "SKILL.md").is_file() and real not in seen:
                seen.add(real)
                yield real
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in PRUNE and not d.startswith(".")]
        if OUT_DIR.name in Path(dirpath).parts:
            dirnames[:] = []
            continue
        if "SKILL.md" in filenames:
            d = Path(dirpath)
            if d not in seen:
                seen.add(d)
                yield d


def walk_skills(root: Path, source: str, fast: bool) -> list[dict]:
    out: list[dict] = []
    if not root.is_dir():
        return out
    for skill_dir in _skill_dirs(root):
        f = skill_dir / "SKILL.md"
        repo = find_repo(f)
        facts = repo_facts(repo) if repo else None
        cls = classify(source, facts)
        committed = None
        if repo and not fast:
            committed = last_commit_iso(repo, f)
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            mtime = None
        out.append({
            "kind": "skill",
            "name": skill_dir.name,
            "class": cls,
            "source": source,
            "path": str(f),
            "repo": facts["repo_name"] if facts else None,
            "github": facts["github"] if facts else None,
            "branch": facts["branch"] if facts else None,
            "last_commit": committed,
            "local_mtime": mtime,
            # A cache copy with no .git is not "unmanaged" in the sense the
            # status column means — it is a downloaded artifact behaving
            # normally. Reusing one word for both made the two summary tables
            # disagree by 474 rows.
            "status": "cached" if (cls == "plugin-cache" and facts is None)
                      else status_for(facts, committed, fast),
        })
    return out


def declared_plugins() -> list[dict]:
    """Roster from the manifests — never a directory scan. See module docstring."""
    seen: dict[str, dict] = {}
    for man in MANIFESTS:
        if not man.is_file():
            continue
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        host = "codex" if ".agents" in man.parts else "claude"
        for e in data.get("plugins", []):
            name = e.get("name")
            if not name:
                continue
            rec = seen.setdefault(name, {"name": name, "hosts": []})
            rec["hosts"].append(host)
            rec.setdefault("description", e.get("description"))
            rec.setdefault("repository", e.get("repository"))
    return sorted(seen.values(), key=lambda r: r["name"])


def resolve_checkout(name: str) -> Path | None:
    p = TOOLKIT_ROOT / "plugins" / name
    if p.exists():
        return p.resolve()
    sib = GIT_FOLDER / name
    return sib.resolve() if (sib / ".git").exists() else None


def plugin_rows(fast: bool) -> list[dict]:
    rows = []
    for d in declared_plugins():
        checkout = resolve_checkout(d["name"])
        facts = repo_facts(checkout) if checkout else None
        version = None
        if checkout:
            for cand in (".claude-plugin/plugin.json", "plugin.json", "package.json"):
                fp = checkout / cand
                if fp.is_file():
                    try:
                        version = json.loads(fp.read_text(encoding="utf-8")).get("version")
                    except (OSError, json.JSONDecodeError):
                        version = None
                    if version:
                        break
        committed = None
        if checkout and not fast:
            committed = _git(["log", "-1", "--format=%cI"], checkout)
        skill_count = len(list((checkout).glob("skills/**/SKILL.md"))) if checkout else 0
        rows.append({
            "kind": "plugin",
            "name": d["name"],
            "hosts": d["hosts"],
            "path": str(checkout) if checkout else None,
            "repo": facts["repo_name"] if facts else None,
            "github": facts["github"] if facts else d.get("repository"),
            "branch": facts["branch"] if facts else None,
            "version": version,
            "last_commit": committed,
            "skills_in_checkout": skill_count,
            "status": status_for(facts, committed, fast) if facts else "not-cloned",
        })
    return rows


def build(fast: bool) -> dict:
    plugins = plugin_rows(fast)
    skills: list[dict] = []
    for root, source in SKILL_ROOTS:
        skills.extend(walk_skills(root, source, fast))
    skills.sort(key=lambda r: (r["source"], r["name"]))
    by_status: dict[str, int] = {}
    for s in skills:
        by_status[s["status"]] = by_status.get(s["status"], 0) + 1
    by_source: dict[str, int] = {}
    for s in skills:
        by_source[s["source"]] = by_source.get(s["source"], 0) + 1
    by_class: dict[str, int] = {}
    for s in skills:
        by_class[s["class"]] = by_class.get(s["class"], 0) + 1
    return {
        "_note": "GENERATED — do not hand-edit. Regenerate: "
                 "python3 RossLabs-AI-Toolkit/scripts/catalog_index.py",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": str(Path(__file__).resolve()),
        "counts": {
            "plugins": len(plugins),
            "skills": len(skills),
            "skills_by_class": dict(sorted(by_class.items())),
            "skills_by_status": dict(sorted(by_status.items())),
            "skills_by_source": dict(sorted(by_source.items())),
        },
        "plugins": plugins,
        "skills": skills,
    }


def render_md(cat: dict) -> str:
    L = []
    A = L.append
    A("<!-- GENERATED — do not hand-edit. Regenerate:")
    A("     python3 RossLabs-AI-Toolkit/scripts/catalog_index.py -->")
    A("")
    A("# Catalog — every plugin and skill on this machine")
    A("")
    A("Plugin roster comes from the marketplace manifests. Skill roster is the "
      "filesystem, because no manifest enumerates skills. Every sighting is "
      "listed; duplicates are not collapsed.")
    A("")
    A(f"- Generated: `{cat['generated_at']}`")
    A(f"- Plugins: **{cat['counts']['plugins']}** · Skills: **{cat['counts']['skills']}**")
    A("")
    A("`unmanaged` means the skill has no owning git repo — no remote, no "
      "version, nothing that can tell you whether it is current.")
    A("")
    A("## Skills by class")
    A("")
    A("`authored` are skills you maintain. `plugin-cache` are installed copies "
      "of someone's published plugin — derived artifacts, listed only as counts. "
      "`unmanaged` have no owning repo at all.")
    A("")
    A("| class | count |")
    A("|---|---|")
    for k, v in cat["counts"]["skills_by_class"].items():
        A(f"| `{k}` | {v} |")
    A("")
    A("## Skills by status")
    A("")
    A("| status | count |")
    A("|---|---|")
    for k, v in cat["counts"]["skills_by_status"].items():
        A(f"| `{k}` | {v} |")
    A("")
    A("## Skills by source")
    A("")
    A("| source | count |")
    A("|---|---|")
    for k, v in cat["counts"]["skills_by_source"].items():
        A(f"| `{k}` | {v} |")
    A("")
    A("## Plugins")
    A("")
    A("Versions here are read from the **working tree** — what is on disk right "
      "now. `PLUGINS.md` reads each plugin's **main** instead. A disagreement "
      "between the two is uncommitted local work, not an error.")
    A("")
    A("| Plugin | version | hosts | last local commit | status | skills | GitHub |")
    A("|---|---|---|---|---|---|---|")
    for p in cat["plugins"]:
        lc = (p["last_commit"] or "—")[:10]
        gh = f"[link]({p['github']})" if p["github"] else "—"
        A(f"| `{p['name']}` | {p['version'] or '—'} | {'/'.join(p['hosts'])} | "
          f"{lc} | {p['status']} | {p['skills_in_checkout']} | {gh} |")
    A("")
    A("## Skills — authored and unmanaged")
    A("")
    A("Installed plugin-cache copies are omitted from this table by design: "
      "they are re-downloaded artifacts, not things you maintain. Full rows "
      "for every sighting live in `catalog.json`.")
    A("")
    A("| Skill | class | source | repo | last local commit | status | GitHub |")
    A("|---|---|---|---|---|---|---|")
    for s in [r for r in cat["skills"] if r["class"] != "plugin-cache"]:
        lc = (s["last_commit"] or s["local_mtime"] or "—")[:10]
        gh = f"[link]({s['github']})" if s["github"] else "—"
        A(f"| `{s['name']}` | {s['class']} | {s['source']} | {s['repo'] or '—'} "
          f"| {lc} | {s['status']} | {gh} |")
    A("")
    return "\n".join(L) + "\n"


def append_log(cat: dict, prev: dict | None) -> dict:
    """One line per run. Deltas are the point — a flat count proves nothing."""
    def names(d, kind):
        return {r["path"] or r["name"] for r in (d.get(kind) or [])} if d else set()
    entry = {
        "at": cat["generated_at"],
        "plugins": cat["counts"]["plugins"],
        "skills": cat["counts"]["skills"],
        "skills_by_class": cat["counts"]["skills_by_class"],
        "skills_by_status": cat["counts"]["skills_by_status"],
    }
    if prev:
        entry["added_skills"] = sorted(names(cat, "skills") - names(prev, "skills"))[:50]
        entry["removed_skills"] = sorted(names(prev, "skills") - names(cat, "skills"))[:50]
        entry["delta_skills"] = cat["counts"]["skills"] - (prev.get("counts", {}).get("skills") or 0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / LOG_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if stale; write nothing")
    ap.add_argument("--json", action="store_true", help="emit catalog to stdout")
    ap.add_argument("--fast", action="store_true", help="skip per-file git dates")
    a = ap.parse_args()

    cat = build(a.fast)

    if a.json:
        print(json.dumps(cat, indent=2))
        return 0

    json_path = OUT_DIR / JSON_NAME
    prev = None
    if json_path.is_file():
        try:
            prev = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prev = None

    if a.check:
        if prev is None:
            print("catalog missing — run without --check", file=sys.stderr)
            return 1
        same = (prev.get("plugins") == cat["plugins"]
                and prev.get("skills") == cat["skills"])
        if not same:
            print("catalog is stale — rerun catalog_index.py", file=sys.stderr)
            return 1
        print("catalog is current.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / MD_NAME).write_text(render_md(cat), encoding="utf-8")
    entry = append_log(cat, prev)
    print(f"catalog: {cat['counts']['plugins']} plugins · "
          f"{cat['counts']['skills']} skills → {OUT_DIR}")
    if "delta_skills" in entry:
        print(f"  delta since last run: {entry['delta_skills']:+d} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
