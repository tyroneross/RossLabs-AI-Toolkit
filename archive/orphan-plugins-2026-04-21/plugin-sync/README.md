# plugin-sync

Local plugin version tracker for Claude Code plugins. Scans plugin source dirs, cross-references marketplace manifests and the Claude Code registry, reports drift, optionally fixes it.

> **Scope:** personal tool, not published to the marketplace. Refuses to run without `~/.config/claude-plugins/config.json`, so downstream marketplace users (who don't have that config) see it as a no-op if they ever install it.

## Quick start

```bash
# 1. Install dependencies (one-time, inside the plugin dir)
cd ~/Desktop/git-folder/RossLabs-AI-Toolkit/plugins/plugin-sync
npm install

# 2. Copy the example config to the XDG location and edit it
mkdir -p ~/.config/claude-plugins
cp config.example.json ~/.config/claude-plugins/config.json
$EDITOR ~/.config/claude-plugins/config.json

# 3. Install the global wrapper
cat > ~/.local/bin/plugin-sync <<'EOF'
#!/usr/bin/env bash
set -e
PLUGIN_SYNC_DIR="${PLUGIN_SYNC_DIR:-$HOME/Desktop/git-folder/RossLabs-AI-Toolkit/plugins/plugin-sync}"
cd "$PLUGIN_SYNC_DIR"
exec npx --no-install tsx scripts/plugin-sync.ts "$@"
EOF
chmod +x ~/.local/bin/plugin-sync

# 4. Run it
plugin-sync status
```

## Subcommands

| Command | Purpose |
|---|---|
| `plugin-sync status` | Drift report (read-only). Exit 0 if clean, 1 if drift found. |
| `plugin-sync status --json` | Same, machine-readable. |
| `plugin-sync status --source-set-only` | Drift report scoped to canonical source repos. Ignores unrelated orphan registry entries. |
| `plugin-sync codex` | Audit Codex installability across canonical source plugins. |
| `plugin-sync codex --json` | Same, machine-readable. |
| `plugin-sync fix` | Update marketplace.json + installed_plugins.json to match source versions. Creates backups. |
| `plugin-sync fix --quiet` | Same, silent when nothing changed. Used by git hooks. |
| `plugin-sync state` | Write dashboard snapshot to `~/.config/claude-plugins/state.json`. |
| `plugin-sync readme` | Update the `<!-- plugin-sync:start --> / <!-- plugin-sync:end -->` section of each configured README. |
| `plugin-sync lint` | Validate plugin.json path fields against the manifest reference rules. Catches `../` escapes, bare paths missing `./`, and paths whose target doesn't exist. |
| `plugin-sync install-hooks` | Install `.git/hooks/post-commit` in every source plugin repo. |
| `plugin-sync uninstall-hooks` | Remove plugin-sync-installed hooks. |

## Config schema

`~/.config/claude-plugins/config.json`:

```json
{
  "searchRoots": ["~/Desktop/git-folder"],
  "excludePaths": [
    "~/Desktop/git-folder/RossLabs-AI-Toolkit/plugins",
    "~/Desktop/git-folder/RossLabs-AI-Toolkit/skills",
    "~/Desktop/git-folder/RossLabs-AI-Toolkit/archive",
    "~/Desktop/git-folder/secrets-vault/plugins"
  ],
  "marketplaceManifests": [
    "~/Desktop/git-folder/RossLabs-AI-Toolkit/.claude-plugin/marketplace.json"
  ],
  "marketplaceReadmes": [
    "~/Desktop/git-folder/RossLabs-AI-Toolkit/README.md"
  ],
  "claudeCodeRegistry": "~/.claude/plugins/installed_plugins.json",
  "stateFile": "~/.config/claude-plugins/state.json",
  "exclude": ["node_modules", ".git", "dist", ".next", "coverage", ".worktrees"]
}
```

- `searchRoots` — dirs to walk looking for `.claude-plugin/plugin.json`. Auto-discovery; no per-plugin config needed.
- `excludePaths` — absolute or `~/` paths to exclude entirely from search-root walks. Use this to remove toolkit mirrors and archive copies so only canonical source repos are scanned.
- `marketplaceManifests` — marketplace.json files to keep in sync with source versions.
- `marketplaceReadmes` — README files with sentinel sections to regenerate.
- `claudeCodeRegistry` — path to Claude Code's `installed_plugins.json`.
- `stateFile` — where `plugin-sync state` writes its snapshot.
- `exclude` — directory names to skip during search-root walks.

## What it detects

- **Drift**: source plugin.json version differs from marketplace.json or registry versions
- **Duplicate plugin names**: multiple canonical source roots advertise the same plugin name; the CLI now fails fast instead of choosing one implicitly
- **Ghost paths**: registry entries whose `installPath` doesn't exist on disk
- **Orphan source plugins**: dirs with `.claude-plugin/plugin.json` not referenced in any marketplace or the registry
- **Orphan registry entries**: registry entries for plugins not in the search roots (usually third-party installs; reported but never modified)

If you want a source-of-truth view for just the canonical plugin set, use `plugin-sync status --source-set-only`. This keeps the default status behavior unchanged for Claude registry drift workflows, but removes noise from unrelated installed plugins.

## Codex Audit

`plugin-sync codex` is a read-only audit focused on additive Codex packaging. It checks:

- canonical `.codex-plugin/plugin.json` exists
- Codex manifest `name`, `version`, and `description` stay aligned with `.claude-plugin/plugin.json`
- the package root exposes a Codex-usable surface through skills and/or MCP
- the package root README mentions Codex installation or usage

This audit does **not** modify Codex manifests. `plugin-sync fix` remains Claude-focused and only syncs marketplace + registry versions.

## What it will NOT do

- Delete files (beyond overwriting version strings in marketplace.json and installed_plugins.json)
- Touch third-party plugin caches (vercel, superpowers, etc.)
- Modify source plugin repos (the post-commit hook installer only writes to `.git/hooks/`, which is never committed)
- Call any network services

## Stack

TypeScript · Node 20+ · `tsx` (run TS directly, no build step) · `zod` (config schema) · `commander` (CLI). Zero runtime dependencies beyond those three.

## Design

- **Filesystem auto-discovery** — scales from 5 to 50+ plugins with no per-plugin config. You add a new plugin repo under `searchRoots` and it's picked up automatically.
- **Canonical-source filtering** — `excludePaths` keeps toolkit mirrors, archived plugins, and other non-authoritative copies out of the canonical source set.
- **Fail-fast duplicate detection** — duplicate plugin names now stop the run before `fix` can update the wrong marketplace entry.
- **Atomic writes** — every config mutation goes through `tmp + rename` so a crash mid-write can't corrupt JSON files. Every write also creates a timestamped backup.
- **Idempotent** — running `fix` twice in a row is safe; the second run detects no drift and exits cleanly.
- **Fail-loud on config errors** — zod schema rejects typos immediately with a precise error message.
- **Never touches third-party state** — the drift engine treats any registry entry not matching a source plugin as "report only."
