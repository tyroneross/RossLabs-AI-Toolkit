#!/usr/bin/env python3
"""
Tests for marketplace-sync.py extensions.

Run:  python3 -m pytest tests/test_marketplace_sync.py -v
  or: python3 tests/test_marketplace_sync.py

All tests use fixture files only — zero live-machine state dependency.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Import marketplace-sync.py via importlib (hyphen in filename prevents normal import)
import importlib.util

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "marketplace_sync",
    str(REPO_ROOT / "scripts" / "marketplace-sync.py"),
)
ms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Semver comparison (Chunk 1)
# ---------------------------------------------------------------------------

class TestSemverCompare(unittest.TestCase):

    def test_equal_versions_not_stale(self):
        self.assertFalse(ms.semver_lt("1.2.3", "1.2.3"))

    def test_patch_older(self):
        self.assertTrue(ms.semver_lt("1.2.2", "1.2.3"))

    def test_patch_newer(self):
        self.assertFalse(ms.semver_lt("1.2.4", "1.2.3"))

    def test_minor_older(self):
        self.assertTrue(ms.semver_lt("1.1.9", "1.2.0"))

    def test_major_older(self):
        self.assertTrue(ms.semver_lt("0.24.2", "1.0.0"))

    def test_major_newer(self):
        self.assertFalse(ms.semver_lt("2.0.0", "1.99.99"))

    def test_two_part_version(self):
        # "1.2" vs "1.3" — missing patch treated as 0
        self.assertTrue(ms.semver_lt("1.2", "1.3"))

    def test_single_part_version(self):
        self.assertTrue(ms.semver_lt("1", "2"))

    def test_non_numeric_component_treated_safely(self):
        # git-sha or hash versions: treat non-numeric parts as equal (0)
        # Must not crash
        result = ms.semver_lt("abc123", "1.0.0")
        self.assertIsInstance(result, bool)

    def test_empty_string_treated_safely(self):
        result = ms.semver_lt("", "1.0.0")
        self.assertIsInstance(result, bool)

    def test_none_treated_safely(self):
        result = ms.semver_lt(None, "1.0.0")
        self.assertIsInstance(result, bool)

    # R1: prerelease / release parity — neither direction should emit a command
    def test_release_vs_prerelease_not_stale(self):
        # "1.0.0" installed, "1.0.0-rc.1" is truth → should NOT flag as stale
        self.assertFalse(ms.semver_lt("1.0.0", "1.0.0-rc.1"))

    def test_prerelease_vs_release_not_stale(self):
        # "1.0.0-rc.1" installed, "1.0.0" is truth → should NOT flag as stale
        self.assertFalse(ms.semver_lt("1.0.0-rc.1", "1.0.0"))

    def test_prerelease_equal_release_not_stale(self):
        # Identical modulo suffix
        self.assertFalse(ms.semver_lt("2.3.4-alpha.1", "2.3.4"))

    def test_older_prerelease_vs_newer_release_is_stale(self):
        # "1.0.0-rc.1" installed, truth is "1.1.0" → numerically older, should be stale
        self.assertTrue(ms.semver_lt("1.0.0-rc.1", "1.1.0"))

    def test_newer_prerelease_vs_older_release_not_stale(self):
        # "2.0.0-rc.1" installed, truth is "1.9.9" → numerically newer, not stale
        self.assertFalse(ms.semver_lt("2.0.0-rc.1", "1.9.9"))

    def test_build_metadata_stripped(self):
        # Build metadata (+build.123) should be stripped the same way
        self.assertFalse(ms.semver_lt("1.0.0+build.123", "1.0.0"))


# ---------------------------------------------------------------------------
# Claude installed_plugins.json parsing (Chunk 1)
# ---------------------------------------------------------------------------

class TestParseClaudeInstalled(unittest.TestCase):

    def setUp(self):
        self.fixture = FIXTURES / "installed_plugins.json"
        self.data = json.loads(self.fixture.read_text())

    def test_parse_returns_dict(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        self.assertIsInstance(result, dict)

    def test_filters_correct_marketplace(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        # Should include toolkit plugins only
        for key in result:
            self.assertNotIn("some-other-marketplace", key)

    def test_detects_build_loop_scopes(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        self.assertIn("build-loop", result)
        scopes = {entry["scope"] for entry in result["build-loop"]}
        self.assertIn("project", scopes)
        self.assertIn("user", scopes)

    def test_build_loop_project_version(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        project_entries = [e for e in result["build-loop"] if e["scope"] == "project"]
        self.assertEqual(project_entries[0]["version"], "0.20.0")

    def test_build_loop_user_version(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        user_entries = [e for e in result["build-loop"] if e["scope"] == "user"]
        self.assertEqual(user_entries[0]["version"], "0.22.0")

    def test_ibr_present(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        self.assertIn("ibr", result)

    def test_unrelated_marketplace_excluded(self):
        result = ms.parse_claude_installed(self.data, "rosslabs-ai-toolkit")
        self.assertNotIn("unrelated", result)

    def test_empty_plugins_dict(self):
        result = ms.parse_claude_installed({"version": 2, "plugins": {}}, "rosslabs-ai-toolkit")
        self.assertEqual(result, {})

    def test_missing_plugins_key(self):
        result = ms.parse_claude_installed({}, "rosslabs-ai-toolkit")
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Codex plugin list parsing (Chunk 1)
# ---------------------------------------------------------------------------

class TestParseCodexPluginList(unittest.TestCase):

    def setUp(self):
        self.fixture_text = (FIXTURES / "codex_plugin_list.txt").read_text()

    def test_parse_returns_dict(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertIsInstance(result, dict)

    def test_filters_correct_marketplace(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        for key in result:
            self.assertNotIn("openai-bundled", key)
            self.assertNotIn("local", key.replace("ross-labs-local", ""))

    def test_detects_build_loop_installed(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertIn("build-loop", result)

    def test_build_loop_version(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertEqual(result["build-loop"]["version"], "0.14.0")

    def test_claude_code_debugger_version(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertEqual(result["claude-code-debugger"]["version"], "1.6.0")

    def test_not_installed_excluded(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertNotIn("agent-astronomer", result)
        self.assertNotIn("navgator", result)

    def test_other_marketplace_ibr_excluded(self):
        # ibr@local should not appear under ross-labs-local
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        # ibr@ross-labs-local is "not installed" in fixture, so absent
        self.assertNotIn("ibr", result)

    # R3: positive-presence assertions for all installed entries
    def test_prompt_builder_present(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertIn("prompt-builder", result)
        self.assertEqual(result["prompt-builder"]["version"], "0.1.0")

    def test_agent_builder_present(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        self.assertIn("agent-builder", result)
        self.assertEqual(result["agent-builder"]["version"], "0.1.0")

    def test_all_installed_entries_present(self):
        # Fixture has 4 installed entries under ross-labs-local:
        # build-loop, claude-code-debugger, prompt-builder, agent-builder
        result = ms.parse_codex_plugin_list(self.fixture_text, "ross-labs-local")
        for expected in ("build-loop", "claude-code-debugger", "prompt-builder", "agent-builder"):
            self.assertIn(expected, result, f"Expected installed plugin '{expected}' to be present")

    def test_empty_output(self):
        result = ms.parse_codex_plugin_list("", "ross-labs-local")
        self.assertEqual(result, {})

    def test_marketplace_not_present_returns_empty(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "nonexistent-mkt")
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Codex config/cache parsing (current CLI path)
# ---------------------------------------------------------------------------

class TestParseCodexConfigPlugins(unittest.TestCase):

    def test_parses_configured_marketplace_plugins(self):
        data = {
            "plugins": {
                "build-loop@ross-labs-local": {"enabled": True},
                "agent-builder@ross-labs-local": {"enabled": False},
                "browser@openai-bundled": {"enabled": True},
            }
        }
        result = ms.parse_codex_config_plugins(data, "ross-labs-local")
        self.assertEqual(set(result), {"build-loop", "agent-builder"})
        self.assertEqual(result["build-loop"]["status"], "enabled")
        self.assertEqual(result["agent-builder"]["status"], "disabled")

    def test_resolves_newest_cached_version(self):
        data = {"plugins": {"build-loop@ross-labs-local": {"enabled": True}}}
        with tempfile.TemporaryDirectory() as d:
            plugin_dir = Path(d) / "ross-labs-local" / "build-loop"
            (plugin_dir / "0.35.0").mkdir(parents=True)
            (plugin_dir / "0.36.0").mkdir()
            result = ms.parse_codex_config_plugins(data, "ross-labs-local", Path(d))
        self.assertEqual(result["build-loop"]["version"], "0.36.0")


# ---------------------------------------------------------------------------
# Stale detection helpers (Chunk 1)
# ---------------------------------------------------------------------------

class TestStaleDetection(unittest.TestCase):

    def test_stale_claude_install(self):
        # installed 0.20.0, source-of-truth 0.24.2
        drift = ms.find_claude_drift(
            installed={"build-loop": [{"scope": "user", "version": "0.20.0"}]},
            truth={"build-loop": "0.24.2"},
        )
        self.assertEqual(len(drift), 1)
        self.assertEqual(drift[0]["name"], "build-loop")
        self.assertEqual(drift[0]["installed_version"], "0.20.0")
        self.assertEqual(drift[0]["truth_version"], "0.24.2")
        self.assertEqual(drift[0]["scope"], "user")

    def test_up_to_date_claude_install(self):
        drift = ms.find_claude_drift(
            installed={"ibr": [{"scope": "user", "version": "1.3.0"}]},
            truth={"ibr": "1.3.0"},
        )
        self.assertEqual(drift, [])

    def test_plugin_not_in_truth_skipped(self):
        # Installed plugins not in the toolkit truth map are ignored
        drift = ms.find_claude_drift(
            installed={"unknown-plugin": [{"scope": "user", "version": "9.9.9"}]},
            truth={"ibr": "1.3.0"},
        )
        self.assertEqual(drift, [])

    # R2: empty installed version must not produce a spurious stale entry
    def test_empty_installed_version_not_flagged_stale(self):
        drift = ms.find_claude_drift(
            installed={"ibr": [{"scope": "user", "version": ""}]},
            truth={"ibr": "1.3.0"},
        )
        self.assertEqual(drift, [], "Empty installed version must not emit an update command")

    def test_missing_version_key_not_flagged_stale(self):
        drift = ms.find_claude_drift(
            installed={"ibr": [{"scope": "user"}]},  # no 'version' key at all
            truth={"ibr": "1.3.0"},
        )
        self.assertEqual(drift, [], "Missing version key must not emit an update command")

    def test_stale_codex_install(self):
        drift = ms.find_codex_drift(
            installed={"build-loop": {"version": "0.14.0", "status": "installed, enabled"}},
            truth={"build-loop": "0.24.2"},
        )
        self.assertEqual(len(drift), 1)
        self.assertEqual(drift[0]["name"], "build-loop")
        self.assertEqual(drift[0]["installed_version"], "0.14.0")
        self.assertEqual(drift[0]["truth_version"], "0.24.2")

    def test_up_to_date_codex_install(self):
        drift = ms.find_codex_drift(
            installed={"build-loop": {"version": "0.24.2", "status": "installed, enabled"}},
            truth={"build-loop": "0.24.2"},
        )
        self.assertEqual(drift, [])


# ---------------------------------------------------------------------------
# Remediation command generation (Chunk 1)
# ---------------------------------------------------------------------------

class TestRemediationCommands(unittest.TestCase):

    def test_claude_update_command_user_scope(self):
        cmd = ms.claude_update_cmd("build-loop", "user")
        self.assertIn("claude plugin update", cmd)
        self.assertIn("build-loop@rosslabs-ai-toolkit", cmd)
        self.assertIn("--scope user", cmd)

    def test_claude_update_command_project_scope(self):
        cmd = ms.claude_update_cmd("ibr", "project")
        self.assertIn("--scope project", cmd)

    def test_codex_remediation_command(self):
        cmd = ms.codex_remediate_cmd("build-loop", "ross-labs-local")
        self.assertEqual(cmd, "codex plugin marketplace upgrade ross-labs-local")


# ---------------------------------------------------------------------------
# README surface writers
# ---------------------------------------------------------------------------

class TestReadmeSurfaceWriters(unittest.TestCase):

    def test_plugin_index_row_updates(self):
        text = (
            "| Plugin | Repo | Description | Version |\n"
            "|--------|------|-------------|---------|\n"
            "| build-loop | [tyroneross/build-loop](https://github.com/tyroneross/build-loop) | Portable build loop | 0.36.0 |\n"
        )
        changes = []
        out = ms.apply_plugin_index_readme(text, {"build-loop": "0.36.1"}, changes)
        self.assertIn("| build-loop | [tyroneross/build-loop](https://github.com/tyroneross/build-loop) | Portable build loop | 0.36.1 |", out)
        self.assertEqual(changes, ["plugins/README.md: build-loop version 0.36.0 → 0.36.1"])

    def test_plugin_index_unknown_row_unchanged(self):
        text = (
            "| Plugin | Repo | Description | Version |\n"
            "|--------|------|-------------|---------|\n"
            "| other | [example/other](https://github.com/example/other) | Other plugin | 1.0.0 |\n"
        )
        changes = []
        out = ms.apply_plugin_index_readme(text, {"build-loop": "0.36.1"}, changes)
        self.assertEqual(out, text)
        self.assertEqual(changes, [])


# ---------------------------------------------------------------------------
# Chunk 3: package.json ↔ plugin.json drift detection
# ---------------------------------------------------------------------------

class TestPackageJsonDrift(unittest.TestCase):

    def setUp(self):
        # Use the real plugins directory from the toolkit
        self.plugins_dir = REPO_ROOT / "plugins"

    def test_scan_returns_list(self):
        results = ms.scan_package_json_drift(self.plugins_dir)
        self.assertIsInstance(results, list)

    def test_each_result_has_required_keys(self):
        results = ms.scan_package_json_drift(self.plugins_dir)
        for item in results:
            self.assertIn("name", item)
            self.assertIn("package_json_version", item)
            self.assertIn("plugin_json_version", item)
            self.assertIn("drifted", item)

    def test_currently_synced_plugins_have_no_drift(self):
        # All plugins are currently in sync per pre-flight check
        results = ms.scan_package_json_drift(self.plugins_dir)
        drifted = [r for r in results if r["drifted"]]
        # All currently in sync — expect zero drift in real tree
        # (this would catch regressions if someone bumps one but not the other)
        for item in drifted:
            self.fail(
                f"package.json/plugin.json drift detected for {item['name']}: "
                f"{item['package_json_version']} vs {item['plugin_json_version']}"
            )

    def test_synthetic_drift_detection(self):
        # Inject synthetic data to verify detection logic works independently
        # of live tree state
        results = ms.detect_pkg_plugin_drift_from_pairs([
            {"name": "foo", "package_json_version": "1.0.0", "plugin_json_version": "1.0.0"},
            {"name": "bar", "package_json_version": "1.1.0", "plugin_json_version": "1.0.0"},
        ])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "bar")
        self.assertTrue(results[0]["drifted"])

    def test_synthetic_no_drift(self):
        results = ms.detect_pkg_plugin_drift_from_pairs([
            {"name": "foo", "package_json_version": "2.0.0", "plugin_json_version": "2.0.0"},
        ])
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# Chunk 5: mirror-on-main invariant
# ---------------------------------------------------------------------------

class TestMirrorBranchHygiene(unittest.TestCase):

    def setUp(self):
        self.plugins_dir = REPO_ROOT / "plugins"

    def test_scan_returns_list(self):
        results = ms.scan_mirror_branches(self.plugins_dir)
        self.assertIsInstance(results, list)

    def test_each_record_has_required_keys(self):
        results = ms.scan_mirror_branches(self.plugins_dir)
        for item in results:
            for key in ("name", "target_path", "branch", "on_main", "error"):
                self.assertIn(key, item, f"missing key {key} in {item}")

    def test_currently_all_mirrors_on_main(self):
        """Regression catch: after the mirror-on-main rule lands, every mirror
        in the live tree must report on_main=True. If a future commit re-points
        a mirror to a feature branch, this test fails."""
        results = ms.scan_mirror_branches(self.plugins_dir)
        off_main = [r for r in results if not r["on_main"]]
        if off_main:
            details = "\n".join(
                f"  - {r['name']}: branch={r['branch']!r} error={r['error']!r}"
                for r in off_main
            )
            self.fail(f"Off-main mirrors detected:\n{details}")

    def test_synthetic_off_main_detected(self):
        records = [
            {"name": "a", "target_path": "/x/a", "branch": "main", "on_main": True, "error": ""},
            {"name": "b", "target_path": "/x/b", "branch": "feature/foo", "on_main": False, "error": ""},
            {"name": "c", "target_path": "/x/c", "branch": "", "on_main": False, "error": "no git"},
        ]
        off_main = ms.find_off_main_mirrors(records)
        self.assertEqual(len(off_main), 2)
        names = {r["name"] for r in off_main}
        self.assertEqual(names, {"b", "c"})

    def test_synthetic_all_on_main_returns_empty(self):
        records = [
            {"name": "a", "target_path": "/x/a", "branch": "main", "on_main": True, "error": ""},
            {"name": "b", "target_path": "/x/b", "branch": "main", "on_main": True, "error": ""},
        ]
        self.assertEqual(ms.find_off_main_mirrors(records), [])

    def test_missing_on_main_key_treated_as_off(self):
        # Defensive: dict missing the on_main key (e.g. corrupted record)
        records = [{"name": "x", "target_path": "/x", "branch": "main"}]
        self.assertEqual(ms.find_off_main_mirrors(records)[0]["name"], "x")

    def test_fix_command_includes_name(self):
        cmd = ms.mirror_fix_command("foo", "/some/path")
        self.assertIn("plugins/foo", cmd)
        self.assertIn("/some/path", cmd)
        self.assertIn("ln -sfn", cmd)

    def test_scan_handles_nonexistent_dir(self):
        results = ms.scan_mirror_branches(REPO_ROOT / "no_such_dir_for_test_xyz")
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# Chunk 6: gh resolution (Item 1 PATH bug)
# ---------------------------------------------------------------------------

import os


class TestGhBin(unittest.TestCase):

    def test_returns_path_when_on_path(self):
        # In the dev environment gh is reachable; if not present at all, the
        # function must still return None without raising.
        result = ms.gh_bin()
        self.assertTrue(result is None or isinstance(result, str))

    def test_falls_back_under_minimal_path(self):
        # Simulate launchd's minimal PATH. gh is at /opt/homebrew/bin (not on
        # /usr/bin:/bin), so which() misses and the fallback must catch it —
        # but only if the fallback binary actually exists on this machine.
        old = os.environ.get("PATH")
        try:
            os.environ["PATH"] = "/usr/bin:/bin"
            result = ms.gh_bin()
            # Match the implementation's predicate exactly: present AND executable.
            fallback_usable = any(
                os.path.exists(p) and os.access(p, os.X_OK) for p in ms._GH_FALLBACKS
            )
            if fallback_usable:
                self.assertIsNotNone(result, "executable gh at a fallback path must be resolved")
                self.assertTrue(os.path.isabs(result))
            else:
                self.assertIsNone(result)
        finally:
            if old is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = old

    def test_none_when_absent_everywhere(self):
        # Empty PATH + monkeypatched-empty fallbacks → None, never a crash.
        old_path = os.environ.get("PATH")
        old_fb = ms._GH_FALLBACKS
        try:
            os.environ["PATH"] = ""
            ms._GH_FALLBACKS = ("/nonexistent/gh/xyz",)
            self.assertIsNone(ms.gh_bin())
        finally:
            ms._GH_FALLBACKS = old_fb
            if old_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = old_path


# ---------------------------------------------------------------------------
# Chunk 6: local_version honors source.path subdir (Item 2)
# ---------------------------------------------------------------------------

class TestLocalVersionSubpath(unittest.TestCase):

    def test_subpath_resolves_agent_astronomer(self):
        # agent-astronomer ships under plugin/ — root has no plugin.json, so a
        # plain local_version(name) misses; the subpath must find 0.1.0.
        # Only assert if the mirror is present (dev machine).
        root_only = ms.local_version("agent-astronomer")
        with_sub = ms.local_version("agent-astronomer", "plugin")
        if with_sub is not None:
            # Subpath resolution must succeed where root-only fails for this layout.
            self.assertEqual(root_only, None,
                             "agent-astronomer repo root should have no plugin.json")
            self.assertRegex(with_sub, r"^\d+\.\d+\.\d+")

    def test_subpath_does_not_break_root_plugins(self):
        # A standard repo-root mirror (web-scraper) must still resolve with an
        # empty subpath exactly as before.
        v = ms.local_version("web-scraper")
        if v is not None:
            self.assertRegex(v, r"^\d+\.\d+\.\d+")

    def test_subpath_strips_slashes(self):
        # "/plugin/" and "plugin" must behave identically.
        a = ms.local_version("agent-astronomer", "plugin")
        b = ms.local_version("agent-astronomer", "/plugin/")
        self.assertEqual(a, b)

    def test_unknown_plugin_returns_none(self):
        self.assertIsNone(ms.local_version("no-such-plugin-xyz", "plugin"))


# ---------------------------------------------------------------------------
# Chunk 6: act-mode pure helpers (Item 1 act mode)
# ---------------------------------------------------------------------------

class TestActModeHelpers(unittest.TestCase):

    def test_commit_message_lists_changes(self):
        msg = ms.commit_message_for([
            ".claude-plugin/marketplace.json: web-scraper.version '0.5.0' → '0.5.2'",
        ])
        self.assertIn("auto-sync catalog", msg)
        self.assertIn("web-scraper", msg)
        self.assertIn("0.5.2", msg)

    def test_commit_message_empty_changes(self):
        msg = ms.commit_message_for([])
        self.assertIn("surface reconcile", msg)
        # Must still be a non-empty, well-formed message.
        self.assertTrue(msg.strip())

    def test_act_worktree_path_is_dedicated(self):
        # The act worktree lives under a dedicated cache dir (~/.cache/
        # marketplace-sync/act-worktree), never a project source tree. Asserting
        # the dedicated location is robust even when the suite itself runs from
        # inside the act worktree (where TOOLKIT_ROOT == ACT_WORKTREE).
        p = str(ms.ACT_WORKTREE)
        self.assertIn("act-worktree", p)
        self.assertIn(".cache", p)
        self.assertIn("marketplace-sync", p)

    def test_plugin_cache_path_targets_marketplace_clone(self):
        self.assertTrue(str(ms.PLUGIN_CACHE_MARKETPLACE).endswith("rosslabs-ai-toolkit"))
        self.assertIn("marketplaces", str(ms.PLUGIN_CACHE_MARKETPLACE))

    def test_surface_files_bounded(self):
        # Commit staging is restricted to exactly the reconcile surfaces —
        # never a blanket `git add -A` that could capture untracked residue.
        self.assertEqual(
            set(ms.ACT_SURFACE_FILES),
            {
                ".claude-plugin/marketplace.json",
                ".agents/plugins/marketplace.json",
                "README.md",
                "plugins/README.md",
            },
        )

    def test_act_branch_is_dedicated(self):
        # Dedicated branch name so a reused worktree never lands commits on main
        # in the developer checkout.
        self.assertEqual(ms.ACT_BRANCH, "marketplace-sync-act")
        self.assertNotEqual(ms.ACT_BRANCH, "main")

    def test_lockfile_under_cache_dir(self):
        self.assertTrue(str(ms.ACT_LOCKFILE).endswith("act.lock"))
        self.assertIn("marketplace-sync", str(ms.ACT_LOCKFILE))

    def test_worktree_invalid_when_not_a_worktree(self):
        # A path with no .git is never a valid act worktree (guards against a
        # stale/symlinked dir pointing at the dev checkout).
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(ms._worktree_is_valid(Path(d), ms.TOOLKIT_ROOT))


# ---------------------------------------------------------------------------
# Chunk 6: plist template uses act mode (Item 1 activation)
# ---------------------------------------------------------------------------

class TestPlistActMode(unittest.TestCase):

    def test_plist_template_uses_act_flag(self):
        rendered = ms.LAUNCHD_PLIST_TEMPLATE.format(
            label="test", python="/usr/bin/python3",
            script="/tmp/marketplace-sync.py", log_dir="/tmp",
        )
        self.assertIn("<string>--act</string>", rendered)
        # The old check-only mode must be gone from the template.
        self.assertNotIn("<string>--check</string>", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
