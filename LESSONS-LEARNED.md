# Lessons Learned — RossLabs Claude Code Plugins

Pattern-level reminders from past incidents. Use this **proactively** when designing, reviewing, or building a new plugin.

## How this file relates to claude-code-debugger

| Use | Tool |
|---|---|
| **Reactive search**: "I'm hitting error X, has this happened before?" | `debugger search "X"` — returns matching JSON incidents |
| **Proactive review**: "Before I ship this plugin, what classes of bugs should I watch for?" | Read this file top to bottom |

They're **not redundant.** Incidents are per-occurrence and searchable by symptom. Lessons are per-pattern and read in full during design. One incident can spawn a lesson; most won't. Only pattern-level generalizations belong here.

## Format

Each entry has:
- **Date** — when the lesson was added
- **Category** — short tag for grouping (e.g. `plugin-manifest`, `hooks`, `skills`, `versioning`, `release-discipline`)
- **Plugins affected** — which plugin(s) exhibited the issue
- **Pattern** — the generalized mistake
- **Correct approach** — what to do instead
- **How to detect** — an audit command or review step that catches the mistake
- **Linked incident** — reference to the claude-code-debugger incident ID if logged there

---

## 2026-04-05 · `plugin.json` path fields must start with `./`

**Category:** `plugin-manifest`
**Plugins affected:** spectra (fixed in `ed20293`), showcase (unfixed), NavGator (unfixed), scraper-app (unfixed)
**Linked incident:** `INC_PLUGIN_MANIFEST_20260405_0200_manifest_paths` (to be logged in claude-code-debugger when MCP is live)
**Authoritative source:** `~/.claude/plugins/cache/claude-plugins-official/plugin-dev/unknown/skills/plugin-structure/references/manifest-reference.md`

### Pattern

Every path field in `.claude-plugin/plugin.json` — `hooks`, `skills`, `commands`, `agents`, `mcpServers` — **must** start with `./`. Two variants of this bug exist:

1. **`../` variant**: points outside the plugin root entirely. Will silently fail to load. Bit us in spectra, showcase, NavGator.
2. **Bare variant** (no `./` prefix): explicitly rejected by the official `plugin-dev:plugin-structure` docs. Bit us in scraper-app.

Neither bare nor `../` paths generate a loud error — the hooks/skills/commands/agents simply don't register, and the user sees "hook count didn't change" in `/reload-plugins` output (if they think to check). The failure is silent and maximally confusing.

### Correct (per plugin-dev:plugin-structure manifest-reference.md)

```json
{
  "hooks": "./hooks/hooks.json",
  "skills": "./skills",
  "commands": "./commands",
  "agents": "./agents",
  "mcpServers": "./.mcp.json"
}
```

### Incorrect — both variants

```json
// ❌ ../ points outside plugin root
{ "hooks": "../hooks/hooks.json" }

// ❌ bare path, no ./ prefix
{ "hooks": "hooks/hooks.json" }
```

### How to detect

Grep all `plugin.json` files in your plugin source dirs for either variant:

```bash
# Variant 1: ../ parent-dir escapes
grep -rn '"\(hooks\|skills\|commands\|mcpServers\|agents\)"\s*:\s*"\.\./' ~/Desktop/git-folder/*/.claude-plugin/plugin.json

# Variant 2: bare paths without ./
grep -rEn '"(hooks|skills|commands|mcpServers|agents)"\s*:\s*"(?!\./)[a-zA-Z_][^"]*"' ~/Desktop/git-folder/*/.claude-plugin/plugin.json
```

### How the bugs hid for so long

All 4 affected plugins are `@local` scope. None of them are in `enabledPlugins` in `~/.claude/settings.json` — so Claude Code never actually tries to load them. The broken manifests sit dormant. The moment any of them is enabled via `/plugin install --local`, hooks/skills/etc would fail to register and the user would be confused by the mismatch between "plugin installed" and "commands not appearing."

### Verification after a fix

1. Enable the plugin: `/plugin install --local <path>`
2. Run `/reload-plugins`
3. Check the reload output's hook/skill/command counts increased by the expected amount
4. If counts didn't change, the path is still wrong

### Prevention — `plugin-sync lint` follow-up

Plugin-sync currently only checks `name` + `version` in `plugin.json`. It should additionally resolve every path field and verify the target file exists under the plugin root. Filed as a follow-up for the next plugin-sync version — would catch this class of bug automatically on every `plugin-sync status` run.

---

<!-- When adding a new lesson, copy the section above and fill in the details. Keep them short — a lesson worth remembering should fit on one screen. Lessons are meant to be read fast during code review. -->
