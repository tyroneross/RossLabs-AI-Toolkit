# LLM Judge Prompt Template

Use a cheap-tier judge (Claude Haiku, gpt-4o-mini) for cost. Calibrate before trusting.

---

## System prompt

```
You are evaluating an AI assistant's response to a user question against a rubric.

You will see:
1. The user's question.
2. The retrieved sources the assistant had access to.
3. The assistant's response.
4. The rubric to apply.

Score the response on each rubric dimension on a 1–5 scale:
- 1 = badly fails the dimension; would harm the user.
- 2 = noticeably wrong on this dimension.
- 3 = partially meets the dimension; usable but flawed.
- 4 = meets the dimension reliably.
- 5 = exemplary on this dimension; no improvement possible.

For each dimension, return:
- score (integer 1–5)
- reason (one sentence citing specific text from the response or sources)
- evidence (verbatim quote from the response, ≤30 words)

Be calibrated. Use the full 1–5 range. Reserve 5 for genuinely exemplary cases. Reserve 1 for true failures. A "fine" response is usually 3 or 4.

Return strict JSON only — no prose, no markdown fences.
```

## User prompt template

```
USER QUESTION:
{{user_question}}

RETRIEVED SOURCES:
{{#each retrieved_sources}}
[{{id}}] {{title}}
Excerpt: {{excerpt}}
{{/each}}

ASSISTANT RESPONSE:
{{response}}

RUBRIC:
{{#each dimensions}}
- {{name}}: {{description}}
{{/each}}

Return JSON of shape:
{
  "dimensions": [
    { "name": "...", "score": 4, "reason": "...", "evidence": "..." }
  ],
  "overall": 4,
  "overall_reason": "..."
}
```

## Example rubric (citation grounding)

```yaml
dimensions:
  - name: citation_correctness
    description: |
      Does every [[doc:<id>]] citation in the response correspond to an ID in retrieved_sources?
      Did the model refuse to cite when no source supports a claim?
  - name: number_labeling
    description: |
      Does every number in prose carry one of the five origin tags (your reported value /
      calculated from your inputs / estimated / industry typical / from source)?
      Are (from source) tags paired with citation tokens?
  - name: register_consistency
    description: |
      Is the response in a single voice register (trust-bearing OR plain), not mixed?
  - name: answers_the_question
    description: |
      Does the response directly answer what the user asked, or does it deflect / restate /
      pivot to adjacent content?
```

## Calibration protocol

Before trusting judge scores:

1. Run judge on 20 mixed-quality responses (10 you'd grade pass, 10 you'd grade fail).
2. Grade them yourself blind — write your scores BEFORE looking at judge's scores.
3. Compute agreement rate (`agreed / 20 = X%`).
4. If agreement < 80%, the judge prompt is broken — not the model. Common fixes:
   - Tighten the dimension descriptions (more specific = higher agreement).
   - Add 2–3 worked examples (good + bad) in the system prompt.
   - Lower the temperature on the judge call.
   - Switch to a frontier-tier judge for hard rubrics.
5. Re-run calibration each release. Tracked drift is the signal.
