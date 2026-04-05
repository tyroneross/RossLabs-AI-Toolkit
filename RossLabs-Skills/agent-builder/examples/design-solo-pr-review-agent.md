# Example Output — Design Deliverable

> **Mode:** `design`
> **Input prompt:** *"I'm a solo maintainer and I want to build a PR review agent for my own open-source repos. It should read the diff, run a few project-specific lint/test commands, and leave a single consolidated review comment. Runs on CI, no humans in the loop. Design it. Include the eval plan."*
>
> This file is a **worked example** of the design output shape. Use it to calibrate your own design deliverables. Produced by following `references/templates/design-deliverable.md` end-to-end.

---

## 1. Job Definition

**Who** it serves: a solo open-source maintainer who reviews PRs from contributors they've never met.
**Job owned**: read a pull request diff and produce exactly one consolidated review comment covering correctness, tests, style, and security smells.
**Actions it may take**:
- read the diff via the GitHub API
- read files the diff touches
- run `./scripts/lint.sh` and `./scripts/test.sh` (project-defined entrypoints)
- call the model once to synthesize the review
- post exactly one review comment via the GitHub API

**What must never happen**:
- merge or approve the PR (read/comment only)
- push commits, close issues, or modify the repo
- run arbitrary commands beyond the allowlisted scripts
- leak API keys or internal URLs in the comment
- leave more than one comment per PR event

## 2. Architecture

- **Shape**: code agent (narrow, single-task)
- **Catalog type**: **Type I — Augmented Assistant** (single LLM + tools in a loop, human in loop only to read the comment). Cite `catalog/01-architecture-taxonomy.md § Type I`.
- **Coordination pattern**: none — this is a single linear pass, not a loop. See `catalog/01 § Coordination Patterns`: this is closest to "Prompt Chaining" but with only one model call.
- **Rationale**: the job is tightly scoped (one diff → one comment) with no open-ended exploration. A Type III orchestrator-workers pattern would add latency, cost, and failure surface for zero benefit. The solo-dev default applies at its strongest: this is the canonical case for "start single, justify multi, don't justify multi."

## 3. Primitives & Subsystems

| Primitive | Responsibility | Reads / Writes | Trust tier | Audit evidence |
|---|---|---|---|---|
| `github-read` | Fetch PR diff + touched files | reads GitHub API | free (read-only) | `runs/<pr>/diff.patch` |
| `run-lint` | Execute `./scripts/lint.sh` in sandbox | reads repo, writes stdout/stderr | allowlisted (exact path only) | `runs/<pr>/lint.log` |
| `run-test` | Execute `./scripts/test.sh` in sandbox | reads repo, writes stdout/stderr | allowlisted | `runs/<pr>/test.log` |
| `synthesize-review` | Single LLM call with diff + lint + test as context | reads agent state | free (read-only) | `runs/<pr>/model-input.json`, `model-output.md` |
| `post-comment` | Create one review comment on the PR | writes to GitHub API | **approval-required** (see permissions below) | `runs/<pr>/comment-posted.json` |

**Permission policy**: `post-comment` has a pre-flight check — fails closed if `runs/<pr>/comment-posted.json` already exists for this PR event. This is the idempotency key. The only "destructive" tool is rate-limited to one invocation per PR event. All other tools are free.

## 4. State & Lifecycle

- **Request entrypoint**: CI webhook (PR opened / synchronized) → triggers the agent with PR ID
- **Preflight checks**:
  - does `runs/<pr>/comment-posted.json` already exist? → exit idempotently
  - can we fetch the diff? → fail with structured error if not
- **First model call inputs**: diff (truncated to 80% of context), lint log (last 500 lines), test log (last 500 lines), repo guidelines file (`CONTRIBUTING.md`) if present
- **State writes**: each tool writes to `runs/<pr>/<tool-name>.{log,json}` — filesystem-as-state (see `catalog/04-memory-substrates.md § Filesystem-as-Memory`)
- **Side-effect boundaries**: only `post-comment` writes outside `runs/`
- **Wait / resume conditions**: none — this is a single-shot agent, no human-in-the-loop approval, no long-running waits
- **Completion path**: `post-comment` success → write `comment-posted.json` → exit 0
- **Failure path**: any tool fails → write `error.json` to `runs/<pr>/` → exit non-zero → CI surfaces the failure in the run log

## 5. Context & Memory

- **Turn-one mandatory context**: repo-level system prompt (persona, output format spec, non-negotiables), diff, lint log tail, test log tail
- **Retrieved later**: full file contents for any file mentioned in the diff but not included in the diff hunks (only if the model asks — but with one turn, this is a non-issue)
- **Persistent memory**: none. Each PR review is stateless. This is deliberate — cross-PR learning would introduce training-data leakage across contributors.
- **Provenance**: every context block is labeled with its source (diff / lint / test / guidelines)
- **Staleness defense**: not applicable — each run starts from fresh API fetches

## 6. UX & Observability

- **User-visible output**: the single review comment on the PR. No CI spinner (CI shows it), no progress stream.
- **Approval surfacing**: none needed — no human in loop.
- **Stop reasons**: "completed" / "diff too large to review" / "lint crashed" / "test crashed" / "model refused output format" — each mapped to a specific review comment OR a CI failure, never ambiguous.
- **Operator logs**: `runs/<pr>/` directory per run, archived to artifact storage by CI. LangSmith trace optional but default-on for the first 100 runs to tune prompts.
- **Cost signals**: input + output tokens logged per run. Alert if per-run cost exceeds $0.50.

