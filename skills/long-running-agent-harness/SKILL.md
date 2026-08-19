---
name: long-running-agent-harness
description: Use when building or operating a coding agent that has to work across multiple context windows or multiple sessions — when one shot won't fit. Encodes Anthropic's published 2025 harness pattern — initializer/coding split, claude-progress.txt + feature-list JSON + git commits as cross-context state, mandatory session-init protocol (read logs → review features → run e2e → start dev server), edit-status-only contract on the feature file. Triggers on "long-running agent", "multi-session agent", "context window keeps filling up", "agent forgets between sessions", "session handoff", "Codex to Claude Code handoff", "Claude Code to Codex handoff", "harness for an agent", "what does the agent read on session start". Not for general harness architecture, permissions, or framework choice — use `agent-builder`. Not for restoring your own current session's context — use `context-continuity`.
author: Tyrone Ross
version: 0.1.0
tags: [agent-harness, session-continuity, long-running, codex, claude-code, handover]
category: agent-engineering
difficulty: intermediate
---

# Long-Running Agent Harness

## Why this skill exists

Anthropic's [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Anthropic Engineering, 2025) documents the harness pattern they use internally when an agent's work spans multiple context windows or sessions. The pattern is concrete enough that you can implement it in a day, and the payoff is enormous: agents that resume cleanly, hand off between tools (Codex ↔ Claude Code), and don't lose state when the context fills up. This skill encodes that pattern.

It pairs with `bookmark` (which handles the *snapshot* mechanics) and `build-loop` (which orchestrates a *single* session). This skill is the *layer above both*: the durable state model that survives context resets and tool switches.

## The three durable artifacts

```
┌─────────────────────────────────────────────────────────────────────────┐
│ claude-progress.txt        Human-readable log of every step. Append-only.│
│                            One paragraph per material event. No history  │
│                            rewrites. The agent's diary.                  │
├─────────────────────────────────────────────────────────────────────────┤
│ feature-list.json           Structured list of features in flight.       │
│                            Status field only — the agent edits status,    │
│                            not the feature definitions.                  │
├─────────────────────────────────────────────────────────────────────────┤
│ git commits                 Code state, atomic, message-rich. Every       │
│                            material change commits with a message that   │
│                            explains the WHY.                              │
└─────────────────────────────────────────────────────────────────────────┘
```

Together, these three answer: *what did we do, what state is each feature in, and what does the code look like?* — for any future session (or any future tool) to read and resume.

## The session-init protocol

When an agent starts (or resumes), it MUST do this in order, before any new work:

```
1. Read claude-progress.txt — last 200 lines minimum, full file if <500 lines.
2. Read feature-list.json — every feature's current status.
3. Run `git log --oneline -30` — confirm the code state matches what progress.txt claims.
4. Run the project's e2e test suite — fail-fast on regressions before adding work.
5. Start the dev server (if applicable) — verify the app boots before changing it.
```

Skipping any step is a violation. Anthropic's published rule: agents that skip session-init repeat work, break invariants, and produce contradictory states across sessions. Make it a hard precondition.

See `templates/init.sh` for a runnable bootstrap.

## The edit-status-only contract

```
{
  "features": [
    {
      "id": "F-31",
      "title": "Embedding catchup CLI + hourly gap health-check",
      "status": "in-progress",          // ← only this field changes
      "owner": "claude-code-session-2",
      "criteria": [
        "CLI invokable with --dry-run",
        "Hourly cron job emits gap report",
        "Test in tests/embedding-catchup.test.ts passes"
      ],
      "started_at": "2026-05-11T14:00Z",
      "completed_at": null
    }
  ]
}
```

The agent's only allowed mutations on `feature-list.json` are:
- Set `status` (`pending` → `in-progress` → `complete` → `verified`).
- Set `owner` (which session/agent claimed it).
- Set `started_at` / `completed_at` timestamps.

The agent does NOT rewrite `title`, `criteria`, or `id`. Those are the contract — set at planning time, immutable during execution. This is what makes the file safe to read across sessions: future agents can trust the features list hasn't been reinterpreted.

See `templates/feature-list.json` for the canonical schema.

## The initializer / coding split

Two distinct agent roles, with different prompts:

| Role | When | Reads | Writes |
|---|---|---|---|
| **Initializer** | Session start | progress.txt + feature-list.json + git log + e2e output + dev-server status | Nothing (read-only) |
| **Coding agent** | After init green | All of the above | Code, progress.txt (append), feature-list.json (status), commits |

