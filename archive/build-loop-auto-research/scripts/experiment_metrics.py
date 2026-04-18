from __future__ import annotations

"""experiment_metrics.py — Compute performance metrics from autoresearch experiments.

Reads archived experiments (experiments/*.json + *.tsv) and active experiments
to produce metrics for evaluating and improving the autoresearch loop prompts.
"""

import json
import sys
from pathlib import Path
from typing import Any

_LOOP_DIR = ".build-loop-auto-research"
_EXPERIMENTS_SUBDIR = "experiments"


def _parse_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    if not lines:
        return []
    headers = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t", maxsplit=len(headers) - 1)
        rows.append(dict(zip(headers, parts)))
    return rows


def compute_metrics(experiment: dict, results: list[dict[str, str]]) -> dict[str, Any]:
    non_baseline = [r for r in results if r.get("status") != "baseline"]
    total = len(non_baseline)
    if total == 0:
        return {
            "target": experiment.get("target", "unnamed"),
            "prompt_version": experiment.get("prompt_version", "unknown"),
            "total_iterations": 0,
            "keep_rate": 0.0,
            "wasted_rate": 0.0,
            "improvement_per_kept": 0.0,
            "convergence_iteration": None,
            "final_improvement_pct": 0.0,
            "hypothesis_diversity": 0.0,
        }

    kept = [r for r in non_baseline if r.get("status") == "keep"]
    discarded = [r for r in non_baseline if r.get("status") == "discard"]
    errors = [r for r in non_baseline if r.get("status") == "error"]

    keep_rate = len(kept) / total if total > 0 else 0.0
    wasted_rate = (len(discarded) + len(errors)) / total if total > 0 else 0.0

    baseline_value = experiment.get("baseline_value", 0.0)
    best_value = experiment.get("best_value", baseline_value)
    final_improvement_pct = 0.0
    if baseline_value != 0:
        final_improvement_pct = round(
            (best_value - baseline_value) / abs(baseline_value) * 100, 2
        )

    total_delta = 0.0
    for r in kept:
        try:
            total_delta += abs(float(r.get("delta", "0")))
        except ValueError:
            pass
    improvement_per_kept = total_delta / len(kept) if kept else 0.0

    # Convergence: find first run of 5 consecutive non-keeps (plateau point)
    convergence_iteration = None
    consecutive_non_keep = 0
    for r in non_baseline:
        if r.get("status") in ("discard", "error"):
            consecutive_non_keep += 1
            if consecutive_non_keep >= 5:
                try:
                    convergence_iteration = int(r["iteration"]) - 4
                except (KeyError, ValueError):
                    pass
                break
        else:
            consecutive_non_keep = 0

    # Hypothesis diversity: unique hypothesis prefixes (first 50 chars) / total
    hypotheses = [r.get("hypothesis", "")[:50] for r in non_baseline if r.get("hypothesis")]
    unique_hypotheses = len(set(hypotheses))
    hypothesis_diversity = unique_hypotheses / len(hypotheses) if hypotheses else 0.0

    return {
        "target": experiment.get("target", "unnamed"),
        "prompt_version": experiment.get("prompt_version", "unknown"),
        "direction": experiment.get("direction", "higher"),
        "total_iterations": total,
        "kept": len(kept),
        "discarded": len(discarded),
        "errors": len(errors),
        "keep_rate": round(keep_rate, 3),
        "wasted_rate": round(wasted_rate, 3),
        "baseline_value": baseline_value,
        "best_value": best_value,
        "final_improvement_pct": final_improvement_pct,
        "improvement_per_kept": round(improvement_per_kept, 4),
        "convergence_iteration": convergence_iteration,
        "hypothesis_diversity": round(hypothesis_diversity, 3),
    }


def collect_all_experiments(workdir: Path) -> list[dict[str, Any]]:
    loop_dir = workdir / _LOOP_DIR
    experiments: list[dict[str, Any]] = []

    # Active experiment
    active_json = loop_dir / "experiment.json"
    active_tsv = loop_dir / "results.tsv"
    if active_json.exists():
        exp = json.loads(active_json.read_text())
        results = _parse_tsv(active_tsv)
        metrics = compute_metrics(exp, results)
        metrics["source"] = "active"
        experiments.append(metrics)

    # Archived experiments
    archive_dir = loop_dir / _EXPERIMENTS_SUBDIR
    if archive_dir.exists():
        for json_path in sorted(archive_dir.glob("*.json")):
            tsv_path = json_path.with_suffix(".tsv")
            exp = json.loads(json_path.read_text())
            results = _parse_tsv(tsv_path)
            metrics = compute_metrics(exp, results)
            metrics["source"] = json_path.name
            experiments.append(metrics)

    return experiments


def format_report(experiments: list[dict[str, Any]]) -> str:
    if not experiments:
        return "No experiments found."

    lines = ["# Autoresearch Performance Report", ""]
    for exp in experiments:
        lines.append(f"## {exp['target']} ({exp['source']})")
        lines.append(f"- Prompt version: `{exp['prompt_version']}`")
        lines.append(f"- Iterations: {exp['total_iterations']} total, {exp.get('kept', 0)} kept")
        lines.append(f"- Keep rate: {exp['keep_rate']:.1%}")
        lines.append(f"- Wasted rate: {exp['wasted_rate']:.1%}")
        lines.append(f"- Baseline → Best: {exp['baseline_value']} → {exp['best_value']} ({exp['final_improvement_pct']:+.1f}%)")
        lines.append(f"- Improvement per kept iteration: {exp['improvement_per_kept']:.4f}")
        if exp['convergence_iteration'] is not None:
            lines.append(f"- Plateau at iteration: {exp['convergence_iteration']}")
        if exp['hypothesis_diversity'] > 0:
            lines.append(f"- Hypothesis diversity: {exp['hypothesis_diversity']:.1%}")
        lines.append("")

    if len(experiments) > 1:
        lines.append("## Cross-Experiment Comparison")
        by_version: dict[str, list[dict]] = {}
        for exp in experiments:
            v = exp["prompt_version"]
            by_version.setdefault(v, []).append(exp)
        for version, exps in by_version.items():
            avg_keep = sum(e["keep_rate"] for e in exps) / len(exps)
            avg_improvement = sum(e["final_improvement_pct"] for e in exps) / len(exps)
            lines.append(f"- `{version}`: {len(exps)} experiments, avg keep rate {avg_keep:.1%}, avg improvement {avg_improvement:+.1f}%")

    return "\n".join(lines)


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Compute autoresearch experiment metrics")
    parser.add_argument("--workdir", default=".", help="target repo root")
    parser.add_argument("--json", action="store_true", help="output raw JSON instead of report")
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    experiments = collect_all_experiments(workdir)

    if args.json:
        print(json.dumps(experiments, indent=2))
    else:
        print(format_report(experiments))


if __name__ == "__main__":
    _cli()
