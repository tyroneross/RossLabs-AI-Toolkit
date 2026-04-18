---
name: optimize-brief
description: Use when the user has a rough request, draft plan, or prompt that needs to be tightened into a clearer, simpler, more verifiable build brief.
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/optimize_brief.py --text "{{user_request}}" --format markdown
```

If the user supplies a file path instead of inline text, pass it through with `--input-file`.

Then improve wording and structure without adding fluff.

Apply these gates:

- prefer the simplest viable approach
- prefer existing app primitives before adding libraries
- ensure the recommendation improves UX without degrading another UX factor
- include integration and handoff checks when the request touches APIs, auth, payments, or deployments
- iterate if confidence remains `medium` or `low`
