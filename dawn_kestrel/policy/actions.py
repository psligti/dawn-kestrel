"""Action handlers and dispatcher for policy engine.

This module provides the handler pattern for executing actions:
- ActionHandler: Protocol defining the handler interface
- ActionResult: Dataclass for action execution results
- ActionDispatcher: Registry and router for action handlers
- ReadFileHandler: Handler implementation for READ_FILE actions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from dawn_kestrel.policy.contracts import Action, ReadFileAction

if TYPE_CHECKING:
    pass


@runtime_checkable
class ActionHandler(Protocol):
    """Protocol for action handlers.

    Handlers are responsible for:
    1. Validating action parameters before execution
    2. Executing the action and returning results
    3. Recording action outcomes for auditing/logging
    """

    def validate(self, action: Action) -> bool:
        """Validate action parameters.

        Args:
            action: The action to validate

        Returns:
            True if valid, False otherwise
        """
        ...

    def execute(self, action: Action) -> ActionResult:
        """Execute the action.

        Args:
            action: The action to execute

        Returns:
            ActionResult with success status and output/error
        """
        ...

    def record(self, action: Action, result: ActionResult) -> None:
        """Record action execution for auditing.

        Args:
            action: The action that was executed
            result: The result of execution
        """
        ...


@dataclass
class ActionResult:
    """Result of action execution.

    Attributes:
        success: Whether the action succeeded
        output: Output data from the action (if successful)
        error: Error message (if failed)
    """

    success: bool
    output: Any = None
    error: str | None = None


class ActionDispatcher:
    """Dispatcher for action handlers.

    Manages registration of handlers and routing of actions to
    appropriate handlers based on action_type.
    """

    def __init__(self) -> None:
        """Initialize dispatcher with empty handler registry."""
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, action_type: str, handler: ActionHandler) -> None:
        """Register a handler for an action type.

        Args:
            action_type: The action_type discriminator (e.g., "READ_FILE")
            handler: Handler instance for this action type
        """
        self._handlers[action_type] = handler

    def dispatch(self, action: Action) -> ActionResult:
        """Dispatch an action to its registered handler.

        Args:
            action: The action to dispatch

        Returns:
            ActionResult from the handler

        Raises:
            UnknownActionTypeError: If no handler is registered for action type
        """
        action_type = action.action_type
        if action_type not in self._handlers:
            raise UnknownActionTypeError(f"No handler registered for action type: {action_type}")
        handler = self._handlers[action_type]
        return handler.execute(action)


class UnknownActionTypeError(Exception):
    """Raised when dispatching to unregistered action type."""

    pass


class ReadFileHandler:
    """Handler for READ_FILE actions.

    Validates that the path parameter is a string.
    """

    def validate(self, action: Action) -> bool:
        """Validate READ_FILE action has string path.

        Args:
            action: Action to validate (must be ReadFileAction)

        Returns:
            True if path is a string
        """
        return isinstance(action, ReadFileAction)

    def execute(self, action: Action) -> ActionResult:
        """Execute READ_FILE action.

        Args:
            action: The ReadFileAction to execute

        Returns:
            ActionResult with success status
        """
        if not isinstance(action, ReadFileAction):
            return ActionResult(success=False, error="Invalid action: expected READ_FILE")
        if not self.validate(action):
            return ActionResult(success=False, error="Invalid action: path must be a string")
        # Placeholder - actual file reading would happen here
        return ActionResult(success=True, output=f"Would read file: {action.path}")

    def record(self, action: Action, result: ActionResult) -> None:
        """Record READ_FILE execution.

        Args:
            action: The executed action
            result: The execution result
        """
        # Placeholder - actual recording would happen here
        pass


__all__ = [
    "ActionHandler",
    "ActionResult",
    "ActionDispatcher",
    "UnknownActionTypeError",
    "ReadFileHandler",
]
