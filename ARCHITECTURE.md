# CLI vs MCP Plugin Architecture Assessment

## Executive Summary

All 4 RossLabs plugins (Bookmark, Claude Code Debugger, IBR, NavGator) currently use **MCP over stdio** for tool invocation, but every plugin already ships a **full CLI implementation** via Commander.js that is a superset of the MCP tools. All storage is **file-based** (JSON/JSONL in `.claude/` directories) — no databases are used today.

This creates three viable paths forward:

1. **CLI-first** — Rewrite Skills to invoke CLI commands via Bash instead of MCP tools
2. **Remote MCP via HTTP** — Deploy MCP servers to Railway/Vercel using Streamable HTTP transport
3. **Hybrid** — CLI locally, remote API with free database for cloud sync

---

## Current State: Per-Plugin Analysis

### Bookmark — Session Context Continuity

| Aspect | Details |
|--------|---------|
| **MCP Tools (5)** | `snapshot`, `restore`, `status`, `list`, `show` |
| **CLI Commands (11)** | All MCP tools + `check`, `stop`, `precompact`, `config`, `init`, `setup`, `uninstall` |
| **Storage** | `.claude/bookmarks/` — JSON snapshots, markdown summaries |
| **Database** | None |
| **Key Dependencies** | None beyond Node.js stdlib |
| **CLI-convertible?** | Yes — trivial. CLI is already the richer interface. Hooks already invoke CLI commands. |

**MCP-specific behavior**: None. The MCP server delegates to the same core functions as the CLI.

### Claude Code Debugger — Debugging Memory

| Aspect | Details |
|--------|---------|
| **MCP Tools (7)** | `search`, `store`, `detail`, `status`, `list`, `patterns`, `outcome` |
| **CLI Commands (18)** | All MCP tools + `debug`, `mine`, `batch`, `detail`, `outcome`, `config`, etc. |
| **Storage** | `.claude/memory/` — JSONL incident log, JSON index files |
| **Database** | None |
| **Key Dependencies** | None beyond Node.js stdlib |
| **CLI-convertible?** | Yes — trivial. JSONL storage is self-contained. |

**MCP-specific behavior**: None. Verdict-based retrieval and pattern extraction work identically via CLI.

### IBR (Interface Built Right) — UI Validation

| Aspect | Details |
|--------|---------|
| **MCP Tools (14)** | `scan`, `snapshot`, `compare`, `list_sessions`, `screenshot`, `references`, `native_scan`, `native_snapshot`, `native_compare`, `native_devices`, `scan_macos`, `validate_tokens`, `scan_static`, `bridge_to_source` |
| **CLI Commands** | `npx ibr scan`, `snapshot`, `compare`, `start`, `check` (fewer than MCP) |
| **Storage** | `.ibr/` — sessions, baselines, reference screenshots, tokens.json |
| **Database** | None |
| **Key Dependencies** | Playwright, Pixelmatch, pngjs (browser automation + image comparison) |
| **CLI-convertible?** | Moderate. 14 MCP tools vs fewer CLI commands — CLI needs parity additions. Image return via MCP (base64 in JSON-RPC) has no direct CLI equivalent, but images can be saved to disk and read via Claude's Read tool. |

**MCP-specific behavior**: The `screenshot` and `native_scan` tools return **base64-encoded PNG images** inline via MCP responses. This is the one plugin where MCP provides a genuine advantage — Claude receives images directly without file I/O. However, writing to `.ibr/references/` and using Claude's Read tool is functionally equivalent.

**IBR also has unique hosting considerations**: Playwright requires a browser environment, making serverless deployment harder (but not impossible — Playwright can run on Railway or Vercel with chromium layer).

### NavGator — Architecture Tracking

| Aspect | Details |
|--------|---------|
| **MCP Tools (7)** | `scan`, `status`, `impact`, `connections`, `diagram`, `trace`, `summary` |
| **CLI Commands (18)** | All MCP tools + `ui`, `rules`, `coverage`, `prompts`, `export`, etc. |
| **Storage** | `.claude/architecture/` — JSON graph, component/connection files, Mermaid diagrams |
| **Database** | None |
| **Key Dependencies** | ts-morph (optional, for AST scanning) |
| **CLI-convertible?** | Yes — trivial. Graph operations and Mermaid generation work identically via CLI. |

**MCP-specific behavior**: None. The MCP server is a thin wrapper around shared core logic.

---

## Option 1: CLI-First (Local, No Server Processes)

### How It Works

Replace MCP tool references in Skills with `allowed-tools: Bash(...)` directives that invoke CLI commands.

