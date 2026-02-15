"""Workflow FSM for agent-based orchestration loop.

This module implements a concrete workflow FSM whose states are:
intake → plan → act → synthesize → check → (plan or done)

Each phase is an LLM prompt-driven execution through AgentRuntime.execute_agent():
- intake: Extracts intent/constraints/evidence
- plan: Generates/modifies/prioritizes todos
- act: Performs tool-using work against prioritized todos
- synthesize: Merges results and updates todo statuses
- check: Decides whether to continue loop or stop (with stop conditions)

The FSM enforces hard budgets regardless of LLM output and stores
workflow context across iterations (todos, evidence, iteration count, budgets).

Stop conditions enforced:
- success/intent met
- stagnation (no new info, same error signature)
- budget exhausted (iterations, tool calls, wall time)
- human required (blocking question, ambiguous requirement)
- risk threshold exceeded
"""

from __future__ import annotations

import asyncio
import logging
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable

from pydantic import ValidationError

from dawn_kestrel.core.fsm import (
    FSM,
    FSMBuilder,
    FSMContext,
    FSMReliabilityConfig,
)
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.core.mediator import EventMediator, EventType
from dawn_kestrel.core.agent_task import AgentTask, TaskStatus, create_agent_task
from dawn_kestrel.core.agent_types import SessionManagerLike
from dawn_kestrel.agents.runtime import AgentRuntime
from dawn_kestrel.tools.framework import ToolRegistry
from dawn_kestrel.agents.workflow import (
    IntakeOutput,
    PlanOutput,
    ActOutput,
    SynthesizeOutput,
    CheckOutput,
    TodoItem,
    BudgetConsumed,
    get_intake_output_schema,
    get_plan_output_schema,
    get_act_output_schema,
    get_synthesize_output_schema,
    get_check_output_schema,
)

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """States for the workflow FSM."""

    INTAKE = "intake"
    PLAN = "plan"
    ACT = "act"
    SYNTHESIZE = "synthesize"
    CHECK = "check"
    DONE = "done"


class StopReason(str, Enum):
    """Canonical stop reasons for workflow execution."""

    SUCCESS = "recommendation_ready"
    BUDGET_EXHAUSTED = "budget_exhausted"
    STAGNATION = "stagnation"
    HUMAN_REQUIRED = "human_required"
    BLOCKING_QUESTION = "blocking_question"
    RISK_THRESHOLD = "risk_threshold"
    NONE = "none"


@dataclass
class WorkflowBudget:
    """Budget limits for workflow execution.

    These are hard limits enforced by the FSM regardless of LLM output.
    """

    max_iterations: int = 10
    """Maximum number of iterations before forced stop."""

    max_tool_calls: int = 100
    """Maximum number of tool calls before forced stop."""

    max_wall_time_seconds: float = 600.0
    """Maximum wall time in seconds before forced stop."""

    max_subagent_calls: int = 20
    """Maximum number of subagent calls before forced stop."""


