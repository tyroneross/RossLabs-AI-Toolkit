# Plugin Architecture: Protocol, Transport, Storage, and Hosting

## Core Insight

MCP is a **protocol layer for AI tool interoperability** — not a CLI wrapper, and not something you "switch to CLI." The architectural questions are:

1. **Transport** — How does Claude talk to the MCP server? (stdio vs Streamable HTTP)
2. **Storage** — Where does data persist? (local files vs cloud database)
3. **Hosting** — Where does the server process run? (local vs Railway/Supabase/Vercel)

These are three independent axes. You can mix and match: stdio transport with cloud storage, HTTP transport with local files, or any combination.

---

## Three-Layer Architecture (All 4 Plugins)

Every RossLabs plugin already follows the same pattern:

```
Interface Layer    MCP Server (AI consumer)  │  CLI (human consumer)
                          ↓                  │         ↓
Core Logic         Shared modules ───────────┘
                   (scanner, storage, capture, snapshot, etc.)
                          ↓
Storage Backend    File I/O (.claude/ or .ibr/)
```

Both MCP and CLI are **thin interface layers** that delegate to the **same shared core modules**. Neither is primary — they serve different consumers (AI agent vs human developer) over the same logic.

### Shared Core Import Map

| Plugin | MCP `tools.ts` and CLI both import from |
|--------|-----------------------------------------|
| **Bookmark** | `config`, `snapshot/capture`, `snapshot/compress`, `snapshot/storage`, `restore/index`, `threshold/state` |
| **Debugger** | `storage`, `retrieval` — MCP adds `withSilentConsole()` (a stdio transport concern, not core logic) |
| **IBR** | `scan`, `index`, `session`, `capture`, `native/index`, `schemas` |
| **NavGator** | `scanner`, `storage`, `impact`, `resolve`, `trace`, `diagram`, `agent-output`, `config`, `git` |

---

## Current State: Per-Plugin Analysis

### Bookmark — Session Context Continuity

| Aspect | Details |
|--------|---------|
| **MCP Tools (5)** | `snapshot`, `restore`, `status`, `list`, `show` |
| **CLI Commands (11)** | All MCP tools + `check`, `stop`, `precompact`, `config`, `init`, `setup`, `uninstall` |
| **Storage** | `.claude/bookmarks/` — JSON snapshots, markdown summaries |
| **Dependencies** | Node.js stdlib only |
| **Skills** | `context-continuity` — triggers on "restore context", "pick up where I left off" |

### Claude Code Debugger — Debugging Memory

| Aspect | Details |
|--------|---------|
| **MCP Tools (7)** | `search`, `store`, `detail`, `status`, `list`, `patterns`, `outcome` |
| **CLI Commands (18)** | All MCP tools + `debug`, `mine`, `batch`, `config`, etc. |
| **Storage** | `.claude/memory/` — JSONL incident log, JSON index files |
| **Dependencies** | Node.js stdlib only |
| **Skills** | `debugging-memory` — verdict-based framework (KNOWN_FIX → LIKELY_MATCH → WEAK_SIGNAL → NO_MATCH) |

### IBR (Interface Built Right) — UI Validation

| Aspect | Details |
|--------|---------|
| **MCP Tools (14)** | `scan`, `snapshot`, `compare`, `screenshot`, `references`, `native_scan`, `native_snapshot`, `native_compare`, `native_devices`, `scan_macos`, `validate_tokens`, `scan_static`, `bridge_to_source` |
| **CLI Commands** | `npx ibr scan`, `snapshot`, `compare`, `start`, `check` (fewer than MCP) |
| **Storage** | `.ibr/` — sessions, baselines, reference screenshots, tokens.json |
| **Dependencies** | Playwright, Pixelmatch, pngjs (browser automation + image comparison) |
| **Skills** | `design-reference`, `design-validation`, `interactive-testing`, `iterative-refinement` |

**IBR is unique in two ways:**
- Returns **base64-encoded PNG images** inline via MCP responses (Claude sees images directly)
- Requires **Playwright/Chromium** — constrains hosting options

### NavGator — Architecture Tracking

| Aspect | Details |
|--------|---------|
| **MCP Tools (7)** | `scan`, `status`, `impact`, `connections`, `diagram`, `trace`, `summary` |
| **CLI Commands (18)** | All MCP tools + `ui`, `rules`, `coverage`, `prompts`, `export`, etc. |
| **Storage** | `.claude/architecture/` — JSON graph, component/connection files, Mermaid diagrams |
| **Dependencies** | ts-morph (optional, for AST scanning) |
| **Skills** | `gator-setup`, `architecture-scan`, `architecture-export`, `impact-analysis` |

