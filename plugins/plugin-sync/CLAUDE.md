<!-- Plugin: plugin-sync · Version: 0.1.0 · Source of truth: local (~/Desktop/git-folder/RossLabs-claude-plugins/plugins/plugin-sync) -->
<!-- Before any commit, version bump, or major change, read ./VERSIONING.md. Update it on version bumps. -->

# plugin-sync

Local plugin version tracker. Scans plugin source dirs, cross-references marketplace manifests and the Claude Code registry, reports drift, optionally fixes it.

**Scope:** personal tool for tracking the author's own plugins. Deliberately NOT listed in `marketplace.json` — downstream marketplace users don't see it. On first run, refuses to do anything unless `~/.config/claude-plugins/config.json` exists.

## Entry point

- Shell: `plugin-sync <subcommand>` (wrapper at `~/.local/bin/plugin-sync`)
- Direct: `npx tsx scripts/plugin-sync.ts <subcommand>` from the plugin root
- Via skill: user language like "sync plugins" / "check plugin versions" triggers the `plugin-sync` skill

## Subcommands

`status` · `fix` · `state` · `readme` · `install-hooks` · `uninstall-hooks`

See `./skills/plugin-sync/SKILL.md` for full semantics.

## Dependencies

`zod` (config schema), `commander` (CLI), `tsx` (run TS directly, no build step). Node 20+.

## Not to do

- Don't add this plugin to `marketplace.json` — it's meant to be invisible to anyone cloning the marketplace repo
- Don't call out to the network (no npm/github sync — yet)
- Don't delete registry entries automatically (orphan detection is report-only)