@dataclass
class WorkflowContext:
    """Context stored across workflow iterations.

    Maintains state between FSM transitions including todos,
    evidence, iteration count, budgets consumed, and novelty tracking.
    """

    # Core workflow state
    intent: str = ""
    """Original intent from intake phase."""

    constraints: List[str] = field(default_factory=list)
    """Constraints identified during intake."""

    initial_evidence: List[str] = field(default_factory=list)
    """Initial evidence snapshot from intake."""

    # Todo tracking (using AgentTask as substrate)
    todos: Dict[str, AgentTask] = field(default_factory=dict)
    """Active todos indexed by task_id."""

    current_todo_id: str = ""
    """ID of the todo currently being worked on."""

    # Evidence tracking
    evidence: List[str] = field(default_factory=list)
    """Accumulated evidence across iterations."""

    findings: List[Dict[str, Any]] = field(default_factory=list)
    """Findings discovered during execution."""

    artifacts: List[str] = field(default_factory=list)
    """Artifacts created (files, outputs, etc.)."""

    # Iteration tracking
    iteration_count: int = 0
    """Number of iterations executed."""

    last_iteration_state: str = ""
    """State where last iteration started."""

    # Budget tracking
    budget_consumed: BudgetConsumed = field(default_factory=BudgetConsumed)
    """Resources consumed so far."""

    # Novelty tracking (for stagnation detection)
    last_novelty_signature: str = ""
    """Hash of evidence from last iteration to detect stagnation."""

    stagnation_count: int = 0
    """Number of consecutive iterations with no new information."""

    # Phase outputs (for debugging/analysis)
    last_intake_output: Optional[IntakeOutput] = None
    last_plan_output: Optional[PlanOutput] = None
    last_act_output: Optional[ActOutput] = None
    last_synthesize_output: Optional[SynthesizeOutput] = None
    last_check_output: Optional[CheckOutput] = None

    # Start time for wall time tracking
    start_time: float = field(default_factory=time.time)
    """When workflow execution started."""

    def compute_novelty_signature(self, evidence: List[str]) -> str:
        """Compute a hash signature for evidence to detect novelty.

        Args:
            evidence: List of evidence strings to hash.

        Returns:
            SHA256 hash of evidence for comparison.
        """
        evidence_str = "|".join(sorted(evidence))
        return hashlib.sha256(evidence_str.encode()).hexdigest()

    def update_evidence(self, new_evidence: List[str]) -> bool:
        """Update evidence and check for novelty.

        Args:
            new_evidence: New evidence to add.

        Returns:
            True if new information detected (novelty), False otherwise.
        """
        signature = self.compute_novelty_signature(new_evidence + self.evidence)

        if signature == self.last_novelty_signature:
            # No new evidence - stagnation detected
            self.stagnation_count += 1
            return False

        # New information detected
        self.evidence.extend(new_evidence)
        self.last_novelty_signature = signature
        self.stagnation_count = 0
        return True

    def get_wall_time_seconds(self) -> float:
        """Get elapsed wall time in seconds."""
        return time.time() - self.start_time


@dataclass
class WorkflowConfig:
    """Configuration for workflow FSM execution."""

    # Agent configuration
    agent_name: str = "workflow"
    """Name of agent to use for all phases."""

    session_id: str = ""
    """Session ID for AgentRuntime."""

    # Tool/skill configuration
    tool_ids: List[str] = field(default_factory=list)
    """Tool IDs available to workflow."""

    skill_names: List[str] = field(default_factory=list)
    """Skill names to inject into context."""

    options: Dict[str, Any] = field(default_factory=dict)
    """Additional execution options (model, temperature, etc.)."""

    # Session and tools
    session_manager: Optional[SessionManagerLike] = None
    """SessionManager for session operations."""

    tools: Optional[ToolRegistry] = None
    """Tool registry for workflow execution."""

    # Budget limits
    budget: WorkflowBudget = field(default_factory=WorkflowBudget)
    """Budget limits for workflow execution."""

    # Stop condition thresholds
    stagnation_threshold: int = 3
    """Number of consecutive iterations without novelty before stop."""

    confidence_threshold: float = 0.8
    """Minimum confidence for success stop."""

    # Risk assessment
    max_risk_level: str = "high"
    """Maximum acceptable risk level (critical, high, medium, low)."""


