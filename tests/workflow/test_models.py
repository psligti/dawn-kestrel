"""Unit tests for workflow models."""

import json
from datetime import datetime

import pytest

from dawn_kestrel.workflow.models import (
    ActionType,
    Confidence,
    DecisionType,
    ReactStep,
    RunLog,
    StructuredContext,
    ThinkingFrame,
    ThinkingStep,
    Todo,
)


class TestThinkingStep:
    """Tests for ThinkingStep model."""

    def test_create_with_required_fields(self):
        """Test creating ThinkingStep with required fields."""
        step = ThinkingStep(
            kind=ActionType.REASON,
            why="Test reason",
        )
        assert step.kind == ActionType.REASON
        assert step.why == "Test reason"
        assert step.confidence == Confidence.MEDIUM
        assert step.evidence == []
        assert step.next == ""
        assert step.action_result is None

    def test_create_with_all_fields(self):
        """Test creating ThinkingStep with all fields."""
        step = ThinkingStep(
            kind=ActionType.ACT,
            why="Execute tool",
            evidence=["file:test.py", "tool:grep#1"],
            next="continue",
            confidence=Confidence.HIGH,
            action_result="Tool completed",
        )
        assert step.kind == ActionType.ACT
        assert step.evidence == ["file:test.py", "tool:grep#1"]
        assert step.next == "continue"
        assert step.confidence == Confidence.HIGH
        assert step.action_result == "Tool completed"

    def test_to_dict(self):
        """Test ThinkingStep to_dict conversion."""
        step = ThinkingStep(
            kind=ActionType.OBSERVE,
            why="Observe result",
            evidence=["tool:output"],
        )
        d = step.to_dict()
        assert d["kind"] == "observe"
        assert d["why"] == "Observe result"
        assert d["evidence"] == ["tool:output"]
        assert d["confidence"] == "medium"


class TestReactStep:
    """Tests for ReactStep model."""

    def test_create_with_required_fields(self):
        """Test creating ReactStep with required fields."""
        cycle = ReactStep(
            reasoning="Need to check file",
            action="Run grep",
            observation="Found 3 matches",
        )
        assert cycle.reasoning == "Need to check file"
        assert cycle.action == "Run grep"
        assert cycle.observation == "Found 3 matches"
        assert cycle.tools_used == []
        assert cycle.evidence == []

    def test_create_with_all_fields(self):
        """Test creating ReactStep with all fields."""
        cycle = ReactStep(
            reasoning="Need to scan",
            action="Run ast-grep",
            observation="Found vulnerabilities",
            tools_used=["ast-grep", "grep"],
            evidence=["file:auth.py", "diff:security"],
        )
        assert len(cycle.tools_used) == 2
        assert len(cycle.evidence) == 2

    def test_to_dict(self):
        """Test ReactStep to_dict conversion."""
        cycle = ReactStep(
            reasoning="Test reasoning",
            action="Test action",
            observation="Test observation",
        )
        d = cycle.to_dict()
        assert d["reasoning"] == "Test reasoning"
        assert d["action"] == "Test action"
        assert d["observation"] == "Test observation"


class TestThinkingFrame:
    """Tests for ThinkingFrame model."""

    def test_create_with_required_fields(self):
        """Test creating ThinkingFrame with required fields."""
        frame = ThinkingFrame(state="test_state")
        assert frame.state == "test_state"
        assert frame.goals == []
        assert frame.steps == []
        assert frame.decision == ""
        assert frame.decision_type == DecisionType.TRANSITION
        assert frame.react_cycles == []

    def test_create_with_all_fields(self):
        """Test creating ThinkingFrame with all fields."""
        step = ThinkingStep(kind=ActionType.REASON, why="Test step")
        frame = ThinkingFrame(
            state="test_state",
            goals=["Goal 1", "Goal 2"],
            checks=["Check 1"],
            risks=["Risk 1"],
            steps=[step],
            decision="Test decision",
            decision_type=DecisionType.STOP,
        )
        assert len(frame.goals) == 2
        assert len(frame.checks) == 1
        assert len(frame.risks) == 1
        assert len(frame.steps) == 1
        assert frame.decision == "Test decision"
        assert frame.decision_type == DecisionType.STOP

    def test_add_step(self):
        """Test adding a step to a frame."""
        frame = ThinkingFrame(state="test")
        step = ThinkingStep(kind=ActionType.REASON, why="Test")
        frame.add_step(step)
        assert len(frame.steps) == 1
        assert frame.steps[0] == step

    def test_add_react_cycle(self):
        """Test adding a REACT cycle to a frame."""
        frame = ThinkingFrame(state="test")
        cycle = ReactStep(reasoning="Test", action="Test", observation="Test")
        frame.add_react_cycle(cycle)
        assert len(frame.react_cycles) == 1
        assert frame.react_cycles[0] == cycle

    def test_to_dict(self):
        """Test ThinkingFrame to_dict conversion."""
        frame = ThinkingFrame(state="test")
        frame.goals = ["Goal 1"]
        step = ThinkingStep(kind=ActionType.REASON, why="Test")
        frame.add_step(step)

        d = frame.to_dict()
        assert d["state"] == "test"
        assert d["goals"] == ["Goal 1"]
        assert len(d["steps"]) == 1
        assert d["steps"][0]["kind"] == "reason"


