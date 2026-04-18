---
name: context-restore
description: "Restore the latest bookmark-style local context snapshot for the current project"
argument-hint: "[--list]"
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context_restore.py --workdir "$PWD" {{ARGUMENTS}}
```

If a snapshot is restored, present:

- current status
- key decisions
- open items
- unknowns
- important files
- whether the restore came from the current workspace or a fallback registry pointer
- any stale or path-mismatch warning
