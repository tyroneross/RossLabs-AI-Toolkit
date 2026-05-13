# Bad Tool — Anti-Pattern Walkthrough

The same Linear-issue tool, badly designed. Read it and find the violations before reading the annotations below.

## Bad version

```ts
const createIssue = {                              // ① no service namespace
  name: "createIssue",                             // ① camelCase, no service prefix
  description: "Create an issue.",                 // ② one sentence, no fields
  input_schema: {
    type: "object",
    properties: {
      title: { type: "string" },                   // ③ no length limit
      team: { type: "string" },                    // ④ "team" — id? slug? name?
      user: { type: "string" },                    // ④ "user" — id? email? name?
      details: { type: "object" },                 // ⑤ freeform object
      urgent: { type: "boolean" },                 // ⑥ boolean field where enum reads better
      important: { type: "boolean" },              // ⑥ another boolean — semantically overlapping
      tags: { type: "array", items: { type: "string" } }  // ⑦ "tags" — names? UUIDs? slugs?
    },
    required: ["title"]                            // ⑧ team should be required
  }
};

// And the error handling:
try {
  return await linear.createIssue(...);
} catch (e) {
  throw new Error("Failed to create issue");      // ⑨ unhelpful error
}
```

## Annotations

**① Naming**: `createIssue` collides with `createIssue` from GitHub, Jira, Asana, and every other ticketing MCP server in the agent's tool list. The model has to disambiguate by description on every call. Fix: `linear_issue_create`.

**② Description**: tells the model nothing. The model has to guess at every field, what the team identifier is, what the return shape is, when to use this vs other tools. Fix: full template from `blocks/description-template.md`.

**③ No length limit on title**: the agent might pass a 5000-char "title" that's actually a description. Add `maxLength: 120`.

**④ Generic parameter names**: `team` could be a UUID, a slug ("eng"), or a display name ("Engineering"). `user` could be an email, a username, or an ID. The agent will pick one (often wrong) and waste calls. Fix: `team_id`, `assignee_id`, with `description: "UUID from linear_team_search"`.

**⑤ Freeform `details` object**: the agent will fill it with reasonable-looking but wrong JSON. There's no schema to validate against. Either flatten to typed fields (`description`, `notes`) or omit.

**⑥ Boolean field where enum reads better**: `urgent: true` and `important: true` could both be set, with no defined meaning. Use a single `priority` enum (`0..4`) with documented values.

**⑦ `tags` array**: are these label names? UUIDs? Slugs? The model can't tell. Rename to `label_ids` with description `"Array of UUID from linear_label_search"`.

**⑧ Missing required field**: `team_id` should be required — issues need a team. Marking only `title` required invites a flood of calls without team context.

**⑨ Unhelpful error**: `"Failed to create issue"` — why? The agent retries with the same broken inputs. Use the validation-error pattern from `blocks/error-string-templates.md`.

## What this tool actually does in production

- Agent loops 3–5× on `team` resolution before finding the right shape.
- Half the issues end up in the wrong team because the model guessed at the team identifier.
- Errors trigger context-burning retries with no path to recovery.
- The `details` field gets filled with hallucinated metadata.
- p50 latency 4× higher than the good version because of all the retry traffic.

## The same problems with OpenAI function-calling

The wire format differs but the failure modes are identical. Bad naming, generic params, freeform JSON, and opaque errors break agents on both vendors the same way.
