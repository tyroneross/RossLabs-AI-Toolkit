# Agentic AI — Memory & Self-Improvement Reference
> On-demand reference · Load for memory architecture or self-improvement patterns
> Parent: `core.md`

---

## Key Insight

Plain-text files in the working directory are the dominant memory substrate in production. Reflexion's memory is a Python list of strings. Voyager's skill library is a folder of JavaScript files. Claude Code's memory system is a markdown file with a 200-line cap. The filesystem IS the external cognition layer.

---

## Memory Substrate Taxonomy

### 1. Filesystem-as-Memory (Markdown)
**Systems:** Claude Code, Manus, Cursor, Devin
**Format:** Plain .md files in working directory
**Strengths:** Human-readable, version-controllable, survives context compression. File paths act as durable pointers even after summarization.
**Insight:** "Filesystem IS the external cognition layer"

### 2. Vector DB + Metadata (Embeddings + JSON)
**Systems:** Voyager (ChromaDB), CrewAI (LanceDB), LangGraph (BaseStore)
**Format:** Embeddings with JSON metadata and timestamps
**Strengths:** Semantic retrieval across growing knowledge bases. Similarity-based deduplication.
**Insight:** "Embed descriptions, not code" — Voyager embeds .txt summaries, not .js source

### 3. In-Context Append-Only (Python Lists/Strings)
**Systems:** Reflexion, Self-Refine, OPRO
**Format:** Python lists of strings concatenated into prompts
**Strengths:** Zero infrastructure overhead, pure in-context learning
**Limitation:** Bounded by context window — Reflexion uses Ω=1-3 reflections only

---

## System Deep Dives

### Claude Code Memory

Four-tier hierarchy with increasing scope:

| Tier | Location | Scope |
|------|----------|-------|
| Enterprise | `/Library/.../ClaudeCode/CLAUDE.md` | Org-wide, IT-managed |
| User | `~/.claude/CLAUDE.md` | Personal, all projects |
| Project | `./CLAUDE.md` | Team-shared via git |
| Local | `./CLAUDE.local.md` | Personal, gitignored |

**Auto Memory:** `~/.claude/projects/<encoded-path>/memory/MEMORY.md`
- 200-line hard limit per file
- Topic files (debugging.md, api-conventions.md) read on demand
- Accumulates 15–30 entries per active project
- Survives context compression via /compact — re-reads from disk
- @import syntax: up to 5 hops deep
- `.claude/rules/*.md` with YAML frontmatter + file globs

### Voyager Skill Library

```
skill/
├── code/          ← async JS functions (Mineflayer API)
├── description/   ← GPT-generated .txt summaries (≤6 sentences)
├── skills.json    ← function name → source code mapping
└── vectordb/      ← ChromaDB persistent storage
```

- Embed descriptions, retrieve by task similarity
- Critic Agent verifies before entry — append-only, never updated or removed
- Complex skills call simpler ones compositionally

### Manus Filesystem

Three core files exploiting recency bias:
- **todo.md** — Live checklist, constant rewriting pushes plan into recent attention
- **notes.md** — Research findings and observations
- **task_plan.md** — Step-by-step roadmap for current task

Design rationale: constant rewriting pushes the plan into the end of the context window. File paths survive summarization as durable pointers even after context compression.

### Cursor Rules

`.cursor/rules/*.md` with YAML frontmatter:

| Mode | Behavior |
|------|----------|
| Always Apply | Injected into every context automatically |
| Auto Attached | Triggered by file glob patterns |
| Agent Requested | Agent selects based on description match |
| Manual | User invokes with @ruleName |

Also supports `AGENTS.md` as simpler alternative for project-level instructions.

### LangGraph Checkpoints

Version 4 checkpoint format:
```json
{
  "v": 4,
  "ts": "2025-...",
  "id": "uuid",
  "channel_values": { ... },
  "channel_versions": { ... },
  "versions_seen": { ... },
  "pending_sends": []
}
```

