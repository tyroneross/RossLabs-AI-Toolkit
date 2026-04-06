---
name: agent-builder-codex
description: Designs, evaluates, and improves agentic harnesses for developer tools, assistants, workflow runtimes, copilots, and AI-powered products — including agents built on local and open-source models. Applies when work involves defining or reviewing tool-use architecture, permissions, workflow state, durability, context and memory systems, evaluation strategy, observability, user experience, framework selection, or phased implementation plans for an agentic system.
tags: [agentic-harness, agents, architecture, evaluation, memory, observability, frameworks, multi-agent, local-models, open-source]
category: developer-tools
difficulty: advanced
metadata:
  priority: 6
  pathPatterns:
    - '**/*harness*'
    - '**/*agent-runtime*'
    - '**/*agent_runtime*'
    - '**/*orchestrat*'
    - '**/*workflow*'
    - '**/*tool-registry*'
    - '**/*tool_registry*'
    - '**/*permission*'
    - '**/*approval*'
    - '**/*state-machine*'
    - '**/*state_machine*'
    - '**/*session*'
    - '**/*memory*'
    - '**/*eval*'
    - '**/*retry*'
    - '**/*ollama*'
    - '**/*llama-cpp*'
    - '**/*vllm*'
  importPatterns:
    - '@modelcontextprotocol/*'
    - 'langgraph'
    - '@langchain/*'
    - 'langchain'
    - '@vercel/workflow'
    - 'langchain_ollama'
    - 'langchain-ollama'
    - 'deepagents'
    - 'ollama'
    - 'llama-cpp-python'
    - 'vllm'
    - 'outlines'
    - 'instructor'
    - 'pydantic_ai'
    - 'pydantic-ai'
    - 'smolagents'
    - 'dspy'
    - 'crewai'
    - 'autogen'
    - 'claude_agent_sdk'
    - 'claude-agent-sdk'
  bashPatterns:
    - '\bnpm\s+(install|i|add)\s+[^\n]*(langgraph|langchain|@vercel/workflow|@modelcontextprotocol)\b'
    - '\bpnpm\s+(install|i|add)\s+[^\n]*(langgraph|langchain|@vercel/workflow|@modelcontextprotocol)\b'
    - '\bbun\s+(install|i|add)\s+[^\n]*(langgraph|langchain|@vercel/workflow|@modelcontextprotocol)\b'
    - '\byarn\s+add\s+[^\n]*(langgraph|langchain|@vercel/workflow|@modelcontextprotocol)\b'
    - '\b(pip|uv|uvx)\s+(install|add)\s+[^\n]*(langchain|langgraph|deepagents|ollama|llama-cpp-python|vllm|outlines|instructor|pydantic-ai|smolagents|dspy|crewai|autogen|claude-agent-sdk)\b'
  promptSignals:
    phrases:
      - "agentic harness"
      - "agent harness"
      - "ai harness"
      - "harness architecture"
      - "agent architecture"
      - "agent runtime"
      - "agent workflow runtime"
      - "tool-use architecture"
      - "tool use architecture"
      - "tool calling system"
      - "tool registry"
      - "capability registry"
      - "permission layer"
      - "approval gate"
      - "human-in-the-loop"
      - "workflow state"
      - "session persistence"
      - "durable agent"
      - "durable workflow"
      - "resume after crash"
      - "crash-safe agent"
      - "retry and idempotency"
      - "context assembly"
      - "memory system"
      - "evaluation harness"
      - "replay evals"
      - "agent observability"
      - "operator visibility"
      - "multi-agent architecture"
      - "single agent vs multi-agent"
      - "stop reasons"
      - "local model agent"
      - "open source agent"
      - "ollama agent"
      - "self-hosted agent"
      - "on-device agent"
      - "offline-first agent"
      - "local llm tool calling"
      - "framework selection"
      - "memory substrate"
    allOf:
      - [agent, harness]
      - [tool, registry]
      - [permission, approval]
      - [workflow, state]
      - [resume, retry]
      - [context, memory]
      - [evaluation, harness]
      - [multi-agent, architecture]
      - [durable, agent]
      - [operator, visibility]
      - [local, agent]
      - [open-source, model]
      - [ollama, agent]
    anyOf:
      - "agent orchestration"
      - "approval workflow"
      - "tool-calling runtime"
      - "tool calling runtime"
      - "state machine"
      - "retry policy"
      - "framework for agents"
      - "which framework"
      - "which memory store"
    noneOf: []
    minScore: 6
