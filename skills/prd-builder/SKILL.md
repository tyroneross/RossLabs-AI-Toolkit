---
name: prd-builder
description: Generate a living, LLM-navigable PRD for an app or feature by answering 3-5 strategic questions. Output is a generative model an AI coding agent can reason from to make tactical decisions without escalating to the human on every choice. Use when starting a new app, scoping a new feature surface, doing a mid-project realignment after reactive iteration, before a major pivot, or whenever an LLM keeps asking the same kind of "should I do A or B?" question because the strategic frame is missing. Trigger phrases include "I want to build an app for", "scoping a new project", "thinking about building", "PRD for", "what should this product be", "starting a new app", "we've been building reactively", "the LLM keeps asking the same kind of question". Skill produces a markdown PRD with frontmatter (always-true principles + load_when triggers), an LLM Navigation Map, a Section Index for offset/limit reads, and a Fidelity check that validates the PRD has enough density to derive any tactical decision.
author: Tyrone Ross
version: 0.2.0
tags: [prd, product-strategy, scoping, kickoff, north-star, persona, generative-model, living-doc]
category: product-development
difficulty: intermediate
---

# PRD Builder

## Problem

Most PRDs fail one of two ways. They're either **too prescriptive** (a list of dos and don'ts that goes stale on first contact with reality) or **too vague** (mission statements that resolve no actual decisions). Neither helps an AI coding agent or a future engineer decide tradeoffs.

A good PRD is a **generative model**: it compresses persona, intent, and philosophy densely enough that any tactical decision can be derived from it, even decisions the author never anticipated. Like a chess evaluation function rather than an opening book.

This skill produces that kind of PRD by:

1. Asking the smallest set of strategic questions whose answers cover ~85% of tactical decisions (Q1-3).
2. Optionally extending to ~95% coverage with two more questions (Q4-5).
3. Drafting a PRD with built-in LLM navigation infrastructure (frontmatter, navigation map, section index, fidelity check) so coding agents can load only what they need.
4. Validating the PRD with a fidelity check before declaring it adequate.

## Trigger Conditions

Load this skill when:

- The user is **starting a new app** ("I want to build...", "scoping...", "thinking about building...")
- The user is **mid-project and asks for alignment** ("we've been building reactively", "what's the north star here", "I keep getting asked the same kind of question")
- The user **explicitly asks for a PRD** ("draft a PRD", "PRD for...", "product requirements doc")
- A coding agent has been **escalating tactical questions repeatedly** in the same project — the strategic frame is missing
- The user is **preparing a pivot** and needs to redocument intent before changing direction

Skip this skill if:

- The user has a working PRD already and just wants to update one section (use Edit on the existing doc).
- The work is purely tactical (one feature, one bug, one refactor) — a PRD is overkill for short-horizon decisions.

## The Generative Model framing

The PRD this skill produces is **not** a list of allowed and forbidden things. It's a compressed model of intent. From that model, an LLM should be able to derive:

- Whether a new feature is on-vision or off
- Whether to prioritize speed or accuracy on a given tradeoff
- Whether to add complexity or simplify
- Whether to accept a feature request from a user who doesn't fit the persona
- When to fail loudly vs degrade gracefully
- When to move work from on-device to cloud (or vice versa)
- Whether onboarding should be opinionated or open

If the LLM **can't** derive these from the PRD, the PRD has a gap. The fix is to deepen the relevant section, not to add a new rule.

**Non-goals are derived, not declared.** The PRD lists them only as illustrative examples of refusals that have been specifically debated. The LLM derives new non-goals from Persona + Outcome on demand.

## The 3-5 Questions

### Coverage map

| Coverage | Set | Resolves |
|---|---|---|
| ~95% | Q1 + Q2 + Q3 + Q4 + Q5 | Most decisions, including edge cases |
| ~85% | **Q1 + Q2 + Q3** | Most tactical decisions; default minimum |
| ~70% | Q1 + Q2 | Persona + outcome, missing tech/architecture |
| ~50% | Q1 only | Insufficient |

Skip Q4-5 unless there's specific nuance worth pinning down. Diminishing returns hit hard below 3.

### Q1 — Who and when (persona + trigger)

**What this answers:** which design tradeoffs default which way.

**Format your answer as three parts:**

**(a) Primary user (one paragraph):** imagine the person who'll use this app three times a week for the next year. Role, life stage, what they already use that this competes with or complements.

**(b) Trigger moments (1-3 bullets):** what event or rhythm makes them open the app — pre-event prep, daily habit, reaction to a problem, boredom, a specific feeling.

**(c) Who they are NOT (3-7 bullets):** explicit exclusions. Often more important than (a). Surfaces personas that look superficially similar but who this app is not for.

**What an LLM can generate from this answer:**
- Onboarding tone and pacing (technical-comfortable vs needs-hand-holding)
- Default content density (sparse vs information-dense)
- Feature gating (everything visible vs progressive disclosure)
- Tone of error states, empty states, coaching language
- Whether monetization is plausible

### Q2 — Outcome (the measurable change)

**What this answers:** what success looks like. Forces priority because most apps could credibly claim multiple outcomes; pick the one you'd defend.