class WorkflowFSM:
    """Workflow FSM for agent-based orchestration loop.

    Implements the intake → plan → act → synthesize → check → done
    loop with stop condition enforcement and budget tracking.

    Each phase is executed as an LLM prompt through AgentRuntime.execute_agent(),
    with structured output parsed via Pydantic contracts from workflow.py.

    The FSM enforces hard budgets regardless of LLM output and maintains
    workflow context across iterations.
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        config: WorkflowConfig,
        fsm_id: Optional[str] = None,
        mediator: Optional[EventMediator] = None,
    ):
        """Initialize workflow FSM.

        Args:
            runtime: AgentRuntime instance for executing phases.
            config: WorkflowConfig with session, tools, budgets, etc.
            fsm_id: Optional unique identifier for this FSM instance.
            mediator: Optional EventMediator for emitting transition events.
        """
        self.runtime = runtime
        self.config = config
        self._fsm_id = fsm_id or f"workflow_fsm_{id(self)}"
        self._mediator = mediator

        # Initialize workflow context
        self.context = WorkflowContext()

        # Build the FSM with states and transitions
        self._fsm = self._build_fsm()

        # Phase execution state
        self._phase_executors = {
            WorkflowState.INTAKE: self._execute_intake_phase,
            WorkflowState.PLAN: self._execute_plan_phase,
            WorkflowState.ACT: self._execute_act_phase,
            WorkflowState.SYNTHESIZE: self._execute_synthesize_phase,
            WorkflowState.CHECK: self._execute_check_phase,
        }

    def _build_fsm(self) -> FSM:
        builder = (
            FSMBuilder()
            .with_state(WorkflowState.INTAKE)
            .with_state(WorkflowState.PLAN)
            .with_state(WorkflowState.ACT)
            .with_state(WorkflowState.SYNTHESIZE)
            .with_state(WorkflowState.CHECK)
            .with_state(WorkflowState.DONE)
            # Linear flow: intake → plan → act → synthesize → check
            .with_transition(WorkflowState.INTAKE, WorkflowState.PLAN)
            .with_transition(
                WorkflowState.INTAKE, WorkflowState.DONE
            )  # Early termination on intake failure
            .with_transition(WorkflowState.PLAN, WorkflowState.ACT)
            .with_transition(
                WorkflowState.PLAN, WorkflowState.DONE
            )  # Early termination on plan failure
            .with_transition(WorkflowState.ACT, WorkflowState.SYNTHESIZE)
            .with_transition(WorkflowState.SYNTHESIZE, WorkflowState.CHECK)
            # Routing from CHECK phase:
            # - check → act (continue current todo)
            # - check → plan (todo complete, pick next)
            # - check → done (all todos complete)
            .with_transition(WorkflowState.CHECK, WorkflowState.ACT)
            .with_transition(WorkflowState.CHECK, WorkflowState.PLAN)
            .with_transition(WorkflowState.CHECK, WorkflowState.DONE)
        )

        if self._mediator is not None:
            for state in WorkflowState:
                builder = builder.with_entry_hook(
                    state.value,
                    lambda ctx, s=state.value: self._emit_transition_event(to_state=s, context=ctx),
                )

        result = builder.build(initial_state=WorkflowState.INTAKE)
        if result.is_err():
            raise ValueError(f"Failed to build workflow FSM: {result.error}")

        return result.unwrap()

    async def get_state(self) -> str:
        """Get current workflow FSM state."""
        return await self._fsm.get_state()

    async def transition_to(self, new_state: str) -> Result[None]:
        """Transition workflow FSM to new state."""
        return await self._fsm.transition_to(new_state)

    def _emit_transition_event(self, to_state: str, context: FSMContext) -> Result[None]:
        """Emit FSM transition event via EventMediator.

        Args:
            to_state: The state being transitioned to.
            context: FSMContext for the transition.

        Returns:
            Result[None] on success.
        """
        if self._mediator is None:
            return Ok(None)

        try:
            from dawn_kestrel.core.mediator import Event
            import datetime

            event = Event(
                event_type=EventType.DOMAIN,
                source=f"WorkflowFSM:{self._fsm_id}",
                data={
                    "fsm_id": self._fsm_id,
                    "from_state": context.get("previous_state")
                    if isinstance(context, dict)
                    else "unknown",
                    "to_state": to_state,
                    "timestamp": datetime.datetime.now().isoformat(),
                },
            )

            asyncio.create_task(self._mediator.publish(event))
            return Ok(None)
        except Exception as e:
            logger.warning(f"Failed to emit FSM transition event: {e}")
            return Ok(None)

    async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        """Check if transition is valid."""
        return await self._fsm.is_transition_valid(from_state, to_state)

    async def run(self) -> Result[Dict[str, Any]]:
        """Run the workflow FSM until completion.

        Executes the workflow loop: intake → plan → act → synthesize → check
        repeating until stop conditions are met, then transitions to done.

        Returns:
            Result with workflow execution summary including stop_reason,
            final_context, and phase outputs.
        """
        logger.info(f"Starting workflow FSM {self._fsm_id}")

        try:
            # Main workflow loop
            while True:
                current_state = await self.get_state()
                logger.info(f"Workflow state: {current_state}")

                # Execute phase based on current state
                if current_state in self._phase_executors:
                    executor = self._phase_executors[current_state]
                    phase_result = await executor()

                    if phase_result.is_err():
                        logger.error(f"Phase {current_state} failed: {phase_result.error}")
                        # Transition to done on error
                        await self.transition_to(WorkflowState.DONE)
                        return Err(f"Workflow failed at {current_state}: {phase_result.error}")

                # Check if we're done
                if await self.get_state() == WorkflowState.DONE:
                    logger.info("Workflow completed successfully")
                    return Ok(self._build_final_result())

                # Safety break to prevent infinite loops
                if self.context.iteration_count > self.config.budget.max_iterations * 2:
                    logger.warning("Workflow exceeded max iterations, forcing stop")
                    await self.transition_to(WorkflowState.DONE)
                    return Err("Workflow exceeded max iteration limit")

        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            await self.transition_to(WorkflowState.DONE)
            return Err(f"Workflow error: {e}")

    async def _execute_intake_phase(self) -> Result[None]:
        """Execute intake phase: extract intent/constraints/evidence.

        Prompts LLM with initial user message and extracts intent,
        constraints, and initial evidence snapshot.

        Returns:
            Result[None] on success, Err on failure.
        """
        logger.info("Executing intake phase")

        prompt = f"""You are in the INTAKE phase of a workflow loop.

