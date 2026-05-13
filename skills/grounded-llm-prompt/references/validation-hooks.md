# Validation Hooks

Two layers catch citation/number-labeling/register drift: a CI contract test and a runtime assertion. Both are cheap; both are necessary.

## 1. CI contract test (per-prompt-file snapshot)

For every file in `prompts/` that composes the grounded-llm-prompt blocks, snapshot-test the *imported* block content against the canonical block file in this skill. When a block file changes (the source of truth), the snapshot for every consuming file changes, and CI demands a deliberate re-snapshot.

```ts
// tests/prompts.contract.test.ts
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const SKILL_BLOCKS = join(__dirname, '../../node_modules/@rosslabs/grounded-llm-prompt/blocks');
//                                                            ^ or wherever the skill lives in this repo

describe('grounded-llm-prompt blocks are imported, not inlined', () => {
  const promptFiles = [
    'lib/engine/orchestrator.prompt.ts',
    'lib/chat/system-prompt.ts',
    'lib/qa/synthesizer.prompt.ts',
  ];

  for (const file of promptFiles) {
    it(`${file} imports citation block`, () => {
      const text = readFileSync(file, 'utf8');
      const canonical = readFileSync(join(SKILL_BLOCKS, 'citation-rule.md'), 'utf8');
      // canonical content (with bracket placeholders expanded) should appear verbatim
      expect(text).toContain(canonical.replace('{{TOKEN_FORMAT}}', '[[doc:<uuid>]]'));
    });
  }
});
```

In a monorepo without npm packaging, replace the `node_modules` path with a relative path to wherever you vendored the skill.

## 2. Runtime assertion (per-response)

Before returning the LLM response to the caller, run these three checks. Any failure → throw a known error with a structured code; the request handler decides whether to retry with a sharper prompt, strip the offending text, or fail the response.

```ts
// lib/grounded-llm/assertions.ts
const CITATION_TOKEN = /\[\[doc:([a-f0-9-]+)\]\]/g;
const NUMBER_IN_PROSE = /(?<!\d)\d+(\.\d+)?(?!\d)/g;
const ORIGIN_TAGS = [
  '(your reported value)',
  '(calculated from your inputs)',
  '(estimated)',
  '(industry typical)',
  '(from source)',
];

export interface AssertionResult {
  ok: boolean;
  failures: Array<{ code: string; detail: string }>;
}

export function assertGroundedResponse(
  responseText: string,
  retrievalListIds: Set<string>,
): AssertionResult {
  const failures: AssertionResult['failures'] = [];

  // 2.1 Every citation token's ID must be in retrievalListIds.
  for (const [, id] of responseText.matchAll(CITATION_TOKEN)) {
    if (!retrievalListIds.has(id)) {
      failures.push({ code: 'CITATION_NOT_IN_RETRIEVAL', detail: id });
    }
  }

  // 2.2 Every number in prose should be within ~40 chars of an origin tag.
  //     This is heuristic — false positives are cheaper than false negatives here.
  for (const m of responseText.matchAll(NUMBER_IN_PROSE)) {
    const window = responseText.slice(
      Math.max(0, m.index! - 5),
      Math.min(responseText.length, m.index! + 40),
    );
    if (!ORIGIN_TAGS.some(t => window.includes(t))) {
      failures.push({ code: 'NUMBER_WITHOUT_ORIGIN_TAG', detail: m[0] });
    }
  }

  // 2.3 (from source) must be paired with a citation token within 60 chars.
  let idx = 0;
  while ((idx = responseText.indexOf('(from source)', idx)) >= 0) {
    const window = responseText.slice(idx, idx + 60);
    if (!CITATION_TOKEN.test(window)) {
      failures.push({ code: 'FROM_SOURCE_WITHOUT_CITATION', detail: window });
    }
    idx += '(from source)'.length;
  }

  return { ok: failures.length === 0, failures };
}
```

Wire `assertGroundedResponse(response, retrievalIds)` into every code path that returns a grounded LLM response. On failure, prefer **one retry with a sharper prompt** ("You emitted a citation for a source not in your retrieval list — re-write without it") over failing the response or hiding the violation.

## 3. Register-mixing lint (optional, recommended)

Add a simple grep to your CI that fails when:
- A prompt file declares Register A (`Register A`, `plain register`, or includes `coffee shop`) AND contains trust-bearing vocabulary (`confidence interval`, `outranking`, `TOPSIS`, `p-value`, `methodTrace`).
- A prompt file declares Register B AND contains plain-register exclamations (`!` in instructions, emoji, "Hey", "Let's").

False positives are cheap; just override with a comment.
