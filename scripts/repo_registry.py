#!/usr/bin/env python3
"""
repo_registry.py — generate a local app/repo registry by scanning ~/dev/git-folder.

Dependency-free (Python stdlib only). Walks the top-level entries of a root dir
and, for each git repository, records: name, absolute path, current branch, last
commit date (ISO) + subject, dirty/clean (porcelain count), origin remote URL,
and a version if one can be found (`.claude-plugin/plugin.json` →
`plugin/.claude-plugin/plugin.json` → `package.json`, first hit). Git worktrees
are distinguished from full repos when cheaply detectable (`.git` is a file, not
a directory). Non-repo files/dirs are skipped silently.

PRIVACY: the generated registry inventories private local projects and absolute
machine paths. It MUST NOT be committed to any public repo. Output goes to the
local private memory repo (build-loop-memory/registry/). See marketplace-sync.py
--act for the integrated generation + private-only commit/push gate.

Standalone usage:
  python3 scripts/repo_registry.py              # write REGISTRY.md + registry.json
  python3 scripts/repo_registry.py --json       # print machine JSON to stdout (no write)
  python3 scripts/repo_registry.py --root DIR    # scan a different root
  python3 scripts/repo_registry.py --out-dir DIR # write to a different output dir

Exit codes:
  0  scan completed (registry generated / printed)
  1  scan could not run (e.g. root dir missing, git unavailable when required)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Default scan root and output destination. Both are resolved at call time so
# tests can override via arguments without importing real machine state.
DEFAULT_ROOT = Path.home() / "dev" / "git-folder"
DEFAULT_OUT_DIR = Path.home() / "dev" / "git-folder" / "build-loop-memory" / "registry"

# Absolute fallbacks for `git` when PATH is minimal (e.g. under launchd, which
# inherits /usr/bin:/bin and lacks Homebrew's bin dir). Mirrors marketplace-sync's
# gh_bin() pattern so a bare `git` invocation never crashes the scan.
_GIT_FALLBACKS = ("/usr/bin/git", "/opt/homebrew/bin/git", "/usr/local/bin/git")

GENERATED_HEADER_NOTE = "generated — do not hand-edit"


def git_bin() -> str | None:
    """Resolve the `git` executable robustly. Returns an absolute path or None.

    Order: PATH (shutil.which) → known system/Homebrew locations. Returns None
    when git is genuinely unavailable so callers can degrade rather than crash.
    """
    found = shutil.which("git")
    if found:
        return found
    for cand in _GIT_FALLBACKS:
        if os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    return None


# ---------------------------------------------------------------------------
# Pure parsing / probing helpers (unit-testable, no I/O beyond reading the path)
# ---------------------------------------------------------------------------

def parse_version_from_json_text(text: str) -> str | None:
    """Extract the top-level `version` string from JSON text. None on any error
    (bad JSON, missing field, non-string version)."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    v = data.get("version")
    return v if isinstance(v, str) and v.strip() else None


# Version probe order: a plugin manifest wins over package.json so a Claude
# plugin's real version is reported even when a package.json also exists.
_VERSION_CANDIDATES = (
    ".claude-plugin/plugin.json",
    "plugin/.claude-plugin/plugin.json",
    "package.json",
)


def probe_version(repo_path: Path) -> tuple[str | None, str | None]:
    """First-hit version probe for a repo. Returns (version, source_relpath).

    Checks, in order: .claude-plugin/plugin.json, plugin/.claude-plugin/plugin.json,
    package.json. Returns the first file that exists AND yields a version. If a
    candidate file exists but has no usable version, the probe continues to the
    next candidate (a package.json without a version shouldn't mask a plugin.json).
    Returns (None, None) when nothing yields a version.
    """
    for rel in _VERSION_CANDIDATES:
        f = repo_path / rel
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        v = parse_version_from_json_text(text)
        if v is not None:
            return v, rel
    return None, None


