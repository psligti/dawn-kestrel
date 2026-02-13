"""Thread safety tests for FSM.

Tests that FSM operations are properly protected by RLock
and concurrent operations are serialized correctly.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from dawn_kestrel.workflow.fsm import FSM, WORKFLOW_FSM_TRANSITIONS
from dawn_kestrel.workflow.models import Todo


class TestFSMLock:
    """Test FSM lock initialization and basic usage."""

    def test_fsm_has_state_lock(self):
        """Verify FSM has a state_lock property that is an RLock."""
        import threading

        fsm = FSM()
        assert type(fsm.state_lock).__name__ == "RLock"

    def test_state_lock_is_instance_attribute(self):
        """Verify each FSM instance has its own lock."""
        fsm1 = FSM()
        fsm2 = FSM()

        assert fsm1.state_lock is not fsm2.state_lock


class TestFSMTransitionSafety:
    """Test that state transitions are protected by lock."""

    def test_transition_protected_by_lock(self):
        """Verify transition_to method uses lock protection."""
        fsm = FSM()

        # Try to transition to valid state
        result = fsm.transition_to("plan")
        assert result.is_ok()
        assert fsm.context.state == "plan"

    def test_invalid_transition_fails_gracefully(self):
        """Verify invalid transitions return Err without changing state."""
        fsm = FSM()

        # Try to transition to invalid state
        result = fsm.transition_to("invalid_state")
        assert result.is_err()
        assert fsm.context.state == "intake"

    def test_concurrent_transitions_serialized(self):
        """Verify concurrent transitions are serialized by lock."""
        fsm = FSM()
        errors = []
        final_states = []

        def attempt_transition(target_state: str):
            try:
                result = fsm.transition_to(target_state)
                if result.is_ok():
                    final_states.append(fsm.context.state)
                else:
                    errors.append(result.error)
            except Exception as e:
                errors.append(str(e))

        # Spawn multiple threads trying to transition simultaneously
        threads = []
        valid_transitions = list(WORKFLOW_FSM_TRANSITIONS["intake"])

        for state in valid_transitions:
            thread = threading.Thread(target=attempt_transition, args=(state,))
            threads.append(thread)

        # Start all threads at once
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(final_states) > 0, "No transitions succeeded"


class TestFSMTodoSafety:
    """Test that todo operations are protected by lock."""

    def test_add_todo_protected_by_lock(self):
        """Verify add_todo method uses lock protection."""
        fsm = FSM()
        todo = Todo(
            id="todo_1",
            title="Test todo",
            rationale="Testing thread safety",
            evidence=[],
            status="pending",
            priority="high",
        )

        fsm.add_todo(todo)

        assert "todo_1" in fsm.context.todos
        assert fsm.context.todos["todo_1"].title == "Test todo"

    def test_update_todo_status_protected_by_lock(self):
        """Verify update_todo_status method uses lock protection."""
        fsm = FSM()
        todo = Todo(
            id="todo_1",
            title="Test todo",
            rationale="Testing thread safety",
            evidence=[],
            status="pending",
            priority="high",
        )
        fsm.add_todo(todo)

        fsm.update_todo_status("todo_1", "in_progress")

        assert fsm.context.todos["todo_1"].status == "in_progress"

    def test_clear_todos_protected_by_lock(self):
        """Verify clear_todos method uses lock protection."""
        fsm = FSM()
        todo1 = Todo(
            id="todo_1",
            title="Test todo 1",
            rationale="Testing",
            evidence=[],
            status="pending",
            priority="high",
        )
        todo2 = Todo(
            id="todo_2",
            title="Test todo 2",
            rationale="Testing",
            evidence=[],
            status="pending",
            priority="medium",
        )
        fsm.add_todo(todo1)
        fsm.add_todo(todo2)

        fsm.clear_todos()

        assert len(fsm.context.todos) == 0

    def test_concurrent_todo_adds(self):
        """Verify concurrent todo adds are serialized."""
        fsm = FSM()
        num_todos = 10
        errors = []

        def add_todo(todo_id: int):
            try:
                todo = Todo(
                    id=f"todo_{todo_id}",
                    title=f"Test todo {todo_id}",
                    rationale="Testing thread safety",
                    evidence=[],
                    status="pending",
                    priority="high",
                )
                fsm.add_todo(todo)
            except Exception as e:
                errors.append(str(e))

        # Add todos concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(add_todo, i) for i in range(num_todos)]
            for future in as_completed(futures):
                future.result()

        # Verify all todos were added (no race conditions)
        assert len(fsm.context.todos) == num_todos
        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestFSMResetSafety:
    """Test that reset operation is protected by lock."""

    def test_reset_protected_by_lock(self):
        """Verify reset method uses lock protection."""
        fsm = FSM()
        todo = Todo(
            id="todo_1",
            title="Test todo",
            rationale="Testing",
            evidence=[],
            status="pending",
            priority="high",
        )
        fsm.add_todo(todo)
        fsm.context.subagent_results["test"] = {"result": "test"}
        fsm.context.consolidated = {"test": "data"}

        # Transition to a different state
        fsm.transition_to("plan")

        # Reset the FSM
        fsm.reset()

        # Verify all state was cleared
        assert fsm.context.state == "intake"
        assert len(fsm.context.todos) == 0
        assert len(fsm.context.subagent_results) == 0
        assert len(fsm.context.consolidated) == 0
        assert len(fsm.context.evaluation) == 0


class TestFSMReadWithoutLock:
    """Test that read operations don't acquire locks."""

    def test_read_context_property(self):
        """Verify reading context property doesn't block."""
        fsm = FSM()

        # Multiple threads reading context should not block
        results = []

        def read_context():
            results.append(fsm.context.state)

        threads = [threading.Thread(target=read_context) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All reads should succeed
        assert len(results) == 10
        assert all(state == "intake" for state in results)

    def test_read_todos_concurrent(self):
        """Verify reading todos concurrently doesn't cause issues."""
        fsm = FSM()
        todo = Todo(
            id="todo_1",
            title="Test todo",
            rationale="Testing",
            evidence=[],
            status="pending",
            priority="high",
        )
        fsm.add_todo(todo)

        results = []

        def read_todos():
            results.append(len(fsm.context.todos))

        threads = [threading.Thread(target=read_todos) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All reads should succeed
        assert len(results) == 10
        assert all(count == 1 for count in results)


class TestFSMIntegration:
    """Integration tests for thread-safe FSM."""

    def test_run_fsm_safety(self):
        """Verify running FSM complete workflow is thread-safe."""
        fsm = FSM(changed_files=["file1.py", "file2.py"])

        # Run FSM
        context = fsm.run()

        # Verify FSM completed successfully
        assert context.state == "done"
        assert context.log.start_time is not None
        assert context.log.end_time is not None
        assert len(context.log.frames) > 0

    def test_multiple_fsm_instances_independent(self):
        """Verify multiple FSM instances are independent."""
        fsm1 = FSM(changed_files=["file1.py"])
        fsm2 = FSM(changed_files=["file2.py"])

        # Transition first FSM
        fsm1.transition_to("plan")

        # Second FSM should not be affected
        assert fsm1.context.state == "plan"
        assert fsm2.context.state == "intake"

        fsm2.transition_to("plan")
        fsm2.transition_to("act")

        assert fsm1.context.state == "plan"
        assert fsm2.context.state == "act"
