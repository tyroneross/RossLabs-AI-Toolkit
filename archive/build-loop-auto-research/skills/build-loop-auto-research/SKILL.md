---
name: build-loop-auto-research
description: Use for significant multi-step research-and-planning work that benefits from a phase-based loop, orchestration, parallel subagents, validation, iteration, and context continuity.
---

# Build Loop Research — Orchestrated Research And Planning

This skill applies the `build-loop` structure to research-backed software planning. It is for meaningful product, feature, algorithm, prompt, bugfix, and refactor work where planning quality matters. Phase 4 supports two execution modes: standard subagent orchestration for implementation tasks, and autoresearch (autonomous metric-driven iteration) for optimization tasks with measurable metrics.

## Scope Check

Skip the full loop when the request is:

- a tiny copy tweak
- a single-file mechanical change
- a straightforward answer that does not need repo grounding

Use the full loop when the request:

- spans multiple files or systems
- needs repo analysis
- depends on integrations, auth, payments, deployment, or APIs
- needs confidence ranking, iteration, or handoff-quality output

## Phases

| # | Phase | Purpose | Output |
|---|---|---|---|
| 1 | Assess | Understand repo, memory, context, and current state | Assessment summary |
| 2 | Define | State the goal, UX target, constraints, and scoring criteria | Goal + scorecard criteria |
| 3 | Plan | Build the dependency graph, integration map, and verification plan | Plan + integration checkpoints |
| 4 | Execute | Run the research/planning work with orchestrated parallel subagents | Working research packet draft |
| 5 | Validate | Score the packet against the criteria and confidence rules | Scorecard |
| 6 | Iterate | Improve medium/low confidence or failed criteria and re-check | Revised scorecard |
| 7 | Fact Check | Verify docs, integrations, handoffs, and unsupported claims | Fact-check report |
| 8 | Report | Deliver final packet, memory updates, and context trailhead | Final report |

## Core Principles

- Orchestrator-led: a single orchestrating agent owns the loop end to end.
- Diagnose before recommending.
- Plan integration points and handoffs before parallelizing.
- Parallelize only independent work streams.
- Simplicity first: prefer the simplest approach that improves UX without degrading another factor.
- Build with existing app primitives before adding libraries.
- Confidence is operational, not decorative.
- If confidence is `medium` or `low`, iterate.
- If confidence is `high`, still spot-check and re-calibrate.

## State Files

Write loop artifacts into the target repo:

```text
.build-loop-auto-research/
├── goal.md
├── state.json
├── scorecards/
│   └── YYYY-MM-DD-<topic>.md
├── context/
│   ├── trailhead.md
│   ├── current-context.md
│   └── snapshots/
└── lessons/
```

