"""Unit tests for workflow loggers."""

import json

import pytest

from dawn_kestrel.workflow.loggers import ConsoleLogger, JsonLogger
from dawn_kestrel.workflow.models import (
    ActionType,
    ReactStep,
    RunLog,
    ThinkingFrame,
    ThinkingStep,
)


class TestConsoleLogger:
    """Tests for ConsoleLogger."""

    def test_log_frame_with_state(self, capsys):
        """Test logging a frame shows state name."""
        frame = ThinkingFrame(state="test_state")
        ConsoleLogger.log_frame(frame)

        captured = capsys.readouterr().out
        assert "TEST_STATE" in captured

    def test_log_frame_with_goals(self, capsys):
        """Test logging a frame shows goals."""
        frame = ThinkingFrame(state="test_state", goals=["Goal 1", "Goal 2"])
        ConsoleLogger.log_frame(frame)

        captured = capsys.readouterr().out
        assert "Goal 1" in captured
        assert "Goal 2" in captured

    def test_log_frame_with_steps(self, capsys):
        """Test logging a frame shows steps."""
        step = ThinkingStep(kind=ActionType.REASON, why="Test reason")
        frame = ThinkingFrame(state="test_state", steps=[step])
        ConsoleLogger.log_frame(frame)

        captured = capsys.readouterr().out
        assert "Test reason" in captured

    def test_log_frame_with_react_cycles(self, capsys):
        """Test logging a frame shows REACT cycles."""
        cycle = ReactStep(reasoning="Test", action="Test", observation="Test")
        frame = ThinkingFrame(state="test_state", react_cycles=[cycle])
        ConsoleLogger.log_frame(frame)

        captured = capsys.readouterr().out
        # Just check for basic elements in the output
        assert "Test" in captured

    def test_log_frame_with_decision(self, capsys):
        """Test logging a frame shows decision."""
        frame = ThinkingFrame(state="test_state", decision="Test decision")
        ConsoleLogger.log_frame(frame)

        captured = capsys.readouterr().out
        assert "Test decision" in captured


class TestJsonLogger:
    """Tests for JsonLogger."""

    def test_log_returns_json_string(self):
        """Test that log returns JSON string."""
        log = RunLog()
        frame = ThinkingFrame(state="test")
        log.add(frame)

        json_str = JsonLogger.log(log)
        assert isinstance(json_str, str)

    def test_log_returns_valid_json(self):
        """Test that log returns valid JSON."""
        log = RunLog()
        frame = ThinkingFrame(state="test")
        log.add(frame)

        json_str = JsonLogger.log(log)
        parsed = json.loads(json_str)

        assert "frames" in parsed
        assert len(parsed["frames"]) == 1
        assert parsed["frames"][0]["state"] == "test"

    def test_log_with_indent(self):
        """Test that log respects indent parameter."""
        log = RunLog()
        frame = ThinkingFrame(state="test")
        log.add(frame)

        json_str_no_indent = JsonLogger.log(log, indent=0)
        json_str_indent = JsonLogger.log(log, indent=2)

        # Indented version should be longer (more spaces)
        assert len(json_str_indent) > len(json_str_no_indent)

    def test_log_frame_returns_json_string(self):
        """Test that log_frame returns JSON string."""
        frame = ThinkingFrame(state="test_state")

        json_str = JsonLogger.log_frame(frame)
        assert isinstance(json_str, str)

    def test_log_frame_returns_valid_json(self):
        """Test that log_frame returns valid JSON."""
        frame = ThinkingFrame(state="test_state")

        json_str = JsonLogger.log_frame(frame)
        parsed = json.loads(json_str)

        assert "state" in parsed
        assert parsed["state"] == "test_state"

    def test_log_react_cycle_returns_json_string(self):
        """Test that log_react_cycle returns JSON string."""
        cycle = ReactStep(reasoning="Test", action="Test", observation="Test")

        json_str = JsonLogger.log_react_cycle(cycle)
        assert isinstance(json_str, str)

    def test_log_react_cycle_returns_valid_json(self):
        """Test that log_react_cycle returns valid JSON."""
        cycle = ReactStep(reasoning="Test", action="Test", observation="Test")

        json_str = JsonLogger.log_react_cycle(cycle)
        parsed = json.loads(json_str)

        assert "reasoning" in parsed
        assert "action" in parsed
        assert "observation" in parsed