**Before (MCP-based Skill):**
```yaml
---
name: context-continuity
description: Save and restore session context across compactions
---
Use the bookmark_snapshot and bookmark_restore MCP tools to manage context.
```

**After (CLI-based Skill):**
```yaml
---
name: context-continuity
description: Save and restore session context across compactions
allowed-tools: Bash(npx @tyroneross/bookmark *)
---
Use `npx @tyroneross/bookmark snapshot` and `npx @tyroneross/bookmark restore` to manage context.
```

### Advantages

- **Zero server processes** — No MCP server running in background
- **CLI commands already exist** — and are a superset of MCP tools (3 of 4 plugins have more CLI commands than MCP tools)
- **Simpler debugging** — Run commands directly in terminal
- **No initialization overhead** — No JSON-RPC handshake or tool discovery
- **Hooks already use CLI** — No changes needed for hook-based automation
- **Works identically anywhere** — Same commands local, CI, remote SSH

### Disadvantages

- **Bash permission prompts** — Each CLI call may trigger approval (mitigated by `allowed-tools` in Skill frontmatter)
- **No structured tool discovery** — Claude doesn't see CLI commands in its tool list; relies on Skill descriptions
- **Text output parsing** — CLI returns text/JSON to stdout; MCP returns typed content (text, images)
- **IBR image handling** — Screenshots must be written to disk then read, rather than returned inline
- **No streaming** — CLI commands complete before Claude sees output

### Migration Effort Per Plugin

| Plugin | Effort | Changes |
|--------|--------|---------|
| Bookmark | ~1 hour | Update 2 SKILL.md files, add `--json` flag if missing |
| Debugger | ~1 hour | Update 2-3 SKILL.md files, verify JSON output |
| IBR | ~4 hours | Add CLI parity for 9 missing commands, update Skills, handle image output |
| NavGator | ~1 hour | Update 2-3 SKILL.md files, verify JSON output |

---

## Option 2: Remote MCP via HTTP Transport

### How It Works

Claude Code natively supports **Streamable HTTP** MCP transport. Deploy each plugin's MCP server as an HTTP endpoint instead of a local stdio process.

```bash
# Current (stdio, local)
claude mcp add bookmark -- node /path/to/dist/mcp/server.js

# Remote (HTTP transport)
claude mcp add --transport http bookmark https://your-api.railway.app/mcp/bookmark
```

### Hosting Platform Comparison

#### Railway

| Aspect | Details |
|--------|---------|
| **Plan** | Pro ($5/mo base + usage) |
| **Deployment** | Docker or Nixpack auto-detect for Node.js |
| **Always-on?** | Yes — persistent services, not cold-start |
| **Database** | Postgres ($5/mo), Redis ($5/mo) — adds cost |
| **Best for** | Long-running MCP servers, IBR with Playwright |
| **Limitations** | Each service uses resources; 4 plugins = 4 services |

**Railway is the best fit for IBR** because Playwright needs a persistent browser environment and Railway supports Docker images with Chromium.

**Cost estimate**: 4 lightweight Node.js services would likely stay within the $5 included credit if usage is moderate. Playwright (IBR) may push above due to memory usage.

#### Vercel

| Aspect | Details |
|--------|---------|
| **Plan** | Pro ($20/mo) |
| **Deployment** | Serverless Functions or Edge Functions |
| **Always-on?** | No — cold starts, 60s timeout (Pro), 15min (Enterprise) |
| **Database** | Vercel Postgres (free: 256MB), Vercel KV (free: 30MB) |
| **Best for** | Stateless API endpoints, lightweight tools |
| **Limitations** | 60s timeout kills IBR scans; cold starts add latency; not ideal for MCP's persistent connections |

**Vercel is problematic for MCP** because:
- MCP Streamable HTTP uses long-lived connections that conflict with serverless timeouts
- IBR's Playwright scans can take >60s
- Cold starts add 1-5s latency to every tool call after idle period

**Vercel works well for**: A REST API wrapper (non-MCP) that Claude calls via Bash/curl, or for hosting a web dashboard.

#### Supabase Edge Functions

| Aspect | Details |
|--------|---------|
| **Plan** | Pro ($25/mo — already paying) |
| **Deployment** | Deno Edge Functions (V8 isolates) |
| **Always-on?** | No — cold starts, but fast (sub-100ms) |
| **Database** | Your existing Postgres — add schemas, no extra cost |
| **Best for** | Bookmark, Debugger, NavGator (lightweight, data-centric) |
| **Limitations** | No Playwright support (Deno runtime); 150s wall time limit; 500K invocations/mo on Pro |
| **No additional DB cost** | Use separate schemas in your existing Supabase project |

