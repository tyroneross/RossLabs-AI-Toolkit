# Drift Failure Modes — Three Real Incidents

These are sanitized but real failures. Read them before deciding whether you actually need the contract test in CI (answer: yes).

## Incident 1 — Citation heading rename, contract test missed it

**Repo**: a Next.js + Drizzle RAG app, three prompts using the same citation contract.

**What changed**: someone renamed `## Citations` to `## Source Attribution` in `lib/engine/orchestrator.prompt.ts` while doing copy polish. The other two files kept `## Citations`. The model started emitting `[Source: doc-7f3c]` in the renamed file (because the heading no longer triggered the canonical contract) and `[[doc:7f3c...]]` in the other two.

**How it surfaced**: a user reported "the citations look different on the recommendation page vs the chat." A week later.

**Why CI missed it**: no contract test. The block files weren't imported — they were copy-pasted prose, so a heading rename was invisible.

**Fix**: introduced the contract test in `references/validation-hooks.md` section 1. Block files now live in one place and are imported (vendored) into every consuming file.

## Incident 2 — Unsourced number in production demo

**Repo**: same.

**What happened**: a recommendation surface said "Practitioners typically save 4 hours per week using this skill" with no origin tag, no citation. The user noticed during a demo and asked where the number came from. The team had no idea — the prompt had drifted to allow general claims without tags.

**Root cause**: the number-labeling block had been pasted into the prompt, but then someone added a new "Talking about ROI" section *below* the block, and the new section's examples violated the rule. The model followed the examples, not the rule.

**Fix**: the runtime assertion in `references/validation-hooks.md` section 2.2 catches this. Any number in prose without a nearby origin tag throws `NUMBER_WITHOUT_ORIGIN_TAG`. The first retry uses a sharper prompt: "You wrote '4 hours per week' without an origin tag. Re-write with an explicit tag or omit the number." Usually fixes on retry 1.

## Incident 3 — Register mix in the audit view

**Repo**: same.

**What happened**: the audit/explain view started its output with "Great question! Here's the breakdown:" followed by "Closeness score 0.74 (TOPSIS)…". The conversational opener was from the chat prompt's plain register; the rest was the audit prompt's trust-bearing register. A copy-edit had merged two prompts into one for "consistency", which corrupted both.

**Root cause**: someone tried to "DRY" the prompts. The two registers got mashed together and both call sites consumed the result.

**Fix**: the register-mixing lint in `references/validation-hooks.md` section 3 forbids trust-bearing vocabulary in plain files and plain exclamations in trust-bearing files. Catches the regression on the PR.

**Lesson**: two registers is two prompts. "DRY-ing" them is not DRY — it's lossy compression. The block files are the right level of DRY; the prompts themselves stay separate.

## Common thread

All three failures were *invisible at code review*. The diffs looked fine. The drift was in the *content* — a heading rename, a new section that violated rules above it, a register cross-pollination. CI grep + runtime assertions catch this; human review does not.
