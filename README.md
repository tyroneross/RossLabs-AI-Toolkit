# RossLabs AI Toolkit

Developer productivity plugins and skills for AI coding agents.

## Structure

```
plugins/     Self-contained installable packages (GitHub repos)
skills/      Canonical standalone skills (source of truth)
agents/      Agent configurations
archive/     Retired/deprecated items
```

**Plugins** are complete packages — MCP server, hooks, commands, skills bundled together. Install one and it works.

**Skills** are the canonical versions of reusable capabilities. Plugins may bundle their own copies that sync over time.

## Plugins

Browse a clickable version at [rosslabs.ai/toolkit](https://rosslabs.ai/toolkit). Each plugin below links to its repo.

### Core workflow

| Plugin | Version | What it does |
|--------|---------|--------------|
| [build-loop](https://github.com/tyroneross/build-loop) | `0.12.10` | Turns big code changes into a checked, repeatable workflow. Five phases: plan, execute, review, iterate, learn. Picks the right model for each task. A strong model plans and reviews. A faster model writes code. A small model does pattern checks. Plans must list every design decision up front. The implementer must say which decisions it made. A lint compares the claim to the actual diff. Work with six or more design decisions auto-routes to the strong model in one pass. A read-only critic runs before full validation. Has an optimize mode that runs multiple tests in a single experiment using Design of Experiments. You can test six variables at once instead of one. The mode plans the test matrix, runs each combination, and tells you which variable actually moved the number. Bundles a debugger memory and a code-base architecture map. Catches the common ways big changes go wrong. The diff drifts from the plan. Quiet design calls slip in. Tests pass but pages do not render. Fake data leaks into production. Use it for features, refactors, migrations, schema changes, anything that touches more than one file. Skip for fixes under about 20 lines. Verifies the production deploy after a push (Vercel): polls the deployment to a terminal state and probes changed routes — an auth-gated 401/403 is healthy, only a 5xx or build error fails. |
| [navgator](https://github.com/tyroneross/NavGator) | `0.8.2` | Architecture tracking — map dependencies, analyze impact, and visualize your stack before you change it. |
| [ibr](https://github.com/tyroneross/interface-built-right) | `1.0.1` | UI validation — verify implementations match intent with live page scanning and visual regression. |
| [bookmark](https://github.com/tyroneross/bookmark) | `0.3.2` | Session context continuity — auto-save and restore across compactions and terminal closures. |
| [claude-code-debugger](https://github.com/tyroneross/claude-code-debugger) | `1.8.1` | Debugging memory — verdict-based retrieval and pattern extraction from past incidents. |
| [research](https://github.com/tyroneross/research-plugin) | `0.5.0` | Token-efficient research KB — SQLite FTS5, source tier scoring, claim + quantitative verification, bulk ingest, project symlinks. |
| [api-registry](https://github.com/tyroneross/api-registry) | `0.1.0` | Local registry of authoritative API/library/tool source URLs — prevents stale-training-data drift when configuring or debugging external services. |

### Agents & prompts

| Plugin | Version | What it does |
|--------|---------|--------------|
| [agent-builder](https://github.com/tyroneross/agent-builder) | `0.1.0` | Design and evaluate agentic harnesses — playbooks plus a catalog of architectures, memory substrates, and production patterns. |
| [agent-astronomer](https://github.com/tyroneross/agent-astronomer) | `0.1.0` | Query your local skill, agent, and plugin library from any conversation. Wraps the Agent Astronomer CLI as MCP tools. |
| [prompt-builder](https://github.com/tyroneross/prompt-builder) | `0.1.1` | Prompt Policy Engine — classify, diagnose, rewrite, and score prompts by model tier and deployment. |
| [pyramid-principle](https://github.com/tyroneross/pyramid-principle) | `0.1.2` | Barbara Minto's Pyramid Principle as composable writing skills — short-form, long-form, presentations, and audit. |

### Capture, design, and research

| Plugin | Version | What it does |
|--------|---------|--------------|
| [showcase](https://github.com/tyroneross/showcase) | `0.1.2` | **Deprecated — use `spectra`.** Folded into `spectra` v0.2.0 via `spectra_library`; migrate with `spectra_library action="migrate-from-showcase"`. |
| [spectra](https://github.com/tyroneross/spectra) | `0.2.1` | Content capture + library for marketing — screenshots, videos, usage sequences across web/macOS/iOS/watchOS, with a tagged library (find, gallery, export, migrate-from-showcase). |
| [mockup-gallery](https://github.com/tyroneross/mockup-gallery) | `0.4.1` | Visual mockup review with component-level ratings, auto-save to file, and Claude Code integration. |
| [replit-migrate](https://github.com/tyroneross/replit-migrate) | `0.1.1` | Migrate Replit apps to web (Vercel) or native (iOS/macOS) with encoded lessons from real migrations. |
| [web-scraper](https://github.com/tyroneross/blog-content-scraper) | `0.5.0` | Intelligent web scraper for extracting blog and news content from any website. |
| [stratagem](https://github.com/tyroneross/stratagem) | `0.1.0` | Market research agent with document processing, web scraping, SEC filings, and financial analysis. |

Install any of them after adding the marketplace:

```bash
claude plugin install <name>@rosslabs-ai-toolkit
```

## Skills

| Skill | Description | Source Plugin |
|-------|-------------|--------------|
| [Agent Builder](https://github.com/tyroneross/agent-builder) | Design and evaluate agentic harnesses | [Standalone repo](https://github.com/tyroneross/agent-builder) |
| [PRD Builder](./skills/prd-builder) | Generate a living, LLM-navigable PRD by answering 3-5 strategic questions | Standalone |
| [Context Continuity](./skills/context-continuity) | Session snapshot and restore logic | Bookmark |
| [Debugging Memory](./skills/debugging-memory) | Verdict-based bug retrieval | Claude Code Debugger |
| [Design Validation](./skills/design-validation) | UI scan and visual regression | IBR |
| [Architecture Scan](./skills/architecture-scan) | Dependency graph and impact analysis | NavGator |
| [Showcase Awareness](./skills/showcase-awareness) | Passive capture suggestions | Showcase |
| [Grounded LLM Prompt](./skills/grounded-llm-prompt) | Composable citation + number-labeling + two-register rule blocks for grounded RAG/audit prompts | Standalone |
| [Multi-Pass LLM Pipeline](./skills/multi-pass-llm-pipeline) | Two-pass LLM pattern (cheap decompose + precision score + deterministic post-process) with auditable methodTrace | Standalone |
| [Agent Tool Design](./skills/agent-tool-design) | Anthropic + OpenAI rules for designing tools an LLM agent will call — naming, params, returns, errors, descriptions | Standalone |
| [Agent Eval Harness](./skills/agent-eval-harness) | 20–50 real-failure tasks, three grader types, pass@k vs pass^k, calibrated LLM judge — Anthropic/OpenAI eval methodology | Standalone |
| [Prompt Cache Shaping](./skills/prompt-cache-shaping) | Static-to-dynamic ordering plus per-vendor cache mechanics (Anthropic cache_control, OpenAI auto-prefix) for 5–10× cost savings | Standalone |
| [Long-Running Agent Harness](./skills/long-running-agent-harness) | progress.txt + feature-list.json + git as cross-context state, initializer/coder split, session-init protocol | Standalone |
| [Reasoning Model Prompting](./skills/reasoning-model-prompting) | Counter-skill for o-series / extended-thinking targets — zero-shot first, no CoT, developer messages, thinking-block echo-back | Standalone |

## Install

### From the marketplace (recommended)

Two steps: add the marketplace, then install plugins from it. In Claude Code's `/plugin marketplace add` dialog, the input format is **`owner/repo`** — do NOT paste the GitHub web URL.

```bash
# Add the marketplace — use owner/repo format, not a full URL
claude plugin marketplace add tyroneross/RossLabs-AI-Toolkit

# Install individual plugins
claude plugin install bookmark@rosslabs-ai-toolkit
claude plugin install claude-code-debugger@rosslabs-ai-toolkit
claude plugin install ibr@rosslabs-ai-toolkit
claude plugin install navgator@rosslabs-ai-toolkit
claude plugin install showcase@rosslabs-ai-toolkit
claude plugin install build-loop@rosslabs-ai-toolkit
claude plugin install agent-builder@rosslabs-ai-toolkit
claude plugin install prompt-builder@rosslabs-ai-toolkit
claude plugin install pyramid-principle@rosslabs-ai-toolkit
claude plugin install research@rosslabs-ai-toolkit
claude plugin install mockup-gallery@rosslabs-ai-toolkit
```

**Common mistake**: pasting `https://github.com/tyroneross/RossLabs-AI-Toolkit/tree/main` into the dialog fails because Claude Code appends `.git/` → `…/tree/main.git/` (404). Use the owner/repo form.

### Directly from GitHub

Each plugin is a standalone installable repo:

```bash
claude plugin install tyroneross/bookmark
claude plugin install tyroneross/claude-code-debugger
claude plugin install tyroneross/interface-built-right
claude plugin install tyroneross/NavGator
claude plugin install tyroneross/showcase
claude plugin install tyroneross/build-loop
claude plugin install tyroneross/agent-builder
claude plugin install tyroneross/prompt-builder
```

## Cross-Platform Agent Support

Each plugin includes an `AGENTS.md` at its root — universal guidance for any AI coding agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI). This covers project structure, development commands, architecture, and change guidance.

## Architecture

Each plugin follows the same structure:

- **MCP server** — How the agent calls tools (structured JSON I/O)
- **Skills** — When/why the agent should call them (auto-trigger via description matching)
- **Hooks** — Lifecycle triggers (session start, file edits, compaction)
- **Commands** — User manual overrides (`/command` shortcuts)

Skills reference MCP tools by name, not CLI commands. The agent calls tools programmatically via MCP rather than shelling out via Bash.

## License

MIT
