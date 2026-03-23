# RossLabs — Claude Code Plugins

Developer productivity plugins for Claude Code.

## Plugins

| Plugin | Description |
|--------|-------------|
| **[Bookmark](https://github.com/tyroneross/bookmark)** | Session context continuity — auto-save and restore context across compactions and terminal closures |
| **[Claude Code Debugger](https://github.com/tyroneross/claude-code-debugger)** | Debugging memory — learn from past bugs with verdict-based retrieval and pattern extraction |
| **[IBR](https://github.com/tyroneross/interface-built-right)** | UI validation — verify implementations match intent with live page scanning and visual regression |
| **[NavGator](https://github.com/tyroneross/NavGator)** | Architecture tracking — map dependencies, analyze impact, and visualize your stack |

## Install

### From the marketplace

```bash
# Add the marketplace
claude plugin marketplace add tyroneross/RossLabs-claude-plugins

# Install individual plugins
claude plugin install bookmark@RossLabs-claude-plugins
claude plugin install claude-code-debugger@RossLabs-claude-plugins
claude plugin install ibr@RossLabs-claude-plugins
claude plugin install navgator@RossLabs-claude-plugins
```

Or from within Claude Code:
```
/plugin marketplace add tyroneross/RossLabs-claude-plugins
/plugin install bookmark@RossLabs-claude-plugins
```

### Directly from GitHub

Each plugin repo is also a standalone installable:
```bash
claude plugin install tyroneross/bookmark
claude plugin install tyroneross/claude-code-debugger
claude plugin install tyroneross/interface-built-right
claude plugin install tyroneross/NavGator
```

### From npm

```bash
npm install -g @tyroneross/bookmark
npm install -g @tyroneross/claude-code-debugger
npm install -g @tyroneross/interface-built-right
npm install -g @tyroneross/navgator
```

## Architecture

Each plugin follows a three-layer architecture where MCP and CLI are both thin interface layers over shared core logic:

```
Interface Layer    MCP Server (AI)  │  CLI (human)
                        ↓           │       ↓
Core Logic         Shared modules (scanner, storage, capture, etc.)
                        ↓
Storage Backend    File I/O (.claude/ or .ibr/)
```

- **MCP server** — How Claude calls tools (structured JSON-RPC, typed responses including images)
- **CLI** — How humans call the same logic (Commander.js, superset of MCP tools)
- **Skills** — When/why Claude should call them (auto-trigger via description matching)
- **Hooks** — Lifecycle triggers (session start, file edits, compaction)
- **Commands** — User manual overrides (`/command` shortcuts)

MCP is the protocol layer — transport (stdio vs HTTP), storage (files vs database), and hosting (local vs cloud) are independent choices. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full assessment.

## License

MIT
