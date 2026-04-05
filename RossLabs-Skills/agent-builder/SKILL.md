---
name: agent-builder
description: Design, evaluate, and improve agentic harnesses for developer tools, assistants, workflow runtimes, copilots, and AI-powered products. Use when work involves tool-use architecture, permissions, approval gates, workflow state, durability, context and memory systems, evaluation strategy, observability, operator visibility, framework selection, or phased implementation plans for an AI system. Trigger when symptoms imply harness gaps too — stale context, surprising tool calls, sessions that die on crash, missing approval controls, costs spiraling without clear visibility, tool counts crossing ~50, or context windows routinely hitting 92%+ capacity.
author: Tyrone Ross
version: 0.1.0
---

# Agent Builder

## Problem

Most AI products do not break because the model is too weak. They break at the **harness layer**: unclear tool boundaries, missing approval policy, brittle state, sloppy context assembly, no evaluation loop, and weak operator visibility. This skill turns those vague issues into concrete primitives, boundaries, phases, and checks — and grounds every decision in empirical evidence from production systems.

Two complementary bodies of knowledge ship with this skill:

- **`references/methodology/`** — *how to decide*. Prescriptive design and evaluation playbooks covering principles, shapes, tools, state, context, extensibility, UX, and output patterns.
- **`references/catalog/`** — *what exists to choose from*. Empirical inventory of architecture types (I–V), the six-component harness model, frameworks (LangGraph, CrewAI, Pydantic AI, smolagents, DSPy, AutoGen, Bedrock), memory substrates (filesystem, vector, in-context), and lab-specific patterns (Anthropic, OpenAI, Perplexity, Manus, Google, Devin, Cursor).

## Trigger Conditions

Activate when any of the following hold:

- The user is designing or rebuilding an agent, assistant, copilot, or AI workflow
- The request mentions harness architecture, tool-use architecture, tool registries, permission layers, approval gates, workflow state, session persistence, retries, resumability, memory, evals, observability, or multi-agent design
- The user wants to evaluate an existing harness for risks, missing primitives, UX gaps, or operational weakness
- The user is choosing between frameworks (LangGraph vs CrewAI vs Pydantic AI vs smolagents vs DSPy vs AutoGen vs Bedrock), memory substrates, or coordination patterns
- The symptoms point to harness problems even if the word "harness" never appears:
  - tools fire without clear permission
  - sessions fail on crash or long waits
  - context gets stale or bloated (routinely hitting 92%+ capacity)
  - tool count climbs past ~50 and quality drops
  - operators cannot see what happened or why
  - costs, retries, or handoffs are drifting out of control
  - multi-agent setup is producing loops or systemic failures

## Default Posture

1. Bias toward lean, solo-maintainable architecture.
2. Start with a single-agent design unless clear constraints justify more.
3. Require an evaluation plan even for greenfield builds.
4. Prefer explicit system boundaries, permission policy, and workflow state over prompt cleverness.
5. Translate ideas into implementation phases, success criteria, and failure tests.
6. **When justifying multi-agent, cite empirical cost**: single agent ≈ 4× chat tokens, multi-agent ≈ 15× chat tokens, 70%+ of multi-agent failures are systemic (MAST), and only 11% of orgs run production agentic systems (Deloitte 2025). See `references/catalog/01-architecture-taxonomy.md` for sources.

## Step 0 — Gather Context

Before routing, make sure you have enough to work with.

For design work, confirm:
- what product or system the harness serves
- what actions the agent will take
- who the users are
- any known constraints (solo maintenance, existing stack, timeline)

For evaluation work, inspect the harness itself:
- read the codebase, agent config, skills, hooks, or architecture docs
- if evidence is missing, ask for the narrowest missing input and keep moving
- do not evaluate from vibes alone

## Step 1 — Classify The Request

Choose one mode before reading reference files.

### `design`
User is creating a new harness, planning a major rebuild, or asking for architecture, MVP shape, or implementation sequencing.

Default reads: `methodology/01-principles-and-solo-dev-defaults.md`, `methodology/02-harness-shapes-and-architecture.md`, `methodology/08-design-and-build-playbook.md`, `catalog/01-architecture-taxonomy.md`, `references/templates/design-deliverable.md`.

### `evaluation`
User has a harness and wants gaps, risks, missing primitives, UX upgrades, or architectural cleanup.

Default reads: `methodology/01-principles-and-solo-dev-defaults.md`, `methodology/09-evaluation-and-improvement-playbook.md`, `catalog/02-harness-components.md`, `references/templates/evaluation-deliverable.md`.

### `design + evaluation`
User wants a target architecture and a way to verify it, compare it with an existing system, or define acceptance criteria before building.

Default reads: union of the two above.

