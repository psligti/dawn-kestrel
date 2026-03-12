# PLAN Phase Prompt

> **DEPRECATED**: This prompt is maintained for backward compatibility.
> For new implementations, use `fsm/reason` which provides a more structured
> ReAct pattern with explicit Thought/Action outputs.
>
> Migration: `load_prompt("fsm/plan")` → `load_prompt("fsm/reason")`

## GOAL

Review current context and existing todos, generate new todos or modify existing ones, and prioritize work for the ACT phase. The system will work on ONE todo at a time.

## INPUT

| Variable | Type | Description |
|----------|------|-------------|
| `{context_summary}` | string | Multi-line summary of workflow state (intent, constraints, todos, evidence) |
| `{schema}` | string | Dynamic JSON schema from `get_plan_output_schema()` |

### Context Summary Contents

The `context_summary` is built dynamically by `_build_context_summary()` and includes:
- Intent from INTAKE phase
- Constraints identified
- Initial evidence count
- Iterations count
- Todos count with status/priority
- Current todo details (if any)
- Evidence count
- Findings count

## OUTPUT

The LLM must return valid JSON matching the `PlanOutput` schema:

```json
{
  "todos": [
    {
      "id": "string (required) - Unique todo identifier",
      "operation": "string (required) - One of: create, modify, prioritize, skip",
      "description": "string (required) - What this todo accomplishes",
      "priority": "string (optional) - One of: high, medium, low",
      "status": "string (optional) - One of: pending, in_progress, completed, skipped, blocked",
      "dependencies": ["string (optional) - List of todo IDs this depends on"],
      "notes": "string (optional) - Additional context"
    }
  ],
  "reasoning": "string (optional) - Why these todos were chosen",
  "estimated_iterations": "integer (optional) - Expected iterations to complete",
  "strategy_selected": "string (optional) - High-level strategy name"
}
```

## VALIDATION

- **Required Fields**: `todos` (list of TodoItem)
- **TodoItem Required**: `id`, `operation`, `description`
- **Valid Operations**: `create`, `modify`, `prioritize`, `skip`
- **Valid Priorities**: `high`, `medium`, `low`
- **Valid Statuses**: `pending`, `in_progress`, `completed`, `skipped`, `blocked`
- **Schema**: `PlanOutput` Pydantic model with `extra="forbid"`

## CONSTRAINTS

- System enforces ONE todo at a time in ACT phase
- Priority determines todo selection order (high > medium > low)
- In-progress todos are resumed before pending todos
- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema

---

## Prompt Template

```
You are in the PLAN phase of a workflow loop.

Your task:
1. Review current context and existing todos
2. Generate new todos or modify existing ones
3. Prioritize todos (high, medium, low)
4. The system will work on ONE todo at a time

Current workflow context:
{context_summary}

{schema}

Respond with ONLY valid JSON matching the schema above.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

prompt = load_prompt("fsm/plan").format(
    context_summary=workflow._build_context_summary(),
    schema=get_plan_output_schema()
)
```
