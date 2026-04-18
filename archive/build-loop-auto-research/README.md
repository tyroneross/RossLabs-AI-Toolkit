# Build Loop Auto Research

`build-loop-auto-research` is a Codex plugin for turning a rough build request into a research packet and a decision-complete implementation plan.

It is optimized for:

- new products
- features
- algorithms
- prompts
- bugfixes
- refactors

## Core Idea

The plugin combines three things:

1. Local repo analysis
2. Optional history-pattern analysis from Codex archives
3. Research-backed planning heuristics drawn from repo-aware retrieval, tool-using agents, self-debugging, generated-test verification, and repo-level exploration

It also enforces a product gate on every recommendation:

- the change must meaningfully improve user experience
- it must not degrade another experience factor
- it must be the simplest viable approach
- it should prefer existing app primitives and local code before adding new libraries
- it should verify integration points, handoffs, and deployment/runtime constraints when external systems are involved

The stable plugin surface is the bundled skills under `skills/`.

## Layout

```text
build-loop-auto-research/
├── .codex-plugin/plugin.json
├── .Codex-plugin/plugin.json
├── .claude-plugin/plugin.json
├── commands/
├── agents/
├── hooks/
├── skills/
│   ├── analyze-history/
│   ├── build-loop-auto-research/
│   ├── context-restore/
│   ├── context-snapshot/
│   ├── memory-lookup/
│   ├── optimize-brief/
│   ├── pattern-aware-planning/
│   └── research-build/
├── memory/
├── scripts/
├── docs/
└── tests/
```

`.codex-plugin/plugin.json` is the canonical manifest. `.Codex-plugin/plugin.json` and `.claude-plugin/plugin.json` are compatibility mirrors only.

## Primary Skills

### `build-loop-auto-research`

Run the full phase-based loop:

- Assess
- Define
- Plan
- Execute
- Validate
- Iterate
- Fact-check
- Report

### `research-build`

Build a structured research packet with:

- `Bottom line`
- `What I found`
- `Best path`
- `Why this path`
- `Risks / unknowns`
- `Next action`

Modes:

- `quick`
- `balanced`
- `max_accuracy`

Artifact modes:

- `research_only`
- `plan_only`
- `research_plus_plan`

### `analyze-history`

Analyze Codex archived sessions from `~/.codex/archived_sessions` or a supplied directory and infer request patterns such as diagnose, authorize, verify, and ship/handoff.

### `optimize-brief`

Take a rough request, plan, or prompt and return:

- a sharper problem statement
- missing assumptions
- suggested optimization mode
- tighter verification guidance
- a reusable handoff prompt

### `context-snapshot`

Create a bookmark-style local context snapshot under the current project's `.build-loop-auto-research/context/` folder before compaction, clearing context, or switching work.

### `context-restore`

Restore the latest local context snapshot from the current project's `.build-loop-auto-research/context/` folder.

### `memory-lookup`

Run a lightweight verdict-gated search over modular lesson memory before repeating a debugging or planning mistake.

## Repo-Local Authoring Artifacts

This repository still contains `commands/`, `agents/`, and `hooks/` directories as local authoring helpers, but the docs-backed plugin interface is the bundled skills. For the current setup notes, see [docs/codex-plugin-setup.md](/Users/tyroneross/Desktop/git-folder/build-loop-auto-research/docs/codex-plugin-setup.md).

## Local Scripts

The plugin uses only Python standard library code.

- `scripts/init_loop.py`
- `scripts/analyze_history.py`
- `scripts/research_build.py`
- `scripts/optimize_brief.py`
- `scripts/capture_memory.py`

These scripts are intended to produce a reliable scaffold quickly. The skills then tell the model how to deepen or refine the output.

## Confidence Handling

Confidence is always ranked as `high`, `medium`, or `low`.

- `high`: spot-check a critical assumption, then re-calibrate if needed
- `medium`: iterate on the weak areas before treating the packet as final
- `low`: gather more repo or documentation evidence and simplify the path before moving forward

## Lessons Learned Memory

The plugin includes a modular lesson-memory area under `memory/`.

- `memory/MEMORY.md` is the index
- `memory/lessons/*.md` stores modular notes
- `scripts/capture_memory.py` appends a new lesson file and updates the index

Use it when:

- something takes multiple iterations
- a recommendation failed because of hidden complexity
- an integration or handoff went wrong
- documentation assumptions were incomplete

## Research Basis

See [docs/research-basis.md](/Users/tyroneross/Desktop/git-folder/build-loop-auto-research/docs/research-basis.md) for the papers and engineering implications that shaped the workflow.

## Validation

Run:

```bash
python3 -m unittest discover -s tests
```

## Install / Load

Use `.codex-plugin/plugin.json` as the canonical install target.

Install through the Codex plugin directory in the app or `/plugins` in the CLI. Do not assume local `--plugin-dir` loading is available in every Codex build.