**Supabase is the zero-cost option** for 3 of 4 plugins. Add schemas (`bookmark`, `debugger`, `navgator`) to your existing database. Edge Functions handle the API layer. IBR would still need Railway or local execution due to Playwright.

**Schema isolation strategy:**
```sql
CREATE SCHEMA bookmark;
CREATE SCHEMA debugger;
CREATE SCHEMA navgator;
-- Each plugin gets its own namespace in your existing database
```

### Remote Hosting Summary

| Plugin | Railway | Vercel | Supabase Edge | Recommendation |
|--------|---------|--------|---------------|----------------|
| Bookmark | Works | Works (stateless) | Works (best) | Supabase — lightweight, uses existing DB |
| Debugger | Works | Works (stateless) | Works (best) | Supabase — JSONL → Postgres tables, free |
| IBR | **Best** | Timeout issues | No Playwright | Railway — needs browser environment |
| NavGator | Works | Works (stateless) | Works (best) | Supabase — graph data fits Postgres well |

---

## Option 3: Free Database Alternatives

If you want cloud storage without using your existing Supabase database, these providers offer generous free tiers:

### Turso (libSQL/SQLite) — Recommended

| Aspect | Details |
|--------|---------|
| **Free tier** | 9GB storage, 500 databases, 25M row reads/mo, 75 areas |
| **Protocol** | SQLite-compatible (easy migration from file-based JSON) |
| **Edge replication** | Built-in, data close to your users |
| **SDK** | `@libsql/client` for Node.js |
| **Why it fits** | Your plugins store JSON files — Turso's SQLite is the closest migration from file I/O. Create separate databases per plugin at no cost. |

### Neon Postgres

| Aspect | Details |
|--------|---------|
| **Free tier** | 0.5GB storage, 100 compute hours/mo, autoscaling to zero |
| **Protocol** | Full Postgres |
| **Branching** | Git-like database branches (useful for testing) |
| **SDK** | `@neondatabase/serverless` for edge environments |
| **Why it fits** | If you want Postgres without touching your Supabase project. 0.5GB is plenty for all 4 plugins' data. |

### Upstash Redis

| Aspect | Details |
|--------|---------|
| **Free tier** | 10K commands/day, 256MB storage |
| **Protocol** | Redis-compatible, REST API for serverless |
| **Best for** | Fast key-value lookups, caching, session state |
| **Why it fits** | Good for Bookmark (snapshot retrieval) and Debugger (incident search). Not ideal for NavGator's graph data. |

### Cloudflare D1

| Aspect | Details |
|--------|---------|
| **Free tier** | 5GB storage, 25 billion row reads/mo, 50M row writes/mo |
| **Protocol** | SQLite (like Turso) |
| **Limitation** | Only accessible from Cloudflare Workers |
| **Why it fits** | Most generous free tier, but locks you into Cloudflare Workers for compute. |

### Comparison Matrix

| Provider | Storage | Reads | Writes | SQLite-compat | Serverless-friendly | Lock-in |
|----------|---------|-------|--------|---------------|--------------------|---------|
| **Turso** | 9GB | 25M rows/mo | Included | Yes | Yes | Low |
| **Neon** | 0.5GB | Unlimited | Unlimited | No (Postgres) | Yes | Low |
| **Upstash** | 256MB | 10K cmds/day | Included | No (Redis) | Yes | Low |
| **Cloudflare D1** | 5GB | 25B rows/mo | 50M rows/mo | Yes | Workers only | Medium |
| **Supabase (existing)** | Your plan | Your plan | Your plan | No (Postgres) | Edge Functions | Already using |

**Recommendation**: **Turso** if you want a separate free database — SQLite compatibility makes migration from file-based JSON trivial, and 500 free databases means one per plugin with room to spare. **Supabase schemas** if you want zero new services.

---

## Option 4: Hybrid Architecture (Recommended)

### Design

```
┌─────────────────────────────────────────────────┐
│                  Claude Code                     │
│                                                  │
│  Skills ──→ CLI (local)  ──→ File storage        │
│     │                         (.claude/)         │
│     └──→ Remote MCP (HTTP) ──→ Cloud DB          │
│           (Railway/Supabase)   (Turso/Supabase)  │
└─────────────────────────────────────────────────┘
```

**Phase 1 — CLI-first (immediate)**:
- Convert Skills from MCP tool references to CLI `allowed-tools: Bash(...)`
- Remove MCP server dependency for local usage
- All plugins work offline, no server processes

