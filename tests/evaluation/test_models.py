"""Comprehensive TDD tests for evaluation models.

Tests for all evaluation model types:
- GraderSpec: type string, custom types, strict validation
- Transcript: embedded messages, defaults, extra fields rejected
- Outcome: success flag, metadata namespacing, defaults
- Task: multi-grader support, custom grader types
- Trial: run_id, attempt, embedded transcript, outcome composition
- Suite: tasks vs task_ids, validator, both supported
- SuiteRun: agent identity, model params, timestamps
"""

import pytest
from pydantic import ValidationError

from dawn_kestrel.core.models import Message
from dawn_kestrel.evaluation.grader_specs import (
    GRADER_TYPE_DETERMINISTIC_TESTS,
    GRADER_TYPE_LLM_RUBRIC,
    GRADER_TYPE_STATIC_ANALYSIS,
    GRADER_TYPE_STATE_CHECK,
    GRADER_TYPE_TOOL_CALLS,
    GRADER_TYPE_TRANSCRIPT,
    GraderSpec,
)
from dawn_kestrel.evaluation.models import (
    Outcome,
    Suite,
    SuiteRun,
    Task,
    Transcript,
    Trial,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_message() -> Message:
    """Create a sample Message for testing."""
    return Message(
        id="msg-1",
        session_id="session-1",
        role="user",
        text="Hello, world!",
    )


@pytest.fixture
def sample_grader_spec() -> GraderSpec:
    """Create a sample GraderSpec for testing."""
    return GraderSpec(
        type=GRADER_TYPE_LLM_RUBRIC,
        name="quality_check",
        config={"threshold": 0.8},
    )


@pytest.fixture
def sample_transcript(sample_message: Message) -> Transcript:
    """Create a sample Transcript for testing."""
    return Transcript(
        id="tr-1",
        session_id="session-1",
        messages=[sample_message],
    )


@pytest.fixture
def sample_outcome() -> Outcome:
    """Create a sample Outcome for testing."""
    return Outcome(
        success=True,
        metadata={"dk.score": 0.95},
    )


@pytest.fixture
def sample_task(sample_grader_spec: GraderSpec) -> Task:
    """Create a sample Task for testing."""
    return Task(
        id="task-1",
        description="Test code generation",
        graders=[sample_grader_spec],
    )


@pytest.fixture
def sample_trial(sample_transcript: Transcript, sample_outcome: Outcome) -> Trial:
    """Create a sample Trial for testing."""
    return Trial(
        id="trial-1",
        task_id="task-1",
        run_id="run-1",
        session_id="session-1",
        transcript=sample_transcript,
        outcome=sample_outcome,
    )


@pytest.fixture
def sample_suite(sample_task: Task) -> Suite:
    """Create a sample Suite for testing."""
    return Suite(
        id="suite-1",
        name="Test Suite",
        tasks=[sample_task],
    )


# ============================================================================
# TestGraderSpec
# ============================================================================


class TestGraderSpec:
    """Tests for GraderSpec model validation."""

    def test_create_with_required_fields(self):
        """Test creating GraderSpec with required fields only."""
        spec = GraderSpec(
            type="custom_grader",
            name="my_grader",
        )
        assert spec.type == "custom_grader"
        assert spec.name == "my_grader"
        assert spec.config == {}

    def test_create_with_all_fields(self):
        """Test creating GraderSpec with all fields."""
        spec = GraderSpec(
            type=GRADER_TYPE_LLM_RUBRIC,
            name="quality_check",
            config={"threshold": 0.8, "rubric": "Is code well-structured?"},
        )
        assert spec.type == GRADER_TYPE_LLM_RUBRIC
        assert spec.name == "quality_check"
        assert spec.config["threshold"] == 0.8
        assert spec.config["rubric"] == "Is code well-structured?"

    def test_well_known_type_constants(self):
        """Test all well-known grader type constants."""
        assert GRADER_TYPE_DETERMINISTIC_TESTS == "deterministic_tests"
        assert GRADER_TYPE_LLM_RUBRIC == "llm_rubric"
        assert GRADER_TYPE_STATIC_ANALYSIS == "static_analysis"
        assert GRADER_TYPE_STATE_CHECK == "state_check"
        assert GRADER_TYPE_TOOL_CALLS == "tool_calls"
        assert GRADER_TYPE_TRANSCRIPT == "transcript"

    def test_custom_grader_types_allowed(self):
        """Test that custom grader types are allowed (extensibility)."""
        custom_types = [
            "my_custom_grader",
            "security_scanner_v2",
            "performance_benchmark",
            "org.internal.QualityGrader",
        ]
        for custom_type in custom_types:
            spec = GraderSpec(type=custom_type, name="custom")
            assert spec.type == custom_type

    def test_extra_fields_forbidden(self):
        """Test GraderSpec rejects extra fields (strict validation)."""
        with pytest.raises(ValidationError, match="extra"):
            GraderSpec(
                type="test",
                name="test",
                unexpected_field="should fail",
            )

    def test_to_dict(self):
        """Test GraderSpec to_dict conversion."""
        spec = GraderSpec(
            type=GRADER_TYPE_LLM_RUBRIC,
            name="quality",
            config={"threshold": 0.9},
        )
        d = spec.to_dict()
        assert d["type"] == GRADER_TYPE_LLM_RUBRIC
        assert d["name"] == "quality"
        assert d["config"]["threshold"] == 0.9

    def test_missing_required_fields(self):
        """Test GraderSpec rejects missing required fields."""
        with pytest.raises(ValidationError):
            GraderSpec()  # type: ignore

        with pytest.raises(ValidationError):
            GraderSpec(type="test")  # type: ignore

        with pytest.raises(ValidationError):
            GraderSpec(name="test")  # type: ignore


# ============================================================================
# TestTranscript
# ============================================================================


class TestTranscript:
    """Tests for Transcript model validation."""

    def test_create_with_required_fields(self, sample_message: Message):
        """Test creating Transcript with required fields."""
        transcript = Transcript(
            id="tr-1",
            session_id="session-1",
            messages=[sample_message],
        )
        assert transcript.id == "tr-1"
        assert transcript.session_id == "session-1"
        assert len(transcript.messages) == 1
        assert transcript.messages[0].id == "msg-1"

    def test_create_with_all_fields(self, sample_message: Message):
        """Test creating Transcript with all fields."""
        transcript = Transcript(
            id="tr-2",
            session_id="session-2",
            messages=[sample_message],
            timing={"total_time": 12.5, "llm_time": 10.0},
        )
        assert transcript.timing["total_time"] == 12.5
        assert transcript.timing["llm_time"] == 10.0

    def test_timing_defaults_to_empty_dict(self, sample_message: Message):
        """Test timing defaults to empty dict."""
        transcript = Transcript(
            id="tr-1",
            session_id="session-1",
            messages=[sample_message],
        )
        assert transcript.timing == {}

    def test_embedded_messages(self, sample_message: Message):
        """Test that messages are embedded directly (not referenced by ID)."""
        transcript = Transcript(
            id="tr-1",
            session_id="session-1",
            messages=[sample_message],
        )
        # Message is the full object, not just an ID reference
        assert isinstance(transcript.messages[0], Message)
        assert transcript.messages[0].text == "Hello, world!"

    def test_empty_messages_list(self):
        """Test Transcript can have empty messages list."""
        transcript = Transcript(
            id="tr-empty",
            session_id="session-1",
            messages=[],
        )
        assert transcript.messages == []

    def test_multiple_messages(self, sample_message: Message):
        """Test Transcript with multiple messages."""
        msg2 = Message(
            id="msg-2",
            session_id="session-1",
            role="assistant",
            text="Hello!",
        )
        transcript = Transcript(
            id="tr-1",
            session_id="session-1",
            messages=[sample_message, msg2],
        )
        assert len(transcript.messages) == 2

    def test_extra_fields_forbidden(self, sample_message: Message):
        """Test Transcript rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Transcript(
                id="tr-1",
                session_id="session-1",
                messages=[sample_message],
                unexpected_field="should fail",
            )

    def test_to_dict(self, sample_message: Message):
        """Test Transcript to_dict conversion."""
        transcript = Transcript(
            id="tr-1",
            session_id="session-1",
            messages=[sample_message],
            timing={"total": 5.0},
        )
        d = transcript.to_dict()
        assert d["id"] == "tr-1"
        assert d["session_id"] == "session-1"
        assert len(d["messages"]) == 1
        assert d["timing"]["total"] == 5.0


# ============================================================================
# TestOutcome
# ============================================================================


class TestOutcome:
    """Tests for Outcome model validation."""

    def test_create_with_success_only(self):
        """Test creating Outcome with success flag only."""
        outcome = Outcome(success=True)
        assert outcome.success is True
        assert outcome.metadata == {}
        assert outcome.error is None
        assert outcome.artifacts == []

    def test_create_with_all_fields(self):
        """Test creating Outcome with all fields."""
        outcome = Outcome(
            success=False,
            metadata={"dk.score": 0.45, "dk.reason": "threshold_not_met"},
            error="Test execution failed",
            artifacts=["artifact1.json", "artifact2.log"],
        )
        assert outcome.success is False
        assert outcome.metadata["dk.score"] == 0.45
        assert outcome.error == "Test execution failed"
        assert len(outcome.artifacts) == 2

    def test_metadata_namespacing_convention(self):
        """Test metadata namespacing convention (dk.* for SDK, ash_hawk.* for harness)."""
        outcome = Outcome(
            success=True,
            metadata={
                "dk.score": 0.95,
                "dk.model": "claude-3-opus",
                "ash_hawk.harness_version": "2.0.0",
                "ash_hawk.run_id": "run-123",
            },
        )
        assert outcome.metadata["dk.score"] == 0.95
        assert outcome.metadata["ash_hawk.harness_version"] == "2.0.0"

    def test_success_true(self):
        """Test Outcome with success=True."""
        outcome = Outcome(success=True)
        assert outcome.success is True

    def test_success_false(self):
        """Test Outcome with success=False."""
        outcome = Outcome(success=False)
        assert outcome.success is False

    def test_defaults(self):
        """Test all defaults for Outcome."""
        outcome = Outcome(success=True)
        assert outcome.metadata == {}
        assert outcome.error is None
        assert outcome.artifacts == []

    def test_extra_fields_forbidden(self):
        """Test Outcome rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Outcome(
                success=True,
                unexpected_field="should fail",
            )

    def test_to_dict(self):
        """Test Outcome to_dict conversion."""
        outcome = Outcome(
            success=True,
            metadata={"dk.score": 0.9},
            artifacts=["result.json"],
        )
        d = outcome.to_dict()
        assert d["success"] is True
        assert d["metadata"]["dk.score"] == 0.9
        assert d["artifacts"] == ["result.json"]

    def test_error_field(self):
        """Test Outcome with error message."""
        outcome = Outcome(
            success=False,
            error="Connection timeout after 30s",
        )
        assert outcome.error == "Connection timeout after 30s"


# ============================================================================
# TestTask
# ============================================================================


class TestTask:
    """Tests for Task model validation."""

    def test_create_with_required_fields(self):
        """Test creating Task with required fields only."""
        task = Task(
            id="task-1",
            description="Test task description",
        )
        assert task.id == "task-1"
        assert task.description == "Test task description"
        assert task.graders == []
        assert task.inputs == {}
        assert task.tracked_metrics == []
        assert task.tags == []

    def test_create_with_all_fields(self, sample_grader_spec: GraderSpec):
        """Test creating Task with all fields."""
        task = Task(
            id="task-2",
            description="Full task with all options",
            graders=[sample_grader_spec],
            inputs={"prompt": "Write a function", "language": "python"},
            tracked_metrics=["latency", "token_count"],
            tags=["code-gen", "python", "production"],
        )
        assert len(task.graders) == 1
        assert task.inputs["prompt"] == "Write a function"
        assert len(task.tracked_metrics) == 2
        assert len(task.tags) == 3

    def test_multi_grader_support(self):
        """Test Task with multiple graders."""
        graders = [
            GraderSpec(type=GRADER_TYPE_DETERMINISTIC_TESTS, name="unit_tests"),
            GraderSpec(type=GRADER_TYPE_LLM_RUBRIC, name="quality"),
            GraderSpec(type=GRADER_TYPE_STATIC_ANALYSIS, name="security"),
        ]
        task = Task(
            id="task-multi",
            description="Multi-grader task",
            graders=graders,
        )
        assert len(task.graders) == 3
        assert task.graders[0].type == GRADER_TYPE_DETERMINISTIC_TESTS
        assert task.graders[1].type == GRADER_TYPE_LLM_RUBRIC
        assert task.graders[2].type == GRADER_TYPE_STATIC_ANALYSIS

    def test_custom_grader_types(self):
        """Test Task with custom grader types."""
        task = Task(
            id="task-custom",
            description="Task with custom grader",
            graders=[
                GraderSpec(type="org.custom.PerformanceGrader", name="perf"),
            ],
        )
        assert task.graders[0].type == "org.custom.PerformanceGrader"

    def test_extra_fields_forbidden(self):
        """Test Task rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Task(
                id="task-1",
                description="test",
                unexpected_field="should fail",
            )

    def test_to_dict(self, sample_grader_spec: GraderSpec):
        """Test Task to_dict conversion."""
        task = Task(
            id="task-1",
            description="Test task",
            graders=[sample_grader_spec],
            tags=["test"],
        )
        d = task.to_dict()
        assert d["id"] == "task-1"
        assert d["description"] == "Test task"
        assert len(d["graders"]) == 1
        assert d["tags"] == ["test"]

    def test_missing_required_fields(self):
        """Test Task rejects missing required fields."""
        with pytest.raises(ValidationError):
            Task()  # type: ignore

        with pytest.raises(ValidationError):
            Task(id="task-1")  # type: ignore

        with pytest.raises(ValidationError):
            Task(description="test")  # type: ignore


# ============================================================================
# TestTrial
# ============================================================================


class TestTrial:
    """Tests for Trial model validation."""

    def test_create_with_required_fields(self):
        """Test creating Trial with required fields only."""
        trial = Trial(
            id="trial-1",
            task_id="task-1",
            run_id="run-1",
            session_id="session-1",
        )
        assert trial.id == "trial-1"
        assert trial.task_id == "task-1"
        assert trial.run_id == "run-1"
        assert trial.session_id == "session-1"
        assert trial.attempt == 1
        assert trial.transcript is None
        assert trial.outcome is None
        assert trial.metrics == {}

    def test_create_with_all_fields(
        self,
        sample_transcript: Transcript,
        sample_outcome: Outcome,
    ):
        """Test creating Trial with all fields."""
        trial = Trial(
            id="trial-2",
            task_id="task-1",
            run_id="run-1",
            attempt=3,
            session_id="session-1",
            transcript=sample_transcript,
            outcome=sample_outcome,
            metrics={"latency_ms": 1500, "tokens_used": 500},
        )
        assert trial.attempt == 3
        assert trial.transcript is not None
        assert trial.outcome is not None
        assert trial.metrics["latency_ms"] == 1500

    def test_attempt_defaults_to_one(self):
        """Test attempt defaults to 1."""
        trial = Trial(
            id="trial-1",
            task_id="task-1",
            run_id="run-1",
            session_id="session-1",
        )
        assert trial.attempt == 1

    def test_run_id_groups_trials(self):
        """Test run_id groups trials across model/policy comparisons."""
        # Multiple trials in the same run
        trial1 = Trial(
            id="trial-1",
            task_id="task-1",
            run_id="run-comparison-1",
            session_id="session-1",
        )
        trial2 = Trial(
            id="trial-2",
            task_id="task-1",
            run_id="run-comparison-1",
            session_id="session-2",
        )
        trial3 = Trial(
            id="trial-3",
            task_id="task-1",
            run_id="run-comparison-2",
            session_id="session-3",
        )
        assert trial1.run_id == trial2.run_id
        assert trial1.run_id != trial3.run_id

    def test_embedded_transcript_composition(self, sample_transcript: Transcript):
        """Test Trial with embedded Transcript."""
        trial = Trial(
            id="trial-1",
            task_id="task-1",
            run_id="run-1",
            session_id="session-1",
            transcript=sample_transcript,
        )
        assert trial.transcript is not None
        assert trial.transcript.id == "tr-1"
        assert len(trial.transcript.messages) == 1

    def test_outcome_composition(self, sample_outcome: Outcome):
        """Test Trial with Outcome composition."""
        trial = Trial(
            id="trial-1",
            task_id="task-1",
            run_id="run-1",
            session_id="session-1",
            outcome=sample_outcome,
        )
        assert trial.outcome is not None
        assert trial.outcome.success is True

    def test_extra_fields_forbidden(self):
        """Test Trial rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Trial(
                id="trial-1",
                task_id="task-1",
                run_id="run-1",
                session_id="session-1",
                unexpected_field="should fail",
            )

    def test_to_dict(self, sample_transcript: Transcript, sample_outcome: Outcome):
        """Test Trial to_dict conversion."""
        trial = Trial(
            id="trial-1",
            task_id="task-1",
            run_id="run-1",
            session_id="session-1",
            transcript=sample_transcript,
            outcome=sample_outcome,
            metrics={"score": 0.9},
        )
        d = trial.to_dict()
        assert d["id"] == "trial-1"
        assert d["task_id"] == "task-1"
        assert d["run_id"] == "run-1"
        assert d["transcript"]["id"] == "tr-1"
        assert d["outcome"]["success"] is True
        assert d["metrics"]["score"] == 0.9


# ============================================================================
# TestSuite
# ============================================================================


class TestSuite:
    """Tests for Suite model validation."""

    def test_create_with_tasks(self, sample_task: Task):
        """Test creating Suite with embedded tasks."""
        suite = Suite(
            id="suite-1",
            name="Test Suite",
            tasks=[sample_task],
        )
        assert suite.id == "suite-1"
        assert suite.name == "Test Suite"
        assert len(suite.tasks) == 1
        assert suite.tasks[0].id == "task-1"
        assert suite.task_ids == []

    def test_create_with_task_ids(self):
        """Test creating Suite with task_ids (references)."""
        suite = Suite(
            id="suite-2",
            name="Reference Suite",
            task_ids=["task-1", "task-2", "task-3"],
        )
        assert suite.task_ids == ["task-1", "task-2", "task-3"]
        assert suite.tasks == []

    def test_create_with_both_tasks_and_ids(self, sample_task: Task):
        """Test Suite supports both tasks and task_ids."""
        suite = Suite(
            id="suite-3",
            name="Mixed Suite",
            tasks=[sample_task],
            task_ids=["task-external-1"],
        )
        assert len(suite.tasks) == 1
        assert len(suite.task_ids) == 1

    def test_validator_rejects_empty(self):
        """Test Suite validator rejects empty (neither tasks nor task_ids)."""
        with pytest.raises(ValidationError, match="at least one"):
            Suite(
                id="suite-empty",
                name="Empty Suite",
            )

    def test_create_with_all_fields(self, sample_task: Task):
        """Test creating Suite with all fields."""
        suite = Suite(
            id="suite-full",
            name="Full Suite",
            description="Comprehensive test suite",
            tasks=[sample_task],
            version="2.1.0",
            tags=["integration", "production"],
        )
        assert suite.description == "Comprehensive test suite"
        assert suite.version == "2.1.0"
        assert suite.tags == ["integration", "production"]

    def test_defaults(self):
        """Test Suite defaults."""
        suite = Suite(
            id="suite-1",
            name="Test",
            task_ids=["t1"],
        )
        assert suite.description is None
        assert suite.tasks == []
        assert suite.version == "1.0.0"
        assert suite.tags == []

    def test_extra_fields_forbidden(self, sample_task: Task):
        """Test Suite rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Suite(
                id="suite-1",
                name="Test",
                tasks=[sample_task],
                unexpected_field="should fail",
            )

    def test_to_dict(self, sample_task: Task):
        """Test Suite to_dict conversion."""
        suite = Suite(
            id="suite-1",
            name="Test Suite",
            tasks=[sample_task],
            version="1.5.0",
        )
        d = suite.to_dict()
        assert d["id"] == "suite-1"
        assert d["name"] == "Test Suite"
        assert len(d["tasks"]) == 1
        assert d["version"] == "1.5.0"

    def test_portable_with_embedded_tasks(self, sample_task: Task):
        """Test Suite is portable with embedded tasks."""
        suite = Suite(
            id="suite-portable",
            name="Portable Suite",
            tasks=[sample_task],
        )
        # Suite is self-contained
        assert len(suite.tasks) == 1
        assert suite.tasks[0].description == "Test code generation"

    def test_lightweight_with_task_ids(self):
        """Test Suite is lightweight with task_ids references."""
        suite = Suite(
            id="suite-lightweight",
            name="Lightweight Suite",
            task_ids=["external-task-1", "external-task-2"],
        )
        # Suite references external tasks
        assert suite.task_ids == ["external-task-1", "external-task-2"]


# ============================================================================
# TestSuiteRun
# ============================================================================


class TestSuiteRun:
    """Tests for SuiteRun model validation."""

    def test_create_with_required_fields(self):
        """Test creating SuiteRun with required fields only."""
        run = SuiteRun(
            id="run-1",
            suite_id="suite-1",
        )
        assert run.id == "run-1"
        assert run.suite_id == "suite-1"
        assert run.agent_identity is None
        assert run.model_params == {}
        assert run.tool_policy == {}
        assert run.config_snapshot == {}
        assert run.started_at is None
        assert run.ended_at is None

    def test_create_with_all_fields(self):
        """Test creating SuiteRun with all fields."""
        run = SuiteRun(
            id="run-2",
            suite_id="suite-1",
            agent_identity="claude-3-opus",
            model_params={"temperature": 0.7, "max_tokens": 4096},
            tool_policy={"allowlist": ["read", "write"], "denylist": ["bash"]},
            config_snapshot={"retry_enabled": True, "timeout_seconds": 300},
            started_at="2024-01-15T10:30:00Z",
            ended_at="2024-01-15T11:45:00Z",
        )
        assert run.agent_identity == "claude-3-opus"
        assert run.model_params["temperature"] == 0.7
        assert run.tool_policy["allowlist"] == ["read", "write"]
        assert run.config_snapshot["retry_enabled"] is True
        assert run.started_at == "2024-01-15T10:30:00Z"
        assert run.ended_at == "2024-01-15T11:45:00Z"

    def test_agent_identity(self):
        """Test SuiteRun agent identity field."""
        identities = [
            "claude-3-opus",
            "gpt-4-turbo",
            "gemini-pro",
            "custom-agent-v2",
        ]
        for identity in identities:
            run = SuiteRun(
                id=f"run-{identity}",
                suite_id="suite-1",
                agent_identity=identity,
            )
            assert run.agent_identity == identity

    def test_model_params_snapshot(self):
        """Test SuiteRun model_params captures model configuration."""
        run = SuiteRun(
            id="run-1",
            suite_id="suite-1",
            model_params={
                "temperature": 0.5,
                "max_tokens": 2048,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
            },
        )
        assert run.model_params["temperature"] == 0.5
        assert run.model_params["max_tokens"] == 2048

    def test_tool_policy_snapshot(self):
        """Test SuiteRun tool_policy captures tool configuration."""
        run = SuiteRun(
            id="run-1",
            suite_id="suite-1",
            tool_policy={
                "mode": "allowlist",
                "tools": ["read", "glob", "grep"],
                "requires_confirmation": ["write", "edit"],
            },
        )
        assert run.tool_policy["mode"] == "allowlist"
        assert "write" in run.tool_policy["requires_confirmation"]

    def test_timestamps(self):
        """Test SuiteRun timestamps in ISO format."""
        run = SuiteRun(
            id="run-1",
            suite_id="suite-1",
            started_at="2024-01-15T10:30:00.123Z",
            ended_at="2024-01-15T10:45:30.456Z",
        )
        assert run.started_at == "2024-01-15T10:30:00.123Z"
        assert run.ended_at == "2024-01-15T10:45:30.456Z"

    def test_id_matches_run_id_convention(self):
        """Test SuiteRun.id is the run_id used in Trial."""
        run = SuiteRun(
            id="run-comparison-1",
            suite_id="suite-1",
        )
        # This id should match the run_id used in Trial for grouping
        assert run.id == "run-comparison-1"

    def test_extra_fields_forbidden(self):
        """Test SuiteRun rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            SuiteRun(
                id="run-1",
                suite_id="suite-1",
                unexpected_field="should fail",
            )

    def test_to_dict(self):
        """Test SuiteRun to_dict conversion."""
        run = SuiteRun(
            id="run-1",
            suite_id="suite-1",
            agent_identity="claude-3-opus",
            started_at="2024-01-15T10:30:00Z",
        )
        d = run.to_dict()
        assert d["id"] == "run-1"
        assert d["suite_id"] == "suite-1"
        assert d["agent_identity"] == "claude-3-opus"
        assert d["started_at"] == "2024-01-15T10:30:00Z"

    def test_config_snapshot_sanitized(self):
        """Test config_snapshot should contain sanitized config."""
        run = SuiteRun(
            id="run-1",
            suite_id="suite-1",
            config_snapshot={
                "storage_path": "/tmp/sessions",
                "max_retries": 3,
                # Note: API keys should NOT be included in snapshot
            },
        )
        assert run.config_snapshot["storage_path"] == "/tmp/sessions"
        assert run.config_snapshot["max_retries"] == 3
