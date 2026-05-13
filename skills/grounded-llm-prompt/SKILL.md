---
name: grounded-llm-prompt
description: Use when writing a system prompt for an LLM response that must cite sources, label every number with origin, and stay in a consistent voice. Composes three reusable rule blocks (citation contract, number-labeling, two-register voice) onto a base prompt and gives you the contract tests to keep them from drifting. Triggers on "build a system prompt", "make it cite sources", "add citations", "ground the output", "label numbers", "truthfulness rule", "system prompt for RAG", "system prompt for an audit view", "stop the model from making up numbers", "the model is citing things that aren't in the retrieval list". Designed for RAG, agentic Q&A, recommendation surfaces, and audit/explain views. Not for creative writing, code generation, or pure structured-extraction tasks.
author: Tyrone Ross
version: 0.1.0
tags: [prompt-engineering, rag, grounding, citations, hallucination-prevention, system-prompt, audit]
category: prompt-engineering
difficulty: intermediate
---

# Grounded LLM Prompt

## Problem

LLM responses that surface facts and numbers to users have three ways to silently break trust:

1. **Hallucinated citations** — the model emits a `[source: doc-12]` token for a source that wasn't actually in the retrieval list, or fabricates a URL.
2. **Unsourced numbers** — the model says "average wait time is 14 days" with no indication whether that came from the user, was calculated from inputs, was estimated, or was made up.
3. **Register drift** — the same product mixes "Hey! Let's figure this out together 🎉" with "The model's confidence-band lower bound is 0.62", because two different prompt files in the same codebase disagree about voice.

Each of these is a *prompt-level* failure with *product-level* consequences. Patching them inline at each call site fails because the patches drift apart over time. The fix is to extract three reusable **rule blocks** and compose them into every grounded prompt the codebase ships, plus contract tests that detect drift.

## What this skill enforces

| Block | What it requires | Where it goes in the prompt |
|---|---|---|
| **Citation contract** | Citation tokens use a documented format (e.g. `[[doc:<uuid>]]`); only emit when the source ID appears in the retrieval list passed to this call; refuse-if-unsourced rule. | After the role/task definition, before output format. |
| **Number-labeling** | Every number in user-facing prose carries an origin tag: `(your reported value)` · `(calculated from your inputs)` · `(estimated)` · `(industry typical)` · `(from source)`. If sourced, pair with a citation token. | Same section as citation contract. |
| **Two-register voice** | Prompt declares either *plain professional* (composer/intake/chat) or *trust-bearing* (audit/recommendation/explain). One register per call site. Mixing is a contract violation. | Top of the prompt (sets tone for everything below). |

Each block lives in `blocks/` as a copy-pasteable markdown fragment. The base prompt composes them by reference. Changes happen in one place.

## How to compose a prompt

1. **Pick the register.** Open `blocks/two-register-voice.md`, choose `plain` or `trust-bearing`, paste that section at the top of your system prompt.
2. **Paste the citation contract.** From `blocks/citation-rule.md`. Customize the token format (default `[[doc:<uuid>]]`) and the retrieval-list field name once at the top, then leave the contract text alone.
3. **Paste the number-labeling rule.** From `blocks/number-labeling-rule.md`. The five origin tags are stable — don't add new ones without updating every call site.
4. **Write the task-specific instructions below the rule blocks.** The blocks come first because the model reads top-down and the rules need to be in the foreground.
5. **Wire validation.** See `references/validation-hooks.md` for the regex assertion and Zod schema patterns that catch drift in CI.

## Anti-patterns

- **Inlining the rules** — copying the citation text into a fourth prompt file. After the second copy, drift is inevitable. Always reference the block.
- **Adding a sixth origin tag** — if you need one, change the block file, then bump every dependent prompt's contract test. Don't add it locally.
- **Mixing registers within a call** — if your prompt has both an "explain to the user" section and a "score these candidates" section, those are *two prompts*. Split them.
- **Trusting the model to refuse** — the refuse-if-unsourced rule is *necessary but not sufficient*. Also enforce with a post-hoc regex check (`/\[\[doc:[^\]]+\]\]/g`) that every emitted citation ID is in the retrieval list.

## Failure modes (and how to detect them)

| Mode | Symptom | Detection | Fix |
|---|---|---|---|
| **Citation drift** | Heading or token format renamed in one file, not others | Contract test grep across all prompt files for canonical token shape | Update block file, re-run grep |
| **Unsourced-number leak** | UI shows "average is 14 days" without origin tag | Regex check on output: every numeric token in prose must be within 40 chars of an origin tag | Tighten number-labeling rule with examples for the missed shape |
| **Register-mixing** | One response opens "Hey!" and closes with "Confidence interval 0.62" | Style-lint pass: forbid trust-bearing tokens (CI, confidence, p-value) in plain-register prompts and vice versa | Split the prompt into two call sites |

## Validation hooks

In a project, wire two checks:

1. **Contract test** (CI): every file in `prompts/` must import the rule blocks; if a block file's hash changes, every consuming file's snapshot test re-runs.
2. **Runtime assertion** (request handler): before returning the LLM response, run the citation-list check and number-labeling regex. Mismatches throw a known error code; the request handler decides whether to retry with a sharper prompt, strip the offending text, or fail the response.

Pseudocode lives in `references/validation-hooks.md`.

## When NOT to use this skill

- **Creative writing / brainstorming** — origin tags break flow and don't apply.
- **Code generation** — citations don't apply; the code is the artifact.
- **Pure structured-extraction** — if no prose is shown to a user, you don't need register or number-labeling. Citation contract may still apply.
- **Conversational agent first turn** — small-talk turns don't need the rules. Only apply once the conversation pivots to factual recall.

## Cross-references

- **`prompt-builder` skill** — for *technique selection* (chain-of-thought, skeleton-first, self-critique). This skill is *enforcement blocks*; the two compose.
- **`multi-pass-llm-pipeline` skill** — when Pass 2 is a grounded response, it should compose these blocks.
- **`pyramid-principle` skill** — for the structural shape of the answer above these enforcement blocks.

## Files in this skill

```
grounded-llm-prompt/
├── SKILL.md                       (this file)
├── blocks/
│   ├── citation-rule.md           (paste-in citation contract)
│   ├── number-labeling-rule.md    (paste-in number labeling)
│   └── two-register-voice.md      (plain / trust-bearing)
├── examples/
│   ├── recommendation-prompt.md   (full composed prompt, audit register)
│   └── synthesizer-prompt.md      (full composed prompt, plain register)
└── references/
    ├── validation-hooks.md        (regex + Zod patterns)
    └── drift-failure-modes.md     (three real drift incidents and how they were caught)
```
