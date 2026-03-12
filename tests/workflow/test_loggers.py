"""Unit tests for workflow loggers."""

import json
from datetime import datetime
import pytest

from dawn_kestrel.workflow.loggers import ConsoleLogger, JsonLogger


def make_step(kind: str = "reason", why: str = "Test reason") -> dict[str, object]:
    return {
        "kind": kind,
        "why": why,
        "evidence": [],
        "next": "",
        "confidence": "medium",
        "action_result": None,
    }


def make_cycle() -> dict[str, object]:
    return {
        "reasoning": "Test",
        "action": "Test",
        "observation": "Test",
        "tools_used": [],
        "evidence": [],
    }


def make_frame(state: str = "test_state") -> dict[str, object]:
    return {
        "state": state,
        "ts": datetime.now(),
        "goals": [],
        "checks": [],
        "risks": [],
        "steps": [],
        "decision": "",
        "decision_type": "transition",
        "react_cycles": [],
    }


def make_log() -> dict[str, object]:
    return {
        "frames": [],
        "start_time": datetime.now(),
        "end_time": datetime.now(),
    }


class TestConsoleLogger:
    """Tests for ConsoleLogger."""

    def test_log_frame_with_state(self, capsys: pytest.CaptureFixture[str]):
        """Test logging a frame shows state name."""
        frame = make_frame("test_state")
        ConsoleLogger.log_frame(frame)

        captured: str = capsys.readouterr().out
        assert "TEST_STATE" in captured

    def test_log_frame_with_goals(self, capsys: pytest.CaptureFixture[str]):
        """Test logging a frame shows goals."""
        frame = make_frame("test_state")
        frame["goals"] = ["Goal 1", "Goal 2"]
        ConsoleLogger.log_frame(frame)

        captured: str = capsys.readouterr().out
        assert "Goal 1" in captured
        assert "Goal 2" in captured

    def test_log_frame_with_steps(self, capsys: pytest.CaptureFixture[str]):
        """Test logging a frame shows steps."""
        step = make_step()
        frame = make_frame("test_state")
        frame["steps"] = [step]
        ConsoleLogger.log_frame(frame)

        captured: str = capsys.readouterr().out
        assert "Test reason" in captured

    def test_log_frame_with_react_cycles(self, capsys: pytest.CaptureFixture[str]):
        """Test logging a frame shows REACT cycles."""
        cycle = make_cycle()
        frame = make_frame("test_state")
        frame["react_cycles"] = [cycle]
        ConsoleLogger.log_frame(frame)

        captured: str = capsys.readouterr().out
        # Just check for basic elements in the output
        assert "Test" in captured

    def test_log_frame_with_decision(self, capsys: pytest.CaptureFixture[str]):
        """Test logging a frame shows decision."""
        frame = make_frame("test_state")
        frame["decision"] = "Test decision"
        ConsoleLogger.log_frame(frame)

        captured: str = capsys.readouterr().out
        assert "Test decision" in captured


class TestJsonLogger:
    """Tests for JsonLogger."""

    def test_log_returns_json_string(self):
        """Test that log returns JSON string."""
        log = make_log()
        log["frames"] = [make_frame("test")]

        json_str = JsonLogger.log(log)
        assert isinstance(json_str, str)

    def test_log_returns_valid_json(self):
        """Test that log returns valid JSON."""
        log = make_log()
        log["frames"] = [make_frame("test")]

        json_str = JsonLogger.log(log)
        parsed = json.loads(json_str)

        assert "frames" in parsed
        assert len(parsed["frames"]) == 1
        assert parsed["frames"][0]["state"] == "test"

    def test_log_with_indent(self):
        """Test that log respects indent parameter."""
        log = make_log()
        log["frames"] = [make_frame("test")]

        json_str_no_indent = JsonLogger.log(log, indent=0)
        json_str_indent = JsonLogger.log(log, indent=2)

        # Indented version should be longer (more spaces)
        assert len(json_str_indent) > len(json_str_no_indent)

    def test_log_frame_returns_json_string(self):
        """Test that log_frame returns JSON string."""
        frame = make_frame("test_state")

        json_str = JsonLogger.log_frame(frame)
        assert isinstance(json_str, str)

    def test_log_frame_returns_valid_json(self):
        """Test that log_frame returns valid JSON."""
        frame = make_frame("test_state")

        json_str = JsonLogger.log_frame(frame)
        parsed = json.loads(json_str)

        assert "state" in parsed
        assert parsed["state"] == "test_state"

    def test_log_react_cycle_returns_json_string(self):
        """Test that log_react_cycle returns JSON string."""
        cycle = make_cycle()

        json_str = JsonLogger.log_react_cycle(cycle)
        assert isinstance(json_str, str)

    def test_log_react_cycle_returns_valid_json(self):
        """Test that log_react_cycle returns valid JSON."""
        cycle = make_cycle()

        json_str = JsonLogger.log_react_cycle(cycle)
        parsed = json.loads(json_str)

        assert "reasoning" in parsed
        assert "action" in parsed
        assert "observation" in parsed
