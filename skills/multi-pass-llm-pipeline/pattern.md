# Pattern — Two-Pass LLM Pipeline (1 page)

For when an LLM workflow needs structured output + calibrated scoring + auditable explanation. The naive shape (one frontier-model call) fails three ways: formula lives in the prompt (irreproducible), precision-model rates pay for cheap work, no graceful degradation. The pattern fixes all three.

## Shape

```
┌──────────┐    ┌─────────────────────────┐    ┌────────────────────────┐    ┌────────────────────────┐
│ Input    │ →  │ Pass 1 — Decompose       │ →  │ Pass 2 — Score         │ →  │ Deterministic post     │
│          │    │ Cheap model              │    │ Precision model        │    │ Formula in TS          │
│          │    │ Emits structure          │    │ Fills scored fields    │    │ Top-K selection        │
│          │    │ Sentinel defaults in     │    │ against strict Zod     │    │ Rationale strings      │
│          │    │ scored fields            │    │ Retry once → fallback  │    │ methodTrace accumulate │
│          │    │ JSON mode                │    │ to Pass 1 defaults     │    │                        │
└──────────┘    └─────────────────────────┘    └────────────────────────┘    └────────────────────────┘
```

## Five rules

1. **Sentinel defaults must be invalid values.** Not `0`, not `"none"`. Use `-1` for numeric scores, `"__pending__"` for enums. Make sentinel leaks crash, not render.
2. **The ranking formula lives in TypeScript, not in the prompt.** Weights are named constants. When a weight changes, version-bump the methodTrace stage.
3. **Pass 2 retries once, then falls back to Pass 1 defaults.** Three retries with the same model rarely converge. Fall back and emit a `pass2.skipped` trace stage so the UI can show "partial result, scores not computed."
4. **Different models per pass.** If you can afford the precision model for Pass 1, you don't need the two-pass design at all. The split is the whole point.
5. **Every stage appends to methodTrace.** A score that isn't traceable to a stage + version + input hash is a score that can't be audited later. The trace is the product.

## When to use

- ≥3 fields the model must score against well-defined criteria.
- Output will be shown with an "explain" or "audit" affordance.
- Cost-sensitive workload at scale (the cheap-pass savings compound).
- Need to reproduce a score given the same input, months later.

## When not to use

- Single-recommendation workflows with no scoring → one frontier-model call is simpler.
- Conversational chat → there's no decomposition step.
- Low-stakes ranking where any reasonable order will do → not worth the wiring.
- When you can't measure quality with eval cases — the two-pass split needs *some* notion of "did Pass 2 do better than Pass 1?" to justify itself.

## Hand-off

The four snippets in `snippets/` are copy-pasteable starting points. The worked example in `examples/decision-doctor-v2-workflow.md` shows what the pipeline looks like end-to-end with real prompts. The validation hooks from the `grounded-llm-prompt` skill apply to Pass 2 if its output includes prose for users.