The initializer's job is to declare "we're safe to proceed" or "we're not — here's what to fix first." If e2e fails, the coding agent does NOT start; the initializer reports the failure and stops.

Why split: the initializer's prompt can be terse and read-only-tool-restricted. The coding agent has a much bigger toolbox. Mixing them invites the coding agent to "fix" something before it understands the state — a recipe for invariant violation.

See `templates/initializer-prompt.md` and `templates/coding-agent-prompt.md`.

## Progress-log discipline

`claude-progress.txt` is append-only, one paragraph per material event. A material event is:

- A feature's status changes.
- A test suite goes red → green or green → red.
- A commit lands.
- An external action happens (deploy, migration, db_push).
- A blocker is identified (and what's needed to unblock).

NOT material events: every tool call, every file read, every grep. Those go in the session transcript, not the progress log.

Format:
```
[2026-05-11 14:32] (claude-code) F-31 — embedding catchup CLI shipped.
Tests in tests/embedding-catchup.test.ts pass. Hourly cron deployed to Railway.
Status: in-progress → complete. Next: F-31-verify will run the gap report
against production data and bump status to verified.

[2026-05-11 14:51] (claude-code) Blocker on F-32 — recall@10 stuck at 0.817
versus 0.91 target. Root cause: 50 of 121 corpus docs are 58-char stubs from
Cloudflare CAPTCHA. Path A (re-crawl) is 1-2 days. Path B (lower target to
0.80) is 1 LoC. Decision pending user. Status: in-progress → blocked.
```

Timestamps + actor + feature + change + reasoning. ~3–5 lines max per event.

## Anti-patterns

- **Rewriting history in `claude-progress.txt`**. The log is the trail; don't rewrite the past. If something was wrong, append a correction entry.
- **Restating `criteria` in `feature-list.json` to match what you actually built**. The feature drift is a planning issue, not a recording issue. If criteria need to change, add a new feature with the new criteria and mark the old one `superseded`.
- **Skipping session-init "because it's fast"**. The cost of a bad assumption compounds over a session. Init is 60 seconds; debugging an invariant violation is 60 minutes.
- **Treating commit messages as cosmetic**. The commits are part of the state; their messages explain *why* to a future agent. Write them like you're writing to a stranger.
- **Living entirely in the agent's context window**. The harness exists because windows fill. If your agent isn't using progress.txt and feature-list.json, you don't have a harness — you have a single-session agent that will lose its work.

## The Codex ↔ Claude Code handover

This pattern's biggest payoff is cross-tool handoff. The user described it explicitly in `decision-doctor-cc`'s `docs/handover/2026-05-1*.md` series (hand-rolled). Encoded:

1. Outgoing agent (e.g., Codex) writes a final progress.txt entry: "Handing off to claude-code. Next action: <X>. Blockers: <Y>. Owned files: <list>."
2. Outgoing agent leaves feature-list.json in a clean state — every feature has a non-stale `status` and `owner`.
3. Incoming agent (Claude Code) runs session-init. The init protocol works identically; the tools differ, the artifacts don't.
4. Incoming agent updates `owner` on any feature it picks up.

Same protocol, two tools. The artifacts are the contract.

## When NOT to use this skill

- One-shot tasks that fit in a single context window.
- Pure conversational chat agents (no code state to preserve).
- Demos / prototypes where speed > continuity.
- Agents that don't write code (research assistants — different harness pattern, closer to `bookmark`).

## Cross-references

- **`bookmark`** plugin — handles the *snapshot* mechanics around compaction. This skill is the *durable artifact* layer that survives compaction AND tool switches. Both work together.
- **`build-loop`** — orchestrates a single session. This skill is the protocol between sessions.
- **`codex` plugin** — for invoking Codex from Claude Code. When you do, the outgoing agent should write the handover entry per this skill.

## Files in this skill

```
long-running-agent-harness/
├── SKILL.md                                  (this file)
├── templates/
│   ├── claude-progress.txt                   (starter file with format example)
│   ├── feature-list.json                     (canonical schema)
│   ├── init.sh                                (runnable session-init bootstrap)
│   ├── initializer-prompt.md                 (system prompt for the initializer agent)
│   └── coding-agent-prompt.md                 (system prompt for the coding agent)
└── references/
    └── anthropic-harness-original.md         (notes from Anthropic's original blog post)
```

## Sources

- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (T1, 2025)
- [Anthropic — Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (T1, 2025) — companion piece on the just-in-time retrieval / compaction / sub-agent isolation patterns.
