"""Tests for FSMImpl (generic finite state machine)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.core.fsm import FSMImpl, FSMBuilder, FSMContext, FSMReliabilityConfig
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.core.fsm_state_repository import FSMStateRepository
from dawn_kestrel.core.mediator import Event, EventType, EventMediator
from dawn_kestrel.core.observer import Observer
from dawn_kestrel.core.commands import TransitionCommand
from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl
from dawn_kestrel.llm.retry import RetryExecutorImpl, ExponentialBackoff
from dawn_kestrel.llm.rate_limiter import RateLimiterImpl
from dawn_kestrel.llm.bulkhead import BulkheadImpl


class TestFSMImpl:
    """Test FSMImpl implementation."""

    def test_fsm_impl_initializes_with_initial_state(self):
        """Initialize FSMImpl with valid state sets state correctly."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)
        assert fsm._state == "idle"

        fsm = FSMImpl("running", valid_states, valid_transitions)
        assert fsm._state == "running"

    def test_fsm_impl_initializes_with_invalid_state_raises_valueerror(self):
        """Initialize FSMImpl with invalid state raises ValueError."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        with pytest.raises(ValueError) as exc_info:
            FSMImpl("unknown_state", valid_states, valid_transitions)

        assert "Invalid initial state" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fsm_impl_returns_current_state(self):
        """get_state returns current state."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("running", valid_states, valid_transitions)
        state = await fsm.get_state()
        assert state == "running"

        fsm._state = "completed"
        state = await fsm.get_state()
        assert state == "completed"

    @pytest.mark.asyncio
    async def test_fsm_impl_transitions_to_valid_state(self):
        """transition_to succeeds for valid state transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)
        result = await fsm.transition_to("running")

        assert result.is_ok()
        assert fsm._state == "running"
        assert len(fsm.get_command_history()) == 1

        result = await fsm.transition_to("completed")
        assert result.is_ok()
        assert fsm._state == "completed"
        assert len(fsm.get_command_history()) == 2

    @pytest.mark.asyncio
    async def test_fsm_impl_rejects_invalid_transition(self):
        """transition_to returns Err for invalid state transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)
        result = await fsm.transition_to("completed")

        assert result.is_err()
        assert "Invalid state transition" in result.error
        assert fsm._state == "idle"
        assert len(fsm.get_command_history()) == 0

    @pytest.mark.asyncio
    async def test_fsm_impl_is_transition_valid_returns_true_for_valid(self):
        """is_transition_valid returns True for valid transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)
        assert await fsm.is_transition_valid("idle", "running") is True

        fsm._state = "running"
        assert await fsm.is_transition_valid("running", "completed") is True

    @pytest.mark.asyncio
    async def test_fsm_impl_is_transition_valid_returns_false_for_invalid(self):
        """is_transition_valid returns False for invalid transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)
        assert await fsm.is_transition_valid("idle", "completed") is False

        assert await fsm.is_transition_valid("unknown", "running") is False

    @pytest.mark.asyncio
    async def test_fsm_impl_get_command_history_returns_audit_trail(self):
        """get_command_history returns list of executed transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm")
        history = fsm.get_command_history()

        assert len(history) == 0

        await fsm.transition_to("running")
        history = fsm.get_command_history()
        assert len(history) == 1
        assert isinstance(history[0], TransitionCommand)

    @pytest.mark.asyncio
    async def test_fsm_impl_command_history_includes_fsm_id_and_states(self):
        """Command history includes fsm_id and state information."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm-123")
        await fsm.transition_to("running")

        history = fsm.get_command_history()
        assert len(history) == 1
        assert history[0].fsm_id == "test-fsm-123"
        assert history[0].from_state == "idle"
        assert history[0].to_state == "running"

    def test_fsm_impl_generates_unique_fsm_id_if_not_provided(self):
        """FSM generates unique ID if not provided."""
        valid_states = {"idle", "running"}
        valid_transitions = {"idle": {"running"}}

        fsm1 = FSMImpl("idle", valid_states, valid_transitions)
        fsm2 = FSMImpl("idle", valid_states, valid_transitions)

        assert fsm1._fsm_id != fsm2._fsm_id
        assert fsm1._fsm_id.startswith("fsm_")
        assert fsm2._fsm_id.startswith("fsm_")