### `catalog-lookup`
User is asking a factual question about what exists — "which framework", "how does Anthropic's orchestrator work", "what memory substrate", "what's the adoption rate of Type III". Route straight to the catalog. Do **not** dump methodology files for this mode.

Default reads: only the catalog file(s) relevant to the question. Cite the exact file and section. Surface trade-offs. Do not turn framework questions into flame wars.

## Step 2 — Classify The Product Shape

Pick the closest shape and state the assumption if ambiguous:

| Shape (methodology) | Maps to Catalog Type |
|---|---|
| chat assistant | Type I (Augmented Assistant) |
| workflow orchestrator | Type II (Workflow Automaton) or Type III (Orchestrated Team) |
| code agent | Type III (Claude Code / Devin / Cursor patterns) |
| internal copilot | Type I or Type II |
| embedded AI product feature | Type I or Type II |
| hybrid system | Type III+ |

## Step 3 — Read The Smallest Useful Reference Set

Read only the files the request actually needs. This file is the index — do not rely on reference-to-reference chains.

### Methodology (how to decide)
- `methodology/01-principles-and-solo-dev-defaults.md` — almost every request. Defines default decision posture.
- `methodology/02-harness-shapes-and-architecture.md` — choosing system shape, boundaries, lifecycle, transports, deployment.
- `methodology/03-tools-execution-and-permissions.md` — tool registries, tool calling, approval gates, sandboxes, trust tiers.
- `methodology/04-state-sessions-and-durability.md` — sessions, resumability, retries, idempotency, approval waits, long-running work.
- `methodology/05-context-memory-and-evaluation.md` — context windows, retrieval, memory, provenance, evals, replay tests, regression detection.
- `methodology/06-agents-and-extensibility.md` — multi-agent design, plugins, hooks, skills, extension surfaces.
- `methodology/07-ux-observability-and-operations.md` — streaming UX, health checks, logs, analytics, budgets, supportability.
- `methodology/08-design-and-build-playbook.md` — build-ready plan from idea to implementation.
- `methodology/09-evaluation-and-improvement-playbook.md` — findings, missing primitives, upgrade priorities, acceptance tests.
- `methodology/10-example-requests-and-output-patterns.md` — prompt examples, response structure examples.
- `methodology/11-codex-translation-notes.md` — adapting this skill for Codex or other LLM clients; cross-client portability notes.

### Catalog (what exists)
- `catalog/01-architecture-taxonomy.md` — Type I–V classification, adoption rates, 4 debates (single-vs-multi, frameworks-vs-raw, scaffolding-vs-minimal, augment-vs-automate), 10 verified stats, coordination patterns, architecture timeline.
- `catalog/02-harness-components.md` — six-component harness model (prompt / tools / memory / context / error / observability) and its mapping to the methodology topic files.
- `catalog/03-frameworks.md` — LangGraph, CrewAI, Pydantic AI, smolagents, DSPy, AutoGen, Bedrock AgentCore. Decision tree for framework selection.
- `catalog/04-memory-substrates.md` — filesystem-as-memory, vector DB, in-context, COALA framework, Claude Code memory tiers, Voyager skill library, DSPy optimization formats, self-improvement patterns (MCTS, OPRO, PromptBreeder, Gödel Agent).
- `catalog/05-lab-patterns.md` — production architecture patterns from Anthropic, OpenAI, Perplexity, LangChain DeepAgents, Manus, Google ADK, Microsoft AutoGen/Copilot, Meta Llama Stack, DeepSeek, Cohere, Devin, xAI Grok, Cursor, Windsurf.

### Templates (output shapes)
- `references/templates/design-deliverable.md` — use when producing a design output.
- `references/templates/evaluation-deliverable.md` — use when producing an evaluation output.

## Operating Rules

- Convert vague ambitions into concrete harness primitives.
- Push back on unnecessary complexity.
- Treat workflow state, permissions, context assembly, and evaluation as first-class architecture, not cleanup tasks.
- Separate universal harness primitives from product-specific manifestation.
- For evaluation requests, present findings first and improvement sequence second.
- For design requests, include how the design will be tested before calling it done.
- When recommending a framework, memory substrate, or multi-agent pattern, **cite the catalog file** you pulled it from.

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
- direct answer to the factual question
- trade-offs relative to alternatives in the same catalog file
- source citation (`catalog/NN-filename.md § Section`)
- one-line pointer to the methodology file that operationalizes the choice, if applicable

## Final Check Before Responding

- Did you keep the design lean enough for a solo developer unless the request clearly demanded more?
- Did you avoid recommending multi-agent coordination by default?
- Did you include evaluation, not just construction?
- Did you give the user an operational path forward instead of abstract theory?
- If you recommended multi-agent, a framework, or a memory substrate, did you cite the catalog file you pulled it from?
