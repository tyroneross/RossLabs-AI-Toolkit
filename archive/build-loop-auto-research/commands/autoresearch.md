---
name: autoresearch
description: "Run autonomous metric-driven optimization. Constrained scope + mechanical metric + git commit/revert + fast iteration."
argument-hint: "[goal]"
---

Load the `autoresearch-loop` skill.

{{#if ARGUMENTS}}
Goal: `{{ARGUMENTS}}`

Run all three phases:

1. **Setup** — detect targets, confirm scope, metric command, guard command, and budget, then initialize `experiment.json`
2. **Loop** — iterate: propose → apply → measure → commit or revert, until budget is exhausted or convergence is reached
3. **Review** — summarize results, top changes by impact, and convergence status

When the goal matches a known profile (build time, test coverage, prompt quality, doc quality, runtime performance), suggest the pre-configured target from `profiles.md` before starting.
{{else}}
No goal provided.

1. Check for an existing `.build-loop-auto-research/experiment.json`
2. If found: display current experiment state (target, iterations used, best improvement so far) and ask whether to resume or start a new experiment
3. If not found: ask the user what they want to optimize, then run Phase 1 (Setup) interactively

For custom goals, run Phase 1 interactively to define scope, metric, guard, and budget before starting the loop.
{{/if}}
