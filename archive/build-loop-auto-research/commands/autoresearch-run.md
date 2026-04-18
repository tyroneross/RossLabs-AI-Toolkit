---
name: autoresearch-run
description: "Execute the autoresearch loop using an existing experiment.json configuration."
---

Load the `autoresearch-loop` skill.

1. Check for `.build-loop-auto-research/experiment.json`
2. If not found: tell the user to run `/autoresearch:plan [goal]` first to set up an experiment
3. If found: display the experiment config (target, scope, metric, guard, budget, direction, baseline, best so far) and confirm with the user before starting
4. Run Phase 2 (Loop) only: dispatch the `autoresearch-runner` agent
5. After convergence or budget exhaustion, run Phase 3 (Review): dispatch the `overfitting-reviewer` agent and generate the summary