**Format:** *"After [N weeks/months] of [usage pattern], the user [measurable change]."* Pick ONE.

The change should be:
- **A number** ("median session length under 30 min")
- **A behavior** ("can deliver a 90-second structured update on demand")
- **A self-perception** ("describes themselves as a runner, not someone who runs")

**Examples (don't pick from these — write your own):**
- *Productivity:* "After 4 weeks of daily use, user reaches inbox-zero before 10am on 4 of 5 weekdays."
- *Speaking coach:* "After 8 weeks of 3x/week practice, user's median rubric score improves by ≥10 pts AND retention ≥3/week."
- *Health tracker:* "After 6 weeks, user logs the target metric on ≥5/7 days for 4 consecutive weeks."
- *Knowledge tool:* "After 30 days, user opens the app to retrieve a saved item ≥3x/week."

**What an LLM can generate from this answer:**
- Which analytics matter (and which are vanity)
- Shape of the rubric / scoring / progress display
- Onboarding goals (does the user have to do X by day Y to count?)
- Retention vs intensity tradeoffs

### Q3 — Stance (the philosophy boundaries)

**What this answers:** the 3-4 architectural tradeoffs that, once locked, save 100 downstream decisions.

**Format — three sentences, one each:**

1. **Privacy / Data:** *"We will/won't [send/store/share] [data X] because [reason]."*
2. **Complexity:** *"Regular users will/won't see [advanced feature class] because [reason]."*
3. **Cost:** *"The app is [free/freemium/paid/subscription/open-source/acquisition-targeted] because [reason]."*

If you can't fill in any "because," that's an unresolved decision. Flag it as `TAG:UNRESOLVED` in the PRD; the LLM proceeds with a placeholder marked clearly.

**Optional fourth sentence (if relevant to category):**
- Health/fitness: regulatory stance (HIPAA, GDPR, FDA)
- Social: moderation philosophy
- AI/ML: hallucination tolerance, model-choice stance
- Finance: compliance posture
- Hardware: integration vs standalone

**What an LLM can generate from this answer:**
- Tech stack defaults (cloud-first vs local-first vs hybrid)
- Settings architecture (one screen vs admin-gated)
- Onboarding flow (free trial vs immediate paywall vs BYOK)
- Marketing voice (privacy-first vs convenience-first vs prosumer-first)

### Q4 — Failure mode (optional)

**What this answers:** when does the user stop using the app? Negative framing surfaces what to defend against.

**Format — three sentences, one each:**

1. **Day 1 failure:** *"User opens the app for the first time and bounces because [...]."*
2. **Week 2 failure:** *"User has been using daily, stops because [...]."*
3. **Month 3 failure:** *"Power user who got value, churned because [...]."*

These are usually different. Day-1 = onboarding. Week-2 = value-delivery. Month-3 = novelty-decay or feature-ceiling.

### Q5 — Specific refusals (optional)

**What this answers:** non-goals that are otherwise derivable from Q1-3 but have been internally debated and need to be pinned down so future-you doesn't reopen them.

**Format — list 3-7 explicit refusals with "because" reasoning:**

- *"This is not for [user type] because [reason]."*
- *"This will not have [feature] because [reason]."*
- *"This will not work for [use case] because [reason]."*

Add Q5 only if a refusal would otherwise drift back in. Q1-3 alone usually generate the non-goals on demand.

## PRD Output Specification

Once Q1-3 (or Q1-5) are answered, draft a markdown PRD at `docs/prd-<appname>.md` with this structure:

### Frontmatter (always-loaded)

```yaml
---
name: prd-<appname>
status: draft | living | pivoting | archived
revision: "0.1"
last_updated: "YYYY-MM-DD"
load_when:
  - non-trivial change to app behavior
  - new feature proposal
  - UX/UI decision before asking the user
  - architectural choice
evolves_when:
  - dogfood feedback contradicts a stated principle
  - the persona shifts
  - the north star is hit (set the next one) or proven wrong (revise)
core_principles:
  - 5-7 always-true rules, 1-2 lines each, derived from Q1-3
---
```

### Body sections (in order, LLM-first ordering)

The PRD is **LLM-first but human-readable**. Frontmatter (above) is the always-loaded machine-readable core. The body opens with a single condensed Reading guide that humanizes the same intent for top-to-bottom reading; the strategic content follows in natural human order; LLM-only tooling sits at the very end. This avoids the v0.1-style anti-pattern where 80+ lines of separate How-to / Navigation / Section-Index / Fidelity-check sections at the top blocked human readers from reaching strategic content.

1. **Reading guide** — single condensed section, ~25 lines, that:
   - Frames the PRD as a generative model (one paragraph, both audiences).
   - Has explicit *"For humans:"* and *"For LLM agents:"* sub-paragraphs (3-4 lines each) directing how each audience should read.
   - Embeds the **Decision-routing map** as a table — decision type → which sections to read. Useful as a TOC for humans and a router for LLMs.
   - Followed by a `---` separator to mark the transition to strategic content.
2. **Intent** — one paragraph derived from Q1+Q2. The TL;DR humans hit first after the Reading guide.
3. **North Star** — the metric from Q2 + the rationale.
4. **Persona** — full Q1 expansion: who they are, what they bring, what they want sharper, trigger moments.
5. **Outcome** — Q2 expanded with 3-5 specific user-visible outcomes.
6. **Methodology** — how the app delivers the outcome. Frameworks, content basis, evidence stance.
7. **Stance** — Q3 expanded into three or four subsections.
8. **Non-goals (illustrative)** — derived from Persona + Outcome, listed only as examples of refusals already debated. Notes that the LLM derives new non-goals from Q1-3 logic, not from this list.
9. **Roadmap stance** — what NOT to build next; how to prioritize. Points to any audit / research packets that operationalize this.
10. **One-line summary** — distills the entire PRD to a single sentence.
11. **Open questions** — what was deferred or unresolved. Flagged as `TAG:UNRESOLVED` if Q3 had blank "because" clauses.
12. **Pivot log** — major direction changes, one line each. Initially empty.
13. **Document maintenance** — when this PRD updates, how to keep section line numbers fresh.
14. **Fidelity check** — at the end of the doc, NOT the top. A self-test the reader runs AFTER absorbing the strategic content. Useful for humans as a quarterly review; for LLMs as a pre-action validation.
15. **Section Index** — last section. LLM-only line-number tooling for `Read --offset --limit`. Explicitly labeled as such; humans can ignore it. Drift more than ~5 lines triggers a sync pass.

### Fidelity check (built into every PRD, placed at the end)

A self-test for whether the PRD is dense enough. Predict the answer to each question below from only the PRD body. If you can't predict, or the PRD doesn't justify the answer, the PRD has a gap.

- Should the next major release prioritize speed or accuracy?
- Should new features add complexity or simplify existing ones?
- Should the home screen show many metrics or one north-star indicator?
- Should we accept a feature request from a vocal user who doesn't fit the persona?
- When should the app degrade gracefully vs fail loudly?
- When should we move work from on-device to cloud (or vice versa)?
- Should onboarding be opinionated or open?
- Should we add a feature competitors have that some users are asking for?

If the PRD answers these cleanly with citations, ship. If not, deepen the relevant section before proceeding.

## Workflow

1. **Confirm the skill applies.** Trigger phrases listed above. If the user has a working PRD already, redirect to a section-edit workflow.
2. **Ask Q1-3** in a single message. Format each as a draft inference, not a blank prompt — show the user what you'd write if forced to guess. They redirect; you refine.
3. **(Optional) Ask Q4-5** if Q1-3 leave specific gaps the user wants pinned down.
4. **Draft the PRD** at `docs/prd-<appname>.md` following the Output Specification above.
5. **Run the Fidelity check.** Predict each question's answer from the draft. If you can't, deepen the relevant section and try again.
6. **Add the project-level pointer.** Create or update `.claude/CLAUDE.md` with: *"For non-trivial changes, read `docs/prd-<appname>.md` and apply its LLM Navigation Map."*
7. **Commit and reference.** The PRD is now the strategic source of truth; subsequent tactical work cites it.

## Maintenance — the PRD is living

This skill produces a doc designed to evolve. The `evolves_when` frontmatter triggers a review:

- **Dogfood feedback contradicts a principle.** Decide: was the principle wrong (update), or the feedback wrong (note and stand firm)? Either resolution belongs in the Pivot log.
- **The persona shifts.** A broader audience emerged, or the current persona narrowed. Rewrite Persona; cascade implications through Outcome and Stance.
- **The north star is hit.** Set the next one. Don't leave the old one as "achieved"; replace it.
- **Quarterly health check.** Walk the Fidelity check. Sections that fail prediction get deepened.

Mark obsolete sections `[OBSOLETE]` rather than deleting them. The history of decisions is the value of a living PRD; future-you (or future-LLM) reading "we used to think X because Y, we now think Z because W" is more useful than reading just Z.

## Worked example

See `examples/speaksavvy-worked-case.md` for a concrete walk-through:

- Q1-3 answers from a real user (Tyrone Ross, building SpeakSavvy iOS)
- The drafted PRD that came out
- The Fidelity check applied to it
- The bidirectional link to the drill audit packet that operationalizes the Roadmap stance

This example demonstrates the full workflow on a real project, not a toy case.

## Related skills

- **`build-loop`** — orchestrated dev loop that should check for PRD presence in Phase 1 (Assess) and recommend this skill if absent.
- **`agent-builder`** — for AI-product-specific harness decisions; load alongside this skill when the app is an AI assistant or agent.
- **`prompt-builder`** — for prompt-engineering-specific PRD sections.

## Anti-patterns this skill avoids

- **Mission-statement PRDs** that resolve nothing tactical.
- **Constraint-list PRDs** that calcify the moment reality changes.
- **PRDs that aren't navigable** — no frontmatter, no section index, LLMs can't load just what they need.
- **Static PRDs** with no evolution mechanism — they become museum pieces within a quarter.
- **PRDs with no Fidelity check** — no way to know if the PRD is dense enough to be useful.
