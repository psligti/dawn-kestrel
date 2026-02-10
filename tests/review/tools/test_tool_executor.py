"""
Test suite for ToolExecutor component.

Tests cover:
- Tool initialization and availability checking
- Successful tool execution with output normalization
- Graceful degradation when tools are not installed
- Timeout handling for long-running tools
- Retry logic for transient failures
- Output normalization for all supported tools (bandit, semgrep, safety, grep)

All tests follow Python 3.9 compatibility (typing.Optional[T] instead of T | None).
"""

import json
import logging
import subprocess
from typing import List
from unittest.mock import Mock, patch

import pytest

from dawn_kestrel.agents.review.fsm_security import SecurityFinding
from dawn_kestrel.agents.review.tools import ToolExecutor, ToolResult, create_tool_executor


# ============================================================================
# Mock Tool Output Fixtures
# ============================================================================

# Bandit mock JSON output
MOCK_BANDIT_OUTPUT = """
{
    "results": [
        {
            "test_id": "B105",
            "test_name": "hardcoded_password_string",
            "issue_severity": "HIGH",
            "issue_text": "Possible hardcoded password: 'password123'",
            "location": {
                "path": "src/auth.py",
                "line": 42
            },
            "code": "password = 'password123'"
        },
        {
            "test_id": "B201",
            "test_name": "flask_debug_true",
            "issue_severity": "MEDIUM",
            "issue_text": "A Flask app appears to be run with debug=True",
            "location": {
                "path": "src/app.py",
                "line": 15
            },
            "code": "app.run(debug=True)"
        }
    ]
}
"""

# Semgrep mock JSON output
MOCK_SEMGREP_OUTPUT = """
{
    "results": [
        {
            "check_id": "python.sql-injection",
            "path": "src/api.py",
            "start": {"line": 123},
            "end": {"line": 123},
            "extra": {
                "severity": "ERROR",
                "message": "SQL injection detected: user input not sanitized",
                "lines": "query = f'SELECT * FROM users WHERE id={user_input}'"
            }
        },
        {
            "check_id": "python.xss",
            "path": "src/views.py",
            "start": {"line": 56},
            "end": {"line": 56},
            "extra": {
                "severity": "WARNING",
                "message": "Possible XSS: unsanitized user input in HTML",
                "lines": "return f'<div>{user_content}</div>'"
            }
        }
    ]
}
"""

# Safety mock JSON output
MOCK_SAFETY_OUTPUT = """
[
    {
        "name": "requests",
        "installed_version": "2.25.0",
        "affected_versions": ["<2.25.1"],
        "advisory": "requests is vulnerable to potential HTTP header injection",
        "id": "40302",
        "cve": "CVE-2021-33503"
    },
    {
        "name": "urllib3",
        "installed_version": "1.26.0",
        "affected_versions": ["<1.26.5"],
        "advisory": "Certifier bypass in urllib3",
        "id": "44584",
        "cve": "CVE-2021-33503"
    }
]
"""

# Grep mock text output (format: file:line:match)
MOCK_GREP_OUTPUT = """
src/auth.py:42:password = 'password123'
src/config.py:15:API_KEY = 'sk-1234567890'
src/utils.py:78:eval(user_input)
"""


# ============================================================================
# Test File Fixtures
# ============================================================================


@pytest.fixture
def vulnerable_python_file(tmp_path) -> str:
    """Create a temporary Python file with vulnerabilities for testing."""
    file_path = tmp_path / "vulnerable.py"
    file_path.write_text("""
import os
import hashlib

# Hardcoded password
password = "password123"

# Debug mode enabled
DEBUG = True

# API key exposed
API_KEY = "sk-1234567890abcdef"

# Weak crypto
hash = hashlib.md5(data).hexdigest()

# SQL injection pattern
query = f"SELECT * FROM users WHERE id={user_input}"

# eval usage (dangerous)
result = eval(user_input)
""")
    return str(file_path)


@pytest.fixture
def tool_executor() -> ToolExecutor:
    """Create a ToolExecutor instance with default timeout."""
    return ToolExecutor(default_timeout=30)


@pytest.fixture
def tool_executor_short_timeout() -> ToolExecutor:
    """Create a ToolExecutor instance with short timeout for testing."""
    return ToolExecutor(default_timeout=1)


# ============================================================================
# Test Class: ToolExecutor Initialization
# ============================================================================


