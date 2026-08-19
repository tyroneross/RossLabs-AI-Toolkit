---
name: agent-tool-design
description: Use when designing the surface of a tool that an LLM agent will call — function declarations, MCP server methods, OpenAI function-calling schemas, Anthropic tool_use definitions, or Agent SDK tools. Encodes Anthropic and OpenAI's published 2025–2026 guidance — namespaced names (service_resource_verb), semantically specific parameters (user_id over user), signal-dense return formats with a response_format knob, prompt-engineered error strings that guide the model toward the fix, and the anti-pattern of wrapping every API endpoint 1:1. Triggers on "design a tool for an agent", "write a function declaration", "MCP server tool", "function calling schema", "tool_use definition", "Agents SDK tool", "the agent keeps calling my tool wrong", "the agent loops on a tool error", "list-all is blowing up context", "tool descriptions". Not for the secrets/credential-safety contract on an MCP server's responses — use `mcp-safe-design`. Cross-vendor; vendor wire-format notes in references/.
author: Tyrone Ross
version: 0.1.0
tags: [agent, tools, mcp, function-calling, openai-agents, anthropic-tools, design]
category: agent-engineering
difficulty: intermediate
---

# Agent Tool Design

## Why this skill exists

Anthropic's published 2025 guidance ([Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)) and OpenAI's function-calling guide converge on the same set of rules — and most teams discover those rules the hard way, after their agent has loop-burned a few thousand tokens trying to call `list_users` to find one record by name. The skill codifies what both vendors recommend so a new tool ships right the first time.

## Five rules (in order of leverage)

### 1. Name tools `service_resource_verb`, not `verb` or `action`

| Good | Bad |
|---|---|
| `github_pull_request_create` | `create_pr` |
| `linear_issue_search` | `search` |
| `slack_message_post` | `post` |
| `aida_recommendation_get` | `get_recommendation` |

The pattern is `<service>_<resource>_<verb>` with snake_case. Why: agents juggle 20+ tools at once, often from multiple MCP servers. A `create` tool collides with every other `create`; the model resolves ambiguity by re-reading descriptions, which is slow and error-prone. Namespacing the name eliminates the ambiguity at the model's first pass.

### 2. Name parameters by what they are, not by what they're called locally

| Good | Bad |
|---|---|
| `user_id` (UUID-shaped) | `user` (string? object? lookup-by-name?) |
| `repository_full_name` (owner/repo) | `repo` |
| `iso_8601_timestamp` | `time` |
| `query_text` | `q` |

Why: the agent reads the parameter name as a type hint. `user` could be an ID, an email, a username, or a display name — the model will pick one, often wrong. `user_id` resolves to a UUID in the model's head; the right caller behavior is forced.

### 3. Return signal-dense output; give the model a `response_format` knob

Default returns should be the minimum the model needs to keep working. Add an optional `response_format: "DETAILED" | "CONCISE"` parameter that the model picks per call. Default to `"CONCISE"`.

```json
// CONCISE (default)
{ "id": "iss_abc123", "title": "Login button broken", "status": "open" }

// DETAILED (when the model asks for it)
{
  "id": "iss_abc123",
  "title": "Login button broken",
  "status": "open",
  "assignee": { "id": "usr_def456", "name": "Alex" },
  "created_at": "2026-04-12T14:32:00Z",
  "comments": [/* … */],
  "labels": [/* … */]
}
```

Why: a 50-result list returned in DETAILED mode burns context for results 4–50 the model will never need. Let the model ask for depth when it actually needs depth.

### 4. Error strings are prompts — write them to guide the next attempt

```text
// Bad
"Error: 400 Bad Request"

// Better
"Error: 400 Bad Request. Field `user_id` must be a UUID, not an email. Use aida_user_search to look up the UUID for an email address."
```

The error is the agent's only signal about what to do next. If the error names the wrong field AND points to the recovery tool, the next attempt usually succeeds. If the error is opaque, the agent retries the same broken call.

Three patterns that work:
- **Name the offending field.** Don't say "validation failed" — say "field X failed validation Y."
- **Point to the recovery tool.** If the error is "user not found by id," include "use `<service>_user_search` to look up the id."
- **State what the model assumed wrong.** If the model passed a slug expecting a UUID, the error should say so.

### 5. Do not wrap every API endpoint 1:1

