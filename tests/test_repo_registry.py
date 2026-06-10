#!/usr/bin/env python3
"""
Tests for repo_registry.py — the local app/repo registry scanner.

Run:  python3 -m pytest tests/test_repo_registry.py -v
  or: python3 tests/test_repo_registry.py

Pure functions are tested directly with synthetic inputs. The git-touching shell
is exercised against a tiny real git repo built in a tempdir (no live-machine
state, no network), so parsing/probing/rendering all run end-to-end without
depending on ~/dev/git-folder.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import repo_registry as rr  # noqa: E402


# ---------------------------------------------------------------------------
# Pure: version parsing
# ---------------------------------------------------------------------------

class TestVersionParsing(unittest.TestCase):

    def test_valid_version(self):
        self.assertEqual(rr.parse_version_from_json_text('{"version": "1.2.3"}'), "1.2.3")

    def test_version_with_other_fields(self):
        text = '{"name": "x", "version": "0.1.0", "deps": {}}'
        self.assertEqual(rr.parse_version_from_json_text(text), "0.1.0")

    def test_missing_version(self):
        self.assertIsNone(rr.parse_version_from_json_text('{"name": "x"}'))

    def test_non_string_version(self):
        self.assertIsNone(rr.parse_version_from_json_text('{"version": 12}'))

    def test_empty_version(self):
        self.assertIsNone(rr.parse_version_from_json_text('{"version": "  "}'))

    def test_bad_json(self):
        self.assertIsNone(rr.parse_version_from_json_text("{not json"))

    def test_non_object_json(self):
        self.assertIsNone(rr.parse_version_from_json_text('["version", "1.0"]'))


# ---------------------------------------------------------------------------
# Pure: version probe order (first-hit precedence)
# ---------------------------------------------------------------------------

class TestProbeVersion(unittest.TestCase):

    def _mk(self, files: dict[str, str]) -> Path:
        d = Path(tempfile.mkdtemp())
        for rel, content in files.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        return d

    def test_claude_plugin_wins(self):
        d = self._mk({
            ".claude-plugin/plugin.json": '{"version": "9.9.9"}',
            "package.json": '{"version": "0.0.1"}',
        })
        v, src = rr.probe_version(d)
        self.assertEqual(v, "9.9.9")
        self.assertEqual(src, ".claude-plugin/plugin.json")

    def test_nested_plugin_second(self):
        d = self._mk({
            "plugin/.claude-plugin/plugin.json": '{"version": "2.0.0"}',
            "package.json": '{"version": "0.0.1"}',
        })
        v, src = rr.probe_version(d)
        self.assertEqual(v, "2.0.0")
        self.assertEqual(src, "plugin/.claude-plugin/plugin.json")

    def test_package_json_fallback(self):
        d = self._mk({"package.json": '{"version": "3.4.5"}'})
        v, src = rr.probe_version(d)
        self.assertEqual(v, "3.4.5")
        self.assertEqual(src, "package.json")

    def test_versionless_candidate_skipped(self):
        # A package.json without a version must not mask a later real one — but
        # here only a versionless package.json exists → (None, None).
        d = self._mk({"package.json": '{"name": "x"}'})
        v, src = rr.probe_version(d)
        self.assertIsNone(v)
        self.assertIsNone(src)

    def test_versionless_plugin_falls_through_to_package(self):
        d = self._mk({
            ".claude-plugin/plugin.json": '{"name": "x"}',  # no version
            "package.json": '{"version": "7.0.0"}',
        })
        v, src = rr.probe_version(d)
        self.assertEqual(v, "7.0.0")
        self.assertEqual(src, "package.json")

    def test_no_version_files(self):
        d = self._mk({"README.md": "hi"})
        self.assertEqual(rr.probe_version(d), (None, None))


# ---------------------------------------------------------------------------
# Pure: markdown + json rendering
# ---------------------------------------------------------------------------

class TestRendering(unittest.TestCase):

    ROWS = [
        {
            "name": "alpha", "path": "/p/alpha", "branch": "main",
            "last_commit_date": "2026-06-10T10:00:00-07:00",
            "last_commit_subject": "feat: thing",
            "dirty_count": 0, "origin": "https://github.com/u/alpha.git",
            "version": "1.0.0", "version_source": "package.json",
            "is_worktree": False,
        },
        {
            "name": "beta", "path": "/p/beta", "branch": "dev",
            "last_commit_date": "2026-06-09T09:00:00-07:00",
            "last_commit_subject": "fix: pipe | in subject\nand newline",
            "dirty_count": 3, "origin": None,
            "version": None, "version_source": None,
            "is_worktree": True,
        },
    ]

    def test_markdown_header_and_note(self):
        md = rr.render_markdown(self.ROWS, "2026-06-10T17:00:00Z", "/g/repo_registry.py", "/root")
        self.assertIn("# Local Repo Registry", md)
        self.assertIn(rr.GENERATED_HEADER_NOTE, md)
        self.assertIn("Repos found: **2**", md)
        self.assertIn("/root", md)

    def test_markdown_rows(self):
        md = rr.render_markdown(self.ROWS, "t", "/g", "/root")
        self.assertIn("| alpha |", md)
        self.assertIn("1.0.0", md)
        self.assertIn("clean", md)
        self.assertIn("dirty (3)", md)
        self.assertIn("worktree", md)
        # The em-dash placeholder for a missing origin/version.
        self.assertIn("| — |", md)

    def test_markdown_escapes_pipe_and_newline(self):
        md = rr.render_markdown(self.ROWS, "t", "/g", "/root")
        # The beta subject's literal pipe must be escaped so it can't split cells.
        self.assertIn("pipe \\| in subject", md)
        self.assertNotIn("pipe | in subject\nand", md)

    def test_json_shape(self):
        out = rr.render_json(self.ROWS, "2026-06-10T17:00:00Z", "/g/x.py", "/root")
        data = json.loads(out)
        self.assertEqual(data["_note"], rr.GENERATED_HEADER_NOTE)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["generated_at"], "2026-06-10T17:00:00Z")
        self.assertEqual(data["root"], "/root")
        self.assertEqual(data["repos"][0]["name"], "alpha")

    def test_json_trailing_newline(self):
        out = rr.render_json([], "t", "/g", "/r")
        self.assertTrue(out.endswith("\n"))


# ---------------------------------------------------------------------------
# Pure: sort order (last-commit desc, undated last)
# ---------------------------------------------------------------------------

class TestSortOrder(unittest.TestCase):

    def test_desc_with_undated_last(self):
        rows = [
            {"name": "old", "last_commit_date": "2026-01-01T00:00:00Z"},
            {"name": "new", "last_commit_date": "2026-06-01T00:00:00Z"},
            {"name": "undated", "last_commit_date": None},
        ]
        rows.sort(key=rr._sort_key, reverse=True)
        self.assertEqual([r["name"] for r in rows], ["new", "old", "undated"])


# ---------------------------------------------------------------------------
# Pure: repo / worktree detection
# ---------------------------------------------------------------------------

class TestRepoDetection(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.d, ignore_errors=True))

    def test_full_repo_dir(self):
        repo = self.d / "full"
        (repo / ".git").mkdir(parents=True)
        self.assertTrue(rr.is_git_repo(repo))
        self.assertFalse(rr.is_worktree(repo))

    def test_worktree_dotgit_file(self):
        wt = self.d / "wt"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: /somewhere/.git/worktrees/wt\n")
        self.assertTrue(rr.is_git_repo(wt))
        self.assertTrue(rr.is_worktree(wt))

    def test_non_repo(self):
        plain = self.d / "plain"
        plain.mkdir()
        self.assertFalse(rr.is_git_repo(plain))


# ---------------------------------------------------------------------------
# Integration: scan a real tiny git repo end-to-end (no machine state)
# ---------------------------------------------------------------------------

class TestScanRealRepo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.git = rr.git_bin()

    def setUp(self):
        if not self.git:
            self.skipTest("git not available")
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))

    def _git(self, *args, cwd):
        env = dict(os.environ,
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
        subprocess.run([self.git, *args], cwd=str(cwd), check=True,
                       capture_output=True, text=True, env=env)

    def _make_repo(self, name: str, files: dict[str, str] | None = None,
                   dirty: bool = False, origin: str | None = None) -> Path:
        repo = self.root / name
        repo.mkdir()
        self._git("init", "-q", "-b", "main", cwd=repo)
        (repo / "README.md").write_text("hi\n")
        for rel, content in (files or {}).items():
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        self._git("add", "-A", cwd=repo)
        self._git("commit", "-q", "-m", "initial commit", cwd=repo)
        if origin:
            self._git("remote", "add", "origin", origin, cwd=repo)
        if dirty:
            (repo / "scratch.txt").write_text("uncommitted\n")
        return repo

    def test_scan_one_repo_fields(self):
        repo = self._make_repo(
            "alpha",
            files={".claude-plugin/plugin.json": '{"version": "4.5.6"}'},
            origin="https://github.com/u/alpha.git",
        )
        row = rr.scan_one_repo(repo, self.git)
        self.assertEqual(row["name"], "alpha")
        self.assertEqual(row["branch"], "main")
        self.assertEqual(row["dirty_count"], 0)
        self.assertEqual(row["origin"], "https://github.com/u/alpha.git")
        self.assertEqual(row["version"], "4.5.6")
        self.assertTrue(row["last_commit_date"].startswith("20"))
        self.assertEqual(row["last_commit_subject"], "initial commit")
        self.assertFalse(row["is_worktree"])

    def test_dirty_count(self):
        repo = self._make_repo("beta", dirty=True)
        row = rr.scan_one_repo(repo, self.git)
        self.assertGreaterEqual(row["dirty_count"], 1)

    def test_scan_all_skips_non_repos_and_sorts(self):
        self._make_repo("repo1", origin="https://github.com/u/r1.git")
        self._make_repo("repo2")
        # A non-repo dir and a loose file must both be skipped silently.
        (self.root / "not-a-repo").mkdir()
        (self.root / "loose.txt").write_text("x")
        rows = rr.scan_all(self.root, self.git)
        names = {r["name"] for r in rows}
        self.assertEqual(names, {"repo1", "repo2"})

    def test_generate_writes_files(self):
        self._make_repo("gamma")
        out_dir = self.root / "_out"
        summary = rr.generate(root=self.root, out_dir=out_dir, write=True)
        self.assertEqual(summary["count"], 1)
        self.assertTrue((out_dir / "REGISTRY.md").is_file())
        self.assertTrue((out_dir / "registry.json").is_file())
        data = json.loads((out_dir / "registry.json").read_text())
        self.assertEqual(data["repos"][0]["name"], "gamma")

    def test_generate_no_write(self):
        self._make_repo("delta")
        out_dir = self.root / "_out2"
        summary = rr.generate(root=self.root, out_dir=out_dir, write=False)
        self.assertEqual(summary["count"], 1)
        self.assertFalse(out_dir.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
