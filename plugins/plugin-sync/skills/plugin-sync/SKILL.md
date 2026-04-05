---
name: plugin-sync
description: Use when the user asks to "sync plugins", "check plugin versions", "which plugins are drifting", "refresh marketplace versions", "update the plugin readme", "install plugin-sync hooks", "lint my plugin manifests", "validate plugin.json paths", "plugin-sync status", or similar. Tool tracks local Claude Code plugins across source repos, marketplace manifests, and Claude Code's installed_plugins.json registry; detects drift and optionally fixes it; also lints plugin.json path fields against the manifest reference rules. Personal tool scoped to its author's machine — bail silently if ~/.config/claude-plugins/config.json is missing.
---

# plugin-sync

Local plugin version tracker and drift fixer. Scans source plugin dirs, cross-references with marketplace manifests and the Claude Code registry, reports mismatches, and optionally writes corrections.

## When this skill fires

User language that should trigger this skill:
- "sync plugins" / "check plugin versions"
- "which plugins are drifting" / "any plugin drift"
- "refresh marketplace versions" / "update the plugin readme"
- "install plugin-sync hooks" / "turn on auto-sync hooks"
- "plugin-sync status" / direct CLI invocations

## Preconditions

This tool is **scoped to its author's machine**. If `~/.config/claude-plugins/config.json` does not exist, the `plugin-sync` command will exit with a clear error. In that case, tell the user:

> This is a personal tool scoped to @tyroneross. To enable it, copy
> `${CLAUDE_PLUGIN_ROOT}/../config.example.json` to `~/.config/claude-plugins/config.json`
> and edit the `searchRoots` to point at where you keep your plugin source dirs.

Do **not** invent a config on someone else's behalf.

## Commands

The tool is installed at `~/.local/bin/plugin-sync` (wrapper around `tsx` running the TypeScript CLI inside this plugin). Available subcommands:

| Command | Purpose |
|---|---|
| `plugin-sync status` | Read-only drift report — exits 0 if clean, 1 if drift found |
| `plugin-sync status --json` | Same, machine-readable output |
| `plugin-sync fix` | Update marketplace manifests and registry to match source versions |
| `plugin-sync fix --quiet` | Same, but silent when nothing changed (used by git hooks) |
| `plugin-sync state` | Write `~/.config/claude-plugins/state.json` snapshot (dashboard input) |
| `plugin-sync readme` | Rewrite the `<!-- plugin-sync:start --> / <!-- plugin-sync:end -->` section of each configured README |
| `plugin-sync lint` | Validate plugin.json path fields (hooks/skills/commands/agents/mcpServers) — catches `../`, bare paths, missing targets |
| `plugin-sync lint --json` | Same, machine-readable output |
| `plugin-sync install-hooks` | Install `.git/hooks/post-commit` in every source plugin repo (auto-runs `fix` on version bumps) |
| `plugin-sync uninstall-hooks` | Remove plugin-sync-installed hooks |

## Typical flow when user asks to check drift

1. Run `plugin-sync status` via the Bash tool
2. Show the table output verbatim (or summarize if long)
3. If drift found (exit 1), ask the user whether to run `plugin-sync fix`
4. On confirmation, run `plugin-sync fix` and show its output
5. Offer to also run `plugin-sync readme` if any marketplace manifests changed (so the README table reflects the fix)

## Typical flow when user asks to install auto-sync

1. Run `plugin-sync install-hooks`
2. Show which plugin repos got a hook and which were skipped (e.g., existing user hooks that refuse to be overwritten)
3. Explain: the hook lives in `.git/hooks/post-commit`, which is never committed, so it stays machine-local

## Interpreting statuses

- `✓ in sync` — source version matches all marketplace + registry entries
- `○ orphan` — plugin source found but not referenced anywhere (informational; not an error)
- `✗ drift` — source version differs from at least one marketplace/registry version, OR a registry entry's installPath doesn't exist on disk
- **Orphan registry entries** — third-party or uninstalled plugins still referenced by `installed_plugins.json`; the tool never modifies these automatically

## What the tool will NOT do

- Delete anything (beyond overwriting marketplace.json and installed_plugins.json version strings)
- Touch third-party plugin caches (vercel, superpowers, etc.)
- Write to any source plugin's repo (the post-commit hook installer is the one exception, and it only writes to `.git/hooks/` which is never committed)
- Modify files outside the configured `marketplaceManifests`, `marketplaceReadmes`, or `claudeCodeRegistry` paths
- Auto-publish to npm, GitHub, or anywhere else

## Backups

Every fix run creates timestamped backups (`.bak-<epoch>`) of every modified file, in the same directory as the original. If a fix goes wrong, restoring is a single `mv` command.

## Scope

Designed for a solo developer managing 5–50+ local plugins. Zero dependencies on cloud services. No telemetry. No network calls.
