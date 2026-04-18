---
name: analyze-history
description: "Analyze Codex archived sessions and infer request / authorization / verification patterns"
argument-hint: "[--history-dir PATH] [--format markdown|json]"
---

Load the `build-loop-auto-research:build-loop-auto-research` skill.

Default to:

- history directory: `~/.codex/archived_sessions`
- format: `markdown`

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_history.py --format markdown
```

If `{{ARGUMENTS}}` includes `--history-dir` or `--format`, pass those values through instead.

Return:

1. the dominant loop pattern
2. the strongest cues by phase
3. confidence and sample-size limits
4. the workflow implications for future build/research commands
