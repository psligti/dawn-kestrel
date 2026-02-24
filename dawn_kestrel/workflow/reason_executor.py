"""ReasonExecutor for executing reasoning strategies with thought trace logging.

This module provides the ReasonExecutor class that wraps a ReasoningStrategy
and executes reasoning decisions while logging the thought trace for debugging.

Key concepts:
- ReasonExecutor: Wraps a ReasoningStrategy and provides execute() method
- Thought trace logging: Logs reasoning decisions for debugging/auditing
- Strategy delegation: All business logic delegated to injected strategy
"""

from __future__ import annotations

import logging

from dawn_kestrel.workflow.strategies import (
    ReasoningContext,
    ReasoningResult,
    ReasoningStrategy,
)

logger = logging.getLogger(__name__)


class ReasonExecutor:
    """Executor that wraps a ReasoningStrategy and executes reasoning decisions.

    The ReasonExecutor is a simple wrapper that:
    1. Accepts a ReasoningStrategy via constructor (dependency injection)
    2. Provides an execute() method that delegates to the strategy
    3. Logs the thought trace for debugging and auditing

    This follows the executor pattern - no business logic, just delegation
    and cross-cutting concerns (logging).

    Example:
        >>> from dawn_kestrel.workflow.strategies import (
        ...     ReasoningContext, ReasoningResult, ReasoningStrategy
        ... )
        >>> class MyStrategy:
        ...     def decide(self, context: ReasoningContext) -> ReasoningResult:
        ...         return ReasoningResult(
        ...             thought="Analyzing...",
        ...             action="analyze",
        ...             next_state="ACT"
        ...         )
        >>> executor = ReasonExecutor(strategy=MyStrategy())
        >>> context = ReasoningContext(current_state="REASON")
        >>> result = executor.execute(context)

    Attributes:
        _strategy: The reasoning strategy to use for decisions.
    """

    def __init__(self, strategy: ReasoningStrategy) -> None:
        """Initialize the executor with a reasoning strategy.

        Args:
            strategy: The ReasoningStrategy to use for making decisions.
                Must implement the decide(context) -> ReasoningResult method.
        """
        self._strategy = strategy

    @property
    def strategy(self) -> ReasoningStrategy:
        """Get the underlying reasoning strategy.

        Returns:
            The ReasoningStrategy instance used by this executor.
        """
        return self._strategy

    def execute(self, context: ReasoningContext) -> ReasoningResult:
        """Execute reasoning on the given context.

        This method:
        1. Logs the start of reasoning with context details
        2. Delegates to the strategy's decide() method
        3. Logs the thought trace from the result
        4. Returns the result

        Args:
            context: The reasoning context containing current state,
                available actions, evidence, and constraints.

        Returns:
            ReasoningResult: The decision with thought, action, and next_state.

        Example:
            >>> context = ReasoningContext(
            ...     current_state="REASON",
            ...     available_actions=["analyze", "delegate"],
            ...     evidence=["file.py:10-20"],
            ... )
            >>> result = executor.execute(context)
            >>> print(result.action)
            'analyze'
        """
        # Log reasoning start with context details
        logger.debug(
            "Starting reasoning execution",
            extra={
                "current_state": context.current_state,
                "available_actions": context.available_actions,
                "evidence_count": len(context.evidence),
                "constraints": context.constraints,
            },
        )

        # Delegate to strategy
        result = self._strategy.decide(context)

        # Log thought trace for debugging
        logger.info(
            "Reasoning decision completed",
            extra={
                "thought": result.thought,
                "action": result.action,
                "next_state": result.next_state,
            },
        )

        return result
