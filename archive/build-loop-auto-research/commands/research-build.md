---
name: research-build
description: "Create a research packet and decision-complete build plan for a product, feature, algorithm, prompt, bugfix, or refactor"
argument-hint: "[request] [--repo-path PATH] [--mode quick|balanced|max_accuracy] [--artifact research_only|plan_only|research_plus_plan]"
---

Load the `build-loop-auto-research:build-loop-auto-research` skill.

Use the `build-loop-auto-research-orchestrator` agent as the coordinating agent for non-trivial work. Parallelize only after the integration points and handoffs are planned.

Interpret `{{ARGUMENTS}}` as:

- the build request
- optional `--repo-path`
- optional `--mode`
- optional `--artifact`

Defaults:

- repo path: current working directory
- optimization mode: `balanced`
- artifact mode: `research_plus_plan`

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/research_build.py --task "{{ARGUMENTS}}" --repo-path "$PWD" --format markdown
```

If `--repo-path`, `--mode`, or `--artifact` are explicitly supplied in `{{ARGUMENTS}}`, use them instead of the defaults.

Use the script output as the initial scaffold, then:

1. deepen repo understanding with focused reads across at least 2 relevant files for repo work
2. in `balanced` and `max_accuracy` mode, add selective external research only when the task depends on current external facts
3. keep any external research restricted to primary sources, academic institutions, and major research labs
4. verify integration points and handoffs, especially for APIs, auth, payments, and cross-service flows
5. for APIs, tools, auth, payments, or deployment-sensitive work, check both provider/tool documentation and deployment/runtime documentation such as Vercel or Apple
6. treat confidence as operational: iterate on `medium` and `low`, spot-check `high`, then re-calibrate
7. ask questions only if ambiguity materially changes the plan
8. if the task is large or likely to outlive the current context window, recommend a context snapshot before compaction or context clearing
9. if the task is issue-like, repetitive, or a prior fix did not hold, run a memory lookup before investigating from scratch

Return the final answer in this order:

1. `Bottom line`
2. `What I found`
3. `Best path`
4. `Why this path`
5. `Risks / unknowns`
6. `Next action`
