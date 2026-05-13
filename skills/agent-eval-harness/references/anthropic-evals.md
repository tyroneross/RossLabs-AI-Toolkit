# Anthropic Eval Guidance — Specifics

Source: [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (Anthropic Engineering, 2025).

## The three grader types — Anthropic's framing

1. **Code-based** — deterministic, exact-match, regex, schema validation, presence checks. Cheapest, most reliable. **Use whenever the rubric is mechanical.**
2. **LLM-as-judge** — for open-ended quality, prose register, multi-step reasoning. Cheaper than human; calibration required.
3. **Human review** — for the long tail where (1) and (2) disagree, AND for grading the LLM judge itself.

Mix all three on a serious eval set. A 30-task set might be 22 code-graded, 6 LLM-judged, 2 human-reviewed.

## Grade outcomes, not paths

Quoted: "Grade the destination, not the route." If two agents arrive at the same correct answer via different reasoning chains, both pass. Penalizing reasoning paths makes you the bottleneck.

Exception: if the path produces a verifiable artifact (e.g. "did the agent search before answering?" via tool-call presence), grade the artifact's existence, not its content.

## pass@k vs pass^k — Anthropic's specific advice

- **pass@k for capability**: "can the model do it at all?" — useful for unblocking releases where some retries are tolerable.
- **pass^k for reliability**: "can the model do it every time?" — required for unattended production agents.

Anthropic publishes pass^k explicitly because their long-running agent harnesses retry on failure, so capability without reliability looks fine in dev and breaks in prod.

## Eval set sizing

- **20 tasks**: minimum to detect a regression of >15% scope.
- **50 tasks**: detect ~5% regressions; usable for tuning prompt-design decisions.
- **200+ tasks**: can slice by category, detect distributional shifts.

Don't gate the eval on reaching 50. Start with 20 you have today.

## Model picks for graders

For an LLM judge:
- **Default**: Claude Haiku 4.5 — fast, cheap, calibrated reasonably out of the box.
- **Hard rubrics**: Claude Sonnet 4.6 — better at nuance, ~3× cost.
- **Adversarial**: Opus 4.7 — only when you suspect the judge is being tricked.

Same-vendor judge ≠ same-tier judge. A Haiku judging an Opus output is the cost-aware default.

## Cost notes

- LLM-judge cost dominates a large eval. For a 50-task eval × k=5 = 250 calls × 2 (model + judge) = 500 LLM round-trips.
- Use prompt caching aggressively on the judge — the system prompt + rubric is shared across all 250 calls.
- Run k=1 in CI for fast feedback; reserve k=5 for nightly / pre-release.

## When the eval saturates

Quoted: "When every model scores 95%+, the eval is over." Saturation signals:
- Capability score plateaued for 3+ releases.
- Per-category scores converged tightly.
- Failed tasks are the same handful, release after release.

Response:
- Retire saturated tasks to a "regression" bucket (still run, no longer scored).
- Build a harder eval set from new failure modes (production logs, edge cases).
- Don't just raise the bar — the eval needs new content, not stricter graders.
