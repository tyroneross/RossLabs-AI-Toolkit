---
name: context-snapshot
description: Use when work is about to span sessions, risk compaction, or switch contexts and you want a bookmark-style local snapshot of the current project state.
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context_snapshot.py --workdir "$PWD" {{user_request}}
```

Then summarize:

- snapshot path
- trailhead path
- current task summary
- open items
- whether the restore looks ready for a future session