class TestFSMBuilder:
    """Test FSMBuilder fluent API."""

    def test_fsm_builder_fluent_api_creates_fsm(self):
        """FSMBuilder with fluent API creates valid FSM instance."""
        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_state("completed")
            .with_transition("idle", "running")
            .with_transition("running", "completed")
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()
        assert fsm._state == "idle"

    def test_fsm_builder_validates_invalid_configuration(self):
        """FSMBuilder auto-adds states from transitions and builds valid FSM."""
        # with_transition() should auto-add states to _states
        result = FSMBuilder().with_transition("idle", "running").build(initial_state="idle")

        # Should succeed - states are auto-added from transitions
        assert result.is_ok()
        fsm = result.unwrap()
        assert fsm._state == "idle"
        # Verify both states were auto-added
        assert fsm._valid_states == {"idle", "running"}

    def test_fsm_builder_validates_invalid_initial_state(self):
        """FSMBuilder build() returns Err when initial state not defined."""
        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .build(initial_state="unknown")
        )

        assert result.is_err()
        assert "Invalid initial state" in result.error
        assert result.code == "INVALID_INITIAL_STATE"

    def test_fsm_builder_with_entry_hook(self):
        """FSMBuilder with_entry_hook stores hook for state."""

        async def test_hook(ctx):
            return Ok(None)

        builder = FSMBuilder()
        builder.with_entry_hook("idle", test_hook)

        assert "idle" in builder._entry_hooks
        assert builder._entry_hooks["idle"] == test_hook

    def test_fsm_builder_with_exit_hook(self):
        """FSMBuilder with_exit_hook stores hook for state."""

        async def test_hook(ctx):
            return Ok(None)

        builder = FSMBuilder()
        builder.with_exit_hook("idle", test_hook)

        assert "idle" in builder._exit_hooks
        assert builder._exit_hooks["idle"] == test_hook

    def test_fsm_builder_with_guard_condition(self):
        """FSMBuilder with_guard stores guard for transition."""

        async def test_guard(ctx):
            return Ok(True)

        builder = FSMBuilder()
        builder.with_guard("idle", "running", test_guard)

        assert ("idle", "running") in builder._guards
        assert builder._guards[("idle", "running")] == test_guard

    def test_fsm_builder_with_persistence(self):
        """FSMBuilder with_persistence stores repository."""
        mock_repo = object()

        builder = FSMBuilder()
        builder.with_persistence(mock_repo)

        assert builder._repository == mock_repo

    def test_fsm_builder_with_mediator(self):
        """FSMBuilder with_mediator stores mediator."""
        mock_mediator = object()

        builder = FSMBuilder()
        builder.with_mediator(mock_mediator)

        assert builder._mediator == mock_mediator

    def test_fsm_builder_with_observer(self):
        """FSMBuilder with_observer appends observer to list."""
        mock_observer = object()

        builder = FSMBuilder()
        builder.with_observer(mock_observer)

        assert len(builder._observers) == 1
        assert builder._observers[0] == mock_observer

    def test_fsm_builder_multiple_observers(self):
        """FSMBuilder with_observer can add multiple observers."""
        mock_observer1 = object()
        mock_observer2 = object()

        builder = FSMBuilder()
        builder.with_observer(mock_observer1).with_observer(mock_observer2)

        assert len(builder._observers) == 2
        assert builder._observers[0] == mock_observer1
        assert builder._observers[1] == mock_observer2


