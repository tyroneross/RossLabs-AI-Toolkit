# Worked example — SpeakSavvy iOS

A real walkthrough of the prd-builder workflow, end-to-end. The user is Tyrone Ross. The app is SpeakSavvy iOS, an AI-powered speaking-coach iOS app already in active development with several drills shipped before this PRD pass.

## Context

Tyrone had been iterating SpeakSavvy reactively for several months. Multiple drills shipped. The architecture was sound. But every UX decision required Tyrone's input ("Settings or Admin?", "fold this or keep it?", "more options or fewer?"), and the LLM kept asking similar tactical questions because the strategic frame wasn't documented.

The trigger to run prd-builder was a meta-observation: *"think about the questions you've asked me about design and architecture choice over the past few days. What would you need to make those decisions yourself?"*

## Q1 — Who and when

**Asked as a draft inference, not a blank prompt:**

> Director+ leadership at any tech company: startup founder, IPO-stage VP, big-tech IC-exec. The unifying trait isn't title — it's that they routinely talk to a board, an exec team, or senior peers, and the quality of those moments shapes their career. Not ESL beginners, not stage performers, not Toastmasters competitors, not TED-talk aspirants.

**Tyrone's response:**

> *"Director+, that's why frameworks like PREP are important because exec communication must be clear, logical, and easy to follow. I'd opt for any senior leader who needs to talk to board of directors or other senior execs whether startup or large tech. That's why I want to focus on general frameworks for answering questions and storytelling to build the overall skill vs focusing on a very narrow situation like a board update on government policy in Asia (super hypothetical)."*

**Key clarification:** the persona is about *transferable skill*, not situational drilling. Frameworks > situations.

## Q2 — Outcome

**Asked as a draft inference:**

> After 8 weeks of 3-sessions-per-week practice, the user's median 7-dim rubric score improves by ≥10 points AND they sustain ≥3 sessions/week through that window. Either alone is meaningless; together they prove speaking is trainable.

**Tyrone's response:**

> *"I want this to translate to executive rhetorical skillset. Next wave is focused on ensuring the core features work seamlessly and effectively, potentially simplifying by offering fewer options but making them more flexible with AI generated content tailored to user goals."*

**Key clarification:** the outcome is *career-advancing executive rhetoric*, not just rubric numbers. Roadmap implication: simplify-and-flex, not add-and-multiply.

## Q3 — Stance

**Asked as a draft inference:**

> Privacy: audio never leaves device, summary metrics + transcript may go to LLM cloud only when cloud tier active. Complexity: regular users see toggles they need (voice on/off, focus, reminders); model picker / API keys behind admin gate. Cost: BYO-key for cloud tier, offline free forever, subscription only after retention + improvement proven.

**Tyrone's response:**

> *"Hybrid. When I say research I'm also heavily weighing practices and framing heavily used and effective in industry that are logically sound. For example I don't know if there's any official research or much on Pyramid Principle and MECE but several consulting firms and most senior leaders including my corporate strategy team find that structure to work incredibly well for communicating ideas. Accuracy first, speed second. Process on phone for scalability with assumption future iPhones will handle more, on-device LLMs improve. I want to process what I can accurately and reasonably on-device, shift other processing to Groq where possible, and finally to ChatGPT if Groq doesn't have a good experience."*

**Key clarifications:**