Your task:
1. Understand the user's request
2. Identify constraints (tools, permissions, time, scope boundaries)
3. Capture initial evidence from context

{get_intake_output_schema()}

User request: {self.config.options.get("user_message", "No user message provided")}

Respond with ONLY valid JSON matching the schema above.
"""

        result = await self.runtime.execute_agent(
            agent_name=self.config.agent_name,
            session_id=self.config.session_id,
            user_message=prompt,
            session_manager=self.config.session_manager,
            tools=self.config.tools,
            skills=self.config.skill_names,
            options=self.config.options,
        )

        if result.error:
            return Err(f"Intake phase execution failed: {result.error}")

        try:
            # Parse JSON output
            output_json = self._extract_json_from_response(result.response)
            intake_output = IntakeOutput(**output_json)

            # Store in context
            self.context.intent = intake_output.intent
            self.context.constraints = intake_output.constraints
            self.context.initial_evidence = intake_output.initial_evidence
            self.context.last_intake_output = intake_output

            logger.info(f"Intake complete: intent={intake_output.intent}")

            # Transition to next phase
            return await self.transition_to(WorkflowState.PLAN)

        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse intake output: {e}")
            return Err(f"Intake phase failed to parse LLM output: {e}")

    async def _execute_plan_phase(self) -> Result[None]:
        logger.info("Executing plan phase")

        context_summary = self._build_context_summary()

        prompt = f"""You are in the PLAN phase of a workflow loop.

Your task:
1. Review current context and existing todos
2. Generate new todos or modify existing ones
3. Prioritize todos (high, medium, low)
4. The system will work on ONE todo at a time

Current workflow context:
{context_summary}

{get_plan_output_schema()}

