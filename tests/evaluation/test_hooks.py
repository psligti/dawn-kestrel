"""Tests for evaluation hooks module.

Tests cover:
- EvaluationHooks: callback registration and emission
- HookManager: multi-hook coordination
- Protocol validation
"""

import pytest
from unittest.mock import MagicMock

from dawn_kestrel.evaluation.hooks import (
    EvaluationHooks,
    HookManager,
    TranscriptCallback,
    ToolCallCallback,
    PhaseCallback,
    BudgetCallback,
)
from dawn_kestrel.evaluation.models import Transcript
from dawn_kestrel.core.models import Message


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_transcript() -> Transcript:
    """Create a sample Transcript for testing."""
    return Transcript(
        id="tr-1",
        session_id="session-1",
        messages=[
            Message(
                id="msg-1",
                session_id="session-1",
                role="user",
                text="Hello!",
            ),
        ],
    )


@pytest.fixture
def hooks() -> EvaluationHooks:
    """Create a fresh EvaluationHooks instance."""
    return EvaluationHooks()


@pytest.fixture
def hook_manager() -> HookManager:
    """Create a fresh HookManager instance."""
    return HookManager()


# ============================================================================
# EvaluationHooks Tests
# ============================================================================


class TestEvaluationHooks:
    """Tests for EvaluationHooks class."""

    def test_create_with_no_callbacks(self, hooks: EvaluationHooks) -> None:
        """Creating hooks without callbacks should work."""
        assert hooks.on_transcript_ready is None
        assert hooks.on_tool_call is None
        assert hooks.on_phase_complete is None
        assert hooks.on_budget_threshold is None

    def test_has_hooks_returns_false_when_empty(self, hooks: EvaluationHooks) -> None:
        """has_hooks should return False when no callbacks are set."""
        assert hooks.has_hooks() is False

    def test_has_hooks_returns_true_when_transcript_set(self, hooks: EvaluationHooks) -> None:
        """has_hooks should return True when transcript callback is set."""
        hooks.on_transcript_ready = lambda t: None
        assert hooks.has_hooks() is True

    def test_has_hooks_returns_true_when_tool_call_set(self, hooks: EvaluationHooks) -> None:
        """has_hooks should return True when tool call callback is set."""
        hooks.on_tool_call = lambda t, i, o: None
        assert hooks.has_hooks() is True

    def test_has_hooks_returns_true_when_phase_set(self, hooks: EvaluationHooks) -> None:
        """has_hooks should return True when phase callback is set."""
        hooks.on_phase_complete = lambda p, o: None
        assert hooks.has_hooks() is True

    def test_has_hooks_returns_true_when_budget_set(self, hooks: EvaluationHooks) -> None:
        """has_hooks should return True when budget callback is set."""
        hooks.on_budget_threshold = lambda u, t: None
        assert hooks.has_hooks() is True

    def test_emit_transcript_calls_callback(
        self, hooks: EvaluationHooks, sample_transcript: Transcript
    ) -> None:
        """emit_transcript should call the registered callback."""
        callback = MagicMock(spec=TranscriptCallback)
        hooks.on_transcript_ready = callback

        hooks.emit_transcript(sample_transcript)

        callback.assert_called_once_with(sample_transcript)

    def test_emit_transcript_does_nothing_without_callback(
        self, hooks: EvaluationHooks, sample_transcript: Transcript
    ) -> None:
        """emit_transcript should be a no-op if no callback is set."""
        # Should not raise
        hooks.emit_transcript(sample_transcript)

    def test_emit_tool_call_calls_callback(self, hooks: EvaluationHooks) -> None:
        """emit_tool_call should call the registered callback."""
        callback = MagicMock(spec=ToolCallCallback)
        hooks.on_tool_call = callback

        hooks.emit_tool_call("bash", {"command": "ls"}, "output")

        callback.assert_called_once_with("bash", {"command": "ls"}, "output")

    def test_emit_tool_call_does_nothing_without_callback(self, hooks: EvaluationHooks) -> None:
        """emit_tool_call should be a no-op if no callback is set."""
        # Should not raise
        hooks.emit_tool_call("bash", {"command": "ls"}, "output")

    def test_emit_phase_calls_callback(self, hooks: EvaluationHooks) -> None:
        """emit_phase should call the registered callback."""
        callback = MagicMock(spec=PhaseCallback)
        hooks.on_phase_complete = callback

        hooks.emit_phase("runner_start", {"run_id": "123"})

        callback.assert_called_once_with("runner_start", {"run_id": "123"})

    def test_emit_phase_does_nothing_without_callback(self, hooks: EvaluationHooks) -> None:
        """emit_phase should be a no-op if no callback is set."""
        # Should not raise
        hooks.emit_phase("runner_start", {"run_id": "123"})

    def test_emit_budget_calls_callback(self, hooks: EvaluationHooks) -> None:
        """emit_budget should call the registered callback."""
        callback = MagicMock(spec=BudgetCallback)
        hooks.on_budget_threshold = callback

        usage = {"input": 100, "output": 50}
        hooks.emit_budget(usage, 0.8)

        callback.assert_called_once_with(usage, 0.8)

    def test_emit_budget_does_nothing_without_callback(self, hooks: EvaluationHooks) -> None:
        """emit_budget should be a no-op if no callback is set."""
        # Should not raise
        hooks.emit_budget({"input": 100}, 0.8)

    def test_multiple_callbacks_can_be_set(self, hooks: EvaluationHooks) -> None:
        """Multiple callbacks can be registered on the same hooks instance."""
        transcript_cb = MagicMock()
        tool_cb = MagicMock()
        phase_cb = MagicMock()

        hooks.on_transcript_ready = transcript_cb
        hooks.on_tool_call = tool_cb
        hooks.on_phase_complete = phase_cb

        assert hooks.has_hooks() is True


