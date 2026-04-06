# Agentic AI — Lab Architectures Reference
> On-demand reference · Load for system-specific architecture details
> Parent: `core.md`

---

## Orchestrated Agent Teams (Type III)

### Anthropic Claude Code / Research
**Pattern:** Orchestrator-Workers (deliberately flat, 1 level)
**Key metrics:** 90.2% improvement | 37% token reduction | 98.7% context savings

- Lead Agent (Opus 4) delegates to multiple Subagents (Sonnet 4)
- One-level-only constraint prevents cascading hallucination
- Subagents write to filesystem; orchestrator reads summaries only
- MCP code-as-API achieves 98.7% context savings
- ~20 lines core logic; compressor triggers at 92% capacity
- h2A dual-buffer queue; 4 cache breakpoints with 90% savings
- 50%+ of LLM calls use cheaper Haiku model

**Innovation:** Context isolation — subagents write to filesystem, orchestrator reads summaries only (no "telephone game"). One-level constraint reflects deliberate safety engineering: deep nesting creates exponentially harder-to-audit call graphs.

**Open problems:** Graceful MCP server failure handling, context management in 100+ tool-call sessions, reliable task resumption after interruption.

---

### OpenAI Agents SDK / Deep Research
**Pattern:** 4 Primitives — Agents, Handoffs, Guardrails, Tracing
**Key metrics:** 87% WebVoyager | 4 primitives | 100s CoT steps

- Handoff mechanism enables agent-to-agent transfers with full context
- Guardrails run in parallel (optimistic execution, not a gate)
- Deep Research: o3 + end-to-end RL, hundreds of CoT steps
- 200K context / 100K max output for Deep Research
- Built-in tracing captures every invocation and handoff

**Innovation:** Handoff mechanism — tools that represent agent transfers. Guardrails run optimistically in parallel, can short-circuit before main agent completes.

**Open problems:** Multi-session state management, preventing handoff loops, cost escalation in Deep Research sessions.

---

### Perplexity Computer
**Pattern:** Meta-Router → Multi-Model → Citation-First Synthesis
**Key metrics:** 20 models | 400+ integrations | 2-4 min Deep Research

- Three-layer stack: Meta-Router → 20 Model Pool → Result Synthesis
- Routes queries across frontier models dynamically (Claude, Gemini, Grok, GPT)
- Dual memory: working (per-session) + persistent (cross-session)
- Citation-first constraint: every claim must be sourced

**Innovation:** Citation-first constraint inherited from search DNA acts as implicit grounding mechanism. Heterogeneous model routing avoids "one-size-fits-all" failure mode.

---

### LangChain DeepAgents
**Pattern:** 4 Additive Components on Basic Agent Loop
**Key metrics:** 3 phases | 4 components | unlimited iterations

- 3-phase graph: Scope → Research → Write
- Research supervisor with self-loop for iterative refinement
- "What makes it deep" = 4 context engineering additions: detailed prompt + planning todo + sub-agents + virtual filesystem

**Innovation:** Not a different algorithm — same basic agent loop with 4 additive context engineering components. Proves that harness design matters more than novel architectures.

---

### Manus AI
**Pattern:** CodeAct + State Machine with Logit Masking
**Key metrics:** Full VM | Python action language | Async execution

- Iterative loop: Analyze → Select → Execute → Observe
- Python code as action language (not JSON tool calls)
- Logit masking controls available tools per state without modifying definitions
- todo.md recitation ensures goal persistence across long sessions
- Refactored 5× in 6 months as models improved

**Innovation:** Logit masking for tool selection — restricts available tools at the logit level per state, rather than modifying tool definitions. Todo.md constant rewriting exploits recency bias in attention.

---

### Google ADK / Gemini
**Pattern:** 5-Component Agent + 8 Canonical Patterns
**Key metrics:** 8 patterns | 1M context window | A2A protocol

- 8 patterns: Sequential, Coordinator, Parallel, Hierarchical, Generator-Critic, Iterative, Human-in-Loop, Composite
- A2A protocol: JSON-RPC 2.0, Agent Cards, Linux Foundation governed
- 1M+ context window (Gemini) enables fewer context management workarounds

**Innovation:** Most comprehensive pattern library paired with A2A as universal agent interoperability protocol. JSON-RPC 2.0 with discoverable Agent Cards.

---

### Microsoft AutoGen / Copilot
**Pattern:** Actor Model (async message-passing) + 3-Layer Architecture
**Key metrics:** 3 layers | 1400+ connectors | M365 deployment

- 3-layer: Core → AgentChat → Extensions
- Actor model enables async message-passing between agents
- Merger with Semantic Kernel into unified Microsoft Agent Framework
- Entra Agent ID provides enterprise identity and governance

