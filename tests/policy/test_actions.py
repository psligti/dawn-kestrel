"""Tests for action handlers and dispatcher."""

import pytest

from dawn_kestrel.policy.actions import (
    ActionDispatcher,
    ActionResult,
    ReadFileHandler,
    UnknownActionTypeError,
)
from dawn_kestrel.policy.contracts import ReadFileAction, SearchRepoAction


class TestActionDispatcher:
    """Tests for ActionDispatcher class."""

    def test_handler_registration_works(self) -> None:
        """Handler registration works correctly."""
        dispatcher = ActionDispatcher()
        handler = ReadFileHandler()

        # Register handler
        dispatcher.register("READ_FILE", handler)

        # Verify handler is registered
        assert "READ_FILE" in dispatcher._handlers
        assert dispatcher._handlers["READ_FILE"] is handler

    def test_dispatch_calls_correct_handler(self) -> None:
        """Dispatch routes action to correct handler."""
        dispatcher = ActionDispatcher()
        handler = ReadFileHandler()
        dispatcher.register("READ_FILE", handler)

        # Create and dispatch action
        action = ReadFileAction(path="/some/file.txt")
        result = dispatcher.dispatch(action)

        # Verify result
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert "/some/file.txt" in result.output

    def test_unknown_action_type_raises_error(self) -> None:
        """Dispatch raises error for unregistered action type."""
        dispatcher = ActionDispatcher()

        # Create action without registered handler
        action = SearchRepoAction(pattern="test")

        # Should raise UnknownActionTypeError
        with pytest.raises(UnknownActionTypeError, match="No handler registered"):
            dispatcher.dispatch(action)


class TestReadFileHandler:
    """Tests for ReadFileHandler class."""

    def test_validate_accepts_string_path(self) -> None:
        """Validate returns True for string path."""
        handler = ReadFileHandler()
        action = ReadFileAction(path="/valid/path.txt")

        assert handler.validate(action) is True

    def test_execute_returns_success_for_valid_action(self) -> None:
        """Execute returns success for valid action."""
        handler = ReadFileHandler()
        action = ReadFileAction(path="/some/file.txt")

        result = handler.execute(action)

        assert result.success is True
        assert result.error is None
        assert "Would read file" in result.output

    def test_record_does_not_raise(self) -> None:
        """Record method completes without error."""
        handler = ReadFileHandler()
        action = ReadFileAction(path="/some/file.txt")
        result = ActionResult(success=True, output="test")

        # Should not raise
        handler.record(action, result)


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_success_result(self) -> None:
        """Create successful result."""
        result = ActionResult(success=True, output="data")

        assert result.success is True
        assert result.output == "data"
        assert result.error is None

    def test_failure_result(self) -> None:
        """Create failure result."""
        result = ActionResult(success=False, error="Something failed")

        assert result.success is False
        assert result.output is None
        assert result.error == "Something failed"
