from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import core  # noqa: E402


class PluginFlowTests(unittest.TestCase):
    def test_docs_aligned_manifest_exists(self) -> None:
        lowercase_manifest = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        uppercase_manifest = PLUGIN_ROOT / ".Codex-plugin" / "plugin.json"

        self.assertTrue(lowercase_manifest.exists())
        self.assertTrue(uppercase_manifest.exists())

        payload = json.loads(lowercase_manifest.read_text())
        self.assertEqual(payload["name"], "build-loop-auto-research")
        self.assertNotIn("commands", payload)
        self.assertNotIn("agents", payload)
        self.assertNotIn("hooks", payload)

    def test_skill_first_surface_exists(self) -> None:
        skill_names = {
            "analyze-history",
            "autoresearch-loop",
            "build-loop-auto-research",
            "context-restore",
            "context-snapshot",
            "memory-lookup",
            "optimize-brief",
            "pattern-aware-planning",
            "research-build",
        }
        actual = {
            path.parent.name
            for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")
        }

        self.assertTrue(skill_names.issubset(actual))

    def test_init_loop_creates_goal_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPTS_DIR / "init_loop.py"),
                    "--workdir",
                    str(workdir),
                    "--goal",
                    "Build a research-backed plugin plan",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            goal_path = Path(payload["goal_path"])
            state_path = Path(payload["state_path"])

            self.assertTrue(goal_path.exists())
            self.assertTrue(state_path.exists())
            self.assertIn("Build a research-backed plugin plan", goal_path.read_text())
            self.assertIn('"phase": "ASSESS"', state_path.read_text())

    def test_analyze_history_detects_dominant_loop(self) -> None:
        fixture_dir = Path(__file__).parent / "fixtures" / "history"
        summary = core.analyze_history_dir(fixture_dir)

        self.assertEqual(
            summary["dominant_loop"],
            "diagnose -> authorize -> verify -> ship_or_handoff",
        )
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["sample_size_confidence"], "low")

    def test_research_packet_includes_guardrails_and_docs_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "src").mkdir()
            (repo_path / "src" / "app.ts").write_text("export const app = true;\n")
            (repo_path / "package.json").write_text(
                json.dumps(
                    {
                        "dependencies": {"next": "15.0.0"},
                        "scripts": {
                            "build": "next build",
                            "test": "vitest",
                            "lint": "eslint .",
                        },
                    }
                )
            )
            (repo_path / "vercel.json").write_text("{}\n")

            packet = core.build_research_packet(
                "Add auth and payments flow for this product and improve user experience",
                repo_path,
                mode="balanced",
            )

            self.assertIn("## Integration points / handoffs", packet)
            self.assertIn("## Documentation checks", packet)
            self.assertIn("## Simplicity + UX gate", packet)
            self.assertIn("## Confidence action", packet)
            self.assertIn("Vercel docs", packet)
            self.assertIn("auth provider docs", packet)
            self.assertIn("payment provider docs", packet)
            self.assertIn("- Overall confidence: `medium`", packet)

    def test_memory_lookup_returns_known_fix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_dir = Path(temp_dir)
            lessons_dir = memory_dir / "lessons"
            lessons_dir.mkdir()
            lesson_path = lessons_dir / "2026-04-15-auth-timeout.md"
            lesson_path.write_text(
                "# Auth timeout callback issue\n\n"
                "The auth callback timeout caused token refresh failures in the checkout flow. "
                "Fix by aligning callback timeout, token refresh, session storage, and retry handling."
            )

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPTS_DIR / "memory_lookup.py"),
                    "--query",
                    "auth callback timeout token refresh checkout session retry failure",
                    "--memory-dir",
                    str(memory_dir),
                    "--format",
                    "json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["verdict"], "KNOWN_FIX")
            self.assertEqual(len(payload["matches"]), 1)

    def test_context_snapshot_and_restore_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as registry_dir:
            workdir = Path(temp_dir)

            subprocess.run(
                [
                    "python3",
                    str(SCRIPTS_DIR / "context_snapshot.py"),
                    "--workdir",
                    str(workdir),
                    "--registry-dir",
                    str(registry_dir),
                    "--summary",
                    "Implement the research packet command",
                    "--status",
                    "Core scripts added, validation pending",
                    "--decision",
                    "Prefer local scripts before external dependencies",
                    "--open-item",
                    "Run unittest suite",
                    "--unknown",
                    "Need to verify restore flow",
                    "--file",
                    "scripts/core.py",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            restore = subprocess.run(
                [
                    "python3",
                    str(SCRIPTS_DIR / "context_restore.py"),
                    "--workdir",
                    str(workdir),
                    "--registry-dir",
                    str(registry_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Implement the research packet command", restore.stdout)
            self.assertIn("Prefer local scripts before external dependencies", restore.stdout)
            self.assertTrue((workdir / ".build-loop-auto-research" / "context" / "trailhead.md").exists())


if __name__ == "__main__":
    unittest.main()
