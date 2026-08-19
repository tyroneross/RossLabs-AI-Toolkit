# SPDX-FileCopyrightText: 2025-2026 Tyrone Ross, Jr <46267523+tyroneross@users.noreply.github.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for the cross-host plugin index.

Each test here pins a bug found while building it. Every one produced a
confident, wrong number first — which is the point of writing them down.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "plugin_registry", Path(__file__).resolve().parents[1] / "scripts" / "plugin_registry.py")
pr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pr)


def _repo(tmp_path: Path, name: str = "r") -> Path:
    p = tmp_path / name
    p.mkdir()
    run = lambda *a: subprocess.run(["git", "-C", str(p), *a], check=True,  # noqa: E731
                                    capture_output=True)
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@e"); run("config", "user.name", "t")
    return p


def _commit(p: Path, msg: str = "c") -> None:
    subprocess.run(["git", "-C", str(p), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(p), "commit", "-qm", msg], check=True,
                   capture_output=True)


def _manifest(p: Path, version: str | None) -> None:
    d = p / ".claude-plugin"; d.mkdir(exist_ok=True)
    body = {"name": "x"} | ({"version": version} if version else {})
    (d / "plugin.json").write_text(json.dumps(body), encoding="utf-8")


# --- version comes from main, not the working tree -------------------------
def test_version_reads_main_not_the_working_tree(tmp_path):
    """A catalog must not publish a number that exists only on a branch."""
    p = _repo(tmp_path)
    _manifest(p, "1.0.0"); _commit(p)
    subprocess.run(["git", "-C", str(p), "checkout", "-qb", "wip"], check=True,
                   capture_output=True)
    _manifest(p, "9.9.9"); _commit(p, "wip bump")
    assert pr.publish_status(p)["main_version"] == "1.0.0"


# --- the same file must be read at both refs -------------------------------
def test_pushed_version_reads_the_same_file_as_main(tmp_path):
    """Probing candidates per-ref compares different files.

    Regression: spectra's main declared 0.3.2 in .claude-plugin/plugin.json
    while origin/main had no such file, so a per-ref probe fell through to
    package.json and reported a phantom published 0.4.0.
    """
    p = _repo(tmp_path)
    (p / "package.json").write_text(json.dumps({"version": "0.4.0"}), encoding="utf-8")
    _commit(p, "package only")
    subprocess.run(["git", "-C", str(p), "update-ref", "refs/remotes/origin/main",
                    "HEAD"], check=True, capture_output=True)
    _manifest(p, "0.3.2"); _commit(p, "add plugin manifest")
    st = pr.publish_status(p)
    assert st["main_version"] == "0.3.2"
    assert st["version_source"] == ".claude-plugin/plugin.json"
    # origin has no plugin.json -> must NOT report package.json's 0.4.0
    assert st["pushed_version"] != "0.4.0"


# --- only release-shaped tags count as versions ----------------------------
@pytest.mark.parametrize("tag,ok", [
    ("v1.2.3", True), ("1.2.3", True), ("plugin-v0.3.1", True), ("v0.9", True),
    ("archive/pre-closeout-2026-07-14/main-before-maintenance", False),
    ("backup-before-rewrite", False), ("latest", False),
])
def test_release_tag_shape(tag, ok):
    """Regression: `git describe --abbrev=0` returned navgator's archive tag and
    it was reported as the published version."""
    assert bool(pr.RELEASE_TAG.fullmatch(tag)) is ok


# --- roster comes from the manifest, never a directory scan ----------------
def test_roster_is_manifest_driven_not_a_directory_scan():
    """A scan of ~/dev/git-folder makes the published catalog depend on whatever
    is cloned next to it — which silently dropped two shipped plugins."""
    src = (Path(__file__).resolve().parents[1] / "scripts" / "plugin_registry.py"
           ).read_text(encoding="utf-8")
    body = src.split("def load_roster")[1].split("\ndef ")[0]
    assert "MANIFESTS" in body
    assert "glob" not in body and "iterdir" not in body


def test_upstream_omitting_a_version_is_not_called_unpushed(tmp_path):
    """bookmark deliberately omits `version` upstream and tracks it by tag.
    Conflating that with 'unpushed' labelled 16 of 18 plugins wrongly."""
    p = _repo(tmp_path)
    _manifest(p, None); _commit(p, "no version by design")
    subprocess.run(["git", "-C", str(p), "update-ref", "refs/remotes/origin/main",
                    "HEAD"], check=True, capture_output=True)
    _manifest(p, "1.0.0"); _commit(p, "local adds version")
    st = pr.publish_status(p)
    assert st["upstream_omits_version"] is True
    assert st["publish_state"] != "version-unpushed"


def test_live_index_builds_and_flags_inversions():
    """The real index must build, and local-behind-published must be reachable
    — the state that answers 'is main at or above what shipped'."""
    idx = pr.build_index()
    assert idx["count"] > 0
    assert all("publish_state" in p for p in idx["plugins"])
    assert pr.STATE_MARK.get("local-behind-published")