# ============================================================================
# HookManager Tests
# ============================================================================


class TestHookManager:
    """Tests for HookManager class."""

    def test_create_empty_manager(self, hook_manager: HookManager) -> None:
        """Creating a HookManager should start with no hooks."""
        assert hook_manager._hooks == []

    def test_register_adds_hooks(self, hook_manager: HookManager, hooks: EvaluationHooks) -> None:
        """register should add hooks to the manager."""
        hook_manager.register(hooks)

        assert hooks in hook_manager._hooks

    def test_unregister_removes_hooks(
        self, hook_manager: HookManager, hooks: EvaluationHooks
    ) -> None:
        """unregister should remove hooks from the manager."""
        hook_manager.register(hooks)
        hook_manager.unregister(hooks)

        assert hooks not in hook_manager._hooks

    def test_unregister_nonexistent_is_safe(
        self, hook_manager: HookManager, hooks: EvaluationHooks
    ) -> None:
        """unregister should be safe if hooks not registered."""
        # Should not raise
        hook_manager.unregister(hooks)

    def test_emit_transcript_to_all_hooks(
        self,
        hook_manager: HookManager,
        sample_transcript: Transcript,
    ) -> None:
        """emit_transcript should send to all registered hooks."""
        hooks1 = EvaluationHooks()
        hooks2 = EvaluationHooks()
        callback1 = MagicMock()
        callback2 = MagicMock()

        hooks1.on_transcript_ready = callback1
        hooks2.on_transcript_ready = callback2

        hook_manager.register(hooks1)
        hook_manager.register(hooks2)

        hook_manager.emit_transcript(sample_transcript)

        callback1.assert_called_once_with(sample_transcript)
        callback2.assert_called_once_with(sample_transcript)

    def test_emit_tool_call_to_all_hooks(self, hook_manager: HookManager) -> None:
        """emit_tool_call should send to all registered hooks."""
        hooks1 = EvaluationHooks()
        hooks2 = EvaluationHooks()
        callback1 = MagicMock()
        callback2 = MagicMock()

        hooks1.on_tool_call = callback1
        hooks2.on_tool_call = callback2

        hook_manager.register(hooks1)
        hook_manager.register(hooks2)

        hook_manager.emit_tool_call("read", {"path": "/tmp"}, "content")

        callback1.assert_called_once_with("read", {"path": "/tmp"}, "content")
        callback2.assert_called_once_with("read", {"path": "/tmp"}, "content")

    def test_emit_phase_to_all_hooks(self, hook_manager: HookManager) -> None:
        """emit_phase should send to all registered hooks."""
        hooks1 = EvaluationHooks()
        hooks2 = EvaluationHooks()
        callback1 = MagicMock()
        callback2 = MagicMock()

        hooks1.on_phase_complete = callback1
        hooks2.on_phase_complete = callback2

        hook_manager.register(hooks1)
        hook_manager.register(hooks2)

        hook_manager.emit_phase("complete", {"status": "ok"})

        callback1.assert_called_once_with("complete", {"status": "ok"})
        callback2.assert_called_once_with("complete", {"status": "ok"})

    def test_emit_budget_to_all_hooks(self, hook_manager: HookManager) -> None:
        """emit_budget should send to all registered hooks."""
        hooks1 = EvaluationHooks()
        hooks2 = EvaluationHooks()
        callback1 = MagicMock()
        callback2 = MagicMock()

        hooks1.on_budget_threshold = callback1
        hooks2.on_budget_threshold = callback2

        hook_manager.register(hooks1)
        hook_manager.register(hooks2)

        usage = {"input": 1000, "output": 500}
        hook_manager.emit_budget(usage, 0.9)

        callback1.assert_called_once_with(usage, 0.9)
        callback2.assert_called_once_with(usage, 0.9)

    def test_hooks_without_callbacks_are_safe(
        self, hook_manager: HookManager, sample_transcript: Transcript
    ) -> None:
        """Emitting to hooks without callbacks should not raise."""
        hooks1 = EvaluationHooks()  # No callbacks
        hooks2 = EvaluationHooks()
        callback = MagicMock()
        hooks2.on_transcript_ready = callback

        hook_manager.register(hooks1)
        hook_manager.register(hooks2)

        # Should not raise
        hook_manager.emit_transcript(sample_transcript)

        # Only hooks2 callback should have been called
        callback.assert_called_once()