**Innovation:** Merger of AutoGen + Semantic Kernel into unified framework. Entra Agent ID brings enterprise identity/governance to agents (agents as first-class organizational entities).

---

### Meta Llama Stack
**Pattern:** Standardized Open-Source API Stack
**Key metrics:** Open source | +29.4% collab gain | PyTorch native

- Horizontal stack: Inference → Safety → Tool Exec → Memory → Agentic API
- Toolformer legacy for self-supervised tool learning
- Enables others to build Types I–IV on standardized base

**Innovation:** Philosophy of providing open foundation vs. commercial orchestration. Standardized API allows any framework to build on top.

---

### DeepSeek
**Pattern:** Reasoning-Integrated Tool Use
**Key metrics:** 1800+ environments | 85K+ instructions | V3.2 latest

- R1 (Jan 2025): Reasoning via pure RL without supervised fine-tuning
- V3.1 (Aug 2025): Hybrid thinking mode, strict function calling
- V3.2 (Dec 2025): First to integrate thinking directly into tool-use
- Massive agent training data synthesis: 1,800+ environments, 85K+ instructions

**Innovation:** Pushing toward Type III from the model level — integrating thinking directly into tool-use rather than separating reasoning and action.

---

### Cohere
**Pattern:** Grounded Generation with Inline Citations
**Key metrics:** Inline citations | Agentic RAG | Grounded generation

- Models trained to produce inline citations for every claim
- Explicit tool_plan field before tool calls provides transparency
- Agentic RAG with cross-reference following

**Innovation:** Grounded generation — models produce inline citations by default. Explicit tool_plan provides reasoning transparency before action.

---

## Autonomous Ecosystem (Type V)

### Devin (Cognition AI)
**Pattern:** Custom RL-Trained Model + Fleet Parallelism
**Key metrics:** 67% PR merge rate | 32B custom model | Fleet parallelism

- Custom 32B parameter model trained via RL (not general LLM)
- Full development environment per agent instance
- Fleet of parallel agents working on PRs simultaneously
- Codebase indexing for deep repository understanding

**Innovation:** Purpose-built model (not general LLM with prompting). Fleet parallelism allows concurrent task execution across multiple PRs.

---

## Cross-Type — Inference-Level Multi-Agent

### xAI Grok
**Pattern:** Native Multi-Agent Council via RL Optimization
**Key metrics:** 4 default agents | 16 max | Native inference

- 4-agent council baked into single inference call: Captain, Research, Logic, Creative
- Configurable up to 16 agents via API
- Multi-agent reasoning at inference level, not application level

**Innovation:** Multi-agent reasoning at inference level (not orchestration code). RL optimization trains the council to collaborate natively within a single model forward pass.

---

## Coding-Focused Architectures

### Cursor
**Pattern:** Shadow Workspace Self-Correction
**Key metrics:** Shadow workspace | Self-test validation | Diff review

- Shadow Workspace: hidden parallel environment for self-testing
- AI tests its own code with linters/unit tests before presenting changes
- Smart assistant philosophy — user reviews diffs
- 4 rule application modes: Always Apply, Auto Attached, Agent Requested, Manual

**Innovation:** Shadow Workspace — hidden parallel environment where AI tests its own code before presenting changes. Self-correction happens before the user sees output.

---

### Windsurf (Cognition)
**Pattern:** Cascade Engine — Graph-Based Codebase Reasoning
**Key metrics:** Cascade engine | Graph reasoning | Auto refactor

- Cascade engine maps entire codebase logic and dependencies
- Graph-based reasoning for autonomous refactors with verification
- Shared timeline model tracks developer actions with timestamps
- Acquired by Cognition (July 2025)
- 57M lines generated per day platform-wide

**Innovation:** Cascade engine uses graph-based reasoning to map codebase dependencies. Shared timeline model distinguishes intentional edits from exploratory changes.

---

## Architecture Selection Decision Tree

```
What are you building?
├── Single LLM + tools (chatbot, Q&A)
│   → Type I. Use any framework or raw API.
│
├── Deterministic multi-step workflow
│   → Type II. LangGraph (control) or CrewAI (speed).
│
├── Multi-agent with orchestrator
│   ├── Research / breadth tasks → Anthropic pattern (orchestrator-workers, context isolation)
│   ├── Enterprise workflow → CrewAI (role-based) or AutoGen (actor model)
│   ├── Code generation → Devin pattern (custom model) or Cursor pattern (shadow workspace)
│   └── Multi-model routing → Perplexity pattern (meta-router)
│
├── Protocol-mediated agent network
│   → Type IV. Google ADK + A2A protocol.
│
└── Self-improving / autonomous
    → Type V. Research only. See self-improvement patterns in memory.md.
```

---

*Lab architectures reference · v1.0 · April 2026*
