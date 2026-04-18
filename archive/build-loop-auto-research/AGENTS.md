# AGENTS.md — Build Loop Auto Research

This plugin is a standalone command + skill bundle for research-backed build planning.

## What To Edit

| Change | File |
|---|---|
| Plugin metadata | `.Codex-plugin/plugin.json` and `.claude-plugin/plugin.json` |
| User-facing slash commands | `commands/*.md` |
| Phase loop skill | `skills/build-loop-auto-research/SKILL.md` |
| Workflow rules | `skills/pattern-aware-planning/SKILL.md` |
| Research rationale | `docs/research-basis.md` |
| Loop initialization | `scripts/init_loop.py` |
| History analysis logic | `scripts/analyze_history.py` and `scripts/core.py` |
| Repo scan and packet rendering | `scripts/research_build.py` and `scripts/core.py` |
| Brief optimization scaffold | `scripts/optimize_brief.py` and `scripts/core.py` |
| Lightweight validation | `tests/*.py` |

## Constraints

- Keep `.Codex-plugin/plugin.json` canonical.
- Keep `.claude-plugin/plugin.json` identical unless there is a compatibility reason not to.
- Avoid external dependencies. Python standard library only.
- Commands should stay user-friendly and low-friction. One main command, minimal branching.
- When research claims change, refresh `docs/research-basis.md` from primary sources.
- Every recommendation should pass the simplicity + UX gate:
  - simpler is better
  - no net UX regression
  - prefer building with existing app code before adding new libraries
- Confidence is operational:
  - `high` => spot-check and re-calibrate
  - `medium` / `low` => iterate before accepting the result
- Keep modular memory notes under `memory/lessons/` and index them in `memory/MEMORY.md`.
