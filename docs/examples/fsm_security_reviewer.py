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
from typing import Dict, List, Optional, Any
from pathlib import Path

from dawn_kestrel.core.agent_fsm import AgentFSMImpl
from dawn_kestrel.core.agent_task import TaskStatus, create_agent_task
from dawn_kestrel.agents.orchestrator import AgentOrchestrator
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
            ReviewState.FAILED,
        },
        ReviewState.FINAL_ASSESSMENT: {ReviewState.COMPLETED, ReviewState.FAILED},
        ReviewState.COMPLETED: {ReviewState.IDLE},  # Can restart
        ReviewState.FAILED: {ReviewState.IDLE},  # Can restart
    }

    def __init__(self, orchestrator: AgentOrchestrator, session_id: str):
        """Initialize the security reviewer agent.

        Args:
            orchestrator: AgentOrchestrator for task delegation
            session_id: Session ID for tracking
        """
        self.orchestrator = orchestrator
        self.session_id = session_id

        # FSM for lifecycle management
        self.fsm = AgentFSMImpl(initial_state=ReviewState.IDLE.value)

        # Review state data
        self.todos: Dict[str, SecurityTodo] = {}
        self.subagent_tasks: Dict[str, SubagentTask] = {}
        self.findings: List[SecurityFinding] = []
        self.context: Optional[ReviewContext] = None

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
                self.logger.info(f"Iteration {self.iteration_count} of {self.max_iterations}")
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
                    # Create additional review tasks
                    await self._transition_to(ReviewState.CREATING_REVIEW_TASKS)
                    await self._create_review_tasks()
                else:
                    # All tasks complete, proceed to final assessment
                    break

            # Final assessment
            await self._transition_to(ReviewState.FINAL_ASSESSMENT)
            assessment = await self._generate_final_assessment()

            await self._transition_to(ReviewState.COMPLETED)
            self.logger.info("")
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

        # Create initial todos based on exploration
        await self._create_initial_todos()

        self.logger.info(f"[INITIAL_EXPLORATION] Created {len(self.todos)} initial todos")

    async def _create_initial_todos(self):
        """Create initial todos based on exploration of changed files.

        The security reviewer analyzes WHAT changed and creates todos for
        WHAT NEEDS CHECKING. It does NOT do the checking itself.
        """
        self.logger.info("[INITIAL_EXPLORATION] Creating initial todos...")

        # Identify files by security relevance
        if not self.context or not self.context.changed_files:
            return

        auth_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["auth", "login", "session", "jwt", "token"])
        ]
        config_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["config", "env", "secret", "credential"])
        ]
        dependency_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["requirements", "pyproject", "package.json"])
        ]
        input_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["form", "input", "query", "param"])
        ]
        network_files = [
            f
            for f in self.context.changed_files
            if any(x in f.lower() for x in ["http", "request", "api", "client"])
        ]

        todo_id = 1

        # Create todos for each security category
        if auth_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review authentication and authorization code",
                description=f"Check {len(auth_files)} auth-related files for security issues: {', '.join(auth_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="auth_reviewer",
            )
            todo_id += 1

        if config_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Scan for secrets and credentials",
                description=f"Check {len(config_files)} config files for leaked secrets or credentials: {', '.join(config_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="secret_scanner",
            )
            todo_id += 1

        if dependency_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Audit dependencies for vulnerabilities",
                description=f"Check {len(dependency_files)} dependency files for known vulnerabilities: {', '.join(dependency_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="dependency_auditor",
            )
            todo_id += 1

        if input_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Check for input validation issues",
                description=f"Review {len(input_files)} files handling user input for injection risks: {', '.join(input_files[:3])}",
                priority=TodoPriority.HIGH,
                agent="input_validator",
            )
            todo_id += 1

        if network_files:
            self.todos[f"todo_{todo_id}"] = SecurityTodo(
                id=f"todo_{todo_id}",
                title="Review network communication security",
                description=f"Check {len(network_files)} network files for security issues: {', '.join(network_files[:3])}",
                priority=TodoPriority.MEDIUM,
                agent="network_reviewer",
            )
            todo_id += 1

        # General diff scan (always create)
        self.todos[f"todo_{todo_id}"] = SecurityTodo(
            id=f"todo_{todo_id}",
            title="Scan diff for security patterns",
            description="Use grep/ast-grep to scan the diff for common security vulnerabilities",
            priority=TodoPriority.MEDIUM,
            agent="pattern_scanner",
        )
        todo_id += 1

    async def _delegate_investigation_tasks(self):
        """
        DELEGATING_INVESTIGATION state handler.

        Delegate all pending todos to investigation subagents.

        The security reviewer DELEGATES - it does NOT investigate.
        Each todo becomes a task for an appropriate subagent.
        """
        self.logger.info("[DELEGATING_INVESTIGATION] Delegating tasks to subagents...")

        for todo_id, todo in self.todos.items():
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
        """Simulate subagent execution (for example purposes).

        A real implementation would delegate via orchestrator.
        Here we simulate different investigation results based on agent type.
        """
        await asyncio.sleep(0.5)  # Simulate work

        # Simulate findings based on agent type
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
        elif "auth" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_002",
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
        elif "input" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_003",
                        "severity": "high",
                        "title": "SQL injection risk",
                        "description": "User input used directly in SQL query without sanitization",
                        "evidence": f"query = f'SELECT * FROM users WHERE id = {{user_id}}'",
                        "file_path": "api/users.py",
                        "line_number": 156,
                        "recommendation": "Use parameterized queries or an ORM.",
                        "requires_review": True,
                    }
                ],
                "summary": "Reviewed input validation and found 1 high-severity issue.",
            }
        elif "dependency" in task.agent_name:
            task.result = {
                "findings": [
                    {
                        "id": "sec_004",
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
            if task.status == TaskStatus.COMPLETED and task.result:
                self.logger.info(f"[REVIEWING_RESULTS] Results from {task.agent_name}")

                # Process findings
                findings_data = task.result.get("findings", [])
                for finding_data in findings_data:
                    finding = SecurityFinding(**finding_data)
                    self.findings.append(finding)
                    self.logger.info(f"  [+] {finding.severity}: {finding.title}")

                    # Mark todo as completed
                    todo = self.todos.get(task.todo_id)
                    if todo:
                        todo.status = TodoStatus.COMPLETED
                        todo.findings.append(finding.id)

                        # Check if finding needs additional review
                        if finding.requires_review:
                            needs_more_tasks = True

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
        """
        self.logger.info("[FINAL_ASSESSMENT] Generating final security assessment...")

        # Count findings by severity
        critical_count = sum(1 for f in self.findings if f.severity == "critical")
        high_count = sum(1 for f in self.findings if f.severity == "high")
        medium_count = sum(1 for f in self.findings if f.severity == "medium")
        low_count = sum(1 for f in self.findings if f.severity == "low")

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
            f"Security review completed with {len(self.findings)} findings.",
            f"Critical: {critical_count}, High: {high_count}, Medium: {medium_count}, Low: {low_count}.",
            f"Overall severity: {overall_severity}",
            f"Merge recommendation: {merge_recommendation}",
        ]
        summary = " ".join(summary_parts)

        assessment = SecurityAssessment(
            overall_severity=overall_severity,
            total_findings=len(self.findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            merge_recommendation=merge_recommendation,
            findings=self.findings,
            summary=summary,
            notes=[
                f"Review completed in {self.iteration_count} iteration(s)",
                f"{len(self.todos)} todos created and processed",
                f"{len(self.subagent_tasks)} subagent tasks delegated",
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
