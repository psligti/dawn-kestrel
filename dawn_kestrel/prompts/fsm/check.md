# CHECK Phase Prompt

## GOAL

Evaluate if the current todo is complete and decide where to route next. This phase determines the workflow loop continuation: continue acting, pick a new todo, or finish.

## INPUT

| Variable | Type | Description |
|----------|------|-------------|
| `{current_todo_id}` | string | ID of the todo being evaluated |
| `{description}` | string | Description of the current todo |
| `{status}` | string | Current status of the todo |
| `{total_todos}` | integer | Total number of todos |
| `{pending_count}` | integer | Number of pending/running todos |
| `{last_action}` | string | Formatted summary of recent tool result |
| `{iterations_consumed}` | integer | Iterations used so far |
| `{iterations_max}` | integer | Maximum allowed iterations |
| `{tool_calls_consumed}` | integer | Tool calls used so far |
| `{tool_calls_max}` | integer | Maximum allowed tool calls |
| `{wall_time_consumed}` | float | Wall time used in seconds |
| `{wall_time_max}` | float | Maximum allowed wall time in seconds |
| `{stagnation_count}` | integer | Current stagnation count |
| `{stagnation_threshold}` | integer | Stagnation threshold limit |
| `{schema}` | string | Dynamic JSON schema from `get_check_output_schema()` |

## OUTPUT

The LLM must return valid JSON matching the `CheckOutput` schema:

```json
{
  "current_todo_id": "string (optional) - ID of todo being evaluated",
  "todo_complete": "boolean (optional) - Whether todo is done",
  "next_phase": "string (optional) - One of: act, plan, done",
  "confidence": "number (optional) - 0.0 to 1.0",
  "budget_consumed": {
    "iterations": "integer (optional)",
    "subagent_calls": "integer (optional)",
    "wall_time_seconds": "number (optional)",
    "tool_calls": "integer (optional)",
    "tokens_consumed": "integer (optional)"
  },
  "blocking_question": "string (optional) - Question blocking progress",
  "novelty_detected": "boolean (optional) - Is this a new type of result?",
  "stagnation_detected": "boolean (optional) - Is progress stalled?",
  "reasoning": "string (optional) - Why this decision was made"
}
```

## VALIDATION

- **Required Fields**: None (all optional with defaults)
- **Valid next_phase**: `act`, `plan`, `done`
- **Confidence Range**: 0.0 to 1.0
- **Schema**: `CheckOutput` Pydantic model with `extra="ignore"`

## CONSTRAINTS

### Hard Budget Enforcement

The FSM can **override** the LLM's decision via `_enforce_hard_budgets()`:

| Condition | Override |
|-----------|----------|
| `max_iterations` exceeded | Force `next_phase="done"` |
| `max_tool_calls` exceeded | Force `next_phase="done"` |
| `max_wall_time_seconds` exceeded | Force `next_phase="done"` |
| `stagnation_threshold` exceeded | Force `next_phase="plan"` |
| `blocking_question` present | Force `next_phase="done"` |
| Risk threshold exceeded | Force `next_phase="done"` |

### Routing Logic

- `act`: Continue working on current todo (`todo_complete=false`)
- `plan`: Todo complete, pick next todo (`todo_complete=true`, more todos pending)
- `done`: All todos complete (`todo_complete=true`, no more todos)

### Other Constraints

- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema
- Wall time is calculated at phase start

---

## Prompt Template

```
You are in the CHECK phase of a workflow loop.

Your task:
1. Evaluate if the current todo is complete
2. Decide where to route next:
   - "act": Continue working on current todo (todo_complete=false)
   - "plan": Todo complete, pick next todo (todo_complete=true, more todos pending)
   - "done": All todos complete (todo_complete=true, no more todos)

Current todo:
- ID: {current_todo_id}
- Description: {description}
- Status: {status}

Todo summary:
- Total todos: {total_todos}
- Pending/Running: {pending_count}

Recent tool result:
{last_action}

Budget consumed:
- Iterations: {iterations_consumed}/{iterations_max}
- Tool calls: {tool_calls_consumed}/{tool_calls_max}
- Wall time: {wall_time_consumed:.1f}/{wall_time_max}s

Stagnation: {stagnation_count}/{stagnation_threshold}

{schema}

Respond with ONLY valid JSON matching the schema above.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

current_task = context.todos[context.current_todo_id]
pending_count = sum(
    1 for t in context.todos.values()
    if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
)

prompt = load_prompt("fsm/check").format(
    current_todo_id=context.current_todo_id,
    description=current_task.description,
    status=current_task.status.value,
    total_todos=len(context.todos),
    pending_count=pending_count,
    last_action=workflow._format_last_action(),
    iterations_consumed=context.budget_consumed.iterations,
    iterations_max=config.budget.max_iterations,
    tool_calls_consumed=context.budget_consumed.tool_calls,
    tool_calls_max=config.budget.max_tool_calls,
    wall_time_consumed=context.budget_consumed.wall_time_seconds,
    wall_time_max=config.budget.max_wall_time_seconds,
    stagnation_count=context.stagnation_count,
    stagnation_threshold=config.stagnation_threshold,
    schema=get_check_output_schema()
)
```
