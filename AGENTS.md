This file provides guidance to AI coding agents (Claude Code, Codex, Cursor, Copilot, Gemini CLI) when working with code in this repository.

## Project snapshot

- Name: RossLabs AI Toolkit
- Purpose: Marketplace and canonical skill registry for Claude Code plugins
- Runtime: Node.js (plugin-sync tooling), Markdown (skills, commands)
- License: MIT

## Structure

```
plugins/       Plugin index — links to self-contained GitHub repos
skills/        Canonical standalone skills (source of truth)
agents/        Agent configurations (index of plugin-bundled agents)
archive/       Retired items
.claude-plugin/marketplace.json   Marketplace manifest (all GitHub sources)
```

## Key concepts

- **Plugins** are self-contained installable packages in their own GitHub repos. Each has an MCP server, hooks, commands, and bundled skills. The `plugins/` directory here is an index, not source code.
- **Skills** are the canonical versions of reusable capabilities. Plugins bundle their own copies that may drift over time. Skills here are the source of truth for syncing.
- **marketplace.json** maps plugin names to GitHub repos. All sources are `"source": "github"` — no npm packages.

## Development commands

- No build step for the toolkit itself
- Plugin-sync tool: `cd plugins/plugin-sync && npm install && npx tsx src/cli.ts status`
- Lint plugin manifests: `cd plugins/plugin-sync && npx tsx src/cli.ts lint`

## Change guidance

- **Adding a plugin**: Add entry to `.claude-plugin/marketplace.json` with `"source": "github"`, add row to `plugins/README.md`
- **Adding a skill**: Create `skills/<name>/SKILL.md` with frontmatter including `canonical: true` and `source-plugin`/`source-repo`
- **Updating a skill**: Edit the canonical version in `skills/`, then sync to the plugin repo's bundled copy
- **Moving to archive**: Move directory to `archive/`, update relevant READMEs