class TestRunLog:
    """Tests for RunLog model."""

    def test_create_empty(self):
        """Test creating empty RunLog."""
        log = RunLog()
        assert log.frames == []
        assert log.frame_count == 0
        assert log.start_time is None
        assert log.end_time is None

    def test_add_frame(self):
        """Test adding a frame to RunLog."""
        log = RunLog()
        frame = ThinkingFrame(state="test")
        log.add(frame)
        assert log.frame_count == 1
        assert log.frames[0] == frame

    def test_to_json(self):
        """Test RunLog to_json conversion."""
        log = RunLog()
        log.start_time = datetime(2024, 1, 1, 12, 0, 0)
        frame = ThinkingFrame(state="test")
        log.add(frame)
        log.end_time = datetime(2024, 1, 1, 12, 30, 0)

        json_str = log.to_json()
        parsed = json.loads(json_str)

        assert "frames" in parsed
        assert "start_time" in parsed
        assert "end_time" in parsed
        assert len(parsed["frames"]) == 1
        assert parsed["frames"][0]["state"] == "test"

    def test_get_frames_for_state(self):
        """Test getting frames for a specific state."""
        log = RunLog()
        frame1 = ThinkingFrame(state="state1")
        frame2 = ThinkingFrame(state="state2")
        frame3 = ThinkingFrame(state="state1")
        log.add(frame1)
        log.add(frame2)
        log.add(frame3)

        state1_frames = log.get_frames_for_state("state1")
        assert len(state1_frames) == 2
        assert frame1 in state1_frames
        assert frame3 in state1_frames


class TestTodo:
    """Tests for Todo model."""

    def test_create_with_required_fields(self):
        """Test creating Todo with required fields."""
        todo = Todo(
            id="todo_1",
            title="Test todo",
            rationale="Need to test",
        )
        assert todo.id == "todo_1"
        assert todo.title == "Test todo"
        assert todo.rationale == "Need to test"
        assert todo.evidence == []
        assert todo.status == "pending"
        assert todo.priority == "medium"

    def test_create_with_all_fields(self):
        """Test creating Todo with all fields."""
        todo = Todo(
            id="todo_2",
            title="Test todo",
            rationale="Need to test",
            evidence=["file:test.py"],
            status="completed",
            priority="high",
        )
        assert todo.evidence == ["file:test.py"]
        assert todo.status == "completed"
        assert todo.priority == "high"

    def test_to_dict(self):
        """Test Todo to_dict conversion."""
        todo = Todo(
            id="todo_1",
            title="Test todo",
            rationale="Need to test",
        )
        d = todo.to_dict()
        assert d["id"] == "todo_1"
        assert d["title"] == "Test todo"
        assert d["rationale"] == "Need to test"


class TestStructuredContext:
    """Tests for StructuredContext model."""

    def test_create_with_defaults(self):
        """Test creating StructuredContext with defaults."""
        ctx = StructuredContext()
        assert ctx.state == "intake"
        assert ctx.changed_files == []
        assert ctx.todos == {}
        assert ctx.subagent_results == {}
        assert ctx.consolidated == {}
        assert ctx.evaluation == {}
        assert ctx.log.frame_count == 0

    def test_create_with_values(self):
        """Test creating StructuredContext with values."""
        ctx = StructuredContext(
            state="delegate",
            changed_files=["file1.py", "file2.py"],
        )
        assert ctx.state == "delegate"
        assert len(ctx.changed_files) == 2

    def test_add_todo(self):
        """Test adding a todo to context."""
        ctx = StructuredContext()
        todo = Todo(id="todo_1", title="Test", rationale="Need")
        ctx.add_todo(todo)
        assert ctx.todo_count == 1
        assert ctx.todos["todo_1"] == todo

    def test_get_todo(self):
        """Test getting a todo by ID."""
        ctx = StructuredContext()
        todo = Todo(id="todo_1", title="Test", rationale="Need")
        ctx.add_todo(todo)
        retrieved = ctx.get_todo("todo_1")
        assert retrieved == todo
        assert ctx.get_todo("nonexistent") is None

    def test_add_subagent_result(self):
        """Test adding subagent result."""
        ctx = StructuredContext()
        ctx.add_subagent_result("task_1", {"result": "success"})
        assert ctx.subagent_results["task_1"] == {"result": "success"}

    def test_add_frame(self):
        """Test adding a frame to log."""
        ctx = StructuredContext()
        frame = ThinkingFrame(state="test")
        ctx.add_frame(frame)
        assert ctx.log.frame_count == 1
        assert ctx.log.frames[0] == frame

    def test_pending_todos(self):
        """Test getting pending todos."""
        ctx = StructuredContext()
        todo1 = Todo(id="t1", title="Test 1", rationale="Need")
        todo2 = Todo(id="t2", title="Test 2", rationale="Need")
        todo3 = Todo(id="t3", title="Test 3", rationale="Need", status="completed")
        ctx.add_todo(todo1)
        ctx.add_todo(todo2)
        ctx.add_todo(todo3)

        pending = ctx.pending_todos
        assert len(pending) == 2
        assert todo1 in pending
        assert todo2 in pending
        assert todo3 not in pending