Initialize these with:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_loop.py --workdir "$PWD" --goal "<goal>"
```

## Phase 1: Assess

1. Initialize `.build-loop-auto-research/` if needed.
2. Restore prior context when useful:
   - `context_restore.py`
   - `memory_lookup.py`
3. Run repo grounding:
   - `research_build.py` as the first scaffold for repo work
   - `analyze_history.py` when user-pattern analysis matters
4. Detect:
   - project kind
   - likely entrypoints
   - validation commands
   - integration surfaces
   - deployment/runtime surfaces
5. If the request is issue-like, run memory lookup before fresh investigation.

Output:

- concise assessment summary
- existing context or memory findings
- detected integration surfaces

## Phase 2: Define

Define all of:

1. Goal in one sentence
2. Expected user-experience improvement:
   - faster
   - more accurate
   - smoother
   - simpler
3. Constraints:
   - time
   - risk
   - security
   - performance
   - compatibility
4. 3-5 scoring criteria

Required criteria:

- recommendation improves UX meaningfully
- recommendation does not degrade another UX factor
- recommendation is the simplest viable path
- integration/handoff coverage is adequate when relevant
- evidence quality is sufficient for the claimed confidence

Write the goal to `.build-loop-auto-research/goal.md`.

## Phase 3: Plan

Plan before parallel execution:

1. dependency graph
2. integration points
3. handoff checks
4. documentation checks
5. validation path
6. context continuity trigger points

For APIs, auth, payments, tools, or deployment-sensitive work:

- verify both provider/tool docs and deployment/runtime docs
- examples:
  - Vercel
  - Apple
  - auth providers
  - payment providers

Parallel-safe work streams usually include:

- repo-context scan
- integration review
- evidence/doc review
- memory/lesson review

## Phase 4: Execute

Use the orchestrator and delegate only after the plan exists.

Default agent set:

- `build-loop-auto-research-orchestrator`
- `repo-context-scanner`
- `integration-checker`
- `evidence-checker`
- `memory-curator`
- `issue-investigator` when issue-like
- `autoresearch-runner` when autoresearch-eligible tasks exist
- `overfitting-reviewer` after autoresearch loop completes

Execution rules:

- subagents must have clear ownership
- each subagent returns a compact brief
- the orchestrator merges results
- if work may outlive the current context window, capture a context snapshot

### Autoresearch Execution Mode

When a task has a constrained scope and a mechanical metric, use the autoresearch inner loop instead of standard subagent execution. Load the `autoresearch-loop` skill for the full protocol.

**Identify autoresearch-eligible tasks in Phase 3 (Plan):**
- The task targets a measurable number (build time, coverage %, eval score, benchmark time)
- The scope is constrained to specific files or a glob pattern
- Verification takes <5 minutes per iteration
- Improvement compounds through iteration

**How to invoke:**
1. Run `detect_autoresearch_targets()` from `scripts/core.py` to find candidates
2. For each candidate, define: scope, metric_cmd, guard_cmd, budget, direction
3. Initialize with: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/autoresearch_loop.py --init ...`
4. Dispatch the `autoresearch-runner` agent for the loop
5. After convergence, dispatch the `overfitting-reviewer` agent

**Parallel execution:** autoresearch targets can run alongside standard subagents. Use separate git worktrees for autoresearch targets that modify source files.

**Results feed into Phase 5 (Validate):** autoresearch experiment summaries contribute to the overall scorecard.

## Phase 5: Validate

Score the output against the criteria from Phase 2.

Minimum validation:

- repo grounding is real, not assumed
- docs checks are present when relevant
- integration/handoff checks are present when relevant
- simplicity + UX gate is explicit
- confidence labels are justified

## Phase 6: Iterate

If any criterion fails, or confidence is `medium` / `low`:

1. diagnose what is weak
2. revise only the weak parts
3. re-check confidence
4. re-score

Convergence rules:

- same weak area unchanged after 2 attempts -> escalate
- repeated complexity creep -> simplify scope
- hard stop at 5 iterations

## Phase 7: Fact Check

Run final checks before reporting:

- documentation-backed integration recommendations
- no unsupported claims
- no unnecessary new dependencies
- no missing handoff coverage
- no hidden UX regressions in the recommendation

## Phase 8: Report

Deliver:

- `Bottom line`
- `What I found`
- `Best path`
- `Why this path`
- `Risks / unknowns`
- `Next action`

Also:

- write or update context trailhead if work should continue later
- capture a modular lesson note if multiple iterations were needed
- write a scorecard file under `.build-loop-auto-research/scorecards/`
- autoresearch experiment logs (if autoresearch was used): iterations, kept/reverted, cumulative improvement

## Helpers

Use these supporting utilities:

- `pattern-aware-planning` for concise packet structure
- `context_snapshot.py` and `context_restore.py` for continuity
- `memory_lookup.py` and `capture_memory.py` for modular lesson memory
- `research_build.py` for local repo-first scaffolding

## Output Style

While running the loop, keep progress updates short and structured:

```text
[Phase N: NAME] key result
```

At iteration:

```text
[Iteration N/5] weak area -> fix -> re-check
```