Respond with ONLY valid JSON matching the schema above.
"""

        result = await self.runtime.execute_agent(
            agent_name=self.config.agent_name,
            session_id=self.config.session_id,
            user_message=prompt,
            session_manager=self.config.session_manager,
            tools=self.config.tools,
            skills=self.config.skill_names,
            options=self.config.options,
        )

        if result.error:
            return Err(f"Plan phase execution failed: {result.error}")

        try:
            output_json = self._extract_json_from_response(result.response)
            plan_output = PlanOutput(**output_json)

            for todo_item in plan_output.todos:
                if todo_item.id not in self.context.todos:
                    agent_task = create_agent_task(
                        agent_name=self.config.agent_name,
                        description=todo_item.description,
                        tool_ids=self.config.tool_ids,
                        skill_names=self.config.skill_names,
                        options=self.config.options,
                        metadata={
                            "priority": todo_item.priority,
                            "operation": todo_item.operation,
                            "notes": todo_item.notes,
                            "dependencies": todo_item.dependencies,
                        },
                    )
                    self.context.todos[todo_item.id] = agent_task
                else:
                    existing_task = self.context.todos[todo_item.id]
                    existing_task.description = todo_item.description
                    existing_task.metadata["priority"] = todo_item.priority
                    existing_task.metadata["operation"] = todo_item.operation
                    existing_task.metadata["notes"] = todo_item.notes
                    existing_task.metadata["dependencies"] = todo_item.dependencies
                    if existing_task.status != TaskStatus.RUNNING:
                        existing_task.status = TaskStatus.PENDING

            self.context.last_plan_output = plan_output

            # Select ONE todo to work on, favoring in-progress over pending
            selected_todo_id = self._select_next_todo()
            if selected_todo_id:
                self.context.current_todo_id = selected_todo_id
                self.context.todos[selected_todo_id].status = TaskStatus.RUNNING
                logger.info(f"Plan complete: selected todo {selected_todo_id}")
            else:
                logger.info("Plan complete: no pending todos")

            return await self.transition_to(WorkflowState.ACT)

        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse plan output: {e}")
            return Err(f"Plan phase failed to parse LLM output: {e}")

    def _select_next_todo(self) -> Optional[str]:
        # Priority 1: Resume in-progress (RUNNING) todos
        for tid, task in self.context.todos.items():
            if task.status == TaskStatus.RUNNING:
                return tid

        # Priority 2: Pick highest priority PENDING todo
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending = [
            (tid, task)
            for tid, task in self.context.todos.items()
            if task.status == TaskStatus.PENDING
        ]
        if not pending:
            return None

        pending.sort(key=lambda x: priority_order.get(x[1].metadata.get("priority", "medium"), 3))
        return pending[0][0]

    async def _execute_act_phase(self) -> Result[None]:
        logger.info("Executing act phase")

        if (
            not self.context.current_todo_id
            or self.context.current_todo_id not in self.context.todos
        ):
            logger.info("No current todo selected, skipping act phase")
            self.context.last_act_output = ActOutput()
            return await self.transition_to(WorkflowState.SYNTHESIZE)

        current_task = self.context.todos[self.context.current_todo_id]

        prompt = f"""You are in the ACT phase of a workflow loop.

SINGLE ACTION CONSTRAINT: Perform exactly ONE tool call this iteration.

Current todo:
- ID: {self.context.current_todo_id}
- Description: {current_task.description}
- Priority: {current_task.metadata.get("priority", "medium")}
- Notes: {current_task.metadata.get("notes", "")}

{get_act_output_schema()}

Respond with ONLY valid JSON matching the schema above.
"""

        result = await self.runtime.execute_agent(
            agent_name=self.config.agent_name,
            session_id=self.config.session_id,
            user_message=prompt,
            session_manager=self.config.session_manager,
            tools=self.config.tools,
            skills=self.config.skill_names,
            options=self.config.options,
        )

        if result.error:
            return Err(f"Act phase execution failed: {result.error}")

        try:
            output_json = self._extract_json_from_response(result.response)
            act_output = ActOutput(**output_json)

            self.context.budget_consumed.tool_calls += 1 if act_output.action else 0
            self.context.artifacts.extend(act_output.artifacts)

            if act_output.action and act_output.action.status == "success":
                new_evidence = [
                    f"{act_output.action.tool_name}: {act_output.action.result_summary}"
                ]
                self.context.update_evidence(new_evidence)

            self.context.last_act_output = act_output

            logger.info(
                f"Act complete: tool={act_output.action.tool_name if act_output.action else 'none'}"
            )

            return await self.transition_to(WorkflowState.SYNTHESIZE)

        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse act output: {e}")
            return Err(f"Act phase failed to parse LLM output: {e}")

    async def _execute_synthesize_phase(self) -> Result[None]:
        logger.info("Executing synthesize phase")

        act_summary = ""
        if self.context.last_act_output:
            action = self.context.last_act_output.action
            if action:
                act_summary = f"""
Tool Result:
- Tool: {action.tool_name}
- Status: {action.status}
- Summary: {action.result_summary}
- Artifacts: {", ".join(action.artifacts) if action.artifacts else "none"}
"""
            if self.context.last_act_output.failure:
                act_summary += f"\nFailure: {self.context.last_act_output.failure}"

        prompt = f"""You are in the SYNTHESIZE phase of a workflow loop.

