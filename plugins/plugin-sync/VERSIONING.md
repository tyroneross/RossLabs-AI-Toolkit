# plugin-sync — Versioning & Source of Truth

## Current

- **Version:** 0.1.0
- **Source of truth:** Local dev (`~/Desktop/git-folder/RossLabs-claude-plugins/plugins/plugin-sync`)
- **Also available at:** nowhere (deliberately not published — personal tool)
- **Claude Code registry entry:** `plugin-sync@local` (after manual install)

## Key changes in 0.1.0

- Initial release: TypeScript CLI with `status`, `fix`, `state`, `readme`, `install-hooks`, `uninstall-hooks` subcommands
- Zod config schema at `~/.config/claude-plugins/config.json`
- Auto-managed README sentinels (`<!-- plugin-sync:start --> / <!-- plugin-sync:end -->`)
- Git post-commit hooks install/uninstall
- Scales from 5 to 50+ plugins via filesystem auto-discovery (searchRoots walk)

## Where to look for the latest version

| Source | Location | Notes |
|---|---|---|
| **Authoritative** | `~/Desktop/git-folder/RossLabs-claude-plugins/plugins/plugin-sync/.claude-plugin/plugin.json` | Local dev — canonical |
| Marketplace | NOT listed (intentional) | This plugin is hidden from downstream marketplace users |
| npm | Not published | Personal tool |

## Release discipline (enforce before committing a version bump)

1. Bump `version` in `.claude-plugin/plugin.json`
2. Bump the version in `package.json` to match
3. Update the version stamp in `CLAUDE.md` (line 1 HTML comment)
4. Update this file's `Current` section + add an entry to `Version history`
5. Typecheck (`npm run typecheck`) must pass
6. Run `plugin-sync status` against your own config as a smoke test
7. Commit all four files (`plugin.json`, `package.json`, `CLAUDE.md`, `VERSIONING.md`) in one commit

This plugin is not in the marketplace and has no npm/cache mirrors — the drift surface is much smaller than the other plugins. But the discipline keeps the version stamp trustworthy in case you ever flip it to a published tool.

## Version history

- **0.1.0** (2026-04-05): Initial release
