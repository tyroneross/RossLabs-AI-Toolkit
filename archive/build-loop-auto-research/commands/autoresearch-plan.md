---
name: autoresearch-plan
description: "Define an autoresearch experiment without running it. Interactive wizard for scope, metric, guard, and budget."
argument-hint: "[goal]"
---

Load the `autoresearch-loop` skill.

Run only Phase 1 (Setup) — do NOT start the optimization loop.

{{#if ARGUMENTS}}
Goal: `{{ARGUMENTS}}`

1. Auto-detect targets by running `detect_autoresearch_targets()` from `scripts/core.py`
2. Present candidate targets with suggested metrics and guards
3. Confirm scope, metric command, guard command, and budget with the user
4. Initialize `experiment.json` with the confirmed configuration
{{else}}
No goal provided. Ask the user what they want to optimize, then:

1. Auto-detect targets by running `detect_autoresearch_targets()` from `scripts/core.py`
2. Present candidate targets with suggested metrics and guards
3. Confirm scope, metric command, guard command, and budget with the user
4. Initialize `experiment.json` with the confirmed configuration
{{/if}}

Stop after setup is complete. Output the full experiment configuration so the user can review before running `/autoresearch:run`.

Do not proceed to Phase 2 (Loop) or Phase 3 (Review).
