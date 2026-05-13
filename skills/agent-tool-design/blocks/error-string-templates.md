# Error String Templates (paste-in)

Error strings are read by the model and used to plan the next call. Optimize them as prompts.

---

## Pattern 1 — validation error

```
Validation failed: field `{field_name}` must be {expected_type}, received {got_type}.
{recovery_hint: e.g. "Use <tool>_search to obtain a {expected_type}."}
```

Example:
```
Validation failed: field `user_id` must be a UUID, received an email string.
Use aida_user_search with the email to obtain the UUID.
```

## Pattern 2 — not-found error

```
{resource_kind} `{identifier}` not found.
{recovery_hint: e.g. "Search by alternate identifiers with <tool>_search."}
{adjacent_resource_hint: "Note: this id may belong to a {other_resource_kind} — try <other_tool> if so."}
```

Example:
```
Issue `iss_abc123` not found.
Search by title or label with linear_issue_search.
Note: this id may belong to a project — try linear_project_get if so.
```

## Pattern 3 — permission error

```
Permission denied on {action} for {resource_kind} `{identifier}`.
{recovery_hint: e.g. "Your API token does not have {scope} scope. Tools requiring {scope}: <list>."}
```

## Pattern 4 — rate-limit error

```
Rate limit exceeded for {service}. Retry after {retry_after_seconds} seconds.
{batching_hint: e.g. "Use <bulk_tool> to fetch multiple {resource_kind} in one call."}
```

## Pattern 5 — schema mismatch (agent passed wrong shape)

```
Schema mismatch: expected {schema_summary}, received {received_summary}.
Common cause: {common_cause, e.g. "passing a slug where a UUID is required"}.
{recovery_hint: "Use <tool>_search to convert {received_kind} to {expected_kind}."}
```

## Anti-patterns

- ❌ `"Error: 400 Bad Request"` — gives the model nothing.
- ❌ `"Internal server error"` — model will retry the same broken call.
- ❌ `"Invalid input"` — which field? what was wrong?
- ❌ Stack traces — burns context, gives the model nothing actionable.

## Rule of thumb

Read the error as if you're the agent. If you can't tell from the error what to change for the next attempt, the error is broken. Fix it.