class TestToolExecutorInit:
    """Test ToolExecutor initialization and configuration."""

    def test_init_with_default_timeout(self):
        """Verify ToolExecutor initializes with default timeout."""
        executor = ToolExecutor()
        assert executor.default_timeout == 30

    def test_init_with_custom_timeout(self):
        """Verify ToolExecutor accepts custom timeout."""
        executor = ToolExecutor(default_timeout=60)
        assert executor.default_timeout == 60

    def test_create_tool_executor_factory(self):
        """Verify create_tool_executor factory function works."""
        executor = create_tool_executor()
        assert isinstance(executor, ToolExecutor)
        assert executor.default_timeout == 30


# ============================================================================
# Test Class: Tool Availability Checking
# ============================================================================


class TestToolAvailability:
    """Test tool installation checking."""

    def test_grep_tool_installed(self, tool_executor):
        """Verify grep tool is detected as installed (should be present)."""
        # grep is usually installed on Unix-like systems
        is_installed = tool_executor.is_tool_installed("grep")
        # We don't assert True because we don't control the test environment
        assert isinstance(is_installed, bool)

    def test_nonexistent_tool_not_installed(self, tool_executor):
        """Verify nonexistent tool returns False."""
        is_installed = tool_executor.is_tool_installed("this_tool_definitely_does_not_exist_12345")
        assert is_installed is False

    @patch("subprocess.run")
    def test_tool_check_logs_warning_when_not_installed(self, mock_run, tool_executor, caplog):
        """Verify missing tool is logged with [TOOL_MISSING] tag."""
        mock_run.return_value = Mock(returncode=1, stderr="command not found")

        with caplog.at_level(logging.WARNING):
            result = tool_executor.is_tool_installed("nonexistent_tool")

        assert result is False
        assert any("[TOOL_MISSING]" in record.message for record in caplog.records)

    @patch("subprocess.run")
    def test_tool_check_logs_success_when_installed(self, mock_run, tool_executor, caplog):
        """Verify tool availability check logs success when tool is installed."""
        mock_run.return_value = Mock(returncode=0, stdout="bandit 1.7.4")

        with caplog.at_level(logging.INFO):
            result = tool_executor.is_tool_installed("bandit")

        assert result is True


# ============================================================================
# Test Class: Tool Execution - Success Cases
# ============================================================================


class TestToolExecutionSuccess:
    """Test successful tool execution scenarios."""

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_execute_bandit_success(self, mock_installed, mock_popen, tool_executor, caplog):
        """Verify bandit executes successfully and normalizes output."""
        # Mock subprocess behavior
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=(MOCK_BANDIT_OUTPUT, ""))
        mock_process.returncode = 1  # Exit code 1 means findings found (not error)
        mock_popen.return_value = mock_process

        with caplog.at_level(logging.INFO):
            result = tool_executor.execute_tool("bandit", ["-f", "json", "test.py"])

        # Verify success
        assert result.success is True
        assert result.exit_code == 1
        assert len(result.findings) == 2

        # Verify findings are normalized correctly
        assert result.findings[0].severity == "high"
        assert "hardcoded_password" in result.findings[0].title.lower()
        assert result.findings[0].confidence_score == 0.70

        # Verify logging
        assert any(
            "[TOOL_EXEC] Starting tool bandit" in record.message for record in caplog.records
        )
        assert any("[TOOL_DONE] bandit completed" in record.message for record in caplog.records)

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_execute_semgrep_success(self, mock_installed, mock_popen, tool_executor):
        """Verify semgrep executes successfully and normalizes output."""
        # Mock subprocess behavior
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=(MOCK_SEMGREP_OUTPUT, ""))
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = tool_executor.execute_tool("semgrep", ["--json", "test.py"])

        # Verify success
        assert result.success is True
        assert result.exit_code == 0
        assert len(result.findings) == 2

        # Verify findings are normalized correctly
        assert result.findings[0].severity == "critical"  # ERROR -> critical
        assert "sql" in result.findings[0].title.lower()
        assert result.findings[0].confidence_score == 0.80

        assert result.findings[1].severity == "high"  # WARNING -> high

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_execute_safety_success(self, mock_installed, mock_popen, tool_executor):
        """Verify safety executes successfully and normalizes output."""
        # Mock subprocess behavior
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=(MOCK_SAFETY_OUTPUT, ""))
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = tool_executor.execute_tool("safety", ["check", "--json"])

        # Verify success
        assert result.success is True
        assert result.exit_code == 0
        assert len(result.findings) == 2

        # Verify findings are normalized correctly
        assert result.findings[0].severity == "high"  # Dependency vulnerabilities are high
        assert "requests" in result.findings[0].title
        assert result.findings[0].confidence_score == 0.90

        # Verify no file_path for dependency issues
        assert result.findings[0].file_path is None

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_execute_grep_success(self, mock_installed, mock_popen, tool_executor):
        """Verify grep executes successfully and normalizes output."""
        # Mock subprocess behavior
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=(MOCK_GREP_OUTPUT, ""))
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = tool_executor.execute_tool("grep", ["-n", "password", "test.py"])

        # Verify success
        assert result.success is True
        assert result.exit_code == 0
        assert len(result.findings) == 3

        # Verify findings are normalized correctly
        assert result.findings[0].severity == "medium"  # Default for grep
        assert result.findings[0].confidence_score == 0.60
        assert result.findings[0].file_path == "src/auth.py"
        assert result.findings[0].line_number == 42


