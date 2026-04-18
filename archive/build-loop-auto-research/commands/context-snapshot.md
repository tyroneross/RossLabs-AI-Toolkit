---
name: context-snapshot
description: "Capture a bookmark-style local context snapshot for the current project"
argument-hint: "[--summary TEXT] [--status TEXT] [--decision TEXT] [--open-item TEXT] [--unknown TEXT] [--file PATH]"
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context_snapshot.py --workdir "$PWD" {{ARGUMENTS}}
```

Then summarize for the user:

- snapshot path
- trailhead path
- current task summary
- open items
- whether this is ready for restore after compaction or a fresh session
