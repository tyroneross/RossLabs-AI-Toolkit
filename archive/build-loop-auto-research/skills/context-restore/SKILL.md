---
name: context-restore
description: Use when resuming work in a project that may already have a build-loop-auto-research context snapshot or registry fallback trailhead.
---

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context_restore.py --workdir "$PWD" {{user_request}}
```

If a snapshot is restored, present:

- current status
- key decisions
- open items
- unknowns
- important files
- whether the restore came from the current workspace or the registry fallback
- any stale or path-mismatch warning
