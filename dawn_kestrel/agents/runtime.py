"""
AgentRuntime - Execute agents with tool filtering and lifecycle management.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, cast

from dawn_kestrel.agents.fsm_orchestrator import FSMOrchestrator
from dawn_kestrel.agents.registry import AgentRegistry
from dawn_kestrel.agents.review.utils.redaction import redact_secrets
from dawn_kestrel.agents.workflow import ReasonOutput
from dawn_kestrel.ai.tool_execution import SessionLifecycleProtocol
from dawn_kestrel.ai_session import AISession
from dawn_kestrel.context.builder import ContextBuilder
from dawn_kestrel.core.agent_types import (
    AgentResult,
    SessionManagerLike,
)
from dawn_kestrel.core.event_bus import Events, bus
from dawn_kestrel.core.models import Session, TextPart, TokenUsage, ToolPart, ToolState
from dawn_kestrel.core.session_lifecycle import SessionLifecycle
from dawn_kestrel.core.settings import settings
from dawn_kestrel.policy import (
    BudgetInfo,
    DefaultPolicyEngine,
    EventSummary,
    HarnessGate,
    PolicyEngine,
    PolicyInput,
    ProposalValidator,
    TodoItem,
)
from dawn_kestrel.policy.router_policy import RouterPolicy
from dawn_kestrel.providers.registry import ProviderRegistry
from dawn_kestrel.tools.framework import ToolRegistry
from dawn_kestrel.tools.permission_filter import ToolPermissionFilter
from dawn_kestrel.tools.cache import ToolResultCache

if TYPE_CHECKING:
    from dawn_kestrel.evaluation.hooks import EvaluationHooks

MAX_TOOL_LOOPS = 10
MAX_TOOL_LOOPS = 10
MAX_TOOL_LOOPS = 10  # Prevent infinite loops

logger = logging.getLogger(__name__)

# FSM State Tracking constants
WORKFLOW_STATES = ["intake", "plan", "reason", "act", "synthesize", "check", "done"]


async def _emit_fsm_state(
    session_id: str,
    agent_name: str,
    state: str,
    data: dict[str, Any] | None = None,
    task_id: str | None = None,
) -> None:
    """Emit an FSM state transition event to the event bus.

    Args:
        session_id: Session ID for correlation
        agent_name: Name of the agent
        state: Current FSM state (intake, plan, reason, act, synthesize, check, done)
        data: Optional data to include with the event
        task_id: Optional task ID for delegation tracking
    """
    event_data: dict[str, Any] = {
        "session_id": session_id,
        "agent_name": agent_name,
        "state": state,
        "timestamp": time.time(),
    }
    if data:
        event_data.update(data)
    if task_id:
        event_data["task_id"] = task_id
    await bus.publish(Events.FSM_STATE_ENTERED, event_data)
    if os.getenv("DK_POLICY_ENGINE", "0") == "1":
        policy_event = dict(event_data)
        policy_event.setdefault("policy_mode", os.getenv("DK_POLICY_MODE", "fsm"))
        await bus.publish(Events.POLICY_STEP_STARTED, policy_event)


class AgentRuntime:
    """Execute agents with tool filtering and lifecycle management."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        base_dir: Path,
        skill_max_char_budget: int | None = None,
        session_lifecycle: SessionLifecycle | None = None,
        provider_registry: ProviderRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        evaluation_hooks: EvaluationHooks | None = None,
        tool_cache: ToolResultCache | None = None,
    ) -> None:
        self.agent_registry = agent_registry
        self.session_lifecycle = session_lifecycle
        self.provider_registry = provider_registry
        self.evaluation_hooks = evaluation_hooks
        self.tool_cache = tool_cache
        self.context_builder = ContextBuilder(
            base_dir=base_dir,
            skill_max_char_budget=skill_max_char_budget,
        )
        self._policy_enabled = os.getenv("DK_POLICY_ENGINE", "0") == "1"
        self._policy_engine = policy_engine or (
            RouterPolicy() if self._policy_enabled else DefaultPolicyEngine()
        )
        self._proposal_validator = ProposalValidator()
        self._harness_gate = HarnessGate()

    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        session_manager: SessionManagerLike,
        tools: ToolRegistry | None,
        skills: list[str],
        options: dict[str, Any] | None = None,
        task_id: str | None = None,
        session_lifecycle: SessionLifecycle | None = None,
    ) -> AgentResult:
        """Execute an agent with tool filtering and lifecycle management."""
        start_time = time.time()
        options = options or {}

        # Step 1: Fetch agent from AgentRegistry
        agent = await self.agent_registry.get_agent(agent_name)
        if not agent:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Agent not found: {agent_name}",
                },
            )
            raise ValueError(f"Agent not found: {agent_name}")

        # Step 2: Load session from SessionManager
        session_or_result = await session_manager.get_session(session_id)

        # Handle both Result[Session | None] and Optional[Session] return types
        # SessionManagerLike protocol says Optional[Session] but DefaultSessionService returns Result
        if hasattr(session_or_result, "is_err"):
            result = session_or_result
            if result.is_err():  # type: ignore[union-attr]
                await bus.publish(
                    Events.AGENT_ERROR,
                    {
                        "session_id": session_id,
                        "agent_name": agent_name,
                        "error": f"Session lookup failed: {result.error}",  # type: ignore[union-attr]
                    },
                )
                raise ValueError(f"Session lookup failed for {session_id}: {result.error}")  # type: ignore[union-attr]
            session = result.unwrap()  # type: ignore[union-attr]
        else:
            session = session_or_result

        if not session:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session not found: {session_id}",
                },
            )
            raise ValueError(f"Session not found: {session_id}")

        assert session is not None  # for type checker
        session = cast(Session, session)

        # Validate session metadata
        if not session.project_id:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session {session_id} has empty project_id",
                },
            )
            raise ValueError(f"Session {session_id} has empty project_id")

        if not session.directory:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session {session_id} has empty directory",
                },
            )
            raise ValueError(f"Session {session_id} has empty directory")

        if not session.title:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session {session_id} has empty title",
                },
            )
            raise ValueError(f"Session {session_id} has empty title")

        # Emit AGENT_INITIALIZED event
        init_event_data: dict[str, Any] = {
            "session_id": session_id,
            "agent_name": agent.name,
            "agent_mode": agent.mode,
        }
        if task_id:
            init_event_data["task_id"] = task_id
        await bus.publish(Events.AGENT_INITIALIZED, init_event_data)

        # Emit session lifecycle event
        lifecycle = session_lifecycle or self.session_lifecycle
        if lifecycle:
            await lifecycle.emit_session_updated(init_event_data)
        logger.info(
            f"Agent {agent.name} initialized for session {session_id}"
            + (f" (task: {task_id})" if task_id else "")
        )

        # FSM INTAKE state will be called after AISession is created
        # (need AISession for LLM-based reasoning)

        try:
            # Step 3: Filter tools via ToolPermissionFilter
            permission_filter = ToolPermissionFilter(
                permissions=agent.permission,
                tool_registry=tools or ToolRegistry(),
            )
            filtered_registry = permission_filter.get_filtered_registry() or ToolRegistry()
            allowed_tool_ids = set(filtered_registry.tools.keys())

            logger.debug(
                f"Filtered tools for {agent.name}: "
                f"{len(allowed_tool_ids)} allowed from {len(tools.tools) if tools else 0} total"
            )

            # Step 4: Build context via ContextBuilder
            agent_dict = {
                "name": agent.name,
                "description": agent.description,
                "mode": agent.mode,
                "permission": agent.permission,
                "prompt": agent.prompt,
                "temperature": agent.temperature,
                "top_p": agent.top_p,
                "model": agent.model,
                "options": agent.options,
                "steps": agent.steps,
            }

            context = await self.context_builder.build_agent_context(
                session=session,
                agent=agent_dict,
                tools=filtered_registry,
                skills=skills,
            )
            _ = context

            # Emit AGENT_READY event
            ready_event_data: dict[str, Any] = {
                "session_id": session_id,
                "agent_name": agent.name,
                "tools_available": len(allowed_tool_ids),
            }
            if task_id:
                ready_event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_READY, ready_event_data)
            logger.info(f"Agent {agent.name} ready for execution")

            # Step 5: Create AISession with filtered tools
            default_account = settings.get_default_account()
            provider_id = options.get(
                "provider",
                default_account.provider_id if default_account else settings.provider_default,
            )
            model = options.get(
                "model", default_account.model if default_account else settings.model_default
            )

            if agent.model:
                model = agent.model.get("model", model)

            lifecycle = session_lifecycle or self.session_lifecycle

            api_key = None
            if self.provider_registry:
                provider_config = await self.provider_registry.get_provider(provider_id)
                if provider_config and provider_config.api_key:
                    api_key = provider_config.api_key
                    if provider_config.model:
                        model = provider_config.model

            if not api_key:
                api_key_secret = settings.get_api_key_for_provider(provider_id)
                if api_key_secret:
                    api_key = api_key_secret.get_secret_value()
            # Resolve lifecycle first (needed for AISession)
            lifecycle = session_lifecycle or self.session_lifecycle

            model = str(model)

            fsm_ai_session = AISession(
                session=session,
                provider_id=provider_id,
                model=model,
                api_key=api_key,
                session_manager=None,
                tool_registry=ToolRegistry(),
                session_lifecycle=None,
                base_dir=self.context_builder.base_dir,
            )

            ai_session = AISession(
                session=session,
                provider_id=provider_id,
                model=model,
                api_key=api_key,
                session_manager=session_manager,
                tool_registry=filtered_registry,
                session_lifecycle=cast(Optional[SessionLifecycleProtocol], lifecycle),
                base_dir=self.context_builder.base_dir,
            )

            # Create FSM Orchestrator for agentic reasoning
            fsm_orchestrator = FSMOrchestrator(
                ai_session=fsm_ai_session,
                session=session,
            )

            # Run INTAKE state with LLM reasoning
            intent_summary = user_message[:200]
            intake_result = await fsm_orchestrator.run_intake(user_message)
            if intake_result:
                intent_summary = intake_result.intent
                cast(Any, fsm_orchestrator)._intent = intake_result.intent
                await fsm_orchestrator.run_plan(
                    intent=intake_result.intent,
                    constraints=intake_result.constraints,
                    evidence=intake_result.initial_evidence,
                    current_todos=fsm_orchestrator.todos,
                )

            # Emit AGENT_EXECUTING event
            executing_event_data: dict[str, Any] = {
                "session_id": session_id,
                "agent_name": agent.name,
                "model": model,
            }
            if task_id:
                executing_event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_EXECUTING, executing_event_data)

            # Emit session lifecycle event
            if lifecycle:
                await lifecycle.emit_session_updated(executing_event_data)

            logger.info(
                f"Executing agent {agent.name} for session {session_id}"
                + (f" (task: {task_id})" if task_id else "")
            )

            execution_options: dict[str, Any] = {
                "temperature": agent.temperature,
                "top_p": agent.top_p,
            }
            execution_options.update(options)

            all_parts: list[Any] = []
            all_tools_used: list[str] = []
            total_tokens = TokenUsage(input=0, output=0, reasoning=0, cache_read=0, cache_write=0)
            response_message = None

            allowed_tools = sorted(allowed_tool_ids)
            tool_signatures = ", ".join(allowed_tools)
            last_tool_summary = ""

            for iteration in range(MAX_TOOL_LOOPS):
                fsm_orchestrator.iteration = iteration + 1
                context_summary = f"Iteration {iteration + 1}/{MAX_TOOL_LOOPS}"

                if self._policy_enabled:
                    policy_input = self._build_policy_input(
                        goal=intent_summary,
                        todos=fsm_orchestrator.todos,
                        iteration=iteration,
                        tools_used=all_tools_used,
                        last_tool_summary=last_tool_summary,
                    )
                    policy_proposal = self._policy_engine.propose(policy_input)
                    validator_result = self._proposal_validator.validate(policy_proposal)
                    gate_result = self._harness_gate.enforce(policy_proposal)

                    await bus.publish(
                        "policy.proposal.decision",
                        {
                            "session_id": session_id,
                            "policy_id": self._policy_engine.__class__.__name__,
                            "proposal_intent": policy_proposal.intent,
                            "risk_level": policy_proposal.risk_level.value,
                            "action_count": len(policy_proposal.actions),
                        },
                    )

                    if not validator_result.valid or not gate_result.valid:
                        rejection = self._parse_rejection_payload(
                            gate_result.errors[0] if gate_result.errors else None
                        )
                        await bus.publish(
                            "policy.proposal.rejection",
                            {
                                "session_id": session_id,
                                "policy_id": rejection["policy_id"],
                                "reason_code": rejection["reason_code"],
                                "blocked_action_type": rejection["blocked_action_type"],
                                "blocked_action_risk": rejection["blocked_action_risk"],
                                "remediation_hints": rejection["remediation_hints"],
                            },
                        )
                        combined_errors = validator_result.errors + gate_result.errors
                        last_tool_summary = "; ".join(combined_errors) or "Policy proposal rejected"
                        fsm_orchestrator.last_tool_result = last_tool_summary
                        break

                    approval_requested = any(
                        action.action_type == "REQUEST_APPROVAL"
                        for action in policy_proposal.actions
                    )
                    if approval_requested:
                        last_tool_summary = (
                            "Policy requested explicit approval before risky actions"
                        )
                        fsm_orchestrator.last_tool_result = last_tool_summary
                        break

                    if "budget exhausted" in policy_proposal.intent.lower():
                        last_tool_summary = policy_proposal.intent
                        fsm_orchestrator.last_tool_result = last_tool_summary
                        break

                reason_output: ReasonOutput | None = await fsm_orchestrator.run_reason(
                    context=context_summary,
                    options={},
                )
                if not reason_output or reason_output.next_phase == "done":
                    break

                act_output = await fsm_orchestrator.run_act_select(
                    reason_output,
                    allowed_tools,
                    tool_signatures,
                )
                if not act_output or not act_output.action:
                    last_tool_summary = "Act selection failed: no tool selected"
                    fsm_orchestrator.last_tool_result = last_tool_summary
                    break

                tool_name = act_output.action.tool_name
                selection_reason = act_output.action.selection_reason.strip()
                if tool_name not in allowed_tool_ids or not selection_reason:
                    failure_text = "Invalid tool selection"
                    act_output.action.status = "failure"
                    act_output.action.result_summary = failure_text
                    act_output.action.duration_seconds = 0.0
                    act_output.tool_result_summary = failure_text
                    act_output.failure = failure_text
                    last_tool_summary = failure_text
                    fsm_orchestrator.last_tool_result = last_tool_summary
                    break

                tool_args = act_output.action.arguments
                tool_call_id = f"fsm_act_{session_id}_{iteration + 1}"
                tool_start = time.monotonic()
                time_start = time.time()
                tool_error: str | None = None
                tool_result_output = ""
                tool_result_metadata: dict[str, Any] = {}
                tool_result_title = ""

                model_name = str(model)
                try:
                    tool_result = await ai_session.tool_manager.execute_tool_call(
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_call_id=tool_call_id,
                        message_id=session_id,
                        agent=agent.name,
                        model=model_name,
                    )
                    tool_duration = time.monotonic() - tool_start
                    time_end = time.time()
                    tool_result_output = tool_result.output
                    tool_result_metadata = tool_result.metadata
                    tool_result_title = tool_result.title
                    result_summary = (
                        tool_result_output[:300] if tool_result_output else tool_result_title
                    )
                    artifacts: list[str] = []
                    metadata_artifacts = tool_result_metadata.get("artifacts")
                    if isinstance(metadata_artifacts, list):
                        artifacts = [str(item) for item in cast(list[object], metadata_artifacts)]
                    attachments = tool_result.attachments or []
                    for attachment in attachments:
                        path_value = attachment.get("path") or attachment.get("filePath")
                        if path_value:
                            artifacts.append(str(path_value))
                    act_output.action.status = "success"
                    act_output.action.result_summary = result_summary
                    act_output.action.duration_seconds = tool_duration
                    act_output.action.artifacts = artifacts
                    act_output.tool_result_summary = result_summary
                    act_output.artifacts = artifacts
                    last_tool_summary = result_summary
                    fsm_orchestrator.last_tool_result = last_tool_summary
                except Exception as exc:
                    tool_duration = time.monotonic() - tool_start
                    time_end = time.time()
                    tool_error = redact_secrets(str(exc))
                    act_output.action.status = "failure"
                    act_output.action.result_summary = tool_error
                    act_output.action.duration_seconds = tool_duration
                    act_output.action.artifacts = []
                    act_output.tool_result_summary = tool_error
                    act_output.artifacts = []
                    act_output.failure = tool_error
                    last_tool_summary = tool_error
                    fsm_orchestrator.last_tool_result = last_tool_summary

                tool_state = ToolState(
                    status="completed" if not tool_error else "error",
                    input=tool_args,
                    output=tool_result_output or tool_error,
                    title=tool_result_title or ("Error" if tool_error else "Tool Result"),
                    metadata=tool_result_metadata if tool_result_metadata else {},
                    time_start=time_start,
                    time_end=time_end,
                    error=tool_error,
                )
                tool_part = ToolPart(
                    id=f"{session_id}_{tool_call_id}",
                    session_id=session_id,
                    message_id=session_id,
                    part_type="tool",
                    tool=tool_name,
                    call_id=tool_call_id,
                    state=tool_state,
                    source={"provider": model_name},
                )
                all_parts.append(tool_part)
                all_tools_used.append(tool_name)

                if self.evaluation_hooks:
                    self.evaluation_hooks.emit_tool_call(
                        tool=tool_name,
                        input=tool_args,
                        output=tool_result_output or tool_error or "",
                    )
                tool_results_data = [
                    {"tool": tool_name, "output": tool_result_output or tool_error or ""}
                ]
                await fsm_orchestrator.run_synthesize(tool_results_data)
                check_result = await fsm_orchestrator.run_check(
                    all_todos=fsm_orchestrator.todos,
                    completed_todos=[
                        todo for todo in fsm_orchestrator.todos if todo.get("status") == "completed"
                    ],
                    pending_todos=[
                        todo for todo in fsm_orchestrator.todos if todo.get("status") != "completed"
                    ],
                )
                if check_result and check_result.next_phase == "done":
                    break

            completed_todos = [
                todo for todo in fsm_orchestrator.todos if todo.get("status") == "completed"
            ]
            completed_lines = [
                f"- {str(todo.get('id', ''))}: {str(todo.get('description', ''))}"
                for todo in completed_todos
            ]
            if not completed_lines:
                completed_lines = ["- none"]

            findings = [
                str(item) for item in fsm_orchestrator.evidence if str(item).startswith("finding:")
            ]
            finding_lines = [f"- {finding}" for finding in findings]
            if not finding_lines:
                finding_lines = ["- none"]

            intent_text = intent_summary
            summary_message = "\n".join(
                [
                    f"Intent: {intent_text}",
                    "Completed todos:",
                    *completed_lines,
                    "Findings:",
                    *finding_lines,
                    f"Last tool result: {last_tool_summary or 'none'}",
                    "Provide the final response to the user now. Do not call tools.",
                ]
            )
            response_message = await ai_session.process_message(
                user_message=summary_message,
                options={**execution_options, "disable_tools": True},
            )
            all_parts.extend(response_message.parts or [])
            for part in response_message.parts or []:
                if isinstance(part, ToolPart) and part.tool not in all_tools_used:
                    all_tools_used.append(part.tool)
            if response_message.metadata and "tokens" in response_message.metadata:
                tokens_data = response_message.metadata["tokens"]
                total_tokens.input += tokens_data.get("input", 0)
                total_tokens.output += tokens_data.get("output", 0)
                total_tokens.reasoning += tokens_data.get("reasoning", 0)
                total_tokens.cache_read += tokens_data.get("cache_read", 0)
                total_tokens.cache_write += tokens_data.get("cache_write", 0)

            response_text = response_message.text or ""
            if not response_text:
                response_text_parts: list[str] = []
                for part in response_message.parts or []:
                    if isinstance(part, TextPart) and part.text:
                        response_text_parts.append(str(part.text))
                response_text = "".join(response_text_parts)

            tools_used = all_tools_used
            tokens_used = total_tokens

            duration = time.time() - start_time

            # Step 7: Emit AGENT_CLEANUP event
            cleanup_event_data: dict[str, Any] = {
                "session_id": session_id,
                "agent_name": agent.name,
                "messages_count": 1,
                "tools_used": tools_used,
                "duration": duration,
            }
            if task_id:
                cleanup_event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_CLEANUP, cleanup_event_data)

            logger.info(
                f"Agent {agent.name} execution complete in {duration:.2f}s, "
                f"tokens: {tokens_used.input + tokens_used.output if tokens_used else 0}, "
                f"tools: {len(tools_used)}"
            )

            await _emit_fsm_state(
                session_id=session_id,
                agent_name=agent.name,
                state="done",
                data={
                    "duration_seconds": duration,
                    "tools_used_count": len(tools_used),
                    "tokens_used": tokens_used.input + tokens_used.output if tokens_used else 0,
                    "response_length": len(response_text),
                },
                task_id=task_id,
            )

            if self.evaluation_hooks:
                self.evaluation_hooks.emit_phase(
                    "agent_complete",
                    {
                        "agent_name": agent.name,
                        "duration_seconds": duration,
                        "tools_used_count": len(tools_used),
                        "success": True,
                    },
                )
            return AgentResult(
                agent_name=agent.name,
                response=response_text,
                parts=all_parts,
                metadata=response_message.metadata or {},
                tools_used=tools_used,
                tokens_used=tokens_used,
                duration=duration,
                error=None,
                task_id=task_id,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            logger.error(f"Agent execution failed: {error_msg}")

            # Emit AGENT_ERROR event
            error_event_data: dict[str, Any] = {
                "session_id": session_id,
                "agent_name": agent.name,
                "error": error_msg,
                "duration": duration,
            }
            if task_id:
                error_event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_ERROR, error_event_data)

            # Return AgentResult with error and task_id
            return AgentResult(
                agent_name=agent.name,
                response=f"Error: {error_msg}",
                parts=[],
                metadata={"error": error_msg},
                tools_used=[],
                tokens_used=None,
                duration=duration,
                error=error_msg,
                task_id=task_id,
            )

    def _build_policy_input(
        self,
        goal: str,
        todos: list[dict[str, Any]],
        iteration: int,
        tools_used: list[str],
        last_tool_summary: str,
    ) -> PolicyInput:
        policy_todos: list[TodoItem] = []
        for todo in todos:
            status = str(todo.get("status", "pending"))
            if status not in {"pending", "in_progress", "completed", "blocked", "skipped"}:
                status = "pending"
            priority = str(todo.get("priority", "medium"))
            if priority not in {"high", "medium", "low"}:
                priority = "medium"
            typed_status = cast(
                Literal["pending", "in_progress", "completed", "blocked", "skipped"],
                status,
            )
            typed_priority = cast(Literal["high", "medium", "low"], priority)
            policy_todos.append(
                TodoItem(
                    id=str(todo.get("id", "")),
                    description=str(todo.get("description", "")),
                    status=typed_status,
                    priority=typed_priority,
                )
            )

        last_events: list[EventSummary] = []
        if last_tool_summary:
            last_events.append(
                EventSummary(
                    event_type="tool_result",
                    timestamp=str(time.time()),
                    summary=last_tool_summary[:200],
                )
            )

        return PolicyInput(
            goal=goal,
            active_todos=policy_todos,
            last_events=last_events,
            budgets=BudgetInfo(
                iterations_consumed=iteration,
                max_iterations=MAX_TOOL_LOOPS,
                tool_calls_consumed=len(tools_used),
            ),
        )

    @staticmethod
    def _parse_rejection_payload(payload: str | None) -> dict[str, Any]:
        if not payload:
            return {
                "policy_id": "harness_invariants",
                "reason_code": "POLICY_REJECTED",
                "blocked_action_type": "UNKNOWN",
                "blocked_action_risk": "LOW",
                "remediation_hints": ["Revise proposal to satisfy validator and harness gates"],
            }

        try:
            parsed = cast(dict[str, Any], json.loads(payload))
        except Exception:
            return {
                "policy_id": "harness_invariants",
                "reason_code": "POLICY_REJECTED",
                "blocked_action_type": "UNKNOWN",
                "blocked_action_risk": "LOW",
                "remediation_hints": [payload],
            }

        return {
            "policy_id": str(parsed.get("policy_id", "harness_invariants")),
            "reason_code": str(parsed.get("reason_code", "POLICY_REJECTED")),
            "blocked_action_type": str(parsed.get("blocked_action_type", "UNKNOWN")),
            "blocked_action_risk": str(parsed.get("blocked_action_risk", "LOW")),
            "remediation_hints": list(parsed.get("remediation_hints", [])),
        }


def create_agent_runtime(
    agent_registry: AgentRegistry,
    base_dir: Path,
    skill_max_char_budget: int | None = None,
    session_lifecycle: SessionLifecycle | None = None,
    provider_registry: ProviderRegistry | None = None,
    policy_engine: PolicyEngine | None = None,
    evaluation_hooks: EvaluationHooks | None = None,
    tool_cache: ToolResultCache | None = None,
) -> AgentRuntime:
    return AgentRuntime(
        agent_registry=agent_registry,
        base_dir=base_dir,
        skill_max_char_budget=skill_max_char_budget,
        session_lifecycle=session_lifecycle,
        provider_registry=provider_registry,
        policy_engine=policy_engine,
        evaluation_hooks=evaluation_hooks,
        tool_cache=tool_cache,
    )
