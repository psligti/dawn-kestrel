# REASON Phase Prompt

## GOAL

Analyze the current context and decide what action to take next using the ReAct (Reasoning + Acting) pattern. Output a reasoning trace (Thought) and a decision on what to do next (Action).

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
  "thought": "string (required) - Natural language reasoning trace analyzing the current state",
  "action": "string (required) - What to do next (tool call, state transition, or done)",
  "next_state": "string (required) - One of: act, synthesize, check, done",
  "confidence": "number (optional) - Confidence level 0.0-1.0 in the reasoning",
  "reasoning_type": "string (optional) - Type: decompose, analyze, plan, evaluate, decide"
}
```

## ReAct Pattern

The REASON state implements the ReAct (Reasoning + Acting) pattern:

1. **Thought**: A natural language reasoning trace that:
   - Decomposes complex problems into smaller steps
   - Analyzes available evidence and context
   - Plans the next action based on current state
   - Evaluates progress toward the goal
   - Makes explicit decisions with justification

2. **Action**: A description of what to do next:
   - Tool call with specific arguments
   - State transition (act, synthesize, check, done)
   - Request for more information

3. **Next State**: Where the workflow should go:
   - `act` - Execute a tool call
   - `synthesize` - Combine findings into a conclusion
   - `check` - Verify completion criteria
   - `done` - Workflow is complete

## VALIDATION

- **Required Fields**: `thought`, `action`, `next_state`
- **Valid Next States**: `act`, `synthesize`, `check`, `done`
- **Confidence Range**: 0.0 to 1.0 (if provided)
- **Schema**: `ReasonOutput` Pydantic model with `extra="ignore"`

## CONSTRAINTS

- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema
- The thought should be detailed enough to understand the reasoning
- The action should be specific and actionable
- The next_state should be consistent with the action

---

## Prompt Template

```
You are in the REASON phase of a workflow loop using the ReAct pattern.

Your task:
1. Analyze the current context and evidence
2. Produce a Thought: natural language reasoning about what to do
3. Produce an Action: specific next step to take
4. Choose the next state: act, synthesize, check, or done

Current workflow context:
{context_summary}

{schema}

Respond with ONLY valid JSON matching the schema above.
Your thought should explain your reasoning process.
Your action should be specific and actionable.
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
  "thought": "Looking at the current state, I have 3 pending todos. The first todo 'implement auth' is high priority and has no dependencies. I have already gathered evidence about the existing auth module. The next logical step is to implement the JWT validation logic.",
  "action": "Call write tool to create jwt_validator.py with JWT validation implementation",
  "next_state": "act",
  "confidence": 0.85,
  "reasoning_type": "plan"
}
```
