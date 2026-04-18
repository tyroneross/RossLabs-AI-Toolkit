from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from scripts.metric_runner import GuardResult, MetricResult, parse_numeric, run_guard, run_metric
from scripts.autoresearch_loop import (
    IterationResult,
    archive_experiment,
    check_convergence,
    get_experiment_summary,
    init_experiment,
    load_experiment,
    load_results,
    log_iteration,
    run_iteration,
)
from scripts.core import detect_autoresearch_targets, suggest_metric_for_target


# ---------------------------------------------------------------------------
# parse_numeric
# ---------------------------------------------------------------------------

class TestParseNumeric(unittest.TestCase):

    def test_plain_integer(self):
        self.assertEqual(parse_numeric("42"), 42.0)

    def test_plain_float(self):
        self.assertAlmostEqual(parse_numeric("3.14"), 3.14)

    def test_percentage(self):
        self.assertAlmostEqual(parse_numeric("85.2%"), 85.2)

    def test_labeled_coverage(self):
        self.assertAlmostEqual(parse_numeric("Coverage: 85.2%"), 85.2)

    def test_labeled_score(self):
        self.assertAlmostEqual(parse_numeric("Score: 0.824"), 0.824)

    def test_labeled_time(self):
        self.assertAlmostEqual(parse_numeric("Time: 19.1s"), 19.1)

    def test_time_command_real(self):
        result = parse_numeric("real\t0m19.123s\nuser\t0m15.456s\nsys\t0m3.789s")
        self.assertAlmostEqual(result, 19.123)

    def test_time_command_with_minutes(self):
        result = parse_numeric("real\t2m30.5s")
        self.assertAlmostEqual(result, 150.5)

    def test_multiline_last_match(self):
        output = "Line 1: 10\nLine 2: 20\nCoverage: 85.5%"
        self.assertAlmostEqual(parse_numeric(output), 85.5)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_numeric("")

    def test_no_number_raises(self):
        with self.assertRaises(ValueError):
            parse_numeric("no numbers here at all")

    def test_trailing_number(self):
        self.assertAlmostEqual(parse_numeric("result is 42.7"), 42.7)


# ---------------------------------------------------------------------------
# run_metric
# ---------------------------------------------------------------------------

class TestRunMetric(unittest.TestCase):

    def test_success(self):
        result = run_metric("echo 42.5")
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.value, 42.5)
        self.assertIsNone(result.error)
        self.assertGreater(result.elapsed_seconds, 0)

    def test_failure_nonzero_exit(self):
        result = run_metric("exit 1")
        self.assertFalse(result.success)
        self.assertIn("exited with code 1", result.error)

    def test_failure_no_number(self):
        result = run_metric("echo 'no numbers'")
        self.assertFalse(result.success)
        self.assertIn("No numeric value", result.error)

    def test_timeout(self):
        result = run_metric("sleep 10", timeout=1)
        self.assertFalse(result.success)
        self.assertIn("timed out", result.error)

    def test_labeled_output(self):
        result = run_metric("echo 'Coverage: 92.3%'")
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.value, 92.3)


# ---------------------------------------------------------------------------
# run_guard
# ---------------------------------------------------------------------------

class TestRunGuard(unittest.TestCase):

    def test_pass(self):
        result = run_guard("true")
        self.assertTrue(result.passed)
        self.assertGreater(result.elapsed_seconds, 0)

    def test_fail(self):
        result = run_guard("false")
        self.assertFalse(result.passed)

    def test_timeout(self):
        result = run_guard("sleep 10", timeout=1)
        self.assertFalse(result.passed)
        self.assertIn("timed out", result.raw_output)


# ---------------------------------------------------------------------------
# init_experiment
# ---------------------------------------------------------------------------

