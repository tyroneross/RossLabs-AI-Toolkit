# Naming Rule (paste-in)

Use this section verbatim in a tool-design review checklist.

---

## Tool names — `service_resource_verb`

- Snake case throughout.
- Three segments: which service, which resource, which verb.
- Use the singular resource (`pull_request`, not `pull_requests`), even when the verb is list-like.
- For list/search/query: prefer `<resource>_search` with parameters, not five separate `list_*` tools.

Examples:
- `github_pull_request_create` ✅
- `linear_issue_search` ✅
- `aida_recommendation_get` ✅
- `aida_recommendation_create` ✅
- `create_pr` ❌ (no service prefix, no resource)
- `getRecommendation` ❌ (camelCase, no namespace)
- `do_action` ❌ (generic; reserve no verb names like `do`, `run`, `process`)

## Parameter names — by type, not by alias

- `user_id` (UUID, expected from `<service>_user_search`) > `user`
- `repository_full_name` (`owner/repo`) > `repo`
- `query_text` > `q`
- `iso_8601_timestamp` > `time`
- `markdown_body` > `body` (when other fields could also be "body")
- `cursor` (opaque pagination cursor) > `page` (numeric pagination is fragile across reorders)

## Enum values

- Use lowercase, hyphen-separated, semantically clear: `"soft-delete"`, `"hard-delete"` not `"sd"`, `"hd"`.
- Avoid boolean fields when an enum reads better. `mode: "soft" | "hard"` > `hard: true`.

## What this rule prevents

- Name collisions between tools from different MCP servers loaded into the same agent.
- The agent guessing at parameter types and passing the wrong shape.
- The agent calling a similarly-named adjacent tool because both sounded right.
