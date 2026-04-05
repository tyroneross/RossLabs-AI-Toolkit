---
name: agent-builder-anthropic
description: >-
  Design, evaluate, and improve agentic harnesses — the orchestration layer
  around LLM-powered tools, agents, assistants, copilots, workflow runtimes,
  and AI-driven product features. Use this skill whenever the user mentions
  building an agentic system, structuring tool use, adding permissions or
  approval gates, designing multi-step AI workflows, managing context windows
  or memory, making agents durable or resumable, evaluating or pressure-testing
  an existing harness, planning phased implementation for an AI product,
  reviewing agent architecture, improving agent UX or observability, choosing
  between frameworks (LangGraph, CrewAI, Pydantic AI, smolagents, DSPy,
  AutoGen, DeepAgents), picking a memory substrate, or asking how to know if
  their harness is actually good. Also use when the user describes problems
  that imply harness gaps — agents doing unexpected things, context getting
  stale, sessions not surviving crashes, tools running without permission, or
  costs spiraling — even if they do not use the word "harness." This variant
  is optimized for Anthropic hosts (Claude Code, Claude Desktop, Claude API)
  and uses natural-language description for auto-activation. Also applies
  when building on local or open-source models (Ollama, llama.cpp, vLLM,
  Llama, Qwen, DeepSeek, Mistral) — see catalog/06.
tags: [agentic-harness, agents, architecture, evaluation, memory, observability, frameworks, multi-agent, local-models, open-source]
category: developer-tools
difficulty: advanced
---

# Agent Builder — Anthropic Variant

Use this skill as a router for designing, building, and evaluating agentic harnesses.

Read only the files you need. Do not load the entire reference set unless the request genuinely spans multiple subsystems.

Default posture:

- Bias toward lean, solo-maintainable architecture.
- Start with a single-agent design unless clear constraints justify more.
- Require an evaluation plan even for greenfield builds.
- Prefer explicit system boundaries, permission policy, and workflow state over prompt cleverness.
- Translate ideas into implementation phases, success criteria, and failure tests.
- When justifying multi-agent, cite empirical cost: single agent ≈ 4× chat tokens, multi-agent ≈ 15× chat tokens, 70%+ of multi-agent failures are systemic. See `references/catalog/01-architecture-taxonomy.md`.

## Step 0 — Gather Context

Before routing, make sure you have enough to work with.

For **design** work, confirm:
- what product or system the harness serves
- what actions the agent will take
- who the users are
- any known constraints (solo dev, existing stack, timeline, local/on-device, hardware limits)

For **evaluation** work, you need the harness itself:
- read the codebase, CLAUDE.md, settings, skills, hooks, architecture docs
- if evidence is missing, ask for the narrowest missing input and keep moving
- do not evaluate from vibes alone

If the request is vague ("help me build an agent" or "is my harness any good"), ask one or two clarifying questions before proceeding. Do not stall the conversation with an interview — get enough to pick a mode and start.

## Step 1 — Classify The Request

Choose one mode before reading reference files.

### `design`
User is creating a new harness, planning a major rebuild, or asking for architecture, MVP shape, or implementation sequencing.

Default reads: `references/methodology/01-principles-and-solo-dev-defaults.md`, `references/methodology/02-harness-shapes-and-architecture.md`, `references/methodology/08-design-and-build-playbook.md`, `references/catalog/01-architecture-taxonomy.md`, `references/templates/design-deliverable.md`. Add `references/catalog/06-local-and-open-source-models.md` when the target is a local/OSS model.

### `evaluation`
User has a harness and wants gaps, risks, missing primitives, UX upgrades, or architectural cleanup.

Default reads: `references/methodology/01-principles-and-solo-dev-defaults.md`, `references/methodology/09-evaluation-and-improvement-playbook.md`, `references/catalog/02-harness-components.md`, `references/templates/evaluation-deliverable.md`.

### `design + evaluation`
User wants a target architecture and a way to verify it, compare it with an existing system, or define acceptance criteria before building.

Default reads: union of the two above.

### `catalog-lookup`
User is asking a factual question about what exists — "which framework", "how does Anthropic's orchestrator work", "what memory substrate", "what's the best local model setup". Route straight to the catalog. Do **not** dump methodology files for this mode.

