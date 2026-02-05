"""Tests for review agent contracts using TDD approach."""
import pytest
from pydantic import ValidationError

from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Check,
    Skip,
    Finding,
    MergeGate,
)


class TestScope:
    """Test Scope model validation."""

    def test_scope_valid(self):
        """Test valid Scope creation."""
        scope = Scope(
            relevant_files=["src/main.py", "tests/test_main.py"],
            ignored_files=["src/legacy.py"],
            reasoning="Main PR changes focused on core logic"
        )
        assert scope.relevant_files == ["src/main.py", "tests/test_main.py"]
        assert scope.ignored_files == ["src/legacy.py"]
        assert scope.reasoning == "Main PR changes focused on core logic"

    def test_scope_minimal(self):
        """Test Scope with minimal fields."""
        scope = Scope(
            relevant_files=["src/main.py"],
            reasoning="No other files relevant"
        )
        assert scope.ignored_files == []

    def test_scope_extra_fields_forbidden(self):
        """Test Scope rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Scope(
                relevant_files=["src/main.py"],
                reasoning="test",
                unexpected_field="should fail"
            )


class TestCheck:
    """Test Check model validation."""

    def test_check_valid(self):
        """Test valid Check creation."""
        check = Check(
            name="security-scan",
            required=True,
            commands=["bandit", "safety check"],
            why="Security is critical for this component",
            expected_signal="Zero vulnerabilities found"
        )
        assert check.name == "security-scan"
        assert check.required is True
        assert check.commands == ["bandit", "safety check"]

    def test_check_minimal(self):
        """Test Check with minimal fields."""
        check = Check(
            name="style-check",
            required=False,
            commands=["black --check ."],
            why="Consistency matters"
        )
        assert check.expected_signal is None


class TestSkip:
    """Test Skip model validation."""

    def test_skip_valid(self):
        """Test valid Skip creation."""
        skip = Skip(
            name="performance-benchmark",
            why_safe="No performance-sensitive changes",
            when_to_run="When performance code changes"
        )
        assert skip.name == "performance-benchmark"
        assert skip.why_safe == "No performance-sensitive changes"

    def test_skip_extra_fields_forbidden(self):
        """Test Skip rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            Skip(
                name="test-skip",
                why_safe="test",
                when_to_run="test",
                extra_field="should fail"
            )


class TestFinding:
    """Test Finding model validation."""

    def test_finding_valid(self):
        """Test valid Finding creation."""
        finding = Finding(
            id="SEC-001",
            title="SQL injection vulnerability",
            severity="critical",
            confidence="high",
            owner="security",
            estimate="M",
            evidence="Line 42: query = f'SELECT * FROM users WHERE id={user_id}'",
            risk="Attackers can execute arbitrary SQL queries",
            recommendation="Use parameterized queries with psycopg2.sql",
            suggested_patch="Replace f-strings with sql.SQL() template"
        )
        assert finding.id == "SEC-001"
        assert finding.severity == "critical"
        assert finding.confidence == "high"
        assert finding.suggested_patch == "Replace f-strings with sql.SQL() template"

    def test_finding_without_suggested_patch(self):
        """Test Finding without optional suggested_patch."""
        finding = Finding(
            id="DOC-001",
            title="Missing docstring",
            severity="warning",
            confidence="medium",
            owner="docs",
            estimate="S",
            evidence="Function process() lacks docstring",
            risk="Users won't understand the function",
            recommendation="Add docstring explaining purpose and parameters"
        )
        assert finding.suggested_patch is None

    def test_finding_invalid_severity(self):
        """Test Finding rejects invalid severity."""
        with pytest.raises(ValidationError):
            Finding(
                id="TEST-001",
                title="Test",
                severity="invalid",
                confidence="high",
                owner="dev",
                estimate="S",
                evidence="test",
                risk="test",
                recommendation="test"
            )

    def test_finding_invalid_confidence(self):
        """Test Finding rejects invalid confidence."""
        with pytest.raises(ValidationError):
            Finding(
                id="TEST-001",
                title="Test",
                severity="warning",
                confidence="invalid",
                owner="dev",
                estimate="S",
                evidence="test",
                risk="test",
                recommendation="test"
            )

    def test_finding_invalid_estimate(self):
        """Test Finding rejects invalid estimate."""
        with pytest.raises(ValidationError):
            Finding(
                id="TEST-001",
                title="Test",
                severity="warning",
                confidence="medium",
                owner="dev",
                estimate="XL",
                evidence="test",
                risk="test",
                recommendation="test"
            )


