# Agentic AI — Framework Reference
> On-demand reference · Load when comparing or implementing frameworks
> Parent: `core.md`

---

## Framework Paradigm Comparison

| Paradigm | Framework | State Model | Execution | Strength | Weakness |
|----------|-----------|-------------|-----------|----------|----------|
| Graph-explicit | LangGraph | Typed dict + reducers | Compiled graph, super-steps | Complex stateful workflows | Steep learning curve |
| Role-based | CrewAI | Role/goal/backstory | Crews + Flows | Accessibility, rapid setup | Less fine-grained control |
| Actor model | AutoGen | Async messages | Actor-based, group chat | Research, multi-agent | Heavier abstraction |
| Code-first | smolagents | Python variables | Code generation | Minimal, fast prototyping | Security sandboxing needed |
| Declarative | DSPy | Signatures | Compiled & optimized | Auto-optimization | Learning curve, less control |
| Type-safe | Pydantic AI | Pydantic models | FSM-based graph | Type safety, DX | Smaller ecosystem |
| Infra-layer | Bedrock AgentCore | Managed state | Policy-governed | Enterprise governance | AWS lock-in |

---

## LangGraph

**Paradigm:** Graph-explicit state machine
**Adoption:** ~80K+ GitHub stars, 400+ companies (Uber, LinkedIn, Replit)
**Types covered:** II–IV

**Core primitives:** StateGraph, State (TypedDict), Nodes (functions), Edges (conditional/fixed), Reducers (channel merge logic)