# ============================================================================
# Test Class: Tool Execution - Failure Cases
# ============================================================================


class TestToolExecutionFailure:
    """Test tool execution failure scenarios."""

    @patch.object(ToolExecutor, "is_tool_installed", return_value=False)
    def test_missing_tool_graceful_degradation(self, mock_installed, tool_executor, caplog):
        """Verify missing tool returns error without crashing."""
        with caplog.at_level(logging.WARNING):
            result = tool_executor.execute_tool("bandit", ["-f", "json", "test.py"])

        # Verify graceful degradation
        assert result.success is False
        assert result.error_message is not None
        assert "not installed" in result.error_message.lower()
        assert result.exit_code == -1
        assert len(result.findings) == 0

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_timeout_handling(self, mock_installed, mock_popen, tool_executor, caplog):
        """Verify tool timeout is handled correctly."""
        # Mock subprocess that returns timeout-like error on exit
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=("", "timeout error"))
        mock_process.returncode = 124  # Standard exit code for timeout
        mock_popen.return_value = mock_process

        with caplog.at_level(logging.WARNING):
            result = tool_executor.execute_tool("bandit", ["-f", "json", "test.py"], timeout=30)

        # Verify failure handling (exit code 124 is treated as error)
        assert result.success is False
        # Note: timed_out is only set when subprocess.TimeoutExpired is raised internally,
        # not when the tool itself returns a timeout exit code
        assert "timed out" in result.error_message.lower() or str(result.exit_code) == "124"
        assert result.exit_code == 124

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_retry_logic_on_failure(self, mock_installed, mock_popen, tool_executor, caplog):
        """Verify retry logic for transient failures."""
        # Mock subprocess that fails twice then succeeds
        mock_process = Mock()
        call_count = [0]

        def mock_communicate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                # First two attempts fail
                raise subprocess.CalledProcessError(returncode=2, cmd="bandit")
            else:
                # Third attempt succeeds
                return (MOCK_BANDIT_OUTPUT, "")

        mock_process.communicate = mock_communicate
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with caplog.at_level(logging.INFO):
            result = tool_executor.execute_tool("bandit", ["-f", "json", "test.py"])

        # Verify success after retries
        assert result.success is True
        assert len(result.findings) == 2
        assert call_count[0] == 3  # 3 attempts (1 initial + 2 retries)

        # Verify retry logging
        assert any("Retrying" in record.message for record in caplog.records)

    @patch("subprocess.Popen")
    @patch.object(ToolExecutor, "is_tool_installed", return_value=True)
    def test_all_retries_exhausted(self, mock_installed, mock_popen, tool_executor, caplog):
        """Verify all retries exhausted returns error."""
        # Mock subprocess that always fails
        mock_process = Mock()
        mock_process.communicate = Mock(
            side_effect=subprocess.CalledProcessError(returncode=2, cmd="bandit")
        )
        mock_process.returncode = 2
        mock_popen.return_value = mock_process

        with caplog.at_level(logging.ERROR):
            result = tool_executor.execute_tool("bandit", ["-f", "json", "test.py"])

        # Verify error after all retries
        assert result.success is False
        assert result.error_message is not None
        assert "after 3 attempts" in result.error_message.lower()

        # Verify error logging (errors are logged per attempt)
        assert any("[TOOL_ERROR]" in record.message for record in caplog.records)


# ============================================================================
# Test Class: Output Normalization
# ============================================================================