class TestMergeGate:
    """Test MergeGate model validation."""

    def test_merge_gate_approve(self):
        """Test MergeGate with approve decision."""
        gate = MergeGate(
            decision="approve",
            must_fix=[],
            should_fix=["DOC-001"],
            notes_for_coding_agent=["Good work, just add docs"]
        )
        assert gate.decision == "approve"

    def test_merge_gate_needs_changes(self):
        """Test MergeGate with needs_changes decision."""
        gate = MergeGate(
            decision="needs_changes",
            must_fix=["SEC-001"],
            should_fix=["DOC-001", "STYLE-002"],
            notes_for_coding_agent=["Fix security issue first"]
        )
        assert gate.decision == "needs_changes"
        assert gate.must_fix == ["SEC-001"]

    def test_merge_gate_block(self):
        """Test MergeGate with block decision."""
        gate = MergeGate(
            decision="block",
            must_fix=["SEC-001", "SEC-002"],
            should_fix=[],
            notes_for_coding_agent=["Critical security issues found"]
        )
        assert gate.decision == "block"

    def test_merge_gate_invalid_decision(self):
        """Test MergeGate rejects invalid decision."""
        with pytest.raises(ValidationError):
            MergeGate(
                decision="maybe",
                must_fix=[],
                should_fix=[],
                notes_for_coding_agent=[]
            )

    def test_merge_gate_approve_with_warnings(self):
        """Test MergeGate with approve_with_warnings decision."""
        gate = MergeGate(
            decision="approve_with_warnings",
            must_fix=[],
            should_fix=["STYLE-001"],
            notes_for_coding_agent=["Style issues found, but not blocking"]
        )
        assert gate.decision == "approve_with_warnings"
        assert gate.should_fix == ["STYLE-001"]

    def test_merge_gate_extra_fields_forbidden(self):
        """Test MergeGate rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            MergeGate(
                decision="approve",
                must_fix=[],
                should_fix=[],
                notes_for_coding_agent=[],
                extra_field="should fail"
            )


class TestReviewOutput:
    """Test ReviewOutput model validation."""

    def test_review_output_valid(self):
        """Test valid ReviewOutput creation."""
        output = ReviewOutput(
            agent="security-reviewer",
            summary="No critical security issues found. One medium-risk item.",
            severity="warning",
            scope=Scope(
                relevant_files=["src/auth.py"],
                ignored_files=[],
                reasoning="Auth changes only"
            ),
            checks=[
                Check(
                    name="bandit-scan",
                    required=True,
                    commands=["bandit -r src/"],
                    why="Static analysis for security issues",
                    expected_signal="No issues found"
                )
            ],
            skips=[
                Skip(
                    name="dependency-check",
                    why_safe="No new dependencies added",
                    when_to_run="When requirements.txt changes"
                )
            ],
            findings=[
                Finding(
                    id="SEC-001",
                    title="Weak password hashing",
                    severity="warning",
                    confidence="medium",
                    owner="security",
                    estimate="M",
                    evidence="src/auth.py:45 uses md5 instead of bcrypt",
                    risk="Password hashes can be cracked",
                    recommendation="Use bcrypt with work factor 12"
                )
            ],
            merge_gate=MergeGate(
                decision="needs_changes",
                must_fix=[],
                should_fix=["SEC-001"],
                notes_for_coding_agent=["Replace md5 with bcrypt"]
            )
        )
        assert output.agent == "security-reviewer"
        assert output.severity == "warning"
        assert len(output.findings) == 1

    def test_review_output_merge_severity(self):
        """Test ReviewOutput with merge severity."""
        output = ReviewOutput(
            agent="code-quality",
            summary="Clean code, ready to merge",
            severity="merge",
            scope=Scope(
                relevant_files=["src/utils.py"],
                ignored_files=[],
                reasoning="Minor refactor"
            ),
            checks=[],
            skips=[],
            findings=[],
            merge_gate=MergeGate(
                decision="approve",
                must_fix=[],
                should_fix=[],
                notes_for_coding_agent=["LGTM"]
            )
        )
        assert output.severity == "merge"

    def test_review_output_invalid_severity(self):
        """Test ReviewOutput rejects invalid severity."""
        with pytest.raises(ValidationError):
            ReviewOutput(
                agent="test",
                summary="test",
                severity="invalid",
                scope=Scope(
                    relevant_files=["test.py"],
                    ignored_files=[],
                    reasoning="test"
                ),
                checks=[],
                skips=[],
                findings=[],
                merge_gate=MergeGate(
                    decision="block",
                    must_fix=[],
                    should_fix=[],
                    notes_for_coding_agent=[]
                )
            )

    def test_review_output_extra_fields_forbidden(self):
        """Test ReviewOutput rejects extra fields."""
        with pytest.raises(ValidationError, match="extra"):
            ReviewOutput(
                agent="test",
                summary="test",
                severity="merge",
                scope=Scope(
                    relevant_files=["test.py"],
                    ignored_files=[],
                    reasoning="test"
                ),
                checks=[],
                skips=[],
                findings=[],
                merge_gate=MergeGate(
                    decision="approve",
                    must_fix=[],
                    should_fix=[],
                    notes_for_coding_agent=[]
                ),
                extra_field="should fail"
            )

    def test_review_output_serialization(self):
        """Test ReviewOutput can be serialized to JSON."""
        output = ReviewOutput(
            agent="security-reviewer",
            summary="Test summary",
            severity="warning",
            scope=Scope(
                relevant_files=["test.py"],
                ignored_files=[],
                reasoning="test"
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
        json_str = output.model_dump_json()
        assert '"agent":"security-reviewer"' in json_str
        assert '"severity":"warning"' in json_str

    def test_review_output_from_json(self):
        """Test ReviewOutput can be loaded from JSON."""
        json_str = """{
            "agent": "security-reviewer",
            "summary": "Test summary",
            "severity": "warning",
            "scope": {
                "relevant_files": ["test.py"],
                "ignored_files": [],
                "reasoning": "test"
            },
            "checks": [],
            "skips": [],
            "findings": [],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }"""
        output = ReviewOutput.model_validate_json(json_str)
        assert output.agent == "security-reviewer"
        assert output.severity == "warning"
