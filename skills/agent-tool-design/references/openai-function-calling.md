# OpenAI Function Calling — Wire Format Notes

Vendor-specific notes that complement the cross-vendor rules in SKILL.md. Source: [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling) and [Agents SDK docs](https://openai.github.io/openai-agents-python/tools/) (T1, current as of 2026).

## Function definition shape

```json
{
  "type": "function",
  "function": {
    "name": "snake_case_name",
    "description": "Full description per blocks/description-template.md",
    "parameters": {
      "type": "object",
      "properties": { /* ... */ },
      "required": [ /* ... */ ],
      "additionalProperties": false
    },
    "strict": true
  }
}
```

- **`strict: true`** is the killer feature: the model is guaranteed to emit JSON that matches the schema, or surface a `refusal`. Without strict, model can drift.
- Strict mode requires:
  - `additionalProperties: false` on every nested object.
  - Every property in `required` (you can't have optional fields under strict — use union with `null` instead, e.g. `{"type": ["string", "null"]}`).
- Anthropic doesn't have an equivalent flag; the JSON-Schema adherence is implicit.

## Calling the model

```python
response = client.responses.create(
    model="gpt-5",
    input=messages,
    tools=tools,
    tool_choice="auto",           # or "required" or {"type":"function","function":{"name":"..."}}
    parallel_tool_calls=True,     # default true on modern models
)
```

## Response shape

```json
{
  "output": [
    {
      "type": "function_call",
      "id": "call_abc123",
      "call_id": "call_abc123",
      "name": "linear_issue_create",
      "arguments": "{\"title\":\"...\",\"team_id\":\"...\"}"
    }
  ]
}
```

- `arguments` is a JSON-encoded string, not an object — parse it.
- `call_id` is the correlation key.

## Returning a result

```python
messages.append({
    "type": "function_call_output",
    "call_id": "call_abc123",
    "output": json.dumps({"id": "iss_xyz", "url": "..."}),
})
```

- `output` is a string; use JSON if your tool returns structured data.

## Parallel tool calls

- Set `parallel_tool_calls=True` (default on gpt-5+).
- Model emits multiple `function_call` items in one response; return all `function_call_output` items in the next turn.
- For deterministic ordering, return them in the order they were emitted.

## Strict mode — gotchas

- Recursive schemas need an explicit `$ref` to a sibling definition; inline recursion isn't supported under strict.
- Anything beyond JSON Schema's strict subset rejects at registration time (good — fail fast).
- `enum` works; `format` (e.g. `"date-time"`) is hint-only — validate yourself.
- Refusals come back as a `refusal` field on the message, not as a thrown error. Handle them explicitly.

## Agents SDK convenience

If you're on the [Agents SDK](https://openai.github.io/openai-agents-python/):

```python
from openai.agents import function_tool
from pydantic import BaseModel

class CreateIssueInput(BaseModel):
    title: str
    team_id: str

@function_tool
async def linear_issue_create(input: CreateIssueInput) -> dict:
    """Create a new issue in Linear. [full description here]"""
    ...
```

- Pydantic model becomes the JSON Schema automatically.
- `strict=True` is the default.
- Docstring becomes the `description`.
- Errors raised inside the tool become prompt-engineered error messages if you raise `ToolError("...")`.

## Reasoning models (o-series, gpt-5 with reasoning_effort)

- Tools work the same on the wire.
- DO NOT instruct the model to "think step by step" before calling a tool — the model already reasons. Use `reasoning_effort` instead.
- See `reasoning-model-prompting` skill for the broader rules.

## What's different from Anthropic

| Topic | OpenAI | Anthropic |
|---|---|---|
| Strict mode | `strict: true` + `additionalProperties: false` | No flag |
| Arguments encoding | JSON string in `arguments` | Parsed object in `input` |
| Refusal handling | `refusal` field on the message | Returns plain `text` block with refusal text |
| Cache control | Automatic prefix hash | Explicit `cache_control` breakpoint |
| Optional fields under strict | Not allowed; use `null` union | Allowed via not-in-`required` |