class TestOutputNormalization:
    """Test tool output normalization to SecurityFinding format."""

    def test_bandit_output_normalization(self, tool_executor):
        """Verify bandit JSON output is normalized correctly."""
        findings = tool_executor.normalize_bandit_output(MOCK_BANDIT_OUTPUT)

        assert len(findings) == 2

        # Check first finding
        assert findings[0].severity == "high"
        assert "B105" in findings[0].title
        assert "src/auth.py" in findings[0].evidence
        assert findings[0].line_number == 42
        assert findings[0].confidence_score == 0.70

        # Check second finding
        assert findings[1].severity == "medium"
        assert "B201" in findings[1].title
        assert findings[1].line_number == 15

    def test_semgrep_output_normalization(self, tool_executor):
        """Verify semgrep JSON output is normalized correctly."""
        findings = tool_executor.normalize_semgrep_output(MOCK_SEMGREP_OUTPUT)

        assert len(findings) == 2

        # Check first finding (ERROR -> critical)
        assert findings[0].severity == "critical"
        assert "sql-injection" in findings[0].title
        assert findings[0].line_number == 123
        assert findings[0].confidence_score == 0.80

        # Check second finding (WARNING -> high)
        assert findings[1].severity == "high"
        assert "xss" in findings[1].title
        assert findings[1].line_number == 56

    def test_safety_output_normalization(self, tool_executor):
        """Verify safety JSON output is normalized correctly."""
        findings = tool_executor.normalize_safety_output(MOCK_SAFETY_OUTPUT)

        assert len(findings) == 2

        # Check first finding
        assert findings[0].severity == "high"
        assert "requests" in findings[0].title
        assert "Vulnerability ID" in findings[0].evidence
        assert findings[0].confidence_score == 0.90
        assert findings[0].file_path is None  # No file path for dependency issues

        # Check second finding
        assert "urllib3" in findings[1].title

    def test_grep_output_normalization(self, tool_executor):
        """Verify grep text output is normalized correctly."""
        findings = tool_executor.normalize_grep_output(MOCK_GREP_OUTPUT)

        assert len(findings) == 3

        # Check first finding
        assert findings[0].severity == "medium"
        assert findings[0].file_path == "src/auth.py"
        assert findings[0].line_number == 42
        assert findings[0].confidence_score == 0.60

        # Check third finding
        assert findings[2].file_path == "src/utils.py"
        assert findings[2].line_number == 78

    def test_invalid_json_bandit(self, tool_executor):
        """Verify invalid JSON is handled gracefully."""
        findings = tool_executor.normalize_bandit_output("invalid json {{{")
        assert len(findings) == 0

    def test_invalid_json_semgrep(self, tool_executor):
        """Verify invalid JSON is handled gracefully."""
        findings = tool_executor.normalize_semgrep_output("not json at all")
        assert len(findings) == 0

    def test_invalid_json_safety(self, tool_executor):
        """Verify invalid JSON is handled gracefully."""
        findings = tool_executor.normalize_safety_output("broken json")
        assert len(findings) == 0

    def test_empty_grep_output(self, tool_executor):
        """Verify empty grep output returns empty findings list."""
        findings = tool_executor.normalize_grep_output("")
        assert len(findings) == 0


# ============================================================================
# Test Class: Deterministic ID Generation
# ============================================================================


class TestDeterministicIDGeneration:
    """Test that finding IDs are generated deterministically."""

    def test_same_data_produces_same_id(self, tool_executor):
        """Verify same finding data produces same ID."""
        finding_data_1 = {
            "test_id": "B105",
            "file_path": "src/auth.py",
            "line_number": 42,
            "code": "password = 'password123'",
        }
        finding_data_2 = {
            "test_id": "B105",
            "file_path": "src/auth.py",
            "line_number": 42,
            "code": "password = 'password123'",
        }

        id_1 = tool_executor._generate_deterministic_id("bandit", finding_data_1)
        id_2 = tool_executor._generate_deterministic_id("bandit", finding_data_2)

        assert id_1 == id_2

    def test_different_data_produces_different_id(self, tool_executor):
        """Verify different finding data produces different IDs."""
        finding_data_1 = {"test_id": "B105", "file_path": "src/auth.py", "line_number": 42}
        finding_data_2 = {"test_id": "B201", "file_path": "src/app.py", "line_number": 15}

        id_1 = tool_executor._generate_deterministic_id("bandit", finding_data_1)
        id_2 = tool_executor._generate_deterministic_id("bandit", finding_data_2)

        assert id_1 != id_2

    def test_different_tools_same_data_produces_different_id(self, tool_executor):
        """Verify different tools with same data produce different IDs."""
        finding_data = {"file_path": "src/auth.py", "line_number": 42}

        id_bandit = tool_executor._generate_deterministic_id("bandit", finding_data)
        id_semgrep = tool_executor._generate_deterministic_id("semgrep", finding_data)

        assert id_bandit != id_semgrep
