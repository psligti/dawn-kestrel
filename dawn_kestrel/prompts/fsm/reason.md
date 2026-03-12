# REASON Phase Prompt

## GOAL

Evaluate the current context and decide the next atomic action. This is a context-first reasoning phase that produces a tool-agnostic atomic step description. The ACT phase will select the appropriate tool to execute based on this atomic step.

## INPUT

| Variable | Type | Description |
|----------|------|-------------|
| `{context_summary}` | string | Multi-line summary of workflow state (intent, constraints, todos, evidence) |
| `{schema}` | string | Dynamic JSON schema from `get_reason_output_schema()` |

### Context Summary Contents

The `context_summary` is built dynamically by `_build_context_summary()` and includes:
- Intent from INTAKE phase
- Constraints identified
- Current todo details (if any)
- Evidence accumulated so far
- Findings from previous iterations
- Iterations count

## OUTPUT

The LLM must return valid JSON matching the `ReasonOutput` schema:

```json
{
  "todo_id": "string (required) - ID of the todo being evaluated",
  "atomic_step": "string (required) - Tool-agnostic next step (NO tool names)",
  "why_now": "string (required) - Justification for why this action is needed now",
  "next_phase": "string (required) - One of: act, done",
  "confidence": "number (optional) - Confidence level 0.0-1.0 in the reasoning",
  "evidence_used": ["string (optional) - Evidence references that informed this decision"],
  "risks": ["string (optional) - Potential risks or concerns with this action"]
}
```

## Context-First Reasoning Pattern

The REASON state produces a tool-agnostic atomic next step:

1. **todo_id**: The current todo being evaluated
2. **atomic_step**: A tool-agnostic description of WHAT to do next:
   - Describes the intent/action without tool names
   - ACT phase will select appropriate tool based on this
   - Example: "Read the authentication module" (not "Use read tool")
3. **why_now**: Justification grounded in constraints/evidence:
   - Why this action is needed at this moment
   - What constraints or evidence drive this decision
4. **next_phase**: Where the workflow should go:
   - `act` - Execute a tool call
   - `done` - Workflow is complete

## VALIDATION

- **Required Fields**: `todo_id`, `atomic_step`, `why_now`
- **Valid next_phase**: `act`, `done`
- **Confidence Range**: 0.0 to 1.0 (if provided)
- **Schema**: `ReasonOutput` Pydantic model with `extra="forbid"`

## CONSTRAINTS

- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema
- atomic_step must NOT mention specific tool names
- why_now should reference constraints, evidence, or todos
- next_phase should be consistent with the atomic_step

---

## Prompt Template

```
You are in the REASON phase of a workflow loop.

Your task is to evaluate the current context and decide the next atomic action.
This is a context-first reasoning phase that produces a tool-agnostic atomic step.

CRITICAL: Your atomic_step must NOT mention specific tool names.
- DO say: "Read the authentication module to understand the current implementation"
- DON'T say: "Use the read tool to fetch src/auth.py"
- The ACT phase will select the appropriate tool based on your atomic step.

Current workflow context:
{context_summary}

{schema}

Respond with ONLY valid JSON matching the schema above.
Your atomic_step should describe WHAT to do, not HOW (tool selection).
Your why_now should justify timing based on constraints/evidence/todos.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

prompt = load_prompt("fsm/reason").format(
    context_summary=workflow._build_context_summary(),
    schema=get_reason_output_schema()
)
```

## Example Output

```json
{
  "todo_id": "todo-1",
  "atomic_step": "Read the authentication module to understand current implementation",
  "why_now": "Cannot implement JWT without understanding existing auth flow; evidence shows auth module exists at src/auth/",
  "next_phase": "act",
  "confidence": 0.85,
  "evidence_used": ["auth module exists at src/auth/", "README mentions session-based auth"],
  "risks": ["May find deprecated patterns requiring refactoring"]
}
```
