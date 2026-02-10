"""
FSM-based Security Review Agent with Subagent Delegation.

This example demonstrates:
- A SecurityReviewerAgent using a Finite State Machine (FSM) for lifecycle management
- Delegation of investigation tasks to subagents (the reviewer does NO investigation)
- Todo creation based on exploration results
- Iterative review with additional task creation based on findings
- Final assessment generation when all tasks complete

Key Design Principles:
- Separation of Concerns: Security reviewer orchestrates, doesn't investigate
- FSM-based Lifecycle: Explicit state transitions ensure proper workflow
- Adaptive Planning: Todos created dynamically based on initial exploration
- Iterative Refinement: Review results generate additional review tasks

FSM States:
- IDLE: Waiting to start review
- INITIAL_EXPLORATION: Gathering context and creating initial todos
- DELEGATING_INVESTIGATION: Delegating investigation tasks to subagents
- REVIEWING_RESULTS: Analyzing subagent investigation results
- CREATING_REVIEW_TASKS: Creating additional review tasks based on findings
- FINAL_ASSESSMENT: Generating final security assessment
- COMPLETED: Review complete
- FAILED: Review failed

Run this example:
    python docs/examples/fsm_security_reviewer.py
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, TYPE_CHECKING
from pathlib import Path

from dawn_kestrel.core.agent_task import TaskStatus, create_agent_task
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.agents.orchestrator import AgentOrchestrator
from dawn_kestrel.agents.review.utils.redaction import format_log_with_redaction

# For type hints (avoid circular import)
if TYPE_CHECKING:
    from dawn_kestrel.llm import LLMClient


class ReviewFSMImpl:
    """Custom FSM for SecurityReviewerAgent with custom states."""

    def __init__(self, initial_state: str = "idle"):
        self._state = initial_state

    async def get_state(self) -> str:
        return self._state

    async def transition_to(self, new_state: str) -> Result[None]:
        current = self._state

        valid_transitions = {
            "idle": {"initial_exploration", "failed"},
            "initial_exploration": {"delegating_investigation", "failed"},
            "delegating_investigation": {"reviewing_results", "failed"},
            "reviewing_results": {"creating_review_tasks", "final_assessment", "failed"},
            "creating_review_tasks": {"delegating_investigation", "final_assessment", "failed"},
            "final_assessment": {"completed", "failed"},
            "completed": {"idle"},
            "failed": {"idle"},
        }

        if new_state not in valid_transitions.get(current, set()):
            return Err(
                f"Invalid state transition: {current} -> {new_state}. "
                f"Valid transitions from {current}: {sorted(valid_transitions.get(current, set()))}",
                code="INVALID_TRANSITION",
            )

        self._state = new_state
        return Ok(None)

    async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        valid_transitions = {
            "idle": {"initial_exploration", "failed"},
            "initial_exploration": {"delegating_investigation", "failed"},
            "delegating_investigation": {"reviewing_results", "failed"},
            "reviewing_results": {"creating_review_tasks", "final_assessment", "failed"},
            "creating_review_tasks": {"delegating_investigation", "final_assessment", "failed"},
            "final_assessment": {"completed", "failed"},
            "completed": {"idle"},
            "failed": {"idle"},
        }
        return to_state in valid_transitions.get(from_state, set())


from dawn_kestrel.agents.runtime import AgentRuntime
from dawn_kestrel.agents.review.utils.git import get_changed_files, get_diff
from dawn_kestrel.agents.review.base import ReviewContext


# =============================================================================
# Enums and Data Models
# =============================================================================


class ReviewState(str, Enum):
    """States for the FSM-based security reviewer."""

    IDLE = "idle"
    INITIAL_EXPLORATION = "initial_exploration"
    DELEGATING_INVESTIGATION = "delegating_investigation"
    REVIEWING_RESULTS = "reviewing_results"
    CREATING_REVIEW_TASKS = "creating_review_tasks"
    FINAL_ASSESSMENT = "final_assessment"
    COMPLETED = "completed"
    FAILED = "failed"


class TodoStatus(str, Enum):
    """Status for todo items."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoPriority(str, Enum):
    """Priority levels for todo items."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SecurityTodo:
    """A todo item for security review tasks."""

    id: str
    title: str
    description: str
    status: TodoStatus = TodoStatus.PENDING
    priority: TodoPriority = TodoPriority.MEDIUM
    agent: Optional[str] = None  # Which subagent handles this
    dependencies: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)

    def is_ready(self, all_todos: Dict[str, "SecurityTodo"]) -> bool:
        """Check if this todo is ready to be executed (dependencies satisfied)."""
        if not self.dependencies:
            return True
        for dep_id in self.dependencies:
            dep_todo = all_todos.get(dep_id)
            if not dep_todo or dep_todo.status != TodoStatus.COMPLETED:
                return False
        return True


@dataclass
class SubagentTask:
    """A task delegated to an investigation subagent."""

    task_id: str
    todo_id: str
    description: str
    agent_name: str
    prompt: str
    tools: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SecurityFinding:
    """A security finding from investigation."""

    id: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    evidence: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None
    requires_review: bool = True  # Whether this finding needs additional review task
    confidence_score: float = 0.50  # Numeric confidence 0.0-1.0 for threshold filtering


@dataclass
class SecurityAssessment:
    """Final security assessment output."""

    overall_severity: str
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    merge_recommendation: str  # approve, needs_changes, block
    findings: List[SecurityFinding]
    summary: str
    notes: List[str] = field(default_factory=list)


# =============================================================================
# Security Reviewer Agent with FSM
# =============================================================================


class SecurityReviewerAgent:
    """
    FSM-based security reviewer that delegates investigation to subagents.

    This agent does NOT perform investigation itself. It:
    1. Uses FSM to manage lifecycle states
    2. Creates todos based on initial exploration
    3. Delegates investigation tasks to subagents
    4. Reviews investigation results
    5. Creates additional review tasks as needed
    6. Generates final assessment

    The FSM ensures proper workflow through explicit state transitions.
    """

    # Define valid state transitions
    VALID_TRANSITIONS: Dict[ReviewState, set[ReviewState]] = {
        ReviewState.IDLE: {ReviewState.INITIAL_EXPLORATION, ReviewState.FAILED},
        ReviewState.INITIAL_EXPLORATION: {ReviewState.DELEGATING_INVESTIGATION, ReviewState.FAILED},
        ReviewState.DELEGATING_INVESTIGATION: {ReviewState.REVIEWING_RESULTS, ReviewState.FAILED},
        ReviewState.REVIEWING_RESULTS: {
            ReviewState.CREATING_REVIEW_TASKS,
            ReviewState.FINAL_ASSESSMENT,
            ReviewState.FAILED,
        },
        ReviewState.CREATING_REVIEW_TASKS: {
            ReviewState.DELEGATING_INVESTIGATION,
            ReviewState.FINAL_ASSESSMENT,
            ReviewState.FAILED,
        },
        ReviewState.FINAL_ASSESSMENT: {ReviewState.COMPLETED, ReviewState.FAILED},
        ReviewState.COMPLETED: {ReviewState.IDLE},  # Can restart
        ReviewState.FAILED: {ReviewState.IDLE},  # Can restart
    }

    def __init__(
        self, orchestrator: AgentOrchestrator, session_id: str, confidence_threshold: float = 0.50
    ):
        """Initialize security reviewer agent.

        Args:
            orchestrator: AgentOrchestrator for task delegation
            session_id: Session ID for tracking
            confidence_threshold: Minimum confidence score (0.0-1.0) for finding inclusion (default 0.50)
        """
        self.orchestrator = orchestrator
        self.session_id = session_id
        self.confidence_threshold = confidence_threshold

        self.fsm = ReviewFSMImpl(initial_state=ReviewState.IDLE.value)

        # Review state data
        self.todos: Dict[str, SecurityTodo] = {}
        self.subagent_tasks: Dict[str, SubagentTask] = {}
        self.findings: List[SecurityFinding] = []
        self.context: Optional[ReviewContext] = None

        # Dedup tracking - prevent reprocessing across iterations
        self.processed_finding_ids: Set[str] = set()
        self.processed_task_ids: Set[str] = set()

        # Tracking
        self.iteration_count = 0
        self.max_iterations = 5  # Prevent infinite loops

        logger = logging.getLogger(__name__)
        self.logger = logger

    # =========================================================================
    # FSM State Management
    # =========================================================================

    async def get_state(self) -> ReviewState:
        """Get current FSM state."""
        state_str = await self.fsm.get_state()
        return ReviewState(state_str)

    async def _transition_to(self, new_state: ReviewState) -> bool:
        """Transition FSM to new state.

        Args:
            new_state: Target state

        Returns:
            True if transition successful, False otherwise
        """
        current_state = await self.get_state()

        if new_state not in SecurityReviewerAgent.VALID_TRANSITIONS.get(current_state, set()):
            self.logger.error(
                f"Invalid FSM transition: {current_state.value} -> {new_state.value}. "
                f"Valid transitions: {SecurityReviewerAgent.VALID_TRANSITIONS.get(current_state, set())}"
            )
            return False

        result = await self.fsm.transition_to(new_state.value)
        if result.is_err():
            from dawn_kestrel.core.result import Err

            err_result = result
            if isinstance(err_result, Err):
                self.logger.error(f"FSM transition failed: {err_result.error}")
            return False

        self.logger.info(f"FSM transitioned: {current_state.value} -> {new_state.value}")
        return True

    # =========================================================================
    # Main Review Orchestration
    # =========================================================================

    async def run_review(self, repo_root: str, base_ref: str, head_ref: str) -> SecurityAssessment:
        """
        Run the complete security review workflow.

        This is the main entry point that drives the FSM through all states.

        Args:
            repo_root: Path to git repository
            base_ref: Base reference (e.g., 'main')
            head_ref: Head reference (e.g., 'feature-branch')

        Returns:
            SecurityAssessment with final review results
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting FSM-based Security Review")
        self.logger.info("=" * 60)
        self.logger.info(f"Repository: {repo_root}")
        self.logger.info(f"Base ref: {base_ref}")
        self.logger.info(f"Head ref: {head_ref}")
        self.logger.info("")

        try:
            # Initial exploration phase
            await self._transition_to(ReviewState.INITIAL_EXPLORATION)
            await self._initial_exploration(repo_root, base_ref, head_ref)

            # Main review loop
            while self.iteration_count < self.max_iterations:
                self.iteration_count += 1
                self.logger.info("")
                # Standardized iteration start logging
                self.logger.info(
                    format_log_with_redaction(
                        message=f"[ITERATION_LIFECYCLE] Starting iteration {self.iteration_count}",
                        iteration_number=str(self.iteration_count),
                        max_iterations=str(self.max_iterations),
                    )
                )
                self.logger.info("-" * 60)

                # Delegate investigation tasks
                await self._transition_to(ReviewState.DELEGATING_INVESTIGATION)
                await self._delegate_investigation_tasks()

                # Wait for tasks to complete
                await self._wait_for_investigation_tasks()

                # Review results
                await self._transition_to(ReviewState.REVIEWING_RESULTS)
                needs_more_tasks = await self._review_investigation_results()

                if needs_more_tasks:
                    await self._transition_to(ReviewState.CREATING_REVIEW_TASKS)
                    await self._create_review_tasks()
                    continue
                else:
                    # Log iteration end
                    self.logger.info(
                        format_log_with_redaction(
                            message=f"[ITERATION_LIFECYCLE] Completed iteration {self.iteration_count}",
                            iteration_number=str(self.iteration_count),
                            total_findings=str(len(self.findings)),
                        )
                    )
                    break

            # Final assessment
            await self._transition_to(ReviewState.FINAL_ASSESSMENT)
            assessment = await self._generate_final_assessment()

            await self._transition_to(ReviewState.COMPLETED)
            self.logger.info("")
            self.logger.info("=" * 60)
            self.logger.info("Security Review Completed")
            self.logger.info("=" * 60)
            self.logger.info("Security Review Completed")
            self.logger.info("=" * 60)

            return assessment

        except Exception as e:
            self.logger.error(f"Security review failed: {e}", exc_info=True)
            await self._transition_to(ReviewState.FAILED)
            raise

    # =========================================================================
    # State Handlers
    # =========================================================================

    async def _initial_exploration(self, repo_root: str, base_ref: str, head_ref: str):
        """
        INITIAL_EXPLORATION state handler.

        Gather context and create initial todos based on what needs to be investigated.

        This is where the security reviewer DOES NO investigation - it just
        analyzes what changed and creates todos for what needs checking.
        """
        self.logger.info("[INITIAL_EXPLORATION] Gathering context...")

        # Get git diff context
        try:
            changed_files = await get_changed_files(repo_root, base_ref, head_ref)
            diff = await get_diff(repo_root, base_ref, head_ref)
        except Exception as e:
            self.logger.error(f"Failed to get git context: {e}")
            raise

        self.context = ReviewContext(
            changed_files=changed_files,
            diff=diff,
            repo_root=repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
        )

        if self.context and self.context.changed_files:
            self.logger.info(
                f"[INITIAL_EXPLORATION] Found {len(self.context.changed_files)} changed files"
            )
            self.logger.info(
                f"[INITIAL_EXPLORATION] Diff size: {len(self.context.diff)} characters"
            )

        # Create initial todos based on exploration (use dynamic method with LLM discovery if available)
        await self._create_dynamic_todos(
            llm_client=None
        )  # Pass None for rule-only mode, can be enhanced later

        self.logger.info(f"[INITIAL_EXPLORATION] Created {len(self.todos)} initial todos")

    async def _create_initial_todos_fallback(self):
        """Create initial todos based on exploration of changed files.

        Always creates comprehensive security checks regardless of filenames.
        """
        self.logger.info("[INITIAL_EXPLORATION] Creating initial todos...")

        if not self.context or not self.context.changed_files:
            self.logger.warning("[INITIAL_EXPLORATION] No changed files found")
            return

        todo_id = 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan for secrets and credentials",
            description=f"Scan {len(self.context.changed_files)} changed files for leaked secrets or credentials",
            priority=TodoPriority.HIGH,
            agent="secret_scanner",
        )
        todo_id += 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan for injection vulnerabilities",
            description="Check for SQL injection, XSS, command injection, and path traversal",
            priority=TodoPriority.HIGH,
            agent="injection_scanner",
        )
        todo_id += 1

        auth_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in ["auth", "login", "session", "jwt", "token", "user", "permission", "role"]
            )
        ]
        if auth_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review authentication and authorization code",
                description=f"Check {len(auth_files)} auth-related files for security issues: {', '.join(auth_files[:5])}",
                priority=TodoPriority.HIGH,
                agent="auth_reviewer",
            )
            todo_id += 1

        dependency_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in [
                    "requirements",
                    "pyproject",
                    "package.json",
                    "yarn",
                    "npm",
                    "composer",
                    "pom.xml",
                ]
            )
        ]
        if dependency_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Audit dependencies for vulnerabilities",
                description=f"Check {len(dependency_files)} dependency files for known vulnerabilities: {', '.join(dependency_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="dependency_auditor",
            )
            todo_id += 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Check for unsafe function usage",
            description="Scan for eval(), exec(), system(), shell_exec, and other dangerous functions",
            priority=TodoPriority.HIGH,
            agent="unsafe_function_scanner",
        )
        todo_id += 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Review cryptography and encoding usage",
            description="Check for weak crypto, hardcoded keys, or encoding issues",
            priority=TodoPriority.MEDIUM,
            agent="crypto_scanner",
        )
        todo_id += 1

        config_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["config", "env", "setting", ".env", "security"])
        ]
        if config_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review security configuration",
                description=f"Check {len(config_files)} config files for security misconfigurations: {', '.join(config_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="config_scanner",
            )
            todo_id += 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan diff for security patterns",
            description="Use grep/ast-grep to scan the diff for common security vulnerabilities",
            priority=TodoPriority.MEDIUM,
            agent="pattern_scanner",
        )
        todo_id += 1

        # Always scan for code injection vulnerabilities (critical check)
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan for injection vulnerabilities",
            description="Check for SQL injection, XSS, command injection, and path traversal",
            priority=TodoPriority.HIGH,
            agent="injection_scanner",
        )
        todo_id += 1

        # Always check for authentication/authorization issues
        auth_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in ["auth", "login", "session", "jwt", "token", "user", "permission", "role"]
            )
        ]
        if auth_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review authentication and authorization code",
                description=f"Check {len(auth_files)} auth-related files for security issues: {', '.join(auth_files[:5])}",
                priority=TodoPriority.HIGH,
                agent="auth_reviewer",
            )
            todo_id += 1

        # Check dependency files for vulnerabilities
        dependency_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in [
                    "requirements",
                    "pyproject",
                    "package.json",
                    "yarn",
                    "npm",
                    "composer",
                    "pom.xml",
                ]
            )
        ]
        if dependency_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Audit dependencies for vulnerabilities",
                description=f"Check {len(dependency_files)} dependency files for known vulnerabilities: {', '.join(dependency_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="dependency_auditor",
            )
            todo_id += 1

        # Always check for unsafe function usage
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Check for unsafe function usage",
            description="Scan for eval(), exec(), system(), shell_exec, and other dangerous functions",
            priority=TodoPriority.HIGH,
            agent="unsafe_function_scanner",
        )
        todo_id += 1

        # Always check for crypto/encoding issues
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Review cryptography and encoding usage",
            description="Check for weak crypto, hardcoded keys, or encoding issues",
            priority=TodoPriority.MEDIUM,
            agent="crypto_scanner",
        )
        todo_id += 1

        # Check network/security config files
        config_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["config", "env", "setting", ".env", "security"])
        ]
        if config_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review security configuration",
                description=f"Check {len(config_files)} config files for security misconfigurations: {', '.join(config_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="config_scanner",
            )
            todo_id += 1

        # Always do general security pattern scan
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan diff for security patterns",
            description="Use grep/ast-grep to scan the diff for common security vulnerabilities",
            priority=TodoPriority.MEDIUM,
            agent="pattern_scanner",
        )
        todo_id += 1

    async def _create_dynamic_todos(self, llm_client: Optional["LLMClient"] = None):
        """
        Create dynamic todos based on file analysis with LLM-powered discovery.

        This method implements a two-layer approach:
        1. Rule-based layer: File-type classification, risk-based prioritization, resource-aware scaling
        2. LLM-powered discovery: Analyze changed files for unexpected security patterns

        Args:
            llm_client: Optional LLMClient for dynamic todo discovery.
                       If None or LLM fails, falls back to rule-only mode.

        Returns:
            None (updates self.todos in place)
        """
        self.logger.info("[DYNAMIC_TODOS] Creating dynamic todos with rule-based layer...")

        if not self.context or not self.context.changed_files:
            self.logger.warning("[DYNAMIC_TODOS] No changed files found")
            return

        # =========================================================================
        # LAYER 1: Rule-Based Todo Generation
        # =========================================================================

        self.logger.info("[DYNAMIC_TODOS] Starting rule-based layer...")

        # Calculate total lines changed for resource-aware scaling
        total_lines_changed = 0
        if self.context.diff:
            # Count non-empty lines in diff
            total_lines_changed = len(
                [line for line in self.context.diff.split("\n") if line.strip()]
            )

        # Resource-aware scaling decision
        max_parallel_subagents = 4  # Default for medium diffs
        if total_lines_changed < 100:
            max_parallel_subagents = 2
            self.logger.info(
                f"[DYNAMIC_TODOS] Small diff ({total_lines_changed} lines), limiting to 2 parallel agents"
            )
        elif total_lines_changed > 1000:
            max_parallel_subagents = 6
            self.logger.info(
                f"[DYNAMIC_TODOS] Large diff ({total_lines_changed} lines), allowing up to 6 parallel agents"
            )
        else:
            self.logger.info(
                f"[DYNAMIC_TODOS] Medium diff ({total_lines_changed} lines), using up to 4 parallel agents"
            )

        # Store scaling decision in agent state for logging
        self._max_parallel_subagents = max_parallel_subagents  # type: ignore[attr-defined]

        # File-type classification
        python_files = [f for f in self.context.changed_files if f.endswith((".py", ".pyx"))]
        js_files = [f for f in self.context.changed_files if f.endswith((".js", ".ts", ".tsx"))]
        config_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in [
                    ".env",
                    "settings",
                    "config",
                    "package.json",
                    "pyproject.toml",
                    "docker-compose.yml",
                    "requirements.txt",
                ]
            )
        ]

        self.logger.info(
            f"[DYNAMIC_TODOS] File classification: {len(python_files)} Python, {len(js_files)} JS/TS, {len(config_files)} config files"
        )

        todo_id = 1

        # Rule-based: Always create core security todos
        # Secrets scan (always HIGH priority)
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan for secrets and credentials",
            description=f"Scan {len(self.context.changed_files)} changed files for leaked secrets or credentials",
            priority=TodoPriority.HIGH,
            agent="secret_scanner",
        )
        todo_id += 1

        # Injection scan (always HIGH priority)
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan for injection vulnerabilities",
            description="Check for SQL injection, XSS, command injection, and path traversal",
            priority=TodoPriority.HIGH,
            agent="injection_scanner",
        )
        todo_id += 1

        # Rule-based: Risk-based prioritization for file types

        # Auth files → HIGH priority auth review
        auth_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in ["auth", "login", "session", "jwt", "token", "user", "permission", "role"]
            )
        ]
        if auth_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review authentication and authorization code",
                description=f"Check {len(auth_files)} auth-related files for security issues: {', '.join(auth_files[:5])}",
                priority=TodoPriority.HIGH,
                agent="auth_reviewer",
            )
            todo_id += 1

        # Dependency files → HIGH priority dependency audit
        dependency_files = [
            f
            for f in self.context.changed_files
            if any(
                x in f.lower()
                for x in [
                    "requirements",
                    "pyproject",
                    "package.json",
                    "yarn",
                    "npm",
                    "composer",
                    "pom.xml",
                ]
            )
        ]
        if dependency_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Audit dependencies for vulnerabilities",
                description=f"Check {len(dependency_files)} dependency files for known vulnerabilities: {', '.join(dependency_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="dependency_auditor",
            )
            todo_id += 1

        # Config files → HIGH priority config scan
        config_security_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["config", "env", "setting", ".env", "security"])
        ]
        if config_security_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review security configuration",
                description=f"Check {len(config_security_files)} config files for security misconfigurations: {', '.join(config_security_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="config_scanner",
            )
            todo_id += 1

        # Regular source files → MEDIUM priority pattern scan
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Check for unsafe function usage",
            description="Scan for eval(), exec(), system(), shell_exec, and other dangerous functions",
            priority=TodoPriority.HIGH,
            agent="unsafe_function_scanner",
        )
        todo_id += 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Review cryptography and encoding usage",
            description="Check for weak crypto, hardcoded keys, or encoding issues",
            priority=TodoPriority.MEDIUM,
            agent="crypto_scanner",
        )
        todo_id += 1

        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan diff for security patterns",
            description="Use grep/ast-grep to scan the diff for common security vulnerabilities",
            priority=TodoPriority.MEDIUM,
            agent="pattern_scanner",
        )
        todo_id += 1

        # =========================================================================
        # LAYER 2: LLM-Powered Discovery (optional)
        # =========================================================================

        if llm_client:
            self.logger.info("[DYNAMIC_TODOS] Starting LLM-powered discovery layer...")
            await self._llm_discover_todos(llm_client)
        else:
            self.logger.info("[DYNAMIC_TODOS] No LLM client provided, skipping discovery layer")

        self.logger.info(
            f"[DYNAMIC_TODOS] Created {len(self.todos)} dynamic todos (rule-based: {todo_id - 1}, LLM-discovered: {len(self.todos) - (todo_id - 1) if self.todos else 0})"
        )

    async def _llm_discover_todos(self, llm_client: "LLMClient"):
        """
        LLM-powered discovery of additional todos not covered by rules.

        This method analyzes changed files for unexpected security patterns
        and proposes context-aware todos.

        Args:
            llm_client: LLMClient for dynamic todo discovery

        Returns:
            None (updates self.todos in place)
        """
        self.logger.info(
            "[LLM_DISCOVERY] Analyzing changed files for unexpected security patterns..."
        )

        # Build context for LLM
        if not self.context or not self.context.changed_files:
            return

        # Build file list summary
        files_str = ", ".join(self.context.changed_files[:20])
        if len(self.context.changed_files) > 20:
            files_str += f" ... and {len(self.context.changed_files) - 20} more"

        # Build diff summary
        diff_summary = self.context.diff[:1000] if self.context.diff else "No diff available"

        # Build existing todos summary
        existing_todos_summary = "\n".join(
            [f"- {todo.title} ({todo.priority} priority)" for todo in self.todos.values()]
        )

        # Build prompt for LLM
        prompt = f"""You are a security code reviewer specializing in dynamic security analysis.

Your task is to analyze changed files for unexpected security patterns that might not be covered by standard rules.

FILES CHANGED:
{files_str}

DIFF SUMMARY:
{diff_summary}

EXISTING RULE-BASED TODOS:
{existing_todos_summary}

ANALYSIS TASK:
Review the changed files and diff for the following:

1. Unexpected Security Patterns:
   - Security issues not typically caught by standard rules
   - Novel attack vectors specific to this codebase
   - Context-specific security risks
   - Business logic security flaws

2. Dynamic Risk Factors:
   - Security patterns unique to this project's architecture
   - Integration points that might introduce vulnerabilities
   - Data flow issues not covered by static analysis
   - Configuration drift or environment-specific risks

3. Iteration Awareness:
   - Consider findings from previous iterations (if any)
   - Prioritize areas where security issues were found before
   - Check if previous fixes introduced new vulnerabilities

OUTPUT FORMAT:
Return proposed todos as a JSON object with:
{{
  "proposed_todos": [
    {{
      "title": "Short descriptive title",
      "description": "Detailed description of what needs to be reviewed",
      "priority": "high|medium|low",
      "agent": "suggested agent name (e.g., pattern_scanner, auth_reviewer)",
      "rationale": "Why this todo is needed based on analysis"
    }}
  ],
  "summary": "Brief summary of LLM discovery"
}}

BE CONSISTENT with existing agents:
- secret_scanner: For secrets and credentials
- injection_scanner: For SQL injection, XSS, command injection, path traversal
- auth_reviewer: For authentication and authorization code
- dependency_auditor: For dependency vulnerabilities
- unsafe_function_scanner: For dangerous functions (eval, exec, system)
- crypto_scanner: For weak crypto, hardcoded keys, encoding issues
- config_scanner: For security misconfigurations
- pattern_scanner: For general security patterns

If no additional todos are needed, return an empty proposed_todos array.
"""

        try:
            from dawn_kestrel.llm import LLMRequestOptions
            import json

            # Call LLM
            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                options=LLMRequestOptions(
                    temperature=0.3,  # Lower temperature for more deterministic results
                    max_tokens=2000,
                ),
            )

            # Parse LLM response
            try:
                llm_result = json.loads(response.text)
                proposed_todos = llm_result.get("proposed_todos", [])
                summary = llm_result.get("summary", "LLM discovery completed")

                # Add LLM-proposed todos to self.todos
                for proposed in proposed_todos:
                    # Validate proposed todo fields
                    title = proposed.get("title", "")
                    description = proposed.get("description", "")
                    priority_str = proposed.get("priority", "medium")
                    agent = proposed.get("agent", "pattern_scanner")

                    if not title or not description:
                        self.logger.warning(
                            f"[LLM_DISCOVERY] Skipping proposed todo with missing title or description"
                        )
                        continue

                    # Validate priority
                    try:
                        priority = TodoPriority(priority_str)
                    except ValueError:
                        self.logger.warning(
                            f"[LLM_DISCOVERY] Invalid priority '{priority_str}', defaulting to medium"
                        )
                        priority = TodoPriority.MEDIUM

                    # Create new todo
                    new_todo_id = f"todo_llm_{len(self.todos) + 1}"
                    self.todos[new_todo_id] = SecurityTodo(
                        id=new_todo_id,
                        title=title,
                        description=description,
                        priority=priority,
                        agent=agent,
                    )
                    self.logger.info(
                        f"[LLM_DISCOVERY] Added todo: {title} ({priority} priority, agent: {agent})"
                    )

                self.logger.info(
                    f"[LLM_DISCOVERY] LLM proposed {len(proposed_todos)} todos: {summary}"
                )

            except json.JSONDecodeError as e:
                self.logger.warning(f"[LLM_DISCOVERY] Failed to parse LLM response as JSON: {e}")
                self.logger.debug(f"[LLM_DISCOVERY] LLM response: {response.text[:500]}")

        except Exception as e:
            self.logger.warning(f"[LLM_DISCOVERY] LLM discovery failed: {e}")
            # Fall back to rule-only mode (todos already created)

    async def _delegate_investigation_tasks(self):
        """
        DELEGATING_INVESTIGATION state handler.

        Delegate all pending todos to investigation subagents.

        The security reviewer DELEGATES - it does NOT investigate.
        Each todo becomes a task for an appropriate subagent.
        """
        self.logger.info("[DELEGATING_INVESTIGATION] Delegating tasks to subagents...")

        for todo_id, todo in self.todos.items():
            # Skip todos whose tasks were already processed in previous iterations
            if todo_id in self.processed_task_ids:
                # Log task skip with task ID and reason
                self.logger.info(
                    format_log_with_redaction(
                        message="[TASK_SKIP] Skipping task already processed in previous iteration",
                        task_id=todo_id,
                        reason=f"Task {todo_id} already completed in previous iteration",
                    )
                )
                continue

            if todo.status == TodoStatus.PENDING and todo.is_ready(self.todos):
                self.logger.info(f"[DELEGATING_INVESTIGATION] Delegating: {todo.title}")

                # Mark todo as in_progress
                todo.status = TodoStatus.IN_PROGRESS

                # Create subagent task
                task = create_agent_task(
                    agent_name=todo.agent or "general_investigator",
                    description=todo.description,
                    skill_names=["security-scanner"],
                    metadata={"todo_id": todo_id},
                )

                subagent_task = SubagentTask(
                    task_id=task.task_id,
                    todo_id=todo_id,
                    description=todo.description,
                    agent_name=todo.agent or "general_investigator",
                    prompt=self._build_subagent_prompt(todo),
                    tools=["grep", "ast-grep", "bandit", "git"],
                )

                self.subagent_tasks[task.task_id] = subagent_task

                # Simulate task execution
                await self._simulate_subagent_execution(subagent_task)

    def _build_subagent_prompt(self, todo: SecurityTodo) -> str:
        """Build prompt for subagent investigation.

        Args:
            todo: The todo to create prompt for

        Returns:
            Prompt string for subagent
        """
        if not self.context or not self.context.changed_files:
            changed_files_str = "No files available"
            diff_size_str = "0"
        else:
            changed_files_str = ", ".join(self.context.changed_files[:10])
            diff_size_str = str(len(self.context.diff))

        prompt = f"""You are a security investigation subagent.

TODO: {todo.title}
DESCRIPTION: {todo.description}
PRIORITY: {todo.priority.value}

CONTEXT:
- Changed files: {changed_files_str}
- Total diff size: {diff_size_str} characters

INVESTIGATION TASK:
Perform a thorough security investigation focusing on the area described above.
Use grep, ast-grep, and other tools to identify potential vulnerabilities.

OUTPUT FORMAT:
Return findings as a JSON object with:
{{
  "findings": [
    {{
      "id": "unique_id",
      "severity": "critical|high|medium|low",
      "title": "Short descriptive title",
      "description": "Detailed description",
      "evidence": "Code snippet or pattern matched",
      "file_path": "path/to/file",
      "line_number": 123,
      "recommendation": "How to fix",
      "requires_review": true/false
    }}
  ],
  "summary": "Brief summary of investigation"
}}

Be thorough. Report ALL potential issues, even low-severity ones.
"""
        return prompt

    async def _simulate_subagent_execution(self, task: SubagentTask):
        await asyncio.sleep(0.5)

        if "secret" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_001",
                        "severity": "critical",
                        "title": "Potential AWS access key found",
                        "description": "Found pattern resembling AWS access key in code",
                        "evidence": "AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'",
                        "file_path": "config.py",
                        "line_number": 42,
                        "recommendation": "Remove hardcoded credentials. Use environment variables or secret manager.",
                        "requires_review": True,
                    }
                ],
                "summary": "Scanned for secrets and found 1 critical issue.",
            }
        elif "injection" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_002",
                        "severity": "high",
                        "title": "SQL injection risk",
                        "description": "User input used directly in SQL query without sanitization",
                        "evidence": f"query = f'SELECT * FROM users WHERE id = {{user_id}}'",
                        "file_path": "api/users.py",
                        "line_number": 156,
                        "recommendation": "Use parameterized queries or an ORM.",
                        "requires_review": True,
                    },
                    {
                        "id": "sec_003",
                        "severity": "high",
                        "title": "XSS vulnerability",
                        "description": "User input rendered without sanitization",
                        "evidence": "return f'<div>{user_input}</div>'",
                        "file_path": "views.py",
                        "line_number": 89,
                        "recommendation": "Use template escaping or HTML sanitization.",
                        "requires_review": True,
                    },
                ],
                "summary": "Scanned for injection vulnerabilities and found 2 high-severity issues.",
            }
        elif "unsafe_function" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_004",
                        "severity": "high",
                        "title": "Use of dangerous eval() function",
                        "description": "Code uses eval() on user input",
                        "evidence": "result = eval(user_data)",
                        "file_path": "utils.py",
                        "line_number": 45,
                        "recommendation": "Replace eval() with safe alternatives or strict validation.",
                        "requires_review": True,
                    }
                ],
                "summary": "Scanned for unsafe functions and found 1 high-severity issue.",
            }
        elif "crypto" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_005",
                        "severity": "medium",
                        "title": "Weak cryptography detected",
                        "description": "Using MD5 which is cryptographically broken",
                        "evidence": "hashlib.md5(data).hexdigest()",
                        "file_path": "hashing.py",
                        "line_number": 23,
                        "recommendation": "Use SHA-256 or stronger hash functions.",
                        "requires_review": False,
                    }
                ],
                "summary": "Reviewed cryptography usage and found 1 medium-severity issue.",
            }
        elif "config" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_006",
                        "severity": "medium",
                        "title": "Debug mode enabled in production",
                        "description": "DEBUG setting is True which may expose sensitive information",
                        "evidence": "DEBUG = True",
                        "file_path": "settings.py",
                        "line_number": 15,
                        "recommendation": "Set DEBUG=False in production environments.",
                        "requires_review": False,
                    }
                ],
                "summary": "Reviewed security configuration and found 1 medium-severity issue.",
            }
        elif "pattern" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_007",
                        "severity": "low",
                        "title": "Print statement in production code",
                        "description": "Debug print statement that may leak information",
                        "evidence": "print(f'Debug: {sensitive_data}')",
                        "file_path": "main.py",
                        "line_number": 112,
                        "recommendation": "Remove or replace with proper logging.",
                        "requires_review": False,
                    }
                ],
                "summary": "Scanned diff for security patterns and found 1 low-severity issue.",
            }
        elif "auth" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_008",
                        "severity": "high",
                        "title": "Missing JWT expiration check",
                        "description": "JWT token validation does not check expiration",
                        "evidence": "if verify_token(token):  # No exp check",
                        "file_path": "auth/middleware.py",
                        "line_number": 87,
                        "recommendation": "Add token expiration validation in verify_token function.",
                        "requires_review": True,
                    }
                ],
                "summary": "Reviewed auth code and found 1 high-severity issue.",
            }
        elif "dependency" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_009",
                        "severity": "medium",
                        "title": "Outdated dependency with known CVE",
                        "description": "requests==2.25.0 has known vulnerabilities",
                        "evidence": "requests==2.25.0 in requirements.txt",
                        "file_path": "requirements.txt",
                        "line_number": 23,
                        "recommendation": "Update to requests>=2.31.0",
                        "requires_review": False,
                    }
                ],
                "summary": "Audited dependencies and found 1 medium-severity issue.",
            }
        else:
            task.result = {
                "findings": [],
                "summary": f"No security issues found in {task.agent_name} investigation.",
            }

        task.status = TaskStatus.COMPLETED
        self.logger.info(f"[DELEGATING_INVESTIGATION] Task {task.task_id} completed")

    async def _wait_for_investigation_tasks(self):
        """Wait for all delegated tasks to complete."""
        self.logger.info("[DELEGATING_INVESTIGATION] Waiting for subagent tasks...")

        while True:
            incomplete_tasks = [
                t for t in self.subagent_tasks.values() if t.status != TaskStatus.COMPLETED
            ]
            if not incomplete_tasks:
                break
            await asyncio.sleep(0.1)

        self.logger.info("[DELEGATING_INVESTIGATION] All subagent tasks completed")

    async def _review_investigation_results(self) -> bool:
        """
        REVIEWING_RESULTS state handler.

        Review investigation results from subagents and determine if more work is needed.

        Returns:
            True if additional review tasks needed, False if ready for final assessment
        """
        self.logger.info("[REVIEWING_RESULTS] Reviewing subagent investigation results...")

        needs_more_tasks = False

        for task_id, task in self.subagent_tasks.items():
            # Skip tasks already processed in previous iterations
            if task_id in self.processed_task_ids:
                continue

            if task.status == TaskStatus.COMPLETED and task.result:
                self.logger.info(f"[REVIEWING_RESULTS] Results from {task.agent_name}")

                findings_data = task.result.get("findings", [])
                for finding_data in findings_data:
                    finding = SecurityFinding(**finding_data)

                    # Skip duplicate findings by ID
                    if finding.id in self.processed_finding_ids:
                        self.logger.info(f"  [DUP] Skipping duplicate finding: {finding.id}")
                        continue

                    self.findings.append(finding)
                    self.processed_finding_ids.add(finding.id)
                    self.logger.info(f"  [+] {finding.severity}: {finding.title}")

                    # Mark todo as completed
                    todo = self.todos.get(task.todo_id)
                    if todo:
                        todo.status = TodoStatus.COMPLETED
                        todo.findings.append(finding.id)

                        # Check if finding needs additional review
                        if finding.requires_review:
                            needs_more_tasks = True

                # Mark todo as processed (not task_id, since delegation checks todo_id)
                self.processed_task_ids.add(task.todo_id)

        self.logger.info(f"[REVIEWING_RESULTS] Total findings so far: {len(self.findings)}")

        # Check if all todos are complete
        completed_count = sum(1 for t in self.todos.values() if t.status == TodoStatus.COMPLETED)
        total_count = len(self.todos)
        self.logger.info(f"[REVIEWING_RESULTS] Todos completed: {completed_count}/{total_count}")

        return needs_more_tasks

    async def _create_review_tasks(self):
        """
        CREATING_REVIEW_TASKS state handler.

        Create additional review tasks based on findings that require review.
        """
        self.logger.info("[CREATING_REVIEW_TASKS] Creating additional review tasks...")

        review_todo_id = 100  # Use different ID range for review tasks

        # Group findings by type for targeted review
        critical_findings = [
            f for f in self.findings if f.severity == "critical" and f.requires_review
        ]
        high_findings = [f for f in self.findings if f.severity == "high" and f.requires_review]

        if critical_findings:
            self.todos[f"todo_{review_todo_id}"] = SecurityTodo(
                id=f"todo_{review_todo_id}",
                title="Critical security deep dive",
                description=f"Perform deep analysis of {len(critical_findings)} critical findings",
                priority=TodoPriority.HIGH,
                agent="deep_security_analyst",
                dependencies=[t.findings[0] for t in self.todos.values() if t.findings],
            )
            review_todo_id += 1

        if high_findings:
            self.todos[f"todo_{review_todo_id}"] = SecurityTodo(
                id=f"todo_{review_todo_id}",
                title="High-severity impact analysis",
                description=f"Analyze potential impact of {len(high_findings)} high-severity findings",
                priority=TodoPriority.HIGH,
                agent="impact_analyst",
                dependencies=[t.findings[0] for t in self.todos.values() if t.findings],
            )
            review_todo_id += 1

        self.logger.info(
            f"[CREATING_REVIEW_TASKS] Created {review_todo_id - 100} additional review todos"
        )

    async def _generate_final_assessment(self) -> SecurityAssessment:
        """
        FINAL_ASSESSMENT state handler.

        Generate final security assessment based on all findings.
        Applies confidence threshold filtering and logs confidence scores.
        """
        self.logger.info("[FINAL_ASSESSMENT] Generating final security assessment...")
        self.logger.info(f"[FINAL_ASSESSMENT] Confidence threshold: {self.confidence_threshold}")

        # Apply confidence threshold filtering with safe fallback for malformed/missing values
        filtered_findings = []
        filtered_out_count = 0

        for finding in self.findings:
            confidence = finding.confidence_score
            if not isinstance(confidence, (int, float)):
                confidence = 0.50
                self.logger.warning(
                    f"[CONFIDENCE_FILTER] Malformed confidence for finding {finding.id}, using fallback 0.50"
                )

            passes_threshold = confidence >= self.confidence_threshold
            self.logger.info(
                format_log_with_redaction(
                    message="[CONFIDENCE_FILTER] Finding evaluated",
                    finding_id=finding.id,
                    confidence_score=str(confidence),
                    threshold=str(self.confidence_threshold),
                    passed="yes" if passes_threshold else "no",
                )
            )

            if passes_threshold:
                filtered_findings.append(finding)
            else:
                filtered_out_count += 1

        self.logger.info(
            f"[FINAL_ASSESSMENT] Filtered out {filtered_out_count} findings below confidence threshold"
        )

        # Count findings by severity (only those passing threshold)
        critical_count = sum(1 for f in filtered_findings if f.severity == "critical")
        high_count = sum(1 for f in filtered_findings if f.severity == "high")
        medium_count = sum(1 for f in filtered_findings if f.severity == "medium")
        low_count = sum(1 for f in filtered_findings if f.severity == "low")

        # Determine overall severity
        if critical_count > 0:
            overall_severity = "critical"
        elif high_count > 0:
            overall_severity = "high"
        elif medium_count > 0:
            overall_severity = "medium"
        else:
            overall_severity = "low"

        # Determine merge recommendation
        if critical_count > 0 or high_count > 0:
            merge_recommendation = "block"
        elif medium_count > 0:
            merge_recommendation = "needs_changes"
        else:
            merge_recommendation = "approve"

        # Build summary
        summary_parts = [
            f"Security review completed with {len(filtered_findings)} findings (filtered out {filtered_out_count} below confidence threshold).",
            f"Critical: {critical_count}, High: {high_count}, Medium: {medium_count}, Low: {low_count}.",
            f"Overall severity: {overall_severity}",
            f"Merge recommendation: {merge_recommendation}",
        ]
        summary = " ".join(summary_parts)

        assessment = SecurityAssessment(
            overall_severity=overall_severity,
            total_findings=len(filtered_findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            merge_recommendation=merge_recommendation,
            findings=filtered_findings,
            summary=summary,
            notes=[
                f"Review completed in {self.iteration_count} iteration(s)",
                f"{len(self.todos)} todos created and processed",
                f"{len(self.subagent_tasks)} subagent tasks delegated",
                f"Confidence threshold: {self.confidence_threshold}",
                f"Filtered out {filtered_out_count} findings below threshold",
            ],
        )

        self.logger.info("[FINAL_ASSESSMENT] Assessment generated:")
        self.logger.info(f"  Overall severity: {assessment.overall_severity}")
        self.logger.info(f"  Total findings: {assessment.total_findings}")
        self.logger.info(f"  Merge recommendation: {assessment.merge_recommendation}")
        self.logger.info(f"  Summary: {assessment.summary}")

        return assessment


# =============================================================================
# Example Usage
# =============================================================================


async def example_usage():
    """Demonstrate FSM-based security reviewer with subagent delegation."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    logger.info("Initializing FSM-based Security Reviewer Agent...")

    # In a real implementation, you would:
    # 1. Create AgentRuntime with your LLM configuration
    # 2. Create AgentOrchestrator with the runtime
    # 3. Create SecurityReviewerAgent with the orchestrator

    # For this example, we'll use a mock orchestrator
    from unittest.mock import AsyncMock, MagicMock

    mock_runtime = MagicMock(spec=AgentRuntime)
    mock_runtime.execute_agent = AsyncMock()
    orchestrator = AgentOrchestrator(mock_runtime)

    # Create session ID
    session_id = "example_session_001"

    # Create security reviewer agent
    reviewer = SecurityReviewerAgent(
        orchestrator=orchestrator,
        session_id=session_id,
    )

    try:
        # Run security review on current repository
        repo_root = str(Path(__file__).parent.parent.parent.parent)
        base_ref = "main"
        head_ref = "HEAD"

        assessment = await reviewer.run_review(
            repo_root=repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
        )

        # Display assessment
        logger.info("")
        logger.info("=" * 60)
        logger.info("FINAL SECURITY ASSESSMENT")
        logger.info("=" * 60)
        logger.info(f"Overall Severity: {assessment.overall_severity}")
        logger.info(f"Total Findings: {assessment.total_findings}")
        logger.info(f"")
        logger.info(f"Breakdown:")
        logger.info(f"  Critical: {assessment.critical_count}")
        logger.info(f"  High: {assessment.high_count}")
        logger.info(f"  Medium: {assessment.medium_count}")
        logger.info(f"  Low: {assessment.low_count}")
        logger.info(f"")
        logger.info(f"Merge Recommendation: {assessment.merge_recommendation}")
        logger.info(f"")
        logger.info(f"Summary: {assessment.summary}")
        logger.info(f"")
        logger.info(f"Notes:")
        for note in assessment.notes:
            logger.info(f"  - {note}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("DETAILED FINDINGS")
        logger.info("=" * 60)
        for i, finding in enumerate(assessment.findings, 1):
            logger.info(f"\nFinding #{i}:")
            logger.info(f"  ID: {finding.id}")
            logger.info(f"  Severity: {finding.severity}")
            logger.info(f"  Title: {finding.title}")
            logger.info(f"  Description: {finding.description}")
            logger.info(f"  Evidence: {finding.evidence}")
            if finding.file_path:
                logger.info(f"  File: {finding.file_path}")
                if finding.line_number:
                    logger.info(f"  Line: {finding.line_number}")
            if finding.recommendation:
                logger.info(f"  Recommendation: {finding.recommendation}")

    except Exception as e:
        logger.error(f"Security review failed: {e}", exc_info=True)
        raise


async def main():
    """Run the example."""
    try:
        await example_usage()
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Example interrupted by user")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Example failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