---

## Axis 1: MCP Transport — stdio vs Streamable HTTP

| Factor | stdio (current) | Streamable HTTP |
|--------|-----------------|-----------------|
| Setup | Auto-spawned by Claude Code | Needs a running server |
| Latency | Zero network overhead | Network round-trip |
| Works offline | Yes | No (unless localhost) |
| Multi-device | No | Yes |
| Team sharing | No | Yes |
| Claude Code web | No | Yes |

These are **not mutually exclusive**. A plugin can register as stdio locally and HTTP remotely. Switching transport does NOT change Skills — MCP tool names stay the same:

```bash
# Local (stdio)
claude mcp add bookmark -- node dist/mcp/server.js

# Remote (HTTP) — same tool names, same Skills
claude mcp add --transport http bookmark https://api.example.com/mcp/bookmark
```

### Transport-Layer Concerns

The Debugger's `withSilentConsole()` wrapper is a perfect example of a transport concern — stdio JSON-RPC cannot tolerate stray `console.log` output. This goes away entirely with HTTP transport. Transport choice affects the server adapter code, not core logic.

---

## Axis 2: Storage Backend — Files vs Database

All plugins currently use direct file I/O. To enable cloud storage without rewriting core logic, introduce a **storage adapter interface**:

```typescript
interface StorageAdapter {
  read(key: string): Promise<string | null>;
  write(key: string, data: string): Promise<void>;
  list(prefix: string): Promise<string[]>;
  delete(key: string): Promise<void>;
}
```

### Implementations

| Adapter | Description | Best For |
|---------|-------------|----------|
| `FileStorageAdapter` | Current behavior — reads/writes `.claude/` or `.ibr/` | Local-only usage |
| `SupabaseStorageAdapter` | Uses existing Supabase project with per-plugin schemas | Zero additional cost |
| `TursoStorageAdapter` | SQLite-compatible, easiest migration from JSON files | Separate free DB |

Storage choice is **independent of transport choice**. You can use stdio transport with a cloud database (data syncs to cloud, but MCP runs locally), or HTTP transport with local file storage (server runs remotely, writes to its own disk).

### Per-Plugin Storage Migration Complexity

| Plugin | Current Format | Migration to SQL | Notes |
|--------|---------------|-----------------|-------|
| Bookmark | JSON files, markdown | Simple — key-value with metadata | Snapshots are self-contained documents |
| Debugger | JSONL log + JSON index | Moderate — incident table + full-text search | JSONL → rows is natural; search needs FTS |
| IBR | JSON + PNG screenshots | Moderate — metadata in DB, images in object storage | Binary assets need blob storage or S3 |
| NavGator | JSON graph structure | Simple — nodes and edges tables | Graph data maps cleanly to relational |

---

## Axis 3: Hosting — Where Does the Server Run?

| Plugin | Local (stdio) | Railway | Supabase Edge | Vercel |
|--------|--------------|---------|---------------|--------|
| Bookmark | Works | Works | Works (best) | Works |
| Debugger | Works | Works | Works (best) | Works |
| IBR | Works | **Best** (Playwright) | No (Deno, no Playwright) | Timeout risk |
| NavGator | Works | Works | Works (best) | Works |

### Railway — Best for IBR

- **Pro plan**: $5/mo base + usage
- Docker support for Playwright/Chromium
- Always-on persistent services (no cold starts)
- IBR is the only plugin that needs this

### Supabase Edge Functions — Best for Bookmark, Debugger, NavGator

- **Already paying** Pro ($25/mo)
- Deno edge functions with sub-100ms cold starts
- **Use your existing database** — add schemas, zero additional cost:

```sql
CREATE SCHEMA bookmark;
CREATE SCHEMA debugger;
CREATE SCHEMA navgator;
```

- 500K invocations/mo on Pro plan
- Cannot run IBR (Deno runtime lacks Playwright support)

### Vercel — Best for Dashboards, Not MCP

- **Pro plan**: $20/mo
- 60s function timeout problematic for IBR scans and MCP's persistent connections
- Cold starts add 1-5s latency after idle periods
- **Good for**: A web dashboard consuming the same cloud storage (NavGator graphs, Debugger patterns, IBR history)
- **Not ideal for**: MCP server hosting

---

## Free Database Options

If you want cloud storage without using your existing Supabase database:

| Provider | Free Tier | SQLite-compatible | Serverless-friendly | Lock-in |
|----------|-----------|-------------------|---------------------|---------|
| **Turso** | 9GB, 500 DBs, 25M reads/mo | Yes | Yes | Low |
| **Neon** | 0.5GB, 100 compute hrs/mo | No (Postgres) | Yes | Low |
| **Upstash** | 256MB, 10K cmds/day | No (Redis) | Yes | Low |
| **Cloudflare D1** | 5GB, 25B reads/mo | Yes | Workers only | Medium |

