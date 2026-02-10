"""Tests for FSM security reviewer deduplication and task state persistence.

Tests TD-001, TD-002, TD-003:
- Finding deduplication across iterations
- Task state persistence (no redelegation)
- Todo completion count accuracy
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from dawn_kestrel.agents.review.fsm_security import (
    SecurityReviewerAgent,
    SecurityFinding,
    SecurityTodo,
    TodoStatus,
    ReviewState,
)
from dawn_kestrel.core.agent_task import TaskStatus, create_agent_task


class TestFindingDeduplication:
    """Test that duplicate findings are not reported multiple times."""

    @pytest.mark.asyncio
    async def test_dedup_across_repeated_iterations(self):
        """Verify that findings with identical IDs are reported once across iterations.

        Simulates multiple iterations where subagents return the same findings.
        Ensures processed_finding_ids prevents duplicates in final output.
        """
        # Create a mock orchestrator
        orchestrator = Mock(spec=object)

        # Create security reviewer
        reviewer = SecurityReviewerAgent(orchestrator=orchestrator, session_id="test-session")

        # Create mock context
        reviewer.context = Mock()
        reviewer.context.changed_files = ["src/auth.py", "src/api.py"]
        reviewer.context.diff = "mock diff content"
        reviewer.context.diff_size = 5000

        # Create initial todos
        await reviewer._create_initial_todos()

        # Get first todo ID
        first_todo_id = list(reviewer.todos.keys())[0]

        # Create mock subagent task with findings
        task_id_1 = "task_001"
        task_id_2 = "task_002"

        reviewer.subagent_tasks[task_id_1] = Mock(
            task_id=task_id_1,
            todo_id=first_todo_id,
            status=TaskStatus.COMPLETED,
            agent_name="secret_scanner",
            result={
                "findings": [
                    {
                        "id": "sec_001",
                        "severity": "critical",
                        "title": "Hardcoded API key",
                        "description": "API key exposed in source code",
                        "evidence": "API_KEY = 'sk-1234567890'",
                        "file_path": "src/auth.py",
                        "line_number": 42,
                        "requires_review": False,
                    },
                    {
                        "id": "sec_002",
                        "severity": "high",
                        "title": "SQL injection vulnerability",
                        "description": "Unsanitized user input in SQL query",
                        "evidence": "query = f'SELECT * FROM users WHERE id={user_input}'",
                        "file_path": "src/api.py",
                        "line_number": 123,
                        "requires_review": False,
                    },
                ]
            },
        )

        reviewer.subagent_tasks[task_id_2] = Mock(
            task_id=task_id_2,
            todo_id=first_todo_id,
            status=TaskStatus.COMPLETED,
            agent_name="injection_scanner",
            result={
                # Note: sec_001 is duplicate from task_001
                "findings": [
                    {
                        "id": "sec_001",
                        "severity": "critical",
                        "title": "Hardcoded API key",
                        "description": "API key exposed in source code",
                        "evidence": "API_KEY = 'sk-1234567890'",
                        "file_path": "src/auth.py",
                        "line_number": 42,
                        "requires_review": False,
                    },
                    {
                        "id": "sec_003",
                        "severity": "medium",
                        "title": "Missing input validation",
                        "description": "No validation on user-provided data",
                        "evidence": "def process_input(data): return data.upper()",
                        "file_path": "src/api.py",
                        "line_number": 200,
                        "requires_review": False,
                    },
                ]
            },
        )

        # Process results in iteration 1
        await reviewer._review_investigation_results()

        # Verify findings from iteration 1
        assert len(reviewer.findings) == 3, (
            f"Expected 3 findings in iteration 1, got {len(reviewer.findings)}"
        )
        finding_ids = [f.id for f in reviewer.findings]
        assert "sec_001" in finding_ids
        assert "sec_002" in finding_ids
        assert "sec_003" in finding_ids

        # Simulate second iteration with same findings (simulating FSM loop)
        # Create new task objects but same finding IDs
        task_id_3 = "task_003"
        reviewer.subagent_tasks[task_id_3] = Mock(
            task_id=task_id_3,
            todo_id=first_todo_id,
            status=TaskStatus.COMPLETED,
            agent_name="secret_scanner",
            result={
                "findings": [
                    {
                        "id": "sec_001",
                        "severity": "critical",
                        "title": "Hardcoded API key",
                        "description": "API key exposed in source code",
                        "evidence": "API_KEY = 'sk-1234567890'",
                        "file_path": "src/auth.py",
                        "line_number": 42,
                        "requires_review": False,
                    },
                    {
                        "id": "sec_002",
                        "severity": "high",
                        "title": "SQL injection vulnerability",
                        "description": "Unsanitized user input in SQL query",
                        "evidence": "query = f'SELECT * FROM users WHERE id={user_input}'",
                        "file_path": "src/api.py",
                        "line_number": 123,
                        "requires_review": False,
                    },
                ]
            },
        )

        # Process results in iteration 2
        await reviewer._review_investigation_results()

        # Verify NO duplicate findings in iteration 2
        assert len(reviewer.findings) == 3, (
            f"Expected still 3 findings after iteration 2 (no duplicates), got {len(reviewer.findings)}"
        )
        finding_ids = [f.id for f in reviewer.findings]
        assert finding_ids.count("sec_001") == 1, (
            f"sec_001 should appear exactly once, appears {finding_ids.count('sec_001')} times"
        )
        assert finding_ids.count("sec_002") == 1, (
            f"sec_002 should appear exactly once, appears {finding_ids.count('sec_002')} times"
        )
        assert finding_ids.count("sec_003") == 1, (
            f"sec_003 should appear exactly once, appears {finding_ids.count('sec_003')} times"
        )


class TestTaskRedelegationPrevention:
    """Test that completed tasks are not redelegated."""

    @pytest.mark.asyncio
    async def test_completed_task_not_redelegated(self):
        """Verify that todos whose tasks are processed are not redelegated.

        Simulates the FSM loop where _review_investigation_results() marks
        tasks as processed (via processed_task_ids), and then _delegate_investigation_tasks()
        should skip those todos.
        """
        # Create a mock orchestrator
        orchestrator = Mock(spec=object)

        # Create security reviewer
        reviewer = SecurityReviewerAgent(orchestrator=orchestrator, session_id="test-session")

        # Create mock context
        reviewer.context = Mock()
        reviewer.context.changed_files = ["src/auth.py"]
        reviewer.context.diff = "mock diff"
        reviewer.context.diff_size = 1000

        # Create initial todos
        await reviewer._create_initial_todos()

        # Store initial todo count
        initial_todo_count = len(reviewer.todos)
        assert initial_todo_count > 0, "Should have initial todos"

        # Get first todo ID
        first_todo_id = list(reviewer.todos.keys())[0]
        first_todo = reviewer.todos[first_todo_id]
        assert first_todo.status == TodoStatus.PENDING

        # Mark the todo as COMPLETED
        first_todo.status = TodoStatus.COMPLETED

        # Add the todo_id to processed_task_ids (simulating previous iteration completion)
        # This is what _review_investigation_results() does when processing a task
        reviewer.processed_task_ids.add(first_todo_id)

        # Track whether the todo gets delegated
        delegated_todos = []

        # Patch create_agent_task to track which todos get delegated
        original_create_agent_task = create_agent_task

        def mock_create_agent_task(*args, **kwargs):
            task = original_create_agent_task(*args, **kwargs)
            # Extract todo_id from metadata
            if "metadata" in kwargs:
                todo_id = kwargs["metadata"].get("todo_id")
                delegated_todos.append(todo_id)
            return task

        with (
            patch.object(reviewer, "_simulate_subagent_execution", new_callable=AsyncMock),
            patch(
                "dawn_kestrel.agents.review.fsm_security.create_agent_task",
                side_effect=mock_create_agent_task,
            ),
        ):
            await reviewer._delegate_investigation_tasks()

        # Verify that the COMPLETED todo was NOT delegated
        assert first_todo_id not in delegated_todos, (
            f"Completed todo {first_todo_id} should not be delegated"
        )

        # Verify that other PENDING todos were delegated
        # (At least some other todos should have been delegated)
        assert len(delegated_todos) > 0, "At least one other todo should have been delegated"


class TestTodoCompletionCount:
    """Test that todo completion count reflects actual progress."""

    @pytest.mark.asyncio
    async def test_todo_completion_count_accuracy(self):
        """Verify that 'completed/total' fraction accurately reflects progress.

        Ensures that only COMPLETED todos are counted, not PENDING or IN_PROGRESS.
        """
        # Create a mock orchestrator
        orchestrator = Mock(spec=object)

        # Create security reviewer
        reviewer = SecurityReviewerAgent(orchestrator=orchestrator, session_id="test-session")

        # Create mock context
        reviewer.context = Mock()
        reviewer.context.changed_files = ["src/file1.py", "src/file2.py", "src/file3.py"]
        reviewer.context.diff = "mock diff"
        reviewer.context.diff_size = 3000

        # Create initial todos
        await reviewer._create_initial_todos()

        # Store initial todo count
        total_todos = len(reviewer.todos)
        assert total_todos > 0, "Should have initial todos"

        # Initially, all todos should be PENDING
        pending_count = sum(1 for t in reviewer.todos.values() if t.status == TodoStatus.PENDING)
        completed_count = sum(
            1 for t in reviewer.todos.values() if t.status == TodoStatus.COMPLETED
        )

        assert pending_count == total_todos, (
            f"Initially all {total_todos} todos should be PENDING, got {pending_count}"
        )
        assert completed_count == 0, (
            f"Initially no todos should be COMPLETED, got {completed_count}"
        )

        # Mark some todos as COMPLETED
        todo_ids = list(reviewer.todos.keys())
        todos_to_complete = todo_ids[: min(3, len(todo_ids))]

        for todo_id in todos_to_complete:
            reviewer.todos[todo_id].status = TodoStatus.COMPLETED

        # Add completed todos to processed_task_ids (simulating iteration completion)
        for todo_id in todos_to_complete:
            reviewer.processed_task_ids.add(todo_id)

        # Re-compute counts
        completed_count = sum(
            1 for t in reviewer.todos.values() if t.status == TodoStatus.COMPLETED
        )
        pending_count = sum(1 for t in reviewer.todos.values() if t.status == TodoStatus.PENDING)

        # Verify counts
        assert completed_count == len(todos_to_complete), (
            f"Expected {len(todos_to_complete)} COMPLETED todos, got {completed_count}"
        )
        assert pending_count == total_todos - len(todos_to_complete), (
            f"Expected {total_todos - len(todos_to_complete)} PENDING todos, got {pending_count}"
        )

        # Verify fraction is correct
        fraction = completed_count / total_todos
        expected_fraction = len(todos_to_complete) / total_todos
        assert fraction == expected_fraction, (
            f"Completion fraction {fraction} doesn't match expected {expected_fraction}"
        )
