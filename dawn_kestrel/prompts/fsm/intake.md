# INTAKE Phase Prompt

## GOAL

Extract the user's intent, identify constraints, and capture initial evidence from the context. This is the first phase of the workflow loop that establishes what the user wants to accomplish and what limitations exist.

## INPUT

| Variable | Type | Description |
|----------|------|-------------|
| `{user_message}` | string | The user's request or task description |
| `{schema}` | string | Dynamic JSON schema from `get_intake_output_schema()` |

## OUTPUT

The LLM must return valid JSON matching the `IntakeOutput` schema:

```json
{
  "intent": "string (required) - The user's intent/goal",
  "constraints": ["string (optional) - List of constraints identified"],
  "initial_evidence": ["string (optional) - List of initial evidence captured"]
}
```

## VALIDATION

- **Required Fields**: `intent` (string)
- **Optional Fields**: `constraints` (list), `initial_evidence` (list)
- **Schema**: `IntakeOutput` Pydantic model with `extra="forbid"`
- **Error Handling**: `ValidationError` on missing required fields

## CONSTRAINTS

- LLM cannot override missing required fields - validation will fail
- Default message "No user message provided" is used if `user_message` is missing
- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema

---

## Prompt Template

```
You are in the INTAKE phase of a workflow loop.

Your task:
1. Understand the user's request
2. Identify constraints (tools, permissions, time, scope boundaries)
3. Capture initial evidence from context

{schema}

User request: {user_message}

Respond with ONLY valid JSON matching the schema above.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

prompt = load_prompt("fsm/intake").format(
    schema=get_intake_output_schema(),
    user_message="Add JWT authentication to the auth module"
)
```
