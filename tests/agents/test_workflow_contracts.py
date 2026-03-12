"""Test suite for workflow phase output contracts.

Tests the Pydantic models in dawn_kestrel/agents/workflow.py for:
- Valid model instantiation
- Required field enforcement
- Extra field rejection (extra="forbid")
- Schema helper functions return valid strings
- Invalid enum values are rejected
- Out-of-range values are rejected
"""

import pytest
from pydantic import ValidationError

from dawn_kestrel.agents.workflow import (
    ActOutput,
    BudgetConsumed,
    CheckOutput,
    IntakeOutput,
    PlanOutput,
    ReasonOutput,
    SynthesizedFinding,
    SynthesizeOutput,
    TodoItem,
    ToolExecution,
    get_act_output_schema,
    get_check_output_schema,
    get_intake_output_schema,
    get_plan_output_schema,
    get_reason_output_schema,
    get_synthesize_output_schema,
)


class TestIntakeOutput:
    """Test IntakeOutput Pydantic model."""

    def test_intake_output_valid_with_all_fields(self):
        """Test IntakeOutput with all fields provided."""
        output = IntakeOutput(
            intent="Add JWT authentication to auth module",
            constraints=["Cannot access external services", "Must complete in 5 iterations"],
            initial_evidence=["Auth module exists at src/auth/", "No existing JWT integration"],
        )

        assert output.intent == "Add JWT authentication to auth module"
        assert len(output.constraints) == 2
        assert len(output.initial_evidence) == 2

    def test_intake_output_valid_with_minimal_fields(self):
        """Test IntakeOutput with only required field."""
        output = IntakeOutput(intent="Test intent")

        assert output.intent == "Test intent"
        assert output.constraints == []
        assert output.initial_evidence == []

    def test_intake_output_missing_required_field(self):
        """Test IntakeOutput rejects missing required intent field."""
        with pytest.raises(ValidationError) as exc_info:
            IntakeOutput(constraints=["test"])

        errors = exc_info.value.errors()
        assert any("intent" in error["loc"] for error in errors)

    def test_intake_output_rejects_extra_fields(self):
        """Test IntakeOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            IntakeOutput(
                intent="Test",
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_intake_output_schema_returns_string(self):
        """Test get_intake_output_schema returns a valid string."""
        schema = get_intake_output_schema()

        assert isinstance(schema, str)
        assert "IntakeOutput" in schema
        assert "intent" in schema
        assert "constraints" in schema
        assert "initial_evidence" in schema
        assert "CRITICAL RULES" in schema
        assert "extra fields" in schema


class TestTodoItem:
    """Test TodoItem Pydantic model."""

    def test_todo_item_valid_with_all_fields(self):
        """Test TodoItem with all fields provided."""
        todo = TodoItem(
            id="1",
            operation="create",
            description="Research JWT patterns",
            priority="high",
            status="pending",
            dependencies=["2"],
            notes="Must understand JWT first",
        )

        assert todo.id == "1"
        assert todo.operation == "create"
        assert todo.priority == "high"
        assert todo.status == "pending"
        assert todo.dependencies == ["2"]
        assert todo.notes == "Must understand JWT first"

    def test_todo_item_valid_with_minimal_fields(self):
        """Test TodoItem with only required fields."""
        todo = TodoItem(
            id="1",
            operation="modify",
            description="Update auth code",
        )

        assert todo.id == "1"
        assert todo.operation == "modify"
        assert todo.priority == "medium"  # default
        assert todo.status == "pending"  # default
        assert todo.dependencies == []  # default
        assert todo.notes == ""  # default

    def test_todo_item_invalid_operation(self):
        """Test TodoItem rejects invalid operation value."""
        with pytest.raises(ValidationError) as exc_info:
            TodoItem(
                id="1",
                operation="invalid_operation",
                description="Test",
            )

        errors = exc_info.value.errors()
        assert any("operation" in error["loc"] for error in errors)

    def test_todo_item_invalid_priority(self):
        """Test TodoItem rejects invalid priority value."""
        with pytest.raises(ValidationError) as exc_info:
            TodoItem(
                id="1",
                operation="create",
                description="Test",
                priority="invalid",
            )

        errors = exc_info.value.errors()
        assert any("priority" in error["loc"] for error in errors)

    def test_todo_item_invalid_status(self):
        """Test TodoItem rejects invalid status value."""
        with pytest.raises(ValidationError) as exc_info:
            TodoItem(
                id="1",
                operation="create",
                description="Test",
                status="invalid",
            )

        errors = exc_info.value.errors()
        assert any("status" in error["loc"] for error in errors)

    def test_todo_item_rejects_extra_fields(self):
        """Test TodoItem with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            TodoItem(
                id="1",
                operation="create",
                description="Test",
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)


