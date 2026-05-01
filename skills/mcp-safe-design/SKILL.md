---
name: mcp-safe-design
description: Apply the Secrets Vault contract to any MCP server you build, edit, or review. The contract is metadata-only — tools return references and IDs, never secret values, bearer tokens, or internal state. Activates when working on `mcp__*` tools, `.mcp.json`, or any MCP server source file (`server.py`, `server.ts`, `*.mcp.*`).
trigger: User mentions building/editing/auditing an MCP server, the file path matches `**/server.{py,ts,js}` inside an MCP context, the user is editing `.mcp.json`, or the user names a tool prefixed `mcp__`.
---

# mcp-safe-design

Reusable safety contract for MCP servers, distilled from `~/dev/git-folder/secrets-vault/src/mcp/server.ts`. The vault is the reference because it has the strongest threat model in this user's stack: it holds encrypted secrets, exposes them to local agents, and ships as a Mac app. Its discipline transfers wherever an MCP tool sits between an LLM and any privileged data path.

## Why this exists

LLMs see whatever lands in tool responses. Anything an MCP tool returns is now in the model's context — and from there, into chat logs, transcripts, and any downstream tool. A leak is not a UI bug; it is a permanent data egress. The five rules below are the cheapest way to prevent that class of leak.

## The contract — five rules

Apply each rule to every MCP tool. Failing any one is a flag.

### Rule 1 — Tools return refs, not values

A tool MUST return identifiers, names, status flags, or counts. It MUST NOT return the underlying value when that value is sensitive (a secret, a bearer token, a private file's contents, a cookie, an API response containing PII).

**Reference pattern (secrets-vault):**
```ts
// list_secrets returns names + categories + projects + expiration metadata.
// secret_info returns category, projects, expiration, notes.
// Neither returns the actual secret value.
// inject_secret writes the value directly to a .env file on disk —
// the value never appears in the JSON-RPC response.
```

If the legitimate use case is "agent needs the value to do its job" (e.g. inject into a config file), do the privileged action server-side and return only the artifact reference (file path, success flag, redacted preview).

### Rule 2 — Bearer tokens and credentials stay server-side

If the MCP tool authenticates against an upstream service (HTTP API, cloud SDK, database), the token must:
- Live in a process variable, environment variable, or a file the server reads — never in tool arguments and never in tool responses.
- Be sent only on the upstream request, never echoed back.

**Reference pattern (secrets-vault):**
```ts
const token = getSessionToken();          // reads from ~/.secrets-vault/session
if (token) headers["Authorization"] = `Bearer ${token}`;
// the response that ships back to the LLM has no Authorization header in it
```

Anti-pattern: writing the token into a debug field, logging it on a failed request, or echoing the upstream response verbatim when the upstream service includes the token in its body.

### Rule 3 — Audit-log entries are token-free

If the server keeps an audit log (and it should, for any tool that can mutate state or read sensitive data), each log entry must record what happened, by whom, and when — not the secret material involved.

Log: `event: secret_injected`, `secret_id: abc-123`, `project_id: def-456`, `actor: cli`, `ts: ...`.

Don't log: the secret value, the bearer token used to authenticate, the full HTTP response body from the upstream, or any decoded JWT payload that may contain identity claims.

### Rule 4 — Errors don't leak internal state

Error responses must be useful to the LLM (so it can recover or surface a human-readable message) without leaking internal facts that help an attacker.

**Avoid in an error string:**
- Absolute file paths inside the project (`Failed to read /Users/<name>/.private_keys/AuthKey_NTNAA84KU6.p8`).
- Stack traces with line numbers from third-party packages.
- Environment variable names paired with their suspected values.
- Database schema fragments (`column "users.password_hash" does not exist`).

**Reference pattern (secrets-vault):**
```ts
if (!res.ok) {
  throw new Error((data as { error?: string }).error || `HTTP ${res.status}`);
}
// errorResponse(text) returns { content: [{type:"text", text}], isError: true }
// — short, action-oriented, no internals
```

Sanitize the upstream error before re-throwing. Map common HTTP/database errors to flat strings: `"vault is locked"`, `"secret not found"`, `"network timeout"`.

### Rule 5 — Tool descriptions don't over-promise

The `description` field in the tool schema is what the LLM uses to decide whether to call the tool. If the description claims a capability the implementation doesn't enforce, the LLM will trust the description and pick a behavior the server can't actually defend.

**Pass:** `"Returns names, categories, projects, and expiration status. Never returns actual secret values."` — and the implementation, when audited, in fact never returns values.

**Flag:** `"Securely retrieves your secrets"` — vague, unenforced, and "securely" promises something the schema can't verify. Either describe the metadata-only contract concretely or drop the safety claim.

## How to apply — checklist before shipping a tool

For each tool in `TOOLS` / `@mcp.tool()` declarations, walk the list:

```
[ ] Rule 1 — does the return value contain only refs/IDs/metadata?
[ ] Rule 2 — is no bearer token, API key, or session secret in the response body?
[ ] Rule 3 — does any audit/log call exclude the secret payload?
[ ] Rule 4 — would the error path on this tool surface internal paths or stack frames?
[ ] Rule 5 — does the description promise no capability the code doesn't enforce?
```

When auditing an existing server, run the checklist tool-by-tool and produce a flag list with file:line citations. Don't try to fix during the audit — flag first, then plan the change.

## Adversarial fixture for testing

A bad MCP looks like this (deliberate fixture — never ship):

```python
@mcp.tool()
def get_api_key(name: str) -> str:
    """Get an API key by name."""
    return read_from_vault(name)   # FLAG Rule 1 — value in response
```

Or this:
```python
@mcp.tool()
def call_upstream(query: str) -> dict:
    """Call internal service."""
    headers = {"Authorization": f"Bearer {os.environ['INTERNAL_TOKEN']}"}
    r = requests.get(f"{INTERNAL}/q?q={query}", headers=headers)
    return {"status": r.status_code, "headers": dict(r.headers), "body": r.text}
    # FLAG Rule 2 — `headers` echoes Authorization back; `body` may contain PII
```

Or this:
```python
@mcp.tool()
def search_users(q: str) -> str:
    """Securely search users."""        # FLAG Rule 5 — vague safety claim
    try:
        return db.query(q)               # FLAG Rule 4 if this raises with SQL state
    except Exception as e:
        return f"DB error at {DB_PATH}: {e}"  # FLAG Rule 4 — leaks path + message
```

## Reversibility

This is a documentation-only skill. Removing it means future MCP work loses the checklist; existing MCP servers are unaffected. Edits triggered by applying the checklist to existing servers are independent reversible commits in those servers' repos.