## Step 2 — Classify The Product Shape

| Shape | Maps to Catalog Type |
|---|---|
| chat assistant | Type I |
| workflow orchestrator | Type II or III |
| code agent | Type III (Claude Code / Devin / Cursor patterns) |
| internal copilot | Type I or II |
| embedded AI product feature | Type I or II |
| hybrid | Type III+ |

If the target runs on a local/open-source model regardless of shape, also read `references/catalog/06-local-and-open-source-models.md`.

## Step 3 — Read The Smallest Useful Reference Set

### Methodology
- `references/methodology/01-principles-and-solo-dev-defaults.md` — default posture
- `references/methodology/02-harness-shapes-and-architecture.md` — shape, boundaries, lifecycle
- `references/methodology/03-tools-execution-and-permissions.md` — tool registries, approvals, trust tiers
- `references/methodology/04-state-sessions-and-durability.md` — resumability, retries, idempotency
- `references/methodology/05-context-memory-and-evaluation.md` — context, retrieval, provenance, evals
- `references/methodology/06-agents-and-extensibility.md` — multi-agent, plugins, hooks, skills
- `references/methodology/07-ux-observability-and-operations.md` — streaming UX, logs, budgets
- `references/methodology/08-design-and-build-playbook.md` — build-ready plan
- `references/methodology/09-evaluation-and-improvement-playbook.md` — findings, upgrade path
- `references/methodology/10-example-requests-and-output-patterns.md` — prompt/output examples
- `references/methodology/11-codex-translation-notes.md` — cross-client portability

### Catalog
- `references/catalog/01-architecture-taxonomy.md` — Type I–V, stats, debates, coordination patterns
- `references/catalog/02-harness-components.md` — six-component harness view
- `references/catalog/03-frameworks.md` — LangGraph, CrewAI, Pydantic AI, smolagents, DSPy, AutoGen, Bedrock
- `references/catalog/04-memory-substrates.md` — filesystem, vector DB, in-context, COALA, Voyager, self-improvement
- `references/catalog/05-lab-patterns.md` — Anthropic, OpenAI, Perplexity, Manus, Google, Devin, Cursor, Windsurf
- `references/catalog/06-local-and-open-source-models.md` — Ollama / llama.cpp / vLLM, Llama / Qwen / DeepSeek / Mistral, tool-call reliability tiers, framework fit, local failure modes

### Templates
- `references/templates/design-deliverable.md` — design output shape
- `references/templates/evaluation-deliverable.md` — evaluation output shape

### Examples
- `examples/design-solo-pr-review-agent.md` — worked design output
- `examples/evaluation-research-orchestrator.md` — worked evaluation output

Do not rely on reference-to-reference chains. This file is the index.

## Operating Rules

- Convert vague ambitions into concrete harness primitives.
- Push back on unnecessary complexity.
- Treat workflow state, permissions, context assembly, and evaluation as first-class architecture, not cleanup tasks.
- Separate universal harness primitives from product-specific manifestation.
- For evaluation requests, present findings first and improvement sequence second.
- For design requests, include how the design will be tested before calling it done.
- When recommending a framework, memory substrate, or multi-agent pattern, cite the catalog file you pulled it from.

## Output Contract

### For `design`
- recommended harness shape
- core primitives and subsystem boundaries
- MVP boundary
- phased implementation plan
- verification and acceptance criteria

### For `evaluation`
- findings ordered by severity or leverage
- missing or weak primitives
- user experience and operational gaps
- prioritized upgrade path
- tests or checks that confirm the fixes

### For `design + evaluation`
- target architecture
- comparison against current or likely failure modes
- implementation phases
- acceptance criteria
- evaluation plan covering regressions, safety, and UX

### For `catalog-lookup`
- direct answer
- trade-offs relative to alternatives
- source citation (`catalog/NN-filename.md § Section`)

## Final Check Before Responding

- Did you keep the design lean enough for a solo developer unless the request clearly demanded more?
- Did you avoid recommending multi-agent coordination by default?
- Did you include evaluation, not just construction?
- Did you give the user an operational path forward instead of abstract theory?
- If you recommended a framework, memory substrate, or multi-agent pattern, did you cite the catalog file?
- If the target is a local model, did you apply the stricter local-model posture from `catalog/06`?
