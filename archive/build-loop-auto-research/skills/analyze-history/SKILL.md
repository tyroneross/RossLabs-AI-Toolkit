---
name: analyze-history
description: Use when the user wants to analyze prior Codex archived sessions to infer request, authorization, verification, and handoff patterns and use those patterns to improve future build workflows.
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_history.py --format markdown
```

If the user specifies a different history directory or wants JSON, pass those values through.

Return:

1. the dominant loop pattern
2. the strongest cues by phase
3. sample-size and confidence limits
4. implications for future build and research flows