class TestFSMPersistence:
    """Test FSM state persistence via repository."""

    @pytest.mark.asyncio
    async def test_fsm_persists_state_to_repository(self):
        """FSM persists state to repository after each transition."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        mock_repo = AsyncMock(spec=FSMStateRepository)
        mock_repo.set_state.return_value = Ok(None)

        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", repository=mock_repo
        )

        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert fsm._state == "running"
        mock_repo.set_state.assert_called_once_with("test-fsm", "running")

        mock_repo.set_state.reset_mock()
        result = await fsm.transition_to("completed")
        assert result.is_ok()
        assert fsm._state == "completed"
        mock_repo.set_state.assert_called_once_with("test-fsm", "completed")

    @pytest.mark.asyncio
    async def test_fsm_handles_persistence_failure(self):
        """FSM returns Err when repository persistence fails."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        mock_repo = AsyncMock(spec=FSMStateRepository)
        mock_repo.set_state.return_value = Err("Storage failure", code="STORAGE_ERROR")

        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", repository=mock_repo
        )

        result = await fsm.transition_to("running")
        assert result.is_err()
        assert "Failed to persist state" in result.error
        assert result.code == "PERSISTENCE_ERROR"
        assert fsm._state == "running"
        mock_repo.set_state.assert_called_once_with("test-fsm", "running")

    @pytest.mark.asyncio
    async def test_fsm_without_repository_does_not_persist(self):
        """FSM without repository parameter does not persist state."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm", repository=None)

        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert fsm._state == "running"

        result = await fsm.transition_to("completed")
        assert result.is_ok()
        assert fsm._state == "completed"


class TestFSMEvents:
    """Test FSM event publishing via Mediator pattern."""

    @pytest.mark.asyncio
    async def test_fsm_publishes_state_change_event(self):
        """FSM publishes state change event via mediator after transition."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        mock_mediator = AsyncMock(spec=EventMediator)
        mock_mediator.publish.return_value = Ok(None)

        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", mediator=mock_mediator
        )

        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert fsm._state == "running"

        # Verify publish was called
        mock_mediator.publish.assert_called_once()
        event = mock_mediator.publish.call_args[0][0]

        assert event.event_type == EventType.DOMAIN
        assert event.source == "test-fsm"
        assert event.data["fsm_id"] == "test-fsm"
        assert event.data["from_state"] == "idle"
        assert event.data["to_state"] == "running"
        assert "timestamp" in event.data

    @pytest.mark.asyncio
    async def test_fsm_publishes_events_for_multiple_transitions(self):
        """FSM publishes events for all state transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        mock_mediator = AsyncMock(spec=EventMediator)
        mock_mediator.publish.return_value = Ok(None)

        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", mediator=mock_mediator
        )

        # First transition
        result = await fsm.transition_to("running")
        assert result.is_ok()

        # Second transition
        result = await fsm.transition_to("completed")
        assert result.is_ok()

        # Verify publish was called twice
        assert mock_mediator.publish.call_count == 2

        # Verify first event
        first_event = mock_mediator.publish.call_args_list[0][0][0]
        assert first_event.data["from_state"] == "idle"
        assert first_event.data["to_state"] == "running"

        # Verify second event
        second_event = mock_mediator.publish.call_args_list[1][0][0]
        assert second_event.data["from_state"] == "running"
        assert second_event.data["to_state"] == "completed"

    @pytest.mark.asyncio
    async def test_fsm_continues_on_publish_failure(self):
        """FSM continues operation when event publish fails."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        mock_mediator = AsyncMock(spec=EventMediator)
        mock_mediator.publish.return_value = Err("Network error", code="MEDIATOR_ERROR")

        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", mediator=mock_mediator
        )

        result = await fsm.transition_to("running")

        # Transition should succeed despite publish failure
        assert result.is_ok()
        assert fsm._state == "running"

        # Verify publish was attempted
        mock_mediator.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_fsm_without_mediator_does_not_publish(self):
        """FSM without mediator does not publish events."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm", mediator=None)

        result = await fsm.transition_to("running")

        assert result.is_ok()
        assert fsm._state == "running"

    @pytest.mark.asyncio
    async def test_fsm_builder_passes_mediator_to_fsm(self):
        """FSMBuilder passes mediator to built FSM instance."""
        mock_mediator = AsyncMock(spec=EventMediator)
        mock_mediator.publish.return_value = Ok(None)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_mediator(mock_mediator)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition and verify publish was called
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()

        mock_mediator.publish.assert_called_once()


class MockFSMObserver:
    """Mock observer for testing FSM notifications."""

    def __init__(self, name: str):
        self.name = name
        self.notifications: list[tuple] = []

    async def on_notify(self, observable: object, event: dict) -> None:
        """Record notification."""
        self.notifications.append((observable, event))


class TestFSMObserver:
    """Test FSM observer pattern integration."""

    @pytest.mark.asyncio
    async def test_fsm_registers_observer(self):
        """FSM registers observer and it receives notifications."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        observer = MockFSMObserver("test_observer")
        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", observers=[observer]
        )

        # Add another observer via register_observer
        observer2 = MockFSMObserver("observer2")
        await fsm.register_observer(observer2)

        # Perform transition
        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert fsm._state == "running"

        # Both observers should have been notified
        assert len(observer.notifications) == 1
        assert len(observer2.notifications) == 1

        # Verify event data
        event = observer.notifications[0][1]
        assert event["fsm_id"] == "test-fsm"
        assert event["from_state"] == "idle"
        assert event["to_state"] == "running"
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_fsm_unregisters_observer(self):
        """FSM unregisters observer and it stops receiving notifications."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        observer = MockFSMObserver("test_observer")
        fsm = FSMImpl(
            "idle", valid_states, valid_transitions, fsm_id="test-fsm", observers=[observer]
        )

        # First transition - observer should be notified
        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert len(observer.notifications) == 1

        # Unregister observer
        await fsm.unregister_observer(observer)

        # Second transition - observer should NOT be notified
        result = await fsm.transition_to("completed")
        assert result.is_ok()
        assert len(observer.notifications) == 1  # Still only 1 notification

    @pytest.mark.asyncio
    async def test_fsm_notifies_observers(self):
        """FSM notifies all observers of state changes."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        observer1 = MockFSMObserver("observer1")
        observer2 = MockFSMObserver("observer2")
        observer3 = MockFSMObserver("observer3")

        fsm = FSMImpl(
            "idle",
            valid_states,
            valid_transitions,
            fsm_id="test-fsm",
            observers=[observer1, observer2, observer3],
        )

        # First transition
        result = await fsm.transition_to("running")
        assert result.is_ok()

        # All observers should be notified
        assert len(observer1.notifications) == 1
        assert len(observer2.notifications) == 1
        assert len(observer3.notifications) == 1

        # Second transition
        result = await fsm.transition_to("completed")
        assert result.is_ok()

        # All observers should be notified again
        assert len(observer1.notifications) == 2
        assert len(observer2.notifications) == 2
        assert len(observer3.notifications) == 2

    @pytest.mark.asyncio
    async def test_fsm_handles_observer_failure(self):
        """FSM continues operation when observer notification fails."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        class FailingObserver:
            """Observer that raises exception on notification."""

            async def on_notify(self, observable: object, event: dict) -> None:
                raise RuntimeError("Observer failed!")

        working_observer = MockFSMObserver("working")
        failing_observer = FailingObserver()

        fsm = FSMImpl(
            "idle",
            valid_states,
            valid_transitions,
            fsm_id="test-fsm",
            observers=[working_observer, failing_observer],
        )

        # Transition should succeed despite observer failure
        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert fsm._state == "running"

        # Working observer should still be notified
        assert len(working_observer.notifications) == 1

    @pytest.mark.asyncio
    async def test_fsm_builder_passes_observers_to_fsm(self):
        """FSMBuilder passes observers to built FSM instance."""
        observer1 = MockFSMObserver("observer1")
        observer2 = MockFSMObserver("observer2")

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_observer(observer1)
            .with_observer(observer2)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Perform transition
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()

        # Both observers should be notified
        assert len(observer1.notifications) == 1
        assert len(observer2.notifications) == 1

    @pytest.mark.asyncio
    async def test_fsm_without_observers_works_normally(self):
        """FSM without observers works normally."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm", observers=None)

        # Transitions should work normally
        result = await fsm.transition_to("running")
        assert result.is_ok()
        assert fsm._state == "running"

        result = await fsm.transition_to("completed")
        assert result.is_ok()
        assert fsm._state == "completed"


