# Research Basis

This plugin encodes workflow guidance from a small set of high-signal papers and research publications.

## Core Sources

### Repo-aware retrieval before generation

- `RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation`
- Link: <https://arxiv.org/abs/2303.12570>
- Practical implication:
  - do not plan from a single file
  - build an initial repo map
  - retrieve cross-file context before proposing the path

### Tool-using software engineering agents

- `SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering`
- Princeton publication page:
  - <https://collaborate.princeton.edu/en/publications/swe-agent-agent-computer-interfaces-enable-automated-software-eng/>
- Practical implication:
  - search, edit, diff, run, and test should be first-class actions
  - interface design matters, not just the model

### Realistic evaluation shape

- `SWE-bench: Can Language Models Resolve Real-World GitHub Issues?`
- Princeton publication page:
  - <https://collaborate.princeton.edu/en/publications/swe-bench-can-language-models-resolve-real-world-github-issues/>
- Practical implication:
  - multi-file, execution-backed tasks are the right benchmark
  - toy prompt success is not enough

### Forced self-debugging

- `Teaching Large Language Models to Self-Debug`
- Link: <https://arxiv.org/abs/2304.05128>
- Practical implication:
  - force a `draft -> explain -> critique -> revise` loop on important outputs
  - do not trust first-pass code or first-pass plans

### Generated-test verification

- `CodeT: Code Generation with Generated Tests`
- Link: <https://arxiv.org/abs/2207.10397>
- Practical implication:
  - verification should exist even when the repo has weak tests
  - synthesize smoke tests, assertions, or checklist-based validators when needed

### Repo-exploration and planning

- `LingmaAgent: Role-playing Language Agents for Repository-level Software Engineering`
- Link: <https://arxiv.org/abs/2406.01422>
- Practical implication:
  - summarize repo structure before narrowing to edit targets
  - plan from repository context, not only local context

## Translation Into Plugin Behavior

The plugin therefore defaults to:

1. repo scan before recommendations
2. targeted cross-file retrieval
3. optional external research only from credible sources
4. explicit verification design before implementation
5. a self-debug pass for high-importance outputs
6. user-friendly reporting with confidence and risk signals
