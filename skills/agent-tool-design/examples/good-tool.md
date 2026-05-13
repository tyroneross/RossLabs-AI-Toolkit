# Good Tool — Worked Example

A well-designed Linear issue-creation tool. Both Anthropic and OpenAI wire formats shown.

## OpenAI Agents SDK

```python
from pydantic import BaseModel, Field
from openai.agents import function_tool
from typing import Literal, Optional

class CreateLinearIssueInput(BaseModel):
    title: str = Field(..., max_length=120, description="Issue headline")
    team_id: str = Field(..., description="UUID from linear_team_search")
    description: Optional[str] = Field(None, description="Markdown body")
    assignee_id: Optional[str] = Field(None, description="UUID from linear_user_search; defaults to unassigned")
    priority: Literal[0, 1, 2, 3, 4] = Field(0, description="0=none, 1=urgent, 2=high, 3=medium, 4=low")
    labels: list[str] = Field(default_factory=list, description="Array of UUIDs from linear_label_search")
    response_format: Literal["CONCISE", "DETAILED"] = Field("CONCISE", description="CONCISE returns id+url+identifier only; DETAILED returns full issue object")

@function_tool
async def linear_issue_create(input: CreateLinearIssueInput) -> dict:
    """Create a new issue in Linear.

    Required:
    - title (string, ≤120 chars): the headline of the issue.
    - team_id (UUID from linear_team_search): which team owns this issue.

    Optional:
    - description (markdown string): body of the issue.
    - assignee_id (UUID from linear_user_search): defaults to unassigned.
    - priority (0..4): 0=none, 1=urgent, 2=high, 3=medium, 4=low.
    - labels (array of UUID from linear_label_search): defaults to empty.
    - response_format ("CONCISE" | "DETAILED"): defaults to "CONCISE".

    Returns on success: { id, identifier (e.g. "ENG-123"), url, created_at } in CONCISE mode;
    full issue object in DETAILED mode.

    Use when the user asks to file a bug, create a task, or open a ticket.
    Do not use to update an existing issue (use linear_issue_update).
    Do not use to create a project (use linear_project_create).
    """
    try:
        result = await linear_client.create_issue(...)
    except LinearValidationError as e:
        # Pattern 1 — validation error
        raise ToolError(
            f"Validation failed: field `{e.field}` must be {e.expected_type}, received {e.got_type}. "
            f"Use linear_{e.expected_type}_search to obtain a {e.expected_type}."
        )
    except LinearNotFoundError as e:
        raise ToolError(
            f"{e.resource_kind} `{e.identifier}` not found. "
            f"Search by alternate identifiers with linear_{e.resource_kind}_search."
        )
    if input.response_format == "DETAILED":
        return result
    return {"id": result["id"], "identifier": result["identifier"], "url": result["url"], "created_at": result["created_at"]}
```

## Anthropic tool_use

```ts
const linearIssueCreate = {
  name: "linear_issue_create",
  description: "Create a new issue in Linear. Required: title (string, ≤120 chars), team_id (UUID from linear_team_search). Optional: description (markdown), assignee_id (UUID from linear_user_search), priority (0=none, 1=urgent, 2=high, 3=medium, 4=low), labels (array of UUID from linear_label_search), response_format (\"CONCISE\" | \"DETAILED\", default \"CONCISE\"). Returns on success: { id, identifier, url, created_at } in CONCISE; full issue object in DETAILED. Use when the user asks to file a bug, create a task, or open a ticket. Do not use to update an existing issue (use linear_issue_update) or to create a project (use linear_project_create).",
  input_schema: {
    type: "object",
    properties: {
      title: { type: "string", maxLength: 120 },
      team_id: { type: "string", description: "UUID from linear_team_search" },
      description: { type: "string", description: "Markdown body" },
      assignee_id: { type: "string", description: "UUID from linear_user_search" },
      priority: { type: "integer", enum: [0, 1, 2, 3, 4] },
      labels: { type: "array", items: { type: "string" } },
      response_format: { type: "string", enum: ["CONCISE", "DETAILED"], default: "CONCISE" }
    },
    required: ["title", "team_id"]
  }
};
```

## What makes this good (checklist)

- [x] Name is `service_resource_verb`.
- [x] Parameters are typed by what they are (`team_id`, `assignee_id`), with source pointers (`from linear_team_search`).
- [x] Description includes summary, every field with type+source, return shape, when-to-use, when-NOT-to-use.
- [x] Errors are prompt-engineered with field name + recovery tool.
- [x] `response_format` knob lets the model pick depth.
- [x] CONCISE default — context-cheap.
- [x] Enum (`priority`) preferred over multiple booleans.
- [x] Mutation-only (no read shortcut).
