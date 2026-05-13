# Description Template (paste-in)

A description field IS the tool's documentation to the model. Pad it; the model reads it on every call.

---

## Template

```
{one-sentence summary of what the tool does}.

Required: {field1} ({type}, {how to obtain it — e.g. "UUID from <other_tool>_search"}), {field2} ({type}).
Optional: {field3} ({type}, {default}), {field4} ({type}, {default}).

Returns on success: {return shape — list the keys the model can use downstream}.

Use when {the agent's intent}. Do not use when {adjacent intent} — use {other_tool} for that.
```

## Worked example

```text
Create a new issue in Linear.

Required:
- title (string, ≤120 chars): the headline of the issue.
- team_id (UUID from linear_team_search): which team owns this issue.

Optional:
- description (markdown string): body of the issue.
- assignee_id (UUID from linear_user_search): defaults to unassigned.
- priority (enum 0..4): 0=none (default), 1=urgent, 2=high, 3=medium, 4=low.
- labels (array of UUID from linear_label_search): defaults to empty.

Returns on success: { id, identifier (e.g. "ENG-123"), url, created_at }.

Use when the user asks to file a bug, create a task, or open a ticket. Do not use to update an existing issue (use linear_issue_update) or to create a project (use linear_project_create).
```

## Checklist

For every tool description, confirm:
- [ ] One-sentence summary at the top, ≤25 words.
- [ ] Every required field, with type and source.
- [ ] Every optional field, with type and default.
- [ ] Return shape — keys the model will read downstream.
- [ ] At least one "use when".
- [ ] At least one "do not use when, use X instead."

A description failing more than one check will surface as agent loops or wrong tool selection in evals.
