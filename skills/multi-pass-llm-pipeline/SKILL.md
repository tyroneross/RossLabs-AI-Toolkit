---
name: multi-pass-llm-pipeline
description: Use when an LLM workflow needs structured output AND calibrated scoring AND an auditable decision trail. Encodes the two-pass pattern - Pass 1 (cheap/fast model like Groq, Haiku, or gpt-4o-mini) emits coarse structure with sentinel defaults for fields the second pass will fill; Pass 2 (precision model like Opus, gpt-4o, or Claude Sonnet) fills the scored fields against a strict Zod schema; a deterministic TS post-process computes the final ranking formula. Triggers on "two-phase LLM", "two-pass LLM", "decompose then score", "classify then rank", "structured output with audit", "auditable LLM workflow", "sentinel defaults", "deterministic post-process", "the LLM scoring is opaque", "I need to show my work", "the model keeps drifting on the ranking formula". Designed for workflow decomposition, multi-criteria scoring, classify-then-rank tasks. Not for single-shot completion, conversational chat, or low-stakes ranking where one frontier-model call is good enough.
author: Tyrone Ross
version: 0.1.0
tags: [llm-pipeline, structured-output, audit-trail, zod, multi-pass, scoring, agentic-workflow]
category: prompt-engineering
difficulty: intermediate
---

# Multi-Pass LLM Pipeline

## Problem

When an LLM workflow has to produce structured output AND calibrated scores AND an auditable explanation, the natural instinct — "one big prompt to a frontier model" — fails three ways:

1. **The formula is in the prompt.** Six months later, no one can explain how a score was computed because the model decided. Re-running the same input on the same model gives different scores. The decision is not reproducible.
2. **You pay precision-model rates for cheap work.** Decomposition (listing the steps of a task) doesn't need Opus; scoring those steps against well-defined criteria does. One-pass collapses both into the expensive tier.
3. **There's no graceful degradation.** If the precision model is rate-limited or down, you have nothing. A two-pass design can return a "we got the structure but not the scores" partial.

The fix is a deliberate three-stage shape:

```
Pass 1 (cheap model) → Sentinel-default structure → Pass 2 (precision model) → Filled scores → Deterministic post-process → Final ranking + methodTrace
```

The formula moves from the prompt into TypeScript, where it can be tested, version-controlled, and audited. The two passes use the right tier for the right job. Failures degrade meaningfully.

## The pattern in one diagram

```
┌──────────────┐    ┌───────────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌───────────────┐
│  User input  │ →  │ Pass 1 (cheap)        │ →  │ Pass 2       │ →  │ Deterministic   │ →  │ Final output  │
│              │    │ Decompose / classify  │    │ (precision)  │    │ post-process    │    │ + methodTrace │
│              │    │ Sentinel defaults     │    │ Fill scores  │    │ Apply formula   │    │               │
│              │    │ in scored fields      │    │ vs Zod       │    │ Pick top-K      │    │               │
└──────────────┘    └───────────────────────┘    └──────────────┘    └─────────────────┘    └───────────────┘
                            ↓                            ↓                    ↓
                       (parse failure?)            (parse failure?)      (formula lives in
                       retry → fail-soft           retry → Pass 1         TS, never in the
                                                   defaults                prompt)
```

## Pass 1 — Decompose (cheap model)

**Goal**: turn the user's input into a coarse but well-typed structure. Speed and cost matter; precision on the scored fields does not.

**Model choice**: a cheap, fast, JSON-mode-capable model. Groq Llama 3.x, Claude Haiku, gpt-4o-mini, or Gemini Flash. Pick by latency and JSON-mode reliability, not by reasoning ceiling.

**Prompt requirements**:

1. Tell the model what it owns (the structure) and what it must NOT fill (the scored fields).
2. Provide the Zod schema *or* an inline example with sentinel values, so the model sees what "leave this alone" looks like.
3. **Sentinel defaults must be invalid values.** If the field is a 0–1 score, the sentinel is `-1`, not `0`. If the field is an enum, the sentinel is a string clearly not in the enum (e.g. `"__pending__"`). The point: a leaked sentinel must blow up loudly in downstream code, never silently render as zero.

See `snippets/pass1-decompose.ts` for the full pattern.

## Pass 2 — Score (precision model)

**Goal**: fill the scored fields against a strict Zod schema. Quality and calibration matter; latency budget is whatever it needs to be (within reason).

**Model choice**: a frontier reasoning model. Claude Opus/Sonnet, gpt-4o, Gemini Pro. Use the same model across calls so calibration is stable.

**Prompt requirements**:

1. Pass 1's output is included as context, *with the sentinel fields visible*. The model must replace them.
2. The Zod schema is the contract. Use JSON mode and the strictest schema you can write — explicit min/max bounds, enums for everything, no free-form strings unless absolutely needed.
3. On parse failure, retry **once** with the parse error appended ("Your previous response failed schema validation: <error>. Please re-emit with the schema constraints respected."). If retry 1 also fails, fall back to Pass 1's defaults — *not* to a third retry.

See `snippets/pass2-score.ts` for the retry-and-fallback pattern.

## Deterministic post-process

**Goal**: compute the final ranking, select top-K, build rationales, accumulate the audit trail.

**Implementation rule**: the formula lives in TypeScript, not in the prompt. The model is for filling field values; the formula combines them.

```ts
// Example: lynchpin selection
const lynchpinScore =
  WEIGHT_PAIN * (step.userPain / 5) +
  WEIGHT_IMPACT * (step.systemImpact / 5) +
  WEIGHT_FIT * step.compositeScore;
```

Weights are constants, named, exported. When a weight changes, version-bump the methodTrace stage so downstream consumers know the score basis changed.

See `snippets/post-process.ts` for the full pattern.

## methodTrace — the audit accumulator

Every pass and every post-process step appends to a `methodTrace` array. The trace is the artifact a downstream UI shows in an "explain this score" panel.

```ts
type MethodTrace = Array<{
  stage: string;       // 'pass1.decompose' | 'pass2.score' | 'post.lynchpin'
  version: string;     // 'v0.3.0' — bump when formula/prompt changes
  inputHash: string;   // sha256 of the input to this stage
  output: unknown;     // the stage's emitted value (for diffing across runs)
  timing: { startMs: number; durationMs: number };
  model?: string;      // for LLM stages
  tokens?: { in: number; out: number };
}>;
```

See `snippets/methodTrace.ts` for the accumulator helper.

## Anti-patterns

- **Sentinel defaults that look real.** `aiRung: "none"` with `compositeScore: 0` looks like a legitimate "no AI fit" result downstream. Use `compositeScore: -1` or `aiRung: "__pending__"` so a leaked sentinel crashes loudly.
- **Putting the ranking formula in the prompt.** "Compute lynchpinScore as 0.4·pain + 0.4·impact + 0.2·composite, then return the top 3." The model will drift; the formula will not be reproducible; you cannot version it. Move it to TS.
- **Retrying Pass 2 more than once.** Three retries with the same model rarely converge. Fall back to Pass 1 defaults and surface the partial result with a methodTrace stage `pass2.skipped`.
- **Using the same model for both passes.** If you can afford the precision model for Pass 1, you don't need the two-pass design — just call once. The pattern is justified by the cost/quality split.
- **Hidden post-process.** If the deterministic step doesn't show up in methodTrace, an "explain" view won't be able to reproduce the score. Every weight, threshold, and formula bump must trace.

## Cost / latency math — when is two passes worth it?

| Workload | One pass (frontier) | Two passes (cheap + frontier) | Verdict |
|---|---|---|---|
| 1 turn / turn, low-value structured output (single recommendation) | $$, ~1.5s | $ + $$, ~0.4s + ~1.5s = ~1.9s | One pass. Two-pass is pure overhead. |
| Decompose 5–10 items, score each, rank top 3 | $$$$, ~2.5s, opaque scores | $ + $$$, ~0.4s + ~2.0s = ~2.4s, auditable | **Two passes.** Comparable latency, lower cost, auditable. |
| Decompose 20+ items, batch score | $$$$$, ~5s, drift risk | $ + $$$$ (batched), ~0.4s + ~3s = ~3.4s, auditable | **Two passes.** Cost difference grows fast. |

Rough rule: **if you have more than ~3 fields the model must score**, two passes wins on cost + auditability.

## Cross-references

- **`grounded-llm-prompt` skill** — Pass 2 prompts that surface prose to a user should compose the citation + number-labeling blocks from that skill.
- **`prompt-builder` skill** — for technique selection within each pass (Pass 1 often benefits from chain-of-thought; Pass 2 from skeleton-first + schema-guided extraction).
- **`pyramid-principle` skill** — for the shape of the rationale strings the post-process emits.

## Files in this skill

```
multi-pass-llm-pipeline/
├── SKILL.md                              (this file)
├── pattern.md                            (the architecture in 1 page, for hand-off)
├── snippets/
│   ├── pass1-decompose.ts                (Groq/Haiku decompose with sentinel defaults)
│   ├── pass2-score.ts                    (Opus/gpt-4o score against Zod with retry-and-fallback)
│   ├── post-process.ts                   (deterministic formula + top-K + rationales)
│   └── methodTrace.ts                    (audit accumulator + version stamping)
└── examples/
    └── decision-doctor-v2-workflow.md    (worked example: pain-path → 5 steps → score → lynchpin → horizons)
```
