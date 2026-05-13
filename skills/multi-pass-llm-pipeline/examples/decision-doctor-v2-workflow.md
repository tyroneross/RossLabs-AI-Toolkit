# Worked Example — Decision Doctor v2 Workflow

This is the real pipeline that motivated the skill. It runs in `decision-doctor-cc` (Aida), branch `v2-pain-to-ai-recommendation`, gated behind `DD_ENGINE_MODE=v2-workflow`. Files referenced here are the canonical implementation; the skill snippets are abstracted from them.

## End-to-end flow

```
User intake → "I spend 4 hours/week on prior-auth letters."
       ↓
Pass 1 — Decompose (Groq Llama 3.3 70B, ~270ms)
   Output: 5 workflow steps with sentinel scores
       ↓
Pass 2 — Score (OpenAI gpt-4o-mini, ~1.8s)
   Output: 5 steps with filled scores [0–5 pain, 0–5 impact, 0–1 composite, enum rung]
       ↓
Deterministic post-process (TS, ~5ms)
   Output: top-3 lynchpins by formula 0.4·pain + 0.4·impact + 0.2·composite
       ↓
Artifact build (per lynchpin)
   Output: starter prompts / checklists / skill scaffolds matched from the library
```

## Example trace

```
methodTrace:
  pass1.decompose @v0.1.0 (271ms, 184→412tok) model=groq/llama-3.3-70b
  pass2.score @v0.1.0 (1812ms, 698→287tok) model=openai/gpt-4o-mini
  post.lynchpin @v0.1.0 (4ms)
  artifact.build @v0.1.0 (834ms, 312→519tok) model=openai/gpt-4o-mini
Total: 2.92s, $0.0021
```

## Why the two-pass split paid off here

The same task with one Opus call (an early prototype):
- ~4.2s, $0.04 per run, scores varied ±0.15 across re-runs of the same input.

Two-pass:
- ~2.9s, $0.002 per run, scores reproducible to ±0 (formula is deterministic; only Pass 2's score input varies, and on identical input Pass 2 is stable within ~±0.05).

The user-visible "explain this recommendation" panel reads `methodTrace` and shows: which model produced which fields, what the formula was, when each weight bumped. That panel does not exist if the formula is in the prompt.

## Real Pass 1 prompt (excerpt)

```
You are decomposing a solo healthcare practitioner's workflow into 5–10 activity steps.

Each step:
- id (dotted HTA, e.g. "1.1")
- title (imperative verb, ≤8 words)
- description (one sentence)
- inputs / outputs (arrays of strings)
- estDurationMins (integer)
- dataNeeded ("low" | "pii" | "phi")

Sentinel-fill these — a later pass owns them:
- userPain: -1
- systemImpact: -1
- compositeScore: -1
- aiRung: "__pending__"

Return JSON. No prose, no fences.
```

## Real Pass 2 prompt (excerpt)

```
You score each step in a decomposed workflow on dimensions the user can audit.

Per step:
- userPain (0–5): how painful is this step for the user today?
- systemImpact (0–5): if eliminated or automated, how much does the workflow improve?
- compositeScore (0–1): your overall AI-fit judgment using the rubric:
    + predictable inputs
    + well-defined outputs
    + high volume
    + low exception rate
    + low data sensitivity
- aiRung: pick by compositeScore threshold:
    < 0.3 → "none"
    0.3–0.5 → "prompt"
    0.5–0.7 → "skill"
    0.7–0.85 → "plugin"
    ≥ 0.85 → "agent"

Replace every sentinel value (-1, "__pending__") with a real score.
Return JSON. No prose, no fences.
```

## Real post-process (excerpt)

```ts
const FORMULA_VERSION = 'v0.1.0';
const WEIGHT_PAIN = 0.4;
const WEIGHT_IMPACT = 0.4;
const WEIGHT_AI_FIT = 0.2;

function lynchpinScore(p: number, i: number, c: number): number {
  return WEIGHT_PAIN * (p / 5) + WEIGHT_IMPACT * (i / 5) + WEIGHT_AI_FIT * c;
}

const ranked = steps
  .map(s => ({ ...s, score: lynchpinScore(s.userPain, s.systemImpact, s.compositeScore) }))
  .sort((a, b) => b.score - a.score);

const lynchpins = ranked.slice(0, 3).filter(s => s.score >= 0.3);
```

## What this example doesn't show

- **Library retrieval (stub-pending)**: the artifact-build step currently invents starter prompts. The production path will retrieve from a library + KB before generating, then methodTrace will include a `retrieval.bm25-vector-rrf` stage. (See the `hybrid-rag-retrieval` skill for that pattern.)
- **The `grounded-llm-prompt` blocks**: Pass 2 and artifact-build prompts in production compose the citation contract + number-labeling rules. Omitted here for readability.
- **Cost budget**: in production, a request handler checks cumulative token cost across stages and refuses to proceed past Pass 2 if the budget would blow. The trace shows where each call landed.