- **Tech tier ladder:** on-device → Groq → OpenAI fallback. *(This flipped the LLM's draft, which had OpenAI as the premium cloud tier.)*
- **Privacy is scalability-driven**, not the primary driver. On-device first because iPhones improve, not because of paranoia.
- **Evidence stance:** industry-tested + logically sound = research-backed. Pyramid Principle counts even without academic literature.

## What got generated

From Q1-3, the LLM drafted `docs/prd-speaksavvy.md` with:

**Frontmatter `core_principles` (the 7 always-true rules):**

1. Director+ leaders practicing general communication frameworks, not situational scripts.
2. North star = 7-dim rubric delta + retention. The app proves speaking is a trainable skill.
3. On-device first; Groq is the default cloud tier; OpenAI is the fallback when Groq quality disappoints. Audio never leaves the device.
4. Hide complexity from regular users; power features behind an admin gate.
5. Don't add new drills next; polish, fold, kill, then make the survivors flexible via AI-tailored content.
6. Industry-tested practice + internally logical = research-backed.
7. This PRD is a generative model, not a checklist. Non-goals are derived from Persona + Outcome, not enumerated as rules.

**LLM Navigation Map** — 10 decision types mapped to PRD sections.

**Section Index** — 16 sections with line ranges for `Read --offset --limit`.

**Fidelity check** — 8 questions the PRD body must enable answering.

## Fidelity check applied

Predicting each question's answer from only the PRD body:

| Question | PRD-derived answer | Cited section |
|---|---|---|
| Speed or accuracy? | Accuracy first, speed second. | Stance / Privacy and processing |
| More features or simpler? | Simpler with AI-tailored content. | Roadmap stance |
| Many metrics or one? | One north-star indicator. | North Star |
| Vocal off-persona feature request? | Decline; cite Persona. | Persona |
| Degrade gracefully or fail loudly? | Degrade — Apple FM offline tier always works. | Stance / Privacy |
| Move work to cloud? | Only when on-device can't, ladder is on-device → Groq → OpenAI. | Stance / Privacy |
| Opinionated onboarding? | Opinionated — coaching focus drives prompt generation. | Roadmap stance + Stance / Complexity |
| Add competitor's feature? | Test against Persona + Outcome. | Persona + Outcome |

All 8 answers derived cleanly with section citations. PRD passed Fidelity check.

## Bidirectional links

The Roadmap stance section points forward to `.build-loop/research/05-drill-audit.md` which operationalizes the *"don't add drills, fold and polish"* directive into concrete keep / fold / cut decisions per drill.

The audit packet header points back to `docs/prd-speaksavvy.md` (Methodology + Roadmap stance) so an LLM reading either doc finds the other.

## Project-level pointer

Created `.claude/CLAUDE.md` with one section:

> *Before any non-trivial change to app behavior, drill catalog, rubric, coaching prompts, or UX: read `docs/prd-speaksavvy.md` frontmatter first, use the LLM Navigation Map to find which section informs your decision, read those sections deeply, cite the relevant principle in your justification.*

This is the discovery mechanism. Every Claude Code session in the SpeakSavvy repo auto-loads CLAUDE.md, so the pointer is always present.

## Lessons from this case

1. **Drafting answers in advance worked.** Tyrone redirected each draft rather than writing from scratch. Faster and more concrete than blank prompts.
2. **The reframe mid-process was important.** Tyrone clarified that the PRD shouldn't list non-goals as rules — it should be a generative model from which non-goals are derived. The skill's framing was updated to reflect this.
3. **Industry-tested counts as research-backed.** This was not the LLM's default assumption. Pyramid Principle has minimal academic literature but is the working language of consulting and corporate strategy. The PRD codifies this stance so the LLM doesn't reach for peer-reviewed sources where industry practice is the better authority.
4. **The Fidelity check found gaps the principles alone missed.** Until the LLM tried to predict "should we move work to cloud?", the tech ladder (on-device → Groq → OpenAI) wasn't pinned down. Predicting it forced the explicit statement.

## What you'd repeat for your own app

1. Draft inferences for Q1-3 based on whatever you know (memory, codebase, prior conversation).
2. Get redirections from the user; refine.
3. Draft the PRD with full LLM-navigation infrastructure.
4. Run the Fidelity check; deepen sections that fail.
5. Add the project-level CLAUDE.md pointer.
6. (If applicable) bidirectionally link to research packets, audit docs, or operationalization documents.