class TestInitExperiment(unittest.TestCase):

    def test_creates_experiment_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            path = init_experiment(workdir, {
                "target": "test-target",
                "scope": "*.py",
                "metric_cmd": "echo 85.2",
                "guard_cmd": "true",
                "budget": 10,
                "direction": "higher",
            })

            self.assertTrue(path.exists())
            exp = json.loads(path.read_text())
            self.assertEqual(exp["target"], "test-target")
            self.assertEqual(exp["scope"], "*.py")
            self.assertEqual(exp["direction"], "higher")
            self.assertEqual(exp["budget"], 10)
            self.assertAlmostEqual(exp["baseline_value"], 85.2)
            self.assertEqual(exp["iterations_kept"], 0)
            self.assertEqual(exp["iterations_total"], 0)

    def test_creates_results_tsv_with_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            init_experiment(workdir, {
                "target": "test",
                "metric_cmd": "echo 50",
                "direction": "higher",
            })

            results = load_results(workdir)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["status"], "baseline")
            self.assertAlmostEqual(float(results[0]["metric"]), 50.0)

    def test_direction_lower(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            init_experiment(workdir, {
                "target": "build-time",
                "metric_cmd": "echo 19.1",
                "direction": "lower",
            })

            exp = load_experiment(workdir)
            self.assertEqual(exp["direction"], "lower")
            self.assertAlmostEqual(exp["baseline_value"], 19.1)

    def test_invalid_direction_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            with self.assertRaises(ValueError):
                init_experiment(workdir, {
                    "target": "test",
                    "metric_cmd": "echo 1",
                    "direction": "sideways",
                })

    def test_missing_metric_cmd_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            with self.assertRaises(ValueError):
                init_experiment(workdir, {"target": "test"})

    def test_failed_baseline_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            with self.assertRaises(RuntimeError):
                init_experiment(workdir, {
                    "target": "test",
                    "metric_cmd": "exit 1",
                })


# ---------------------------------------------------------------------------
# run_iteration — direction-aware keep/discard
# ---------------------------------------------------------------------------

class TestRunIteration(unittest.TestCase):

    def _setup_experiment(self, tmp, baseline_cmd, direction="higher", guard_cmd=None):
        workdir = Path(tmp)
        subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)
        init_experiment(workdir, {
            "target": "test",
            "metric_cmd": baseline_cmd,
            "guard_cmd": guard_cmd,
            "budget": 20,
            "direction": direction,
        })
        return workdir

    def test_higher_improved_keeps(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            # Now change metric to return higher value
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 60"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "keep")
            self.assertAlmostEqual(result.metric_value, 60.0)
            self.assertAlmostEqual(result.delta, 10.0)

    def test_higher_regressed_discards(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 40"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "discard")

    def test_lower_improved_keeps(self):
        """Lower direction: metric going DOWN is improvement."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 19.1", direction="lower")
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 15.0"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "keep")
            self.assertAlmostEqual(result.delta, 15.0 - 19.1, places=1)

    def test_lower_regressed_discards(self):
        """Lower direction: metric going UP is regression."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 19.1", direction="lower")
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 25.0"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "discard")

    def test_guard_failure_discards(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher", guard_cmd="false")
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 60"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "discard")
            self.assertFalse(result.guard_passed)
            self.assertIn("guard failed", result.description)

    def test_metric_failure_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "exit 1"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "error")

    def test_no_change_discards(self):
        """Same value as baseline = no improvement = discard."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            # metric_cmd still returns 50 (same as baseline)
            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "discard")

    def test_counters_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 60"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            run_iteration(workdir, iteration=1)
            exp = load_experiment(workdir)
            self.assertEqual(exp["iterations_total"], 1)
            self.assertEqual(exp["iterations_kept"], 1)

    def test_best_value_updated_on_keep(self):
        """best_value in experiment.json tracks the running best, not baseline."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            exp = load_experiment(workdir)
            self.assertAlmostEqual(exp["best_value"], 50.0)

            exp["metric_cmd"] = "echo 60"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))
            run_iteration(workdir, iteration=1)

            exp = load_experiment(workdir)
            self.assertAlmostEqual(exp["best_value"], 60.0)

    def test_best_value_not_updated_on_discard(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")
            # metric returns 40, worse than baseline=50
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 40"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))
            run_iteration(workdir, iteration=1)

            exp = load_experiment(workdir)
            self.assertAlmostEqual(exp["best_value"], 50.0)

    def test_compares_against_best_not_baseline(self):
        """After keeping 60, a value of 55 should be discarded (worse than best=60)
        even though it's better than baseline=50."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 50", direction="higher")

            # First iteration: 50 → 60 (keep, best becomes 60)
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 60"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))
            result1 = run_iteration(workdir, iteration=1)
            self.assertEqual(result1.status, "keep")

            # Second iteration: 55 (better than baseline 50, but worse than best 60)
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 55"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))
            result2 = run_iteration(workdir, iteration=2)
            self.assertEqual(result2.status, "discard")

    def test_best_value_lower_direction(self):
        """For lower-is-better, best_value tracks the lowest value."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_experiment(tmp, "echo 20", direction="lower")

            # Improve: 20 → 15 (keep, best becomes 15)
            exp = load_experiment(workdir)
            exp["metric_cmd"] = "echo 15"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))
            result = run_iteration(workdir, iteration=1)
            self.assertEqual(result.status, "keep")

            exp = load_experiment(workdir)
            self.assertAlmostEqual(exp["best_value"], 15.0)

            # Regress from best: 17 (worse than best=15, even though better than baseline=20)
            exp["metric_cmd"] = "echo 17"
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))
            result2 = run_iteration(workdir, iteration=2)
            self.assertEqual(result2.status, "discard")