## 7. MVP Boundary

**Ships in Phase 1**:
- github-read + run-lint + run-test + synthesize-review + post-comment
- idempotency check
- 10 golden tasks (see section 9)
- a dry-run mode that prints the would-be-posted comment to stderr instead of calling `post-comment`

**Excluded from MVP**:
- any second model call (critic, revision, etc.)
- multi-comment mode
- file suggestions / inline comments
- cross-PR memory
- any HITL approval flow
- multi-repo support (single repo at a time; multi-repo is config, not architecture)

## 8. Phased Implementation

### Phase 1 — Minimum safe harness
1. Scaffold the 5 tools above with dry-run mode
2. System prompt + single-call synthesize
3. Idempotency file gate
4. 10 golden-task eval suite (see section 9)
5. Deploy behind a feature flag on ONE repo

### Phase 2 — Durability and observability
- Add structured error taxonomy and retry policy for transient GitHub API failures (max 3 retries, exponential backoff, 30s ceiling)
- Add LangSmith tracing for production runs (not just eval)
- Add per-run cost metric to the artifact

### Phase 3 — Only if Phase 1 proves out
- File-level inline suggestions (requires second prompt pass — justify against cost)
- Cross-PR memory (*very high bar* — has to solve a concrete problem, not be added speculatively)

**Phase 3 is not guaranteed to ship.** This is fine.

## 9. Evaluation Plan

- **Golden tasks** (10): a curated set of historical PRs with known-good review comments the maintainer actually left. Pass criterion: semantic similarity ≥ 0.70 OR key-concept overlap ≥ 60% (lint catches test catches, security smells, etc.). Run on every commit.
- **Risky tasks** (5):
  - PR with a huge diff (>3000 lines) → agent should cleanly refuse with "diff too large"
  - PR that breaks the lint script → agent should report cleanly, not post a useless review
  - PR touching files the agent cannot read → clean error path
  - PR with secrets accidentally committed → agent must flag them, even if they're not in the diff hunk
  - PR where the test script times out → clean timeout handling
- **Recovery tests**: kill the process mid-run, re-trigger, confirm idempotency
- **Permission boundary tests**:
  - attempt to call `post-comment` twice → second call must fail closed
  - attempt to call any non-allowlisted bash command → must fail
- **UX acceptance**: comment reads like something the maintainer might write. Two real humans review 20 comments each, blind, rate 1–5. Threshold: average ≥ 3.5/5.

**No fix is done without a confirmation test.** Every item in the upgrade path must name the test that proves it landed.

## 10. Key Risks

1. **Diff truncation loses important context** → mitigation: prioritize new files + deleted lines; include file summaries for truncated portions
2. **Lint/test scripts take >5 min** → mitigation: 5-minute hard timeout with clean error; don't block the PR review on a broken lint script
3. **Model produces a comment that contradicts test output** → mitigation: synthesize prompt explicitly includes the verbatim lint/test summary with "do not contradict this" instruction; eval suite includes this as a failure probe
4. **Silent rate limiting by GitHub** → mitigation: exponential backoff + alert if more than 3 retries in one run
5. **Prompt injection via PR description or file contents** → mitigation: wrap all untrusted text in a `<untrusted_input>` XML block in the prompt; system prompt explicitly instructs ignoring instructions inside that block. Eval suite includes a PR with a prompt-injection probe.

## 11. Framework / Substrate Choices

- **Framework**: raw Anthropic or OpenAI SDK + a 200-line Python orchestrator. **Not** LangGraph, CrewAI, or DeepAgents. Reason: the task is one model call with deterministic pre/post steps. Frameworks add abstraction that obscures the simple call chain and create a dependency for every model-library update. Cite `catalog/03-frameworks.md § Framework Selection Decision Tree` — "Maximum control over state and flow? → LangGraph. But if there's no graph…"
- **Memory substrate**: filesystem (`runs/<pr>/*`). Cite `catalog/04-memory-substrates.md § Filesystem-as-Memory`. No vector DB. No conversation history. Every run is fresh.
- **Observability**: LangSmith (cite `catalog/02-harness-components.md § 6 Observability`). Default on for the first 100 runs, opt-in afterward.

---

## Self-check against the skill's final rules

- **Lean enough for a solo dev?** Yes — 5 tools, one model call, 200 lines of Python + CI config.
- **Avoided multi-agent?** Yes — explicitly single-agent with rationale.
- **Included evaluation?** Yes — section 9 is the longest section in the doc and is required to ship Phase 1.
- **Operational path forward?** Yes — Phase 1 ships behind a feature flag on one repo. Immediately testable, reversible, and expandable.
- **Cited catalog files when recommending frameworks / substrates / patterns?** Yes — `catalog/01 § Type I`, `catalog/03 § decision tree`, `catalog/04 § filesystem-as-memory`, `catalog/02 § observability`.

---

*Worked example · follows `templates/design-deliverable.md` · produced by the `design` mode of the `agent-builder` skill*