Your task:
1. Review the tool result from the ACT phase
2. Merge findings into the overall context
3. Summarize what was learned

Current todo: {self.context.current_todo_id}
{act_summary}

{get_synthesize_output_schema()}

Respond with ONLY valid JSON matching the schema above.
"""

        result = await self.runtime.execute_agent(
            agent_name=self.config.agent_name,
            session_id=self.config.session_id,
            user_message=prompt,
            session_manager=self.config.session_manager,
            tools=self.config.tools,
            skills=self.config.skill_names,
            options=self.config.options,
        )

        if result.error:
            return Err(f"Synthesize phase execution failed: {result.error}")

        try:
            output_json = self._extract_json_from_response(result.response)
            synthesize_output = SynthesizeOutput(**output_json)

            for finding in synthesize_output.findings:
                self.context.findings.append(finding.model_dump())

            self.context.last_synthesize_output = synthesize_output

            self.context.iteration_count += 1
            self.context.budget_consumed.iterations = self.context.iteration_count

            logger.info(f"Synthesize complete: {len(synthesize_output.findings)} findings")

            return await self.transition_to(WorkflowState.CHECK)

        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse synthesize output: {e}")
            return Err(f"Synthesize phase failed to parse LLM output: {e}")

    async def _execute_check_phase(self) -> Result[None]:
        logger.info("Executing check phase")

        self.context.budget_consumed.wall_time_seconds = self.context.get_wall_time_seconds()

        if not self.context.current_todo_id:
            pending_count = sum(
                1 for t in self.context.todos.values() if t.status == TaskStatus.PENDING
            )
            if pending_count == 0:
                logger.info("Check complete: no todos, done")
                return await self.transition_to(WorkflowState.DONE)
            else:
                logger.info("Check complete: no current todo, routing to plan")
                return await self.transition_to(WorkflowState.PLAN)

        current_task = self.context.todos.get(self.context.current_todo_id)
        if not current_task:
            logger.warning(f"Current todo {self.context.current_todo_id} not found")
            return await self.transition_to(WorkflowState.PLAN)

        pending_count = sum(
            1
            for t in self.context.todos.values()
            if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        )

        prompt = f"""You are in the CHECK phase of a workflow loop.

Your task:
1. Evaluate if the current todo is complete
2. Decide where to route next:
   - "act": Continue working on current todo (todo_complete=false)
   - "plan": Todo complete, pick next todo (todo_complete=true, more todos pending)
   - "done": All todos complete (todo_complete=true, no more todos)

Current todo:
- ID: {self.context.current_todo_id}
- Description: {current_task.description}
- Status: {current_task.status.value}

Todo summary:
- Total todos: {len(self.context.todos)}
- Pending/Running: {pending_count}

Recent tool result:
{self._format_last_action()}

Budget consumed:
- Iterations: {self.context.budget_consumed.iterations}/{self.config.budget.max_iterations}
- Tool calls: {self.context.budget_consumed.tool_calls}/{self.config.budget.max_tool_calls}
- Wall time: {self.context.budget_consumed.wall_time_seconds:.1f}/{self.config.budget.max_wall_time_seconds}s

Stagnation: {self.context.stagnation_count}/{self.config.stagnation_threshold}

{get_check_output_schema()}

