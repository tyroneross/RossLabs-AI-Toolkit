---
name: optimize-brief
description: "Tighten a rough request, plan, or prompt into a clearer build brief with verification guidance"
argument-hint: "[rough brief text or --input-file PATH]"
---

Load the `build-loop-auto-research:build-loop-auto-research` skill.

If `{{ARGUMENTS}}` contains `--input-file`, pass it through directly.

Otherwise run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/optimize_brief.py --text "{{ARGUMENTS}}" --format markdown
```

Use the output as the base scaffold, then improve wording and structure without adding fluff.

Apply these gates:

- prefer the simplest viable approach
- prefer existing app primitives before adding libraries
- ensure the recommendation improves UX without degrading another UX factor
- include integration / handoff checks when the request touches APIs, auth, payments, or deployments
- treat `medium` and `low` confidence as a cue to iterate before finalizing

Return:

1. `Bottom line`
2. `Sharpened request`
3. `Missing assumptions`
4. `Suggested mode`
5. `Verification plan`
6. `Handoff prompt`
