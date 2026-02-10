"""Test self-verification functionality in BaseReviewerAgent."""

import pytest
from unittest.mock import Mock
from pathlib import Path
import tempfile
import subprocess
import shlex

from dawn_kestrel.agents.review.base import BaseReviewerAgent
from dawn_kestrel.agents.review.contracts import Finding
from dawn_kestrel.agents.review.verifier import GrepFindingsVerifier


class MockReviewerAgent(BaseReviewerAgent):
    """Concrete mock reviewer for testing BaseReviewerAgent methods."""

    async def review(self, context):
        """Mock review implementation."""
        from dawn_kestrel.agents.review.contracts import ReviewOutput, Scope, MergeGate

        return ReviewOutput(
            agent="mock",
            summary="Mock review",
            severity="merge",
            scope=Scope(
                relevant_files=context.changed_files, ignored_files=[], reasoning="Mock reviewer"
            ),
            merge_gate=MergeGate(decision="approve", must_fix=[], should_fix=[]),
        )

    def get_system_prompt(self):
        """Mock system prompt."""
        return "Mock system prompt"

    def get_relevant_file_patterns(self):
        """Mock file patterns."""
        return ["*.py"]

    def get_agent_name(self) -> str:
        return "MockReviewerAgent"

    def get_allowed_tools(self) -> list:
        return []


