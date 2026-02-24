# Migration Guide: plan → reason State

## Overview

The `plan` state has been deprecated in favor of the `reason` state, which implements the ReAct (Reasoning + Acting) pattern. This guide helps you migrate existing code.

## What Changed

| Old | New |
|-----|-----|
| `plan` state | `reason` state |
| `next_phase="plan"` | `next_phase="reason"` |
| `metadata={"agent_mode": "plan"}` | `metadata={"agent_mode": "reason"}` |

## Deprecation Timeline

- **Now**: `plan` state emits `DeprecationWarning` but still works
- **Future**: `plan` state will be removed in a future version

## Migration Steps

### 1. Update FSM Transitions

```python
# OLD
await fsm.transition_to("plan")

# NEW
await fsm.transition_to("reason")
```

### 2. Update CheckOutput

```python
# OLD
CheckOutput(next_phase="plan", ...)

# NEW
CheckOutput(next_phase="reason", ...)
```

### 3. Update Metadata

```python
# OLD
metadata={"agent_mode": "plan"}

# NEW
metadata={"agent_mode": "reason"}
```

## REASON State Output

The REASON state outputs a `ReasoningResult`:

```python
@dataclass
class ReasoningResult:
    thought: str      # Natural language reasoning trace
    action: str       # What action to take
    next_state: str   # Target state (act, synthesize, check, done)
```

## Available Strategies

### CoTStrategy (Chain-of-Thought)
Linear reasoning: analyze → plan → execute

### ReActStrategy
Interleaved reasoning: reason → act → observe → repeat

## Example Usage

```python
from dawn_kestrel.workflow.strategies import CoTStrategy, ReasoningContext
from dawn_kestrel.workflow.reason_executor import ReasonExecutor

# Create executor with strategy
strategy = CoTStrategy()
executor = ReasonExecutor(strategy)

# Execute reasoning
context = ReasoningContext(
    current_state="reason",
    available_actions=["analyze", "execute"],
    evidence=["Found X", "Observed Y"],
    constraints={"max_iterations": 10}
)
result = executor.execute(context)

print(result.thought)      # "Based on evidence X and Y, I should..."
print(result.action)      # "analyze"
print(result.next_state)  # "act"
```

## Questions?

See:
- `dawn_kestrel/prompts/fsm/reason.md` - REASON state prompt
- `dawn_kestrel/workflow/strategies.py` - Strategy implementations
- `.sisyphus/notepads/fsm-reason-step-refactor/learnings.md` - Implementation notes
