// Pass 2 — Score (precision model)
//
// Goal: fill scored fields against a STRICT schema. Retry once on parse
// failure with the error appended. If retry 1 also fails, fall back to
// Pass 1's sentinel defaults and emit a `pass2.skipped` methodTrace stage —
// never retry a third time.

import { z } from 'zod';
import { Pass1Output, SENTINEL_NUMBER, SENTINEL_ENUM } from './pass1-decompose';
import type { CallLLM } from './pass1-decompose';

// ─── Schema ─────────────────────────────────────────────────────────────────

const AI_RUNGS = ['none', 'prompt', 'skill', 'plugin', 'agent'] as const;
type AiRung = typeof AI_RUNGS[number];

// Strict scored-step schema. Note: legitimate values only — no sentinel
// allowed in Pass 2's output. The model MUST replace the sentinels.
const ScoredStepSchema = z.object({
  id: z.string(),
  userPain: z.number().min(0).max(5),
  systemImpact: z.number().min(0).max(5),
  compositeScore: z.number().min(0).max(1),
  aiRung: z.enum(AI_RUNGS),
});

export const Pass2OutputSchema = z.object({
  scoredSteps: z.array(ScoredStepSchema),
});

export type Pass2Output = z.infer<typeof Pass2OutputSchema>;

// ─── Prompt ─────────────────────────────────────────────────────────────────

export const PASS2_SYSTEM_PROMPT = `You score each step in a decomposed workflow on four dimensions.

For every step in the input, return a scored object with:
- id: copy from the input
- userPain: 0–5. How painful is this step for the user today? 0 = trivial, 5 = blocks them.
- systemImpact: 0–5. If this step were eliminated or automated, how much does the overall workflow improve? 0 = no effect, 5 = transformative.
- compositeScore: 0–1. Your overall judgment of AI fit for this step. Use the rubric: predictable inputs (+), well-defined outputs (+), high volume (+), low exception rate (+), low data sensitivity (+).
- aiRung: one of "none", "prompt", "skill", "plugin", "agent". Use thresholds:
  • compositeScore < 0.3 → "none"
  • 0.3 ≤ compositeScore < 0.5 → "prompt"
  • 0.5 ≤ compositeScore < 0.7 → "skill"
  • 0.7 ≤ compositeScore < 0.85 → "plugin"
  • compositeScore ≥ 0.85 → "agent"

Do not invent steps. Do not omit steps. Return JSON matching the schema. No prose, no markdown fences.`;

// ─── Call with retry-and-fallback ───────────────────────────────────────────

export interface Pass2Result {
  output: Pass2Output;
  source: 'pass2' | 'fallback-from-pass1';
  tokens: { in: number; out: number };
  retries: number;
}

export async function runPass2(
  pass1: Pass1Output,
  callPrecisionModel: CallLLM,
): Promise<Pass2Result> {
  const userPrompt = JSON.stringify({ steps: pass1.steps }, null, 2);

  // Attempt 1
  let lastError: string | null = null;
  try {
    const r = await callPrecisionModel({
      system: PASS2_SYSTEM_PROMPT,
      user: userPrompt,
      jsonMode: true,
    });
    const parsed = Pass2OutputSchema.parse(JSON.parse(r.content));
    return { output: parsed, source: 'pass2', tokens: r.tokens, retries: 0 };
  } catch (e) {
    lastError = e instanceof Error ? e.message : String(e);
  }

  // Retry once with error appended
  try {
    const r = await callPrecisionModel({
      system: PASS2_SYSTEM_PROMPT,
      user: `${userPrompt}\n\n--- PREVIOUS ATTEMPT FAILED VALIDATION ---\nError: ${lastError}\nPlease re-emit JSON that strictly matches the schema. Replace every sentinel value (${SENTINEL_NUMBER}, "${SENTINEL_ENUM}") with a real score.`,
      jsonMode: true,
    });
    const parsed = Pass2OutputSchema.parse(JSON.parse(r.content));
    return { output: parsed, source: 'pass2', tokens: r.tokens, retries: 1 };
  } catch (e) {
    // Fallback: use Pass 1's sentinel-defaulted output. Downstream code
    // detects this via `source === 'fallback-from-pass1'` and either emits
    // a partial UI ("scores not computed") or refuses the response.
    const fallback: Pass2Output = {
      scoredSteps: pass1.steps.map(s => ({
        id: s.id,
        userPain: 0,
        systemImpact: 0,
        compositeScore: 0,
        aiRung: 'none' as AiRung,
      })),
    };
    return {
      output: fallback,
      source: 'fallback-from-pass1',
      tokens: { in: 0, out: 0 },
      retries: 2,
    };
  }
}