class TestPlanOutput:
    """Test PlanOutput Pydantic model."""

    def test_plan_output_valid_with_all_fields(self):
        """Test PlanOutput with all fields provided."""
        todos = [
            TodoItem(id="1", operation="create", description="Task 1"),
            TodoItem(id="2", operation="modify", description="Task 2"),
        ]

        output = PlanOutput(
            todos=todos,
            reasoning="Test reasoning",
            estimated_iterations=3,
            strategy_selected="Test strategy",
        )

        assert len(output.todos) == 2
        assert output.reasoning == "Test reasoning"
        assert output.estimated_iterations == 3
        assert output.strategy_selected == "Test strategy"

    def test_plan_output_valid_with_minimal_fields(self):
        """Test PlanOutput with only required field."""
        output = PlanOutput(todos=[])

        assert output.todos == []
        assert output.reasoning == ""
        assert output.estimated_iterations == 1
        assert output.strategy_selected == ""

    def test_plan_output_accepts_empty_todos_list(self):
        """Test PlanOutput accepts empty todos list with default."""
        output = PlanOutput(reasoning="test")

        assert output.reasoning == "test"
        # todos has default_factory=list, so empty list is accepted
        assert output.todos == []

    def test_plan_output_rejects_extra_fields(self):
        """Test PlanOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            PlanOutput(todos=[], unknown_field="should be rejected")

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_plan_output_schema_returns_string(self):
        """Test get_plan_output_schema returns a valid string."""
        schema = get_plan_output_schema()

        assert isinstance(schema, str)
        assert "PlanOutput" in schema
        assert "todos" in schema
        assert "operation" in schema
        assert "CRITICAL RULES" in schema


class TestReasonOutput:
    """Test ReasonOutput Pydantic model."""

    def test_reason_output_valid_with_all_fields(self):
        """Test ReasonOutput with all fields provided."""
        output = ReasonOutput(
            todo_id="todo-1",
            atomic_step="Read auth module",
            why_now="Need to understand current implementation",
            next_phase="act",
            confidence=0.85,
            evidence_used=["auth module exists"],
            risks=["may need refactoring"],
        )

        assert output.todo_id == "todo-1"
        assert output.atomic_step == "Read auth module"
        assert output.why_now == "Need to understand current implementation"
        assert output.next_phase == "act"
        assert output.confidence == 0.85
        assert output.evidence_used == ["auth module exists"]
        assert output.risks == ["may need refactoring"]

    def test_reason_output_valid_with_minimal_fields(self):
        """Test ReasonOutput with only required fields."""
        output = ReasonOutput(
            todo_id="todo-2",
            atomic_step="Search for tests",
            why_now="Need to verify existing coverage",
        )

        assert output.todo_id == "todo-2"
        assert output.atomic_step == "Search for tests"
        assert output.why_now == "Need to verify existing coverage"
        assert output.next_phase == "act"  # default
        assert output.confidence is None
        assert output.evidence_used is None
        assert output.risks is None

    def test_reason_output_missing_required_field(self):
        """Test ReasonOutput rejects missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ReasonOutput(todo_id="todo-1")  # missing atomic_step, why_now

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "atomic_step" in error_fields
        assert "why_now" in error_fields

    def test_reason_output_rejects_extra_fields(self):
        """Test ReasonOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ReasonOutput(
                todo_id="todo-1",
                atomic_step="Test",
                why_now="Test reason",
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_reason_output_invalid_next_phase(self):
        """Test ReasonOutput rejects invalid next_phase value."""
        with pytest.raises(ValidationError) as exc_info:
            ReasonOutput(
                todo_id="todo-1",
                atomic_step="Test",
                why_now="Test reason",
                next_phase="invalid_phase",
            )

        errors = exc_info.value.errors()
        assert any("next_phase" in error["loc"] for error in errors)

    def test_get_reason_output_schema_returns_string(self):
        """Test get_reason_output_schema returns a valid string."""
        schema = get_reason_output_schema()

        assert isinstance(schema, str)
        assert "ReasonOutput" in schema
        assert "todo_id" in schema
        assert "atomic_step" in schema
        assert "why_now" in schema
        assert "CRITICAL RULES" in schema

class TestToolExecution:
    """Test ToolExecution Pydantic model."""

    def test_tool_execution_valid_with_all_fields(self):
        """Test ToolExecution with all fields provided."""
        execution = ToolExecution(
            tool_name="read",
            selection_reason="Need to examine file structure",
            arguments={"file_path": "test.py"},
            status="success",
            result_summary="Read file successfully",
            duration_seconds=1.5,
            artifacts=["test.py"],
        )

        assert execution.tool_name == "read"
        assert execution.selection_reason == "Need to examine file structure"
        assert execution.arguments == {"file_path": "test.py"}
        assert execution.status == "success"
        assert execution.duration_seconds == 1.5
        assert execution.artifacts == ["test.py"]

    def test_tool_execution_valid_with_minimal_fields(self):
        """Test ToolExecution with only required fields."""
        execution = ToolExecution(
            tool_name="grep",
            selection_reason="Need to search for patterns",
            status="success",
        )

        assert execution.tool_name == "grep"
        assert execution.selection_reason == "Need to search for patterns"
        assert execution.arguments == {}
        assert execution.result_summary == ""
        assert execution.duration_seconds == 0.0
        assert execution.artifacts == []

    def test_tool_execution_invalid_status(self):
        """Test ToolExecution rejects invalid status value."""
        with pytest.raises(ValidationError) as exc_info:
            ToolExecution(
                tool_name="test",
                selection_reason="Test reason",
                status="invalid_status",
            )

        errors = exc_info.value.errors()
        assert any("status" in error["loc"] for error in errors)

    def test_tool_execution_rejects_extra_fields(self):
        """Test ToolExecution with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ToolExecution(
                tool_name="test",
                selection_reason="Test reason",
                status="success",
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_tool_execution_missing_selection_reason(self):
        """Test ToolExecution rejects missing selection_reason field."""
        with pytest.raises(ValidationError) as exc_info:
            ToolExecution(
                tool_name="test",
                status="success",
            )  # missing selection_reason

        errors = exc_info.value.errors()
        assert any("selection_reason" in error["loc"] for error in errors)

class TestActOutput:
    """Test ActOutput Pydantic model."""

    def test_act_output_valid_with_all_fields(self):
        """Test ActOutput with all fields provided."""
        action = ToolExecution(
            tool_name="read",
            selection_reason="Need to examine file",
            status="success",
        )

        output = ActOutput(
            action=action,
            acted_todo_id="todo-1",
            tool_result_summary="Test summary",
            artifacts=["file1.py", "file2.py"],
            failure="",
        )

        assert output.action is not None
        assert output.action.tool_name == "read"
        assert output.acted_todo_id == "todo-1"
        assert output.tool_result_summary == "Test summary"
        assert output.artifacts == ["file1.py", "file2.py"]
        assert output.failure == ""

    def test_act_output_valid_with_minimal_fields(self):
        """Test ActOutput with only required field."""
        output = ActOutput()

        assert output.action is None
        assert output.acted_todo_id == ""
        assert output.tool_result_summary == ""
        assert output.artifacts == []
        assert output.failure == ""

    def test_act_output_accepts_null_action(self):
        """Test ActOutput accepts null action with default."""
        output = ActOutput(acted_todo_id="todo-2")

        assert output.acted_todo_id == "todo-2"
        # action defaults to None
        assert output.action is None

    def test_act_output_rejects_extra_fields(self):
        """Test ActOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ActOutput(unknown_field="should be rejected")

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_act_output_schema_returns_string(self):
        """Test get_act_output_schema returns a valid string."""
        schema = get_act_output_schema()

        assert isinstance(schema, str)
        assert "ActOutput" in schema
        assert "action" in schema
        assert "tool_name" in schema
        assert "selection_reason" in schema
        assert "CRITICAL RULES" in schema

    def test_get_act_output_schema_forbids_justification_in_arguments(self):
        """Test get_act_output_schema explicitly forbids justification in action.arguments."""
        schema = get_act_output_schema()

        assert "DO NOT put justification" in schema
        assert "action.arguments" in schema
        assert "selection_reason" in schema


class TestSynthesizedFinding:
    """Test SynthesizedFinding Pydantic model."""

    def test_synthesized_finding_valid_with_all_fields(self):
        """Test SynthesizedFinding with all fields provided."""
        finding = SynthesizedFinding(
            id="F-001",
            category="security",
            severity="critical",
            title="Test finding",
            description="Test description",
            evidence="Test evidence",
            recommendation="Test recommendation",
            confidence=0.85,
            related_todos=["1"],
        )

        assert finding.id == "F-001"
        assert finding.category == "security"
        assert finding.severity == "critical"
        assert finding.confidence == 0.85
        assert finding.related_todos == ["1"]

    def test_synthesized_finding_valid_with_minimal_fields(self):
        """Test SynthesizedFinding with only required fields."""
        finding = SynthesizedFinding(
            id="F-002",
            category="performance",
            severity="high",
            title="Performance issue",
        )

        assert finding.id == "F-002"
        assert finding.description == ""
        assert finding.recommendation == ""
        assert finding.confidence == 0.5
        assert finding.related_todos == []

    def test_synthesized_finding_invalid_category(self):
        """Test SynthesizedFinding rejects invalid category value."""
        with pytest.raises(ValidationError) as exc_info:
            SynthesizedFinding(
                id="1",
                category="invalid",
                severity="high",
                title="Test",
            )

        errors = exc_info.value.errors()
        assert any("category" in error["loc"] for error in errors)

    def test_synthesized_finding_invalid_severity(self):
        """Test SynthesizedFinding rejects invalid severity value."""
        with pytest.raises(ValidationError) as exc_info:
            SynthesizedFinding(
                id="1",
                category="security",
                severity="invalid",
                title="Test",
            )

        errors = exc_info.value.errors()
        assert any("severity" in error["loc"] for error in errors)

    def test_synthesized_finding_confidence_out_of_range(self):
        """Test SynthesizedFinding rejects confidence outside 0.0-1.0 range."""
        with pytest.raises(ValueError) as exc_info:
            SynthesizedFinding(
                id="1",
                category="security",
                severity="high",
                title="Test",
                confidence=1.5,
            )

        assert "confidence must be between 0.0 and 1.0" in str(exc_info.value)

    def test_synthesized_finding_rejects_extra_fields(self):
        """Test SynthesizedFinding with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            SynthesizedFinding(
                id="1",
                category="security",
                severity="high",
                title="Test",
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)


class TestSynthesizeOutput:
    """Test SynthesizeOutput Pydantic model."""

    def test_synthesize_output_valid_with_all_fields(self):
        """Test SynthesizeOutput with all fields provided."""
        findings = [
            SynthesizedFinding(
                id="F-001",
                category="security",
                severity="high",
                title="Test finding",
            )
        ]
        todos = [TodoItem(id="1", operation="create", description="Task")]

        output = SynthesizeOutput(
            findings=findings,
            updated_todos=todos,
            summary="Test summary",
            uncertainty_reduction=0.6,
            confidence_level=0.8,
        )

        assert len(output.findings) == 1
        assert len(output.updated_todos) == 1
        assert output.summary == "Test summary"
        assert output.uncertainty_reduction == 0.6
        assert output.confidence_level == 0.8

    def test_synthesize_output_valid_with_minimal_fields(self):
        """Test SynthesizeOutput with only required fields."""
        output = SynthesizeOutput(findings=[], updated_todos=[])

        assert output.findings == []
        assert output.updated_todos == []
        assert output.summary == ""
        assert output.uncertainty_reduction == 0.0
        assert output.confidence_level == 0.5

    def test_synthesize_output_accepts_empty_lists(self):
        """Test SynthesizeOutput accepts empty lists with defaults."""
        output = SynthesizeOutput(updated_todos=[])

        assert output.updated_todos == []
        # findings has default_factory=list, so empty list is accepted
        assert output.findings == []

    def test_synthesize_output_rejects_extra_fields(self):
        """Test SynthesizeOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            SynthesizeOutput(findings=[], updated_todos=[], unknown_field="should be rejected")

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_synthesize_output_schema_returns_string(self):
        """Test get_synthesize_output_schema returns a valid string."""
        schema = get_synthesize_output_schema()

        assert isinstance(schema, str)
        assert "SynthesizeOutput" in schema
        assert "findings" in schema
        assert "category" in schema
        assert "CRITICAL RULES" in schema


class TestBudgetConsumed:
    """Test BudgetConsumed Pydantic model."""

    def test_budget_consumed_valid_with_all_fields(self):
        """Test BudgetConsumed with all fields provided."""
        budget = BudgetConsumed(
            iterations=5,
            subagent_calls=8,
            wall_time_seconds=120.0,
            tool_calls=15,
            tokens_consumed=6000,
        )

        assert budget.iterations == 5
        assert budget.subagent_calls == 8
        assert budget.wall_time_seconds == 120.0
        assert budget.tool_calls == 15
        assert budget.tokens_consumed == 6000

    def test_budget_consumed_valid_with_minimal_fields(self):
        """Test BudgetConsumed with only default values."""
        budget = BudgetConsumed()

        assert budget.iterations == 0
        assert budget.subagent_calls == 0
        assert budget.wall_time_seconds == 0.0
        assert budget.tool_calls == 0
        assert budget.tokens_consumed == 0

    def test_budget_consumed_rejects_extra_fields(self):
        """Test BudgetConsumed with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            BudgetConsumed(unknown_field="should be rejected")

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)


