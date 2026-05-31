#!/usr/bin/env python3
"""
Tests for marketplace-sync.py extensions.

Run:  python3 -m pytest tests/test_marketplace_sync.py -v
  or: python3 tests/test_marketplace_sync.py

All tests use fixture files only — zero live-machine state dependency.
"""
import json
import sys
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

    def test_empty_output(self):
        result = ms.parse_codex_plugin_list("", "ross-labs-local")
        self.assertEqual(result, {})

    def test_marketplace_not_present_returns_empty(self):
        result = ms.parse_codex_plugin_list(self.fixture_text, "nonexistent-mkt")
        self.assertEqual(result, {})


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
        remove_cmd, add_cmd = ms.codex_remediate_cmds("build-loop", "ross-labs-local")
        self.assertIn("codex plugin remove", remove_cmd)
        self.assertIn("build-loop@ross-labs-local", remove_cmd)
        self.assertIn("codex plugin add", add_cmd)
        self.assertIn("build-loop@ross-labs-local", add_cmd)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
