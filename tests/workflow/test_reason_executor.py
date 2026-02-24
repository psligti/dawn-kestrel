"""Tests for ReasonExecutor class.

This module tests the ReasonExecutor that wraps a ReasoningStrategy and
executes reasoning decisions while logging the thought trace for debugging.
"""

import logging
from unittest.mock import MagicMock

import pytest

from dawn_kestrel.workflow.reason_executor import ReasonExecutor
from dawn_kestrel.workflow.strategies import (
    ReasoningContext,
    ReasoningResult,
    ReasoningStrategy,
)


class MockReasoningStrategy:
    """Mock implementation of ReasoningStrategy for testing."""

    def decide(self, context: ReasoningContext) -> ReasoningResult:
        """Make a decision based on context."""
        return ReasoningResult(
            thought="Mock reasoning thought",
            action="mock_action",
            next_state="ACT",
        )


class TestReasonExecutorExists:
    """Test ReasonExecutor class exists and can be instantiated."""

    def test_reason_executor_exists(self):
        """Verify ReasonExecutor class can be imported and instantiated."""
        executor = ReasonExecutor(strategy=MockReasoningStrategy())
        assert executor is not None
        assert isinstance(executor, ReasonExecutor)

    def test_reason_executor_is_class(self):
        """Verify ReasonExecutor is a class, not a function."""
        assert isinstance(ReasonExecutor, type)


class TestReasonExecutorTakesStrategy:
    """Test ReasonExecutor accepts strategy via constructor."""

    def test_reason_executor_takes_strategy(self):
        """Verify ReasonExecutor accepts a strategy in constructor."""
        strategy = MockReasoningStrategy()
        executor = ReasonExecutor(strategy=strategy)
        assert executor._strategy is strategy

    def test_reason_executor_strategy_property(self):
        """Verify strategy property returns the injected strategy."""
        strategy = MockReasoningStrategy()
        executor = ReasonExecutor(strategy=strategy)
        assert executor.strategy is strategy

    def test_reason_executor_with_protocol_mock(self):
        """Verify ReasonExecutor works with spec=ReasoningStrategy mock."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)
        mock_strategy.decide.return_value = ReasoningResult(
            thought="Mock thought",
            action="mock",
            next_state="DONE",
        )
        executor = ReasonExecutor(strategy=mock_strategy)
        assert executor.strategy is mock_strategy


class TestReasonExecutorExecuteReturnsResult:
    """Test ReasonExecutor.execute() returns ReasoningResult."""

    def test_reason_executor_execute_returns_result(self):
        """Verify execute() returns a ReasoningResult."""
        executor = ReasonExecutor(strategy=MockReasoningStrategy())
        context = ReasoningContext(current_state="REASON")
        result = executor.execute(context)
        assert isinstance(result, ReasoningResult)

    def test_reason_executor_execute_result_has_required_fields(self):
        """Verify execute() result has thought, action, next_state."""
        executor = ReasonExecutor(strategy=MockReasoningStrategy())
        context = ReasoningContext(current_state="REASON")
        result = executor.execute(context)
        assert hasattr(result, "thought")
        assert hasattr(result, "action")
        assert hasattr(result, "next_state")

    def test_reason_executor_execute_with_context(self):
        """Verify execute() works with full context."""
        executor = ReasonExecutor(strategy=MockReasoningStrategy())
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate"],
            evidence=["file.py:10-20"],
            constraints={"max_iterations": 5},
        )
        result = executor.execute(context)
        assert result.thought == "Mock reasoning thought"
        assert result.action == "mock_action"
        assert result.next_state == "ACT"


class TestReasonExecutorDelegatesToStrategy:
    """Test ReasonExecutor delegates to strategy.decide()."""

    def test_reason_executor_delegates_to_strategy(self):
        """Verify execute() calls strategy.decide() with context."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)
        mock_strategy.decide.return_value = ReasoningResult(
            thought="Delegated thought",
            action="delegated_action",
            next_state="SYNTHESIZE",
        )
        executor = ReasonExecutor(strategy=mock_strategy)
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["act"],
        )
        result = executor.execute(context)
        # Verify decide was called with the context
        mock_strategy.decide.assert_called_once_with(context)
        # Verify result is from strategy
        assert result.thought == "Delegated thought"
        assert result.action == "delegated_action"
        assert result.next_state == "SYNTHESIZE"

    def test_reason_executor_no_business_logic(self):
        """Verify executor doesn't modify the strategy's result."""
        expected_result = ReasoningResult(
            thought="Original thought",
            action="original_action",
            next_state="DONE",
        )
        mock_strategy = MagicMock(spec=ReasoningStrategy)
        mock_strategy.decide.return_value = expected_result
        executor = ReasonExecutor(strategy=mock_strategy)
        context = ReasoningContext(current_state="REASON")
        result = executor.execute(context)
        # Result should be exactly what strategy returned
        assert result is expected_result


class TestReasonExecutorLogging:
    """Test ReasonExecutor logs thought trace for debugging."""

    def test_reason_executor_logs_thought_trace(self, caplog):
        """Verify execute() logs the thought trace in extra dict."""
        executor = ReasonExecutor(strategy=MockReasoningStrategy())
        context = ReasoningContext(current_state="REASON")
        with caplog.at_level(logging.INFO):
            result = executor.execute(context)
        # Should have logged the reasoning decision
        assert "Reasoning decision completed" in caplog.text
        # The thought is logged in extra dict, check via log record
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.thought == "Mock reasoning thought"
        assert record.action == "mock_action"
        assert record.next_state == "ACT"

    def test_reason_executor_logs_context_at_debug(self, caplog):
        """Verify execute() logs context details at debug level."""
        executor = ReasonExecutor(strategy=MockReasoningStrategy())
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze"],
            evidence=["evidence1"],
        )
        with caplog.at_level(logging.DEBUG):
            executor.execute(context)
        # Should have logged reasoning start
        assert "Starting reasoning execution" in caplog.text