# ============================================================================
# Protocol Tests
# ============================================================================


class TestProtocols:
    """Tests for Protocol validation."""

    def test_transcript_callback_protocol(self, sample_transcript: Transcript) -> None:
        """TranscriptCallback should work with callable."""
        called = []

        def callback(t: Transcript) -> None:
            called.append(t)

        hooks = EvaluationHooks()
        hooks.on_transcript_ready = callback
        hooks.emit_transcript(sample_transcript)

        assert called == [sample_transcript]

    def test_tool_call_callback_protocol(self) -> None:
        """ToolCallCallback should work with callable."""
        called = []

        def callback(tool: str, input: dict, output: object) -> None:
            called.append((tool, input, output))

        hooks = EvaluationHooks()
        hooks.on_tool_call = callback
        hooks.emit_tool_call("bash", {"cmd": "ls"}, "files")

        assert called == [("bash", {"cmd": "ls"}, "files")]

    def test_phase_callback_protocol(self) -> None:
        """PhaseCallback should work with callable."""
        called = []

        def callback(phase: str, output: dict) -> None:
            called.append((phase, output))

        hooks = EvaluationHooks()
        hooks.on_phase_complete = callback
        hooks.emit_phase("start", {"id": "1"})

        assert called == [("start", {"id": "1"})]

    def test_budget_callback_protocol(self) -> None:
        """BudgetCallback should work with callable."""
        called = []

        def callback(usage: dict, threshold: float) -> None:
            called.append((usage, threshold))

        hooks = EvaluationHooks()
        hooks.on_budget_threshold = callback
        hooks.emit_budget({"tokens": 100}, 0.5)

        assert called == [({"tokens": 100}, 0.5)]
