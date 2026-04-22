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
| [build-loop](https://github.com/tyroneross/build-loop) | `0.3.0` | Orchestrated 5-phase dev loop — Assess → Plan → Execute → Review → Iterate, plus optional Learn. Opus 4.7 orchestrator with NavGator, debugger, and tracer bridges. |
| [navgator](https://github.com/tyroneross/NavGator) | `0.6.2` | Architecture tracking — map dependencies, analyze impact, and visualize your stack before you change it. |
| [ibr](https://github.com/tyroneross/interface-built-right) | `1.0.1` | UI validation — verify implementations match intent with live page scanning and visual regression. |
| [bookmark](https://github.com/tyroneross/bookmark) | `0.3.2` | Session context continuity — auto-save and restore across compactions and terminal closures. |
| [claude-code-debugger](https://github.com/tyroneross/claude-code-debugger) | `1.8.1` | Debugging memory — verdict-based retrieval and pattern extraction from past incidents. |
| [research](https://github.com/tyroneross/research) | `0.3.2` | Token-efficient research KB — SQLite FTS5, source tier scoring, claim verification, lifecycle management. |
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
| [showcase](https://github.com/tyroneross/showcase) | `0.1.1` | **Deprecated — use `spectra`.** Folded into `spectra` v0.2.0 via `spectra_library`; migrate with `spectra_library action="migrate-from-showcase"`. |
| [spectra](https://github.com/tyroneross/spectra) | `0.2.0` | Content capture + library for marketing — screenshots, videos, usage sequences across web/macOS/iOS/watchOS, with a tagged library (find, gallery, export, migrate-from-showcase). |
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
| [Context Continuity](./skills/context-continuity) | Session snapshot and restore logic | Bookmark |
| [Debugging Memory](./skills/debugging-memory) | Verdict-based bug retrieval | Claude Code Debugger |
| [Design Validation](./skills/design-validation) | UI scan and visual regression | IBR |
| [Architecture Scan](./skills/architecture-scan) | Dependency graph and impact analysis | NavGator |
| [Showcase Awareness](./skills/showcase-awareness) | Passive capture suggestions | Showcase |

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
