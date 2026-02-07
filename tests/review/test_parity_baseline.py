"""Tests for parity between review agent output and baseline fixtures.

This module validates that:
1. Baseline fixtures match ReviewOutput schema
2. Orchestrator can produce outputs compatible with fixtures
3. JSON loading and schema validation works correctly
"""
import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from dawn_kestrel.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Check,
    Skip,
    Finding,
    MergeGate,
    ReviewInputs,
)
from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator


# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "review_baseline"
MINIMAL_FIXTURE_PATH = FIXTURES_DIR / "minimal.json"
TYPICAL_FIXTURE_PATH = FIXTURES_DIR / "typical.json"


def load_json_fixture(file_path: Path) -> dict:
    """Load a JSON fixture file.

    Args:
        file_path: Path to JSON fixture file

    Returns:
        Parsed JSON as dictionary

    Raises:
        FileNotFoundError: If fixture file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestMinimalFixture:
    """Test minimal baseline fixture."""

    def test_minimal_fixture_exists(self):
        """Verify minimal fixture file exists."""
        assert MINIMAL_FIXTURE_PATH.exists(), f"Minimal fixture not found at {MINIMAL_FIXTURE_PATH}"

    def test_minimal_fixture_loads(self):
        """Verify minimal fixture can be loaded as JSON."""
        data = load_json_fixture(MINIMAL_FIXTURE_PATH)
        assert isinstance(data, dict), "Fixture must be a JSON object"
        assert "agent" in data
        assert "summary" in data
        assert "severity" in data
        assert "scope" in data
        assert "merge_gate" in data

    def test_minimal_fixture_schema_valid(self):
        """Verify minimal fixture passes ReviewOutput schema validation."""
        data = load_json_fixture(MINIMAL_FIXTURE_PATH)

        # Validate as ReviewOutput
        output = ReviewOutput(**data)

        # Verify required fields
        assert output.agent == "security"
        assert output.summary == "No security issues found in reviewed files"
        assert output.severity == "merge"
        assert len(output.scope.relevant_files) == 2
        assert len(output.scope.ignored_files) == 0
        assert output.scope.reasoning == "Reviewed authentication and API route files for common security vulnerabilities"
        assert output.merge_gate.decision == "approve"

    def test_minimal_fixture_output(self):
        """Create ReviewOutput from minimal fixture for further testing."""
        data = load_json_fixture(MINIMAL_FIXTURE_PATH)
        return ReviewOutput(**data)


class TestTypicalFixture:
    """Test typical baseline fixture with findings."""

    def test_typical_fixture_exists(self):
        """Verify typical fixture file exists."""
        assert TYPICAL_FIXTURE_PATH.exists(), f"Typical fixture not found at {TYPICAL_FIXTURE_PATH}"

    def test_typical_fixture_loads(self):
        """Verify typical fixture can be loaded as JSON."""
        data = load_json_fixture(TYPICAL_FIXTURE_PATH)
        assert isinstance(data, dict), "Fixture must be a JSON object"
        assert "agent" in data
        assert "summary" in data
        assert "severity" in data
        assert "scope" in data
        assert "merge_gate" in data
        assert len(data["findings"]) > 0

    def test_typical_fixture_schema_valid(self):
        """Verify typical fixture passes ReviewOutput schema validation."""
        data = load_json_fixture(TYPICAL_FIXTURE_PATH)

        # Validate as ReviewOutput
        output = ReviewOutput(**data)

        # Verify required fields
        assert output.agent == "security"
        assert "potential credential exposure" in output.summary.lower()
        assert output.severity == "blocking"
        assert len(output.scope.relevant_files) == 1
        assert len(output.findings) == 1

        # Verify finding structure
        finding = output.findings[0]
        assert finding.id == "SEC-001"
        assert finding.title == "Hardcoded API key in config"
        assert finding.severity == "blocking"
        assert finding.confidence == "high"
        assert finding.owner == "security"
        assert finding.estimate == "S"
        assert "AWS_ACCESS_KEY" in finding.evidence

        # Verify merge gate
        assert output.merge_gate.decision == "block"
        assert len(output.merge_gate.must_fix) > 0
        assert "AWS_ACCESS_KEY" in output.merge_gate.must_fix[0]


class TestFixtureCompatibility:
    """Test that baseline fixtures are compatible with orchestrator output."""

    @pytest.fixture
    def mock_reviewer(self):
        """Create a mock reviewer agent that returns minimal fixture output."""

        class MockReviewer(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "security"

            async def review(self, context: ReviewContext) -> ReviewOutput:
                # Return minimal fixture output (no findings, merge severity)
                return ReviewOutput(
                    agent="security",
                    summary="No security issues found in reviewed files",
                    severity="merge",
                    scope=Scope(
                        relevant_files=["config/auth.py", "config/routes.py"],
                        ignored_files=[],
                        reasoning="Reviewed authentication and API route files for common security vulnerabilities"
                    ),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve",
                        must_fix=[],
                        should_fix=[],
                        notes_for_coding_agent=[]
                    )
                )

            def get_system_prompt(self) -> str:
                return "Mock security review agent"

            def get_relevant_file_patterns(self) -> list[str]:
                return ["*.py"]

        return MockReviewer()

    @staticmethod
    def _typical_fixture_output() -> ReviewOutput:
        """Create ReviewOutput matching typical fixture."""
        return ReviewOutput(
            agent="security",
            summary="No security issues found in reviewed files",
            severity="merge",
            scope=Scope(
                relevant_files=["config/secrets.yaml"],
                ignored_files=[],
                reasoning="Detected what appears to be a hardcoded API key in the configuration file"
            ),
            checks=[
                Check(
                    name="Check for hardcoded secrets",
                    required=True,
                    commands=[
                        "grep -r 'sk_live\\|sk_test\\|AKIA\\|secret_key' . --include='*.py' --include='*.yaml' --include='*.env'"
                    ],
                    why="Security check for common credential patterns",
                    expected_signal="No matches found"
                )
            ],
            skips=[],
            findings=[
                Finding(
                    id="SEC-001",
                    title="Hardcoded API key in config",
                    severity="blocking",
                    confidence="high",
                    owner="security",
                    estimate="S",
                    evidence="Line 42 in config/secrets.yaml contains: AWS_ACCESS_KEY='AKIAIOSFODNN7EXAMPLE'",
                    risk="Secret exposed in version control and production",
                    recommendation="Remove the hardcoded key and load it from a secure environment variable or secret manager",
                    suggested_patch="Remove line 42 from config/secrets.yaml and use os.getenv('AWS_ACCESS_KEY')"
                )
            ],
            merge_gate=MergeGate(
                decision="block",
                must_fix=["Remove hardcoded AWS_ACCESS_KEY from config/secrets.yaml"],
                should_fix=["Add secrets validation during deployment"],
                notes_for_coding_agent=[
                    "CRITICAL: Remove hardcoded AWS credentials immediately",
                    "Rotate any existing keys that may have been exposed"
                ]
            )
        )

    @pytest.mark.asyncio
    async def test_orchestrator_compatibility_minimal(self, mock_reviewer):
        """Verify orchestrator can handle minimal fixture output."""
        from unittest.mock import AsyncMock, patch

        orchestrator = PRReviewOrchestrator(subagents=[mock_reviewer])
        inputs = ReviewInputs(
            repo_root="/tmp/test",
            base_ref="origin/main",
            head_ref="HEAD",
            pr_title="Test PR",
            pr_description="Test description",
        )

        # Mock git operations to avoid repository path validation
        with patch('dawn_kestrel.agents.review.utils.git.get_changed_files') as mock_get_files, \
             patch('dawn_kestrel.agents.review.utils.git.get_diff') as mock_get_diff:
            mock_get_files.return_value = []
            mock_get_diff.return_value = ""

            output = await orchestrator.run_review(inputs)

        # Verify orchestrator output structure
        from dawn_kestrel.agents.review.contracts import OrchestratorOutput
        assert isinstance(output, OrchestratorOutput)
        assert len(output.subagent_results) == 1
        result = output.subagent_results[0]

        # Verify minimal fixture structure
        assert result.agent == "security"
        assert result.summary == "No security issues found in reviewed files"
        assert result.severity == "merge"
        assert len(result.scope.relevant_files) == 2
        assert result.merge_gate.decision == "approve"

    @pytest.mark.asyncio
    async def test_orchestrator_compatibility_typical(self):
        """Verify orchestrator can handle typical fixture output with findings."""
        from unittest.mock import AsyncMock, patch
        from dawn_kestrel.agents.review.contracts import OrchestratorOutput, ReviewOutput, Finding, MergeGate, Scope

        # Create a mock reviewer that returns typical fixture output with findings
        class MockReviewerWithFindings(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "security"

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="security",
                    summary="Found potential credential exposure in config file",
                    severity="blocking",
                    scope=Scope(
                        relevant_files=["config/secrets.yaml"],
                        ignored_files=[],
                        reasoning="Detected what appears to be a hardcoded API key in the configuration file"
                    ),
                    checks=[],
                    skips=[],
                    findings=[
                        Finding(
                            id="SEC-001",
                            title="Hardcoded API key in config",
                            severity="blocking",
                            confidence="high",
                            owner="security",
                            estimate="S",
                            evidence="Line 42 in config/secrets.yaml contains: AWS_ACCESS_KEY='AKIAIOSFODNN7EXAMPLE'",
                            risk="Secret exposed in version control and production",
                            recommendation="Remove the hardcoded key and load it from a secure environment variable or secret manager",
                            suggested_patch="Remove line 42 from config/secrets.yaml and use os.getenv('AWS_ACCESS_KEY')"
                        )
                    ],
                    merge_gate=MergeGate(
                        decision="block",
                        must_fix=["Remove hardcoded AWS_ACCESS_KEY from config/secrets.yaml"],
                        should_fix=["Add secrets validation during deployment"],
                        notes_for_coding_agent=[
                            "CRITICAL: Remove hardcoded AWS credentials immediately",
                            "Rotate any existing keys that may have been exposed"
                        ]
                    )
                )

            def get_system_prompt(self) -> str:
                return "Mock security review agent"

            def get_relevant_file_patterns(self) -> list[str]:
                return ["*.py"]

        orchestrator = PRReviewOrchestrator(subagents=[MockReviewerWithFindings()])
        inputs = ReviewInputs(
            repo_root="/tmp/test",
            base_ref="origin/main",
            head_ref="HEAD",
            pr_title="Test PR with credentials",
            pr_description="This PR adds a config file with AWS keys",
        )

        # Mock git operations to avoid repository path validation
        with patch('dawn_kestrel.agents.review.utils.git.get_changed_files') as mock_get_files, \
             patch('dawn_kestrel.agents.review.utils.git.get_diff') as mock_get_diff:
            mock_get_files.return_value = []
            mock_get_diff.return_value = ""

            output = await orchestrator.run_review(inputs)

        # Verify orchestrator output structure
        assert isinstance(output, OrchestratorOutput)
        assert len(output.subagent_results) == 1
        result = output.subagent_results[0]

        # Verify typical fixture structure
        assert result.agent == "security"
        assert "credential exposure" in result.summary.lower()
        assert result.severity == "blocking"
        assert len(result.findings) == 1

        # Verify finding matches typical fixture
        finding = result.findings[0]
        assert finding.id == "SEC-001"
        assert finding.title == "Hardcoded API key in config"
        assert finding.severity == "blocking"
        assert finding.evidence == "Line 42 in config/secrets.yaml contains: AWS_ACCESS_KEY='AKIAIOSFODNN7EXAMPLE'"
        assert finding.recommendation == "Remove the hardcoded key and load it from a secure environment variable or secret manager"

        # Verify merge gate matches typical fixture
        assert result.merge_gate.decision == "block"
        assert len(result.merge_gate.must_fix) > 0
        assert "AWS_ACCESS_KEY" in result.merge_gate.must_fix[0]

    @pytest.mark.asyncio
    async def test_orchestrator_deduplication(self, mock_reviewer):
        """Verify orchestrator deduplicates findings from multiple agents."""
        from unittest.mock import patch
        from dawn_kestrel.agents.review.contracts import OrchestratorOutput

        # Create two reviewers returning the same finding
        class MockReviewer1(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "security"

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="security",
                    summary="Found security issue",
                    severity="critical",
                    scope=Scope(
                        relevant_files=["config/secrets.yaml"],
                        ignored_files=[],
                        reasoning="Security review"
                    ),
                    checks=[],
                    skips=[],
                    findings=[Finding(
                        id="SEC-001",
                        title="Hardcoded key",
                        severity="critical",
                        confidence="high",
                        owner="security",
                        estimate="S",
                        evidence="Key found",
                        risk="High risk",
                        recommendation="Fix it"
                    )],
                    merge_gate=MergeGate(
                        decision="block",
                        must_fix=["Fix key"],
                        should_fix=[],
                        notes_for_coding_agent=[]
                    )
                )

            def get_system_prompt(self) -> str:
                return "Security agent"

            def get_relevant_file_patterns(self) -> list[str]:
                return ["*.py"]

        class MockReviewer2(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "quality"

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="quality",
                    summary="Security issue found",
                    severity="critical",
                    scope=Scope(
                        relevant_files=["config/secrets.yaml"],
                        ignored_files=[],
                        reasoning="Quality review"
                    ),
                    checks=[],
                    skips=[],
                    findings=[Finding(
                        id="SEC-001",
                        title="Hardcoded key",
                        severity="critical",
                        confidence="high",
                        owner="quality",
                        estimate="S",
                        evidence="Key found in quality review",
                        risk="High risk",
                        recommendation="Fix it"
                    )],
                    merge_gate=MergeGate(
                        decision="block",
                        must_fix=["Fix key"],
                        should_fix=[],
                        notes_for_coding_agent=[]
                    )
                )

            def get_system_prompt(self) -> str:
                return "Quality agent"

            def get_relevant_file_patterns(self) -> list[str]:
                return ["*.py"]

        orchestrator = PRReviewOrchestrator(subagents=[MockReviewer1(), MockReviewer2()])
        inputs = ReviewInputs(
            repo_root="/tmp/test",
            base_ref="origin/main",
            head_ref="HEAD",
            pr_title="Test PR",
        )

        # Mock git operations to avoid repository path validation
        with patch('dawn_kestrel.agents.review.utils.git.get_changed_files') as mock_get_files, \
             patch('dawn_kestrel.agents.review.utils.git.get_diff') as mock_get_diff:
            mock_get_files.return_value = []
            mock_get_diff.return_value = ""

            output = await orchestrator.run_review(inputs)

        # Verify single unique finding (deduplicated)
        assert len(output.subagent_results) == 2
        assert len(output.findings) == 1
        assert output.findings[0].id == "SEC-001"


class TestInvalidFixtureDetection:
    def test_invalid_fixture_raises_validation_error(self):
        """Verify that invalid JSON structure raises ValidationError."""
        invalid_data = {
            "agent": "security",
            "summary": "Test",
            "severity": "invalid_severity",  # Invalid severity value
            "scope": {
                "relevant_files": ["test.py"],
                "reasoning": "Test"
            },
            "merge_gate": {
                "decision": "invalid_decision",  # Invalid decision
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }

        with pytest.raises(ValidationError):
            ReviewOutput(**invalid_data)

    def test_missing_required_field_raises_validation_error(self):
        """Verify that missing required field raises ValidationError."""
        invalid_data = {
            "agent": "security",
            "summary": "Test",
            # Missing severity
            "scope": {
                "relevant_files": ["test.py"],
                "reasoning": "Test"
            },
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }

        with pytest.raises(ValidationError):
            ReviewOutput(**invalid_data)
