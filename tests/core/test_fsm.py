"""Tests for FSMImpl (generic finite state machine)."""

import pytest
from dawn_kestrel.core.fsm import FSMImpl, FSMBuilder
from dawn_kestrel.core.result import Result, Ok, Err


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

    def test_fsm_impl_get_command_history_returns_audit_trail(self):
        """get_command_history returns list of executed transitions."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm")
        history = fsm.get_command_history()

        assert len(history) == 0

    def test_fsm_impl_command_history_includes_fsm_id_and_states(self):
        """Command history includes fsm_id and state information."""
        valid_states = {"idle", "running", "completed"}
        valid_transitions = {"idle": {"running"}, "running": {"completed"}}

        fsm = FSMImpl("idle", valid_states, valid_transitions, fsm_id="test-fsm-123")
        fsm._command_history.append(
            {
                "fsm_id": fsm._fsm_id,
                "from_state": "idle",
                "to_state": "running",
            }
        )

        history = fsm.get_command_history()
        assert len(history) == 1
        assert history[0]["fsm_id"] == "test-fsm-123"
        assert history[0]["from_state"] == "idle"
        assert history[0]["to_state"] == "running"

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
