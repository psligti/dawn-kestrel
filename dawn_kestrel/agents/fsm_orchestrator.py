"""FSM Orchestrator - Manages FSM state transitions with LLM reasoning.

This module provides an orchestrator that calls the LLM at each FSM state
with specific prompts to get structured reasoning output, and emits
events with the actual thinking content.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Literal, cast

from dawn_kestrel.agents.workflow import (
    ActOutput,
    CheckOutput,
    IntakeOutput,
    PlanOutput,
    ReasonOutput,
    get_act_output_schema,
    get_check_output_schema,
    get_intake_output_schema,
    get_plan_output_schema,
    get_reason_output_schema,
    get_synthesize_output_schema,
)
from dawn_kestrel.core.event_bus import Events, bus
from dawn_kestrel.prompts.loader import load_prompt

from dawn_kestrel.ai_session import AISession

from dawn_kestrel.core.models import Session

logger = logging.getLogger(__name__)


WORKFLOW_STATES = ["intake", "plan", "reason", "act", "synthesize", "check", "done"]


class FSMOrchestrator:
    """Orchestrates FSM state transitions with LLM reasoning.

    This class manages the FSM lifecycle for calling the LLM at each state
    with specific prompts to get structured reasoning output.

    The structured output is then emitted as FSM events that the CLI
    can display to show the agent's thinking process.
    """

    def __init__(
        self,
        ai_session: AISession,
        session: Session,
    ):
        """Initialize FSM orchestrator.

        Args:
            ai_session: The AI session for LLM calls
            session: The session object
        """
        self.ai_session = ai_session
        self.session = session
        self.current_state = "intake"
        self.todos: list[dict[str, Any]] = []
        self.iteration = 0
        self.evidence: list[str] = []
        self.last_tool_result: str = ""
        self._intent: str = ""  # Store intent for later states
        self._constraints: list[str] = []
        self.last_reason_output: ReasonOutput | None = None

    @staticmethod
    def _to_str_list(value: Any) -> list[str]:
        if isinstance(value, list):
            items = cast(list[object], value)
            return [str(item) for item in items if item is not None]
        return []

    def _get_current_todo(self, todo_id: str | None = None) -> dict[str, Any]:
        if todo_id:
            for todo in self.todos:
                if str(todo.get("id")) == todo_id:
                    return todo
        for todo in self.todos:
            if todo.get("status") in {"in_progress", "pending"}:
                return todo
        return self.todos[0] if self.todos else {}

    @staticmethod
    def _compact_text(text: str) -> str:
        return " ".join(str(text).split())

    def _build_context_summary(self, extra_context: str | None = None) -> str:
        last_tool_summary = self._compact_text(self.last_tool_result) or "none"
        lines = [
            f"Intent: {self._intent}",
            f"Constraints: {json.dumps(self._constraints, ensure_ascii=True)}",
            "Todos:",
        ]
        if self.todos:
            for todo in self.todos[:10]:
                todo_id = str(todo.get("id", ""))
                description = self._compact_text(str(todo.get("description", "")))
                status = str(todo.get("status", "pending"))
                priority = str(todo.get("priority", "medium"))
                lines.append(f"- {todo_id} | {description} | {status} | {priority}")
        else:
            lines.append("- none")

        lines.append("Evidence:")
        if self.evidence:
            for item in self.evidence[:10]:
                lines.append(f"- {self._compact_text(str(item))}")
        else:
            lines.append("- none")

        lines.extend(
            [
                f"Iteration: {self.iteration}",
                f"Last tool result: {last_tool_summary}",
            ]
        )
        if extra_context:
            lines.append(f"Context: {extra_context}")
        return "\n".join(lines)

    async def run_intake(self, user_message: str) -> IntakeOutput | None:
        """Run INTAKE state - analyze user request.

        This calls the LLM to analyze the user's request and extract:
        - intent: What the agent is trying to achieve
        - constraints: Known limitations
        - initial_evidence: What is already known

        Args:
            user_message: The user's original request

        Returns:
            IntakeOutput with structured analysis
        """
        template = load_prompt("fsm/intake")
        prompt = template.format(
            user_message=user_message,
            schema=get_intake_output_schema(),
        )

        try:
            response = await self.ai_session.process_message(
                user_message=prompt,
                options={"temperature": 0.3, "disable_tools": True},
            )
            response_text = response.text or ""

            # Try to extract JSON from response
            parsed = self._extract_json(response_text)

            if parsed:
                result = IntakeOutput(
                    intent=str(parsed.get("intent", user_message[:200])),
                    constraints=self._to_str_list(parsed.get("constraints", [])),
                    initial_evidence=self._to_str_list(parsed.get("initial_evidence", [])),
                )
                self._intent = result.intent
                self._constraints = result.constraints
                self.evidence = result.initial_evidence

                reasoning_text = str(
                    parsed.get("reasoning")
                    or parsed.get("thinking")
                    or result.intent
                    or "Intake complete"
                )

                # Emit FSM event with reasoning
                await self._emit_fsm_event(
                    state="intake",
                    reasoning=reasoning_text,
                    data={
                        "intent": result.intent,
                        "todo_id": "",
                        "atomic_step": "",
                        "selection_reason": "",
                        "constraints": result.constraints[:3] if result.constraints else [],
                        "initial_evidence": result.initial_evidence[:3]
                        if result.initial_evidence
                        else [],
                        "llm_response": response_text[:4000],
                    },
                )

                self.current_state = "plan"
                return result
            else:
                # Fallback to raw output
                intent = response_text[:200] if response_text else user_message[:200]
                self._intent = intent
                self._constraints = []
                await self._emit_fsm_event(
                    state="intake",
                    reasoning=response_text[:600] if response_text else intent,
                    data={
                        "intent": intent,
                        "todo_id": "",
                        "atomic_step": "",
                        "selection_reason": "",
                        "llm_response": response_text[:4000],
                    },
                )
                return IntakeOutput(intent=intent)

        except Exception as e:
            logger.warning(f"Intake parsing failed: {e}")
            self._intent = user_message[:100]
            self._constraints = []
            await self._emit_fsm_event(
                state="intake",
                reasoning=f"Parsing failed, using raw message",
                data={
                    "error": str(e),
                    "intent": self._intent,
                    "todo_id": "",
                    "atomic_step": "",
                    "selection_reason": "",
                    "llm_response": "",
                },
            )
            return IntakeOutput(intent=user_message[:100])

    async def run_reason(
        self, context: str, options: dict[str, Any] | None = None
    ) -> ReasonOutput | None:
        """Run REASON state - decide what to do next.

        This calls the LLM to reason about the current context
        and decide the next action.

        Args:
            context: Context about current state
            options: Optional options

        Returns:
            ReasonOutput with reasoning and next action
        """
        context_summary = self._build_context_summary(extra_context=context)
        template = load_prompt("fsm/reason")
        prompt = template.format(
            context_summary=context_summary,
            schema=get_reason_output_schema(),
        )

        try:
            reasoning_options: dict[str, Any] = {"temperature": 0.3, "disable_tools": True}
            if options:
                reasoning_options.update(options)
            response = await self.ai_session.process_message(
                user_message=prompt,
                options=reasoning_options,
            )
            response_text = response.text or ""

            parsed = self._extract_json(response_text)

            if parsed:
                result = ReasonOutput(**parsed)
                self.last_reason_output = result

                await self._emit_fsm_event(
                    state="reason",
                    reasoning=result.why_now or result.atomic_step,
                    data={
                        "intent": self._intent,
                        "todo_id": result.todo_id,
                        "atomic_step": result.atomic_step,
                        "why_now": result.why_now,
                        "next_phase": result.next_phase,
                        "iteration": self.iteration,
                        "llm_response": response_text[:4000],
                    },
                )

                return result
            else:
                # Fallback - just use raw text as reasoning
                fallback_todo = self._get_current_todo()
                todo_id = str(fallback_todo.get("id", ""))
                atomic_step = (
                    "Continue with current todo"
                    if todo_id
                    else "Determine next step based on intent"
                )
                why_now = response_text[:300] if response_text else "Continuing based on intent"
                result = ReasonOutput(
                    todo_id=todo_id,
                    atomic_step=atomic_step,
                    why_now=why_now,
                    next_phase="act",
                )
                self.last_reason_output = result
                await self._emit_fsm_event(
                    state="reason",
                    reasoning=why_now,
                    data={
                        "intent": self._intent,
                        "todo_id": todo_id,
                        "atomic_step": atomic_step,
                        "next_phase": "act",
                        "raw_response": True,
                        "llm_response": response_text[:4000],
                    },
                )
                return result

        except Exception as e:
            logger.warning(f"Reason parsing failed: {e}")
            fallback_todo = self._get_current_todo()
            todo_id = str(fallback_todo.get("id", ""))
            result = ReasonOutput(
                todo_id=todo_id,
                atomic_step="Fallback reasoning",
                why_now=f"Error: {str(e)[:100]}",
                next_phase="act",
            )
            self.last_reason_output = result
            await self._emit_fsm_event(
                state="reason",
                reasoning=result.why_now,
                data={
                    "intent": self._intent,
                    "todo_id": todo_id,
                    "atomic_step": result.atomic_step,
                    "next_phase": "act",
                    "error": str(e)[:100],
                },
            )
            return result

    async def run_act_select(
        self,
        reason: ReasonOutput,
        allowed_tools: list[str],
        tool_signatures: str,
    ) -> ActOutput | None:
        current_todo = self._get_current_todo(reason.todo_id)
        todo_notes = self._compact_text(str(current_todo.get("notes", "")))
        last_tool_summary = self._compact_text(self.last_tool_result) or "none"
        notes_parts: list[str] = []
        if todo_notes:
            notes_parts.append(f"Todo notes: {todo_notes}")
        notes_parts.append(f"Last tool result: {last_tool_summary}")
        notes = " ".join(notes_parts)

        allowed_tools_text = ", ".join([tool.lower() for tool in allowed_tools])
        constraints_text = json.dumps(self._constraints, ensure_ascii=True)
        template = load_prompt("fsm/act")
        prompt = template.format(
            intent=self._intent,
            atomic_step=reason.atomic_step,
            why_now=reason.why_now,
            constraints=constraints_text,
            allowed_tools=allowed_tools_text,
            current_todo_id=str(current_todo.get("id", reason.todo_id)),
            description=str(current_todo.get("description", "")),
            priority=str(current_todo.get("priority", "medium")),
            notes=notes,
            schema=get_act_output_schema(),
        )

        try:
            response = await self.ai_session.process_message(
                user_message=prompt,
                options={"temperature": 0.2, "disable_tools": True},
            )
            response_text = response.text or ""
            parsed = self._extract_json(response_text)
            if parsed:
                result = ActOutput(**parsed)
            else:
                result = ActOutput(
                    action=None,
                    acted_todo_id=reason.todo_id,
                    tool_result_summary="Selection failed",
                    failure="Parse failed",
                )

            tool_name = result.action.tool_name if result.action else ""
            selection_reason = result.action.selection_reason if result.action else ""
            await self._emit_fsm_event(
                state="act",
                reasoning=selection_reason or "Selected tool",
                data={
                    "intent": self._intent,
                    "todo_id": reason.todo_id,
                    "atomic_step": reason.atomic_step,
                    "tool_name": tool_name,
                    "selection_reason": selection_reason,
                    "llm_response": response_text[:4000],
                },
            )

            return result
        except Exception as e:
            logger.warning(f"Act selection failed: {e}")
            await self._emit_fsm_event(
                state="act",
                reasoning=f"Error: {str(e)[:100]}",
                data={
                    "intent": self._intent,
                    "todo_id": reason.todo_id,
                    "atomic_step": reason.atomic_step,
                    "tool_name": "",
                    "selection_reason": "",
                    "error": str(e)[:100],
                },
            )
            return ActOutput(
                action=None,
                acted_todo_id=reason.todo_id,
                tool_result_summary="Selection failed",
                failure=str(e)[:200],
            )

    async def run_synthesize(self, tool_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Run SYNTHESIZE state - process tool results.

        This calls the LLM to synthesize tool results and extract:
        - findings: Key discoveries
        - updated_todos: Todo status updates
        - summary: High-level summary

        Args:
            tool_results: Results from tool executions
            options: Optional options

        Returns:
            Dict with synthesized findings
        """
        summary_lines: list[str] = []
        for result in tool_results:
            tool_name = str(result.get("tool", "unknown"))
            output_text = str(result.get("output", ""))
            summary_lines.append(
                "\n".join(
                    [
                        "Tool Result:",
                        f"- Tool: {tool_name}",
                        "- Status: unknown",
                        f"- Summary: {output_text[:200]}",
                        "- Artifacts: none",
                    ]
                )
            )

        act_summary = "\n\n".join(summary_lines) if summary_lines else "Tool Result:\n- Tool: none"
        self.last_tool_result = act_summary[:400]
        template = load_prompt("fsm/synthesize")
        prompt = template.format(
            current_todo_id=(self.last_reason_output.todo_id if self.last_reason_output else ""),
            act_summary=act_summary,
            schema=get_synthesize_output_schema(),
        )

        try:
            response = await self.ai_session.process_message(
                user_message=prompt,
                options={"temperature": 0.3, "disable_tools": True},
            )
            response_text = response.text or ""

            parsed = self._extract_json(response_text)

            if parsed:
                findings_raw = cast(list[Any], parsed.get("findings", []))
                updated_todos_raw = cast(list[Any], parsed.get("updated_todos", []))
                summary_raw = (
                    parsed.get("summary") or parsed.get("thinking") or "Synthesis complete"
                )

                findings_count = len(findings_raw)
                updated_todos_count = len(updated_todos_raw)
                reasoning_text = str(summary_raw)

                await self._emit_fsm_event(
                    state="synthesize",
                    reasoning=reasoning_text,
                    data={
                        "intent": self._intent,
                        "todo_id": self.last_reason_output.todo_id
                        if self.last_reason_output
                        else "",
                        "atomic_step": self.last_reason_output.atomic_step
                        if self.last_reason_output
                        else "",
                        "selection_reason": "",
                        "findings_count": findings_count,
                        "summary": reasoning_text[:300],
                        "updated_todos_count": updated_todos_count,
                        "llm_response": response_text[:4000],
                    },
                )

                for idx, finding in enumerate(findings_raw):
                    if isinstance(finding, dict):
                        finding_dict = cast(dict[str, Any], finding)
                        title = str(finding_dict.get("title", f"finding-{idx + 1}"))
                    else:
                        title = str(finding)
                    self.evidence.append(f"finding:{idx + 1}:{title}")

                return {
                    "findings": findings_raw,
                    "summary": reasoning_text,
                    "updated_todos": updated_todos_raw,
                }
            else:
                # Fallback
                summary = response_text[:300] if response_text else "Synthesis complete"
                await self._emit_fsm_event(
                    state="synthesize",
                    reasoning=summary,
                    data={
                        "intent": self._intent,
                        "todo_id": self.last_reason_output.todo_id
                        if self.last_reason_output
                        else "",
                        "atomic_step": self.last_reason_output.atomic_step
                        if self.last_reason_output
                        else "",
                        "selection_reason": "",
                        "raw_summary": summary,
                        "llm_response": response_text[:4000],
                    },
                )
                return {"summary": summary}

        except Exception as e:
            logger.warning(f"Synthesize parsing failed: {e}")
            await self._emit_fsm_event(
                state="synthesize",
                reasoning=f"Parsing failed: {str(e)}",
                data={
                    "intent": self._intent,
                    "todo_id": self.last_reason_output.todo_id if self.last_reason_output else "",
                    "atomic_step": self.last_reason_output.atomic_step
                    if self.last_reason_output
                    else "",
                    "selection_reason": "",
                    "error": str(e),
                    "llm_response": "",
                },
            )
            return {"summary": f"Error: {e}"}

    async def run_plan(
        self,
        intent: str,
        constraints: list[str],
        evidence: list[str],
        current_todos: list[dict[str, Any]] | None = None,
    ) -> PlanOutput | None:
        """Run PLAN state - create/update todo list.

        This calls the LLM to plan out todos based on the intent and context.

        Args:
            intent: The user's intent from intake
            constraints: Known constraints
            evidence: Evidence gathered so far
            current_todos: Current todo list (if any)

        Returns:
            PlanOutput with todos
        """
        self._intent = intent
        self._constraints = constraints
        self.evidence = evidence
        context_summary = self._build_context_summary()
        template = load_prompt("fsm/plan")
        prompt = template.format(
            context_summary=context_summary,
            schema=get_plan_output_schema(),
        )

        try:
            response = await self.ai_session.process_message(
                user_message=prompt,
                options={"temperature": 0.3, "disable_tools": True},
            )
            response_text = response.text or ""

            parsed = self._extract_json(response_text)

            if parsed:
                filtered_plan_payload = {
                    key: parsed[key]
                    for key in ("todos", "reasoning", "estimated_iterations", "strategy_selected")
                    if key in parsed
                }
                result = PlanOutput(**filtered_plan_payload)

                # Store todos
                self.todos = [t.model_dump() for t in result.todos]

                # Emit FSM event with reasoning
                reasoning_text = result.reasoning or str(
                    parsed.get("thinking") or response_text[:600]
                )

                await self._emit_fsm_event(
                    state="plan",
                    reasoning=reasoning_text,
                    data={
                        "intent": self._intent,
                        "todo_id": "",
                        "atomic_step": "",
                        "selection_reason": "",
                        "todos_count": len(result.todos),
                        "todos": [t.model_dump() for t in result.todos],
                        "strategy": result.strategy_selected,
                        "estimated_iterations": result.estimated_iterations,
                        "llm_response": response_text[:4000],
                    },
                )

                self.current_state = "reason"
                return result
            else:
                # Fallback
                await self._emit_fsm_event(
                    state="plan",
                    reasoning=response_text[:600] if response_text else "Plan parse failed",
                    data={
                        "intent": self._intent,
                        "todo_id": "",
                        "atomic_step": "",
                        "selection_reason": "",
                        "error": "Parse failed",
                        "raw": response_text[:200],
                        "llm_response": response_text[:4000],
                    },
                )
                return PlanOutput(todos=[])

        except Exception as e:
            logger.warning(f"Plan parsing failed: {e}")
            await self._emit_fsm_event(
                state="plan",
                reasoning=f"Error: {str(e)}",
                data={
                    "intent": self._intent,
                    "todo_id": "",
                    "atomic_step": "",
                    "selection_reason": "",
                    "error": str(e),
                },
            )
            return PlanOutput(todos=[])

    async def run_act(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        todo_id: str = "",
    ) -> ActOutput | None:
        """Run ACT state - record tool execution.

        This emits an FSM event with the tool being executed.
        Note: The actual tool execution happens in runtime.py, this just
        records the action for the FSM event.

        Args:
            tool_name: Name of the tool being executed
            tool_args: Arguments passed to the tool
            todo_id: ID of the todo being acted on

        Returns:
            ActOutput with action details
        """
        # Build copiable command string for bash tools
        command_str = ""
        if tool_name == "bash":
            command_str = tool_args.get("command", "")
        elif tool_name == "read":
            command_str = f"read({tool_args.get('filePath', '')})"
        elif tool_name == "write":
            command_str = f"write({tool_args.get('filePath', '')})"
        else:
            command_str = f"{tool_name}({tool_args})"

        # Emit FSM event with copiable command
        await self._emit_fsm_event(
            state="act",
            reasoning=f"Executing: {tool_name}",
            data={
                "intent": self._intent,
                "todo_id": todo_id,
                "atomic_step": self.last_reason_output.atomic_step
                if self.last_reason_output
                else "",
                "tool_name": tool_name,
                "selection_reason": "",
                "command": command_str,
                "copiable": True,
            },
        )

        return ActOutput(
            action=None,  # Actual execution happens elsewhere
            acted_todo_id=todo_id,
            tool_result_summary="Pending",
        )

    async def run_check(
        self,
        all_todos: list[dict[str, Any]],
        completed_todos: list[dict[str, Any]],
        pending_todos: list[dict[str, Any]],
    ) -> CheckOutput | None:
        """Run CHECK state - evaluate progress.

        This calls the LLM to evaluate whether todos are complete and
        what to do next.

        Args:
            all_todos: All todos
            completed_todos: Completed todos
            pending_todos: Pending todos

        Returns:
            CheckOutput with routing decision
        """
        current_todo = self._get_current_todo(
            self.last_reason_output.todo_id if self.last_reason_output else None
        )
        prompt = load_prompt("fsm/check").format(
            current_todo_id=str(current_todo.get("id", "")),
            description=str(current_todo.get("description", "")),
            status=str(current_todo.get("status", "pending")),
            total_todos=len(all_todos),
            pending_count=len(pending_todos),
            last_action=self.last_tool_result or "No recent tool results",
            iterations_consumed=self.iteration,
            iterations_max=10,
            tool_calls_consumed=0,
            tool_calls_max=100,
            wall_time_consumed=0.0,
            wall_time_max=3600.0,
            stagnation_count=0,
            stagnation_threshold=3,
            schema=get_check_output_schema(),
        )

        try:
            response = await self.ai_session.process_message(
                user_message=prompt,
                options={"temperature": 0.3, "disable_tools": True},
            )
            response_text = response.text or ""

            parsed = self._extract_json(response_text)

            if parsed:
                try:
                    result = CheckOutput(**parsed)
                    reasoning = result.reasoning or "No reasoning provided"

                    # AGENT-DRIVEN TODO COMPLETION: Mark todos complete based on LLM reasoning
                    # The LLM identifies which todos are complete via completed_todo_ids
                    completed_ids = result.completed_todo_ids or []

                    # Also check legacy fields for backwards compatibility
                    if result.todo_complete and result.current_todo_id:
                        if result.current_todo_id not in completed_ids:
                            completed_ids.append(result.current_todo_id)

                    # Mark each identified todo as completed
                    for todo_id in completed_ids:
                        for todo in self.todos:
                            if todo.get("id") == todo_id and todo.get("status") != "completed":
                                todo["status"] = "completed"
                                logger.info(f"Agent marked todo {todo_id} as completed")
                                break

                    # If next_phase is "done", mark ALL remaining todos as completed
                    if result.next_phase == "done":
                        for todo in self.todos:
                            if todo.get("status") != "completed":
                                todo["status"] = "completed"
                                logger.info(
                                    f"Auto-marked todo {todo.get('id')} as completed (done phase)"
                                )

                    # Re-compute completed/pending lists after mutation
                    updated_completed = [t for t in self.todos if t.get("status") == "completed"]
                    updated_pending = [t for t in self.todos if t.get("status") != "completed"]

                    await self._emit_fsm_event(
                        state="check",
                        reasoning=reasoning,
                        data={
                            "intent": self._intent,
                            "todo_id": current_todo.get("id", ""),
                            "atomic_step": self.last_reason_output.atomic_step
                            if self.last_reason_output
                            else "",
                            "selection_reason": "",
                            "todo_complete": result.todo_complete,
                            "next_phase": result.next_phase,
                            "confidence": result.confidence,
                            "completed_count": len(updated_completed),
                            "pending_count": len(updated_pending),
                            "completed_todos": updated_completed,
                            "pending_todos": updated_pending,
                            "completed_todo_ids": completed_ids,
                            "llm_response": response_text[:4000],
                        },
                    )
                    return result
                except Exception:
                    all_done = len(pending_todos) == 0
                    derived_next = parsed.get("next_phase") or parsed.get("next")
                    if derived_next in {"act", "plan", "reason", "done"}:
                        next_phase_val: Literal["act", "plan", "reason", "done"] = derived_next
                    else:
                        next_phase_val = "done" if all_done else "reason"
                    reasoning = str(
                        parsed.get("reasoning")
                        or parsed.get("thinking")
                        or f"Checked {len(completed_todos)} complete, {len(pending_todos)} pending"
                    )
                    await self._emit_fsm_event(
                        state="check",
                        reasoning=reasoning,
                        data={
                            "intent": self._intent,
                            "todo_id": current_todo.get("id", ""),
                            "atomic_step": self.last_reason_output.atomic_step
                            if self.last_reason_output
                            else "",
                            "selection_reason": "",
                            "todo_complete": bool(parsed.get("todo_complete", all_done)),
                            "next_phase": next_phase_val,
                            "completed_count": len(completed_todos),
                            "pending_count": len(pending_todos),
                            "completed_todos": completed_todos,
                            "pending_todos": pending_todos,
                            "llm_response": response_text[:4000],
                        },
                    )
                    return CheckOutput(
                        todo_complete=bool(parsed.get("todo_complete", all_done)),
                        next_phase=next_phase_val,
                        reasoning=reasoning,
                    )
            else:
                # Fallback - determine based on pending todos
                all_done = len(pending_todos) == 0
                next_phase = "done" if all_done else "reason"

                await self._emit_fsm_event(
                    state="check",
                    reasoning=f"Parsed {len(completed_todos)} complete, {len(pending_todos)} pending",
                    data={
                        "intent": self._intent,
                        "todo_id": current_todo.get("id", ""),
                        "atomic_step": self.last_reason_output.atomic_step
                        if self.last_reason_output
                        else "",
                        "selection_reason": "",
                        "todo_complete": all_done,
                        "next_phase": next_phase,
                        "completed_todos": completed_todos,
                        "pending_todos": pending_todos,
                        "parse_failed": True,
                        "llm_response": response_text[:4000],
                    },
                )

                fallback_next_phase: Literal["act", "plan", "reason", "done"] = (
                    "done" if all_done else "reason"
                )

                return CheckOutput(
                    todo_complete=all_done,
                    next_phase=fallback_next_phase,
                    reasoning="Fallback: checked pending todos",
                )

        except Exception as e:
            logger.warning(f"Check parsing failed: {e}")
            await self._emit_fsm_event(
                state="check",
                reasoning=f"Error: {str(e)}",
                data={
                    "intent": self._intent,
                    "todo_id": current_todo.get("id", ""),
                    "atomic_step": self.last_reason_output.atomic_step
                    if self.last_reason_output
                    else "",
                    "selection_reason": "",
                    "error": str(e),
                    "llm_response": "",
                },
            )
            return CheckOutput(next_phase="act", reasoning=f"Error: {e}")

    async def _emit_fsm_event(
        self,
        state: str,
        reasoning: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit an FSM state transition event.

        Args:
            state: Current FSM state name
            reasoning: The LLM's reasoning for this state
            data: Additional data to include in the event
        """
        event_payload = dict(data) if data else {}
        event_payload.setdefault("intent", self._intent)
        if not event_payload.get("todo_id"):
            event_payload["todo_id"] = (
                self.last_reason_output.todo_id if self.last_reason_output else ""
            )
        if not event_payload.get("atomic_step"):
            event_payload["atomic_step"] = (
                self.last_reason_output.atomic_step if self.last_reason_output else ""
            )
        event_payload.setdefault("tool_name", "")
        event_payload.setdefault("selection_reason", "")

        event_data: dict[str, Any] = {
            "session_id": self.session.id,
            "state": state,
            "reasoning": reasoning,
            "iteration": self.iteration,
            "timestamp": time.time(),
        }
        if event_payload:
            event_data.update(event_payload)
        await bus.publish(Events.FSM_THINKING, event_data)
        if os.getenv("DK_POLICY_ENGINE", "0") == "1":
            policy_event = dict(event_data)
            policy_event.setdefault("policy_mode", os.getenv("DK_POLICY_MODE", "fsm"))
            await bus.publish(Events.POLICY_REASONING, policy_event)

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """Extract JSON from LLM response text.

        Handles markdown code blocks and raw JSON.

        Args:
            text: Response text that may contain JSON

        Returns:
            Parsed dict or None if parsing fails
        """
        if not text:
            return None

        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                json_str = text[start:end].strip()
            else:
                json_str = text[start:].strip()
        elif "```" in text:
            # Handle plain code blocks
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                json_str = text[start:end].strip()
            else:
                json_str = text[start:].strip()
        else:
            # Try to find raw JSON
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                json_str = text[start : end + 1]
            else:
                return None

        try:
            return cast(dict[str, Any], json.loads(json_str))
        except json.JSONDecodeError:
            return None
