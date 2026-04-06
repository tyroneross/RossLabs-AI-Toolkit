# Plugins

Self-contained Claude Code plugins. Each plugin repo includes everything needed to install and run: MCP server, skills, hooks, commands, and AGENTS.md.

## Registry

| Plugin | Repo | Description | Version |
|--------|------|-------------|---------|
| Bookmark | [tyroneross/bookmark](https://github.com/tyroneross/bookmark) | Session context continuity — auto-save and restore across compactions | 0.3.2 |
| Claude Code Debugger | [tyroneross/claude-code-debugger](https://github.com/tyroneross/claude-code-debugger) | Debugging memory — verdict-based retrieval and pattern extraction | 1.8.0 |
| IBR | [tyroneross/interface-built-right](https://github.com/tyroneross/interface-built-right) | UI validation — live page scanning and visual regression | 0.7.0 |
| NavGator | [tyroneross/NavGator](https://github.com/tyroneross/NavGator) | Architecture tracking — dependency mapping and impact analysis | 0.6.1 |
| Showcase | [tyroneross/showcase](https://github.com/tyroneross/showcase) | Dev asset capture — screenshots and video for blog/website content | 0.1.0 |

## Install

```bash
# From marketplace
claude plugin install bookmark@RossLabs-AI-Toolkit

# Directly from GitHub
claude plugin install tyroneross/bookmark
```

## Local Development Plugins

| Plugin | Description |
|--------|-------------|
| [plugin-sync](./plugin-sync) | Local plugin version tracker — drift detection and auto-sync |
| [build-loop](./build-loop) | Build loop automation |
