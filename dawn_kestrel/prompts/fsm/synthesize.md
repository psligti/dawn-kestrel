# SYNTHESIZE Phase Prompt

## GOAL

Review the tool result from the ACT phase, merge findings into the overall context, and summarize what was learned. This phase processes action results and extracts structured findings.

## INPUT

| Variable | Type | Description |
|----------|------|-------------|
| `{current_todo_id}` | string | ID of the todo just acted upon |
| `{act_summary}` | string | Multi-line summary of the ACT phase result |
| `{schema}` | string | Dynamic JSON schema from `get_synthesize_output_schema()` |

### Act Summary Contents

The `act_summary` is built dynamically from `context.last_act_output`:
```
Tool Result:
- Tool: {tool_name}
- Status: {status}
- Summary: {result_summary}
- Artifacts: {comma-separated list or "none"}

Failure: {failure message if any}
```

## OUTPUT

The LLM must return valid JSON matching the `SynthesizeOutput` schema:

```json
{
  "findings": [
    {
      "id": "string (required) - Unique finding identifier",
      "category": "string (required) - One of: security, performance, correctness, style, architecture, documentation, other",
      "severity": "string (required) - One of: critical, high, medium, low, info",
      "title": "string (required) - Short title",
      "description": "string (optional) - Detailed description",
      "evidence": "string (optional) - Evidence supporting this finding",
      "recommendation": "string (optional) - Suggested fix",
      "confidence": "number (optional) - 0.0 to 1.0",
      "related_todos": ["string (optional) - Related todo IDs"]
    }
  ],
  "updated_todos": [
    {
      "id": "string (required)",
      "operation": "string (required)",
      "description": "string (required)",
      "priority": "string (optional)",
      "status": "string (optional)",
      "dependencies": ["string (optional)"],
      "notes": "string (optional)"
    }
  ],
  "summary": "string (optional) - High-level summary",
  "uncertainty_reduction": "number (optional) - How much uncertainty was reduced (0.0-1.0)",
  "confidence_level": "number (optional) - Overall confidence (0.0-1.0)"
}
```

## VALIDATION

- **Required Fields**: `findings`, `updated_todos` (can be empty arrays)
- **Finding Required**: `id`, `category`, `severity`, `title`
- **Valid Categories**: `security`, `performance`, `correctness`, `style`, `architecture`, `documentation`, `other`
- **Valid Severities**: `critical`, `high`, `medium`, `low`, `info`
- **Confidence Range**: 0.0 to 1.0
- **Schema**: `SynthesizeOutput` Pydantic model with `extra="forbid"`

## CONSTRAINTS

- Iteration count incremented after this phase
- Findings are appended to `context.findings`
- Budget `iterations` is updated
- Output must be valid JSON only - no markdown code blocks
- Never include fields outside the schema

---

## Prompt Template

```
You are in the SYNTHESIZE phase of a workflow loop.

Your task:
1. Review the tool result from the ACT phase
2. Merge findings into the overall context
3. Summarize what was learned

Current todo: {current_todo_id}
{act_summary}

{schema}

Respond with ONLY valid JSON matching the schema above.
```

## Example Usage

```python
from dawn_kestrel.prompts.loader import load_prompt

# Build act_summary from last_act_output
action = context.last_act_output.action
act_summary = f"""
Tool Result:
- Tool: {action.tool_name}
- Status: {action.status}
- Summary: {action.result_summary}
- Artifacts: {", ".join(action.artifacts) if action.artifacts else "none"}
"""
if context.last_act_output.failure:
    act_summary += f"\nFailure: {context.last_act_output.failure}"

prompt = load_prompt("fsm/synthesize").format(
    current_todo_id=context.current_todo_id,
    act_summary=act_summary,
    schema=get_synthesize_output_schema()
)
```
