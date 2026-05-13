# Anthropic Prompt Caching — Specifics

Source: [Prompt caching docs](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) (T1, current 2026).

## Mechanism

Anthropic exposes prompt caching as **explicit breakpoints** you place in the prompt:

```json
{
  "type": "text",
  "text": "{{long stable content}}",
  "cache_control": { "type": "ephemeral" }
}
```

A `cache_control` marker says: "Cache everything up to and including this block." On the next call, if the prompt prefix up to this marker matches, you get a cache hit.

## Budget — 4 breakpoints, 20-block lookback

- You can place **up to 4 `cache_control` breakpoints** in a single request.
- Anthropic scans the **last 20 blocks** of your prefix for prior cache entries. Anything older won't match.
- This limits cache hierarchy depth — practical implication: don't try to micro-cache every block.

Typical placement:

```
[Tool block 1] [Tool block 2] ... [Tool block N]  ← breakpoint 1: after tools
[System prompt]                                    ← breakpoint 2: after system
[Stable rule blocks (citation, number-labeling)]   ← breakpoint 3: after stable blocks
[Retrieval context — if stable]                    ← breakpoint 4: after retrieval
[Conversation history]                             ← uncached
[Current user turn]                                ← uncached
```

If you don't need 4, use fewer. Spending fewer breakpoints does not improve anything.

## TTL — 5 minutes or 1 hour

| TTL | Default? | How |
|---|---|---|
| 5 minutes (ephemeral default) | Yes | `cache_control: { type: "ephemeral" }` |
| 1 hour | Opt-in | `cache_control: { type: "ephemeral", ttl: "1h" }` (requires `anthropic-beta: cache-control-ttl-1h` header) |

5-min works for interactive UIs. 1-hour wins for batch jobs, eval runs, workers that fire every few minutes but not every few seconds.

## Pricing

- **Cache write**: 1.25× input token price (Sonnet/Opus). Pay once for the first call that writes the prefix.
- **Cache read**: 0.1× input token price (90% discount). Pay this on every subsequent hit.
- Breakeven: cache wins after the 2nd hit. For any prefix you call more than once within the TTL window, it's net positive.

Example math for a 5000-token prefix called 50 times on Sonnet ($3/Mtok input):
- Uncached: 5000 × 50 × $3/Mtok = **$0.75**
- Cached: 5000 × 1.25 × $3/Mtok (1 write) + 5000 × 0.1 × $3/Mtok × 49 (49 reads) = $0.019 + $0.074 = **$0.093**

Net **~88% reduction**.

## Cache key — what affects the hash

The cache key includes:
- Tools (definitions, order, descriptions).
- System prompt (verbatim).
- Conversation messages up to the cache breakpoint.
- Model version.
- Sampling parameters? **No** — temperature/top_p don't break the cache.

Even a 1-character change in the prefix invalidates the cache. Whitespace matters. Date strings in the system prompt are a common silent breaker — move them out.

## tool_use + cache_control

Cache the last `tool_use` block in a tool list to checkpoint the entire tools section:

```ts
const tools = [
  toolA,
  toolB,
  { ...toolC, cache_control: { type: "ephemeral" } }, // ← checkpoint
];
```

Anthropic uses the LAST `cache_control` in the tools array as the tools-section boundary.

## Common gotchas

- **Reordering tools** breaks the cache. Lock tool order at the call site.
- **Reordering retrieved docs by score per call** breaks the cache past that point. Either order by stable ID or accept the miss.
- **Embedding the user query in the system prompt** breaks every call. User content stays at the end.
- **Beta header drift**: the 1h-TTL header (`anthropic-beta: cache-control-ttl-1h`) may move from beta to GA — check current docs before pinning.
- **Cache_control on a too-short block** is wasted budget. Don't checkpoint <200 tokens.

## When to skip caching

- Total cacheable prefix <1000 tokens (write cost > savings).
- You call the model fewer than 2× per cache window.
- The "stable" parts of your prompt actually change every call (re-examine the prompt — usually a templating bug).