Respond with ONLY valid JSON matching the schema above.
"""

        result = await self.runtime.execute_agent(
            agent_name=self.config.agent_name,
            session_id=self.config.session_id,
            user_message=prompt,
            session_manager=self.config.session_manager,
            tools=self.config.tools,
            skills=self.config.skill_names,
            options=self.config.options,
        )

        if result.error:
            return Err(f"Check phase execution failed: {result.error}")

        try:
            output_json = self._extract_json_from_response(result.response)
            check_output = CheckOutput(**output_json)

            final_decision = self._enforce_hard_budgets(check_output)
            self.context.last_check_output = final_decision

            if final_decision.todo_complete:
                self.context.todos[self.context.current_todo_id].status = TaskStatus.COMPLETED
                self.context.current_todo_id = ""

            next_phase = final_decision.next_phase
            logger.info(
                f"Check complete: todo_complete={final_decision.todo_complete}, routing to {next_phase}"
            )

            if next_phase == "done":
                return await self.transition_to(WorkflowState.DONE)
            elif next_phase == "plan":
                return await self.transition_to(WorkflowState.PLAN)
            else:
                return await self.transition_to(WorkflowState.ACT)

        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse check output: {e}")
            return Err(f"Check phase failed to parse LLM output: {e}")

    def _format_last_action(self) -> str:
        if not self.context.last_act_output or not self.context.last_act_output.action:
            return "No action in this iteration"
        action = self.context.last_act_output.action
        return (
            f"- Tool: {action.tool_name}, Status: {action.status}, Result: {action.result_summary}"
        )

    def _enforce_hard_budgets(self, check_output: CheckOutput) -> CheckOutput:
        if self.context.iteration_count >= self.config.budget.max_iterations:
            logger.warning(f"Budget exceeded: max_iterations ({self.config.budget.max_iterations})")
            return CheckOutput(
                current_todo_id=check_output.current_todo_id,
                todo_complete=True,
                next_phase="done",
                confidence=check_output.confidence,
                budget_consumed=check_output.budget_consumed,
                novelty_detected=False,
                stagnation_detected=True,
                reasoning="Budget exhausted: max iterations reached",
            )

        if self.context.budget_consumed.tool_calls >= self.config.budget.max_tool_calls:
            logger.warning(f"Budget exceeded: max_tool_calls ({self.config.budget.max_tool_calls})")
            return CheckOutput(
                current_todo_id=check_output.current_todo_id,
                todo_complete=True,
                next_phase="done",
                confidence=check_output.confidence,
                budget_consumed=check_output.budget_consumed,
                novelty_detected=False,
                stagnation_detected=True,
                reasoning="Budget exhausted: max tool calls reached",
            )

        if (
            self.context.budget_consumed.wall_time_seconds
            >= self.config.budget.max_wall_time_seconds
        ):
            logger.warning(
                f"Budget exceeded: max_wall_time_seconds ({self.config.budget.max_wall_time_seconds})"
            )
            return CheckOutput(
                current_todo_id=check_output.current_todo_id,
                todo_complete=True,
                next_phase="done",
                confidence=check_output.confidence,
                budget_consumed=check_output.budget_consumed,
                novelty_detected=False,
                stagnation_detected=True,
                reasoning="Budget exhausted: max wall time reached",
            )

        if self.context.stagnation_count >= self.config.stagnation_threshold:
            logger.warning(
                f"Stagnation detected: {self.context.stagnation_count} iterations without novelty"
            )
            return CheckOutput(
                current_todo_id=check_output.current_todo_id,
                todo_complete=True,
                next_phase="plan",
                confidence=check_output.confidence,
                budget_consumed=check_output.budget_consumed,
                novelty_detected=False,
                stagnation_detected=True,
                reasoning="Stagnation: switching strategy",
            )

        if check_output.blocking_question:
            logger.warning("Blocking question detected")
            return CheckOutput(
                current_todo_id=check_output.current_todo_id,
                todo_complete=False,
                next_phase="done",
                confidence=check_output.confidence,
                budget_consumed=check_output.budget_consumed,
                novelty_detected=check_output.novelty_detected,
                stagnation_detected=check_output.stagnation_detected,
                blocking_question=check_output.blocking_question,
                reasoning=f"Blocking question: {check_output.blocking_question}",
            )

        if self._risk_threshold_exceeded():
            logger.warning(f"Risk threshold exceeded: max allowed is {self.config.max_risk_level}")
            return CheckOutput(
                current_todo_id=check_output.current_todo_id,
                todo_complete=True,
                next_phase="done",
                confidence=check_output.confidence,
                budget_consumed=check_output.budget_consumed,
                novelty_detected=check_output.novelty_detected,
                stagnation_detected=check_output.stagnation_detected,
                reasoning="Risk threshold exceeded",
            )

        return check_output

    def _risk_threshold_exceeded(self) -> bool:
        """Check if risk threshold is exceeded.

        Returns:
            True if any finding exceeds max_risk_level, False otherwise.
        """
        risk_levels = {"critical": 3, "high": 2, "medium": 1, "low": 0, "info": 0}
        max_allowed = risk_levels.get(self.config.max_risk_level, 1)

        for finding in self.context.findings:
            finding_risk = risk_levels.get(finding.get("severity", "medium"), 1)
            if finding_risk > max_allowed:
                return True

        return False

    def _build_context_summary(self) -> str:
        lines = [
            f"Intent: {self.context.intent}",
            f"Constraints: {', '.join(self.context.constraints) or 'None'}",
            f"Initial evidence: {len(self.context.initial_evidence)} items",
            f"Iterations: {self.context.iteration_count}",
            f"Todos: {len(self.context.todos)} items",
            f"Evidence: {len(self.context.evidence)} items",
            f"Findings: {len(self.context.findings)} items",
        ]

        if self.context.current_todo_id and self.context.current_todo_id in self.context.todos:
            current = self.context.todos[self.context.current_todo_id]
            lines.append(f"\nCurrent todo: {self.context.current_todo_id}")
            lines.append(f"  Description: {current.description}")
            lines.append(f"  Priority: {current.metadata.get('priority', 'medium')}")

        if self.context.todos:
            lines.append("\nAll todos:")
            for tid, task in self.context.todos.items():
                status = "current" if tid == self.context.current_todo_id else task.status.value
                priority = task.metadata.get("priority", "medium")
                lines.append(f"  - {tid}: {task.description} ({priority}, {status})")

        return "\n".join(lines)

    def _build_final_result(self) -> Dict[str, Any]:
        return {
            "stop_reason": "completed",
            "iteration_count": self.context.iteration_count,
            "final_state": WorkflowState.DONE,
            "context": {
                "intent": self.context.intent,
                "constraints": self.context.constraints,
                "todos_count": len(self.context.todos),
                "completed_todos": sum(
                    1 for t in self.context.todos.values() if t.status == TaskStatus.COMPLETED
                ),
                "evidence_count": len(self.context.evidence),
                "findings_count": len(self.context.findings),
                "artifacts": self.context.artifacts,
            },
            "budget_consumed": {
                "iterations": self.context.budget_consumed.iterations,
                "tool_calls": self.context.budget_consumed.tool_calls,
                "wall_time_seconds": self.context.budget_consumed.wall_time_seconds,
                "tokens_consumed": self.context.budget_consumed.tokens_consumed,
            },
            "phase_outputs": {
                "intake": self.context.last_intake_output.model_dump()
                if self.context.last_intake_output
                else None,
                "plan": self.context.last_plan_output.model_dump()
                if self.context.last_plan_output
                else None,
                "act": self.context.last_act_output.model_dump()
                if self.context.last_act_output
                else None,
                "synthesize": self.context.last_synthesize_output.model_dump()
                if self.context.last_synthesize_output
                else None,
                "check": self.context.last_check_output.model_dump()
                if self.context.last_check_output
                else None,
            },
        }

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response.

        Handles cases where JSON is wrapped in markdown code blocks
        or has extra text.

        Args:
            response: Raw LLM response string.

        Returns:
            Parsed JSON dict.

        Raises:
            json.JSONDecodeError if JSON cannot be parsed.
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in response:
            # Extract content between ```json and ```
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        # Try to extract from ``` block without json marker
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        # Find JSON object boundaries
        start_idx = response.find("{")
        end_idx = response.rfind("}")

        if start_idx >= 0 and end_idx > start_idx:
            response = response[start_idx : end_idx + 1]

        return json.loads(response)


def create_workflow_fsm(
    runtime: AgentRuntime,
    config: WorkflowConfig,
    fsm_id: Optional[str] = None,
    mediator: Optional[EventMediator] = None,
) -> WorkflowFSM:
    """Factory function to create a workflow FSM.

    Args:
        runtime: AgentRuntime instance for executing phases.
        config: WorkflowConfig with session, tools, budgets, etc.
        fsm_id: Optional unique identifier for this FSM instance.
        mediator: Optional EventMediator for emitting transition events.

    Returns:
        Configured WorkflowFSM instance.
    """
    return WorkflowFSM(runtime=runtime, config=config, fsm_id=fsm_id, mediator=mediator)