def read_version_at_ref(repo_path: Path, ref: str, rel: str, git: str) -> str | None:
    """Version from ONE specific file at ONE ref. No candidate fallback.

    Comparing refs requires reading the SAME file at both. Probing candidates
    independently per ref compares apples to oranges: spectra's main declares
    0.3.2 in .claude-plugin/plugin.json while origin/main has no such file, so a
    per-ref probe fell through to package.json and reported a phantom 0.4.0
    "newer published version" that did not exist.
    """
    try:
        out = subprocess.run(
            [git, "-C", str(repo_path), "show", f"{ref}:{rel}"],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return parse_version_from_json_text(out.stdout)


def probe_version_at_ref(repo_path: Path, ref: str, git: str) -> tuple[str | None, str | None]:
    """Version as declared AT A GIT REF, not in the working tree.

    The working tree is whatever branch happens to be checked out, possibly
    dirty, possibly a feature branch mid-refactor. A published catalog must not
    depend on that: it reports what `main` declares. Returns (None, None) when
    the ref or the file is absent — callers fall back to the working tree.
    """
    for rel in _VERSION_CANDIDATES:
        try:
            out = subprocess.run(
                [git, "-C", str(repo_path), "show", f"{ref}:{rel}"],
                capture_output=True, text=True, timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None, None
        if out.returncode != 0:
            continue
        v = parse_version_from_json_text(out.stdout)
        if v is not None:
            return v, rel
    return None, None


def push_status(repo_path: Path, git: str) -> dict:
    """What is actually PUBLISHED versus what exists locally.

    A version in the working tree tells you nothing about what anyone else can
    install. These fields answer the question a catalog actually needs: what
    does the pushed branch declare, when did it last move, and how far has
    local run ahead of it.
    """
    def g(args: list[str]) -> str | None:
        return _git(args, repo_path, git)

    main_ref = None
    for cand in ("main", "master"):
        if g(["rev-parse", "--verify", "--quiet", cand]):
            main_ref = cand
            break

    remote_ref = None
    if main_ref and g(["rev-parse", "--verify", "--quiet", f"origin/{main_ref}"]):
        remote_ref = f"origin/{main_ref}"

    out: dict = {
        "main_ref": main_ref,
        "main_version": None,
        "pushed_version": None,
        "last_pushed_at": None,
        "last_pushed_subject": None,
        "unpushed_commits": None,
        "unpulled_commits": None,
        "publish_state": "unknown",
    }
    if main_ref:
        v, src = probe_version_at_ref(repo_path, main_ref, git)
        out["main_version"] = v
        out["main_version_source"] = src
    if remote_ref:
        # Read the SAME file main used, so the two are comparable. Falling back
        # to a candidate probe here would compare different files across refs.
        src = out.get("main_version_source")
        out["pushed_version"] = (
            read_version_at_ref(repo_path, remote_ref, src, git) if src else None
        )
        out["pushed_version_source"] = src
        last = g(["log", "-1", "--format=%cI%x09%s", remote_ref])
        if last and "\t" in last:
            out["last_pushed_at"], out["last_pushed_subject"] = last.split("\t", 1)
        counts = g(["rev-list", "--left-right", "--count", f"{remote_ref}...{main_ref}"])
        if counts and len(counts.split()) == 2:
            behind, ahead = counts.split()
            out["unpulled_commits"] = int(behind)
            out["unpushed_commits"] = int(ahead)

    # publish_state answers "is what people can install current?"
    lv, pv = out["main_version"], out["pushed_version"]
    if remote_ref is None:
        out["publish_state"] = "local-only"
    elif lv is None and pv is None:
        out["publish_state"] = "unversioned"
    elif lv == pv and not out.get("unpushed_commits"):
        out["publish_state"] = "published"
    elif lv == pv:
        out["publish_state"] = "commits-unpushed"
    elif lv is not None and pv is not None and _semver_key(pv) > _semver_key(lv):
        # main is BEHIND what is published. Either someone released without
        # merging back, or local main was reset. Never silently pick one.
        out["publish_state"] = "local-behind-published"
    else:
        out["publish_state"] = "version-unpushed"
    return out


def _semver_key(v: str) -> tuple:
    """Loose semver sort key; non-numeric parts sort as 0 rather than raising."""
    parts = re.split(r"[.\-+]", str(v))
    key = []
    for part in parts[:4]:
        key.append(int(part) if part.isdigit() else 0)
    return tuple(key)


def is_git_repo(entry: Path) -> bool:
    """True if `entry` is a git repo OR a git worktree. A full repo has a `.git`
    directory; a worktree (or submodule) has a `.git` FILE that points elsewhere."""
    dotgit = entry / ".git"
    return dotgit.is_dir() or dotgit.is_file()


def is_worktree(entry: Path) -> bool:
    """True if `entry` is a git worktree (or submodule) rather than a full repo.
    Cheap detection: a worktree's `.git` is a regular file (a gitdir pointer),
    a full repo's `.git` is a directory."""
    return (entry / ".git").is_file()


def render_json(rows: list[dict], generated_at: str, generator_path: str,
                root: str) -> str:
    """Render the machine-readable registry JSON (stable key order, trailing nl)."""
    payload = {
        "_note": GENERATED_HEADER_NOTE,
        "generated_at": generated_at,
        "generator": generator_path,
        "root": root,
        "count": len(rows),
        "repos": rows,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _md_escape(s: str) -> str:
    """Escape pipe and newline so a field can't break the markdown table."""
    return s.replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def render_markdown(rows: list[dict], generated_at: str, generator_path: str,
                    root: str) -> str:
    """Render the human-readable REGISTRY.md (table sorted by last-commit desc).

    `rows` is assumed already sorted by the caller; this function does not
    re-sort so the JSON and MD share one ordering decision.
    """
    lines: list[str] = []
    lines.append("# Local Repo Registry")
    lines.append("")
    lines.append(f"> {GENERATED_HEADER_NOTE} — regenerated by the marketplace-sync `--act` cron")
    lines.append(f"> and on demand via `{generator_path}`.")
    lines.append("")
    lines.append(f"- Generated: `{generated_at}`")
    lines.append(f"- Root scanned: `{root}`")
    lines.append(f"- Repos found: **{len(rows)}**")
    lines.append("")
    lines.append("| Repo | Branch | Last commit | Subject | State | Version | Kind | Origin |")
    lines.append("|------|--------|-------------|---------|-------|---------|------|--------|")
    for r in rows:
        state = "dirty" if r.get("dirty_count", 0) else "clean"
        if r.get("dirty_count", 0):
            state = f"dirty ({r['dirty_count']})"
        version = r.get("version") or "—"
        origin = r.get("origin") or "—"
        kind = "worktree" if r.get("is_worktree") else "repo"
        subject = _md_escape(r.get("last_commit_subject") or "")
        if len(subject) > 80:
            subject = subject[:77] + "…"
        lines.append(
            f"| {_md_escape(r.get('name', ''))} "
            f"| {_md_escape(r.get('branch') or '—')} "
            f"| {_md_escape(r.get('last_commit_date') or '—')} "
            f"| {subject} "
            f"| {state} "
            f"| {_md_escape(version)} "
            f"| {kind} "
            f"| {_md_escape(origin)} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# I/O shell — git invocations + filesystem walk
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: Path, git: str, timeout: int = 20) -> str | None:
    """Run a git command in `cwd`, returning stripped stdout, or None on failure.
    Never raises — a single bad repo must not abort the whole scan."""
    try:
        r = subprocess.run(
            [git, *args], cwd=str(cwd),
            capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def scan_one_repo(entry: Path, git: str) -> dict:
    """Collect registry fields for a single repo dir. Best-effort: any field that
    can't be resolved is left None / 0 rather than failing the row."""
    # Branch (may be detached → 'HEAD'); fall back to short SHA when detached.
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], entry, git)
    if branch == "HEAD":
        sha = _git(["rev-parse", "--short", "HEAD"], entry, git)
        branch = f"(detached {sha})" if sha else "(detached)"

    # Last commit: strict-ISO date + subject in one call, tab-separated.
    last = _git(["log", "-1", "--format=%cI%x09%s"], entry, git)
    last_date: str | None = None
    last_subject: str | None = None
    if last and "\t" in last:
        last_date, last_subject = last.split("\t", 1)
    elif last:
        last_date = last

    # Dirty count = number of porcelain lines (0 == clean).
    porcelain = _git(["status", "--porcelain"], entry, git)
    dirty_count = len([ln for ln in porcelain.splitlines() if ln.strip()]) if porcelain else 0

    origin = _git(["config", "--get", "remote.origin.url"], entry, git)

    version, version_source = probe_version(entry)

    # What main declares and what is actually published. The working-tree
    # version above is kept as `worktree_version` because it is what a local
    # dev sees, but `version` now reports main -- a catalog must not publish a
    # number that only exists on someone's feature branch.
    pub = push_status(entry, git)
    worktree_version, worktree_source = version, version_source
    if pub.get("main_version"):
        version = pub["main_version"]
        version_source = pub.get("main_version_source") or version_source

    return {
        "name": entry.name,
        "path": str(entry),
        "branch": branch,
        "last_commit_date": last_date,
        "last_commit_subject": last_subject,
        "dirty_count": dirty_count,
        "origin": origin,
        "version": version,
        "version_source": version_source,
        "worktree_version": worktree_version,
        "worktree_version_source": worktree_source,
        "is_worktree": is_worktree(entry),
        **pub,
    }


def _sort_key(row: dict):
    """Sort by last-commit date descending. Rows without a date sort last."""
    d = row.get("last_commit_date")
    # ISO strings sort lexicographically in the right order; empty → sorts last
    # under reverse=True by using a sentinel that is lexicographically smallest.
    return (d is not None, d or "")


def scan_all(root: Path, git: str) -> list[dict]:
    """Scan top-level entries of `root`; return rows for every git repo/worktree,
    sorted by last-commit date descending. Non-repo entries are skipped silently."""
    rows: list[dict] = []
    try:
        entries = sorted(root.iterdir())
    except (OSError, FileNotFoundError):
        return rows
    for entry in entries:
        # Only directories can be repos; skip files (and broken symlinks) silently.
        if not entry.is_dir():
            continue
        if not is_git_repo(entry):
            continue
        rows.append(scan_one_repo(entry, git))
    rows.sort(key=_sort_key, reverse=True)
    return rows


def write_outputs(rows: list[dict], out_dir: Path, generated_at: str,
                  generator_path: str, root: str) -> tuple[Path, Path]:
    """Write REGISTRY.md + registry.json to out_dir. Returns the two paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "REGISTRY.md"
    json_path = out_dir / "registry.json"
    md_path.write_text(
        render_markdown(rows, generated_at, generator_path, root), encoding="utf-8"
    )
    json_path.write_text(
        render_json(rows, generated_at, generator_path, root), encoding="utf-8"
    )
    return md_path, json_path


def generate(root: Path = DEFAULT_ROOT, out_dir: Path = DEFAULT_OUT_DIR,
             write: bool = True) -> dict:
    """Top-level entry: scan `root`, optionally write outputs. Returns a summary
    dict {root, out_dir, count, rows, generated_at, md_path, json_path}.

    Raises RuntimeError only when git is genuinely unavailable (callers in the
    cron wrap this so a scan failure never fails the catalog sync)."""
    git = git_bin()
    if git is None:
        raise RuntimeError("git executable not found — cannot scan repos")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    generator_path = str(Path(__file__).resolve())
    rows = scan_all(root, git)
    summary = {
        "root": str(root),
        "out_dir": str(out_dir),
        "count": len(rows),
        "rows": rows,
        "generated_at": generated_at,
        "md_path": None,
        "json_path": None,
    }
    if write:
        md_path, json_path = write_outputs(
            rows, out_dir, generated_at, generator_path, str(root)
        )
        summary["md_path"] = str(md_path)
        summary["json_path"] = str(json_path)
    return summary


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Generate a local app/repo registry by scanning ~/dev/git-folder."
    )
    ap.add_argument("--root", default=str(DEFAULT_ROOT),
                    help=f"Root dir to scan (default: {DEFAULT_ROOT})")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                    help=f"Output dir for REGISTRY.md/registry.json (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--json", action="store_true",
                    help="Print machine JSON to stdout instead of writing files.")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"repo_registry: root not found: {root}", file=sys.stderr)
        return 1

    try:
        if args.json:
            summary = generate(root=root, out_dir=Path(args.out_dir).expanduser(),
                               write=False)
            print(render_json(
                summary["rows"], summary["generated_at"],
                str(Path(__file__).resolve()), summary["root"],
            ), end="")
            return 0
        summary = generate(root=root, out_dir=Path(args.out_dir).expanduser(),
                           write=True)
    except RuntimeError as e:
        print(f"repo_registry: {e}", file=sys.stderr)
        return 1

    print(f"repo_registry: scanned {summary['count']} repos under {summary['root']}")
    print(f"  wrote {summary['md_path']}")
    print(f"  wrote {summary['json_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
