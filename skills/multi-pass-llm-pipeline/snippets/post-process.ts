// Deterministic post-process
//
// The ranking formula lives here, NOT in any prompt. Weights are named
// constants exported for transparency. When you change a weight, bump
// FORMULA_VERSION so downstream methodTrace records a different stage.

import { Pass1Output } from './pass1-decompose';
import { Pass2Output } from './pass2-score';

// ─── Constants ──────────────────────────────────────────────────────────────

export const FORMULA_VERSION = 'v0.1.0' as const;

// Lynchpin score weights. Sum to 1.0.
// Bump FORMULA_VERSION when any of these change.
export const WEIGHT_PAIN = 0.4;
export const WEIGHT_IMPACT = 0.4;
export const WEIGHT_AI_FIT = 0.2;

export const LYNCHPIN_THRESHOLD = 0.3;
export const TOP_K = 3;

// ─── Output type ────────────────────────────────────────────────────────────

export interface LynchpinResult {
  stepId: string;
  title: string;
  lynchpinScore: number;
  isLynchpin: boolean;
  rationale: string;
  rung: string;
}

export interface PostProcessOutput {
  formulaVersion: typeof FORMULA_VERSION;
  weights: { pain: number; impact: number; aiFit: number };
  results: LynchpinResult[];
  topK: LynchpinResult[];
}

// ─── Formula ────────────────────────────────────────────────────────────────

function computeLynchpinScore(
  userPain: number,    // 0–5
  systemImpact: number, // 0–5
  compositeScore: number, // 0–1
): number {
  return (
    WEIGHT_PAIN * (userPain / 5) +
    WEIGHT_IMPACT * (systemImpact / 5) +
    WEIGHT_AI_FIT * compositeScore
  );
}

function buildRationale(result: {
  title: string;
  userPain: number;
  systemImpact: number;
  rung: string;
}): string {
  const painDesc = result.userPain >= 4 ? 'high-pain' : result.userPain >= 2 ? 'moderate-pain' : 'low-pain';
  const impactDesc = result.systemImpact >= 4 ? 'high-impact' : result.systemImpact >= 2 ? 'moderate-impact' : 'low-impact';
  return `${painDesc}, ${impactDesc}, AI rung: ${result.rung}`;
}

// ─── Entry point ────────────────────────────────────────────────────────────

export function runPostProcess(
  pass1: Pass1Output,
  pass2: Pass2Output,
): PostProcessOutput {
  const scoreById = new Map(pass2.scoredSteps.map(s => [s.id, s]));

  const results: LynchpinResult[] = pass1.steps.map(step => {
    const scored = scoreById.get(step.id);
    if (!scored) {
      // Pass 2 omitted this step — possible after fallback. Score = 0.
      return {
        stepId: step.id,
        title: step.title,
        lynchpinScore: 0,
        isLynchpin: false,
        rationale: 'no Pass 2 score available',
        rung: 'none',
      };
    }
    const lynchpinScore = computeLynchpinScore(
      scored.userPain,
      scored.systemImpact,
      scored.compositeScore,
    );
    return {
      stepId: step.id,
      title: step.title,
      lynchpinScore,
      isLynchpin: lynchpinScore >= LYNCHPIN_THRESHOLD,
      rationale: buildRationale({
        title: step.title,
        userPain: scored.userPain,
        systemImpact: scored.systemImpact,
        rung: scored.aiRung,
      }),
      rung: scored.aiRung,
    };
  });

  const ranked = [...results].sort((a, b) => b.lynchpinScore - a.lynchpinScore);
  const topK = ranked.slice(0, TOP_K).filter(r => r.isLynchpin);

  return {
    formulaVersion: FORMULA_VERSION,
    weights: { pain: WEIGHT_PAIN, impact: WEIGHT_IMPACT, aiFit: WEIGHT_AI_FIT },
    results,
    topK,
  };
}
