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

## 2026-04-05 · `plugin.json` `hooks` field must not use `../` paths

**Category:** `plugin-manifest`
**Plugins affected:** spectra (fixed 2026-04-05 in `ed20293`)
**Linked incident:** `INC_PLUGIN_MANIFEST_20260405_0200_hooks_relpath` (to be logged in claude-code-debugger when MCP is live)

### Pattern

The `hooks` field in `.claude-plugin/plugin.json` is resolved **relative to the plugin root** — the directory that contains `.claude-plugin/`, not the `.claude-plugin/` subdirectory itself. Using `../hooks/hooks.json` points outside the plugin root entirely and will silently fail to load hooks when the plugin is installed.

Spectra had `"hooks": "../hooks/hooks.json"` for an unknown amount of time. It wasn't caught because spectra was never installed — the hooks registration would have failed on first `/plugin install` with no user-visible error other than "no hooks appeared in `/reload-plugins` output."

### Correct

```json
{
  "hooks": "./hooks/hooks.json"
}
```

or the equally valid bare form:

```json
{
  "hooks": "hooks/hooks.json"
}
```

### Incorrect (bit us)

```json
{
  "hooks": "../hooks/hooks.json"
}
```

### How to detect

Grep across all your plugin.json files for suspicious parent-dir references:

```bash
grep -rn '"hooks"\s*:\s*"\.\./' ~/Desktop/git-folder/*/.claude-plugin/plugin.json
```

Or more broadly, any field referencing a path above the plugin root:

```bash
grep -rn '"\(hooks\|skills\|commands\|mcpServers\|agents\)"\s*:\s*"\.\./' ~/Desktop/git-folder/*/.claude-plugin/plugin.json
```

### Verification after fix

1. Install the plugin locally: `/plugin install --local <path>`
2. Run `/reload-plugins` and check the output's hook count increases
3. If the count doesn't increase, the hook path is still wrong

### Why this was missed

Plugin-sync's scanner only validates that `plugin.json` has `name` and `version` fields — it doesn't validate that referenced files actually exist at the declared paths. Possible enhancement: add a `plugin-sync lint` subcommand that resolves every path field in every `plugin.json` and flags missing files. (Filed as follow-up, not blocking.)

---

<!-- When adding a new lesson, copy the section above and fill in the details. Keep them short — a lesson worth remembering should fit on one screen. Lessons are meant to be read fast during code review. -->
