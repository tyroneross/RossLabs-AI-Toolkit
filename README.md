# RossLabs — Claude Code Plugins

Developer productivity plugins for Claude Code.

## Plugins

| Plugin | Description |
|--------|-------------|
| **[Bookmark](https://github.com/tyroneross/bookmark)** | Session context continuity — auto-save and restore context across compactions and terminal closures |
| **[Claude Code Debugger](https://github.com/tyroneross/claude-code-debugger)** | Debugging memory — learn from past bugs with verdict-based retrieval and pattern extraction |
| **[IBR](https://github.com/tyroneross/interface-built-right)** | UI validation — verify implementations match intent with live page scanning and visual regression |
| **[NavGator](https://github.com/tyroneross/navgator)** | Architecture tracking — map dependencies, analyze impact, and visualize your stack |

## Install

```bash
# Add the marketplace
/plugin marketplace add tyroneross/RossLabs-claude-plugins

# Install individual plugins
/plugin install bookmark@RossLabs
/plugin install claude-code-debugger@RossLabs
/plugin install ibr@RossLabs
/plugin install navgator@RossLabs
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