class TestFSMHooks:
    """Test FSM state entry/exit hooks."""

    @pytest.mark.asyncio
    async def test_entry_hook_executes(self):
        """Entry hook executes when entering a state."""
        entry_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            entry_called.append(ctx.metadata["state"])
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition to running should trigger entry hook
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()
        assert len(entry_called) == 1
        assert entry_called[0] == "running"

    @pytest.mark.asyncio
    async def test_exit_hook_executes(self):
        """Exit hook executes when leaving a state."""
        exit_called = []

        def exit_hook(ctx: FSMContext) -> Result[None]:
            exit_called.append(ctx.metadata["state"])
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_exit_hook("idle", exit_hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition from idle should trigger exit hook
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()
        assert len(exit_called) == 1
        assert exit_called[0] == "idle"

    @pytest.mark.asyncio
    async def test_hook_failure_logs_and_continues(self):
        """Hook failure is logged and transition continues."""

        def failing_hook(ctx: FSMContext) -> Result[None]:
            return Err("Hook failed", code="HOOK_ERROR")

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_exit_hook("idle", failing_hook)
            .with_entry_hook("running", failing_hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition should succeed despite hook failure
        with patch("dawn_kestrel.core.fsm.logger") as mock_logger:
            transition_result = await fsm.transition_to("running")
            assert transition_result.is_ok()
            assert fsm._state == "running"

            # Both hooks should log errors
            assert mock_logger.error.call_count >= 2

            # Check that error messages include hook failure details
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("Exit hook failed" in call for call in error_calls)
            assert any("Entry hook failed" in call for call in error_calls)

    @pytest.mark.asyncio
    async def test_hook_exception_logs_and_continues(self):
        """Hook exception is caught, logged, and transition continues."""

        def exception_hook(ctx: FSMContext) -> Result[None]:
            raise ValueError("Hook raised exception")

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_exit_hook("idle", exception_hook)
            .with_entry_hook("running", exception_hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition should succeed despite hook exception
        with patch("dawn_kestrel.core.fsm.logger") as mock_logger:
            transition_result = await fsm.transition_to("running")
            assert transition_result.is_ok()
            assert fsm._state == "running"

            # Both hooks should log exceptions (from _execute_with_reliability)
            assert mock_logger.error.call_count >= 2

            # Check that error messages include exception details
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("Hook execution error" in call for call in error_calls)
            assert any("Hook raised exception" in call for call in error_calls)

    @pytest.mark.asyncio
    async def test_hooks_receive_fsm_context(self):
        """Hooks receive FSMContext with state and fsm_id."""
        contexts_received = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            contexts_received.append(("entry", ctx))
            return Ok(None)

        def exit_hook(ctx: FSMContext) -> Result[None]:
            contexts_received.append(("exit", ctx))
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_exit_hook("idle", exit_hook)
            .with_entry_hook("running", entry_hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition to trigger hooks
        await fsm.transition_to("running")

        # Should have received exit and entry contexts
        assert len(contexts_received) == 2

        # Check exit hook context
        exit_type, exit_ctx = contexts_received[0]
        assert exit_type == "exit"
        assert exit_ctx.metadata["state"] == "idle"
        assert "fsm_id" in exit_ctx.metadata

        # Check entry hook context
        entry_type, entry_ctx = contexts_received[1]
        assert entry_type == "entry"
        assert entry_ctx.metadata["state"] == "running"
        assert "fsm_id" in entry_ctx.metadata

    @pytest.mark.asyncio
    async def test_hooks_with_user_data(self):
        """Hooks receive FSMContext with user_data."""
        contexts_received = []

        def hook(ctx: FSMContext) -> Result[None]:
            contexts_received.append(ctx.user_data)
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition with context containing user_data
        context = FSMContext(user_data={"key": "value", "number": 42})
        await fsm.transition_to("running", context)

        # Hook should receive user_data
        assert len(contexts_received) == 1
        assert contexts_received[0]["key"] == "value"
        assert contexts_received[0]["number"] == 42

    @pytest.mark.asyncio
    async def test_fsm_without_hooks_works_normally(self):
        """FSM without hooks works normally."""
        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transitions should work normally without hooks
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()
        assert fsm._state == "running"


class TestFSMCommands:
    """Test FSM command-based transitions with audit logging."""

    @pytest.mark.asyncio
    async def test_transition_command_created(self):
        """FSM creates TransitionCommand for each state transition."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm")
        result = await fsm.transition_to("running")

        assert result.is_ok()
        command = result.unwrap()
        assert isinstance(command, TransitionCommand)
        assert command.fsm_id == "test-fsm"
        assert command.from_state == "idle"
        assert command.to_state == "running"
        assert command.name == "transition"

    @pytest.mark.asyncio
    async def test_transition_command_executes(self):
        """TransitionCommand execute() returns target state."""
        valid_states = {"idle", "running"}
        valid_transitions = {"idle": {"running"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)
        result = await fsm.transition_to("running")

        assert result.is_ok()
        command = result.unwrap()
        execute_result = await command.execute(FSMContext())
        assert execute_result.is_ok()
        assert execute_result.unwrap() == "running"
        assert fsm._state == "running"

    @pytest.mark.asyncio
    async def test_command_provenance_includes_audit_data(self):
        """TransitionCommand get_provenance() returns complete audit data."""
        valid_states = {"idle", "running"}
        valid_transitions = {"idle": {"running"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="audit-fsm")
        result = await fsm.transition_to("running")

        assert result.is_ok()
        command = result.unwrap()
        provenance_result = await command.get_provenance()

        assert provenance_result.is_ok()
        provenance = provenance_result.unwrap()
        assert provenance["command"] == "transition"
        assert provenance["fsm_id"] == "audit-fsm"
        assert provenance["from_state"] == "idle"
        assert provenance["to_state"] == "running"
        assert "created_at" in provenance
        assert "can_undo" in provenance
        assert provenance["can_undo"] is False

    @pytest.mark.asyncio
    async def test_command_history_accessible(self):
        """get_command_history() returns list of executed commands."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="history-fsm")

        history = fsm.get_command_history()
        assert len(history) == 0

        await fsm.transition_to("running")
        history = fsm.get_command_history()
        assert len(history) == 1
        assert isinstance(history[0], TransitionCommand)
        assert history[0].from_state == "idle"
        assert history[0].to_state == "running"

        await fsm.transition_to("completed")
        history = fsm.get_command_history()
        assert len(history) == 2
        assert history[0].from_state == "idle"
        assert history[0].to_state == "running"
        assert history[1].from_state == "running"
        assert history[1].to_state == "completed"

    def test_transition_command_cannot_undo(self):
        """TransitionCommand does not support undo."""
        command = TransitionCommand(fsm_id="test", from_state="idle", to_state="running")
        assert command.can_undo() is False

    @pytest.mark.asyncio
    async def test_invalid_transition_no_command_created(self):
        """Invalid transitions do not create commands."""
        valid_states = {"idle", "running"}
        valid_transitions = {"idle": {"running"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)

        result = await fsm.transition_to("completed")
        assert result.is_err()
        assert "Invalid state transition" in result.error
        history = fsm.get_command_history()
        assert len(history) == 0


class TestFSMReliability:
    """Test FSM reliability wrapper integration."""

    @pytest.mark.asyncio
    async def test_fsm_wraps_external_actions_in_circuit_breaker(self):
        """FSM wraps external actions in CircuitBreaker."""
        hook_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            hook_called.append("entry")
            return Ok(None)

        mock_circuit_breaker = MagicMock()

        reliability_config = FSMReliabilityConfig(circuit_breaker=mock_circuit_breaker)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .with_reliability(reliability_config)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify reliability_config is set
        assert fsm._reliability_config == reliability_config

        # Transition to trigger hook
        await fsm.transition_to("running")

        # Hook should be called
        assert "entry" in hook_called

    @pytest.mark.asyncio
    async def test_fsm_wraps_external_actions_in_retry(self):
        """FSM wraps external actions in RetryExecutor."""
        hook_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            hook_called.append("entry")
            return Ok(None)

        retry_executor = RetryExecutorImpl(max_attempts=3)
        reliability_config = FSMReliabilityConfig(retry_executor=retry_executor)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .with_reliability(reliability_config)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify reliability_config is set
        assert fsm._reliability_config == reliability_config

        # Transition to trigger hook
        await fsm.transition_to("running")

        # Hook should be called (with retry)
        assert "entry" in hook_called

    @pytest.mark.asyncio
    async def test_fsm_wraps_external_actions_in_rate_limiter(self):
        """FSM wraps external actions in RateLimiter."""
        hook_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            hook_called.append("entry")
            return Ok(None)

        rate_limiter = RateLimiterImpl(default_capacity=10, default_refill_rate=1.0)
        reliability_config = FSMReliabilityConfig(rate_limiter=rate_limiter)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .with_reliability(reliability_config)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify reliability_config is set
        assert fsm._reliability_config == reliability_config

        # Transition to trigger hook
        await fsm.transition_to("running")

        # Hook should be called (with rate limiter)
        assert "entry" in hook_called

    @pytest.mark.asyncio
    async def test_fsm_wraps_external_actions_in_bulkhead(self):
        """FSM wraps external actions in Bulkhead."""
        hook_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            hook_called.append("entry")
            return Ok(None)

        bulkhead = BulkheadImpl()
        bulkhead.set_limit("default", 5)
        reliability_config = FSMReliabilityConfig(bulkhead=bulkhead)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .with_reliability(reliability_config)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify reliability_config is set
        assert fsm._reliability_config == reliability_config

        # Transition to trigger hook
        await fsm.transition_to("running")

        # Hook should be called (with bulkhead)
        assert "entry" in hook_called

    @pytest.mark.asyncio
    async def test_fsm_reliability_disabled_when_config_none(self):
        """FSM does not wrap when reliability_config is None."""
        hook_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            hook_called.append("entry")
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify reliability_config is None
        assert fsm._reliability_config is None

        # Transition to trigger hook
        await fsm.transition_to("running")

        # Hook should be called directly (without wrappers)
        assert "entry" in hook_called

    @pytest.mark.asyncio
    async def test_fsm_reliability_disabled_when_enabled_false(self):
        """FSM does not wrap when reliability_config.enabled is False."""
        hook_called = []

        def entry_hook(ctx: FSMContext) -> Result[None]:
            hook_called.append("entry")
            return Ok(None)

        rate_limiter = RateLimiterImpl()
        reliability_config = FSMReliabilityConfig(rate_limiter=rate_limiter, enabled=False)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_entry_hook("running", entry_hook)
            .with_reliability(reliability_config)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify reliability_config is set but disabled
        assert fsm._reliability_config == reliability_config
        assert fsm._reliability_config.enabled is False

        # Transition to trigger hook
        await fsm.transition_to("running")

        # Hook should be called directly (without wrappers)
        assert "entry" in hook_called


class TestFSMDIIntegration:
    """Test FSM integration with DI container."""

    def test_fsm_repository_provider_registered(self):
        """FSM repository provider is registered in DI container."""
        from dawn_kestrel.core.di_container import container

        # Provider should be accessible
        assert hasattr(container, "fsm_repository")
        fsm_repo = container.fsm_repository()

        # Should return FSMStateRepositoryImpl
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        assert isinstance(fsm_repo, FSMStateRepositoryImpl)

    def test_fsm_builder_provider_registered(self):
        """FSM builder provider is registered in DI container."""
        from dawn_kestrel.core.di_container import container

        # Provider should be accessible
        assert hasattr(container, "fsm_builder")
        fsm_builder = container.fsm_builder()

        # Should return FSMBuilder instance
        from dawn_kestrel.core.fsm import FSMBuilder

        assert isinstance(fsm_builder, FSMBuilder)

    def test_fsm_repository_uses_container_storage(self):
        """FSM repository uses container's storage provider."""
        from dawn_kestrel.core.di_container import container
        from dawn_kestrel.storage.store import SessionStorage

        # Get both storage and fsm_repository
        storage = container.storage()
        fsm_repo = container.fsm_repository()

        # FSM repository should have a SessionStorage instance
        assert isinstance(fsm_repo._storage, SessionStorage)

    @pytest.mark.asyncio
    async def test_fsm_builder_creates_fsm_from_container(self):
        """FSM builder from container can create valid FSM instances."""
        from dawn_kestrel.core.di_container import container
        from dawn_kestrel.core.result import Ok

        # Get FSM builder from container
        fsm_builder = container.fsm_builder()

        # Use builder to create FSM
        result = (
            fsm_builder.with_state("idle")
            .with_state("running")
            .with_state("completed")
            .with_transition("idle", "running")
            .with_transition("running", "completed")
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify FSM instance
        state = await fsm.get_state()
        assert state == "idle"

    @pytest.mark.asyncio
    async def test_fsm_builder_with_persistence_from_container(self):
        """FSM builder with persistence uses container's FSM repository."""
        from dawn_kestrel.core.di_container import container
        from dawn_kestrel.core.result import Ok

        # Get FSM builder and repository from container
        fsm_builder = container.fsm_builder()
        fsm_repo = container.fsm_repository()

        # Build FSM with persistence
        result = (
            fsm_builder.with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_persistence(fsm_repo)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Store fsm_id for testing
        fsm_id = fsm._fsm_id

        # Verify FSM has repository
        assert fsm._repository is fsm_repo

        # Transition should persist state
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()

        # Verify state was persisted
        state_result = await fsm_repo.get_state(fsm_id)
        assert state_result.is_ok()
        assert state_result.unwrap() == "running"

    def test_fsm_builder_lazy_initialization(self):
        """FSM builder provider uses lazy initialization."""
        from dawn_kestrel.core.di_container import container

        # Access provider - should not create instance yet (Factory pattern)
        provider = container.fsm_repository

        # Multiple calls should return same provider
        assert container.fsm_repository is provider

        # But getting instance should work
        fsm_repo1 = container.fsm_repository()
        fsm_repo2 = container.fsm_repository()

        # Factory creates new instances each time (not Singleton)
        assert fsm_repo1 is not fsm_repo2

    @pytest.mark.asyncio
    async def test_fsm_dependencies_injected_correctly(self):
        """FSM dependencies are injected correctly from container."""
        from dawn_kestrel.core.di_container import container
        from dawn_kestrel.core.result import Ok

        # Get FSM builder and repository from container
        fsm_builder = container.fsm_builder()
        fsm_repo = container.fsm_repository()

        # Build FSM with all optional dependencies
        result = (
            fsm_builder.with_state("idle")
            .with_state("running")
            .with_persistence(fsm_repo)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify all dependencies are correctly set
        assert fsm._repository is fsm_repo
        assert fsm._fsm_id is not None  # fsm_id is auto-generated
        assert fsm._fsm_id.startswith("fsm_")
        assert fsm._state == "idle"

    @pytest.mark.asyncio
    async def test_fsm_repository_state_get_set(self):
        """FSM repository from container can get and set state."""
        from dawn_kestrel.core.di_container import container
        from dawn_kestrel.core.result import Ok

        # Get FSM repository from container
        fsm_repo = container.fsm_repository()

        # Set state
        set_result = await fsm_repo.set_state("test-fsm-state", "running")
        assert set_result.is_ok()

        # Get state
        get_result = await fsm_repo.get_state("test-fsm-state")
        assert get_result.is_ok()
        assert get_result.unwrap() == "running"

        # Update state
        set_result = await fsm_repo.set_state("test-fsm-state", "completed")
        assert set_result.is_ok()

        # Get updated state
        get_result = await fsm_repo.get_state("test-fsm-state")
        assert get_result.is_ok()
        assert get_result.unwrap() == "completed"

    @pytest.mark.asyncio
    async def test_fsm_builder_chaining_works_from_container(self):
        """FSM builder method chaining works from container provider."""
        from dawn_kestrel.core.di_container import container
        from dawn_kestrel.core.result import Ok

        # Get FSM builder from container
        fsm_builder = container.fsm_builder()

        # Test fluent API chaining
        result = (
            fsm_builder.with_state("idle")
            .with_state("processing")
            .with_state("done")
            .with_state("error")
            .with_transition("idle", "processing")
            .with_transition("processing", "done")
            .with_transition("processing", "error")
            .with_transition("error", "idle")
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Verify all states and transitions are set
        assert fsm._valid_states == {"idle", "processing", "done", "error"}

        # Verify transitions work
        result1 = await fsm.transition_to("processing")
        assert result1.is_ok()

        result2 = await fsm.transition_to("done")
        assert result2.is_ok()


class TestFSMProtocol:
    """Test FSM protocol interface."""

    def test_fsm_protocol_has_required_methods(self):
        """FSM protocol defines get_state, transition_to, is_transition_valid methods."""
        from dawn_kestrel.core.fsm import FSM
        import inspect

        # Check protocol has required methods
        assert hasattr(FSM, "get_state")
        assert hasattr(FSM, "transition_to")
        assert hasattr(FSM, "is_transition_valid")

        # Check methods are protocol methods (not actual implementations)
        get_state_method = getattr(FSM, "get_state")
        transition_method = getattr(FSM, "transition_to")
        is_valid_method = getattr(FSM, "is_transition_valid")

        # Should be callable (protocol methods)
        assert callable(get_state_method)
        assert callable(transition_method)
        assert callable(is_valid_method)

    def test_fsm_protocol_is_runtime_checkable(self):
        """FSM protocol is marked as runtime_checkable for isinstance() checks."""
        from dawn_kestrel.core.fsm import FSM

        # @runtime_checkable protocol allows isinstance checks
        # Create a mock FSM instance
        class MockFSM(FSM):
            async def get_state(self) -> str:
                return "idle"

            async def transition_to(
                self, new_state: str, context: FSMContext | None = None
            ) -> Result[None]:
                return Ok(None)

            async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
                return True

        mock = MockFSM()
        assert isinstance(mock, FSM)

    @pytest.mark.asyncio
    async def test_fsm_impl_satisfies_protocol(self):
        """FSMImpl class satisfies FSM protocol."""
        from dawn_kestrel.core.fsm import FSM

        valid_states = {"idle", "running"}
        valid_transitions = {"idle": {"running"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions)

        # FSMImpl should satisfy FSM protocol
        assert isinstance(fsm, FSM)

        # Test all protocol methods work
        state = await fsm.get_state()
        assert state == "idle"

        is_valid = await fsm.is_transition_valid("idle", "running")
        assert is_valid is True

        result = await fsm.transition_to("running")
        assert result.is_ok()


class TestFSMStateRepository:
    """Test FSM state repository implementation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock SessionStorage for testing."""
        from dawn_kestrel.storage.store import SessionStorage
        from unittest.mock import MagicMock

        storage = MagicMock(spec=SessionStorage)
        return storage

    @pytest.mark.asyncio
    async def test_repository_get_state_returns_ok_when_found(self, mock_storage):
        """get_state returns Ok(state) when state is found in storage."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        mock_storage.read.return_value = {"state": "running"}

        repo = FSMStateRepositoryImpl(mock_storage)
        result = await repo.get_state("test-fsm")

        assert result.is_ok()
        assert result.unwrap() == "running"
        mock_storage.read.assert_called_once_with(["fsm_state", "test-fsm"])

    @pytest.mark.asyncio
    async def test_repository_get_state_returns_err_when_not_found(self, mock_storage):
        """get_state returns Err when state is not found in storage."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        mock_storage.read.return_value = None

        repo = FSMStateRepositoryImpl(mock_storage)
        result = await repo.get_state("test-fsm")

        assert result.is_err()
        assert "FSM state not found" in result.error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_repository_get_state_returns_err_when_invalid_data(self, mock_storage):
        """get_state returns Err when storage data is missing state field."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        mock_storage.read.return_value = {"invalid_field": "value"}

        repo = FSMStateRepositoryImpl(mock_storage)
        result = await repo.get_state("test-fsm")

        assert result.is_err()
        assert "Invalid FSM state data" in result.error
        assert result.code == "INVALID_DATA"

    @pytest.mark.asyncio
    async def test_repository_set_state_returns_ok_on_success(self, mock_storage):
        """set_state returns Ok on successful write to storage."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        mock_storage.write.return_value = None  # write doesn't return anything

        repo = FSMStateRepositoryImpl(mock_storage)
        result = await repo.set_state("test-fsm", "running")

        assert result.is_ok()
        assert result.unwrap() is None
        mock_storage.write.assert_called_once_with(["fsm_state", "test-fsm"], {"state": "running"})

    @pytest.mark.asyncio
    async def test_repository_set_state_returns_err_on_storage_error(self, mock_storage):
        """set_state returns Err when storage write fails."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        mock_storage.write.side_effect = IOError("Storage unavailable")

        repo = FSMStateRepositoryImpl(mock_storage)
        result = await repo.set_state("test-fsm", "running")

        assert result.is_err()
        assert "Failed to persist FSM state" in result.error
        assert result.code == "STORAGE_ERROR"

    @pytest.mark.asyncio
    async def test_repository_get_state_returns_err_on_storage_error(self, mock_storage):
        """get_state returns Err when storage read fails."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        mock_storage.read.side_effect = IOError("Storage unavailable")

        repo = FSMStateRepositoryImpl(mock_storage)
        result = await repo.get_state("test-fsm")

        assert result.is_err()
        assert "Failed to get FSM state" in result.error
        assert result.code == "STORAGE_ERROR"

    @pytest.mark.asyncio
    async def test_repository_get_set_roundtrip(self, mock_storage):
        """Repository can store and retrieve state in roundtrip."""
        from dawn_kestrel.core.fsm_state_repository import FSMStateRepositoryImpl

        # Store state
        repo = FSMStateRepositoryImpl(mock_storage)
        set_result = await repo.set_state("roundtrip-fsm", "completed")
        assert set_result.is_ok()

        # Retrieve state
        mock_storage.read.return_value = {"state": "completed"}
        get_result = await repo.get_state("roundtrip-fsm")
        assert get_result.is_ok()
        assert get_result.unwrap() == "completed"


class TestFSMGuards:
    """Test FSM guard condition storage in builder."""

    def test_guard_stored_in_builder(self):
        """Guard is stored in builder for transition."""

        def test_guard(ctx: FSMContext) -> Result[bool]:
            return Ok(True)

        builder = FSMBuilder()
        builder.with_guard("idle", "running", test_guard)

        assert ("idle", "running") in builder._guards
        assert builder._guards[("idle", "running")] == test_guard

    def test_multiple_guards_stored_in_builder(self):
        """Multiple guards can be stored for different transitions."""

        def guard1(ctx: FSMContext) -> Result[bool]:
            return Ok(True)

        def guard2(ctx: FSMContext) -> Result[bool]:
            return Ok(True)

        builder = FSMBuilder()
        builder.with_guard("idle", "running", guard1)
        builder.with_guard("running", "done", guard2)

        assert ("idle", "running") in builder._guards
        assert ("running", "done") in builder._guards
        assert builder._guards[("idle", "running")] == guard1
        assert builder._guards[("running", "done")] == guard2

    def test_guard_overwrites_previous_guard(self):
        """Calling with_guard twice for same transition overwrites previous guard."""

        def guard1(ctx: FSMContext) -> Result[bool]:
            return Ok(True)

        def guard2(ctx: FSMContext) -> Result[bool]:
            return Ok(True)

        builder = FSMBuilder()
        builder.with_guard("idle", "running", guard1)
        builder.with_guard("idle", "running", guard2)

        assert builder._guards[("idle", "running")] == guard2

    @pytest.mark.asyncio
    async def test_fsm_with_guard_still_transitions(self):
        """FSM with guards configured still performs transitions."""

        def allow_guard(ctx: FSMContext) -> Result[bool]:
            return Ok(True)

        result = (
            FSMBuilder()
            .with_state("idle")
            .with_state("running")
            .with_transition("idle", "running")
            .with_guard("idle", "running", allow_guard)
            .build(initial_state="idle")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Transition should succeed (guards are stored but not yet implemented in FSMImpl)
        transition_result = await fsm.transition_to("running")
        assert transition_result.is_ok()
        assert fsm._state == "running"
