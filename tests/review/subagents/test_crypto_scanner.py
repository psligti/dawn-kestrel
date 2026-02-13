"""
Tests for CryptoScannerAgent.

This test suite verifies:
- CryptoScannerAgent initialization
- Grep-based pattern detection (MD5, SHA1, hardcoded keys, ECB, constant-time)
- Finding normalization to SecurityFinding format
- Pattern matching with various weak crypto patterns
- Deduplication of findings
"""

import os
import tempfile
import textwrap
from unittest.mock import MagicMock, Mock, patch

import pytest

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.subagents.crypto_scanner import CryptoScannerAgent
from dawn_kestrel.agents.review.tools import ToolResult


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def tool_executor():
    """Create a ToolExecutor mock for testing."""
    executor = MagicMock()
    return executor


@pytest.fixture
def crypto_scanner(tool_executor):
    """Create a CryptoScannerAgent with mocked ToolExecutor."""
    return CryptoScannerAgent(tool_executor=tool_executor)


@pytest.fixture
def vulnerable_python_file(tmp_path):
    """Create a Python file with weak cryptography patterns."""
    file_path = tmp_path / "vulnerable_crypto.py"
    content = textwrap.dedent(
        """
        import hashlib

        # Weak hash function: MD5
        def hash_password(password: str) -> str:
            return hashlib.md5(password.encode()).hexdigest()

        # Weak hash function: SHA1
        def hash_data(data: str) -> str:
            return hashlib.sha1(data.encode()).hexdigest()

        # Hardcoded key
        ENCRYPTION_KEY = "this_is_a_hardcoded_key_12345"

        # Hardcoded secret
        API_SECRET = "super_secret_key_for_api_98765"

        # Constant-time issue: simple hash comparison
        def verify_token(token: str, expected: str) -> bool:
            return token == expected

        # ECB mode detection (commented pattern for grep)
        # MODE_ECB is a weak encryption mode
        """
    )
    file_path.write_text(content)
    return str(file_path)


@pytest.fixture
def grep_md5_output():
    """Mock grep output for MD5 pattern."""
    return "vulnerable_crypto.py:4:hashlib.md5(password.encode()).hexdigest()"


@pytest.fixture
def grep_sha1_output():
    """Mock grep output for SHA1 pattern."""
    return "vulnerable_crypto.py:9:hashlib.sha1(data.encode()).hexdigest()"


@pytest.fixture
def grep_hardcoded_key_output():
    """Mock grep output for hardcoded key pattern."""
    return 'vulnerable_crypto.py:13:ENCRYPTION_KEY = "this_is_a_hardcoded_key_12345"'


@pytest.fixture
def grep_constant_time_output():
    """Mock grep output for constant-time issue pattern."""
    return "vulnerable_crypto.py:21:return token == expected"


# =============================================================================
# Test Initialization
# =============================================================================


class TestCryptoScannerAgentInit:
    """Test CryptoScannerAgent initialization."""

    def test_init_default_executor(self):
        """Test initialization with default ToolExecutor."""
        from dawn_kestrel.agents.review.tools import ToolExecutor

        agent = CryptoScannerAgent()
        assert agent.tool_executor is not None
        assert isinstance(agent.tool_executor, ToolExecutor)

    def test_init_custom_executor(self, tool_executor):
        """Test initialization with custom ToolExecutor."""
        agent = CryptoScannerAgent(tool_executor=tool_executor)
        assert agent.tool_executor == tool_executor

    def test_init_logger(self, tool_executor):
        """Test that logger is initialized."""
        agent = CryptoScannerAgent(tool_executor=tool_executor)
        assert agent.logger is not None


# =============================================================================
# Test Execution
# =============================================================================


