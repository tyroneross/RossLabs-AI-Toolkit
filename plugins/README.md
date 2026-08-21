# Plugins

Self-contained plugin repositories indexed by the RossLabs AI Toolkit marketplace. The source repos live outside this directory; entries here are mirrors or symlinks used for version checks and marketplace maintenance.

## Registry

| Plugin | Repo | Description | Version |
|--------|------|-------------|---------|
| build-loop | [tyroneross/build-loop](https://github.com/tyroneross/build-loop) | Portable multi-phase build loop for Claude Code, Codex, and AGENTS.md-aware tools | 0.36.1 |
| navgator | [tyroneross/NavGator](https://github.com/tyroneross/NavGator) | Architecture tracking — dependency mapping and impact analysis | 0.9.0 |
| ibr | [tyroneross/interface-built-right](https://github.com/tyroneross/interface-built-right) | UI validation — live page scanning and visual regression | 1.4.0 |
| bookmark | [tyroneross/bookmark](https://github.com/tyroneross/bookmark) | Session context continuity across compactions and terminal closures | 0.3.2 |
| claude-code-debugger | [tyroneross/claude-code-debugger](https://github.com/tyroneross/claude-code-debugger) | Debugging memory and incident pattern retrieval | 1.9.0 |
| research | [tyroneross/research-plugin](https://github.com/tyroneross/research-plugin) | Structured research KB with source scoring and claim verification | 0.6.0 |
| api-registry | [tyroneross/api-registry](https://github.com/tyroneross/api-registry) | Local API documentation registry with freshness checks | 0.2.0 |
| agent-rally-point | [tyroneross/agent-rally-point](https://github.com/tyroneross/agent-rally-point) | Repo-local coordination surface for parallel coding agents | 0.1.3 |
| agent-builder | [tyroneross/agent-builder](https://github.com/tyroneross/agent-builder) | Design and evaluate agentic harnesses | 0.3.1 |
| agent-astronomer | [tyroneross/agent-astronomer](https://github.com/tyroneross/agent-astronomer) | Query the local skill, agent, and plugin library | 0.1.0 |
| prompt-builder | [tyroneross/prompt-builder](https://github.com/tyroneross/prompt-builder) | Prompt Policy Engine for classification, rewrite, and scoring | 0.1.2 |
| pyramid-principle | [tyroneross/pyramid-principle](https://github.com/tyroneross/pyramid-principle) | Pyramid Principle writing skills for short-form, long-form, presentations, and audit | 0.1.2 |
| spectra | [tyroneross/spectra](https://github.com/tyroneross/spectra) | Cross-platform capture, demo, and tagged content library | 0.3.2 |
| mockup-gallery | [tyroneross/mockup-gallery](https://github.com/tyroneross/mockup-gallery) | Visual mockup review with component-level ratings | 0.5.1 |
| replit-migrate | [tyroneross/replit-migrate](https://github.com/tyroneross/replit-migrate) | Migrate Replit apps to web or native targets | 0.1.1 |
| web-scraper | [tyroneross/blog-content-scraper](https://github.com/tyroneross/blog-content-scraper) | Blog and news content extraction | 0.5.2 |
| showcase | [tyroneross/showcase](https://github.com/tyroneross/showcase) | Deprecated — use spectra | 0.1.2 |

## Install

Claude Code marketplace:

```bash
claude plugin marketplace add tyroneross/RossLabs-AI-Toolkit
claude plugin install build-loop@rosslabs-ai-toolkit
```

Codex marketplace:

```bash
codex plugin marketplace add tyroneross/RossLabs-AI-Toolkit --sparse .agents/plugins
codex plugin marketplace upgrade ross-labs-local
```

## Maintenance

Run the reconciler before changing marketplace rows or README versions:

```bash
python3 scripts/marketplace-sync.py --all
python3 scripts/marketplace-sync.py --all --write
```

Local development helpers live in [scripts/](../scripts).
