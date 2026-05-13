// Pass 1 — Decompose (cheap model)
//
// Goal: turn user input into a coarse, well-typed structure. Sentinel defaults
// occupy fields that Pass 2 will fill. Sentinels are INVALID values so that
// any leak past Pass 2 (model skipped a field) crashes downstream loudly.

import { z } from 'zod';

// ─── Schema ─────────────────────────────────────────────────────────────────

// SENTINEL_NUMBER must be outside the legitimate range of any scored field.
// If real scores are in [0, 1], pick -1. If [-1, 1], pick -99. The rule is:
// downstream code that reads the field should crash on the sentinel, not
// render it as a legitimate value.
export const SENTINEL_NUMBER = -1;
export const SENTINEL_ENUM = '__pending__' as const;

const StepSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  // Fields Pass 1 owns:
  inputs: z.array(z.string()),
  outputs: z.array(z.string()),
  estDurationMins: z.number().int().min(1),
  // Fields Pass 2 will fill — sentinel-initialized by Pass 1.
  // The .refine() ensures the schema accepts the sentinel value here AND
  // accepts a real score in Pass 2; downstream code checks for the sentinel
  // and routes accordingly.
  userPain: z.number(),       // Pass 2 will set [0, 5]; Pass 1 emits SENTINEL_NUMBER
  systemImpact: z.number(),   // Same
  compositeScore: z.number(), // Same — Pass 2 sets [0, 1]
  aiRung: z.string(),         // Pass 2 will pick from enum; Pass 1 emits SENTINEL_ENUM
});

export const Pass1OutputSchema = z.object({
  workflowTitle: z.string(),
  steps: z.array(StepSchema).min(1).max(15),
});

export type Pass1Output = z.infer<typeof Pass1OutputSchema>;

// ─── Prompt ─────────────────────────────────────────────────────────────────

export const PASS1_SYSTEM_PROMPT = `You are decomposing a user-described workflow into discrete steps.

Decompose the workflow into 5–15 steps. For each step, fill these fields:
- id: a short stable identifier like "1.1", "1.2", "2.1"
- title: imperative verb phrase, ≤8 words
- description: one sentence explaining what happens in this step
- inputs: array of strings naming what comes in to this step
- outputs: array of strings naming what comes out
- estDurationMins: integer, your best estimate

For these fields, EMIT THE SENTINEL VALUES. A later pass will fill them:
- userPain: ${SENTINEL_NUMBER}
- systemImpact: ${SENTINEL_NUMBER}
- compositeScore: ${SENTINEL_NUMBER}
- aiRung: "${SENTINEL_ENUM}"

Do not score, rank, or prioritize the steps. Do not invent inputs/outputs not implied by the user's description. Return JSON matching the schema. No prose, no markdown fences.`;

// ─── Call ───────────────────────────────────────────────────────────────────

export interface CallLLM {
  (params: { system: string; user: string; jsonMode: true }): Promise<{
    content: string;
    tokens: { in: number; out: number };
  }>;
}

export async function runPass1(
  userInput: string,
  callCheapModel: CallLLM,
): Promise<{ output: Pass1Output; tokens: { in: number; out: number } }> {
  const response = await callCheapModel({
    system: PASS1_SYSTEM_PROMPT,
    user: userInput,
    jsonMode: true,
  });

  const parsed = Pass1OutputSchema.parse(JSON.parse(response.content));
  return { output: parsed, tokens: response.tokens };
}
