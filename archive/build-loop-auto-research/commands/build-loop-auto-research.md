---
name: build-loop-auto-research
description: "Orchestrated research-backed build loop: assess → define → plan → execute → validate → iterate → fact-check → report"
argument-hint: "[goal description]"
---

{{#if ARGUMENTS}}
Load the `build-loop-auto-research:build-loop-auto-research` skill. Goal: `{{ARGUMENTS}}`
{{else}}
Load the `build-loop-auto-research:build-loop-auto-research` skill. Ask the user what they want to build, investigate, or improve.
{{/if}}