---

# Agent Builder — Codex Variant

Use this skill as a router for designing, building, and evaluating agentic harnesses.

Read only the files you need. Do not load the entire reference set unless the request genuinely spans multiple subsystems.

Default posture:

- Bias toward lean, solo-maintainable architecture.
- Start with a single-agent design unless clear constraints justify more.
- Require an evaluation plan even for greenfield builds.
- Prefer explicit system boundaries, permission policy, and workflow state over prompt cleverness.
- Translate ideas into implementation phases, success criteria, and failure tests.
- When justifying multi-agent, cite empirical cost: single agent ≈ 4× chat tokens, multi-agent ≈ 15× chat tokens, 70%+ of multi-agent failures are systemic. See `references/catalog/01-architecture-taxonomy.md`.

## Step 1 — Classify The Request

Choose one mode before reading reference files.

### `design`
User is creating a new harness, planning a major rebuild, or asking for architecture, MVP shape, or implementation sequencing.

Default reads: `references/methodology/01-principles-and-solo-dev-defaults.md`, `references/methodology/02-harness-shapes-and-architecture.md`, `references/methodology/08-design-and-build-playbook.md`, `references/catalog/01-architecture-taxonomy.md`, `references/templates/design-deliverable.md`. Add `references/catalog/06-local-and-open-source-models.md` when the target is a local or open-source model.

### `evaluation`
User has a harness and wants gaps, risks, missing primitives, UX upgrades, or architectural cleanup.

Default reads: `references/methodology/01-principles-and-solo-dev-defaults.md`, `references/methodology/09-evaluation-and-improvement-playbook.md`, `references/catalog/02-harness-components.md`, `references/templates/evaluation-deliverable.md`.

### `design + evaluation`
User wants a target architecture and a way to verify it, compare it with an existing system, or define acceptance criteria before building.

Default reads: union of the two above.

### `catalog-lookup`
User is asking a factual question about what exists — "which framework", "how does Anthropic's orchestrator work", "what memory substrate", "what's the best local model tool-calling stack". Route straight to the catalog. Do not dump methodology files.

## Step 2 — Classify The Product Shape

| Shape | Maps to Catalog Type |
|---|---|
| chat assistant | Type I |
| workflow orchestrator | Type II or III |
| code agent | Type III |
| internal copilot | Type I or II |
| embedded AI product feature | Type I or II |
| hybrid | Type III+ |

If the target runs on a local/open-source model, also read `references/catalog/06-local-and-open-source-models.md`.

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
- `references/catalog/01-architecture-taxonomy.md` — Type I–V, stats, debates
- `references/catalog/02-harness-components.md` — six-component harness view
- `references/catalog/03-frameworks.md` — LangGraph / CrewAI / Pydantic AI / smolagents / DSPy / AutoGen / Bedrock
- `references/catalog/04-memory-substrates.md` — filesystem / vector / in-context, COALA, Voyager
- `references/catalog/05-lab-patterns.md` — Anthropic, OpenAI, Perplexity, Manus, Google, Devin, Cursor
- `references/catalog/06-local-and-open-source-models.md` — Ollama / llama.cpp / vLLM, Llama / Qwen / DeepSeek / Mistral, tool-call tiers, framework fit

### Templates
- `references/templates/design-deliverable.md`
- `references/templates/evaluation-deliverable.md`

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
- source citation

## Final Check Before Responding

- Did you keep the design lean enough for a solo developer unless the request clearly demanded more?
- Did you avoid recommending multi-agent coordination by default?
- Did you include evaluation, not just construction?
- Did you give the user an operational path forward instead of abstract theory?
- If you recommended a framework, memory substrate, or multi-agent pattern, did you cite the catalog file?
- If the target is a local model, did you apply the stricter local-model posture from `catalog/06`?