- **SQLite:** 2 tables (checkpoints, writes) with serialized BLOBs
- **PostgreSQL:** adds checkpoint_blobs, JSONB containment operators
- **BaseStore:** namespace/key/value with vector indexing for semantic search

### CrewAI Memory

**Traditional:** SQLite (id, task_description, metadata JSON, datetime, score) + ChromaDB for embeddings

**Unified (new):** LanceDB with content, scope (hierarchical path), categories, importance (0–1), embeddings, timestamp
- Consolidation threshold: 0.85 similarity
- LLM decides: keep, update, delete, or insert
- Hierarchical scoping enables team-level memory sharing

### Reflexion & Generative Agents

**Reflexion:** `mem: List[str]`, sliding window Ω=1–3
- Each entry: natural language self-reflection after failed trial
- Concatenated directly into actor prompt

**Generative Agents:** 6-field memory objects
- Fields: description, creation_timestamp, last_access_timestamp, importance (1–10), embedding, type
- 3-factor retrieval: recency (exponential decay) + importance + relevance (cosine similarity)
- Reflection threshold: ~150 cumulative importance points, triggers 2–3× per simulated day

### DSPy Optimization

JSON save format:
```json
{
  "demos": [...],                 // compiled few-shot examples
  "signature_instructions": "...", // auto-optimized
  "signature_field_details": {...},
  "traces": [...],
  "metadata": {...}
}
```

- **BootstrapFewShot** → populates demos field
- **MIPROv2 / GEPA** → rewrites signature_instructions entirely
- Optimization runs ~$2, ~20 minutes

---

## Self-Improvement Patterns

Four distinct approaches to agents that improve their own performance:

### MCTS-Based Search (Tree of Thought)
**Pattern:** Monte Carlo Tree Search applied to reasoning
**Mechanism:** Score multiple reasoning paths, expand best branches, backpropagate quality
- UCB selection with c ≈ 1.4 balances exploration/exploitation
- Reflection arrows allow revisiting and improving earlier reasoning
- Applicable to any multi-step decision problem

### OPRO — Optimization by PROmpting
**Pattern:** Append-only trajectory optimization
**Mechanism:** Maintain (instruction_string, accuracy_float) pairs. Each step: sort top-20 ascending, feed to meta-prompt, generate 8 new candidates at temp 1.0
- 100 iterations per optimization run
- Linear trajectory — each step builds on previous best
- Append-only: never removes prior attempts

### PromptBreeder — Evolutionary Population
**Pattern:** Evolutionary optimization of prompts
**Mechanism:** 50 units of (task_prompt + mutation_prompt + fitness score). Two-level mutation: mutation-prompts mutate task-prompts, hyper-mutation prompts mutate mutation-prompts
- Self-referential: P' = LLM(M + P), M' = LLM(H + M)
- Population-based — maintains diversity of approaches
- Fitness-driven selection pressure

### Gödel Agent — Recursive Self-Modification
**Pattern:** Agent reads and modifies its own source code
**Mechanism:** Reads own source via `inspect.getsource()`. LLM proposes modifications → executes → evaluates → retains or rolls back
- Cost: ~$15 for 30 iterations (vs $300 baseline)
- Four-step loop: Read → Propose → Execute → Evaluate
- Retain/rollback decision on each iteration

---

## Memory Design Decision Tree

```
What kind of data?
├── User preferences, small settings → @AppStorage / env vars
├── Session state, task progress → Filesystem (.md files)
├── Growing knowledge base → Vector DB (embeddings)
├── Conversation history → In-context (bounded) or checkpoint store
├── Compiled optimizations → JSON (DSPy format)
├── Structured facts → Entity memory (key-value + metadata)
└── Procedural directives → Config files (CLAUDE.md, rules/*.md)
```

---

*Memory & self-improvement reference · v1.0 · April 2026*
