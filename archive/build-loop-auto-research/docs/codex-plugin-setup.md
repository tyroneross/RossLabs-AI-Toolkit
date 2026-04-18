# Codex Plugin Setup Notes

This file captures the current Codex-documentation-backed setup assumptions for `build-loop-auto-research`.

## Canonical plugin entrypoint

- Canonical manifest: `.codex-plugin/plugin.json`
- `.Codex-plugin/plugin.json` is kept only as a legacy compatibility mirror for environments that still look for the older path casing.

## Stable plugin surface

Current Codex plugin documentation describes plugins as bundling:

- skills
- app integrations
- MCP servers

For that reason, the stable user-facing surface for this plugin is the bundled skills under `skills/`.

## Invocation model

- Ask for the task directly and let Codex choose the right installed plugin/skill when possible.
- To invoke a specific skill explicitly, use Codex skill invocation rather than relying on repo-local slash-command behavior.

## Hooks and subagents

Official Codex docs place hooks and custom subagents in repo or user `.codex/` config, not in the plugin manifest:

- hooks: `~/.codex/hooks.json` or `<repo>/.codex/hooks.json`
- subagents: `.codex/agents/*.toml`

The `hooks/`, `agents/`, and `commands/` directories in this repo are retained as local authoring artifacts, but they are not treated as the canonical plugin interface.

## Installation approach

- Use the Codex plugin directory in the app or `/plugins` in the CLI.
- Do not assume local `--plugin-dir` loading is available in every Codex build.
