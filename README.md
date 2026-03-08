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

Each plugin follows the same structure:

- **MCP server** — How Claude calls tools (structured JSON I/O)
- **Skills** — When/why Claude should call them (auto-trigger via description matching)
- **Hooks** — Lifecycle triggers (session start, file edits, compaction)
- **Commands** — User manual overrides (`/command` shortcuts)

Skills reference MCP tools by name, not CLI commands. This means Claude calls tools programmatically via the MCP protocol rather than shelling out via Bash — faster, quieter, structured output.

## License

MIT
