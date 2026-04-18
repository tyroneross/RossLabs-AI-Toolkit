---
name: memory-lookup
description: "Search modular lesson memory and return a debugger-style verdict before repeating an investigation"
argument-hint: "[query]"
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory_lookup.py --query "{{ARGUMENTS}}" --format markdown
```

Then tell the user:

- the verdict: `KNOWN_FIX`, `LIKELY_MATCH`, `WEAK_SIGNAL`, or `NO_MATCH`
- whether to reuse prior learning directly or investigate fresh
- the strongest matching lesson notes if any exist
