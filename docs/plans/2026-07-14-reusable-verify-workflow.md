# Plan — Reusable plugin-manifest verification workflow

## Goal
Kill the copy-pasted CI ceremony. The "Verify manifest versions" block currently exists
independently in claude-code-debugger, replit-migrate, spectra (x2 files), mockup-gallery —
hand-patched 4x on 2026-07-14 for the auto-SHA migration. It must live in ONE place so repo #19
inherits it instead of copying it.

## Non-goals
- NOT touching the publish/release path in this chunk (release = PRODUCTION; a bug there breaks
  shipping). That is chunk C4, gated on C1-C3 proving out.
- NOT migrating repos to a monorepo (evaluated + declined, see ADR 2026-07-14).

## Approach: Path A vs Path B
- Path A (CHOSEN): reusable workflow for manifest verification only. Universal — fits all 18 repos
  including outliers (NavGator's artifact-hash pipeline, bookmark's trusted publishing). Zero
  release risk.
- Path B (DEFERRED to C4): full reusable publish pipeline (install/build/test/publish+provenance).
  Absorbs more duplication but fits only the ~6-repo common family AND touches PRODUCTION release.
- Rationale: Path A solves the measured pain, adopts universally, and proves the reusable-workflow
  mechanism with a live green run BEFORE aiming it at releases. Path B is a named follow-on, not
  speculative abstraction.

## Host
`tyroneross/RossLabs-AI-Toolkit` (PUBLIC, fleet hub, currently no workflows). Public host =>
callable by any repo incl. private ones. Called as:
`uses: tyroneross/RossLabs-AI-Toolkit/.github/workflows/verify-plugin-manifests.yml@main`

## The invariant the workflow enforces (auto-SHA convention)
Let V = `.claude-plugin/plugin.json` version (MAY be absent => auto-SHA; absent is the fleet default).
1. plugin.json exists, is valid JSON, has non-empty `name` + `description`.
2. `.codex-plugin/plugin.json` (if present) MUST agree with V (both absent, or both equal).
3. self-marketplace `.claude-plugin/marketplace.json` entry (if present) MUST agree with V.
4. If V is present: V must be semver AND equal `package.json` version (if package.json exists).
Rule 2+3 encode the no-masking rule from the CC docs: a version set in only ONE surface silently
masks the other. Version is OPTIONAL (build-loop legitimately keeps semver) but must be CONSISTENT.

## Chunks
- C1 Author `.github/workflows/verify-plugin-manifests.yml` (on: workflow_call; input: plugin-dir,
  default "."). Pure python3 (preinstalled on runners) — no node dep. actionlint clean. Push.
- C2 Wire ONE caller repo; trigger; prove a LIVE GREEN run via `gh run`. Acceptance = green run.
- C3 Fan out to remaining plugin repos (additive; does not replace publish.yml).
- C4 (GATED on C1-C3) Reusable publish pipeline for the common family.

## Risks
- A broken reusable workflow fails checks across many repos at once. MITIGATION: live-green on ONE
  caller before any fan-out (C2 gates C3).
- Reusable workflow checks out the CALLER's repo (workflow_call context) — verify this assumption
  empirically in C2, do not assume.

## Acceptance
- actionlint clean on the reusable workflow.
- A real workflow run on a caller repo goes GREEN (not just "yaml parses").
- The check FAILS loudly when fed an inconsistent manifest (mutation test — prove it is not a
  rubber stamp).
