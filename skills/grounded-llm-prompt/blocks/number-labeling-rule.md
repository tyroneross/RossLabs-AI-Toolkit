# Number Labeling Rule

Paste the section below into the rules block of a grounded LLM system prompt. The five origin tags are the entire vocabulary — do not add a sixth without updating this file and every consuming prompt.

---

## Numbers

Every number in user-facing prose must carry an origin tag in parentheses immediately after the number. The five permitted tags are:

| Tag | Use when |
|---|---|
| `(your reported value)` | The user typed this number into the intake / form / chat in this session. |
| `(calculated from your inputs)` | You computed this number from the user's inputs in this session. State the formula or operation in one short clause when ambiguous. |
| `(estimated)` | This is your estimate, not from a source. The user should treat it as a working assumption that they can correct. |
| `(industry typical)` | This is a general range you know from training data, not from a specific retrieved source. Use sparingly and only when the claim is non-controversial. |
| `(from source)` | This number came from a retrieved source. Pair with a citation token per the citation contract. |

If you cannot honestly assign one of the five tags, do not state the number. Round it down to a qualitative descriptor ("a few weeks", "uncommon") or omit it.

Tag every number, including numbers in the same sentence — e.g. "Wait time is 14 days (from source) [[doc:7f3c...]] versus your estimate of 7 days (your reported value)."

Numbers in code blocks, JSON output, or structured fields do not require tags. The rule applies to prose only.

---

## Notes for the prompt author (not for the model)

- **Why these five?** They cover the entire space of provenance: user-given, derived, model-guessed, model-general, source-grounded. Anything outside this is fabrication.
- **`(estimated)` vs `(industry typical)`**: estimated is "I'm making this up based on the situation in front of me." Industry typical is "this is a broadly known range, not specific to you." Both are unsourced; the distinction matters because users may push back differently.
- **Pair `(from source)` with a citation token, always.** A `(from source)` tag without a `[[doc:...]]` token is a prompt failure mode — the model is claiming a source it can't name. Catch it in the runtime assertion.
- **Don't bother labeling structured output numbers.** If your call returns JSON to a UI that renders the numbers in cards, the rule doesn't fire. The rule is for *prose* surfaces.
