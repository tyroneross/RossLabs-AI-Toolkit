# PRD Builder

Generate a living, LLM-navigable PRD for an app or feature by answering 3-5 strategic questions. Output is a generative model an AI coding agent can reason from.

## What it produces

A markdown PRD with:

- **Frontmatter** — always-true principles + `load_when` triggers
- **LLM Navigation Map** — decision type → section to read
- **Section Index** — line ranges for `Read --offset --limit`
- **Fidelity check** — questions the PRD must enable answering
- **Body** — Intent, North Star, Persona, Outcome, Methodology, Stance, Non-goals, Roadmap stance, Open questions, Pivot log, Maintenance

## When to use

- Starting a new app
- Mid-project realignment after reactive iteration
- Before a major pivot
- When an LLM keeps escalating the same kind of tactical question

## Coverage

3 questions → ~85% of tactical decisions resolved without escalation.
5 questions → ~95% coverage.

## Worked example

See `examples/speaksavvy-worked-case.md` for a real project walkthrough.

## Read more

`SKILL.md` has the full methodology, output spec, and workflow.