# ---------------------------------------------------------------------------
# log_iteration + load_results
# ---------------------------------------------------------------------------

class TestLogging(unittest.TestCase):

    def test_log_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / ".build-loop-auto-research").mkdir(parents=True)

            log_iteration(workdir, IterationResult(
                iteration=0, commit="abc123", metric_value=85.2,
                delta=0.0, status="baseline", description="initial state",
            ))
            log_iteration(workdir, IterationResult(
                iteration=1, commit="def456", metric_value=87.1,
                delta=1.9, status="keep", description="optimized imports",
            ))
            log_iteration(workdir, IterationResult(
                iteration=2, commit="ghi789", metric_value=84.0,
                delta=-1.2, status="discard", description="removed caching",
            ))

            results = load_results(workdir)
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["status"], "baseline")
            self.assertEqual(results[1]["status"], "keep")
            self.assertEqual(results[2]["status"], "discard")
            self.assertAlmostEqual(float(results[1]["metric"]), 87.1, places=1)


# ---------------------------------------------------------------------------
# check_convergence
# ---------------------------------------------------------------------------

class TestConvergence(unittest.TestCase):

    def _setup_with_results(self, tmp, direction, budget, rows):
        """Helper: init experiment then write custom results."""
        workdir = Path(tmp)
        subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)
        init_experiment(workdir, {
            "target": "test",
            "metric_cmd": "echo 50",
            "budget": budget,
            "direction": direction,
        })
        # Write custom rows (overwrite the baseline-only results.tsv)
        for row in rows:
            log_iteration(workdir, row)
        return workdir

    def test_fresh_experiment_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)
            init_experiment(workdir, {
                "target": "test", "metric_cmd": "echo 50", "direction": "higher",
            })
            should_stop, reason = check_convergence(workdir)
            self.assertFalse(should_stop)
            self.assertEqual(reason, "")

    def test_budget_exhausted(self):
        """Budget = total iterations (kept + discarded + errors), not just kept."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=3, rows=[
                IterationResult(1, "a", 51, 1, "keep", "change 1"),
                IterationResult(2, "b", 49, -1, "discard", "bad change"),
                IterationResult(3, "c", 53, 3, "keep", "change 3"),
            ])
            # Set iterations_total to match budget (3 total, not 3 kept)
            exp = load_experiment(workdir)
            exp["iterations_total"] = 3
            (workdir / ".build-loop-auto-research" / "experiment.json").write_text(json.dumps(exp))

            should_stop, reason = check_convergence(workdir)
            self.assertTrue(should_stop)
            self.assertEqual(reason, "budget")

    def test_plateau_five_consecutive_discards(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=20, rows=[
                IterationResult(1, "a", 51, 1, "keep", "good change"),
                IterationResult(2, "b", 49, -1, "discard", "bad 1"),
                IterationResult(3, "c", 49, -1, "discard", "bad 2"),
                IterationResult(4, "d", 49, -1, "discard", "bad 3"),
                IterationResult(5, "e", 49, -1, "discard", "bad 4"),
                IterationResult(6, "f", 49, -1, "discard", "bad 5"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertTrue(should_stop)
            self.assertEqual(reason, "plateau")

    def test_four_discards_continues(self):
        """4 consecutive discards is NOT plateau (need 5)."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=20, rows=[
                IterationResult(1, "a", 49, -1, "discard", "bad 1"),
                IterationResult(2, "b", 49, -1, "discard", "bad 2"),
                IterationResult(3, "c", 49, -1, "discard", "bad 3"),
                IterationResult(4, "d", 49, -1, "discard", "bad 4"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertFalse(should_stop)

    def test_errors_count_as_non_keep_for_plateau(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=20, rows=[
                IterationResult(1, "a", 0, 0, "error", "crash 1"),
                IterationResult(2, "b", 49, -1, "discard", "bad"),
                IterationResult(3, "c", 0, 0, "error", "crash 2"),
                IterationResult(4, "d", 49, -1, "discard", "bad"),
                IterationResult(5, "e", 0, 0, "error", "crash 3"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertTrue(should_stop)
            self.assertEqual(reason, "plateau")

    def test_regression_higher_direction(self):
        """3 kept iterations with declining values = regressing (higher direction)."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=20, rows=[
                IterationResult(1, "a", 55, 5, "keep", "good 1"),
                IterationResult(2, "b", 53, 3, "keep", "ok 2"),
                IterationResult(3, "c", 51, 1, "keep", "worse 3"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertTrue(should_stop)
            self.assertEqual(reason, "regressing")

    def test_regression_lower_direction(self):
        """3 kept iterations with increasing values = regressing (lower direction)."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "lower", budget=20, rows=[
                IterationResult(1, "a", 15, -5, "keep", "good 1"),
                IterationResult(2, "b", 17, -3, "keep", "worse 2"),
                IterationResult(3, "c", 18, -2, "keep", "even worse 3"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertTrue(should_stop)
            self.assertEqual(reason, "regressing")

    def test_no_regression_with_improving_values(self):
        """3 kept iterations with improving values = continue."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=20, rows=[
                IterationResult(1, "a", 51, 1, "keep", "good 1"),
                IterationResult(2, "b", 53, 3, "keep", "better 2"),
                IterationResult(3, "c", 55, 5, "keep", "best 3"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertFalse(should_stop)

    def test_discards_between_keeps_dont_trigger_regression(self):
        """Only kept iterations matter for regression check."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = self._setup_with_results(tmp, "higher", budget=20, rows=[
                IterationResult(1, "a", 55, 5, "keep", "good"),
                IterationResult(2, "b", 49, -1, "discard", "bad"),
                IterationResult(3, "c", 53, 3, "keep", "ok"),
                IterationResult(4, "d", 49, -1, "discard", "bad"),
                IterationResult(5, "e", 51, 1, "keep", "meh"),
            ])
            should_stop, reason = check_convergence(workdir)
            self.assertTrue(should_stop)
            self.assertEqual(reason, "regressing")


# ---------------------------------------------------------------------------
# get_experiment_summary
# ---------------------------------------------------------------------------

class TestExperimentSummary(unittest.TestCase):

    def test_summary_with_mixed_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)
            init_experiment(workdir, {
                "target": "build-time",
                "metric_cmd": "echo 50",
                "direction": "higher",
            })
            log_iteration(workdir, IterationResult(1, "a", 55, 5, "keep", "good change"))
            log_iteration(workdir, IterationResult(2, "b", 48, -2, "discard", "bad change"))
            log_iteration(workdir, IterationResult(3, "c", 0, 0, "error", "crash"))
            log_iteration(workdir, IterationResult(4, "d", 60, 10, "keep", "great change"))

            summary = get_experiment_summary(workdir)
            self.assertEqual(summary["target"], "build-time")
            self.assertEqual(summary["total_iterations"], 4)
            self.assertEqual(summary["kept"], 2)
            self.assertEqual(summary["discarded"], 1)
            self.assertEqual(summary["errors"], 1)
            self.assertAlmostEqual(summary["baseline_value"], 50.0)
            self.assertAlmostEqual(summary["current_best"], 60.0)
            self.assertAlmostEqual(summary["improvement_pct"], 20.0)
            self.assertGreaterEqual(len(summary["top_changes"]), 1)


# ---------------------------------------------------------------------------
# archive_experiment
# ---------------------------------------------------------------------------

class TestArchiveExperiment(unittest.TestCase):

    def test_archive_moves_experiment_and_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)
            init_experiment(workdir, {
                "target": "build-time",
                "metric_cmd": "echo 50",
                "direction": "higher",
            })
            loop_dir = workdir / ".build-loop-auto-research"
            self.assertTrue((loop_dir / "experiment.json").exists())
            self.assertTrue((loop_dir / "results.tsv").exists())

            dest = archive_experiment(workdir)
            self.assertTrue(dest.exists())
            self.assertFalse((loop_dir / "experiment.json").exists())
            self.assertFalse((loop_dir / "results.tsv").exists())
            self.assertIn("build-time", dest.name)

            # results.tsv archived alongside with same base name
            tsv_dest = dest.with_suffix(".tsv")
            self.assertTrue(tsv_dest.exists())

    def test_archive_avoids_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            init_experiment(workdir, {"target": "t", "metric_cmd": "echo 1", "direction": "higher"})
            dest1 = archive_experiment(workdir)

            init_experiment(workdir, {"target": "t", "metric_cmd": "echo 2", "direction": "higher"})
            dest2 = archive_experiment(workdir)

            self.assertNotEqual(dest1, dest2)
            self.assertTrue(dest1.exists())
            self.assertTrue(dest2.exists())


# ---------------------------------------------------------------------------
# detect_autoresearch_targets
# ---------------------------------------------------------------------------

class TestDetectTargets(unittest.TestCase):

    def test_detects_build_from_package_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(json.dumps({
                "scripts": {"build": "next build", "test": "jest"},
            }))
            from scripts.core import scan_repo
            summary = scan_repo(repo)
            targets = detect_autoresearch_targets(repo, summary)
            target_names = [t["target"] for t in targets]
            self.assertIn("optimize-build", target_names)
            self.assertIn("optimize-tests", target_names)

    def test_detects_prompt_from_skills_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "skills" / "my-skill").mkdir(parents=True)
            (repo / "skills" / "my-skill" / "SKILL.md").write_text("---\nname: test\n---\n")
            from scripts.core import scan_repo
            summary = scan_repo(repo)
            targets = detect_autoresearch_targets(repo, summary)
            target_names = [t["target"] for t in targets]
            self.assertIn("optimize-prompt", target_names)

    def test_detects_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docs").mkdir()
            (repo / "docs" / "guide.md").write_text("# Guide\n")
            from scripts.core import scan_repo
            summary = scan_repo(repo)
            targets = detect_autoresearch_targets(repo, summary)
            target_names = [t["target"] for t in targets]
            self.assertIn("optimize-docs", target_names)

    def test_empty_repo_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            from scripts.core import scan_repo
            summary = scan_repo(repo)
            targets = detect_autoresearch_targets(repo, summary)
            self.assertEqual(targets, [])


