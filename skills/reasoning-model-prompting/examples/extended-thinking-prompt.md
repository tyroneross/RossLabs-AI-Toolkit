# Example — Anthropic Claude Extended Thinking Prompt

Task: review a pull request's diff and report whether it has hidden semantic bugs.

## The call

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=8000,
    thinking={"type": "enabled", "budget_tokens": 5000},
    system="""You review code diffs for hidden semantic bugs. Report findings as JSON:
{
  "findings": [
    {"severity": "high|medium|low", "file": "...", "line": 42, "issue": "...", "evidence": "..."}
  ],
  "overall_risk": "ship|review|reject"
}""",
    messages=[
        {"role": "user", "content": f"DIFF:\n{diff_text}\n\nReport findings."}
    ],
)

# response.content is a list of blocks:
# [
#   {"type": "thinking", "thinking": "<reasoning trace>"},
#   {"type": "text", "text": "<JSON answer>"}
# ]

reasoning = next(b for b in response.content if b.type == "thinking")
answer = next(b for b in response.content if b.type == "text")
findings = json.loads(answer.text)
```

## What makes this good

- **System prompt is direct**: states the task and the output format. No "think carefully." No role-priming beyond "You review code diffs."
- **`budget_tokens: 5000`**: gives the model real reasoning room. The default is too low for diffs of any size.
- **Structured output**: JSON, fields named clearly. The model's reasoning is in the `thinking` block; the prose-version isn't needed.
- **No conflicting prose instructions**: no "show your work," no "before answering."

## Multi-turn / tool use — the echo-back rule

If you continue the conversation (e.g., to ask for more detail on a specific finding), you MUST echo the previous assistant content back. The Anthropic SDK does this for you if you append `response.content`:

```python
messages = [{"role": "user", "content": "DIFF: ..."}]

response_1 = client.messages.create(messages=messages, ...)
messages.append({"role": "assistant", "content": response_1.content})  # ← thinking + text both echoed

messages.append({"role": "user", "content": "Tell me more about finding 2."})
response_2 = client.messages.create(messages=messages, ...)  # reasoning state preserved
```

**Do NOT** strip the `thinking` blocks before appending. The model relies on them to maintain coherent reasoning across turns.

## When NOT to use extended thinking

- The task is mechanical (parse this regex, run this lookup). Reasoning is overhead.
- The output is a single short answer. Reasoning won't fit a meaningful budget.
- You're cost-bound — reasoning tokens are charged.

For these, use plain Claude (no `thinking` block) — much cheaper, no echo-back rule, simpler prompting.

## Tuning `budget_tokens`

| Task class | Suggested budget |
|---|---|
| One-shot classification with rationale | 1000–2000 |
| Code review of a small diff (~50 lines) | 3000–5000 |
| Code review of a large PR (~500 lines) | 8000–15000 |
| Multi-step plan generation | 5000–10000 |

Start at the low end; raise empirically if findings are shallow.

## Compared to OpenAI o-series

| Topic | Anthropic extended thinking | OpenAI o-series |
|---|---|---|
| Enable | `thinking: { type: "enabled", budget_tokens: N }` | Use o-series model + `reasoning_effort` |
| Reasoning visibility | `thinking` content block, full trace | `reasoning.summary` — summary only |
| Across turns | Must echo `thinking` blocks back | Implicit, model retains internally |
| Role for hard rules | `system` (works fine) | `developer` (preferred) |
| CoT prompts | Hurt | Hurt |
| Role-priming | Mild help on Anthropic, often a wash | Hurts on OpenAI |
