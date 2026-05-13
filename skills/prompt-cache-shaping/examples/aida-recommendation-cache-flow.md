# Worked Example — Aida Recommendation Flow

Concrete cache shaping for the recommendation engine in `decision-doctor-cc`, with both Anthropic and OpenAI versions.

## The flow

Per active session, ~50 LLM calls touch the recommendation surface:
- Pass 1 (decompose) on the user's intake.
- Pass 2 (score) on the decomposed workflow.
- Artifact-build per lynchpin (3 calls).
- Follow-up chat turns about the recommendation.

All of these share most of their prompt prefix: tool definitions (none in chat, some in artifact-build), system prompt, citation + number-labeling rule blocks, two-register voice block, and stable retrieval context (the user's pinned sources).

## Without cache shaping

Each call sends:
- 1800 tokens tool definitions (artifact-build only; 0 elsewhere)
- 2400 tokens system prompt + rule blocks
- 600 tokens stable retrieval context
- 80 tokens user turn

Average ~4700 tokens/call. 50 calls → **235k input tokens** per session.

## With cache shaping — Anthropic

```ts
const messages = [
  {
    role: 'user',
    content: [
      // Stable rule blocks first — these are identical across every call
      { type: 'text', text: SYSTEM_PROMPT_PLUS_REGISTER },
      { type: 'text', text: CITATION_RULE_BLOCK },
      {
        type: 'text',
        text: NUMBER_LABELING_RULE_BLOCK,
        cache_control: { type: 'ephemeral', ttl: '1h' }, // ← breakpoint 1: end of stable rules
      },
      // Retrieval context — stable across this session's calls
      {
        type: 'text',
        text: stableRetrievalContext,
        cache_control: { type: 'ephemeral', ttl: '1h' }, // ← breakpoint 2: end of context
      },
      // User's current turn — never cached
      { type: 'text', text: userTurn },
    ],
  },
];
```

For artifact-build (which has tools), add a third breakpoint after the last tool:

```ts
const tools = [
  toolA,
  toolB,
  { ...toolC, cache_control: { type: 'ephemeral', ttl: '1h' } }, // ← tools checkpoint
];
```

**Math** (Sonnet, $3/Mtok input):
- Uncached: 4700 × 50 × $3/Mtok = **$0.705**
- First call writes 4620 tokens to cache: 4620 × 1.25 × $3/Mtok = **$0.0173**
- 49 hits read 4620 from cache: 4620 × 0.1 × $3/Mtok × 49 = **$0.0679**
- Plus uncached user turns: 80 × 50 × $3/Mtok = **$0.012**
- Total cached: **$0.097**
- **Reduction: 86%.**

## With cache shaping — OpenAI

Automatic — no `cache_control` blocks. Order content the same way:

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT_PLUS_REGISTER + CITATION_RULE_BLOCK + NUMBER_LABELING_RULE_BLOCK + stable_retrieval_context},
    {"role": "user", "content": user_turn},
]

response = client.responses.create(
    model="gpt-5",
    input=messages,
    tools=tools,                # tool definitions are part of the prefix
    parallel_tool_calls=True,
)

# Check cache hit
cached = response.usage.prompt_tokens_details.cached_tokens
total = response.usage.prompt_tokens
print(f"Cache hit rate: {cached/total:.0%}")
```

OpenAI hashes the prefix automatically. The cacheable portion is ~4620 tokens; over 1024, so it qualifies. On gpt-5.5+, idle TTL extends to 24h — useful if the session spans hours.

**Math** (gpt-5, ~$1.25/Mtok input, ~50% discount on cache hits):
- Uncached: 4700 × 50 × $1.25/Mtok = **$0.29**
- First call: full price. 49 cache hits at 50% off the prefix.
- Cached: 4700 × $1.25/Mtok + (4620 × 0.5 + 80) × 49 × $1.25/Mtok = **$0.006 + $0.146 = $0.15**
- **Reduction: 48%.**

OpenAI's lower per-Mtok cost + automatic caching makes the absolute savings smaller than Anthropic, but the percentage reduction is still substantial.

## What we kept dynamic on purpose

- **User turn** — obviously per-call.
- **Conversation history** — grows per turn; can checkpoint at the end of "settled" history but the in-flight turn moves the boundary.
- **Stage-N output passed to Stage-N+1** (in multi-pass-llm-pipeline) — by definition per-call.

## What broke the cache early in dev

Two real breakages from the v2-workflow rollout in `decision-doctor-cc`:

1. **A `Date.now()` timestamp** in the system prompt (was tracking session ID). Every call shifted the prefix. **Fix**: removed the timestamp from the prompt and put session ID in metadata.

2. **Retrieval results ordered by RRF score** per call. Same documents, different order = different hash. **Fix**: append-sort retrieval results by document ID before formatting them into the prompt. Order is now stable across calls in the same session.

Hit rate before fixes: ~5%. After: 92% steady-state.

## Telemetry

Log per-call:
```ts
{
  call_id: '...',
  model: 'sonnet-4-6',
  input_tokens_total: 4720,
  input_tokens_cached: 4620,
  cache_hit_rate: 0.979,
  cache_ttl: '1h',
  // ...
}
```

Aggregate as a daily / weekly hit-rate metric. A drop is your earliest warning that someone broke the prefix.
