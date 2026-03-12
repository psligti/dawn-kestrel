# ACT Phase Prompt

## GOAL

Execute a SINGLE tool call to make progress on the current todo. This phase performs one discrete action per iteration, then routes to SYNTHESIZE for result processing.

## INPUT

| Variable | Type | Description |
|----------|------|------------|
| `{intent}` | string | Original user intent from INTAKE phase |
| `{atomic_step}` | string | Tool-agnostic atomic step from REASON phase |
| `{why_now}` | string | Justification for this action from REASON phase |
| `{constraints}` | string | Constraints identified (multiline) |
| `{allowed_tools}` | string | Comma-separated list of allowed tools |
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
    "selection_reason": "string (required) - Justification for this tool choice (must reference intent + atomic_step)",
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

- **Required Fields**: `action.selection_reason` (if action is present)
- **Action Status**: Must be one of `success`, `failure`, `timeout`
- **Schema**: `ActOutput` Pydantic model with `extra="forbid"`
- **Special Case**: If no current todo, skips to SYNTHESIZE with empty `ActOutput()`

## CONSTRAINTS

- **SINGLE ACTION CONSTRAINT**: Must perform exactly ONE tool call per iteration
- **SELECTION REASON REQUIRED**: `action.selection_reason` must explicitly reference intent + atomic_step
- Tool calls increment `budget_consumed.tool_calls`
- Successful actions add evidence to context
- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema
- Do NOT put justification in `action.arguments` - use `action.selection_reason`

---

## Prompt Template

```
You are in the ACT phase of a workflow loop.

SINGLE ACTION CONSTRAINT: Perform exactly ONE tool call this iteration.

CRITICAL: Your action.selection_reason MUST explicitly reference:
1. The original intent
2. The atomic_step from REASON phase

Context from previous phases:

Original intent: {intent}

Reason atomic step: {atomic_step}

Why now: {why_now}

Constraints: {constraints}

Allowed tools: {allowed_tools}

Current todo:
- ID: {current_todo_id}
- Description: {description}
- Priority: {priority}
- Notes: {notes}

{schema}

Respond with ONLY valid JSON matching the schema above.
Your action.selection_reason must explain how this tool choice serves the intent and atomic_step.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

# Context from previous phases
reason_output = context.last_reason_output
intake_output = context.intake_output

current_task = context.todos[context.current_todo_id]

prompt = load_prompt("fsm/act").format(
    # Context from previous phases
    intent=intake_output.intent,
    atomic_step=reason_output.atomic_step,
    why_now=reason_output.why_now,
    constraints="\n".join(intake_output.constraints),
    allowed_tools=", ".join(context.allowed_tools),
    # Current todo
    current_todo_id=context.current_todo_id,
    description=current_task.description,
    priority=current_task.metadata.get("priority", "medium"),
    notes=current_task.metadata.get("notes", ""),
    schema=get_act_output_schema()
)
```
