"""Tests for policy engine contracts.

This module tests the typed models for the pluggable policy engine,
ensuring strict validation and correct behavior of all contract types.

Test categories:
- RiskLevel enum validation
- Action variant creation and validation
- ContextRequest and TodoCompletionClaim validation
- PolicyInput creation and factory methods
- StepProposal validation and helper methods
- Strict schema validation (extra="forbid")
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_level_values(self):
        """RiskLevel has LOW, MED, HIGH values."""
        from dawn_kestrel.policy.contracts import RiskLevel

        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MED.value == "MED"
        assert RiskLevel.HIGH.value == "HIGH"

    def test_risk_level_is_str_enum(self):
        """RiskLevel is a StrEnum."""
        from dawn_kestrel.policy.contracts import RiskLevel

        assert isinstance(RiskLevel.LOW, str)
        assert RiskLevel.LOW == "LOW"

    def test_risk_level_from_string(self):
        """RiskLevel can be created from string."""
        from dawn_kestrel.policy.contracts import RiskLevel

        assert RiskLevel("LOW") == RiskLevel.LOW
        assert RiskLevel("MED") == RiskLevel.MED
        assert RiskLevel("HIGH") == RiskLevel.HIGH


class TestReadFileAction:
    """Test ReadFileAction model."""

    def test_read_file_action_minimal(self):
        """ReadFileAction with minimal required fields."""
        from dawn_kestrel.policy.contracts import ReadFileAction

        action = ReadFileAction(path="test.py")
        assert action.action_type == "READ_FILE"
        assert action.path == "test.py"
        assert action.offset is None
        assert action.limit is None

    def test_read_file_action_full(self):
        """ReadFileAction with all fields."""
        from dawn_kestrel.policy.contracts import ReadFileAction

        action = ReadFileAction(path="test.py", offset=10, limit=100)
        assert action.path == "test.py"
        assert action.offset == 10
        assert action.limit == 100

    def test_read_file_action_rejects_extra_fields(self):
        """ReadFileAction rejects extra fields."""
        from dawn_kestrel.policy.contracts import ReadFileAction

        with pytest.raises(ValidationError) as exc_info:
            ReadFileAction(path="test.py", extra_field="not_allowed")

        assert "extra" in str(exc_info.value).lower()


class TestSearchRepoAction:
    """Test SearchRepoAction model."""

    def test_search_repo_action_minimal(self):
        """SearchRepoAction with minimal required fields."""
        from dawn_kestrel.policy.contracts import SearchRepoAction

        action = SearchRepoAction(pattern="TODO")
        assert action.action_type == "SEARCH_REPO"
        assert action.pattern == "TODO"
        assert action.file_pattern is None
        assert action.max_results == 100

    def test_search_repo_action_full(self):
        """SearchRepoAction with all fields."""
        from dawn_kestrel.policy.contracts import SearchRepoAction

        action = SearchRepoAction(pattern="TODO", file_pattern="*.py", max_results=50)
        assert action.pattern == "TODO"
        assert action.file_pattern == "*.py"
        assert action.max_results == 50

    def test_search_repo_action_rejects_extra_fields(self):
        """SearchRepoAction rejects extra fields."""
        from dawn_kestrel.policy.contracts import SearchRepoAction

        with pytest.raises(ValidationError) as exc_info:
            SearchRepoAction(pattern="test", unknown="field")

        assert "extra" in str(exc_info.value).lower()


class TestEditFileAction:
    """Test EditFileAction model."""

    def test_edit_file_action_minimal(self):
        """EditFileAction with minimal required fields."""
        from dawn_kestrel.policy.contracts import EditFileAction

        action = EditFileAction(path="test.py")
        assert action.action_type == "EDIT_FILE"
        assert action.path == "test.py"
        assert action.operation == "replace"

    def test_edit_file_action_with_content(self):
        """EditFileAction with content."""
        from dawn_kestrel.policy.contracts import EditFileAction

        action = EditFileAction(
            path="test.py",
            operation="replace",
            content="new content",
            line_start=1,
            line_end=10,
        )
        assert action.content == "new content"
        assert action.line_start == 1
        assert action.line_end == 10

    def test_edit_file_action_operations(self):
        """EditFileAction accepts valid operations."""
        from dawn_kestrel.policy.contracts import EditFileAction

        for op in ["replace", "insert", "append", "delete"]:
            action = EditFileAction(path="test.py", operation=op)
            assert action.operation == op

    def test_edit_file_action_rejects_invalid_operation(self):
        """EditFileAction rejects invalid operation."""
        from dawn_kestrel.policy.contracts import EditFileAction

        with pytest.raises(ValidationError):
            EditFileAction(path="test.py", operation="invalid_op")

    def test_edit_file_action_rejects_extra_fields(self):
        """EditFileAction rejects extra fields."""
        from dawn_kestrel.policy.contracts import EditFileAction

        with pytest.raises(ValidationError) as exc_info:
            EditFileAction(path="test.py", extra="not_allowed")

        assert "extra" in str(exc_info.value).lower()


class TestRunTestsAction:
    """Test RunTestsAction model."""

    def test_run_tests_action_minimal(self):
        """RunTestsAction with minimal required fields."""
        from dawn_kestrel.policy.contracts import RunTestsAction

        action = RunTestsAction(test_path="tests/")
        assert action.action_type == "RUN_TESTS"
        assert action.test_path == "tests/"
        assert action.filter_pattern is None
        assert action.extra_args == []

    def test_run_tests_action_full(self):
        """RunTestsAction with all fields."""
        from dawn_kestrel.policy.contracts import RunTestsAction

        action = RunTestsAction(
            test_path="tests/test_main.py",
            filter_pattern="test_login",
            extra_args=["-v", "--tb=short"],
        )
        assert action.test_path == "tests/test_main.py"
        assert action.filter_pattern == "test_login"
        assert action.extra_args == ["-v", "--tb=short"]


class TestUpsertTodosAction:
    """Test UpsertTodosAction model."""

    def test_upsert_todos_action_empty(self):
        """UpsertTodosAction can be empty."""
        from dawn_kestrel.policy.contracts import UpsertTodosAction

        action = UpsertTodosAction()
        assert action.action_type == "UPSERT_TODOS"
        assert action.todos == []
        assert action.delete_ids == []

    def test_upsert_todos_action_with_todos(self):
        """UpsertTodosAction with todos."""
        from dawn_kestrel.policy.contracts import UpsertTodosAction

        action = UpsertTodosAction(
            todos=[{"id": "1", "description": "Task 1"}],
            delete_ids=["2", "3"],
        )
        assert len(action.todos) == 1
        assert action.delete_ids == ["2", "3"]


class TestRequestApprovalAction:
    """Test RequestApprovalAction model."""

    def test_request_approval_action_minimal(self):
        """RequestApprovalAction with minimal required fields."""
        from dawn_kestrel.policy.contracts import RequestApprovalAction

        action = RequestApprovalAction(message="Approve this action?")
        assert action.action_type == "REQUEST_APPROVAL"
        assert action.message == "Approve this action?"
        assert action.options == ["approve", "reject"]
        assert action.timeout_seconds is None

    def test_request_approval_action_full(self):
        """RequestApprovalAction with all fields."""
        from dawn_kestrel.policy.contracts import RequestApprovalAction

        action = RequestApprovalAction(
            message="Choose an option",
            options=["yes", "no", "maybe"],
            timeout_seconds=30.0,
        )
        assert action.message == "Choose an option"
        assert action.options == ["yes", "no", "maybe"]
        assert action.timeout_seconds == 30.0


class TestSummarizeAction:
    """Test SummarizeAction model."""

    def test_summarize_action_minimal(self):
        """SummarizeAction with minimal required fields."""
        from dawn_kestrel.policy.contracts import SummarizeAction

        action = SummarizeAction(content="Long text to summarize...")
        assert action.action_type == "SUMMARIZE"
        assert action.content == "Long text to summarize..."
        assert action.max_length == 500
        assert action.focus_areas == []

    def test_summarize_action_full(self):
        """SummarizeAction with all fields."""
        from dawn_kestrel.policy.contracts import SummarizeAction

        action = SummarizeAction(
            content="Long text...",
            max_length=200,
            focus_areas=["security", "performance"],
        )
        assert action.max_length == 200
        assert action.focus_areas == ["security", "performance"]


class TestContextRequest:
    """Test ContextRequest model."""

    def test_context_request_minimal(self):
        """ContextRequest with minimal required fields."""
        from dawn_kestrel.policy.contracts import ContextRequest

        request = ContextRequest(request_type="file", query="auth.py")
        assert request.request_type == "file"
        assert request.query == "auth.py"
        assert request.scope == []
        assert request.priority == "medium"
        assert request.rationale == ""

    def test_context_request_full(self):
        """ContextRequest with all fields."""
        from dawn_kestrel.policy.contracts import ContextRequest

        request = ContextRequest(
            request_type="symbol",
            query="authenticate",
            scope=["auth/", "api/"],
            priority="high",
            rationale="Need to understand auth flow",
        )
        assert request.request_type == "symbol"
        assert request.scope == ["auth/", "api/"]
        assert request.priority == "high"

    def test_context_request_types(self):
        """ContextRequest accepts valid request types."""
        from dawn_kestrel.policy.contracts import ContextRequest

        for rt in ["file", "symbol", "search", "dependency", "history", "custom"]:
            request = ContextRequest(request_type=rt, query="test")
            assert request.request_type == rt

    def test_context_request_rejects_invalid_type(self):
        """ContextRequest rejects invalid request type."""
        from dawn_kestrel.policy.contracts import ContextRequest

        with pytest.raises(ValidationError):
            ContextRequest(request_type="invalid", query="test")

    def test_context_request_rejects_extra_fields(self):
        """ContextRequest rejects extra fields."""
        from dawn_kestrel.policy.contracts import ContextRequest

        with pytest.raises(ValidationError) as exc_info:
            ContextRequest(request_type="file", query="test", extra="not_allowed")

        assert "extra" in str(exc_info.value).lower()


class TestTodoCompletionClaim:
    """Test TodoCompletionClaim model."""

    def test_todo_completion_claim_minimal(self):
        """TodoCompletionClaim with minimal required fields."""
        from dawn_kestrel.policy.contracts import TodoCompletionClaim

        claim = TodoCompletionClaim(
            todo_id="todo-1",
            evidence_type="file_modified",
            evidence_summary="Modified auth.py to add login",
        )
        assert claim.todo_id == "todo-1"
        assert claim.evidence_type == "file_modified"
        assert claim.evidence_summary == "Modified auth.py to add login"
        assert claim.evidence_refs == []
        assert claim.confidence == 1.0

    def test_todo_completion_claim_full(self):
        """TodoCompletionClaim with all fields."""
        from dawn_kestrel.policy.contracts import TodoCompletionClaim

        claim = TodoCompletionClaim(
            todo_id="todo-1",
            evidence_type="test_passed",
            evidence_summary="All tests pass",
            evidence_refs=["tests/test_auth.py:45", "tests/test_auth.py:67"],
            confidence=0.95,
            verification_hints="Run pytest tests/test_auth.py",
        )
        assert claim.evidence_refs == ["tests/test_auth.py:45", "tests/test_auth.py:67"]
        assert claim.confidence == 0.95

    def test_todo_completion_claim_confidence_range(self):
        """TodoCompletionClaim validates confidence range."""
        from dawn_kestrel.policy.contracts import TodoCompletionClaim

        # Valid range
        claim = TodoCompletionClaim(
            todo_id="t1",
            evidence_type="file_modified",
            evidence_summary="test",
            confidence=0.5,
        )
        assert claim.confidence == 0.5

        # Below range
        with pytest.raises(ValidationError):
            TodoCompletionClaim(
                todo_id="t1",
                evidence_type="file_modified",
                evidence_summary="test",
                confidence=-0.1,
            )

        # Above range
        with pytest.raises(ValidationError):
            TodoCompletionClaim(
                todo_id="t1",
                evidence_type="file_modified",
                evidence_summary="test",
                confidence=1.1,
            )

    def test_todo_completion_claim_evidence_types(self):
        """TodoCompletionClaim accepts valid evidence types."""
        from dawn_kestrel.policy.contracts import TodoCompletionClaim

        for et in [
            "file_modified",
            "test_passed",
            "build_succeeded",
            "manual_review",
            "inference",
            "other",
        ]:
            claim = TodoCompletionClaim(
                todo_id="t1",
                evidence_type=et,
                evidence_summary="test",
            )
            assert claim.evidence_type == et

    def test_todo_completion_claim_rejects_extra_fields(self):
        """TodoCompletionClaim rejects extra fields."""
        from dawn_kestrel.policy.contracts import TodoCompletionClaim

        with pytest.raises(ValidationError) as exc_info:
            TodoCompletionClaim(
                todo_id="t1",
                evidence_type="file_modified",
                evidence_summary="test",
                unknown="field",
            )

        assert "extra" in str(exc_info.value).lower()


class TestTodoItem:
    """Test TodoItem model."""

    def test_todo_item_minimal(self):
        """TodoItem with minimal required fields."""
        from dawn_kestrel.policy.contracts import TodoItem

        todo = TodoItem(id="todo-1", description="Implement feature X")
        assert todo.id == "todo-1"
        assert todo.description == "Implement feature X"
        assert todo.status == "pending"
        assert todo.priority == "medium"
        assert todo.dependencies == []

    def test_todo_item_full(self):
        """TodoItem with all fields."""
        from dawn_kestrel.policy.contracts import TodoItem

        todo = TodoItem(
            id="todo-1",
            description="Implement feature X",
            status="in_progress",
            priority="high",
            dependencies=["todo-0"],
        )
        assert todo.status == "in_progress"
        assert todo.priority == "high"
        assert todo.dependencies == ["todo-0"]

    def test_todo_item_statuses(self):
        """TodoItem accepts valid statuses."""
        from dawn_kestrel.policy.contracts import TodoItem

        for status in ["pending", "in_progress", "completed", "blocked", "skipped"]:
            todo = TodoItem(id="t1", description="test", status=status)
            assert todo.status == status


class TestEventSummary:
    """Test EventSummary model."""

    def test_event_summary_minimal(self):
        """EventSummary with minimal required fields."""
        from dawn_kestrel.policy.contracts import EventSummary

        event = EventSummary(
            event_type="file_read",
            timestamp="2024-01-01T12:00:00Z",
            summary="Read auth.py",
        )
        assert event.event_type == "file_read"
        assert event.timestamp == "2024-01-01T12:00:00Z"
        assert event.summary == "Read auth.py"
        assert event.outcome == "success"

    def test_event_summary_full(self):
        """EventSummary with all fields."""
        from dawn_kestrel.policy.contracts import EventSummary

        event = EventSummary(
            event_type="tool_call",
            timestamp="2024-01-01T12:00:00Z",
            summary="Executed bash command",
            outcome="failure",
        )
        assert event.outcome == "failure"

    def test_event_summary_outcomes(self):
        """EventSummary accepts valid outcomes."""
        from dawn_kestrel.policy.contracts import EventSummary

        for outcome in ["success", "failure", "pending", "skipped"]:
            event = EventSummary(
                event_type="test",
                timestamp="2024-01-01T00:00:00Z",
                summary="test",
                outcome=outcome,
            )
            assert event.outcome == outcome


class TestBudgetInfo:
    """Test BudgetInfo model."""

    def test_budget_info_defaults(self):
        """BudgetInfo has sensible defaults."""
        from dawn_kestrel.policy.contracts import BudgetInfo

        budget = BudgetInfo()
        assert budget.max_iterations == 100
        assert budget.max_tool_calls == 1000
        assert budget.max_wall_time_seconds == 3600.0
        assert budget.max_subagent_calls == 50
        assert budget.iterations_consumed == 0
        assert budget.tool_calls_consumed == 0
        assert budget.wall_time_consumed == 0.0
        assert budget.subagent_calls_consumed == 0

    def test_budget_info_custom(self):
        """BudgetInfo with custom values."""
        from dawn_kestrel.policy.contracts import BudgetInfo

        budget = BudgetInfo(
            max_iterations=50,
            max_tool_calls=500,
            iterations_consumed=10,
            tool_calls_consumed=100,
        )
        assert budget.max_iterations == 50
        assert budget.max_tool_calls == 500
        assert budget.iterations_consumed == 10
        assert budget.tool_calls_consumed == 100


class TestConstraint:
    """Test Constraint model."""

    def test_constraint_minimal(self):
        """Constraint with minimal required fields."""
        from dawn_kestrel.policy.contracts import Constraint

        constraint = Constraint(
            constraint_type="permission",
            value="read_only",
        )
        assert constraint.constraint_type == "permission"
        assert constraint.value == "read_only"
        assert constraint.description == ""
        assert constraint.severity == "hard"

    def test_constraint_full(self):
        """Constraint with all fields."""
        from dawn_kestrel.policy.contracts import Constraint

        constraint = Constraint(
            constraint_type="file_pattern",
            value="*.py",
            description="Only Python files",
            severity="soft",
        )
        assert constraint.description == "Only Python files"
        assert constraint.severity == "soft"

    def test_constraint_types(self):
        """Constraint accepts valid types."""
        from dawn_kestrel.policy.contracts import Constraint

        for ct in ["permission", "tool_restriction", "file_pattern", "time_limit", "custom"]:
            constraint = Constraint(constraint_type=ct, value="test")
            assert constraint.constraint_type == ct


class TestPolicyInput:
    """Test PolicyInput model."""

    def test_policy_input_minimal(self):
        """PolicyInput with minimal required fields."""
        from dawn_kestrel.policy.contracts import PolicyInput

        policy_input = PolicyInput(goal="Implement authentication")
        assert policy_input.goal == "Implement authentication"
        assert policy_input.active_todos == []
        assert policy_input.last_events == []
        assert policy_input.granted_context == {}
        assert policy_input.budgets is not None
        assert policy_input.constraints == []

    def test_policy_input_full(self):
        """PolicyInput with all fields."""
        from dawn_kestrel.policy.contracts import (
            BudgetInfo,
            Constraint,
            EventSummary,
            PolicyInput,
            TodoItem,
        )

        policy_input = PolicyInput(
            goal="Implement authentication",
            active_todos=[
                TodoItem(id="t1", description="Create login form"),
                TodoItem(id="t2", description="Add password hashing"),
            ],
            last_events=[
                EventSummary(
                    event_type="file_read",
                    timestamp="2024-01-01T00:00:00Z",
                    summary="Read auth.py",
                )
            ],
            granted_context={"files": ["auth.py"]},
            budgets=BudgetInfo(max_iterations=50),
            constraints=[Constraint(constraint_type="permission", value="no_delete")],
        )
        assert len(policy_input.active_todos) == 2
        assert len(policy_input.last_events) == 1
        assert policy_input.granted_context == {"files": ["auth.py"]}
        assert policy_input.budgets.max_iterations == 50
        assert len(policy_input.constraints) == 1

    def test_policy_input_from_trial(self):
        """PolicyInput.from_trial factory method."""
        from dawn_kestrel.policy.contracts import PolicyInput

        # With dict todos
        policy_input = PolicyInput.from_trial(
            goal="Test goal",
            todos=[
                {"id": "1", "description": "Task 1"},
                {"id": "2", "description": "Task 2", "status": "completed"},
            ],
        )
        assert policy_input.goal == "Test goal"
        assert len(policy_input.active_todos) == 2
        assert policy_input.active_todos[0].id == "1"
        assert policy_input.active_todos[1].status == "completed"

    def test_policy_input_from_trial_with_kwargs(self):
        """PolicyInput.from_trial accepts additional kwargs."""
        from dawn_kestrel.policy.contracts import (
            BudgetInfo,
            Constraint,
            PolicyInput,
        )

        policy_input = PolicyInput.from_trial(
            goal="Test",
            todos=[],
            budgets=BudgetInfo(max_iterations=25),
            constraints=[Constraint(constraint_type="custom", value="test")],
        )
        assert policy_input.budgets.max_iterations == 25
        assert len(policy_input.constraints) == 1

    def test_policy_input_rejects_extra_fields(self):
        """PolicyInput rejects extra fields."""
        from dawn_kestrel.policy.contracts import PolicyInput

        with pytest.raises(ValidationError) as exc_info:
            PolicyInput(goal="Test", unknown_field="not_allowed")

        assert "extra" in str(exc_info.value).lower()


class TestStepProposal:
    """Test StepProposal model."""

    def test_step_proposal_minimal(self):
        """StepProposal with minimal required fields."""
        from dawn_kestrel.policy.contracts import RiskLevel, StepProposal

        proposal = StepProposal(intent="Read authentication module")
        assert proposal.intent == "Read authentication module"
        assert proposal.target_todo_ids == []
        assert proposal.requested_context == []
        assert proposal.actions == []
        assert proposal.completion_claims == []
        assert proposal.risk_level == RiskLevel.LOW
        assert proposal.notes == ""

    def test_step_proposal_with_actions(self):
        """StepProposal with actions."""
        from dawn_kestrel.policy.contracts import (
            ReadFileAction,
            RiskLevel,
            StepProposal,
        )

        proposal = StepProposal(
            intent="Read auth module",
            actions=[ReadFileAction(path="auth.py")],
            risk_level=RiskLevel.LOW,
        )
        assert len(proposal.actions) == 1
        assert proposal.actions[0].action_type == "READ_FILE"
        assert proposal.risk_level == RiskLevel.LOW

    def test_step_proposal_with_multiple_actions(self):
        """StepProposal with multiple action types."""
        from dawn_kestrel.policy.contracts import (
            EditFileAction,
            ReadFileAction,
            RunTestsAction,
            StepProposal,
        )

        proposal = StepProposal(
            intent="Fix bug and test",
            actions=[
                ReadFileAction(path="buggy.py"),
                EditFileAction(path="buggy.py", content="fix"),
                RunTestsAction(test_path="tests/"),
            ],
        )
        assert len(proposal.actions) == 3

    def test_step_proposal_with_completion_claims(self):
        """StepProposal with completion claims."""
        from dawn_kestrel.policy.contracts import (
            StepProposal,
            TodoCompletionClaim,
        )

        proposal = StepProposal(
            intent="Complete authentication",
            completion_claims=[
                TodoCompletionClaim(
                    todo_id="t1",
                    evidence_type="file_modified",
                    evidence_summary="Added login function",
                )
            ],
        )
        assert len(proposal.completion_claims) == 1
        assert proposal.completion_claims[0].todo_id == "t1"

    def test_step_proposal_get_action_types(self):
        """StepProposal.get_action_types returns action types."""
        from dawn_kestrel.policy.contracts import (
            ReadFileAction,
            RunTestsAction,
            SearchRepoAction,
            StepProposal,
        )

        proposal = StepProposal(
            intent="Multi-action",
            actions=[
                ReadFileAction(path="a.py"),
                SearchRepoAction(pattern="TODO"),
                RunTestsAction(test_path="tests/"),
            ],
        )
        types = proposal.get_action_types()
        assert types == ["READ_FILE", "SEARCH_REPO", "RUN_TESTS"]

    def test_step_proposal_has_high_risk_actions(self):
        """StepProposal.has_high_risk_actions detects risky actions."""
        from dawn_kestrel.policy.contracts import (
            EditFileAction,
            ReadFileAction,
            RunTestsAction,
            StepProposal,
        )

        # Low risk only
        low_risk = StepProposal(
            intent="Read only",
            actions=[ReadFileAction(path="a.py")],
        )
        assert low_risk.has_high_risk_actions() is False

        # Has high risk
        high_risk = StepProposal(
            intent="Edit and test",
            actions=[
                ReadFileAction(path="a.py"),
                EditFileAction(path="a.py", content="new"),
            ],
        )
        assert high_risk.has_high_risk_actions() is True

        # Run tests is also high risk
        test_risk = StepProposal(
            intent="Run tests",
            actions=[RunTestsAction(test_path="tests/")],
        )
        assert test_risk.has_high_risk_actions() is True

    def test_step_proposal_rejects_extra_fields(self):
        """StepProposal rejects extra fields."""
        from dawn_kestrel.policy.contracts import StepProposal

        with pytest.raises(ValidationError) as exc_info:
            StepProposal(intent="Test", unknown="not_allowed")

        assert "extra" in str(exc_info.value).lower()

    def test_step_proposal_rejects_invalid_risk_level(self):
        """StepProposal rejects invalid risk level."""
        from dawn_kestrel.policy.contracts import StepProposal

        with pytest.raises(ValidationError):
            StepProposal(intent="Test", risk_level="INVALID")


class TestActionDiscrimination:
    """Test action type discrimination."""

    def test_action_union_accepts_all_types(self):
        """Action union accepts all valid action types."""
        from dawn_kestrel.policy.contracts import (
            EditFileAction,
            ReadFileAction,
            RequestApprovalAction,
            RunTestsAction,
            SearchRepoAction,
            StepProposal,
            SummarizeAction,
            UpsertTodosAction,
        )

        # Create proposal with all action types
        proposal = StepProposal(
            intent="All actions",
            actions=[
                ReadFileAction(path="a.py"),
                SearchRepoAction(pattern="TODO"),
                EditFileAction(path="a.py"),
                RunTestsAction(test_path="tests/"),
                UpsertTodosAction(todos=[{"id": "1", "desc": "test"}]),
                RequestApprovalAction(message="OK?"),
                SummarizeAction(content="text"),
            ],
        )
        assert len(proposal.actions) == 7

    def test_action_discrimination_in_actions_list(self):
        """Actions are properly discriminated by action_type."""
        from dawn_kestrel.policy.contracts import (
            EditFileAction,
            ReadFileAction,
            StepProposal,
        )

        proposal = StepProposal(
            intent="Test",
            actions=[
                ReadFileAction(path="read.py"),
                EditFileAction(path="edit.py", content="new"),
            ],
        )

        # Check types are preserved
        assert isinstance(proposal.actions[0], ReadFileAction)
        assert isinstance(proposal.actions[1], EditFileAction)
        assert proposal.actions[0].action_type == "READ_FILE"
        assert proposal.actions[1].action_type == "EDIT_FILE"


class TestPackageExports:
    """Test package-level exports."""

    def test_all_exports_available_from_package(self):
        """All expected types are available from package."""
        from dawn_kestrel.policy import (
            Action,
            BudgetInfo,
            Constraint,
            ContextRequest,
            EditFileAction,
            EventSummary,
            PolicyInput,
            ReadFileAction,
            RequestApprovalAction,
            RiskLevel,
            RunTestsAction,
            SearchRepoAction,
            StepProposal,
            SummarizeAction,
            TodoCompletionClaim,
            TodoItem,
            UpsertTodosAction,
        )

        # Verify they are the correct types
        assert RiskLevel.LOW.value == "LOW"
        assert ReadFileAction(path="test").action_type == "READ_FILE"

    def test_module_exports_match_package(self):
        """Module __all__ matches package __all__."""
        import dawn_kestrel.policy as pkg
        import dawn_kestrel.policy.contracts as contracts

        assert set(contracts.__all__).issubset(set(pkg.__all__))
