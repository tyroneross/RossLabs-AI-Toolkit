# OpenAI Eval Guidance — Specifics

Sources: [OpenAI Structured Outputs § evals](https://platform.openai.com/docs/guides/structured-outputs), [OpenAI Cookbook — Evals](https://cookbook.openai.com/), [OpenAI Evals API](https://platform.openai.com/docs/guides/evals) (T1).

## The OpenAI Evals API

OpenAI provides a built-in evals platform on the dashboard. You can:
- Upload an eval set (JSONL).
- Define graders (deterministic code via Python expressions, or model-based).
- Run an eval against any model version.
- Compare runs side-by-side.

Useful when:
- You want the eval visible to non-engineers.
- You want side-by-side runs across gpt-5 / gpt-5-mini / o-series / older versions.
- You don't want to host the runner yourself.

Not useful when:
- Your tasks call your own agent code (not just a model). Use the local runner in `templates/runner.ts` for that.
- Your graders need access to your own infrastructure.

## Structured outputs as a free eval

If you use `response_format` with `strict: true` and a Zod schema:
- Schema-validity is checked by the API itself.
- Refusals come back as a separate field.
- You get a built-in deterministic-code grader without writing one.

For any structured-output task, eval = "did the response parse against the schema, and was the refusal field empty?" That's a single line of code.

## pass@k / pass^k

OpenAI's docs don't use these names verbatim, but the methodology aligns. The `n` parameter on the Responses API lets you sample k completions in one call (cheaper than k separate calls) — use it.

```python
response = client.responses.create(
    model="gpt-5",
    input=...,
    n=5,                  # sample 5 completions
)
# Now compute pass@5 and pass^5 across response.outputs
```

## LLM-judge model picks

- **Default**: `gpt-4.1-mini` or `gpt-5-mini` — cheap, calibrated, JSON-mode reliable.
- **Hard rubrics**: `gpt-5` — better nuance, ~5× cost.
- **Adversarial**: `o3-mini` with `reasoning_effort: medium` — reasoning models are better at "is this argument valid?" judgments. See `reasoning-model-prompting` skill for how to prompt them (do NOT add CoT).

## Cost notes

- Prompt caching is automatic on OpenAI. Structure the judge system prompt + rubric as the static prefix (≥1024 tokens) and you'll get cache hits on every call after the first.
- Use the Batch API for nightly evals — 50% discount, runs within 24h.

## Compared to Anthropic

| Topic | OpenAI | Anthropic |
|---|---|---|
| Hosted eval platform | Yes (Evals dashboard) | No first-party platform; community tools (Inspect, Promptfoo) work fine. |
| Schema-validity grader | Built-in via `strict: true` | No flag; validate in your code. |
| Multi-sample API | `n` parameter on Responses API | Run k requests separately. |
| Reasoning-model judge | o-series with `reasoning_effort` | Extended thinking on Claude with `thinking` blocks. |
| Cache control on judge | Automatic prefix hash | Explicit `cache_control` breakpoint. |

## Cookbook references

OpenAI Cookbook (cookbook.openai.com) entries to read first:
- "Structured outputs with Pydantic" — schema-validity evals.
- "Evals with the Responses API" — pass@k mechanics.
- "Calibrating an LLM judge" — calibration protocol.
- "Reasoning model evals" — o-series-specific eval design.

Always cross-check the cookbook for entry dates — patterns shift quickly on the OpenAI side.