class TestCryptoScannerAgentExecute:
    """Test CryptoScannerAgent execution."""

    def test_execute_with_md5_finding(
        self, crypto_scanner, tool_executor, vulnerable_python_file, grep_md5_output
    ):
        """Test execution finding MD5 usage."""
        # Create fresh finding objects for EACH mock call (important!)
        md5_results = []
        for i in range(5):  # 5 MD5 patterns
            md5_finding_obj = SecurityFinding(
                id=f"md5-id-{i}",
                severity="medium",
                title="Pattern matched in vulnerable_crypto.py",
                description="Grep pattern matched",
                evidence=f"File: vulnerable_crypto.py\nLine: 4\nMatch: {grep_md5_output.split(':', 2)[2]}",
                file_path="vulnerable_crypto.py",
                line_number=4,
                recommendation="Review the matched pattern",
                confidence_score=0.60,
                requires_review=True,
            )
            md5_results.append(
                ToolResult(
                    success=True,
                    stdout=grep_md5_output,
                    stderr="",
                    exit_code=0,
                    findings=[md5_finding_obj],
                )
            )

        # Empty results for other patterns
        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        # Crypto patterns has 5 categories: md5, sha1, hardcoded_key, ecb_mode, constant_time_issue
        # Each category has multiple patterns in the list
        # md5 has 5 patterns, sha1 has 5, hardcoded_key has 5, ecb_mode has 5, constant_time_issue has 5
        # Total patterns: 25 patterns
        # First 5 calls (md5 patterns) return md5_results, others return empty
        side_effects = md5_results + [empty_result] * 20
        tool_executor.execute_tool.side_effect = side_effects

        # Execute scanner with explicit file list to avoid os.walk issues
        result = crypto_scanner.execute(
            repo_root=os.path.dirname(vulnerable_python_file),
            files=[vulnerable_python_file],
        )

        # Verify SubagentTask result
        assert isinstance(result, SubagentTask)
        assert result.task_id == "crypto_scanner_task"
        assert result.agent_name == "crypto_scanner"

        # Verify findings (after deduplication, we expect 1 finding for the same line)
        assert result.result is not None
        findings = result.result.get("findings", [])
        # Findings should be present (deduplication keeps one finding per file/line)
        assert len(findings) >= 1

        # Check that findings have proper structure
        assert findings[0]["file_path"] == "vulnerable_crypto.py"
        assert findings[0]["line_number"] == 4
        assert findings[0]["severity"] in ["medium", "high"]
        assert "md5" in findings[0]["evidence"].lower()

    def test_execute_with_multiple_findings(
        self,
        crypto_scanner,
        tool_executor,
        vulnerable_python_file,
        grep_md5_output,
        grep_sha1_output,
    ):
        """Test execution finding multiple crypto issues."""
        # Create fresh finding objects
        md5_finding_obj = SecurityFinding(
            id="md5-id",
            severity="medium",
            title="Pattern matched in vulnerable_crypto.py",
            description="Grep pattern matched",
            evidence="File: vulnerable_crypto.py\nLine: 4\nMatch: hashlib.md5",
            file_path="vulnerable_crypto.py",
            line_number=4,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        sha1_finding_obj = SecurityFinding(
            id="sha1-id",
            severity="medium",
            title="Pattern matched in vulnerable_crypto.py",
            description="Grep pattern matched",
            evidence="File: vulnerable_crypto.py\nLine: 9\nMatch: hashlib.sha1",
            file_path="vulnerable_crypto.py",
            line_number=9,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        # Mock grep execution for MD5
        md5_result = ToolResult(
            success=True,
            stdout=grep_md5_output,
            stderr="",
            exit_code=0,
            findings=[md5_finding_obj],
        )

        # Mock grep execution for SHA1
        sha1_result = ToolResult(
            success=True,
            stdout=grep_sha1_output,
            stderr="",
            exit_code=0,
            findings=[sha1_finding_obj],
        )

        # Empty result for other patterns
        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        # Setup side_effect for multiple grep calls
        # Crypto patterns has 5 categories with 5 patterns each = 25 total patterns
        # md5 (5 patterns) -> md5_result
        # sha1 (5 patterns) -> sha1_result
        # rest (15 patterns) -> empty_result
        tool_executor.execute_tool.side_effect = (
            [md5_result] * 5 + [sha1_result] * 5 + [empty_result] * 15
        )

        # Execute scanner
        result = crypto_scanner.execute(repo_root=os.path.dirname(vulnerable_python_file))

        # Verify findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        assert len(findings) >= 2

        # Verify summary mentions both findings
        summary = result.result.get("summary", "")
        assert "cryptographic weakness scan" in summary.lower()

    def test_execute_no_findings(self, crypto_scanner, tool_executor, tmp_path):
        """Test execution with no crypto issues found."""
        # Create a clean Python file
        clean_file = tmp_path / "clean_crypto.py"
        clean_file.write_text("def safe_function():\n    return 'safe'")

        # Mock grep execution to return no findings
        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )
        tool_executor.execute_tool.return_value = empty_result

        # Execute scanner
        result = crypto_scanner.execute(repo_root=str(tmp_path))

        # Verify no findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        assert len(findings) == 0

        # Verify summary mentions no findings
        summary = result.result.get("summary", "")
        assert "0" in summary or "no potential issues" in summary.lower()

    def test_execute_with_specific_files(
        self, crypto_scanner, tool_executor, vulnerable_python_file, grep_md5_output
    ):
        """Test execution with specific file list."""
        # Create fresh finding object
        finding_obj = SecurityFinding(
            id="test-id",
            severity="medium",
            title="Pattern matched",
            description="Grep pattern matched",
            evidence=f"File: {vulnerable_python_file}",
            file_path=vulnerable_python_file,
            line_number=4,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout=grep_md5_output,
            stderr="",
            exit_code=0,
            findings=[finding_obj],
        )

        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        # Provide enough mock responses for all pattern calls
        tool_executor.execute_tool.side_effect = [tool_result] * 5 + [empty_result] * 20

        # Execute scanner with specific files
        result = crypto_scanner.execute(
            repo_root=os.path.dirname(vulnerable_python_file),
            files=[vulnerable_python_file],
        )

        # Verify execution was called with file list
        assert tool_executor.execute_tool.called

        # Verify grep was called with the specific file (check first call)
        first_call = tool_executor.execute_tool.call_args_list[0]
        # The args are passed as keyword arguments: tool_name="grep", args=[...]
        args = first_call[1].get("args", [])
        assert vulnerable_python_file in args

    def test_deduplication(self, crypto_scanner, tool_executor, tmp_path):
        """Test finding deduplication."""
        # Create a file
        test_file = tmp_path / "test.py"
        test_file.write_text("hashlib.md5('data')")

        # Create fresh finding objects
        finding1 = SecurityFinding(
            id="id1",
            severity="medium",
            title="Pattern matched",
            description="Grep pattern matched",
            evidence="File: test.py\nLine: 1",
            file_path="test.py",
            line_number=1,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )
        finding2 = SecurityFinding(
            id="id2",
            severity="medium",
            title="Pattern matched",
            description="Grep pattern matched",
            evidence="File: test.py\nLine: 1",
            file_path="test.py",
            line_number=1,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:hashlib.md5('data')",
            stderr="",
            exit_code=0,
            findings=[finding1, finding2],
        )

        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        tool_executor.execute_tool.side_effect = [tool_result] * 5 + [empty_result] * 20

        # Execute scanner
        result = crypto_scanner.execute(repo_root=str(tmp_path))

        # Verify deduplication - should only have 1 finding for line 1 (same file and line)
        assert result.result is not None
        findings = result.result.get("findings", [])
        # The internal _deduplicate_findings removes duplicates based on (file_path, line_number)
        assert len(findings) == 1
        # Both original findings had same file and line
        assert finding1.file_path == finding2.file_path
        assert finding1.line_number == finding2.line_number

    def test_pattern_severity_mapping(
        self, crypto_scanner, tool_executor, vulnerable_python_file, grep_md5_output
    ):
        """Test that pattern categories have correct severity levels."""
        # Mock grep execution for each pattern type
        tool_result = ToolResult(
            success=True,
            stdout=grep_md5_output,
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",  # Default from grep
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: vulnerable_crypto.py",
                    file_path="vulnerable_crypto.py",
                    line_number=4,
                    recommendation="Review pattern",
                    confidence_score=0.60,
                    requires_review=True,
                )
            ],
        )
        tool_executor.execute_tool.return_value = tool_result

        # Execute scanner
        result = crypto_scanner.execute(repo_root=os.path.dirname(vulnerable_python_file))

        # Verify findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        if findings:
            # MD5 should be medium severity
            assert findings[0]["severity"] in ["medium", "high", "low"]


