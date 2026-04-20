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

| Plugin | Description | Install |
|--------|-------------|---------|
| [Bookmark](https://github.com/tyroneross/bookmark) | Session context continuity — auto-save and restore across compactions | `claude plugin install tyroneross/bookmark` |
| [Claude Code Debugger](https://github.com/tyroneross/claude-code-debugger) | Debugging memory — verdict-based retrieval and pattern extraction | `claude plugin install tyroneross/claude-code-debugger` |
| [IBR](https://github.com/tyroneross/interface-built-right) | UI validation — live page scanning and visual regression | `claude plugin install tyroneross/interface-built-right` |
| [NavGator](https://github.com/tyroneross/NavGator) | Architecture tracking — dependency mapping and impact analysis | `claude plugin install tyroneross/NavGator` |
| [Showcase](https://github.com/tyroneross/showcase) | Dev asset capture — screenshots and video for blog/website content | `claude plugin install tyroneross/showcase` |
| [Build Loop](https://github.com/tyroneross/build-loop) | Orchestrated 5-phase dev loop (+ optional Learn) with bridges to NavGator, debugger, logging-tracer and standalone fallbacks | `claude plugin install tyroneross/build-loop` |
| [Prompt Builder](https://github.com/tyroneross/prompt-builder) | Prompt Policy Engine — classify, diagnose, rewrite, and score prompts by model tier and deployment | `claude plugin install tyroneross/prompt-builder` |

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
