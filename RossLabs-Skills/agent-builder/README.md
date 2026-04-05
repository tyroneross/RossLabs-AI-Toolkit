# agent-builder

A comprehensive, modular skill for designing, evaluating, and improving agentic harnesses — the layer around the model that turns a language model into a product.

**Two bodies of knowledge, one skill:**

- **Methodology** — *how to decide*. Principles, shapes, tools, state, context, extensibility, UX, design playbook, evaluation playbook, output patterns, and cross-client portability notes. 11 topic files.
- **Catalog** — *what exists*. Architecture taxonomy (Type I–V), six-component harness model, 7 framework deep dives (LangGraph / CrewAI / Pydantic AI / smolagents / DSPy / AutoGen / Bedrock), memory substrate inventory, and 14 production lab patterns (Anthropic, OpenAI, Perplexity, Manus, Google, Devin, Cursor, Windsurf, and more). 5 catalog files.

Plus two output templates — design deliverable and evaluation deliverable — that make the skill's output shape explicit.

## When it activates

Automatic triggers include requests to design or rebuild an agent/assistant/copilot, evaluate an existing harness, compare frameworks, pick a memory substrate, or diagnose symptoms like stale context, surprising tool calls, brittle sessions, missing approval controls, or costs drifting out of control. See the `description` field in `SKILL.md` for the full trigger list.

## Modes

1. `design` — new harness or major rebuild
2. `evaluation` — existing harness needs findings + upgrade path
3. `design + evaluation` — target architecture plus acceptance criteria
4. `catalog-lookup` — factual questions about what frameworks / substrates / patterns exist

## Structure

```
agent-builder/
├── SKILL.md                            # entry, trigger, router
├── README.md                           # this file
├── LICENSE
├── .claude-plugin/
│   └── plugin.json                     # marketplace manifest
└── references/
    ├── methodology/                    # 11 files — how to decide
    │   ├── 01-principles-and-solo-dev-defaults.md
    │   ├── 02-harness-shapes-and-architecture.md
    │   ├── 03-tools-execution-and-permissions.md
    │   ├── 04-state-sessions-and-durability.md
    │   ├── 05-context-memory-and-evaluation.md
    │   ├── 06-agents-and-extensibility.md
    │   ├── 07-ux-observability-and-operations.md
    │   ├── 08-design-and-build-playbook.md
    │   ├── 09-evaluation-and-improvement-playbook.md
    │   ├── 10-example-requests-and-output-patterns.md
    │   └── 11-codex-translation-notes.md
    ├── catalog/                        # 5 files — what exists
    │   ├── 01-architecture-taxonomy.md
    │   ├── 02-harness-components.md
    │   ├── 03-frameworks.md
    │   ├── 04-memory-substrates.md
    │   └── 05-lab-patterns.md
    └── templates/                      # 2 files — output shapes
        ├── design-deliverable.md
        └── evaluation-deliverable.md
```

## Install

**As a Claude Code plugin via the RossLabs marketplace:**
```bash
/plugin marketplace add tyroneross/RossLabs-claude-plugins
/plugin install agent-builder@RossLabs-claude-plugins
```

**As a standalone user skill** (any plugin host or bare Claude Code):
```bash
cp -R RossLabs-Skills/agent-builder ~/.claude/skills/agent-builder
```

**Inside another plugin:** drop `agent-builder/` into that plugin's `skills/` directory and it becomes available wherever the host plugin is installed.

## Design posture

The skill defaults to lean, solo-maintainable, single-agent architecture and requires empirical evidence (not vibes) before escalating to multi-agent. The catalog's verified stats — multi-agent costs 15× chat tokens, 70%+ of multi-agent failures are systemic, only 11% of orgs run production agents — are the anchor. When you push for complexity, the skill will ask for the constraint that justifies it.

## Attribution

- **Methodology inspiration** — the structure and framing of `references/methodology/` (design vs evaluation routing, solo-dev defaults, harness primitives, playbooks) is inspired by the [**`n-agentic-harnesses`**](https://github.com/NateBJones-Projects/OB1/tree/main/skills/n-agentic-harnesses) agent harness design skill by **Nate B Jones**. Nothing else from the OB1 repository was used.
- **Catalog** (`references/catalog/`) is original research from the **RossLabs.ai agentic AI architectures corpus** (April 2026, 368 sources) authored by Tyrone Ross.
- **SKILL.md, templates, and README** are new compositions written for this skill, combining the two lineages above with Tyrone Ross's own harness-design practice.

## Sources used for the catalog

Anthropic (Claude Code, multi-agent research system), OpenAI (Agents SDK, Deep Research), Perplexity, LangChain (DeepAgents, TerminalBench), Manus AI, Google (ADK, A2A protocol), Microsoft (AutoGen, Semantic Kernel, Copilot), Meta (Llama Stack), DeepSeek, Cohere, Cognition (Devin, Windsurf), Cursor, xAI, Deloitte 2025 Emerging Tech Trends, Gartner (June 2025), MAST arXiv, Stanford AI Index 2025, Chip Huyen's compound error analysis, Phil Schmid, Lance Martin, Karpathy, Andrew Ng, Harrison Chase, Lilian Weng, Voyager, Reflexion, Generative Agents, DSPy optimization, COALA framework, and others.

## License

MIT. Methodology files retain their original authorship attribution in frontmatter.
