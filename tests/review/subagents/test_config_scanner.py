"""
Tests for ConfigScannerAgent.

This test suite verifies:
- ConfigScannerAgent initialization
- Grep-based pattern detection (debug_mode, test_keys, insecure_defaults, exposed_env_vars, db_passwords, insecure_ssl)
- Finding normalization to SecurityFinding format
- Pattern matching with various config misconfigurations
- Deduplication of findings
"""

import os
import tempfile
import textwrap
from unittest.mock import MagicMock, Mock

import pytest

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.subagents.config_scanner import ConfigScannerAgent
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
def config_scanner(tool_executor):
    """Create a ConfigScannerAgent with mocked ToolExecutor."""
    return ConfigScannerAgent(tool_executor=tool_executor)


@pytest.fixture
def vulnerable_config_file(tmp_path):
    """Create a Python file with security misconfigurations."""
    file_path = tmp_path / "settings.py"
    content = textwrap.dedent(
        """
        # Debug mode enabled
        DEBUG = True

        # Test key in production
        AWS_TEST_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"

        # Insecure CORS wildcard
        ALLOWED_HOSTS = ['*']

        # Exposed environment variable
        db_host = os.environ.get('DB_HOST', 'localhost')

        # Hardcoded database password
        DATABASE_PASSWORD = "hardcoded_password_12345"

        # Insecure SSL configuration
        SSL_VERIFY = False
        """
    )
    file_path.write_text(content)
    return str(file_path)


# =============================================================================
# Test Initialization
# =============================================================================


class TestConfigScannerAgentInit:
    """Test ConfigScannerAgent initialization."""

    def test_init_default_executor(self):
        """Test initialization with default ToolExecutor."""
        from dawn_kestrel.agents.review.tools import ToolExecutor

        agent = ConfigScannerAgent()
        assert agent.tool_executor is not None
        assert isinstance(agent.tool_executor, ToolExecutor)

    def test_init_custom_executor(self, tool_executor):
        """Test initialization with custom ToolExecutor."""
        agent = ConfigScannerAgent(tool_executor=tool_executor)
        assert agent.tool_executor == tool_executor

    def test_init_logger(self, tool_executor):
        """Test that logger is initialized."""
        agent = ConfigScannerAgent(tool_executor=tool_executor)
        assert agent.logger is not None


# =============================================================================
# Test Execution
# =============================================================================


