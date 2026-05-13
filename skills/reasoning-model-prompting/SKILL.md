---
name: reasoning-model-prompting
description: Use when prompting a reasoning model — OpenAI o-series (o3, o4-mini, o5), GPT-5 with reasoning_effort, or Anthropic Claude with extended thinking enabled. This is a counter-skill — the default prompt-builder advice (CoT, role-priming, "think step by step") actively hurts reasoning models. Encodes OpenAI and Anthropic's published 2025–2026 guidance — zero-shot first, do NOT add chain-of-thought, do NOT role-prime, developer messages replace system, reasoning_effort is a tuning knob not a quality lever, "Formatting re-enabled" recovers structured output, preserve thinking blocks across tool turns on Anthropic. Triggers on "prompt an o-series model", "prompt o3 / o4-mini / o5", "GPT-5 reasoning_effort", "extended thinking on Claude", "reasoning model", "the o-series is being weird", "the model ignores my CoT prompt", "thinking blocks", "should I use chain-of-thought here".
author: Tyrone Ross
version: 0.1.0
tags: [reasoning-models, o-series, gpt-5, extended-thinking, prompt-engineering, openai, anthropic]
category: prompt-engineering
difficulty: intermediate
---

# Reasoning Model Prompting

## Why this skill exists — and why it contradicts `prompt-builder`

The default `prompt-builder` skill teaches chain-of-thought, role-priming, and skeleton-first patterns. Those work brilliantly on non-reasoning models (Sonnet 4.6, gpt-4o, Haiku). They **hurt** reasoning models — because reasoning models are already doing chain-of-thought internally, and your "think step by step" instruction either gets ignored (best case) or double-counts and confuses the response (worst case).

OpenAI's own published guidance: *"Treat `reasoning.effort` as a tuning knob, not the primary way to recover quality."* and *"Do not instruct the model to think step-by-step."* This skill encodes the contrary advice you need when the target is a reasoning model.

## What counts as a reasoning model

| Vendor | Models | How to recognize |
|---|---|---|
| OpenAI | o3, o4-mini, o5, gpt-5 (when `reasoning_effort` is set) | Has a `reasoning` field in the response; `reasoning_tokens` in usage. |
| Anthropic | Claude (any tier) with `extended_thinking` enabled | Has `thinking` content blocks in the response. |

If the model isn't a reasoning model, this skill does NOT apply — use `prompt-builder` defaults instead.

## Five rules for reasoning-model prompts

### Rule 1 — Zero-shot first

Start with the bare minimum prompt: state the goal, provide inputs, ask for output. **Don't** add reasoning scaffolding. **Don't** add role-priming. **Don't** add "think carefully." Try the bare prompt first; only add structure if outputs are wrong.

```text
# Bad (for a reasoning model)
You are an expert data analyst. Think step by step about the following CSV.
First, identify the columns. Second, find the outliers. Third, ... Then output your final answer.

# Good
Given this CSV, list the outliers in column `price` with one-sentence rationale for each.

CSV:
{{csv_data}}
```

Why: the model is already doing the multi-step reasoning. Your scaffolding either overrides the model's plan (with a worse one), or duplicates it (wasting reasoning budget).

### Rule 2 — Do NOT add chain-of-thought instructions

These hurt:
- "Think step by step."
- "Let's work through this carefully."
- "Walk through your reasoning before answering."
- "First, X. Then, Y. Then, Z."

These help:
- Direct task statement.
- Clear inputs.
- Clear output format.

If you want the reasoning visible in the response, OpenAI o-series exposes `reasoning.summary` (when enabled); Anthropic exposes the `thinking` block directly. Read the model's reasoning; don't ask the model to emit reasoning prose.

### Rule 3 — `reasoning_effort` is a tuning knob, not a quality lever

OpenAI's o-series and gpt-5-with-reasoning expose `reasoning_effort: "minimal" | "low" | "medium" | "high"`. Higher effort = more reasoning tokens = better on hard tasks AND higher cost + latency.

Use `medium` as default. Bump to `high` only for tasks where you've measured that `medium` is genuinely failing — not because "more is better." If `high` doesn't fix the problem, the problem isn't reasoning depth; it's prompt shape or model fit.

Anthropic's `budget_tokens` on extended thinking is the equivalent knob.

### Rule 4 — Developer messages replace system messages (OpenAI)

OpenAI's reasoning models treat the `developer` role as the highest-priority instruction. Use `developer` for hard rules; reserve `system` for older non-reasoning models.

