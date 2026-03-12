"""FSM State Reasoning - LLM-based reasoning at each workflow state.

This module provides structured prompts for the LLM to reason about the current state
and make decisions about next actions. Each FSM state has a specific prompt that
asks the LLM to output structured JSON with their reasoning.

FSM States:
- INTAKE: Analyze user intent and establish context
- PLAN: Create/modify todos based on current state
- REASON: Decide what action to take next
- ACT: Execute tool calls
- SYNTHESIZE: Process tool results and update understanding
- CHECK: Evaluate progress and decide whether to continue

The LLM outputs are parsed into Pydantic models from workflow.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dawn_kestrel.agents.workflow import (
    IntakeOutput,
    PlanOutput,
    ActOutput,
    SynthesizeOutput,
    CheckOutput,
    ReasonOutput,
    TodoItem,
    ToolExecution,
    SynthesizedFinding,
    BudgetConsumed,
    get_intake_output_schema,
    get_plan_output_schema,
    get_act_output_schema,
    get_synthesize_output_schema,
    get_check_output_schema,
    get_reason_output_schema,
)
from dawn_kestrel.prompts.loader import load_prompt

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXT SUMMARY BUILDER
# =============================================================================


def _build_context_summary(state: str, context: dict[str, Any]) -> str:
    """Build a context summary string from individual context fields.

    This creates a formatted multi-line string that summarizes the workflow
    context for use in prompt templates.

    Args:
        state: FSM state name (plan, reason, act, synthesize, check)
        context: Dictionary of context variables

    Returns:
        Formatted context summary string
    """
    lines: list[str] = []

    if state == "plan":
        # PLAN context: intent, constraints, evidence, current_todos, last_tool_results
        intent = context.get("intent", "Unknown")
        constraints = context.get("constraints", [])
        evidence = context.get("evidence", [])
        current_todos = context.get("current_todos", [])
        last_tool_results = context.get("last_tool_results", "")

        lines.append(f"Intent: {intent}")
        if constraints:
            lines.append(f"Constraints: {', '.join(str(c) for c in constraints[:5])}")
        if evidence:
            lines.append(f"Evidence gathered: {len(evidence)} items")
        if current_todos:
            lines.append(f"Current todos: {len(current_todos)} items")
            for todo in current_todos[:5]:
                if isinstance(todo, dict):
                    lines.append(f"  - {todo.get('id', '?')}: {todo.get('description', '')[:50]}")
        if last_tool_results:
            lines.append(f"Last tool results: {str(last_tool_results)[:200]}")

    elif state == "reason":
        # REASON context: intent, current_todos, evidence, iteration, max_iterations, last_tool_results
        intent = context.get("intent", "Unknown")
        current_todos = context.get("current_todos", [])
        evidence = context.get("evidence", [])
        iteration = context.get("iteration", "0")
        max_iterations = context.get("max_iterations", "10")
        last_tool_results = context.get("last_tool_results", "")

        lines.append(f"Intent: {intent}")
        lines.append(f"Iteration: {iteration}/{max_iterations}")
        if current_todos:
            lines.append(f"Current todos: {len(current_todos)} items")
            for todo in current_todos[:5]:
                if isinstance(todo, dict):
                    lines.append(
                        f"  - {todo.get('id', '?')}: {todo.get('description', '')[:50]} (status: {todo.get('status', 'pending')})"
                    )
        if evidence:
            lines.append(f"Evidence gathered: {len(evidence)} items")
        if last_tool_results:
            lines.append(f"Last tool results: {str(last_tool_results)[:200]}")

    elif state == "check":
        # CHECK context: intent, all_todos, completed_todos, pending_todos, evidence, iteration, max_iterations, tokens_used
        intent = context.get("intent", "Unknown")
        all_todos = context.get("all_todos", [])
        completed_todos = context.get("completed_todos", [])
        pending_todos = context.get("pending_todos", [])
        evidence = context.get("evidence", [])
        iteration = context.get("iteration", "0")
        max_iterations = context.get("max_iterations", "10")
        tokens_used = context.get("tokens_used", "0")

        lines.append(f"Intent: {intent}")
        lines.append(f"Total todos: {len(all_todos)}")
        lines.append(f"Completed: {len(completed_todos)}")
        lines.append(f"Pending: {len(pending_todos)}")
        if evidence:
            lines.append(f"Evidence gathered: {len(evidence)} items")
        lines.append(f"Iteration: {iteration}/{max_iterations}")
        lines.append(f"Tokens used: {tokens_used}")

    else:
        # Generic fallback
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}: {json.dumps(value, indent=2)[:200]}")
            else:
                lines.append(f"{key}: {str(value)[:200]}")

    return "\n".join(lines)


def _get_schema_for_state(state: str) -> str:
    """Get the JSON schema string for a given FSM state.

    Args:
        state: FSM state name

    Returns:
        JSON schema string
    """
    schema_map = {
        "intake": get_intake_output_schema,
        "plan": get_plan_output_schema,
        "reason": get_reason_output_schema,
        "act": get_act_output_schema,
        "synthesize": get_synthesize_output_schema,
        "check": get_check_output_schema,
    }
    schema_fn = schema_map.get(state)
    if schema_fn:
        return schema_fn()
    return ""


# =============================================================================
# REASONING FUNCTIONS
# =============================================================================


def format_fsm_prompt(
    state: str,
    context: dict[str, Any],
) -> str:
    """Format an FSM state prompt with context.

    Loads the prompt template from markdown files and formats it with
    the provided context variables.

    Args:
        state: FSM state name (intake, plan, reason, act, synthesize, check)
        context: Dictionary of context variables to fill in

    Returns:
        Formatted prompt string
    """
    try:
        # Load the markdown prompt template
        template = load_prompt(f"fsm/{state}")
    except FileNotFoundError:
        logger.warning(f"Prompt file not found for state: {state}")
        return ""

    # Build the formatted context based on state requirements
    if state == "intake":
        # INTAKE expects: {user_message}, {schema}
        formatted_context = {
            "user_message": context.get("user_message", ""),
            "schema": get_intake_output_schema(),
        }
    elif state == "act":
        # ACT expects: {intent}, {atomic_step}, {why_now}, {constraints}, {allowed_tools},
        #              {current_todo_id}, {description}, {priority}, {notes}, {schema}
        formatted_context = {
            "intent": context.get("intent", ""),
            "atomic_step": context.get("atomic_step", ""),
            "why_now": context.get("why_now", ""),
            "constraints": context.get("constraints", ""),
            "allowed_tools": context.get("allowed_tools", ""),
            "current_todo_id": context.get("current_todo_id", ""),
            "description": context.get("description", ""),
            "priority": context.get("priority", "medium"),
            "notes": context.get("notes", ""),
            "schema": get_act_output_schema(),
        }
    elif state == "synthesize":
        # SYNTHESIZE expects: {current_todo_id}, {act_summary}, {schema}
        formatted_context = {
            "current_todo_id": context.get("current_todo_id", ""),
            "act_summary": context.get("act_summary", ""),
            "schema": get_synthesize_output_schema(),
        }
    elif state == "check":
        # CHECK expects: many individual fields - build context_summary for compatibility
        # with older markdown template, or use individual fields if present
        formatted_context = {
            "current_todo_id": context.get("current_todo_id", ""),
            "description": context.get("description", ""),
            "status": context.get("status", "pending"),
            "total_todos": context.get("total_todos", str(len(context.get("all_todos", [])))),
            "pending_count": context.get(
                "pending_count", str(len(context.get("pending_todos", [])))
            ),
            "last_action": context.get("last_action", ""),
            "iterations_consumed": context.get(
                "iterations_consumed", context.get("iteration", "0")
            ),
            "iterations_max": context.get("iterations_max", context.get("max_iterations", "10")),
            "tool_calls_consumed": context.get("tool_calls_consumed", "0"),
            "tool_calls_max": context.get("tool_calls_max", "100"),
            "wall_time_consumed": context.get("wall_time_consumed", "0.0"),
            "wall_time_max": context.get("wall_time_max", "3600.0"),
            "stagnation_count": context.get("stagnation_count", "0"),
            "stagnation_threshold": context.get("stagnation_threshold", "3"),
            "schema": get_check_output_schema(),
        }
    else:
        # PLAN, REASON expect: {context_summary}, {schema}
        context_summary = _build_context_summary(state, context)
        formatted_context = {
            "context_summary": context_summary,
            "schema": _get_schema_for_state(state),
        }

    # Format context values for string substitution
    final_context = {}
    for key, value in formatted_context.items():
        if isinstance(value, list):
            final_context[key] = json.dumps(value, indent=2) if value else "[]"
        elif isinstance(value, dict):
            final_context[key] = json.dumps(value, indent=2) if value else "{}"
        else:
            final_context[key] = str(value) if value is not None else ""

    # Format the template
    try:
        return template.format(**final_context)
    except KeyError as e:
        logger.warning(f"Missing key in prompt template for {state}: {e}")
        return template


def parse_fsm_output(
    state: str,
    llm_output: str,
) -> dict[str, Any] | None:
    """Parse LLM output for an FSM state.

    Args:
        state: FSM state name
        llm_output: Raw LLM output string

    Returns:
        Parsed output as dict, or None if parsing fails
    """
    try:
        # Try to extract JSON from the output
        # Handle markdown code blocks
        output = llm_output.strip()
        if "```json" in output:
            start = output.find("```json") + 7
            end = output.find("```", start)
            output = output[start:end].strip()
        elif "```" in output:
            start = output.find("```") + 3
            end = output.find("```", start)
            output = output[start:end].strip()

        parsed = json.loads(output)

        # Validate with Pydantic models
        if state == "intake":
            return IntakeOutput(**parsed).model_dump()
        elif state == "plan":
            return PlanOutput(**parsed).model_dump()
        elif state == "act":
            return ActOutput(**parsed).model_dump()
        elif state == "synthesize":
            return SynthesizeOutput(**parsed).model_dump()
        elif state == "check":
            return CheckOutput(**parsed).model_dump()
        elif state == "reason":
            # Validate with ReasonOutput model
            return ReasonOutput(**parsed).model_dump()

        # Fallback for unknown states
        return dict[str, Any](parsed)

    except Exception as e:
        logger.warning(f"Failed to parse FSM output for {state}: {e}")
        # Return raw output as thinking
        return {
            "thinking": llm_output,
            "parse_error": str(e),
        }


def get_fsm_reasoning_summary(state: str, parsed_output: dict[str, Any]) -> str:
    """Get a human-readable summary of FSM reasoning output.

    Args:
        state: FSM state name
        parsed_output: Parsed output dict

    Returns:
        Human-readable summary string
    """
    if not parsed_output:
        return ""

    if state == "intake":
        intent = parsed_output.get("intent", "")
        constraints = parsed_output.get("constraints", [])
        evidence = parsed_output.get("initial_evidence", [])

        summary = f"Intent: {intent}"
        if constraints:
            summary += f"\nConstraints: {', '.join(constraints[:3])}"
            if len(constraints) > 3:
                summary += f" (+{len(constraints) - 3} more)"
        if evidence:
            summary += f"\nInitial evidence: {len(evidence)} items"
        return summary

    elif state == "plan":
        todos = parsed_output.get("todos", [])
        reasoning = parsed_output.get("reasoning", "")

        summary = f"Created {len(todos)} todos"
        if reasoning:
            summary += f"\nReasoning: {reasoning[:200]}"

        # List high priority todos
        high_priority = [t for t in todos if t.get("priority") == "high"]
        if high_priority:
            summary += f"\nHigh priority: {', '.join(t.get('description', '')[:50] for t in high_priority[:3])}"
        return summary

    elif state == "reason":
        # Updated for new ReasonOutput schema
        todo_id = parsed_output.get("todo_id", "")
        atomic_step = parsed_output.get("atomic_step", "")
        why_now = parsed_output.get("why_now", "")
        next_phase = parsed_output.get("next_phase", "act")
        confidence = parsed_output.get("confidence", 0)
        risks = parsed_output.get("risks", [])

        summary = f"Todo: {todo_id}"
        if atomic_step:
            summary += f"\nAtomic step: {atomic_step[:200]}"
        if why_now:
            summary += f"\nWhy now: {why_now[:200]}"
        summary += f"\nNext phase: {next_phase}"
        summary += f"\nConfidence: {confidence:.0%}"
        if risks:
            summary += f"\nRisks: {', '.join(risks[:3])}"
        return summary

    elif state == "synthesize":
        findings = parsed_output.get("findings", [])
        updated_todos = parsed_output.get("updated_todos", [])
        summary_text = parsed_output.get("summary", "")

        summary = f"Found {len(findings)} findings"
        if updated_todos:
            completed = [t for t in updated_todos if t.get("status") == "completed"]
            summary += f", updated {len(updated_todos)} todos ({len(completed)} completed)"
        if summary_text:
            summary += f"\n{summary_text[:300]}"
        return summary

    elif state == "check":
        todo_complete = parsed_output.get("todo_complete", False)
        next_phase = parsed_output.get("next_phase", "")
        confidence = parsed_output.get("confidence", 0)
        reasoning = parsed_output.get("reasoning", "")

        summary = f"Todo complete: {todo_complete}"
        summary += f"\nNext phase: {next_phase}"
        summary += f"\nConfidence: {confidence:.0%}"
        if reasoning:
            summary += f"\nReasoning: {reasoning[:200]}"
        return summary

    return str(parsed_output)[:500]
