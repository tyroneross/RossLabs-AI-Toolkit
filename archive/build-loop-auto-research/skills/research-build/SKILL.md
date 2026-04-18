---
name: research-build
description: Use when the user wants a research packet plus a decision-complete implementation plan for a product, feature, algorithm, prompt, bugfix, or refactor, but does not need the full explicit phase-by-phase build loop narration.
---

Load the `build-loop-auto-research` skill when the work is multi-step, integration-heavy, or likely to need iteration.

Use this skill as the shorter packet-oriented path:

1. Ground in the repo first.
2. Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/research_build.py --task "{{user_request}}" --repo-path "$PWD" --format markdown
```

3. Use the script output as the base scaffold.
4. Deepen repo understanding with focused reads across at least 2 relevant files before finalizing any non-trivial plan.
5. Add external research only when current external facts materially affect the recommendation, and then restrict it to primary sources, academic institutions, or major research labs.
6. Verify integration points and handoffs, especially for APIs, auth, payments, and deployment/runtime-sensitive flows.
7. Re-rank confidence as `high`, `medium`, or `low`.
8. Iterate on `medium` and `low`. Spot-check `high`, then re-calibrate.

Return the final answer in this order:

1. `Bottom line`
2. `What I found`
3. `Best path`
4. `Why this path`
5. `Risks / unknowns`
6. `Next action`
