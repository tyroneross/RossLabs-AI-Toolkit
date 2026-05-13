# OpenAI Reasoning Models — Specifics

Source: [Reasoning models guide](https://developers.openai.com/api/docs/guides/reasoning), [Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) (T1, 2026).

## Which models are "reasoning"

- **o-series**: o3, o4-mini, o5 (and successors). Always reasoning.
- **gpt-5 with `reasoning_effort` set**: turns reasoning on for that call.
- gpt-4.x, gpt-4o, gpt-4o-mini: NOT reasoning models. Use `prompt-builder` defaults for these.

## The four published rules

OpenAI's reasoning-best-practices doc:

1. **Zero-shot first.** Try the bare prompt before adding examples or scaffolding.
2. **Do NOT prompt for chain-of-thought.** The model is already doing it.
3. **Do NOT role-prime.** Reasoning models perform worse with persona scaffolding ("You are an expert..."). Just state the task.
4. **Use `reasoning_effort` as a knob, not a quality lever.** Tune empirically; default `medium`.

## Roles — `developer` is the highest-priority lane

- `developer` — hard rules, output contracts, structural constraints.
- `system` — works on reasoning models but is lower priority than `developer`.
- `user` — the actual query.

If you have conflicting instructions, put the must-obey ones in `developer`.

## `reasoning_effort` levels

| Level | Use when |
|---|---|
| `minimal` | Hint at light reasoning, mostly direct answer. Closest to a non-reasoning call. |
| `low` | Modest reasoning budget. Good for simple classification, short extraction. |
| `medium` | **Default.** Hard tasks with structured outputs, code review, multi-criteria scoring. |
| `high` | Only when eval shows medium fails. Expensive. |

Cost roughly doubles between adjacent levels on most tasks; reasoning tokens scale 2–5× per level on hard prompts.

## "Formatting re-enabled."

Reasoning models occasionally drop markdown / line breaks / structure when reasoning dominates the output. The published recovery: insert the literal token `"Formatting re-enabled."` near the end of the developer message.

```text
developer: |
  Return well-formed markdown:
  ## Section A
  ...
  ## Section B
  ...

  Formatting re-enabled.
```

Treat this as a workaround, not a long-term contract — OpenAI may change the model's default behavior. Re-check on every major model release.

## `reasoning.summary`

When you want to see the model's reasoning trace:

```python
response = client.responses.create(model="o4-mini", input=..., reasoning={"summary": "concise"})
print(response.reasoning.summary)
```

Options: `"none"`, `"concise"`, `"detailed"`. The summary is a compressed version of the full reasoning trace.

The full trace is NOT returned by default — and the summary tokens count toward output, so factor them into latency.

## Streaming

Reasoning models stream like other models. The reasoning trace comes through `reasoning_summary` events; the final answer through `text_delta` events. UIs can show progress through the reasoning if they want.

## Tools

Reasoning models support function calling and parallel tool calls normally. Same wire format as gpt-5. The reasoning happens before tool calls; tool results trigger more reasoning before the next decision.

## What doesn't work

- `temperature` parameter — most o-series models ignore it; some reject it.
- `top_p` — same.
- `n > 1` — supported but expensive. Generally cheaper to call once at higher effort than to sample several at lower effort.
- Long CoT few-shot examples — provide demos as JSON pairs, not as "and here's how I'd think through it" prose.

## Cost notes

- Reasoning tokens are typically priced at the input-token rate, but billed against the output budget.
- Track `usage.reasoning_tokens` to understand where cost is going.
- Prompt caching applies; reasoning tokens themselves are NOT cached (they're regenerated per call).
