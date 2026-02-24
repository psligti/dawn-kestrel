"""Tests for ReasoningStrategy protocol and related models.

This module tests the ReasoningStrategy protocol that defines the interface
for reasoning strategies (CoT, ReAct, etc.) used by the REASON state.
"""

from dataclasses import asdict

import pytest

from dawn_kestrel.workflow.strategies import (
    ReasoningContext,
    ReasoningResult,
    ReasoningStrategy,
    ReActStrategy,
)


class TestReasoningStrategyProtocol:
    """Test ReasoningStrategy protocol can be implemented and used."""

    def test_reasoning_strategy_protocol_can_be_implemented(self):
        """Verify a class can implement ReasoningStrategy protocol."""

        class MockReasoningStrategy:
            """Mock implementation of ReasoningStrategy for testing."""

            def decide(self, context: ReasoningContext) -> ReasoningResult:
                """Make a decision based on context."""
                return ReasoningResult(
                    thought="Test thought",
                    action="test_action",
                    next_state="TEST_STATE",
                )

        strategy = MockReasoningStrategy()
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate", "complete"],
            evidence=["file.py:10-20"],
            constraints={"max_iterations": 5},
        )

        result = strategy.decide(context)

        assert result.thought == "Test thought"
        assert result.action == "test_action"
        assert result.next_state == "TEST_STATE"


class TestReasoningContext:
    """Test ReasoningContext dataclass."""

    def test_reasoning_context_creation(self):
        """Verify ReasoningContext can be created with required fields."""
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate"],
            evidence=["file.py:10"],
            constraints={"budget": 100},
        )

        assert context.current_state == "REASON"
        assert context.available_actions == ["analyze", "delegate"]
        assert context.evidence == ["file.py:10"]
        assert context.constraints == {"budget": 100}

    def test_reasoning_context_defaults(self):
        """Verify ReasoningContext has sensible defaults."""
        context = ReasoningContext(current_state="REASON")

        assert context.available_actions == []
        assert context.evidence == []
        assert context.constraints == {}


class TestReasoningResult:
    """Test ReasoningResult dataclass."""

    def test_reasoning_result_creation(self):
        """Verify ReasoningResult can be created with required fields."""
        result = ReasoningResult(
            thought="Need to analyze the code first",
            action="analyze",
            next_state="ACT",
        )

        assert result.thought == "Need to analyze the code first"
        assert result.action == "analyze"
        assert result.next_state == "ACT"

    def test_reasoning_result_is_dataclass(self):
        """Verify ReasoningResult is a dataclass with asdict support."""
        result = ReasoningResult(
            thought="Test",
            action="test",
            next_state="DONE",
        )

        result_dict = asdict(result)
        assert result_dict["thought"] == "Test"
        assert result_dict["action"] == "test"
        assert result_dict["next_state"] == "DONE"


class TestCoTStrategy:
    """Test CoTStrategy implementation."""

    def test_cot_strategy_exists(self):
        """Verify CoTStrategy class exists and can be instantiated."""
        from dawn_kestrel.workflow.strategies import CoTStrategy

        strategy = CoTStrategy()
        assert strategy is not None
        assert hasattr(strategy, "decide")

    def test_cot_strategy_implements_protocol(self):
        """Verify CoTStrategy implements ReasoningStrategy protocol."""
        from dawn_kestrel.workflow.strategies import CoTStrategy, ReasoningStrategy

        strategy = CoTStrategy()
        assert isinstance(strategy, ReasoningStrategy)

    def test_cot_strategy_decide_returns_result(self):
        """Verify CoTStrategy.decide() returns ReasoningResult."""
        from dawn_kestrel.workflow.strategies import CoTStrategy

        strategy = CoTStrategy()
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate", "complete"],
            evidence=["file.py:10-20"],
        )

        result = strategy.decide(context)

        assert isinstance(result, ReasoningResult)
        assert isinstance(result.thought, str)
        assert len(result.thought) > 0
        assert isinstance(result.action, str)
        assert len(result.action) > 0
        assert isinstance(result.next_state, str)
        assert len(result.next_state) > 0


class TestReActStrategy:
    """Test ReActStrategy implementation."""

    def test_react_strategy_exists(self):
        """Verify ReActStrategy class exists and can be instantiated."""
        strategy = ReActStrategy()
        assert strategy is not None
        assert hasattr(strategy, "decide")

    def test_react_strategy_implements_protocol(self):
        """Verify ReActStrategy implements ReasoningStrategy protocol."""
        strategy = ReActStrategy()
        assert isinstance(strategy, ReasoningStrategy)

    def test_react_strategy_decide_returns_result(self):
        """Verify ReActStrategy.decide() returns ReasoningResult."""
        strategy = ReActStrategy()
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate", "complete"],
            evidence=["file.py:10-20"],
        )

        result = strategy.decide(context)

        assert isinstance(result, ReasoningResult)
        assert isinstance(result.thought, str)
        assert len(result.thought) > 0
        assert isinstance(result.action, str)
        assert len(result.action) > 0
        assert isinstance(result.next_state, str)
        assert len(result.next_state) > 0

    def test_react_strategy_with_observation(self):
        """Verify ReActStrategy handles observations from previous steps."""
        strategy = ReActStrategy()
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate", "complete"],
            evidence=[
                "file.py:10-20",
                "observation:grep_found_3_files",
            ],
        )

        result = strategy.decide(context)

        assert isinstance(result, ReasoningResult)
        assert "observation" in result.thought.lower()
        assert "grep_found_3_files" in result.thought
