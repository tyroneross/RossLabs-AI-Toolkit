# Anthropic Extended Thinking — Specifics

Source: [Extended thinking docs](https://platform.claude.com/docs/en/docs/build-with-claude/extended-thinking) (T1, 2026).

## How to enable

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=8000,
    thinking={
        "type": "enabled",
        "budget_tokens": 5000,
    },
    messages=[...],
)
```

`budget_tokens` is the soft cap on reasoning. The model uses up to this many; it may use fewer for simple tasks.

## Response shape

`response.content` is a list of blocks:

```json
[
  {"type": "thinking", "thinking": "<full reasoning trace>"},
  {"type": "text", "text": "<the answer>"}
]
```

Order: `thinking` blocks first, then `text` and/or `tool_use` blocks. There may be multiple `thinking` blocks if the model reasons in stages (e.g., before and after a tool call).

## The echo-back rule

Critical: when a `thinking` block appears in an assistant response and the conversation continues, you MUST include the `thinking` blocks in the next message you send back. Skipping them corrupts the reasoning state and may cause the model to re-derive context.

The Anthropic SDK's idiom handles this automatically when you append `response.content` to your messages array:

```python
messages.append({"role": "assistant", "content": response.content})  # includes thinking
```

Don't strip them. Don't summarize them. Echo them verbatim.

## Tool use + extended thinking

When the model emits both `thinking` and `tool_use` blocks in the same turn, you must:

1. Send back `tool_result` for each `tool_use`.
2. Echo the `thinking` block(s) back as part of the assistant's previous message.

```python
# Previous turn
response_1 = client.messages.create(thinking={"type": "enabled", ...}, messages=[user_msg], tools=tools)
# response_1.content = [thinking_block, tool_use_block]

# Next turn — assistant content (including thinking) + tool result
messages = [
    user_msg,
    {"role": "assistant", "content": response_1.content},  # thinking + tool_use
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use_block.id, "content": tool_output},
    ]},
]
response_2 = client.messages.create(thinking={"type": "enabled", ...}, messages=messages, tools=tools)
```

## `budget_tokens` tuning

| Task class | Suggested |
|---|---|
| Light reasoning (classification with rationale) | 1000–2000 |
| Code review (small diff) | 3000–5000 |
| Code review (large diff) | 8000–15000 |
| Multi-step planning | 5000–10000 |
| Math / logic problems | 4000–10000 |

Empirical tuning: start low, raise if outputs are shallow. The model can take less than budget — only the actually-used tokens are billed.

## What doesn't work

- Setting `temperature` while `thinking` is enabled — temperature has limited effect; the model picks its own under reasoning.
- Asking for the `thinking` block's content in prose ("show me your reasoning") — already shown as a structured block; redundant.
- Using extended thinking on a non-Opus tier without verifying it's supported — some tiers are reasoning-capable, some aren't. Check current docs.

## `tool_choice` interactions

- `tool_choice: "any"` or `{"type": "tool", ...}` works with extended thinking.
- The model reasons before deciding which tool to call (or whether to call any).

## Cost notes

- Thinking tokens are billed at output-token rates.
- Cache control applies to the prefix; thinking tokens are not cached.
- `budget_tokens` is a budget, not a quota — the model may use fewer if it converges.

## When NOT to enable extended thinking

- Conversational chat — the model is responsive enough without reasoning overhead.
- Structured-extraction-only tasks — reasoning won't change the JSON output.
- Cost-sensitive workloads — reasoning tokens add up.

## Compared to OpenAI o-series

The skill's `examples/extended-thinking-prompt.md` has the full comparison table. Key differences:

- Anthropic: explicit `thinking` blocks in response, must echo back.
- OpenAI: opaque internal reasoning, optional summary, no echo-back needed.
- Anthropic: `budget_tokens` is a soft cap.
- OpenAI: `reasoning_effort` is a level selector.
- Anthropic: `system` role works fine for hard rules.
- OpenAI: `developer` role is the higher-priority lane on reasoning models.
