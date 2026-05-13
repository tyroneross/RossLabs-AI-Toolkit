// Vendor-neutral eval runner
//
// Computes pass@k and pass^k across an eval set. Plug in your model client
// at runOne; plug in deterministic graders + judge graders as you build them.

import { readFileSync } from 'node:fs';

// ─── Types ──────────────────────────────────────────────────────────────────

interface EvalTask {
  task_id: string;
  category: string;
  input: Record<string, unknown>;
  expected: Record<string, unknown>;
  grader: { type: 'deterministic_code' | 'llm_judge' | 'human'; fn: string };
  k_runs: number;
  pass_k_threshold?: number;       // for pass@k (e.g. 0.95)
  pass_pow_k_threshold?: number;   // for pass^k (e.g. 0.80)
  tags?: string[];
}

interface RunResult {
  task_id: string;
  attempts: { passed: boolean; output: string; gradeDetail?: unknown }[];
  pass_at_k: boolean;     // any attempt passed
  pass_pow_k: boolean;    // all attempts passed
}

interface EvalReport {
  total_tasks: number;
  capability: number;         // mean(pass@k)
  reliability: number;        // mean(pass^k)
  per_category: Record<string, { capability: number; reliability: number; count: number }>;
  failed_tasks: string[];     // tasks where pass^k = false
}

// ─── Hooks you implement ────────────────────────────────────────────────────

export interface Runner {
  // Call your model/agent here. Returns the assistant's response.
  runOne(input: Record<string, unknown>): Promise<string>;

  // Map grader fn names ("graders.citation_and_number_labeling") to functions.
  graders: Record<string, (output: string, expected: Record<string, unknown>) => Promise<{passed: boolean; detail?: unknown}>>;
}

// ─── Core loop ──────────────────────────────────────────────────────────────

export async function runEval(tasks: EvalTask[], runner: Runner): Promise<{ report: EvalReport; runs: RunResult[] }> {
  const runs: RunResult[] = [];

  for (const task of tasks) {
    const attempts: RunResult['attempts'] = [];
    for (let i = 0; i < task.k_runs; i++) {
      const output = await runner.runOne(task.input);
      const grader = runner.graders[task.grader.fn];
      if (!grader) throw new Error(`Grader not registered: ${task.grader.fn}`);
      const { passed, detail } = await grader(output, task.expected);
      attempts.push({ passed, output, gradeDetail: detail });
    }
    runs.push({
      task_id: task.task_id,
      attempts,
      pass_at_k: attempts.some(a => a.passed),
      pass_pow_k: attempts.every(a => a.passed),
    });
  }

  const report = buildReport(tasks, runs);
  return { report, runs };
}

// ─── Aggregation ────────────────────────────────────────────────────────────

function buildReport(tasks: EvalTask[], runs: RunResult[]): EvalReport {
  const taskById = new Map(tasks.map(t => [t.task_id, t]));
  const total = runs.length;
  const capability = mean(runs.map(r => (r.pass_at_k ? 1 : 0)));
  const reliability = mean(runs.map(r => (r.pass_pow_k ? 1 : 0)));

  const byCategory: Record<string, { caps: number[]; rels: number[] }> = {};
  for (const r of runs) {
    const t = taskById.get(r.task_id)!;
    byCategory[t.category] ??= { caps: [], rels: [] };
    byCategory[t.category].caps.push(r.pass_at_k ? 1 : 0);
    byCategory[t.category].rels.push(r.pass_pow_k ? 1 : 0);
  }
  const per_category = Object.fromEntries(
    Object.entries(byCategory).map(([k, v]) => [
      k,
      { capability: mean(v.caps), reliability: mean(v.rels), count: v.caps.length },
    ]),
  );

  const failed_tasks = runs.filter(r => !r.pass_pow_k).map(r => r.task_id);

  return { total_tasks: total, capability, reliability, per_category, failed_tasks };
}

function mean(xs: number[]): number {
  return xs.length === 0 ? 0 : xs.reduce((a, b) => a + b, 0) / xs.length;
}

// ─── Convenience: load tasks from a directory ───────────────────────────────

export function loadTasks(jsonPaths: string[]): EvalTask[] {
  return jsonPaths.map(p => JSON.parse(readFileSync(p, 'utf8')) as EvalTask);
}

// ─── Example usage (delete in your project) ─────────────────────────────────

/*
const runner: Runner = {
  async runOne(input) {
    // Call your model here. Could be Anthropic, OpenAI, your agent harness, etc.
    return await callMyAgent(input);
  },
  graders: {
    'graders.citation_and_number_labeling': async (output, expected) => {
      const expectedIds = (expected.must_include_citation_for as string[]) ?? [];
      const found = [...output.matchAll(/\[\[doc:([a-f0-9-]+)\]\]/g)].map(m => m[1]);
      const allFound = expectedIds.every(id => found.includes(id));
      return { passed: allFound, detail: { found, expected: expectedIds } };
    },
  },
};

const tasks = loadTasks(['tasks/T-0001.json', 'tasks/T-0002.json', '...']);
const { report } = await runEval(tasks, runner);
console.log(JSON.stringify(report, null, 2));
*/