**Architecture:** Pregel/BSP-inspired execution engine. Each superstep: select nodes whose subscribed channels changed → execute in parallel with isolated state → apply updates deterministically. Supports arbitrary cycles (critical for agent loops — can't do this in DAG-only frameworks like Airflow).

**State patterns:**
- Messages-only: `messages: Annotated[list, add_messages]`
- Custom fields with reducers: append, sum, last-write-wins
- `MessagesState` shorthand for common case

**Key capabilities:**
- Checkpointing (MsgPack) enables interrupt/resume on any machine, time-travel debugging
- Send() API for MapReduce fan-out to dynamic worker sets
- 6 streaming modes: values, updates, messages, tasks, checkpoints, custom events
- LangGraph Cloud: task queue decouples triggers from execution threads, retries from last checkpoint

**Trade-offs:** Low-abstraction design requires explicit state schema and edge wiring. Learning curve is the #1 cited limitation. But this explicitness is what makes complex workflows debuggable.

---

## CrewAI

**Paradigm:** Role-based multi-agent teams
**Adoption:** 100K+ certified devs, 60% Fortune 500
**Types covered:** II–III

**Core primitives:** Crews (agent teams), Flows (event-driven orchestration), @start (entry), @listen (subscribe), @router (conditional branch)

**Architecture:** Agents defined by role, goal, and backstory. Three process types: sequential, hierarchical (manager agent delegates dynamically), custom. Flows layer adds event-driven orchestration with typed state.

**Memory architecture:**
- Short-term: in-session message history
- Long-term: vector store persistence across sessions
- Entity memory: structured facts about key entities
- Contextual: relevance-ranked retrieval
- Unified system (new): LanceDB with 0.85 similarity consolidation threshold

**Key capabilities:**
- Dual-workflow: Crews for autonomous collaboration, Flows for deterministic orchestration
- Hierarchical mode: manager LLM acts as dispatcher with meta-reasoning
- MCP tool support, LangChain tool compatibility
- AMP (agent management platform) for deployment/monitoring

**Trade-offs:** Less fine-grained control than LangGraph. Communication overhead scales quadratically in fully-connected patterns. Key open problem: detecting consensus vs. unproductive debate loops.

---

## Pydantic AI

**Paradigm:** Type-safe agents
**Adoption:** Growing ecosystem, built by Pydantic team
**Types covered:** II–III

**Core primitives:** Agent, RunContext[T], Result, Tools (with dependency injection)

**Architecture:** FSM-based graph execution with Pydantic models for all inputs/outputs. Built-in dependency injection via RunContext. History processors run before each LLM call.

**Key capabilities:**
- Type-safe state management with IDE autocomplete
- Three context management strategies: truncation, token-aware trimming, LLM summarization
- Logfire integration: 4 lines for full observability (OpenTelemetry-based)
- ModelRetry for graceful tool failure handling
- Native MCP support via toolsets

**Trade-offs:** Smaller ecosystem than LangGraph/CrewAI. Strong DX but fewer production case studies.

---

## smolagents (Hugging Face)

**Paradigm:** Code-first agents
**Adoption:** HuggingFace ecosystem
**Types covered:** I–III

**Core primitives:** CodeAgent (generates executable Python), ToolCallingAgent (structured tool calls), ManagedAgent (sub-agent delegation)

**Architecture:** Agents write and execute Python code directly instead of structured JSON tool calls. This gives agents native control flow (loops, conditionals, error handling) at lower token cost.

**Key capabilities:**
- CodeAgent generates executable Python rather than JSON tool calls
- Multi-step code execution with variable persistence across steps
- ManagedAgent for orchestrator-worker patterns
- OpenTelemetry-based observability via SmolagentsInstrumentor

**Trade-offs:** Security sandboxing is critical — executing generated code needs E2B or Docker isolation. Minimal framework with fewer guardrails.

---

## DSPy (Stanford)

**Paradigm:** Declarative programming model
**Adoption:** Research + growing production use
**Types covered:** I–II

**Core primitives:** Signature (input/output spec), Module (composable component), Optimizer (auto-prompt-tuner), Evaluate (metric-based assessment)

**Architecture:** Separates what (Signatures) from how (Optimizers). Define the task spec, let the framework find optimal prompts automatically.

**Key capabilities:**
- BootstrapFewShot: populates few-shot demos automatically
- MIPROv2 / GEPA: rewrites instructions entirely via optimization
- Optimization runs ~$2, ~20 minutes
- JSON save format preserves compiled demos + optimized instructions

**Trade-offs:** Learning curve for the declarative paradigm. Less control over exact prompt wording. Strongest for tasks with clear metrics.

---

## AutoGen (Microsoft)

**Paradigm:** Actor-model async messaging
**Adoption:** Microsoft/Azure ecosystem
**Types covered:** III–IV

**Core primitives:** AssistantAgent, GroupChat, Messages (async)

**Architecture:** Three-layer: Core (event-driven messaging) → AgentChat (multi-agent orchestration) → Extensions (tool integrations). Actor model enables async message passing.

**Key capabilities:**
- Group chat patterns for multi-agent reasoning
- Async message passing decouples agents
- Merger with Semantic Kernel into unified Microsoft Agent Framework
- Entra Agent ID for enterprise identity/governance
- 1400+ connectors through Microsoft ecosystem

**Trade-offs:** Heavier abstraction. More suited to research and exploration than lean production deployments.

---

## Bedrock AgentCore (Amazon)

**Paradigm:** Managed infrastructure layer
**Adoption:** AWS enterprise customers
**Types covered:** II–III

**Core primitives:** Action Groups, Knowledge Bases, Guardrails (managed)

**Architecture:** Managed agent service with policy-governed execution. Integrates with AWS identity, security, and compliance infrastructure.

**Key capabilities:**
- Built-in guardrails (content filtering, topic avoidance)
- Knowledge base integration (RAG with managed vector stores)
- Multi-agent collaboration protocols
- Enterprise governance out of the box

**Trade-offs:** AWS lock-in. Less flexibility than open-source alternatives. Best for orgs already deep in AWS.

---

## Framework Selection Decision Tree

```
What's the priority?
├── Maximum control over state and flow?
│   → LangGraph (graph-explicit, Pregel-inspired)
├── Fast setup with role-based teams?
│   → CrewAI (role/goal/backstory, Flows for orchestration)
├── Type safety and modern Python DX?
│   → Pydantic AI (FSM + dependency injection)
├── Minimal code, code-as-action?
│   → smolagents (Python execution, HF ecosystem)
├── Auto-optimize prompts from metrics?
│   → DSPy (declarative, compiler approach)
├── Research / async multi-agent exploration?
│   → AutoGen (actor model, group chat)
└── Enterprise AWS-native with managed governance?
    → Bedrock AgentCore
```

---

## Cross-Framework Comparison: Tool Integration

| Capability | LangGraph | CrewAI | Pydantic AI | smolagents |
|-----------|-----------|--------|-------------|------------|
| Tool definition | @tool decorator | CrewAI-native + LangChain | @tool + Pydantic schema | @tool / ToolCollection |
| MCP support | Via langchain | Via crewai-tools | Native (toolsets) | ToolCollection |
| State access from tools | InjectedState | Not in tools | Via RunContext | Class __init__ |
| Retry from tool | RetryPolicy | max_retry_limit | raise ModelRetry | Re-run agent |
| Tool count limit | Practical ~50 | Practical ~20/crew | Practical ~30 | Practical ~20 |

---

*Framework reference · v1.0 · April 2026*
