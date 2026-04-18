---
name: memory-lookup
description: Use before repeating an investigation, debugging loop, or multi-iteration fix so Codex can check modular lessons learned and decide whether a known fix or likely match already exists.
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory_lookup.py --query "{{user_request}}" --format markdown
```

Then tell the user:

- the verdict: `KNOWN_FIX`, `LIKELY_MATCH`, `WEAK_SIGNAL`, or `NO_MATCH`
- whether to reuse prior learning directly or investigate fresh
- the strongest matching lesson notes if any exist
