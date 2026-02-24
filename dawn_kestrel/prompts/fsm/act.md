# ACT Phase Prompt

## GOAL

Execute a SINGLE tool call to make progress on the current todo. This phase performs one discrete action per iteration, then routes to SYNTHESIZE for result processing.

## INPUT

| Variable | Type | Description |
|----------|------|-------------|
| `{current_todo_id}` | string | ID of the todo being worked on |
| `{description}` | string | Description of the current todo |
| `{priority}` | string | Priority level: high, medium, or low |
| `{notes}` | string | Additional context/notes for the todo |
| `{schema}` | string | Dynamic JSON schema from `get_act_output_schema()` |

## OUTPUT

The LLM must return valid JSON matching the `ActOutput` schema:

```json
{
  "action": {
    "tool_name": "string (required) - Name of tool to call",
    "arguments": "object (optional) - Arguments to pass to tool",
    "status": "string (required) - One of: success, failure, timeout",
    "result_summary": "string (optional) - Summary of what happened",
    "duration_seconds": "number (optional) - How long the action took",
    "artifacts": ["string (optional) - Files/resources produced"]
  },
  "acted_todo_id": "string (optional) - ID of todo acted upon",
  "tool_result_summary": "string (optional) - Human-readable result",
  "artifacts": ["string (optional) - List of artifacts produced"],
  "failure": "string (optional) - Error message if failed"
}
```

## VALIDATION

- **Required Fields**: None (all optional with defaults)
- **Action Status**: Must be one of `success`, `failure`, `timeout`
- **Schema**: `ActOutput` Pydantic model with `extra="ignore"`
- **Special Case**: If no current todo, skips to SYNTHESIZE with empty `ActOutput()`

## CONSTRAINTS

- **SINGLE ACTION CONSTRAINT**: Must perform exactly ONE tool call per iteration
- Tool calls increment `budget_consumed.tool_calls`
- Successful actions add evidence to context
- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema

---

## Prompt Template

```
You are in the ACT phase of a workflow loop.

SINGLE ACTION CONSTRAINT: Perform exactly ONE tool call this iteration.

Current todo:
- ID: {current_todo_id}
- Description: {description}
- Priority: {priority}
- Notes: {notes}

{schema}

Respond with ONLY valid JSON matching the schema above.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

current_task = context.todos[context.current_todo_id]
prompt = load_prompt("fsm/act").format(
    current_todo_id=context.current_todo_id,
    description=current_task.description,
    priority=current_task.metadata.get("priority", "medium"),
    notes=current_task.metadata.get("notes", ""),
    schema=get_act_output_schema()
)
```