class TestCheckOutput:
    """Test CheckOutput Pydantic model."""

    def test_check_output_valid_with_all_fields(self):
        """Test CheckOutput with all fields provided."""
        budget = BudgetConsumed(iterations=4, subagent_calls=6)

        output = CheckOutput(
            current_todo_id="todo-1",
            todo_complete=True,
            next_phase="reason",
            confidence=0.85,
            budget_consumed=budget,
            blocking_question="",
            novelty_detected=False,
            stagnation_detected=False,
            reasoning="Task completed successfully",
            completed_todo_ids=["todo-1"],
        )

        assert output.current_todo_id == "todo-1"
        assert output.todo_complete is True
        assert output.next_phase == "reason"
        assert output.confidence == 0.85
        assert output.budget_consumed.iterations == 4
        assert output.completed_todo_ids == ["todo-1"]

    def test_check_output_valid_with_minimal_fields(self):
        """Test CheckOutput with only required field."""
        output = CheckOutput()

        assert output.current_todo_id == ""
        assert output.todo_complete is False
        assert output.next_phase == "act"
        assert output.confidence == 0.5
        assert output.budget_consumed.iterations == 0

    def test_check_output_invalid_next_phase(self):
        """Test CheckOutput rejects invalid next_phase value."""
        with pytest.raises(ValidationError) as exc_info:
            CheckOutput(
                next_phase="invalid_phase",
            )

        errors = exc_info.value.errors()
        assert any("next_phase" in error["loc"] for error in errors)

    def test_check_output_confidence_out_of_range(self):
        """Test CheckOutput rejects confidence outside 0.0-1.0 range."""
        with pytest.raises(ValueError) as exc_info:
            CheckOutput(
                confidence=1.5,
            )

        assert "confidence must be between 0.0 and 1.0" in str(exc_info.value)

    def test_check_output_all_valid_next_phases(self):
        """Test CheckOutput accepts all valid next_phase values."""
        valid_phases = ["act", "plan", "reason", "done"]

        for phase in valid_phases:
            output = CheckOutput(next_phase=phase)
            assert output.next_phase == phase

    def test_check_output_completed_todo_ids(self):
        """Test CheckOutput accepts completed_todo_ids."""
        output = CheckOutput(
            todo_complete=True,
            completed_todo_ids=["todo-1", "todo-2"],
        )

        assert output.todo_complete is True
        assert output.completed_todo_ids == ["todo-1", "todo-2"]

    def test_check_output_rejects_extra_fields(self):
        """Test CheckOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            CheckOutput(
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_check_output_schema_returns_string(self):
        """Test get_check_output_schema returns a valid string."""
        schema = get_check_output_schema()

        assert isinstance(schema, str)
        assert "CheckOutput" in schema
        assert "current_todo_id" in schema
        assert "next_phase" in schema
        assert "CRITICAL RULES" in schema

    def test_get_check_output_schema_includes_routing_logic(self):
        """Test get_check_output_schema includes routing logic."""
        schema = get_check_output_schema()

        assert "next_phase" in schema
        assert "todo_complete" in schema
        assert "completed_todo_ids" in schema
