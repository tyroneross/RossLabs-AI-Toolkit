# Example — OpenAI o-series Prompt

Task: classify a support ticket into one of 8 categories AND extract the root-cause cluster.

## Bad version (CoT-style, hurts the model)

```python
response = client.responses.create(
    model="o4-mini",
    input=[
        {
            "role": "system",
            "content": """You are an expert support engineer. When classifying tickets, think step by step:
1. Read the ticket carefully.
2. Identify keywords that suggest a category.
3. Match keywords to categories.
4. If multiple categories match, pick the most specific.
5. Then identify the root-cause cluster.
6. Return your answer.

Be thoughtful. Think through each step. Show your reasoning before answering."""
        },
        {"role": "user", "content": ticket_text}
    ]
)
```

What's wrong:
- `system` role on a reasoning model — should be `developer`.
- Multi-step procedural instruction — duplicates what the model does internally.
- "Think step by step" — actively hurts.
- "Show your reasoning before answering" — asks for reasoning-as-prose, which wastes tokens vs. structured `reasoning.summary`.

## Good version

```python
response = client.responses.create(
    model="o4-mini",
    input=[
        {
            "role": "developer",
            "content": """Classify the support ticket below into exactly one category and one root-cause cluster.

Categories: auth, billing, performance, data-loss, ui-bug, integration, feature-request, other
Root-cause clusters: env-config, third-party-outage, code-defect, user-error, capacity, unclear

Return JSON only:
{"category": "...", "root_cause_cluster": "...", "confidence": 0.0-1.0}

Formatting re-enabled."""
        },
        {"role": "user", "content": ticket_text}
    ],
    reasoning_effort="medium",
)

# To see the model's reasoning trace:
print(response.reasoning.summary)
```

What changed:
- `developer` role (correct for reasoning models).
- No CoT instructions, no role-priming, no "be thoughtful."
- Direct task, direct output format, "Formatting re-enabled" to keep the JSON shape clean.
- `reasoning_effort="medium"` — the default; bump to `high` only if eval shows medium fails.
- Read the reasoning via `reasoning.summary`, not by asking the model to emit it.

## When to bump effort

`medium` is the right default. Bump to `high` when:

- Eval pass rate at `medium` is below your threshold AND
- You've already verified the prompt is right (zero-shot, structured output) AND
- You've measured that `high` actually improves your specific eval (not just an adjacent one).

Cost goes up sharply: `high` is ~5× the reasoning tokens of `medium` on most tasks.

## Common gotchas

- **`system` role still works**, but `developer` is higher priority on reasoning models. Use developer.
- **No `temperature` knob** on most o-series models — reasoning models pick their own. Don't set it.
- **`max_output_tokens` is for the final answer**, NOT the reasoning. The reasoning has its own budget under `reasoning_effort`.
- **Streaming**: reasoning blocks come in stream events; you can show them progressively or hide them.
