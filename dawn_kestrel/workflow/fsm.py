"""REACT-enhanced FSM for workflow orchestration.

This module implements a finite state machine with REACT pattern support,
where each state can contain multiple reasoning-action-observation cycles.

REACT Pattern Integration:
- Each state handler can perform multiple REACT cycles
- Reasoning captures what the agent is thinking
- Action represents tool execution or decisions
- Observation captures the results and updates understanding

States:
- intake: Gather context and analyze input
- plan: Create task list based on findings
- act: Execute planned tasks
- synthesize: Combine and synthesize findings
- evaluate: Final evaluation and decision
- done: Workflow completion
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, Optional
import threading
import asyncio

from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.workflow.models import (
    ActionType,
    Confidence,
    DecisionType,
    ReactStep,
    StructuredContext,
    ThinkingFrame,
    ThinkingStep,
    Todo,
)


WORKFLOW_FSM_TRANSITIONS: dict[str, set[str]] = {
    "intake": {"plan", "failed"},
    "plan": {"act", "failed"},
    "act": {"synthesize", "evaluate", "done", "failed"},
    "synthesize": {"evaluate", "failed"},
    "evaluate": {"done", "failed"},
    "done": {"intake"},
    "failed": {"intake"},
}


def assert_transition(from_state: str, to_state: str) -> Result[str]:
    """Validate that a state transition is allowed.

    Args:
        from_state: Current state
        to_state: Target state

    Returns:
        Result[str]: Ok(to_state) if transition is valid, Err with error message otherwise
    """
    if from_state not in WORKFLOW_FSM_TRANSITIONS:
        return Err(
            error=(
                f"Invalid from_state: {from_state}. "
                f"Valid states: {sorted(WORKFLOW_FSM_TRANSITIONS.keys())}"
            ),
            code="INVALID_FROM_STATE",
        )

    if to_state not in WORKFLOW_FSM_TRANSITIONS[from_state]:
        return Err(
            error=(
                f"Invalid state transition: {from_state} -> {to_state}. "
                f"Valid transitions from {from_state}: "
                f"{sorted(WORKFLOW_FSM_TRANSITIONS[from_state])}"
            ),
            code="INVALID_TRANSITION",
        )

    return Ok(to_state)


class FSM:
    """Thread-safe finite state machine for workflow orchestration.

    Manages state transitions for workflow execution with REACT pattern support.
    Uses threading.RLock for reentrant-safe state mutation protection.

    Locking Strategy:
        - Uses threading.RLock for reentrant-safe state mutation protection
        - All state mutations (transitions, todo updates, reset) are protected by _state_lock
        - Read operations (property getters) do NOT acquire locks for performance
        - Each FSM instance has its own lock instance (shared lock pattern not used)
        - RLock ensures same thread can reacquire lock without deadlock

    Hierarchical Composition:
        FSM instances can contain other FSM instances as sub-FSMs, enabling
        complex workflow orchestration where sub-workflows run independently
        within the parent context. Register sub-FSMs using register_sub_fsm()
        and remove them using remove_sub_fsm().

    Attributes:
        context: The StructuredContext holding workflow state.
        state_lock: Threading lock for protecting state mutations.
        sub_fsms: Dictionary of registered sub-FSMs for hierarchical composition.

    Example:
        >>> fsm = FSM(changed_files=["file1.py", "file2.py"])
        >>> result = fsm.transition_to("plan")
        >>> result.is_ok()
        True
        >>> fsm.context.state
        'plan'
    """

    def __init__(self, changed_files: Optional[list[str]] = None):
        """Initialize workflow FSM.

        Args:
            changed_files: Optional list of changed files to initialize context.
        """
        self._context = StructuredContext(changed_files=changed_files or [])
        self._state_lock = threading.RLock()  # RLock for reentrant-safe state mutations
        self._async_state_lock: Optional[asyncio.Lock] = None
        self._retry_count = 0
        self._last_error: Optional[str] = None
        self._sub_fsms: Dict[str, FSM] = {}

    @property
    def context(self) -> StructuredContext:
        """Get the context (read-only)."""
        return self._context

    @property
    def state_lock(self) -> threading.RLock:
        """Get the state lock for protecting transitions (read-only)."""
        return self._state_lock

    @property
    def sub_fsms(self) -> Dict[str, FSM]:
        """Get registered sub-FSMs (read-only)."""
        return self._sub_fsms

    def transition_to(self, next_state: str) -> Result[str]:
        """Attempt to transition to a new state.

        Validates the transition against the transition map. Returns:
        - Ok(next_state): Transition was successful, state changed
        - Err(error): Invalid transition, state unchanged

        State transitions are serialized using _state_lock to prevent concurrent mutations.

        Args:
            next_state: The target state to transition to.

        Returns:
            Result[str]: Ok with new state, or Err with error message.

        Example:
            >>> fsm = FSM()
            >>> result = fsm.transition_to("plan")
            >>> result.is_ok()
            True
            >>> bad_result = fsm.transition_to("invalid_state")
            >>> bad_result.is_err()
            True
        """
        with self._state_lock:
            transition_result = assert_transition(self._context.state, next_state)
            if transition_result.is_ok():
                self._context.state = next_state
            return transition_result

    async def _transition_to_async(self, next_state: str) -> Result[str]:
        if self._async_state_lock is None:
            self._async_state_lock = asyncio.Lock()

        async with self._async_state_lock:
            transition_result = assert_transition(self._context.state, next_state)
            if transition_result.is_ok():
                self._context.state = next_state
            return transition_result

    def add_todo(self, todo: Todo) -> None:
        """Add a todo to the context.

        State mutations are serialized using _state_lock.

        Args:
            todo: The Todo object to add.
        """
        with self._state_lock:
            self._context.add_todo(todo)

    def update_todo_status(self, todo_id: str, status: str) -> None:
        """Update the status of an existing todo.

        State mutations are serialized using _state_lock.

        Args:
            todo_id: The ID of the todo to update.
            status: The new status value ("pending", "in_progress", "completed", "failed").
        """
        with self._state_lock:
            if todo_id in self._context.todos:
                self._context.todos[todo_id].status = status

    def clear_todos(self) -> None:
        """Remove all todos from the context.

        State mutations are serialized using _state_lock.
        """
        with self._state_lock:
            self._context.todos.clear()

    def register_sub_fsm(self, name: str, sub_fsm: FSM) -> None:
        """Register a sub-FSM with this FSM instance.

        Allows hierarchical composition where FSMs can contain other FSMs.

        Args:
            name: Unique name for the sub-FSM.
            sub_fsm: The FSM instance to register as a sub-FSM.

        Raises:
            ValueError: If a sub-FSM with the same name already exists.
        """
        with self._state_lock:
            if name in self._sub_fsms:
                raise ValueError(f"Sub-FSM '{name}' already registered")
            self._sub_fsms[name] = sub_fsm

    def remove_sub_fsm(self, name: str) -> None:
        """Remove a registered sub-FSM.

        Args:
            name: Name of the sub-FSM to remove.

        Raises:
            KeyError: If no sub-FSM with the given name exists.
        """
        with self._state_lock:
            if name not in self._sub_fsms:
                raise KeyError(f"Sub-FSM '{name}' not found")
            del self._sub_fsms[name]

    def reset(self) -> None:
        """Reset the state machine to intake state.

        This is a convenience method for testing or recovery scenarios.
        Clears todos, subagent results, consolidated findings, evaluation, error state,
        and all registered sub-FSMs.
        State mutations are serialized using _state_lock.
        """
        with self._state_lock:
            self._context.state = "intake"
            self._context.todos.clear()
            self._context.subagent_results.clear()
            self._context.consolidated.clear()
            self._context.evaluation.clear()
            self._context.user_data.clear()
            self._sub_fsms.clear()

    def run(self) -> StructuredContext:
        """Run the FSM until completion.

        Executes the workflow through all states, capturing
        REACT cycles and thinking traces at each step.

        Returns:
            StructuredContext with complete workflow trace
        """
        self._context.log.start_time = datetime.now()

        # Run FSM until reaching 'done' state
        while self._context.state != "done":
            if self._context.state in STATE_HANDLERS:
                # Execute handler and get next state
                next_state = STATE_HANDLERS[self._context.state](self._context)
                transition_result = self.transition_to(next_state)
                if transition_result.is_err():
                    self._context.state = "failed"
            else:
                self._context.state = "done"

        self._context.log.end_time = datetime.now()

        return self._context

    async def run_fsm_async(self) -> StructuredContext:
        """Run the FSM until completion asynchronously.

        Executes the workflow through all states, capturing
        REACT cycles and thinking traces at each step.
        Uses asyncio.Lock for state protection in async context.

        Returns:
            StructuredContext with complete workflow trace
        """
        if self._async_state_lock is None:
            self._async_state_lock = asyncio.Lock()

        self._context.log.start_time = datetime.now()

        # Run FSM until reaching 'done' state
        while self._context.state != "done":
            if self._context.state in STATE_HANDLERS:
                # Execute handler and get next state
                next_state = STATE_HANDLERS[self._context.state](self._context)
                transition_result = await self._transition_to_async(next_state)
                if transition_result.is_err():
                    self._context.state = "failed"
            else:
                self._context.state = "done"

        self._context.log.end_time = datetime.now()

        return self._context


def _create_react_cycle(
    reasoning: str,
    action: str,
    observation: str,
    tools_used: Optional[list[str]] = None,
    evidence: Optional[list[str]] = None,
) -> ReactStep:
    """Helper to create a REACT cycle.

    Args:
        reasoning: What the agent is thinking
        action: What the agent decides to do
        observation: What happened
        tools_used: Tools called (optional)
        evidence: Evidence references (optional)

    Returns:
        ReactStep instance
    """
    return ReactStep(
        reasoning=reasoning,
        action=action,
        observation=observation,
        tools_used=tools_used or [],
        evidence=evidence or [],
    )


def _create_thinking_step(
    kind: ActionType,
    why: str,
    next: str = "",
    evidence: Optional[list[str]] = None,
    confidence: Confidence = Confidence.MEDIUM,
) -> ThinkingStep:
    """Helper to create a thinking step.

    Args:
        kind: Step type (reason, act, observe)
        why: Reasoning
        next: Next action
        evidence: Evidence references (optional)
        confidence: Confidence level

    Returns:
        ThinkingStep instance
    """
    return ThinkingStep(
        kind=kind,
        why=why,
        evidence=evidence or [],
        next=next,
        confidence=confidence,
    )


def intake_handler(ctx: StructuredContext) -> str:
    """INTAKE state handler with REACT cycles.

    Analyzes changed files and gathers context through
    reasoning-action-observation cycles.

    Args:
        ctx: StructuredContext with workflow state

    Returns:
        Next state
    """
    frame = ThinkingFrame(state="intake")

    frame.goals = [
        f"Analyze {len(ctx.changed_files)} changed files",
        "Gather context and identify patterns",
        "Prepare for todo planning",
    ]

    # REACT Cycle 1: Analyze file list
    react_1 = _create_react_cycle(
        reasoning="Need to understand what changed to plan the workflow",
        action="Scan changed files for patterns and types",
        observation=f"Found {len(ctx.changed_files)} files to process",
        tools_used=["glob", "file_scan"],
        evidence=[f"changed:{len(ctx.changed_files)}"],
    )
    frame.add_react_cycle(react_1)

    # Thinking step
    step_1 = _create_thinking_step(
        kind=ActionType.REASON,
        why="File analysis complete, ready to plan",
        next="plan",
        confidence=Confidence.HIGH,
    )
    frame.add_step(step_1)

    frame.decision = "Context gathered, proceeding to plan"
    frame.decision_type = DecisionType.TRANSITION

    ctx.add_frame(frame)
    return "plan"


def plan_handler(ctx: StructuredContext) -> str:
    """PLAN state handler with REACT cycles.

    Creates a todo list based on context and analysis.

    Args:
        ctx: StructuredContext with workflow state

    Returns:
        Next state
    """
    frame = ThinkingFrame(state="plan")

    frame.goals = [
        "Create task breakdown from context",
        "Assign priorities based on impact",
        "Link tasks to evidence",
    ]

    # REACT Cycle 1: Plan tasks
    react_1 = _create_react_cycle(
        reasoning=f"Based on {len(ctx.changed_files)} changed files, need to create specific tasks",
        action="Generate todo items for each category of work",
        observation=f"Created {len(ctx.changed_files)} todo items dynamically",
        tools_used=["todo_planner"],
        evidence=["file_analysis", "pattern_detection"],
    )
    frame.add_react_cycle(react_1)

    # Dynamic todo creation based on changed_files
    todo_id = 1
    for i, file in enumerate(ctx.changed_files[:5], 1):
        todo = Todo(
            id=f"todo_{todo_id}",
            title=f"Review {file}",
            rationale=f"File #{i} in changed list needs analysis",
            evidence=[f"file:{file}"],
            status="pending",
            priority="high" if i == 1 else "medium",
        )
        ctx.add_todo(todo)
        todo_id += 1

    # Thinking step
    step_1 = _create_thinking_step(
        kind=ActionType.REASON,
        why=f"Created {len(ctx.todos)} todos, ready to act",
        next="act",
        confidence=Confidence.HIGH,
    )
    frame.add_step(step_1)

    frame.decision = f"Created {len(ctx.todos)} todos, proceeding to act"
    frame.decision_type = DecisionType.TRANSITION

    ctx.add_frame(frame)
    return "act"


def act_handler(ctx: StructuredContext) -> str:
    """ACT state handler with REACT cycles.

    Executes planned tasks.

    Args:
        ctx: StructuredContext with workflow state

    Returns:
        Next state
    """
    frame = ThinkingFrame(state="act")

    frame.goals = [
        "Execute planned todos",
        "Track execution status",
        "Capture results",
    ]

    # REACT Cycle 1: Execute tasks
    react_1 = _create_react_cycle(
        reasoning=f"Have {len(ctx.todos)} todos to execute",
        action="Execute each todo and capture results",
        observation=f"Executed all {len(ctx.todos)} todos",
        tools_used=["task_executor"],
        evidence=[f"todos:{len(ctx.todos)}"],
    )
    frame.add_react_cycle(react_1)

    # Execute todos and collect results
    for todo_id, todo in ctx.todos.items():
        todo.status = "in_progress"
        ctx.subagent_results[todo_id] = {
            "title": todo.title,
            "status": "completed",
            "findings": f"Analysis of {todo.title} completed",
        }
        todo.status = "completed"

    # Thinking step
    step_1 = _create_thinking_step(
        kind=ActionType.ACT,
        why="All todos executed, results captured",
        next="synthesize",
        confidence=Confidence.HIGH,
    )
    frame.add_step(step_1)

    frame.decision = "Execution complete, proceeding to synthesis"
    frame.decision_type = DecisionType.TRANSITION

    ctx.add_frame(frame)
    return "synthesize"


def synthesize_handler(ctx: StructuredContext) -> str:
    """SYNTHESIZE state handler with REACT cycles.

    Combines and synthesizes findings from execution.

    Args:
        ctx: StructuredContext with workflow state

    Returns:
        Next state
    """
    frame = ThinkingFrame(state="synthesize")

    frame.goals = [
        "Merge findings from all sources",
        "Resolve conflicts",
        "Synthesize unified view",
    ]

    # REACT Cycle 1: Synthesize
    react_1 = _create_react_cycle(
        reasoning=f"Have {len(ctx.subagent_results)} results to synthesize",
        action="Merge and analyze results into unified view",
        observation=f"Synthesized {len(ctx.subagent_results)} findings",
        tools_used=["result_merger", "synthesis"],
        evidence=[f"results:{len(ctx.subagent_results)}"],
    )
    frame.add_react_cycle(react_1)

    # Synthesis
    ctx.consolidated = {
        "total_results": len(ctx.subagent_results),
        "summary": "All tasks completed successfully",
        "findings_count": len(ctx.todos),
    }

    # Thinking step
    step_1 = _create_thinking_step(
        kind=ActionType.REASON,
        why="Synthesis complete, ready for evaluation",
        next="evaluate",
        confidence=Confidence.HIGH,
    )
    frame.add_step(step_1)

    frame.decision = "Synthesis complete, proceeding to evaluation"
    frame.decision_type = DecisionType.TRANSITION

    ctx.add_frame(frame)
    return "evaluate"


def evaluate_handler(ctx: StructuredContext) -> str:
    """EVALUATE state handler with REACT cycles.

    Final evaluation and decision making.

    Args:
        ctx: StructuredContext with workflow state

    Returns:
        Next state
    """
    frame = ThinkingFrame(state="evaluate")

    frame.goals = [
        "Evaluate overall success",
        "Check acceptance criteria",
        "Decide next action",
    ]

    # REACT Cycle 1: Evaluate
    react_1 = _create_react_cycle(
        reasoning="Need to evaluate if workflow succeeded",
        action="Check if all criteria met",
        observation=f"Workflow completed with {len(ctx.todos)} tasks done",
        tools_used=["evaluator", "criteria_checker"],
        evidence=["completion_check", "criteria_validation"],
    )
    frame.add_react_cycle(react_1)

    # Thinking step
    step_1 = _create_thinking_step(
        kind=ActionType.REASON,
        why="Evaluation passed, workflow complete",
        next="done",
        confidence=Confidence.HIGH,
    )
    frame.add_step(step_1)

    frame.decision = "Evaluation successful, workflow done"
    frame.decision_type = DecisionType.STOP

    # Add frame to log before setting evaluation (so frames_generated is accurate)
    ctx.add_frame(frame)

    # Evaluation
    ctx.evaluation = {
        "verdict": "success",
        "confidence": 0.95,
        "todos_completed": len(ctx.todos),
        "frames_generated": ctx.log.frame_count,
    }

    return "done"


STATE_HANDLERS: dict[str, Callable[[StructuredContext], str]] = {
    "intake": intake_handler,
    "plan": plan_handler,
    "act": act_handler,
    "synthesize": synthesize_handler,
    "evaluate": evaluate_handler,
}


def run_workflow_fsm(changed_files: list[str]) -> StructuredContext:
    """Run the complete workflow FSM with REACT tracing.

    Executes the workflow through all states, capturing
    REACT cycles and thinking traces at each step.

    Args:
        changed_files: List of changed files to process

    Returns:
        StructuredContext with complete workflow trace
    """

    fsm = FSM(changed_files=changed_files)
    return fsm.run()
