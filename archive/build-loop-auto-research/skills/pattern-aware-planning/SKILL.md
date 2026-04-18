---
name: pattern-aware-planning
description: Use when a user wants a research-backed build packet, a concise build investigation, a history-pattern analysis, or a brief/prompt optimization pass.
---

# Pattern-Aware Planning

This skill turns a rough request into a structured research packet and implementation plan with minimal friction.

## Use Cases

- new product exploration
- feature investigation
- algorithm evaluation
- prompt design or revision
- bugfix or refactor planning
- chat-history pattern extraction

## Default Workflow

1. **Classify the task**
   - `product | feature | algorithm | prompt | bugfix | refactor`
2. **Choose optimization mode**
   - `quick`: repo-first only, fastest path
   - `balanced`: repo-first plus selective external research
   - `max_accuracy`: full repo scan, targeted external research, extra self-debug pass
3. **Ground in the repo**
   - run `scripts/research_build.py` for repo work
   - run `scripts/analyze_history.py` for history work
   - never recommend a path from a single file alone when the request touches an existing repo
4. **Apply research-backed heuristics**
   - repo-aware retrieval before planning
   - tool-using flow over pure prompting
   - explicit verification before execution
   - self-debug pass on important outputs
   - simplicity + UX gate on every recommendation and iteration
5. **Return a predictable packet**
   - `Bottom line`
   - `What I found`
   - `Best path`
   - `Why this path`
   - `Risks / unknowns`
   - `Next action`

## Orchestration Pattern

- Always use an orchestrating agent for non-trivial work.
- Plan integration points and handoffs before parallelizing anything.
- Safe parallel subagents:
  - repo scan
  - integration checking
  - evidence / documentation checking
  - memory curation
- The orchestrator remains responsible for:
  - the final packet
  - integration readiness
  - confidence re-calibration
  - what the builder can do directly vs what still depends on the user

## Context Continuity

Use bookmark-style local context continuity under the current project:

- snapshot path: `.build-loop-auto-research/context/current-context.md`
- archive path: `.build-loop-auto-research/context/snapshots/`

Before compaction, context clearing, or switching to new work:

1. capture a snapshot
2. summarize current status, decisions, open items, unknowns, and important files
3. restore from the latest snapshot at the start of follow-on work

Use:

- `scripts/context_snapshot.py`
- `scripts/context_restore.py`

This borrows the continuity pattern from `bookmark` without depending on its MCP tools.

## Investigation Pattern

Borrow the issue-investigation discipline from `claude-code-debugger`:

1. run a verdict-gated memory lookup first
   - `KNOWN_FIX`
   - `LIKELY_MATCH`
   - `WEAK_SIGNAL`
   - `NO_MATCH`
2. if the verdict is not `KNOWN_FIX`, investigate root cause before proposing a fix
3. verify with evidence
4. critique weak assumptions
5. store lessons when the first pass was wrong or incomplete

Use:

- `scripts/memory_lookup.py`
- `issue-investigator`

Do not load the full memory corpus by default. Search first, then drill down only when needed.

## Output Contract

Every full research packet should cover:

- `executive_summary`
- `repo_findings`
- `external_findings`
- `recommended_approach`
- `verification_plan`
- `confidence_report`
- `plan_md`
- `handoff_prompt_md`

If the user only wants a brief optimization or history analysis, compress to the minimum relevant subset.

## Question Discipline

- Ask questions only if ambiguity materially changes the plan.
- Keep questions to 1-3 maximum.
- Offer a recommended default first.
- Accept a freeform override when the user does not fit the preset choices.

## Confidence Signals

Use these labels in outputs:

- `Context coverage`: `low | medium | high`
- `Verification coverage`: `low | medium | high`
- `Novelty risk`: `low | medium | high`
- `Evidence quality`: `low | medium | high`
- overall `confidence`: `low | medium | high`

## Confidence Actions

- `high`
  - spot-check at least one critical assumption
  - re-calibrate if the spot check reveals hidden complexity
- `medium`
  - iterate on the weak areas before finalizing
  - re-run the confidence check after revising the path
- `low`
  - gather more repo or documentation evidence
  - simplify scope or approach
  - re-calibrate before recommending implementation

Do not treat confidence as decorative metadata.

## Simplicity + UX Gate

Every recommendation, plan revision, or iteration should answer:

1. Does this materially improve user experience?
   - faster
   - more accurate
   - smoother
   - simpler
2. Does it avoid degrading another experience factor?
3. Is it the simplest approach that still solves the problem?
4. Can it be built with the app's existing primitives before adding a new library?

If the answer is not clearly yes, revise the recommendation.

## Research Rules

- Prefer local repo evidence before web evidence.
- External research is required only when:
  - the task depends on current frameworks, APIs, models, or benchmarks
  - the user asks for research explicitly
  - a recommendation would otherwise be weak or stale
- When external research is used, prefer:
  - official docs
  - arXiv or peer-reviewed papers
  - academic institutions
  - major research labs
- For APIs, auth, payments, tools, or deployment-sensitive work, verify both sides:
  - provider / tool documentation
  - deployment / runtime documentation such as Vercel or Apple platform docs

## Integration And Handoff Rules

- Check module boundaries, data contracts, and state handoffs.
- Check API client/server handoffs, webhook flows, background jobs, and retries where relevant.
- For auth flows, verify login, refresh, logout, callback, session persistence, and secret handling.
- For payments, verify checkout, webhook, entitlement, refund, and failure-handling flows.
- Surface what the builder can do directly vs what still depends on user-owned secrets, accounts, or deployment settings.

## Verification Rules

- If strong tests exist, use them in the proposed verification plan.
- If tests are weak or missing, synthesize:
  - smoke tests
  - assertions
  - manual verification checklist
- For high-importance tasks, run a self-debug pass:
  - draft
  - explain
  - critique
  - revise
- During the self-debug pass, explicitly ask whether the plan added avoidable complexity or introduced a UX tradeoff the user did not ask for.

## Memory Rules

- When something fails because of hidden complexity, weak assumptions, or integration gaps, capture a modular lesson note.
- When something takes multiple iterations, write:
  - what happened
  - why it happened
  - how to improve future iterations in that specific situation
  - how to solve that class of problem better next time
- Store notes in `memory/lessons/` and index them in `memory/MEMORY.md`.

## Templates

Template files live under `templates/`:

- `research-packet.md`
- `optimized-brief.md`
- `history-analysis.md`
- `../../memory/templates/lesson.md`

Use them when a consistent structure helps more than freeform output.
