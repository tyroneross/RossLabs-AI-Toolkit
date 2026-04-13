# Upstream patches — staged for contribution to claude-plugins-official

## 2026-04-13 · `plugin-dev:hook-development` — flip default from prompt to command hooks

**Upstream repo:** Anthropic's `claude-plugins-official` marketplace (the source of `plugin-dev@claude-plugins-official`).

**Problem:** The shipped `plugin-dev:hook-development` SKILL.md actively recommended `"type": "prompt"` hooks for conditional/gating logic (lines 22, 649, 703, 712 of the prior version). Prompt-type hooks synthesize an LLM response on every matcher hit — they cannot silently "do nothing" when a condition isn't met, because the model always produces a visible `<system-reminder>` explaining why it didn't act. This causes notification spam across every project where the plugin is enabled. Two independent incidents observed in local plugins:

- **2026-03 · `build-loop`** — PostToolUse prompt hook said "if deploy command, warn. Otherwise do nothing." Spammed every Bash call.
- **2026-04-12 · `navgator`** — Four prompt hooks on SessionStart / PreToolUse / PostToolUse (Bash + Write|Edit) / Stop. Drowned out `/build-loop:build-loop` completely.

Both were fixed in the affected plugin. The skill that *taught* the pattern was still shipping it.

### Files

| File | What it is | Where it belongs upstream |
|---|---|---|
| `hook-development.SKILL.md.updated` | Rewritten SKILL.md — command-first recommendation, Anti-Patterns section added, workflow reordered to lint before smoke-test | `skills/hook-development/SKILL.md` in the plugin-dev plugin |
| `hook-linter.sh` | New script — flags prompt-on-PostToolUse/Stop (ERROR), conditional-language prompts (WARN), prompt-on-SessionStart (WARN) | `scripts/hook-linter.sh` in the plugin-dev plugin |

### Submission path

The plugin-dev plugin is published by Anthropic via the default `claude-plugins-official` marketplace. To contribute upstream:

1. Locate the source repo (likely `anthropics/claude-plugins` or a successor). Check `~/.claude/plugins/cache/claude-plugins-official/` for any git remote metadata, or ask in Anthropic's developer channels.
2. Open a PR that drops these two files into `plugins/plugin-dev/`.
3. Reference the incident summary in `feedback_hook_design.md` (in this user's personal memory) for the original bug description.
4. The linter is defensive — running it against Anthropic's own shipped plugins (superpowers, vercel, agent-sdk-dev, etc.) reports `OK` for all 13 files on this machine, so adoption has zero regression risk.

### Local status until upstream merges

These files are **already installed** at:
- `~/.claude/plugins/cache/claude-plugins-official/plugin-dev/unknown/skills/hook-development/SKILL.md`
- `~/.claude/plugins/cache/claude-plugins-official/plugin-dev/unknown/scripts/hook-linter.sh`

They will survive normal use but **may be overwritten** by `/plugin update plugin-dev` or a marketplace resync. If that happens, copy these staged files back:

```bash
cp ~/Desktop/git-folder/RossLabs-AI-Toolkit/archive/upstream-patches/hook-development.SKILL.md.updated \
   ~/.claude/plugins/cache/claude-plugins-official/plugin-dev/unknown/skills/hook-development/SKILL.md
cp ~/Desktop/git-folder/RossLabs-AI-Toolkit/archive/upstream-patches/hook-linter.sh \
   ~/.claude/plugins/cache/claude-plugins-official/plugin-dev/unknown/scripts/hook-linter.sh
chmod +x ~/.claude/plugins/cache/claude-plugins-official/plugin-dev/unknown/scripts/hook-linter.sh
```

### Independent defense (does not depend on upstream merging)

Two hooks in `~/.claude/settings.json` enforce the pattern regardless of the skill's teaching:

- **PreToolUse:Write** → `lint-hooks-json-on-write.sh` — blocks the write (exit 2) if the linter reports ERROR in a file named `hooks.json`.
- **SessionStart** → `session-start-hook-scan.sh` — scans every installed plugin on session start, warns if any are noisy.

The upstream PR is nice-to-have for the broader Claude Code community. Local safety is guaranteed by the two settings.json hooks above.