### Recommendations

- **Zero new services**: Add schemas to your existing Supabase Postgres. Already paying for it.
- **Separate free DB**: **Turso** — SQLite-compatible means trivial migration from JSON files. 9GB and 500 databases for free.
- **Skip Neon**: 0.5GB is tight and you already have Supabase Postgres.
- **Skip Cloudflare D1**: Locks you into Workers for compute. Not worth the vendor lock-in.

---

## Skills and Permissions

Skills are the glue between Claude's intent and plugin tools. They are **transport-agnostic** — the same Skill works whether MCP uses stdio or HTTP.

### How Skills Reference Tools

Skills use `allowed-tools` in frontmatter:

```yaml
# MCP tools (current pattern)
allowed-tools: mcp__bookmark__snapshot, mcp__bookmark__restore

# CLI via Bash (alternative)
allowed-tools: Bash(npx @tyroneross/bookmark *)
```

The Skill body text describes *when* and *how* to use tools semantically. It doesn't care about transport:

```markdown
When the user says "restore context", use `bookmark restore` to recover the most recent snapshot.
```

### Switching Transport Doesn't Change Skills

Changing MCP from stdio to HTTP transport only changes the registration command:

```bash
# Before (stdio)
claude mcp add bookmark -- node dist/mcp/server.js

# After (HTTP) — Skills unchanged, tool names unchanged
claude mcp add --transport http bookmark https://api.example.com/mcp/bookmark
```

### Hooks

Hooks support multiple trigger types — these are orthogonal to MCP transport:

| Hook Type | Example | Transport-dependent? |
|-----------|---------|---------------------|
| `command` | `npx @tyroneross/bookmark check` | No — runs locally |
| `http` | `https://api.example.com/hooks/notify` | No — independent HTTP call |
| `prompt` | Inject context into Claude's prompt | No — client-side |
| `agent` | Spawn sub-agent for complex logic | No — client-side |

---

## Interface Layer Trade-offs

### Token Costs

| Approach | Discovery cost | Per-call cost | Output format |
|----------|---------------|---------------|---------------|
| MCP (7 tools) | ~350 tokens (schemas in context) | 0 (direct call) | Typed (text, images) |
| CLI (7 commands) | ~100 tokens (Skill description) | ~30 tokens (Bash command) | Text/JSON parsing needed |

MCP tools consume more context tokens upfront (schemas always loaded), but CLI invocations add per-call overhead. For plugins with <10 tools, the difference is negligible.

### Permission Model

| Approach | Behavior |
|----------|----------|
| MCP tools | Auto-allowed after server approval at session start |
| CLI via Bash | Per-call approval unless `allowed-tools` set in Skill frontmatter |

Both achieve the same result with proper configuration. MCP is quieter by default.

### Image Handling (IBR)

| Approach | Flow |
|----------|------|
| MCP | Tool returns base64 PNG inline → Claude sees image directly |
| CLI | Command saves PNG to disk → Claude uses Read tool → sees image |

Both work. MCP is one fewer step. CLI is equally functional since Claude Code's Read tool handles images natively.

---

## Phased Roadmap

### Phase 0 — Document (This PR)

Rewrite this ARCHITECTURE.md with corrected protocol-layer framing. No code changes required.

### Phase 1 — Storage Adapter Interface

- Define `StorageAdapter` interface in each plugin's core module
- Refactor existing file I/O calls into `FileStorageAdapter` implementing that interface
- **Pure refactor** — all behavior stays identical, all tests pass unchanged
- Enables Phases 2 and 3 without further core changes

### Phase 2 — Remote Transport

- Add HTTP transport adapter to MCP servers (Streamable HTTP)
- Deploy **IBR → Railway** (Playwright requirement)
- Deploy **Bookmark, Debugger, NavGator → Supabase Edge Functions** (zero additional cost)
- Register with `claude mcp add --transport http`
- Skills unchanged — tool names are transport-independent

### Phase 3 — Cloud Storage

- Implement `SupabaseStorageAdapter` (reuse existing project, add schemas)
- Or implement `TursoStorageAdapter` (free, SQLite-compatible)
- Enables: multi-device sync, team sharing, Claude Code web sessions
- Migrate from file-based JSON/JSONL to database tables

### Phase 4 — Dashboard

- Vercel-hosted web UI consuming the same cloud storage
- Visualize NavGator architecture graphs, Debugger incident patterns, IBR regression history
- Read-only consumer of the shared database — separate from MCP servers