**Phase 2 — Add remote sync (when needed)**:
- Wrap existing core functions in HTTP API (Express/Hono)
- Deploy to Railway (IBR) or Supabase Edge Functions (others)
- Add storage adapter: file I/O → Turso/Supabase Postgres
- Configure Claude Code with HTTP MCP transport for remote access

**Phase 3 — Multi-device (future)**:
- Debugger incidents and NavGator architecture maps sync across machines
- Bookmark snapshots available in Claude Code web sessions
- IBR baselines stored centrally for team comparison

### Why Hybrid Wins

| Concern | CLI-only | Remote-only | Hybrid |
|---------|----------|-------------|--------|
| Works offline | Yes | No | Yes |
| Works in Claude Code web | No | Yes | Yes |
| No server processes | Yes | No | Yes (local mode) |
| Team sharing | No | Yes | Yes (remote mode) |
| Additional cost | $0 | $0-5/mo | $0 (local), $0-5 (remote) |
| Migration effort | Low | High | Low → incremental |

---

## MCP vs CLI: Technical Deep Dive

### How Claude Code Discovers and Calls Tools

**MCP tools** are registered at session start via the MCP protocol:
1. Claude Code spawns MCP server process (stdio) or connects via HTTP
2. Server responds with `tools/list` → Claude sees tool names, descriptions, schemas
3. Claude calls tools directly via JSON-RPC — no Bash, no permission prompts
4. Results are typed (text, images, embedded resources)

**CLI commands** invoked via Bash tool:
1. Claude reads Skill description → learns what commands exist
2. Claude generates Bash command → `npx @tyroneross/bookmark snapshot --json`
3. Bash tool executes → stdout captured as text
4. Claude parses text/JSON output

### Token Cost Comparison

| Approach | Discovery cost | Per-call cost | Output parsing |
|----------|---------------|---------------|----------------|
| MCP (7 tools) | ~350 tokens (tool schemas in context) | 0 (direct call) | Typed, no parsing |
| CLI (7 commands) | ~100 tokens (Skill description) | ~30 tokens (Bash command) | Text parsing needed |

MCP tools consume more context tokens upfront (schemas always loaded), but CLI invocations consume tokens per call. For plugins with <10 tools, the difference is negligible.

### Permission Model

| Approach | Permission behavior |
|----------|-------------------|
| MCP tools | Auto-allowed after MCP server approval at session start |
| CLI via Bash | Requires per-call approval UNLESS `allowed-tools` is set in Skill frontmatter |

With `allowed-tools: Bash(npx @tyroneross/bookmark *)`, CLI calls are auto-approved just like MCP tools.

### Image Handling (IBR-specific)

| Approach | Image flow |
|----------|-----------|
| MCP | Tool returns base64 PNG inline → Claude sees image directly |
| CLI | Command saves PNG to disk → Claude uses Read tool → sees image |

Both work. MCP is one fewer step. CLI requires the Read tool but is equally functional since Claude Code's Read tool handles images natively.

---

## Decision Matrix

Answer these questions to choose your approach:

| Question | If Yes → | If No → |
|----------|----------|---------|
| Do you only use Claude Code locally (terminal)? | CLI-first | Consider remote |
| Do you need plugins in Claude Code web sessions? | Remote hosting needed | CLI-first is fine |
| Do you want team members sharing debug incidents? | Remote DB needed | Local files are fine |
| Is $0 additional cost a hard constraint? | CLI-first + Supabase schemas | Railway for IBR is worth $5/mo |
| Do you want to minimize running processes? | CLI-first | MCP is fine |

---

## Next Steps

### If choosing CLI-first:
1. For each plugin repo, update `skills/*/SKILL.md` to use `allowed-tools: Bash(npx @tyroneross/<plugin> *)`
2. Verify all CLI commands support `--json` output flag
3. For IBR, add missing CLI commands to reach parity with 14 MCP tools
4. Remove `.mcp.json` from plugin packages (or make optional via install flag)
5. Update marketplace README

### If choosing remote hosting:
1. Add HTTP API layer to each plugin (wrap existing core functions)
2. Add storage adapter (file I/O → Turso or Supabase schema)
3. Deploy: IBR → Railway, others → Supabase Edge Functions
4. Configure Claude Code: `claude mcp add --transport http <name> <url>`

### If choosing hybrid:
1. Start with CLI-first (Phase 1)
2. Add remote API when a specific need arises (web sessions, team sharing)
3. Use Turso for free database (SQLite-compatible = easy migration from JSON files)
