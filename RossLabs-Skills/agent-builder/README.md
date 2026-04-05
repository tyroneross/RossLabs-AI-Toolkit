# agent-builder

A comprehensive, modular skill for designing, evaluating, and improving agentic harnesses — the layer around the model that turns a language model into a product.

**Two bodies of knowledge, one skill:**

- **Methodology** — *how to decide*. Principles, shapes, tools, state, context, extensibility, UX, design playbook, evaluation playbook, output patterns, and cross-client portability notes. 11 topic files.
- **Catalog** — *what exists*. Architecture taxonomy (Type I–V), six-component harness model, 7 framework deep dives (LangGraph / CrewAI / Pydantic AI / smolagents / DSPy / AutoGen / Bedrock), memory substrate inventory, 14 production lab patterns (Anthropic, OpenAI, Perplexity, Manus, Google, Devin, Cursor, Windsurf, and more), and dedicated guidance for agents built on local/open-source models (Ollama, llama.cpp, vLLM, Llama, Qwen, DeepSeek, Mistral). 6 catalog files.

Plus output templates, two fully worked examples, and host-specific variants (Anthropic, Codex) with their own auto-activation metadata.

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
├── SKILL.md                            # entry, trigger, router (host-agnostic default)
├── README.md                           # this file
├── LICENSE
├── metadata.json                       # skill catalog metadata (tags, difficulty, attribution)
├── .claude-plugin/
│   └── plugin.json                     # Claude Code marketplace manifest
├── agents/
│   └── openai.yaml                     # OpenAI-host UX + variant routing
├── variants/
│   ├── anthropic/
│   │   └── SKILL.md                    # Anthropic-optimized router (natural-language description)
│   └── codex/
│       └── SKILL.md                    # Codex-optimized router (pathPatterns, importPatterns, promptSignals)
├── examples/
│   ├── design-solo-pr-review-agent.md  # worked design deliverable
│   └── evaluation-research-orchestrator.md  # worked evaluation deliverable
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
    ├── catalog/                        # 6 files — what exists
    │   ├── 01-architecture-taxonomy.md
    │   ├── 02-harness-components.md
    │   ├── 03-frameworks.md
    │   ├── 04-memory-substrates.md
    │   ├── 05-lab-patterns.md
    │   └── 06-local-and-open-source-models.md   # local/OSS model guidance
    └── templates/                      # 2 files — output shapes
        ├── design-deliverable.md
        └── evaluation-deliverable.md
```

### Host variants

The root `SKILL.md` is host-agnostic and works on any Claude Code skill host. Two optimized variants are available:

- **`variants/anthropic/SKILL.md`** — uses the natural-language description format Anthropic hosts prefer for auto-activation. Use this if you're deploying on Claude Code, Claude Desktop, or the Claude API.
- **`variants/codex/SKILL.md`** — includes the `metadata:` frontmatter block with `pathPatterns`, `importPatterns`, `bashPatterns`, and `promptSignals` (scoring system with `minScore: 6`) that Codex-style hosts use to decide when to auto-activate a skill. Use this if you're deploying on Codex or any host that honors the same metadata schema.

To activate a variant as the default, replace the root `SKILL.md` with the variant file. All reference paths in the variants assume they're copied to the skill root.

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

- **Methodology** (`references/methodology/`) — the 11 topic files in this directory are copied from the [**`n-agentic-harnesses`**](https://github.com/NateBJones-Projects/OB1/tree/main/skills/n-agentic-harnesses) agent harness design skill authored by **Jonathan Edwards** (GitHub: [jonathanedwards](https://github.com/jonathanedwards)), published in the OB1 repository owned by **Nate B Jones** ([NateBJones-Projects](https://github.com/NateBJones-Projects)). Nothing else from OB1 was used.
- **Catalog** (`references/catalog/`) — original research from the **RossLabs.ai agentic AI architectures corpus** (April 2026, 368 sources) authored by Tyrone Ross.
- **SKILL.md, templates, examples, variants, and README** — new compositions by Tyrone Ross bridging the two lineages.

## Sources used for the catalog

Anthropic (Claude Code, multi-agent research system), OpenAI (Agents SDK, Deep Research), Perplexity, LangChain (DeepAgents, TerminalBench), Manus AI, Google (ADK, A2A protocol), Microsoft (AutoGen, Semantic Kernel, Copilot), Meta (Llama Stack), DeepSeek, Cohere, Cognition (Devin, Windsurf), Cursor, xAI, Deloitte 2025 Emerging Tech Trends, Gartner (June 2025), MAST arXiv, Stanford AI Index 2025, Chip Huyen's compound error analysis, Phil Schmid, Lance Martin, Karpathy, Andrew Ng, Harrison Chase, Lilian Weng, Voyager, Reflexion, Generative Agents, DSPy optimization, COALA framework, and others.

## License

MIT. Methodology files retain their original authorship attribution in frontmatter.