```python
response = client.responses.create(
    model="o4-mini",
    input=[
        {"role": "developer", "content": "Return JSON only. No prose. No markdown fences."},
        {"role": "user", "content": user_query},
    ],
    reasoning_effort="medium",
)
```

Anthropic doesn't have a developer-role concept; system prompt works as expected for extended-thinking calls.

### Rule 5 — "Formatting re-enabled" recovers structured output

OpenAI reasoning models occasionally drop formatting (markdown, line breaks, structure) when reasoning dominates. The published recovery token: insert `"Formatting re-enabled."` near the end of the developer/system message.

```text
developer: |
  You produce decision audits. Return well-formed markdown with sections:
  - Headline
  - Basis (3-5 sentences)
  - Caveats

  Formatting re-enabled.
```

Treat this as a Known Workaround, not a long-term fix — OpenAI may revise the model's behavior at any time.

## Anthropic extended thinking — the thinking-block contract

On Anthropic Claude with extended thinking:

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=8000,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=[{"role": "user", "content": user_query}],
)
# response.content is a list of blocks:
# [{type: "thinking", thinking: "<the reasoning>"}, {type: "text", text: "<answer>"}]
```

**Crucial rule**: if a `thinking` block appears in the assistant's response and the conversation continues (tool use, multi-turn), you MUST echo the `thinking` blocks back in the next user message. Skipping them corrupts the reasoning state.

```python
# Next user turn
messages.append({"role": "assistant", "content": response.content})  # includes thinking
messages.append({"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "...", "content": "..."},
]})
```

The `thinking` block stays in the assistant message; the user message just adds new content. The Anthropic SDK handles this for you if you append the whole `response.content` array.

## Anti-patterns

- **Adding CoT to a reasoning model**. Default impulse from prompt engineering culture; actively hurts on o-series. Stop.
- **Cranking `reasoning_effort` to high "just in case"**. Costs 4–10× more, marginal quality lift. Tune empirically; default `medium`.
- **Using `system` role on OpenAI reasoning models**. Use `developer`. OpenAI does process `system` but `developer` is the higher-priority lane on reasoning models.
- **Dropping `thinking` blocks on subsequent turns (Anthropic)**. Breaks the reasoning state. Always echo back the previous assistant content array verbatim.
- **Asking the model to emit its reasoning as prose**. Use the structured `reasoning.summary` (OpenAI) or `thinking` block (Anthropic). Asking for prose-reasoning wastes tokens on a worse format.

## Where this skill IS NOT the right call

- **Non-reasoning models** — Sonnet 4.6 without extended thinking, gpt-4o, Haiku, gpt-4o-mini. Use `prompt-builder` defaults; CoT helps these.
- **Pure structured-output tasks** — schema-validity-only tasks don't need reasoning; use `gpt-5` with `reasoning_effort: "minimal"` or just a regular model.
- **Cost-bound workloads** — reasoning models are ~5–10× more expensive than non-reasoning. If your eval shows non-reasoning is sufficient, ship that.

## Cross-references

- **`prompt-builder`** — the default prompting playbook. This skill is the counter-skill that fires when the target is a reasoning model. They don't conflict; they specialize.
- **`grounded-llm-prompt`** — citation + number-labeling blocks work the same on reasoning models. Compose them per usual.
- **`agent-eval-harness`** — eval o-series vs gpt-5-mini side-by-side before picking a tier; reasoning isn't always the right tool.
- **`prompt-cache-shaping`** — caching works on reasoning models the same way. Don't skip it because the model "thinks."

## Files in this skill

```
reasoning-model-prompting/
├── SKILL.md                              (this file)
├── examples/
│   ├── o-series-prompt.md                (full worked example, OpenAI o4-mini)
│   └── extended-thinking-prompt.md       (full worked example, Anthropic Opus extended thinking)
└── references/
    ├── openai-reasoning.md               (developer role, reasoning_effort, Formatting re-enabled)
    └── anthropic-extended-thinking.md    (thinking blocks, budget_tokens, echo-back rule)
```

## Sources

- [OpenAI — Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) (T1, 2026)
- [OpenAI — Reasoning models guide](https://developers.openai.com/api/docs/guides/reasoning) (T1, 2026)
- [OpenAI Cookbook — o-series prompting](https://cookbook.openai.com/) (T1)
- [Anthropic — Extended thinking](https://platform.claude.com/docs/en/docs/build-with-claude/extended-thinking) (T1, 2026)
