---
name: autoresearch-loop
description: Autonomous metric-driven optimization loop. Constrained scope + mechanical metric + git commit/revert + fast iteration. Use for build optimization, test coverage, prompt tuning, doc quality, or runtime performance.
---

# Autoresearch Loop — Autonomous Metric-Driven Optimization

Karpathy's autoresearch pattern adapted for app development: define a mechanical metric, constrain the scope, and iterate autonomously — committing improvements and reverting regressions — until convergence. Three phases: Setup → Loop → Review.

## Scope Check

Use autoresearch when:
- There is a clear mechanical metric (a number you can measure via shell command)
- The scope is constrained (specific files or a glob pattern)
- Verification takes <5 minutes per iteration
- Improvement compounds through iteration

Skip when:
- The metric requires human judgment
- Changes require cross-system coordination
- The task is a one-shot implementation, not iterative optimization

See `profiles.md` for pre-configured targets (build, tests, prompts, docs, perf).

## Phase 1: SETUP (Opus)

The highest-leverage phase. Wrong metric = Goodhart's Law: the loop optimizes the proxy, not the goal.

Define:
1. `target` — what to optimize (plain name, e.g. "build time")
2. `scope` — which files can change (glob or explicit list)
3. `metric_cmd` — shell command that outputs a single number
4. `guard_cmd` — shell command that must exit 0 for any change to be accepted
5. `budget` — max iterations (default 20)
6. `direction` — `"lower"` or `"higher"` (which direction is improvement?)

Auto-detection: when the user provides only a goal, use `detect_autoresearch_targets()` from `scripts/core.py` to propose candidates.

Initialize the experiment:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/autoresearch_loop.py \
  --init \
  --workdir "$PWD" \
  --target "<name>" \
  --scope "<glob>" \
  --metric-cmd "<cmd>" \
  --guard-cmd "<cmd>" \
  --budget <N> \
  --direction "<lower|higher>"
```

Output: `.build-loop-auto-research/experiment.json` with baseline measurement recorded.

## Phase 2: LOOP (Sonnet)

Autonomous iteration. No human gates. Dispatch the `autoresearch-runner` agent, which executes this cycle:

```
0. Read experiment.json + results.tsv + git log of experiment: commits
1. Hypothesize: propose ONE atomic change based on experiment history
2. Edit: modify only files matching the scope constraint
3. Commit: git commit -m "experiment: <description>"
4. Measure: run metric_cmd via metric_runner.py
5. Guard: run guard_cmd via metric_runner.py
6. Decide (compare against running best, not baseline):
   - metric improved over best_value AND guard passes  → KEEP, update best_value
   - metric worse than best OR guard fails             → git revert HEAD
   - crash/error                       → fix (max 2 tries), else git revert HEAD
7. Log: append to results.tsv via autoresearch_loop.py --log
8. Convergence check via autoresearch_loop.py --check-convergence
   - 5 consecutive discards → plateau, stop
   - metric trending worse over 3 kept iterations → regressing, stop
   - budget exhausted → stop
9. If not converged → go to step 1
```

Key rules:
- ONE change per iteration (atomic, reviewable)
- Read full experiment history before each hypothesis (never repeat a failed approach)
- Respect scope constraint strictly — touch only files matching the glob
- All commits use the `experiment:` prefix for easy identification and cleanup

## Phase 3: REVIEW (Opus + Sonnet)

Check for overfitting. Report findings.

**Step 1 — Dispatch `overfitting-reviewer` agent (Sonnet, read-only):**

Check whether the loop:
- Removed safety features, approval gates, or validation
- Replaced robust implementations with fragile shortcuts
- Optimized for test-harness quirks rather than real-world quality
- Produced improvements that are test-specific and non-generalizable

**Step 2 — Generate summary (Opus):**
- Iterations run, kept vs reverted, cumulative improvement
- Top 3 most impactful changes (with git diffs)
- Overfitting warnings (if any)
- Recommendation: accept all / cherry-pick / discard

**Step 3 — Archive:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/autoresearch_loop.py --archive --workdir "$PWD"
```

## Model Tiering

| Component | Model | Why |
|-----------|-------|-----|
| Setup | Opus | Wrong metric = Goodhart. Highest-leverage decision |
| Hypothesis generation | Sonnet (pinned) | Creative but constrained. High volume. ~5x cheaper than Opus |
| Metric/guard execution | Bash (no LLM) | Pure command execution |
| Keep/revert decision | Deterministic | Numeric comparison — no model needed |
| Overfitting review | Sonnet (read-only) | Pattern matching across diffs |
| Final report | Opus | Judgment on what to accept |

## Convergence Rules

- 5 consecutive discards → plateau (easy wins exhausted, stop)
- Metric trending worse over 3 kept iterations → regressing (changes are counterproductive, stop)
- Budget exhausted (total iterations, not just kept) → hard stop
- Same hypothesis attempted twice → skip it, read history more carefully

## Branch Isolation

By default, experiments run on the current branch with `experiment:` prefix commits. For cleanup or rollback, filter by prefix: `git log --oneline --grep="experiment:"`.

**Recommended for production repos:** create a dedicated branch before starting.
```bash
git checkout -b autoresearch/<target>
# run the loop
# review results, then merge or discard the branch
```

When invoked from build-loop Phase 4, autoresearch targets that modify source files should use separate git worktrees to avoid conflicts with standard subagents.

## Integration with build-loop-auto-research

When invoked from build-loop Phase 4:
- Phase 3 (Plan) identifies autoresearch-eligible tasks
- Phase 4 dispatches `autoresearch-runner` alongside standard subagents
- Autoresearch results feed into Phase 5 (Validate) for overall scoring

When invoked standalone via `/autoresearch`:
- Run all three phases directly
- Use the same `.build-loop-auto-research/` state directory as build-loop

## State Files

```text
.build-loop-auto-research/
├── experiment.json       # Active config: scope, metric, guard, budget, direction, baseline, best_value
├── results.tsv           # Iteration log: iteration, metric, kept/reverted, hypothesis
└── experiments/          # Archived pairs: YYYY-MM-DD-<target>.json + .tsv
```

## Progress Format

While running, emit structured one-liners:

```text
[Setup] baseline=4.2s scope=src/**/*.ts budget=20 direction=lower
[Loop 1/20] hypothesis: tree-shake unused icons → metric=3.9s → KEPT (+0.3s)
[Loop 2/20] hypothesis: inline critical CSS → metric=4.1s → REVERTED (worse)
[Converged] plateau after 5 discards. Best: 3.4s (-19%). 12 iterations, 7 kept.
[Review] overfitting-reviewer: no safety regressions found. Recommendation: accept all.
```