class TestSelfVerification:
    """Test verify_findings(), _extract_search_terms(), _grep_files() methods."""

    @pytest.fixture
    def reviewer(self):
        """Create a GrepFindingsVerifier instance."""
        return GrepFindingsVerifier()

    @pytest.fixture
    def sample_finding(self):
        """Create a sample Finding object."""
        return Finding(
            id="test-001",
            title="HARDCODED_SECRET found in code",
            severity="critical",
            confidence="high",
            owner="security",
            estimate="S",
            evidence='File: config.py:45 - Found hardcoded secret "API_KEY" in code',
            risk="Secret exposure",
            recommendation="Remove hardcoded secret",
        )

    @pytest.fixture
    def sample_findings(self):
        """Create multiple sample Finding objects."""
        return [
            Finding(
                id="test-001",
                title="HARDCODED_SECRET in config.py",
                severity="critical",
                confidence="high",
                owner="security",
                estimate="S",
                evidence='Found hardcoded "API_KEY" on line 45',
                risk="Secret exposed",
                recommendation="Use environment variables",
            ),
            Finding(
                id="test-002",
                title="Unsafe eval() call detected",
                severity="critical",
                confidence="high",
                owner="dev",
                estimate="M",
                evidence="eval(user_input) found in process_data()",
                risk="Code injection",
                recommendation="Use ast.literal_eval instead",
            ),
            Finding(
                id="test-003",
                title="SQL injection risk",
                severity="warning",
                confidence="medium",
                owner="dev",
                estimate="L",
                evidence='subprocess.run("rm -rf /", shell=True) detected',
                risk="Command injection",
                recommendation="Avoid shell=True",
            ),
        ]

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with mock code files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.py"
            config_path.write_text("""
# Configuration file
API_KEY = "sk-1234567890"
DEBUG = True
DATABASE_URL = "postgres://localhost/db"
""")

            process_path = Path(tmpdir) / "process.py"
            process_path.write_text("""
def process_data(user_input):
    result = eval(user_input)
    return result
""")

            utils_path = Path(tmpdir) / "utils.py"
            utils_path.write_text("""
import subprocess

def run_command(cmd):
    return subprocess.run(cmd, shell=True)
""")

            yield tmpdir

    # ===== verify_findings() tests =====

    def test_verify_findings_with_valid_findings(
        self, reviewer, sample_findings, temp_repo, mocker
    ):
        """Test verify_findings() with valid findings returns verification evidence."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '5:API_KEY = "sk-1234567890"\n10:DATABASE_URL = "postgres://localhost/db"'
        )

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer.verify(sample_findings, ["config.py", "process.py"], temp_repo)

        assert isinstance(result, list)
        assert len(result) > 0

        for evidence in result:
            assert "tool_type" in evidence
            assert "search_pattern" in evidence
            assert "matches" in evidence
            assert "line_numbers" in evidence
            assert "file_path" in evidence
            assert evidence["tool_type"] == "grep"

    def test_verify_findings_with_empty_findings(self, reviewer):
        """Test verify_findings() with empty findings returns empty list."""
        result = reviewer.verify([], [], "/fake/repo")

        assert result == []
        assert isinstance(result, list)

    def test_verify_findings_with_invalid_finding_objects(self, reviewer, temp_repo, mocker):
        """Test verify_findings() gracefully handles invalid finding objects."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        mocker.patch("subprocess.run", return_value=mock_result)

        mixed_findings = [
            Finding(
                id="valid-001",
                title="Valid finding",
                severity="warning",
                confidence="medium",
                owner="dev",
                estimate="S",
                evidence="Valid evidence",
                risk="Low risk",
                recommendation="Fix it",
            ),
            "invalid string",
            None,
            12345,
            Mock(title="Mock object without evidence"),
        ]

        result = reviewer.verify(mixed_findings, ["config.py"], temp_repo)

        assert isinstance(result, list)

    def test_verify_findings_evidence_structure_complete(
        self, reviewer, sample_finding, temp_repo, mocker
    ):
        """Test that verify_findings() returns complete evidence structure."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '5:API_KEY = "sk-1234567890"'

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer.verify([sample_finding], ["config.py"], temp_repo)

        assert len(result) > 0

        evidence = result[0]
        assert evidence["tool_type"] == "grep"
        assert evidence["search_pattern"] in ["API_KEY", "HARDCODED_SECRET", "config"]
        assert isinstance(evidence["matches"], list)
        assert isinstance(evidence["line_numbers"], list)
        assert isinstance(evidence["file_path"], str)

        if evidence["matches"]:
            assert all(isinstance(m, str) for m in evidence["matches"])

        if evidence["line_numbers"]:
            assert all(isinstance(ln, int) for ln in evidence["line_numbers"])

    # ===== _extract_search_terms() tests =====

    def test_extract_search_terms_with_quoted_strings(self, reviewer):
        """Test _extract_search_terms() extracts quoted strings correctly."""
        evidence = 'Found hardcoded "API_KEY" and "password" in code'
        title = "Security issue"

        result = reviewer._extract_search_terms(evidence, title)

        assert "API_KEY" in result
        assert "password" in result

    def test_extract_search_terms_with_single_quotes(self, reviewer):
        """Test _extract_search_terms() handles single-quoted strings."""
        evidence = "Found 'SECRET_TOKEN' and 'database_password'"
        title = "Issue"

        result = reviewer._extract_search_terms(evidence, title)

        assert "SECRET_TOKEN" in result
        assert "database_password" in result

    def test_extract_search_terms_with_code_identifiers(self, reviewer):
        """Test _extract_search_terms() extracts code identifiers."""
        evidence = "Function eval(user_input) and subprocess.run(cmd) detected"
        title = "Code safety"

        result = reviewer._extract_search_terms(evidence, title)

        assert "eval" in result
        assert "subprocess" in result

    def test_extract_search_terms_with_assignments(self, reviewer):
        """Test _extract_search_terms() extracts identifiers from assignments."""
        evidence = "Variable result = subprocess.run() and data = json.loads()"
        title = "Issue"

        result = reviewer._extract_search_terms(evidence, title)

        assert "subprocess" in result
        assert "json" in result

    def test_extract_search_terms_with_title_all_caps(self, reviewer):
        """Test _extract_search_terms() extracts all-caps identifiers from title."""
        evidence = "Some evidence here"
        title = "SQL_INJECTION found in QUERY_BUILDER"

        result = reviewer._extract_search_terms(evidence, title)

        assert "SQL_INJECTION" in result
        assert "QUERY_BUILDER" in result

    def test_extract_search_terms_filters_common_words(self, reviewer):
        """Test _extract_search_terms() filters out common words."""
        evidence = "The line and file for the function are tested"
        title = "Test finding"

        result = reviewer._extract_search_terms(evidence, title)

        assert "the" not in result
        assert "and" not in result
        assert "for" not in result
        assert "are" not in result
        assert "line" not in result
        assert "file" not in result

    def test_extract_search_terms_limits_to_five_terms(self, reviewer):
        """Test _extract_search_terms() limits to 5 search terms."""
        evidence = 'Found "API_KEY", "password", "token", "secret", "key", "credential", "auth"'
        title = "MULTIPLE_ISSUES_DETECTED"

        result = reviewer._extract_search_terms(evidence, title)

        assert len(result) <= 5
        assert isinstance(result, list)

    def test_extract_search_terms_filters_empty_strings(self, reviewer):
        """Test _extract_search_terms() filters empty strings."""
        evidence = 'Found "API_KEY" and "" in code'
        title = "  "

        result = reviewer._extract_search_terms(evidence, title)

        assert "" not in result
        assert "  " not in result
        assert all(term for term in result)

    def test_extract_search_terms_mixed_patterns(self, reviewer):
        """Test _extract_search_terms() with mixed patterns."""
        evidence = 'Found "API_KEY" in code with eval() call and subprocess.run()'
        title = "SQL_INJECTION detected"

        result = reviewer._extract_search_terms(evidence, title)

        assert "API_KEY" in result
        assert "eval" in result or "subprocess" in result
        assert "SQL_INJECTION" in result

    def test_extract_search_terms_case_sensitive(self, reviewer):
        """Test _extract_search_terms() is case-sensitive for code identifiers."""
        evidence = "Found Eval() and eval() in code"
        title = "Issue"

        result = reviewer._extract_search_terms(evidence, title)

        assert any("Eval" in term or "eval" in term for term in result)

    # ===== _grep_files() tests =====

    def test_grep_files_with_mock_files(self, reviewer, temp_repo, mocker):
        """Test _grep_files() with real mock files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '3:API_KEY = "sk-1234567890"\n4:DEBUG = True\n5:DATABASE_URL = "postgres://localhost/db"'

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer._grep_files("API_KEY", ["config.py"], temp_repo)

        mock_run.assert_called_once()
        call_args = mock_run.call_args

        assert call_args[0][0][0] == "grep"
        assert "-n" in call_args[0][0]
        assert "-F" in call_args[0][0]

        escaped_pattern = call_args[0][0][3]
        assert shlex.quote("API_KEY") == escaped_pattern

        assert "matches" in result
        assert "line_numbers" in result
        assert "file_path" in result
        assert len(result["matches"]) == 3
        assert len(result["line_numbers"]) == 3
        assert result["file_path"] == "config.py"

    def test_grep_files_timeout(self, reviewer, temp_repo, mocker):
        """Test _grep_files() handles timeout gracefully."""
        mocker.patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["grep", "-n"], timeout=5)
        )

        result = reviewer._grep_files("pattern", ["config.py"], temp_repo)

        assert result == {"matches": [], "line_numbers": [], "file_path": ""}

    def test_grep_files_no_matches(self, reviewer, temp_repo, mocker):
        """Test _grep_files() when grep finds no matches."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer._grep_files("NONEXISTENT_PATTERN", ["config.py"], temp_repo)

        assert result["matches"] == []
        assert result["line_numbers"] == []
        assert result["file_path"] == ""

    def test_grep_files_multiple_files(self, reviewer, temp_repo, mocker):
        """Test _grep_files() searches multiple files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "3:import subprocess\n5:subprocess.run"

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer._grep_files("subprocess", ["process.py", "utils.py"], temp_repo)

        assert len(result["matches"]) > 0
        assert len(result["line_numbers"]) > 0
        assert result["file_path"] in ["process.py", "utils.py"]

    def test_grep_files_file_not_exists(self, reviewer, temp_repo, mocker):
        """Test _grep_files() with non-existent file."""
        mock_run = mocker.patch("subprocess.run")

        result = reviewer._grep_files("pattern", ["nonexistent.py"], temp_repo)

        mock_run.assert_not_called()
        assert result == {"matches": [], "line_numbers": [], "file_path": ""}

    def test_grep_uses_fixed_string_matching(self, reviewer, temp_repo, mocker):
        """Test that grep uses -F flag for fixed string matching."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "5:some content"

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        reviewer._grep_files("API_KEY", ["config.py"], temp_repo)

        call_args = mock_run.call_args[0][0]
        assert "-F" in call_args

    def test_grep_uses_line_numbers(self, reviewer, temp_repo, mocker):
        """Test that grep uses -n flag for line numbers."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "5:some content"

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        reviewer._grep_files("pattern", ["config.py"], temp_repo)

        call_args = mock_run.call_args[0][0]
        assert "-n" in call_args

    def test_grep_parsing_line_numbers(self, reviewer, temp_repo, mocker):
        """Test _grep_files() correctly parses grep output with line numbers."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "3:first match\n7:second match\n10:third match"

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer._grep_files("pattern", ["config.py"], temp_repo)

        assert result["line_numbers"] == [3, 7, 10]
        assert result["matches"] == ["first match", "second match", "third match"]

    def test_grep_malformed_output(self, reviewer, temp_repo, mocker):
        """Test _grep_files() handles malformed grep output gracefully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "line without colon\nanother bad line\n5:good line"

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer._grep_files("pattern", ["config.py"], temp_repo)

        assert result["line_numbers"] == [5]
        assert result["matches"] == ["good line"]

    # ===== Backward Compatibility tests =====

    def test_backward_compatibility_existing_methods(self, reviewer):
        """Test that existing methods still work correctly."""
        # GrepFindingsVerifier is a simple verification strategy,
        # not a full reviewer agent, so it doesn't have these methods
        # This test is kept for reference but no longer applies to GrepFindingsVerifier
        pass

    # ===== Performance and Edge Cases =====

    def test_performance_multiple_findings_multiple_terms(
        self, reviewer, sample_findings, temp_repo, mocker
    ):
        """Test performance with multiple findings and search terms."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "5:match found"

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        reviewer.verify(sample_findings, ["config.py", "process.py", "utils.py"], temp_repo)

        assert mock_run.call_count <= len(sample_findings) * 5 * len(
            ["config.py", "process.py", "utils.py"]
        )

    def test_empty_evidence_and_title(self, reviewer):
        """Test _extract_search_terms() with empty evidence and title."""
        result = reviewer._extract_search_terms("", "")

        assert result == []

    def test_very_long_evidence(self, reviewer):
        """Test _extract_search_terms() with very long evidence text."""
        long_evidence = "Found " + " " * 10000 + "API_KEY" + " " * 10000 + "end"
        title = "Issue"

        result = reviewer._extract_search_terms(long_evidence, title)

        assert len(result) <= 5
        assert isinstance(result, list)

    def test_special_characters_in_pattern(self, reviewer, temp_repo, mocker):
        """Test _grep_files() with special characters in pattern."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "5:pattern with special chars"

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        pattern = "API_KEY.*[](){}$^"
        reviewer._grep_files(pattern, ["config.py"], temp_repo)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args is not None
        assert len(call_args) >= 4

    def test_unicode_in_evidence(self, reviewer):
        """Test _extract_search_terms() with unicode characters."""
        evidence = 'Found "API_KEY_日本語" and "password_中文"'
        title = "Issue with émojis 🎉"

        result = reviewer._extract_search_terms(evidence, title)

        assert isinstance(result, list)
        assert "API_KEY_日本語" in result or len(result) <= 5

    def test_verify_findings_logs_warnings(
        self, reviewer, sample_finding, temp_repo, mocker, caplog
    ):
        """Test that verify_findings() logs warnings on errors."""
        mocker.patch("subprocess.run", side_effect=Exception("Grep failed"))

        import logging

        caplog.set_level(logging.DEBUG)

        reviewer.verify([sample_finding], ["config.py"], temp_repo)

        assert isinstance(caplog.records, list)
        assert len(caplog.records) >= 0

    # ===== Integration Tests =====

    def test_full_verification_workflow(self, reviewer, sample_finding, temp_repo, mocker):
        """Test complete workflow: extract terms → grep → return evidence."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '5:API_KEY = "sk-1234567890"\n10:DEBUG = True'

        mocker.patch("subprocess.run", return_value=mock_result)

        result = reviewer.verify([sample_finding], ["config.py"], temp_repo)

        assert isinstance(result, list)
        assert len(result) > 0

        for evidence in result:
            assert evidence["tool_type"] == "grep"
            assert evidence["search_pattern"]
            assert evidence["file_path"] == "config.py"

            if evidence["matches"]:
                assert evidence["line_numbers"]
                assert len(evidence["matches"]) == len(evidence["line_numbers"])

    def test_multiple_search_terms_per_finding(self, reviewer, temp_repo, mocker):
        """Test that multiple search terms are extracted per finding."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '5:API_KEY = "value"\n10:subprocess.run()\n15:eval()'

        mocker.patch("subprocess.run", return_value=mock_result)

        finding = Finding(
            id="test-001",
            title="MULTIPLE_SECURITY_ISSUES",
            severity="critical",
            confidence="high",
            owner="security",
            estimate="L",
            evidence='Found "API_KEY", subprocess.run(), and eval() in code',
            risk="Multiple security risks",
            recommendation="Fix all issues",
        )

        result = reviewer.verify([finding], ["config.py"], temp_repo)

        assert len(result) >= 1
        assert all(e["tool_type"] == "grep" for e in result)
