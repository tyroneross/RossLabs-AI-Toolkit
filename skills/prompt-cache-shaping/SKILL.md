---
name: prompt-cache-shaping
description: Use when designing a prompt or agent that will run at scale and you want to maximize prompt-cache hit rate. Encodes the cross-vendor invariant — order content static-to-dynamic so the cacheable prefix is stable — plus Anthropic's explicit cache_control breakpoint mechanics (4-breakpoint budget, 20-block lookback, 5m vs 1h TTL) and OpenAI's automatic prefix hashing (≥1024 token threshold, 128-token increments, 5–10min idle TTL, up to 24h on gpt-5.5+). Triggers on "prompt caching", "cache hit rate", "reduce LLM cost", "ephemeral cache", "cache_control", "prompt is slow on every call", "we're paying for the same tokens twice", "TTL", "cache breakpoint". Vendor-neutral spine plus per-vendor branches in references/.
author: Tyrone Ross
version: 0.1.0
tags: [prompt-caching, cost-optimization, latency, anthropic, openai]
category: prompt-engineering
difficulty: intermediate
---

# Prompt Cache Shaping

## Why this skill exists

Prompt caching is a 5–10× cost lever and a 2–3× latency lever for any production LLM app. Anthropic and OpenAI both ship it, both publish guidance, and both reward the same prompt-shape — but they expose it differently. Anthropic gives you explicit `cache_control` breakpoints; OpenAI does it automatically by prefix hash. Get the shape right once and you reap the savings on every call. Get it wrong and you pay full price for tokens you reuse.

## The cross-vendor invariant — static-to-dynamic ordering

```
┌─────────────────────────────────────────────────────────────────┐
│ STATIC (cacheable)                          DYNAMIC (per-call) │
├─────────────────────────────────────────────────────────────────┤
│ 1. Tool definitions                      → Cache hit boundary  │
│ 2. System prompt                                                │
│ 3. Stable instruction blocks                                    │
│ 4. Retrieved sources / RAG context     ─── boundary candidate ──│
│ 5. Conversation history                                         │
│ 6. The user's current turn                                      │
└─────────────────────────────────────────────────────────────────┘
```

The rule is identical on both vendors: anything that's stable across calls goes early; anything that changes per-call goes late. Vendors hash the prefix; if your prefix shifts by even one token, the cache misses.

## Three rules

### Rule 1 — Order the prompt static-to-dynamic, always

This applies to:
- **System prompt + instructions** at the top, before any per-call content.
- **Tool definitions** before the system prompt (Anthropic's order; OpenAI is flexible but follow this order anyway for portability).
- **RAG context** in the middle — *stable* if you're retrieving the same docs for a batch of related queries, *dynamic* if every query retrieves different docs.
- **Conversation history** near the end, but BEFORE the current turn.
- **User's current turn** at the very end.

The order is dictated by what changes per-call. Anything before the first change-point is cached; anything after is not.

### Rule 2 — Make the cacheable prefix at least ~1024 tokens

OpenAI's automatic cache only kicks in at ≥1024 tokens. Anthropic charges for cache writes and rewards cache hits, so a tiny cacheable block isn't worth the write cost.

If your system prompt is 400 tokens, you'll see no caching. Pad with stable content (canonical instructions, reusable rule blocks, full tool descriptions) until the cacheable prefix is well over 1024 tokens. Or accept that small-prompt apps don't benefit from caching.

### Rule 3 — Match TTL to call rhythm

| TTL choice | Use when |
|---|---|
| Anthropic ephemeral 5-min | Interactive sessions; chat; UI loops; anything bursty within minutes. |
| Anthropic ephemeral 1-hour (beta `cache-control-ttl-1h`) | Batch jobs; cron-driven workers; eval runs; longer-form workflows. |
| OpenAI automatic (5–10min idle) | Whatever falls naturally; you don't control TTL. |
| OpenAI extended (gpt-5.5+, up to 24h) | Stable agents called sporadically across the day. |

If your inter-call gap exceeds the TTL, the cache expires and you pay full price on the next call. For sporadic high-volume workloads, prefer 1h TTL (Anthropic) or extended retention (OpenAI gpt-5.5+).

## Anti-patterns

- **Embedding the user's turn in the middle.** If you template the user's query INTO your system prompt ("…answer this question: {{user_query}}"), the whole prompt mutates per call. Cache cannot hit. Put user content at the end.
- **Rotating context positions.** Reordering retrieved docs (e.g., by score) on every call changes the hash. Either lock the order (e.g., by ID) or accept the cache miss past the rotation point.
- **Timestamping the system prompt.** `"Today is 2026-05-12T14:32:17Z"` shifts the prefix every second. Move timestamps to a per-call section, or round to the day.
- **Sub-1024-token cacheable block + OpenAI**: nothing caches. Either pad or skip caching.
- **Cache breakpoint after every block (Anthropic).** You get 4 breakpoints; spending them on adjacent blocks wastes the budget. Place breakpoints at meaningful boundaries: after tools, after system, after stable context, before history.

## Wire-format details

See:
- `references/vendor-anthropic.md` — explicit `cache_control` blocks, 20-block lookback, 4-breakpoint budget, beta 1h TTL header, billing notes.
- `references/vendor-openai.md` — automatic prefix hash, 128-token alignment, idle TTL, extended retention on gpt-5.5+, no API surface.

## When NOT to use this skill

- One-shot scripts (caching only helps if you call the model more than ~5–10 times with overlapping prefixes).
- Very small prompts (<1024 tokens of cacheable content on OpenAI; <~1024 on Anthropic for net positive).
- Per-call prompts that genuinely have no stable prefix (rare; usually a sign you're templating wrong).

## Worked example — Aida recommendation flow

The recommendation surface in `decision-doctor-cc` runs ~50 calls per active session. Without cache shaping, each call sent:
- 2400-token system prompt (truthfulness rules + citation contract + register)
- 1800-token tool definitions
- ~600-token retrieval context
- ~80-token user turn

Total: ~4880 tokens/call × 50 = 244k tokens input.

After shaping:
- Tools + system prompt + truthfulness/citation blocks + ordered (by ID) retrieval context = ~4800 token cacheable prefix.
- User turn = ~80 tokens (uncached).
- First call writes 4800 to cache (10% surcharge on Anthropic).
- Calls 2–50 read 4800 from cache at 10% of input cost (90% discount).

Net: ~4800 × 1.1 + 4800 × 0.1 × 49 + 80 × 50 = ~5280 + 23,520 + 4,000 = ~33k effective tokens vs 244k uncached. **~87% reduction**.

## Cross-references

- **`grounded-llm-prompt`** — the citation + number-labeling rule blocks go in the cacheable prefix. Composing them properly is half the win.
- **`agent-tool-design`** — tool definitions are the first thing in the prefix; well-written tool descriptions cache exactly once.
- **`multi-pass-llm-pipeline`** — Pass 1 and Pass 2 system prompts cache independently; cache shaping doubles when you have two stable prompts.

## Files in this skill

```
prompt-cache-shaping/
├── SKILL.md                                  (this file)
├── examples/
│   └── aida-recommendation-cache-flow.md     (the worked example expanded with code)
└── references/
    ├── vendor-anthropic.md                    (cache_control breakpoints, TTL, 20-block lookback, billing)
    └── vendor-openai.md                       (automatic caching, 128-token alignment, extended retention)
```

## Sources

- [Anthropic — Prompt caching](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) (T1, current 2026)
- [OpenAI — Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) (T1)
- [OpenAI Cookbook — Prompt Caching 101 / 201](https://cookbook.openai.com/) (T1)
