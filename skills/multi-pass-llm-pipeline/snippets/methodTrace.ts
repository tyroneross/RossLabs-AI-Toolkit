// methodTrace — audit accumulator
//
// Every stage of the pipeline appends one entry. Downstream "explain" UI
// reads this array to reconstruct the score for any output. inputHash makes
// runs comparable across time; version makes formula changes visible.

import { createHash } from 'node:crypto';

export interface MethodTraceEntry {
  stage: string;          // 'pass1.decompose' | 'pass2.score' | 'pass2.skipped' | 'post.lynchpin'
  version: string;        // 'v0.1.0' — bump when prompt or formula changes
  inputHash: string;      // sha256(stringified input) — first 12 chars
  output: unknown;        // the stage's emitted value, for cross-run diffs
  timing: { startMs: number; durationMs: number };
  model?: string;         // for LLM stages
  tokens?: { in: number; out: number };
  notes?: string;         // free-form, used by 'pass2.skipped' to record fallback reason
}

export type MethodTrace = MethodTraceEntry[];

export function hashInput(input: unknown): string {
  return createHash('sha256')
    .update(typeof input === 'string' ? input : JSON.stringify(input))
    .digest('hex')
    .slice(0, 12);
}

/**
 * Wrap a stage execution to auto-append a methodTrace entry.
 * Use like:
 *   const result = await traceStage(trace, {
 *     stage: 'pass1.decompose',
 *     version: 'v0.1.0',
 *     input: userInput,
 *     model: 'groq-llama-3.3-70b',
 *   }, async () => runPass1(userInput, callGroq));
 */
export async function traceStage<T extends { tokens?: { in: number; out: number } }>(
  trace: MethodTrace,
  meta: { stage: string; version: string; input: unknown; model?: string; notes?: string },
  fn: () => Promise<T>,
): Promise<T> {
  const startMs = Date.now();
  const inputHash = hashInput(meta.input);
  try {
    const result = await fn();
    trace.push({
      stage: meta.stage,
      version: meta.version,
      inputHash,
      output: result,
      timing: { startMs, durationMs: Date.now() - startMs },
      model: meta.model,
      tokens: result.tokens,
      notes: meta.notes,
    });
    return result;
  } catch (err) {
    trace.push({
      stage: `${meta.stage}.error`,
      version: meta.version,
      inputHash,
      output: { error: err instanceof Error ? err.message : String(err) },
      timing: { startMs, durationMs: Date.now() - startMs },
      model: meta.model,
      notes: meta.notes,
    });
    throw err;
  }
}

/** Compact summary for UI display. */
export function summarizeTrace(trace: MethodTrace): string {
  return trace
    .map(t => {
      const tok = t.tokens ? ` ${t.tokens.in}→${t.tokens.out}tok` : '';
      const ms = `${t.timing.durationMs}ms`;
      return `${t.stage} @${t.version} (${ms}${tok})`;
    })
    .join('\n');
}