The strongest anti-pattern. A REST API has 47 endpoints; the agent does not need 47 tools. Group by **agent task**, not by **API surface**.

| Wrong (1:1 wrap) | Right (task-grouped) |
|---|---|
| `github_list_repos`, `github_list_pulls`, `github_list_issues`, `github_list_comments`, `github_list_users`, `github_list_branches`, `github_list_commits`, `github_list_files` | `github_search` (typed by resource_kind), `github_fetch` (one resource at a time, by ID) |
| `linear_create_issue`, `linear_create_project`, `linear_create_label`, `linear_create_cycle` | `linear_create` (typed by entity_kind, validated by Zod inside the tool) |

Why: 47 tools blow past the context budget and confuse the model on overlapping names. 5–10 task-shaped tools fit in cache, are easier to describe, and produce reliable behavior.

A useful test: count how many of your tools have the same first word. If `list_*` appears 6+ times, collapse to one parameterized `search` tool.

## Description writing — the most-skipped step

The `description` field is the agent's only documentation. Write it like a tutorial for someone who's never seen the API.

```ts
// Bad
description: "Create an issue."

// Good
description: `Create a new issue in Linear. Required fields: title (string), team_id (UUID from linear_team_search). Optional: description (markdown), assignee_id (UUID from linear_user_search), priority (1=urgent, 2=high, 3=medium, 4=low, 0=none), labels (array of label_id from linear_label_search). Returns the created issue's id, url, and identifier (e.g., "ENG-123") on success.

Use when the user asks to file a bug, create a task, or open a ticket. Do not use to update an existing issue (use linear_issue_update) or to create a project (use linear_project_create).`
```

Includes:
- What the tool does in one sentence.
- Every required field, every optional field, types.
- Where to get IDs from (cross-references to other tools).
- Return shape on success.
- When to use it AND when NOT to use it (point to the right tool for adjacent intents).

A good description doubles the success rate on first call. A bad description doubles your tool's loop-cost.

## Anti-patterns

- **Boolean parameters with no docs**: `force: true` — force what? Use enums (`mode: "soft" | "hard"`) and document each value.
- **`extra: any` / freeform JSON**: the model will fill it with reasonable-looking junk. Pick a schema or omit the field.
- **Returning HTML / unstructured prose**: parse it once at the tool boundary and return structured fields. Never make the model parse HTML in context.
- **Silent paging**: a tool that returns "first 20 of N" without saying so makes the model believe it has the whole answer. Always return `total` and `has_more`.
- **Tools that mutate AND read**: a tool named `update_and_get_user` invites the model to call it just to read. Split.

## Anthropic vs OpenAI wire-format notes

See `references/anthropic-tool-use.md` and `references/openai-function-calling.md` for the per-vendor specifics (block types, response shape, parallel tool calls, JSON-mode interplay). The five rules above apply to both vendors identically.

## When NOT to use this skill

- One-off internal scripts that aren't called by an agent.
- UI buttons that happen to be implemented as functions (no LLM in the loop).
- Tools called by Code Interpreter / sandboxed-Python — those have different ergonomics; the model treats them as `exec`, not as named tools.

## Cross-references

- **`prompt-builder`** — write the system prompt that talks about the tools after the tools are well-designed.
- **`agent-eval-harness`** — write evals against the tool surface, not against the underlying API. Bad tool design surfaces as eval failures.
- **`mcp-builder`** (in `build-loop` plugin) — for MCP-specific implementation; this skill is the design layer above it.

## Files in this skill

```
agent-tool-design/
├── SKILL.md                                  (this file)
├── blocks/
│   ├── naming-rule.md                        (paste-in naming rules)
│   ├── description-template.md               (paste-in description template)
│   └── error-string-templates.md             (paste-in error string patterns)
├── examples/
│   ├── good-tool.md                          (a well-designed Linear tool, end-to-end)
│   └── bad-tool.md                           (the same tool, poorly designed; what to look for)
└── references/
    ├── anthropic-tool-use.md                 (Claude tool_use blocks + wire format)
    └── openai-function-calling.md            (OpenAI function-calling + Agents SDK wire format)
```

## Sources

- [Anthropic — Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) (T1, 2025)
- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling) (T1)
- [OpenAI Agents SDK — Tools](https://openai.github.io/openai-agents-python/tools/) (T1)
- [Anthropic — Tool use overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) (T1)