# ---------------------------------------------------------------------------
# suggest_metric_for_target
# ---------------------------------------------------------------------------

class TestSuggestMetric(unittest.TestCase):

    def test_optimize_build_node(self):
        suggestion = suggest_metric_for_target("optimize-build", {
            "project_kind": "node",
            "validation_commands": {"build": "npm run build", "test": "npm test"},
        })
        self.assertIn("build", suggestion["metric_cmd"].lower())
        self.assertIn("budget", suggestion)

    def test_optimize_tests_python(self):
        suggestion = suggest_metric_for_target("optimize-tests", {
            "project_kind": "python",
            "validation_commands": {"test": "pytest"},
        })
        self.assertIn("budget", suggestion)

    def test_unknown_target_returns_defaults(self):
        suggestion = suggest_metric_for_target("optimize-unknown", {
            "project_kind": "generic",
            "validation_commands": {},
        })
        self.assertIn("budget", suggestion)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):

    def test_metric_runner_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.metric_runner", "--cmd", "echo 42"],
            capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertTrue(data["success"])
        self.assertAlmostEqual(data["value"], 42.0)

    def test_metric_runner_guard_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.metric_runner", "--guard", "true"],
            capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertTrue(data["passed"])

    def test_autoresearch_loop_init_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            result = subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--init", "--workdir", tmp,
                 "--target", "cli-test",
                 "--metric-cmd", "echo 99",
                 "--direction", "higher"],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("Baseline: 99", result.stdout)

    def test_autoresearch_loop_convergence_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--init", "--workdir", tmp,
                 "--target", "test", "--metric-cmd", "echo 50",
                 "--direction", "higher"],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )

            result = subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--check-convergence", "--workdir", tmp],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )
            # Exit code 1 = CONTINUE (not converged)
            self.assertEqual(result.returncode, 1)
            self.assertIn("CONTINUE", result.stdout)

    def test_autoresearch_loop_log_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--init", "--workdir", tmp,
                 "--target", "test", "--metric-cmd", "echo 50",
                 "--direction", "higher"],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )

            result = subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--log", "--workdir", tmp,
                 "--iteration", "1", "--commit", "abc123",
                 "--metric", "55.0", "--delta", "5.0",
                 "--status", "keep", "--description", "test change"],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("Logged iteration 1: keep", result.stdout)

    def test_autoresearch_loop_summary_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--init", "--workdir", tmp,
                 "--target", "test", "--metric-cmd", "echo 50",
                 "--direction", "higher"],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )

            result = subprocess.run(
                [sys.executable, "-m", "scripts.autoresearch_loop",
                 "--summary", "--workdir", tmp],
                capture_output=True, text=True, cwd=str(PLUGIN_ROOT),
            )
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data["target"], "test")
            self.assertAlmostEqual(data["baseline_value"], 50.0)


if __name__ == "__main__":
    unittest.main()
