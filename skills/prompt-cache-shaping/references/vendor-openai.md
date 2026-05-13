# OpenAI Prompt Caching — Specifics

Source: [Prompt caching docs](https://developers.openai.com/api/docs/guides/prompt-caching) and [Cookbook — Prompt Caching 101/201](https://cookbook.openai.com/) (T1, current 2026).

## Mechanism

OpenAI's prompt cache is **automatic** — no API surface, no `cache_control` blocks. The platform hashes the prefix of every request; if a hash matches a previous request within the TTL window, you get a cache hit.

## Thresholds

| Threshold | Value |
|---|---|
| Minimum cacheable prefix | **1024 tokens** |
| Cache alignment increment | 128 tokens |
| Idle TTL | 5–10 minutes |
| Extended TTL on gpt-5.5+ | Up to **24 hours** |

If your stable prefix is under 1024 tokens, **nothing caches**. Pad it (add full tool descriptions, full rule blocks, canonical instructions) or accept no caching.

The 128-token alignment means the cache boundary snaps to 128-token increments. A prefix of 1500 tokens caches the first 1408 (= 1024 + 3×128); anything past that is uncached.

## Pricing

- **Cache hit**: typically **50% off input tokens** on most current models. Some recent models reduce further (~75%); read the live docs.
- **Cache write**: same as normal input pricing (no surcharge on OpenAI, unlike Anthropic). You pay once for the prefix and once per hit.
- **No explicit breakeven** — the cache hit is always cheaper than a miss. The only reason not to use it is if your prefix is too short or too volatile.

## Cache key — what affects the hash

- The prefix tokens (verbatim, in order).
- Model name (gpt-5 cache ≠ gpt-5-mini cache).
- Tool definitions are part of the prefix.
- Sampling parameters do NOT break the cache.
- `user` parameter (the optional user identifier) does NOT affect the cache.

Same gotchas as Anthropic apply: timestamps, reordered tools, reordered docs, embedded user query all invalidate.

## Extended retention on gpt-5.5+

On `gpt-5.5` and newer, OpenAI introduces **extended retention** — the cache can persist up to 24 hours of idle time. This is documented to be "best-effort" and may be silently shorter under load.

Implication: sporadic agents (one call per hour, e.g. cron workers) benefit massively on gpt-5.5+ where they'd see zero benefit on older models with a 5-min idle TTL.

Check the live docs for which models qualify — this list moves.

## Structured outputs + caching

Structured-output schemas (`response_format` with `strict: true`) are part of the prefix. A stable schema caches; a per-call schema doesn't.

For per-call schemas (e.g. dynamically-generated Zod), consider:
- Hoisting the schema to a small set of stable variants.
- Including the schema mid-prompt as a string (then it's part of the cacheable section).

## Cookbook references worth pulling

- "Prompt Caching 101" — basic mechanics, when it applies.
- "Prompt Caching 201" — advanced: schema caching, structured outputs, agent prefixes.
- "Reducing latency with prompt caching" — latency-focused tuning.

## Common gotchas

- **Sub-1024-token prefix**: silent no-op. Easy to miss in dev where prompts are short.
- **Mixed-tier traffic**: routing some calls to gpt-5 and some to gpt-5-mini means two cache populations, each with their own warm-up. Stick to one tier per cache prefix.
- **Streaming**: caching works on streaming responses the same way.
- **Batch API**: separate cache. Don't expect cache hits between live and batch traffic.
- **Embedded user content**: same rule as Anthropic — never embed user turn in the system prompt.

## How to detect cache hits

OpenAI's response includes `usage.prompt_tokens_details.cached_tokens` — the number of tokens served from cache. Compare it to total prompt tokens to compute hit rate.

```python
response = client.responses.create(...)
cached = response.usage.prompt_tokens_details.cached_tokens
total = response.usage.prompt_tokens
hit_rate = cached / total if total else 0
```

Track this metric in production. A drop in hit rate is the loudest signal that someone broke the prefix.

## When to skip caching

- Prompt prefix <1024 tokens.
- Stateless one-shot calls.
- Adversarial / red-team workloads where you intentionally rotate the prefix.
