# Anthropic's Original Harness Blog — Annotated Notes

Source: [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Anthropic Engineering, 2025).

## What Anthropic actually published

The post documents the harness pattern Anthropic uses internally for agents that work across many context windows. Three durable artifacts (progress log, feature list, git), an initializer/coder split, a session-init protocol.

## Direct quotes that drive this skill's design

- **"Always read `claude-progress.txt` at the start of every session before doing anything else."** This is the source of the SKILL.md "session-init protocol" rule.
- **"The agent edits only the `status` field on a feature."** Source of the edit-status-only contract.
- **"Treat commits as cross-context state."** Source of the "every material change commits" rule.
- **"An initializer agent with a much smaller toolbox can verify the codebase is in a safe state before the coding agent starts."** Source of the initializer/coder split.

## What the post does NOT say (but is consistent with)

- Specific file names — `claude-progress.txt` is one name; you may use `PROGRESS.md` or `.agent-progress.txt` and the pattern works identically.
- Specific feature-list field names — the schema in `templates/feature-list.json` is an idiomatic version. Anthropic's blog uses similar but not identical naming.
- Cross-tool handover (Codex ↔ Claude Code) — this skill extends the pattern to two-tool workflows. The original blog is single-tool.

## What's evolved since the post

- Tool isolation via sub-agents (covered in [Context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)) is the natural complement.
- Skills (this directory) as a way to encode the harness as reusable knowledge — meta but useful.

## Adoption signal

Anthropic's own Claude Code internal usage relies on the harness pattern, per the blog. If you're building a long-running coding agent and ignoring this pattern, you're rebuilding what they already learned and published.

## Citation discipline

When citing the original pattern in a project, link to the blog post directly. Don't paraphrase Anthropic's claims; quote them. This skill is the *operationalization* of the pattern, not the pattern itself.
