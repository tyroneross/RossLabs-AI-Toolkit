---
name: agent-eval-harness
description: Use when building an evaluation harness for an LLM agent, RAG pipeline, or prompt — when the question is "is this actually working?" Encodes Anthropic and OpenAI's published 2025–2026 eval guidance — start with 20–50 real-failure tasks (not synthetic happy-paths), use three grader types in the right places (deterministic code / LLM judge / human review), measure pass@k vs pass^k for production reliability, grade outcomes not reasoning paths, calibrate the LLM judge against human review before trusting it, and detect eval saturation. Triggers on "build an eval", "build evals", "eval harness", "is this prompt working", "regression test for LLM", "how do I know my agent is better", "LLM judge", "pass@k", "compare two prompts on real data", "the prompt looks fine but production is broken". Vendor-neutral with starter templates.
author: Tyrone Ross
version: 0.1.0
tags: [evals, llm-judge, agent-evaluation, regression, anthropic, openai]
category: agent-engineering
difficulty: intermediate
---

# Agent Eval Harness

## Why this skill exists

Anthropic ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)) and OpenAI ([Structured Outputs § evals](https://platform.openai.com/docs/guides/structured-outputs), [Cookbook eval guides](https://cookbook.openai.com/)) now both publish the same eval methodology, and both lead with the same advice: **build evals before you scale anything**. Most teams skip this because evals feel like overhead. They aren't — they're the only signal that "the new prompt is better" or "this regression is real" or "the agent is ready to ship." Without them, every change is a vibe-driven gamble.

This skill is the methodology + the templates to start in 30 minutes.

## The four-step cycle

```
┌─────────────────────────┐
│ 1. Collect 20–50 tasks  │  Real failures from production logs, support tickets, edge cases.
│    from real failures   │  NOT synthetic happy-paths.
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│ 2. Pick graders per     │  Deterministic code where possible (cheapest, most reliable).
│    task                 │  LLM judge for prose / open-ended (calibrate first).
│                         │  Human for the ambiguous remainder (small subset).
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│ 3. Run pass@k AND       │  pass@k = at least 1 of k attempts succeeds.
│    pass^k               │  pass^k = ALL k attempts succeed. Production reliability.
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│ 4. Recalibrate the      │  Sample 10–20 judge verdicts; compare to human review.
│    judge each release   │  If judge ≠ human, fix the judge prompt, not the model.
└─────────────────────────┘
```

## Step 1 — Collect 20–50 tasks from real failures

**Real failures, not synthetic.** Anthropic's explicit guidance: synthetic eval sets test what you imagine the agent will face; real-failure sets test what it actually faces. The hit rate on the former predicts nothing about production.

Sources for real-failure tasks:
- Production logs of failed agent runs.
- Support tickets where the user complained the agent was wrong.
- Edge cases you've fixed bugs for (regression layer).
- Domain-expert-curated hard cases.

Count: **20 minimum, 50 typical, 200+ when the system stabilizes.** 20 is enough to detect systematic regressions; 50 starts to capture distributional shifts; 200 lets you slice by category. Don't wait for 200 to start — start with 20 you have today.

See `templates/eval-task.json` for the per-task schema.

## Step 2 — Pick graders per task

Three grader types, in order of preference:

### A. Deterministic code (use whenever possible)

```ts
// Check for exact output, presence of a citation token, schema validity, etc.
function gradeCitation(output: string, expectedSourceIds: string[]): boolean {
  const matches = [...output.matchAll(/\[\[doc:([a-f0-9-]+)\]\]/g)].map(m => m[1]);
  return expectedSourceIds.every(id => matches.includes(id));
}
```

Use when:
- Output has a well-defined structure (JSON, tokens, schema).
- Correctness is unambiguous (numeric answer, classification label, tool call shape).
- You can write a 5–20 line function that says yes/no.

Cheapest, most reliable, no calibration needed. Default to this.

### B. LLM-as-judge (for prose / open-ended)

```ts
async function gradeAnswerQuality(question: string, answer: string, criteria: string): Promise<{score: 1|2|3|4|5; reason: string}> {
  // Call cheap model with a careful prompt — see templates/judge-prompt.md
}
```

Use when:
- Output is prose and quality is judgmental.
- Multiple correct answers exist.
- You have a clear rubric you can describe to the judge.

**Always calibrate first** (step 4). An uncalibrated LLM judge is a noise generator.

### C. Human review (for the ambiguous remainder)

Reserve for:
- Tasks where the rubric itself is unclear.
- Tail cases the judge gets wrong even after calibration.
- The judge-calibration step itself (humans grade 10–20 to set the bar).

Keep this subset small (5–10% of total). Humans are expensive; budget accordingly.

## Step 3 — pass@k AND pass^k

**pass@k** = at least 1 of k attempts produces a passing result. Measures *capability*: can the model do this at all?

**pass^k** = ALL k attempts pass. Measures *reliability*: can the model do this every time?

```
For each task:
  Run the agent k times (k=3 or k=5 typical).
  pass@k = OR(any of the k attempts passed)
  pass^k = AND(all k attempts passed)

Eval score:
  Capability  = mean(pass@k across tasks)
  Reliability = mean(pass^k across tasks)
```

Production reliability requires pass^k. A 90% pass@1 model that fails every 5th call is unshippable; a 70% pass^5 model is.

## Step 4 — Recalibrate the judge

LLM judges drift. New model versions change calibration; minor judge-prompt edits change scores; the eval set itself can shift the judge's tone-of-distribution.

Each release cycle:
1. Sample 10–20 judge verdicts (mix of pass and fail).
2. Have a human grade them blind.
3. Compute agreement rate (Cohen's kappa or simple % agreement).
4. If agreement < 80%, fix the judge prompt — not the underlying model.

Track agreement over time. A trending-down agreement is the loudest signal that the eval is broken before the model is.

## Anti-patterns

- **Eval on what's easy to measure, not what matters.** "BLEU score" is easy; "did the model help the user?" is what matters. Pick rubrics that predict business outcomes, not what's grep-able.
- **Synthetic happy-path eval set.** Generated from a template, all easy, the model passes 99% and nobody knows the production regression exists. Real-failure tasks only.
- **Single-run scoring.** k=1 misses reliability tail. Always k≥3.
- **Trusted judge with no calibration.** "GPT-4 as judge" looks rigorous; uncalibrated it's a coin flip on hard cases. Calibrate before publishing scores.
- **Grading reasoning paths.** "Did the agent think the right way?" — grade outcomes only. Anthropic's published rule. Path-grading punishes models for taking valid alternate routes.
- **Eval-set leak to training.** If you fine-tune or RAG-train on data that overlaps the eval set, scores inflate. Keep the eval set sealed.
- **Eval saturation invisible.** Once every model passes 95%+ on your set, the eval is over. Build harder tasks; retire saturated categories.

## Vendor-specific notes

See `references/anthropic-evals.md` and `references/openai-evals.md` for per-vendor mechanics (Anthropic's grader types, OpenAI's eval API, dashboard tools, cost optimizations).

## When NOT to use this skill

- One-shot scripts that don't need to be reliable.
- Pure UI code with no LLM in the loop.
- Internal tools where the user is also the developer (you'll notice the failures).
- Demos for clients (build evals AFTER you've validated the demo flies).

## Cross-references

- **`prompt-builder`** — write the prompts you'll eval.
- **`grounded-llm-prompt`** — eval criteria for citation + number-labeling fire here.
- **`multi-pass-llm-pipeline`** — eval each pass separately; the audit trail makes per-stage eval cheap.
- **`build-loop:optimize`** — once you have evals, optimize-loop uses them as the convergence metric.

## Files in this skill

```
agent-eval-harness/
├── SKILL.md                            (this file)
├── templates/
│   ├── eval-task.json                  (one-task schema with grader fields)
│   ├── judge-prompt.md                 (LLM-judge prompt template)
│   └── runner.ts                       (vendor-neutral eval runner with pass@k + pass^k)
└── references/
    ├── anthropic-evals.md              (grader types, model picks, cost notes)
    └── openai-evals.md                 (eval API, dashboard, structured-outputs evals)
```

## Sources

- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (T1, 2025)
- [OpenAI — Structured outputs § evals](https://platform.openai.com/docs/guides/structured-outputs) (T1)
- [OpenAI Cookbook — Evaluation patterns](https://cookbook.openai.com/) (T1)
- [Anthropic — Skill best practices § build evals before extensive docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) (T1)
