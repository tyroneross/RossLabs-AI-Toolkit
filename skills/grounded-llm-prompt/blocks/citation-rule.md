# Citation Contract

Paste the section below into the rules block of any grounded LLM system prompt. Customize the bracketed parts (`{{TOKEN_FORMAT}}`, `{{RETRIEVAL_LIST_NAME}}`) once per project, then leave the contract text alone.

---

## Citations

Every factual claim that came from a retrieved source must end with a citation token in the exact format `{{TOKEN_FORMAT}}` — for example `[[doc:7f3c1e2a-...]]`. The token wraps the document's stable identifier (UUID, slug, or URL hash — whatever appears in `{{RETRIEVAL_LIST_NAME}}`).

You may only emit a citation token if its source identifier appears in `{{RETRIEVAL_LIST_NAME}}` (the list of sources passed to you in this turn). If the claim is true but no source in `{{RETRIEVAL_LIST_NAME}}` supports it, do not emit a citation token. Instead, write the claim plainly and state explicitly that you lack a grounded source — for example: "I don't have a source for this in your retrieval set."

Do not invent identifiers. Do not paraphrase identifiers (no `[[doc:7f3c...]]` truncation). Do not emit URLs in place of tokens unless the URL itself is the canonical identifier in `{{RETRIEVAL_LIST_NAME}}`.

A citation token may pair with a number-origin tag (see number-labeling rules) when the number itself comes from a source — for example: "The median wait time is 11 days (from source) [[doc:7f3c1e2a-...]]."

---

## Notes for the prompt author (not for the model)

- **Token format default**: `[[doc:<uuid>]]` because it survives markdown rendering and HTML escape (`[[` won't collide with markdown link syntax).
- **Why "stable identifier"**: rows in your retrieval table will be re-indexed, re-chunked, and renumbered. A UUID survives all of that. Don't use chunk indexes.
- **Plural sources for one claim**: model is free to chain — `[[doc:a]][[doc:b]]` is fine. Don't try to enforce a "primary source" rule unless your UI needs it.
- **The refuse-if-unsourced rule is necessary but not sufficient.** Always also wire the runtime regex assertion documented in `references/validation-hooks.md`.