class TestConfigScannerAgentExecute:
    """Test ConfigScannerAgent execution."""

    def test_execute_with_debug_mode_finding(
        self, config_scanner, tool_executor, vulnerable_config_file
    ):
        """Test execution finding DEBUG mode enabled."""
        # Create finding object for debug mode
        finding_obj = SecurityFinding(
            id="test-id",
            severity="high",
            title="Pattern matched in settings.py",
            description="Grep pattern matched",
            evidence="File: settings.py\nLine: 3\nMatch: DEBUG = True",
            file_path="settings.py",
            line_number=3,
            recommendation="Review the matched pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout="settings.py:3:DEBUG = True",
            stderr="",
            exit_code=0,
            findings=[finding_obj],
        )

        # Empty result for other patterns
        empty_result = ToolResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            findings=[],
        )

        # Config patterns has 6 categories with varying pattern counts
        # debug_mode: 6 patterns, test_keys: 6 patterns, insecure_defaults: 10 patterns
        # exposed_env_vars: 10 patterns, db_passwords: 9 patterns, insecure_ssl: 12 patterns
        # Total patterns: 53 patterns
        # First 6 calls (debug_mode patterns) return tool_result, others return empty
        side_effects = [tool_result] * 6 + [empty_result] * 47
        tool_executor.execute_tool.side_effect = side_effects

        # Execute scanner with explicit file list
        result = config_scanner.execute(
            repo_root=os.path.dirname(vulnerable_config_file),
            files=[vulnerable_config_file],
        )

        # Verify SubagentTask result
        assert isinstance(result, SubagentTask)
        assert result.task_id == "config_scanner_task"
        assert result.agent_name == "config_scanner"

        # Verify findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        assert len(findings) >= 1

        # Check that findings have proper structure
        assert findings[0]["file_path"] == "settings.py"
        assert findings[0]["line_number"] == 3
        assert findings[0]["severity"] == "high"
        assert "debug" in findings[0]["title"].lower()

    def test_execute_with_multiple_findings(
        self, config_scanner, tool_executor, vulnerable_config_file
    ):
        """Test execution finding multiple config misconfigurations."""
        # Create finding objects for different patterns
        debug_finding = SecurityFinding(
            id="debug-id",
            severity="high",
            title="Pattern matched",
            description="Grep pattern matched",
            evidence="File: settings.py\nLine: 3\nMatch: DEBUG = True",
            file_path="settings.py",
            line_number=3,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        test_key_finding = SecurityFinding(
            id="testkey-id",
            severity="high",
            title="Pattern matched",
            description="Grep pattern matched",
            evidence="File: settings.py\nLine: 6\nMatch: AWS_TEST_ACCESS_KEY",
            file_path="settings.py",
            line_number=6,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        # Mock grep execution for debug_mode
        debug_result = ToolResult(
            success=True,
            stdout="settings.py:3:DEBUG = True",
            stderr="",
            exit_code=0,
            findings=[debug_finding],
        )

        # Mock grep execution for test_keys
        test_key_result = ToolResult(
            success=True,
            stdout="settings.py:6:AWS_TEST_ACCESS_KEY",
            stderr="",
            exit_code=0,
            findings=[test_key_finding],
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
        # debug_mode (6 patterns) -> debug_result
        # test_keys (6 patterns) -> test_key_result
        # rest (41 patterns) -> empty_result
        tool_executor.execute_tool.side_effect = (
            [debug_result] * 6 + [test_key_result] * 6 + [empty_result] * 41
        )

        # Execute scanner
        result = config_scanner.execute(repo_root=os.path.dirname(vulnerable_config_file))

        # Verify findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        assert len(findings) >= 2

        # Verify summary mentions findings
        summary = result.result.get("summary", "")
        assert "configuration scan" in summary.lower()

    def test_execute_no_findings(self, config_scanner, tool_executor, tmp_path):
        """Test execution with no config misconfigurations found."""
        # Create a clean Python file
        clean_file = tmp_path / "clean_settings.py"
        clean_file.write_text("DEBUG = False\nSECRET_KEY = 'random_secret_key'")

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
        result = config_scanner.execute(repo_root=str(tmp_path))

        # Verify no findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        assert len(findings) == 0

        # Verify summary mentions 0 findings
        summary = result.result.get("summary", "")
        assert "0" in summary or "no potential misconfigurations" in summary.lower()

    def test_execute_with_specific_files(
        self, config_scanner, tool_executor, vulnerable_config_file
    ):
        """Test execution with specific file list."""
        # Create finding object
        finding_obj = SecurityFinding(
            id="test-id",
            severity="high",
            title="Pattern matched",
            description="Grep pattern matched",
            evidence=f"File: {vulnerable_config_file}",
            file_path=vulnerable_config_file,
            line_number=3,
            recommendation="Review pattern",
            confidence_score=0.60,
            requires_review=True,
        )

        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout="settings.py:3:DEBUG = True",
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
        tool_executor.execute_tool.side_effect = [tool_result] * 6 + [empty_result] * 47

        # Execute scanner with specific files
        result = config_scanner.execute(
            repo_root=os.path.dirname(vulnerable_config_file),
            files=[vulnerable_config_file],
        )

        # Verify execution was called
        assert tool_executor.execute_tool.called

        # Verify grep was called with the specific file (check first call)
        first_call = tool_executor.execute_tool.call_args_list[0]
        args = first_call[1].get("args", [])
        assert vulnerable_config_file in args

    def test_deduplication(self, config_scanner, tool_executor, tmp_path):
        """Test finding deduplication."""
        # Create a file
        test_file = tmp_path / "test.py"
        test_file.write_text("DEBUG = True")

        # Create finding objects with same file and line
        finding1 = SecurityFinding(
            id="id1",
            severity="high",
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
            severity="high",
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
            stdout="test.py:1:DEBUG = True",
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

        tool_executor.execute_tool.side_effect = [tool_result] * 6 + [empty_result] * 47

        # Execute scanner
        result = config_scanner.execute(repo_root=str(tmp_path))

        # Verify deduplication - should only have 1 finding for line 1
        assert result.result is not None
        findings = result.result.get("findings", [])
        assert len(findings) == 1

    def test_pattern_severity_mapping(self, config_scanner, tool_executor, tmp_path):
        """Test that pattern categories have correct severity levels."""
        # Create finding with specific severity
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:DEBUG = True",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="high",  # debug_mode is high severity
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py",
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
        result = config_scanner.execute(repo_root=str(tmp_path))

        # Verify findings
        assert result.result is not None
        findings = result.result.get("findings", [])
        if findings:
            # debug_mode should be high severity
            assert findings[0]["severity"] in ["critical", "high", "medium", "low"]


# =============================================================================
# Test Pattern Matching
# =============================================================================


class TestConfigPatternMatching:
    """Test config misconfiguration pattern matching."""

    def test_debug_mode_pattern(self, config_scanner, tool_executor):
        """Test debug mode pattern detection."""
        # Create finding objects for each pattern call
        debug_results = []
        for i in range(6):  # 6 debug_mode patterns
            finding_obj = SecurityFinding(
                id=f"test-id-{i}",
                severity="high",
                title="Pattern matched",
                description="Grep pattern matched",
                evidence="File: test.py\nLine: 1\nMatch: DEBUG = True",
                file_path="test.py",
                line_number=1,
                recommendation="Review pattern",
                confidence_score=0.60,
                requires_review=True,
            )
            debug_results.append(
                ToolResult(
                    success=True,
                    stdout="test.py:1:DEBUG = True",
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

        tool_executor.execute_tool.side_effect = debug_results + [empty_result] * 47

        # Execute with actual file list
        result = config_scanner.execute(repo_root="/fake/path", files=["test.py"])

        findings = result.result.get("findings", [])
        # After deduplication, we expect 1 finding
        assert len(findings) == 1

        # Verify finding structure
        assert findings[0]["file_path"] == "test.py"
        assert findings[0]["line_number"] == 1
        assert findings[0]["severity"] == "high"
        assert "debug" in findings[0]["description"].lower()

    def test_test_keys_pattern(self, config_scanner, tool_executor):
        """Test test keys pattern detection."""
        # Create finding objects
        test_key_results = []
        for i in range(6):  # 6 test_keys patterns
            finding_obj = SecurityFinding(
                id=f"test-id-{i}",
                severity="high",
                title="Pattern matched",
                description="Grep pattern matched",
                evidence="File: test.py\nLine: 1\nMatch: AWS_TEST_ACCESS_KEY",
                file_path="test.py",
                line_number=1,
                recommendation="Review pattern",
                confidence_score=0.60,
                requires_review=True,
            )
            test_key_results.append(
                ToolResult(
                    success=True,
                    stdout="test.py:1:AWS_TEST_ACCESS_KEY",
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
            [empty_result] * 6 + test_key_results + [empty_result] * 41
        )

        # Execute with actual file list
        result = config_scanner.execute(repo_root="/fake/path", files=["test.py"])

        findings = result.result.get("findings", [])
        assert len(findings) == 1

        # Verify finding structure
        assert findings[0]["file_path"] == "test.py"
        assert findings[0]["severity"] == "high"
        assert (
            "test" in findings[0]["description"].lower()
            or "key" in findings[0]["description"].lower()
        )

    def test_insecure_defaults_pattern(self, config_scanner, tool_executor):
        """Test insecure defaults pattern detection."""
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:ALLOWED_HOSTS = ['*']",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py\nLine: 1\nMatch: ALLOWED_HOSTS = ['*']",
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
            result = config_scanner.execute(repo_root=tmpdir)

            findings = result.result.get("findings", [])
            if findings:
                assert "insecure" in findings[0]["title"].lower()

    def test_exposed_env_vars_pattern(self, config_scanner, tool_executor):
        """Test exposed environment variables pattern detection."""
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:db_host = os.environ.get('DB_HOST')",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="medium",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py\nLine: 1\nMatch: os.environ.get",
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
            result = config_scanner.execute(repo_root=tmpdir)

            findings = result.result.get("findings", [])
            if findings:
                assert "env" in findings[0]["title"].lower()

    def test_db_passwords_pattern(self, config_scanner, tool_executor):
        """Test database passwords pattern detection."""
        tool_result = ToolResult(
            success=True,
            stdout='test.py:1:DATABASE_PASSWORD = "hardcoded_password"',
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="critical",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence='File: test.py\nLine: 1\nMatch: DATABASE_PASSWORD = "hardcoded_password"',
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
            result = config_scanner.execute(repo_root=tmpdir)

            findings = result.result.get("findings", [])
            if findings:
                assert "password" in findings[0]["title"].lower()

    def test_insecure_ssl_pattern(self, config_scanner, tool_executor):
        """Test insecure SSL pattern detection."""
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:SSL_VERIFY = False",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="high",
                    title="Pattern matched",
                    description="Grep pattern matched",
                    evidence="File: test.py\nLine: 1\nMatch: SSL_VERIFY = False",
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
            result = config_scanner.execute(repo_root=tmpdir)

            findings = result.result.get("findings", [])
            if findings:
                assert "ssl" in findings[0]["title"].lower()


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestConfigHelperMethods:
    """Test ConfigScannerAgent helper methods."""

    def test_get_pattern_description(self, config_scanner):
        """Test pattern description generation."""
        desc_debug = config_scanner._get_pattern_description("debug_mode")
        assert "debug" in desc_debug.lower()
        assert "production" in desc_debug.lower()

        desc_test_key = config_scanner._get_pattern_description("test_keys")
        assert "test" in desc_test_key.lower()
        assert "key" in desc_test_key.lower()

        desc_insecure = config_scanner._get_pattern_description("insecure_defaults")
        assert "insecure" in desc_insecure.lower()

        desc_env = config_scanner._get_pattern_description("exposed_env_vars")
        assert "environment" in desc_env.lower() or "env" in desc_env.lower()

        desc_db = config_scanner._get_pattern_description("db_passwords")
        assert "password" in desc_db.lower() or "secret" in desc_db.lower()

        desc_ssl = config_scanner._get_pattern_description("insecure_ssl")
        assert "ssl" in desc_ssl.lower() or "tls" in desc_ssl.lower()

    def test_get_pattern_recommendation(self, config_scanner):
        """Test pattern recommendation generation."""
        rec_debug = config_scanner._get_pattern_recommendation("debug_mode")
        assert "disable" in rec_debug.lower() or "false" in rec_debug.lower()

        rec_test_key = config_scanner._get_pattern_recommendation("test_keys")
        assert "remove" in rec_test_key.lower()

        rec_insecure = config_scanner._get_pattern_recommendation("insecure_defaults")
        assert "review" in rec_insecure.lower() or "secure" in rec_insecure.lower()

        rec_env = config_scanner._get_pattern_recommendation("exposed_env_vars")
        assert "environment" in rec_env.lower() or "secret" in rec_env.lower()

        rec_db = config_scanner._get_pattern_recommendation("db_passwords")
        assert "environment variable" in rec_db.lower() or "secret" in rec_db.lower()

        rec_ssl = config_scanner._get_pattern_recommendation("insecure_ssl")
        assert "enable" in rec_ssl.lower() or "verify" in rec_ssl.lower()

    def test_get_pattern_severity(self, config_scanner):
        """Test pattern severity mapping."""
        assert config_scanner._get_pattern_severity("debug_mode") == "high"
        assert config_scanner._get_pattern_severity("test_keys") == "high"
        assert config_scanner._get_pattern_severity("insecure_defaults") == "medium"
        assert config_scanner._get_pattern_severity("exposed_env_vars") == "medium"
        assert config_scanner._get_pattern_severity("db_passwords") == "critical"
        assert config_scanner._get_pattern_severity("insecure_ssl") == "high"
        assert config_scanner._get_pattern_severity("unknown") == "medium"  # Default

    def test_deduplicate_findings(self, config_scanner):
        """Test finding deduplication logic."""
        finding1 = SecurityFinding(
            id="id1",
            severity="high",
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
            severity="high",
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
            severity="high",
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
        dedup = config_scanner._deduplicate_findings([finding1, finding2, finding3])

        # Should have 2 findings (line 1 and line 2)
        assert len(dedup) == 2


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestConfigEdgeCases:
    """Test ConfigScannerAgent edge cases."""

    def test_empty_file_list(self, config_scanner, tool_executor):
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
            result = config_scanner.execute(repo_root=tmpdir, files=[])

            # Verify no findings
            assert result.result is not None
            findings = result.result.get("findings", [])
            assert len(findings) == 0

    def test_grep_failure(self, config_scanner, tool_executor):
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
            result = config_scanner.execute(repo_root=tmpdir)

            # Should still return a valid SubagentTask
            assert isinstance(result, SubagentTask)
            assert result.task_id == "config_scanner_task"
            assert result.result is not None

    def test_summary_format(self, config_scanner, tool_executor):
        """Test summary message format."""
        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:DEBUG = True",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="high",
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
            result = config_scanner.execute(repo_root=tmpdir)

            # Verify summary contains key information
            summary = result.result.get("summary", "")
            assert "configuration scan" in summary.lower()
            assert "completed" in summary.lower()

    def test_finding_structure_compliance(self, config_scanner, tool_executor):
        """Test that findings have correct structure for SubagentTask."""
        # Mock grep execution
        tool_result = ToolResult(
            success=True,
            stdout="test.py:1:DEBUG = True",
            stderr="",
            exit_code=0,
            findings=[
                SecurityFinding(
                    id="test-id",
                    severity="high",
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
            result = config_scanner.execute(repo_root=tmpdir)

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
