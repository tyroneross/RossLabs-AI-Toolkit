---
name: autoresearch-status
description: "Show the current autoresearch experiment state, results, and progress."
---

Load the `autoresearch-loop` skill.

1. Check if `.build-loop-auto-research/experiment.json` exists

If it exists:

- Load the experiment config and results
- Run `get_experiment_summary()` from `scripts/autoresearch_loop.py`
- Display:
  - Target, scope, metric command, guard command
  - Budget used / remaining
  - Iterations: total, kept, discarded, errors
  - Baseline → current best → improvement %
  - Top 3 changes by impact
  - Convergence status

If no active experiment exists:

- Say so clearly
- Suggest `/autoresearch [goal]` to start a new experiment or `/autoresearch:plan [goal]` to configure one first

Also check `.build-loop-auto-research/experiments/` for archived experiments. If any exist, list them with their goal and final improvement %.
