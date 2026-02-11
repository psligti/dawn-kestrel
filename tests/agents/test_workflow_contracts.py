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
    IntakeOutput,
    PlanOutput,
    ActOutput,
    SynthesizeOutput,
    CheckOutput,
    TodoItem,
    ToolExecution,
    SynthesizedFinding,
    BudgetConsumed,
    get_intake_output_schema,
    get_plan_output_schema,
    get_act_output_schema,
    get_synthesize_output_schema,
    get_check_output_schema,
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


class TestToolExecution:
    """Test ToolExecution Pydantic model."""

    def test_tool_execution_valid_with_all_fields(self):
        """Test ToolExecution with all fields provided."""
        execution = ToolExecution(
            tool_name="read",
            arguments={"file_path": "test.py"},
            status="success",
            result_summary="Read file successfully",
            duration_seconds=1.5,
            artifacts=["test.py"],
        )

        assert execution.tool_name == "read"
        assert execution.arguments == {"file_path": "test.py"}
        assert execution.status == "success"
        assert execution.duration_seconds == 1.5
        assert execution.artifacts == ["test.py"]

    def test_tool_execution_valid_with_minimal_fields(self):
        """Test ToolExecution with only required fields."""
        execution = ToolExecution(
            tool_name="grep",
            status="success",
        )

        assert execution.tool_name == "grep"
        assert execution.arguments == {}
        assert execution.result_summary == ""
        assert execution.duration_seconds == 0.0
        assert execution.artifacts == []

    def test_tool_execution_invalid_status(self):
        """Test ToolExecution rejects invalid status value."""
        with pytest.raises(ValidationError) as exc_info:
            ToolExecution(
                tool_name="test",
                status="invalid_status",
            )

        errors = exc_info.value.errors()
        assert any("status" in error["loc"] for error in errors)

    def test_tool_execution_rejects_extra_fields(self):
        """Test ToolExecution with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ToolExecution(
                tool_name="test",
                status="success",
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)


class TestActOutput:
    """Test ActOutput Pydantic model."""

    def test_act_output_valid_with_all_fields(self):
        """Test ActOutput with all fields provided."""
        actions = [
            ToolExecution(tool_name="read", status="success"),
            ToolExecution(tool_name="grep", status="failure"),
        ]

        output = ActOutput(
            actions_attempted=actions,
            todos_addressed=["1", "2"],
            tool_results_summary="Test summary",
            artifacts=["file1.py", "file2.py"],
            failures=["Test failure"],
        )

        assert len(output.actions_attempted) == 2
        assert output.todos_addressed == ["1", "2"]
        assert output.tool_results_summary == "Test summary"
        assert output.artifacts == ["file1.py", "file2.py"]
        assert output.failures == ["Test failure"]

    def test_act_output_valid_with_minimal_fields(self):
        """Test ActOutput with only required field."""
        output = ActOutput(actions_attempted=[])

        assert output.actions_attempted == []
        assert output.todos_addressed == []
        assert output.tool_results_summary == ""
        assert output.artifacts == []
        assert output.failures == []

    def test_act_output_accepts_empty_actions_list(self):
        """Test ActOutput accepts empty actions_attempted list with default."""
        output = ActOutput(tool_results_summary="test")

        assert output.tool_results_summary == "test"
        # actions_attempted has default_factory=list, so empty list is accepted
        assert output.actions_attempted == []

    def test_act_output_rejects_extra_fields(self):
        """Test ActOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ActOutput(actions_attempted=[], unknown_field="should be rejected")

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_act_output_schema_returns_string(self):
        """Test get_act_output_schema returns a valid string."""
        schema = get_act_output_schema()

        assert isinstance(schema, str)
        assert "ActOutput" in schema
        assert "actions_attempted" in schema
        assert "tool_name" in schema
        assert "CRITICAL RULES" in schema


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
            should_continue=False,
            stop_reason="recommendation_ready",
            confidence=0.85,
            budget_consumed=budget,
            blocking_question="",
            novelty_detected=False,
            stagnation_detected=False,
            next_action="commit",
        )

        assert output.should_continue is False
        assert output.stop_reason == "recommendation_ready"
        assert output.confidence == 0.85
        assert output.budget_consumed.iterations == 4
        assert output.next_action == "commit"

    def test_check_output_valid_with_minimal_fields(self):
        """Test CheckOutput with only required field."""
        output = CheckOutput(should_continue=True)

        assert output.should_continue is True
        assert output.stop_reason == "none"
        assert output.confidence == 0.5
        assert output.budget_consumed.iterations == 0

    def test_check_output_invalid_stop_reason(self):
        """Test CheckOutput rejects invalid stop_reason value."""
        with pytest.raises(ValidationError) as exc_info:
            CheckOutput(
                should_continue=False,
                stop_reason="invalid_reason",
            )

        errors = exc_info.value.errors()
        assert any("stop_reason" in error["loc"] for error in errors)

    def test_check_output_invalid_next_action(self):
        """Test CheckOutput rejects invalid next_action value."""
        with pytest.raises(ValidationError) as exc_info:
            CheckOutput(
                should_continue=True,
                next_action="invalid_action",
            )

        errors = exc_info.value.errors()
        assert any("next_action" in error["loc"] for error in errors)

    def test_check_output_confidence_out_of_range(self):
        """Test CheckOutput rejects confidence outside 0.0-1.0 range."""
        with pytest.raises(ValueError) as exc_info:
            CheckOutput(
                should_continue=True,
                confidence=1.5,
            )

        assert "confidence must be between 0.0 and 1.0" in str(exc_info.value)

    def test_check_output_all_valid_stop_reasons(self):
        """Test CheckOutput accepts all valid stop_reason values."""
        valid_stop_reasons = [
            "recommendation_ready",
            "blocking_question",
            "budget_exhausted",
            "stagnation",
            "human_required",
            "none",
        ]

        for reason in valid_stop_reasons:
            output = CheckOutput(should_continue=False, stop_reason=reason)
            assert output.stop_reason == reason

    def test_check_output_all_valid_next_actions(self):
        """Test CheckOutput accepts all valid next_action values."""
        valid_actions = ["continue", "switch_strategy", "escalate", "commit", "stop"]

        for action in valid_actions:
            output = CheckOutput(should_continue=True, next_action=action)
            assert output.next_action == action

    def test_check_output_rejects_extra_fields(self):
        """Test CheckOutput with extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            CheckOutput(
                should_continue=True,
                unknown_field="should be rejected",
            )

        errors = exc_info.value.errors()
        assert any("extra_forbidden" in error["type"] for error in errors)

    def test_get_check_output_schema_returns_string(self):
        """Test get_check_output_schema returns a valid string."""
        schema = get_check_output_schema()

        assert isinstance(schema, str)
        assert "CheckOutput" in schema
        assert "should_continue" in schema
        assert "stop_reason" in schema
        assert "CRITICAL RULES" in schema
        assert "STOP REASONS" in schema

    def test_get_check_output_schema_includes_canonical_policy(self):
        """Test get_check_output_schema includes canonical stop/loop policy."""
        schema = get_check_output_schema()

        assert "docs/planning-agent-orchestration.md" in schema
        assert "recommendation_ready" in schema
        assert "blocking_question" in schema
        assert "budget_exhausted" in schema
        assert "stagnation" in schema
        assert "human_required" in schema
