# Agentic AI — Architecture Taxonomy

> Empirical catalog · RossLabs.ai research corpus · 368 sources · Data verified April 2026
> Parent skill: `agent-builder` · Sibling catalog: `02-harness-components.md`, `03-frameworks.md`, `04-memory-substrates.md`, `05-lab-patterns.md`

**Read this when** the request involves choosing or classifying an architecture type, citing adoption stats, resolving single-vs-multi-agent debates, or grounding a design decision in empirical evidence.

---

## Governing Thought

Agentic AI architectures are converging from isolated assistants toward protocol-standardized multi-agent ecosystems — but production deployment requires solving **coordination reliability**, not just model capability.

Three pillars support this:

1. **Five architecture eras** (2015–2026), each adding a capability layer: RL game-players → Transformers → First LLM agents → Framework explosion → Production systems with A2A/MCP protocols
2. **Five architecture types** along Autonomy × Coordination axes segment every known approach (see Taxonomy below)
3. **Binding constraints** are trust, governance, and coordination — not model capability. 70%+ multi-agent failures are systemic (MAST). Only 11% of orgs run production agents (Deloitte 2025). Gartner: 40%+ agentic projects canceled by 2027.

---

## Architecture Taxonomy

Five types along two axes: autonomy (how much human direction) × coordination (how agents interact).

### Type I — Augmented Assistant
Single LLM + tools, human in loop. L1–L2 autonomy. Single-turn horizon. **88% adoption.**
Examples: ChatGPT with plugins, basic RAG systems.

### Type II — Workflow Automaton
Human-coded paths with LLM as module. L2–L3 autonomy. Minutes horizon. **38% adoption.**
Linear/DAG topology. Designer + monitor human role.

### Type III — Orchestrated Agent Team
LLM orchestrator delegates to specialized workers. L3–L4 autonomy. Hours–days horizon. **23% adoption.**
Hub-and-spoke topology, 2–12 agents. Early production. **Current frontier.**

### Type IV — Networked Fabric
Protocol-mediated agent swarm. L4 autonomy. Days–weeks horizon. **~5% adoption.**
Mesh/federation topology, 10–100+ agents. Pilot/experimental. Governance + oversight human role.

### Type V — Autonomous Ecosystem
Self-goal-setting, self-modifying. L4–L5 autonomy. Continuous horizon. **~1% adoption.**
Adaptive network, unbounded agents. Research only. Human as strategic auditor.

### Comparison Matrix

| Dimension | Type I | Type II | Type III | Type IV | Type V |
|-----------|--------|---------|----------|---------|--------|
| Core | LLM + tools | Coded paths | LLM orchestrator | Distributed consensus | Self-modifying |
| Topology | Single node | Linear/DAG | Hub-and-spoke | Mesh | Adaptive |
| Agent Count | 1 | 1 (multi-step) | 2–12 | 10–100+ | Unbounded |
| Task Horizon | Single turn | Minutes | Hours–days | Days–weeks | Continuous |
| Human Role | Operator | Designer | Goal setter | Governance | Auditor |
| Readiness | Production | Production | Early production | Pilot | Research |

---

## 5 Points of Consensus

1. **Minimal agent = LLM + tools in a loop** — Every major source converges: Lilian Weng (2023), Anthropic, Swyx's IMPACT framework.

2. **Start simple, add complexity only when validated** — Anthropic, Chip Huyen, Harrison Chase all emphasize independently.

3. **Evaluations are critical** — Andrew Ng: evals are "the single biggest predictor of whether someone executes well."

4. **Compound errors are the fundamental math challenge** — Chip Huyen: 95% accuracy per step → only 0.6% accuracy over 100 steps.

5. **Tool design matters as much as prompt design** — Anthropic: tool descriptions deserve the same engineering attention as system prompts.

---

## 4 Active Debates

### 1. Single-Agent vs. Multi-Agent
- **Pro multi-agent:** Anthropic June 2025: 90.2% improvement on research tasks. Parallelizable breadth tasks excel.
- **Pro single-agent:** Cognition: "Don't Build Multi-Agents." Reasoning models handle planning natively.
- **Resolution:** Use-case dependent. Multi-agent for breadth; single for depth. Cost: agents 4× tokens; multi-agent 15×.

### 2. Frameworks vs. Raw APIs
- **Pro frameworks:** Harrison Chase: capture collective wisdom, useful infrastructure.
- **Pro raw APIs:** Anthropic: "extra layers of abstraction obscure prompts and responses."
- **Resolution:** Own your cognitive architecture (differentiator). Outsource agentic infrastructure (task queues, persistence).