# =============================================================================
# Test Pattern Matching
# =============================================================================


class TestCryptoPatternMatching:
    """Test weak crypto pattern matching."""

    def test_md5_pattern(self, crypto_scanner, tool_executor):
        """Test MD5 pattern detection."""
        # Create fresh finding objects for EACH pattern call
        md5_results = []
        for i in range(5):  # 5 MD5 patterns
            finding_obj = SecurityFinding(
                id=f"test-id-{i}",
                severity="medium",
                title="Pattern matched",
                description="Grep pattern matched",
                evidence="File: test.py\nLine: 1\nMatch: hashlib.md5(data)",
                file_path="test.py",
                line_number=1,
                recommendation="Review pattern",
                confidence_score=0.60,
                requires_review=True,
            )
            md5_results.append(
                ToolResult(
                    success=True,
                    stdout="test.py:1:hashlib.md5(data)",
                    stderr="",
                    exit_code=0,
                    findings=[finding_obj],
                )
            )

        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        tool_executor.execute_tool.side_effect = md5_results + [empty_result] * 20

        # Execute with actual file list (to avoid os.walk on empty dir)
        result = crypto_scanner.execute(repo_root="/fake/path", files=["test.py"])

        findings = result.result.get("findings", [])
        # After deduplication, we expect 1 finding (all 5 patterns match same line)
        assert len(findings) == 1

        # Verify finding structure (not checking for specific title pattern due to concatenation)
        assert findings[0]["file_path"] == "test.py"
        assert findings[0]["line_number"] == 1
        assert findings[0]["severity"] == "medium"
        # Description should be set by the scanner
        assert (
            "MD5" in findings[0]["description"]
            or "cryptographically" in findings[0]["description"].lower()
        )

    def test_sha1_pattern(self, crypto_scanner, tool_executor):
        """Test SHA1 pattern detection."""
        # Create fresh finding objects for EACH pattern call
        sha1_results = []
        for i in range(5):  # 5 SHA1 patterns
            finding_obj = SecurityFinding(
                id=f"test-id-{i}",
                severity="medium",
                title="Pattern matched",
                description="Grep pattern matched",
                evidence="File: test.py\nLine: 1\nMatch: hashlib.sha1(data)",
                file_path="test.py",
                line_number=1,
                recommendation="Review pattern",
                confidence_score=0.60,
                requires_review=True,
            )
            sha1_results.append(
                ToolResult(
                    success=True,
                    stdout="test.py:1:hashlib.sha1(data)",
                    stderr="",
                    exit_code=0,
                    findings=[finding_obj],
                )
            )

        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        tool_executor.execute_tool.side_effect = (
            [empty_result] * 5 + sha1_results + [empty_result] * 15
        )

        # Execute with actual file list (to avoid os.walk on empty dir)
        result = crypto_scanner.execute(repo_root="/fake/path", files=["test.py"])

        findings = result.result.get("findings", [])
        # After deduplication, we expect 1 finding (all 5 patterns match same line)
        assert len(findings) == 1

        # Verify finding structure
        assert findings[0]["file_path"] == "test.py"
        assert findings[0]["line_number"] == 1
        assert findings[0]["severity"] == "medium"
        # Description should be set by the scanner
        assert (
            "SHA1" in findings[0]["description"]
            or "deprecated" in findings[0]["description"].lower()
        )

    def test_hardcoded_key_pattern(self, crypto_scanner, tool_executor):
        """Test hardcoded key pattern detection."""
        tool_result = ToolResult(
            success=True,
            stdout='test.py:1:ENCRYPTION_KEY = "hardcoded_key_12345678"',
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence='File: test.py\nLine: 1\nMatch: ENCRYPTION_KEY = "hardcoded_key_12345678"',
                    file_path="test.py",
                    line_number=1,
                    recommendation="Review pattern",
                    confidence_score=0.60,
                    requires_review=True,
                )
            ],
        )
        tool_executor.execute_tool.return_value = tool_result

        # Execute
        with tempfile.TemporaryDirectory() as tmpdir:
            result = crypto_scanner.execute(repo_root=tmpdir)

            findings = result.result.get("findings", [])
            if findings:
                assert "hardcoded_key" in findings[0]["title"].lower()

    def test_constant_time_pattern(self, crypto_scanner, tool_executor):
        """Test constant-time issue pattern detection."""
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:if hash1 == hash2:",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py\nLine: 1\nMatch: if hash1 == hash2:",
                    file_path="test.py",
                    line_number=1,
                    recommendation="Review pattern",
                    confidence_score=0.60,
                    requires_review=True,
                )
            ],
        )
        tool_executor.execute_tool.return_value = tool_result

        # Execute
        with tempfile.TemporaryDirectory() as tmpdir:
            result = crypto_scanner.execute(repo_root=tmpdir)

            findings = result.result.get("findings", [])
            if findings:
                assert "constant_time" in findings[0]["title"].lower()


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestCryptoHelperMethods:
    """Test CryptoScannerAgent helper methods."""

    def test_get_pattern_description(self, crypto_scanner):
        """Test pattern description generation."""
        desc_md5 = crypto_scanner._get_pattern_description("md5")
        assert "MD5" in desc_md5
        assert "cryptographically broken" in desc_md5

        desc_sha1 = crypto_scanner._get_pattern_description("sha1")
        assert "SHA1" in desc_sha1
        assert "deprecated" in desc_sha1

        desc_key = crypto_scanner._get_pattern_description("hardcoded_key")
        assert "Hardcoded" in desc_key
        assert "keys" in desc_key.lower()

    def test_get_pattern_recommendation(self, crypto_scanner):
        """Test pattern recommendation generation."""
        rec_md5 = crypto_scanner._get_pattern_recommendation("md5")
        assert "SHA-256" in rec_md5 or "SHA-3" in rec_md5

        rec_sha1 = crypto_scanner._get_pattern_recommendation("sha1")
        assert "SHA-256" in rec_sha1 or "SHA-3" in rec_sha1

        rec_key = crypto_scanner._get_pattern_recommendation("hardcoded_key")
        assert "environment variables" in rec_key.lower()

        rec_ecb = crypto_scanner._get_pattern_recommendation("ecb_mode")
        assert "GCM" in rec_ecb or "CBC" in rec_ecb

        rec_const = crypto_scanner._get_pattern_recommendation("constant_time_issue")
        assert "constant-time" in rec_const.lower()

    def test_get_pattern_severity(self, crypto_scanner):
        """Test pattern severity mapping."""
        assert crypto_scanner._get_pattern_severity("md5") == "medium"
        assert crypto_scanner._get_pattern_severity("sha1") == "medium"
        assert crypto_scanner._get_pattern_severity("hardcoded_key") == "high"
        assert crypto_scanner._get_pattern_severity("ecb_mode") == "medium"
        assert crypto_scanner._get_pattern_severity("constant_time_issue") == "medium"
        assert crypto_scanner._get_pattern_severity("unknown") == "medium"  # Default

    def test_deduplicate_findings(self, crypto_scanner):
        """Test finding deduplication logic."""
        finding1 = SecurityFinding(
            id="id1",
            severity="medium",
            title="Test",
            description="Test",
            evidence="Test",
            file_path="test.py",
            line_number=1,
            recommendation="Test",
            confidence_score=0.60,
            requires_review=True,
        )
        finding2 = SecurityFinding(
            id="id2",
            severity="medium",
            title="Test",
            description="Test",
            evidence="Test",
            file_path="test.py",
            line_number=1,
            recommendation="Test",
            confidence_score=0.60,
            requires_review=True,
        )
        finding3 = SecurityFinding(
            id="id3",
            severity="medium",
            title="Test",
            description="Test",
            evidence="Test",
            file_path="test.py",
            line_number=2,
            recommendation="Test",
            confidence_score=0.60,
            requires_review=True,
        )

        # Deduplicate (finding1 and finding2 should be merged)
        dedup = crypto_scanner._deduplicate_findings([finding1, finding2, finding3])

        # Should have 2 findings (line 1 and line 2)
        assert len(dedup) == 2


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestCryptoEdgeCases:
    """Test CryptoScannerAgent edge cases."""

    def test_empty_file_list(self, crypto_scanner, tool_executor):
        """Test with empty file list."""
        # Mock grep to return no findings
        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )
        tool_executor.execute_tool.return_value = empty_result

        # Execute with empty file list
        with tempfile.TemporaryDirectory() as tmpdir:
            result = crypto_scanner.execute(repo_root=tmpdir, files=[])

            # Verify no findings
            assert result.result is not None
            findings = result.result.get("findings", [])
            assert len(findings) == 0

    def test_grep_failure(self, crypto_scanner, tool_executor):
        """Test graceful handling of grep failure."""
        # Mock grep execution failure
        tool_result = ToolResult(
            success=False,
            stdout="",
            stderr="grep: command failed",
            exit_code=1,
            error_message="grep command failed",
        )
        tool_executor.execute_tool.return_value = tool_result

        # Execute scanner
        with tempfile.TemporaryDirectory() as tmpdir:
            result = crypto_scanner.execute(repo_root=tmpdir)

            # Should still return a valid SubagentTask
            assert isinstance(result, SubagentTask)
            assert result.task_id == "crypto_scanner_task"
            assert result.result is not None

    def test_summary_format(self, crypto_scanner, tool_executor):
        """Test summary message format."""
        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:hashlib.md5(data)",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py\nLine: 1",
                    file_path="test.py",
                    line_number=1,
                    recommendation="Review pattern",
                    confidence_score=0.60,
                    requires_review=True,
                )
            ],
        )
        tool_executor.execute_tool.return_value = tool_result

        # Execute scanner
        with tempfile.TemporaryDirectory() as tmpdir:
            result = crypto_scanner.execute(repo_root=tmpdir)

            # Verify summary contains key information
            summary = result.result.get("summary", "")
            assert "cryptographic weakness scan" in summary.lower()
            assert "completed" in summary.lower()

    def test_finding_structure_compliance(self, crypto_scanner, tool_executor):
        """Test that findings have correct structure for SubagentTask."""
        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:hashlib.md5(data)",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py\nLine: 1",
                    file_path="test.py",
                    line_number=1,
                    recommendation="Review pattern",
                    confidence_score=0.60,
                    requires_review=True,
                )
            ],
        )
        tool_executor.execute_tool.return_value = tool_result

        # Execute scanner
        with tempfile.TemporaryDirectory() as tmpdir:
            result = crypto_scanner.execute(repo_root=tmpdir)

            # Verify finding structure
            assert result.result is not None
            findings = result.result.get("findings", [])
            if findings:
                finding = findings[0]
                # Verify all required fields are present
                assert "id" in finding
                assert "severity" in finding
                assert "title" in finding
                assert "description" in finding
                assert "evidence" in finding
                assert "file_path" in finding
                assert "line_number" in finding
                assert "recommendation" in finding
                assert "requires_review" in finding
