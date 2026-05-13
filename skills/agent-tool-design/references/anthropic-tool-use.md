# Anthropic Tool Use — Wire Format Notes

Vendor-specific notes that complement the cross-vendor rules in SKILL.md. Source: [Anthropic Tool Use docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) (T1, current as of 2026).

## Tool definition shape

```json
{
  "name": "snake_case_name",
  "description": "Full description per blocks/description-template.md",
  "input_schema": {
    "type": "object",
    "properties": { /* ... */ },
    "required": [ /* ... */ ]
  }
}
```

- `input_schema` is JSON Schema (Draft 2020-12 subset). Anthropic respects `enum`, `minLength`, `maxLength`, `minimum`, `maximum`, `pattern`, nested `properties`.
- No top-level `strict: true` knob (that's OpenAI). Anthropic's models follow the schema reliably without a strict flag, especially Claude 3.5+.
- Optional fields go in `properties` but not in `required`.

## tool_use block in the response

```json
{
  "type": "tool_use",
  "id": "toolu_01XYZ...",
  "name": "linear_issue_create",
  "input": { "title": "...", "team_id": "..." }
}
```

- The `id` is the correlation key. Return the result with `tool_use_id` matching this id.
- The model emits a `tool_use` block alongside any prior `text` block in the same assistant message.

## tool_result block on the way back

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01XYZ...",
  "content": "Plain string OR array of content blocks",
  "is_error": false
}
```

- `content` can be a plain string (cheap, what most tools should return) OR an array of content blocks for richer returns (text + image, for vision tools).
- On error, set `is_error: true` and put the prompt-engineered error string in `content`. The model reads error results differently than success results.

## Parallel tool calls

- The model can emit multiple `tool_use` blocks in a single assistant message.
- Send back all `tool_result` blocks in the next user message (one per call).
- The model resolves them in parallel.
- Use this for fanout — e.g. fetching 5 issues by id in one assistant turn.

## Extended thinking + tools

If the model is using extended thinking (`thinking` blocks):
- The `tool_use` blocks come AFTER the `thinking` block in the same message.
- When you return `tool_result`, you must echo the `thinking` blocks back in the next user message (per the [Extended thinking docs](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)).
- This preserves the model's reasoning state across the tool-call boundary.

## `tool_choice` knob

- `"auto"` (default) — model decides whether to call a tool.
- `"any"` — force any tool call.
- `{"type": "tool", "name": "..."}` — force a specific tool.
- `"none"` — disable tool calls for this turn.

Use `"any"` or specific-tool when you know a tool must run; reserve `"auto"` for general chat surfaces.

## Cache control on tool definitions

Tools live in the prompt prefix. Add `cache_control: { type: "ephemeral" }` to the last tool definition to checkpoint the tool block for prompt caching — see `prompt-cache-shaping` skill for the full pattern.

## What's different from OpenAI

| Topic | Anthropic | OpenAI |
|---|---|---|
| Strict mode | No flag; reliable by default | `strict: true` + `additionalProperties: false` |
| Response shape | `tool_use` block in `content` array | `function_call` field on the assistant message |
| Result return | `tool_result` block | `function` role message |
| Parallel calls | Native, multiple blocks per message | `parallel_tool_calls: true` flag |
| Extended thinking + tools | Must echo `thinking` blocks back | N/A — no equivalent at this layer |