### 3. The "Bitter Lesson" for Agents
- **Pro scaffolding:** Harness changes yield 13.7pt gains. Frameworks provide collective wisdom.
- **Pro minimalism:** Manus refactored 5× in 6 months. Vercel removed 80% of tools → fewer steps, better results.
- **Resolution:** Heavy scaffolding may have diminishing returns. Lance Martin: "Over time you're having to strip away structure."

### 4. Augmentation vs. Automation
- **Augmentation camp:** Karpathy: "Iron Man suit, not Iron Man." Tesla Autopilot: 12 years without full autonomy.
- **Automation camp:** Claude Code and Devin demonstrate genuine autonomous capability in bounded domains.
- **Resolution:** Karpathy's "autonomy slider" — Cursor's Tab → cmd+K → Cmd+L → Agent mode. Let users control autonomy level.

---

## Key Statistics (Verified)

| Stat | Source | Verified |
|------|--------|----------|
| 11% of orgs have production agentic systems | Deloitte 2025 Emerging Tech Trends (500 US tech leaders) | ✓ |
| 40%+ agentic projects canceled by 2027 | Gartner June 2025 | ✓ |
| 70%+ multi-agent failures are systemic | MAST study (arXiv) | ✓ |
| 90.2% improvement multi-agent vs single-agent | Anthropic internal eval, Claude Opus 4 + Sonnet 4 | ✓ |
| 15× token consumption for multi-agent vs chat | Anthropic multi-agent research system | ✓ |
| 4× token consumption for single agent vs chat | Anthropic multi-agent research system | ✓ |
| 40% decrease in task completion from tool desc rewriting | Anthropic tool-testing agent | ✓ |
| 13.7pt improvement from harness changes alone | LangChain TerminalBench 2.0 | ✓ |
| 280-fold drop in inference costs over 2 years | Stanford AI Index 2025 | ✓ |
| 95% step accuracy → 0.6% over 100 steps | Chip Huyen compound error analysis | ✓ |

These numbers are the empirical anchor for the methodology's "start single, justify multi" default. Cite them when a user pushes for multi-agent without cost/failure-mode justification.

---

## Future Trajectory

### Near (2026–2027) — Protocol Standardization
A2A and MCP become de facto standards. Vertical agents dominate (legal, finance, healthcare, code). Enterprise trust frameworks mature. Type III reaches 40%+ adoption.

### Mid (2027–2029) — Agent Economies
Type IV Networked Fabrics reach production. Agent-to-agent marketplaces emerge. Multi-agent governance becomes regulatory requirement. Human role shifts to strategic auditor.

### Far (2029+) — AGI Through Agents
Type V Autonomous Ecosystems enter narrow production. Self-improving systems raise safety considerations. International governance for autonomous AI networks. AGI may emerge through multi-agent collaboration, not single models.

---

## Architecture Timeline

| Era | Period | Key Developments |
|-----|--------|-----------------|
| RL Pioneers | 2015–2017 | AlphaGo, DQN, OpenAI Gym. Goal-directed agents in closed environments. |
| Transformer | 2017–2020 | Attention Is All You Need, BERT, GPT-2/3. Scalable reasoning emerges. |
| First LLM Agents | 2021–2023 | ReAct, Toolformer, AutoGPT, BabyAGI. Chain-of-thought + tool use. |
| Framework Explosion | 2023–2025 | LangGraph, CrewAI, AutoGen, DSPy. Multi-agent orchestration matures. |
| Production Systems | 2025–2026 | A2A/MCP protocols, enterprise governance, vertical agents at scale. |

---

## Coordination Patterns

Seven recurring patterns across all architectures:

| Pattern | Description | Complexity | When to Use |
|---------|-------------|-----------|-------------|
| Prompt Chaining | Sequential LLM calls, each output feeds next | Low | Linear tasks with clear stages |
| Routing/Triage | Classify input → dispatch to specialist | Low | Multi-domain, heterogeneous queries |
| Parallelization | Multiple LLMs on same input simultaneously | Medium | Tasks decomposable into independent parts |
| Orchestrator-Workers | Lead agent delegates, synthesizes results | Medium | Research, complex analysis |
| Evaluator-Optimizer | Generate + critique + refine loop | Medium | Quality-critical outputs |
| Hierarchical | Multi-level delegation tree | High | Large-scale, enterprise workflows |
| Autonomous Loop | LLM decides when to stop | High | Open-ended, exploratory tasks |

---

*Catalog file 01/05 · derived from RossLabs agentic architectures research corpus · April 2026*
