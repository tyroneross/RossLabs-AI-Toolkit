# RossLabs AI Toolkit

Developer productivity plugins and skills for AI coding agents across Claude Code, Codex, and AGENTS.md-aware tools.

## Structure

```
plugins/     Self-contained installable packages (GitHub repos)
skills/      Canonical standalone skills (source of truth)
agents/      Agent configurations
archive/     Retired/deprecated items
```

**Plugins** are complete packages — MCP server, hooks, commands, skills, and agent guidance bundled together. Claude Code installs through `.claude-plugin/marketplace.json`; Codex installs through `.agents/plugins/marketplace.json`.

**Skills** are the canonical versions of reusable capabilities. Plugins may bundle their own copies that sync over time.

## Plugins

Browse a clickable version at [rosslabs.ai/toolkit](https://rosslabs.ai/toolkit). Each plugin below links to its repo.

### Core workflow

| Plugin | Version | What it does |
|--------|---------|--------------|
| [build-loop](https://github.com/tyroneross/build-loop) | `0.36.1` | Portable multi-phase build loop for AI coding agents. Gives Claude Code, Codex, and AGENTS.md-aware tools the same disciplined operating loop: assess, plan, execute, review, iterate, then learn. Best for non-trivial features, refactors, migrations, and bug hunts across more than one file. Skip for one-line edits, pure Q&A, or status checks. |
| [navgator](https://github.com/tyroneross/NavGator) | `0.9.0` | Architecture tracking — map dependencies, analyze impact, and visualize your stack before you change it. |
| [ibr](https://github.com/tyroneross/interface-built-right) | `1.4.0` | UI validation — verify implementations match intent with live page scanning and visual regression. |
| [bookmark](https://github.com/tyroneross/bookmark) | `0.3.2` | Session context continuity — auto-save and restore across compactions and terminal closures. |
| [claude-code-debugger](https://github.com/tyroneross/claude-code-debugger) | `1.9.0` | Debugging memory — verdict-based retrieval and pattern extraction from past incidents. |
| [research](https://github.com/tyroneross/research-plugin) | `0.5.1` | Token-efficient research KB — SQLite FTS5, source tier scoring, claim + quantitative verification, bulk ingest, project symlinks. |
| [api-registry](https://github.com/tyroneross/api-registry) | `0.2.0` | Local doc-content cache and authoritative API source registry. Caches docs as dated markdown with a 7-day freshness contract, answers from the local cache first (Context7 is fallback only), and flags docs past the window. Tracks each package's latest-release date and emits an install-cooldown verdict — third-party releases under 7 days old are flagged, the author's own packages exempt. |
| [agent-rally-point](https://github.com/tyroneross/agent-rally-point) | `0.1.3` | Repo-local coordination surface for parallel coding agents. Tracks claims, handoffs, room state, and soft file conflicts across Claude Code, Codex, Gemini, and other hosts. |

### Agents & prompts

| Plugin | Version | What it does |
|--------|---------|--------------|
| [agent-builder](https://github.com/tyroneross/agent-builder) | `0.3.1` | Design and evaluate agentic harnesses — playbooks plus a catalog of architectures, memory substrates, and production patterns. |
| [agent-astronomer](https://github.com/tyroneross/agent-astronomer) | `0.1.0` | Query your local skill, agent, and plugin library from any conversation. Wraps the Agent Astronomer CLI as MCP tools. |
| [prompt-builder](https://github.com/tyroneross/prompt-builder) | `0.1.2` | Prompt Policy Engine — classify, diagnose, rewrite, and score prompts by model tier and deployment. |
| [pyramid-principle](https://github.com/tyroneross/pyramid-principle) | `0.1.2` | Barbara Minto's Pyramid Principle as composable writing skills — short-form, long-form, presentations, and audit. |

### Capture, design, and research

| Plugin | Version | What it does |
|--------|---------|--------------|
| [showcase](https://github.com/tyroneross/showcase) | `0.1.2` | **Deprecated — use `spectra`.** Folded into `spectra` v0.2.0 via `spectra_library`; migrate with `spectra_library action="migrate-from-showcase"`. |
| [spectra](https://github.com/tyroneross/spectra) | `0.3.2` | Content capture + library for marketing — screenshots, videos, usage sequences across web/macOS/iOS/watchOS, with a tagged library (find, gallery, export, migrate-from-showcase). |
| [mockup-gallery](https://github.com/tyroneross/mockup-gallery) | `0.5.1` | Visual mockup review with component-level ratings, auto-save to file, and Claude Code integration. |
| [replit-migrate](https://github.com/tyroneross/replit-migrate) | `0.1.1` | Migrate Replit apps to web (Vercel) or native (iOS/macOS) with encoded lessons from real migrations. |
| [web-scraper](https://github.com/tyroneross/blog-content-scraper) | `0.5.2` | Intelligent web scraper for extracting blog and news content from any website. |

Install any Claude Code plugin after adding the marketplace:

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
| [Judge](./skills/judge) | Score an artifact against a locked 5-dimension rubric with evidence anchoring — deterministic table + aggregate | Standalone |
| [Marketplace Maintenance](./skills/marketplace-maintenance) | Operational rules for maintaining a plugin marketplace — schema, four-surface sync, install-command drift | Standalone |
| [MCP Safe Design](./skills/mcp-safe-design) | Metadata-only MCP tool contract — return references and IDs, never secret values or tokens | Standalone |
| [Publish Packages](./skills/publish-packages) | Publish public npm packages to GitHub Packages (@tyroneross scope) — single-repo + monorepo patterns | Standalone |
| [Test Pattern Library](./skills/test-pattern-library) | Routes "what should I test first" to substrate-specific, risk-prioritized test sequences | Standalone |

## Install

### Claude Code Marketplace

Two steps: add the marketplace, then install plugins from it. In Claude Code's `/plugin marketplace add` dialog, the input format is **`owner/repo`** — do NOT paste the GitHub web URL.

Copy this into the Claude Code marketplace add dialog:

```text
tyroneross/RossLabs-AI-Toolkit
```

```bash
# Add the marketplace — use owner/repo format, not a full URL
claude plugin marketplace add tyroneross/RossLabs-AI-Toolkit

# Install individual plugins (all keys use the @rosslabs-ai-toolkit suffix)

# Core workflow
claude plugin install build-loop@rosslabs-ai-toolkit
claude plugin install navgator@rosslabs-ai-toolkit
claude plugin install ibr@rosslabs-ai-toolkit
claude plugin install bookmark@rosslabs-ai-toolkit
claude plugin install claude-code-debugger@rosslabs-ai-toolkit
claude plugin install research@rosslabs-ai-toolkit
claude plugin install api-registry@rosslabs-ai-toolkit
claude plugin install agent-rally-point@rosslabs-ai-toolkit

# Agents & prompts
claude plugin install agent-builder@rosslabs-ai-toolkit
claude plugin install agent-astronomer@rosslabs-ai-toolkit
claude plugin install prompt-builder@rosslabs-ai-toolkit
claude plugin install pyramid-principle@rosslabs-ai-toolkit

# Capture, design & research
claude plugin install spectra@rosslabs-ai-toolkit
claude plugin install mockup-gallery@rosslabs-ai-toolkit
claude plugin install replit-migrate@rosslabs-ai-toolkit
claude plugin install web-scraper@rosslabs-ai-toolkit
```

> `showcase` is deprecated — install `spectra` instead (showcase folded into `spectra` v0.2.0; migrate with `spectra_library action="migrate-from-showcase"`).

**Common mistake**: pasting `https://github.com/tyroneross/RossLabs-AI-Toolkit/tree/main` into the dialog fails because Claude Code appends `.git/` → `…/tree/main.git/` (404). Use the owner/repo form.

### Codex Marketplace

Codex uses the marketplace mirror at `.agents/plugins/marketplace.json`. With Codex CLI 0.130.0, marketplace operations are under `codex plugin marketplace`:

Copy and run this command in Codex:

```bash
codex plugin marketplace add tyroneross/RossLabs-AI-Toolkit --sparse .agents/plugins
```

```bash
# Add the Codex marketplace from the repo sparse path
codex plugin marketplace add tyroneross/RossLabs-AI-Toolkit --sparse .agents/plugins

# Refresh installed/enabled plugins from that marketplace
codex plugin marketplace upgrade ross-labs-local
```

The Codex marketplace name is `ross-labs-local`; plugin keys use `<plugin>@ross-labs-local`.

### Directly from GitHub for Claude Code

Each plugin is also a standalone installable repo — `claude plugin install tyroneross/<repo>`. The canonical repo for every plugin is linked from the [Plugins](#plugins) table above. A few repo names differ from the plugin name:

```bash
claude plugin install tyroneross/build-loop
claude plugin install tyroneross/interface-built-right   # ibr
claude plugin install tyroneross/NavGator                # navgator
claude plugin install tyroneross/research-plugin         # research
claude plugin install tyroneross/blog-content-scraper    # web-scraper
claude plugin install tyroneross/agent-rally-point
```

## Cross-Platform Agent Support

Each plugin includes an `AGENTS.md` at its root — universal guidance for any AI coding agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI). Codex-capable plugins also include `.codex-plugin/` metadata and the marketplace mirror under `.agents/plugins/`.

## Architecture

Each plugin follows the same structure:

- **MCP server** — How the agent calls tools (structured JSON I/O)
- **Skills** — When/why the agent should call them (auto-trigger via description matching)
- **Hooks** — Lifecycle triggers (session start, file edits, compaction)
- **Commands** — User manual overrides (`/command` shortcuts)

Skills reference MCP tools by name, not CLI commands. The agent calls tools programmatically via MCP rather than shelling out via Bash.

## License

[Apache License 2.0](./LICENSE) © Tyrone Ross, Jr. See [`NOTICE`](./NOTICE) for attribution.
