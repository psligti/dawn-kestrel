"""
Tests for SecretsScannerAgent.

Tests cover:
- Bandit execution with hardcoded secrets detection
- Grep fallback pattern matching
- Output normalization to SecurityFinding format
- Mock test fixtures for bandit output
"""

import json
import os
import tempfile
from unittest.mock import Mock

import pytest

# Import the agent and related types
from dawn_kestrel.agents.review.subagents.secrets_scanner import (
    SECRET_PATTERNS,
    SecretsScannerAgent,
)
from dawn_kestrel.agents.review.tools import ToolExecutor, ToolResult
from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_bandit_json_output():
    """Mock bandit JSON output with hardcoded secret findings."""
    return json.dumps({
        "results": [
            {
                "code": "password = 'super_secret_password'",
                "filename": "tests/fixtures/secrets.py",
                "issue_confidence": "HIGH",
                "issue_severity": "HIGH",
                "issue_text": "Possible hardcoded password",
                "line_number": 10,
                "line_range": [10, 10],
                "more_info": "https://bandit.readthedocs.io/en/latest/plugins/b105_hardcoded_password_string.html",
                "test_id": "B105",
                "test_name": "hardcoded_password_string",
                "test_offset": -1,
                "test_name_suffix": "",
            },
        ],
        "errors": [],
        "stats": {
            "nosec": 0,
            "skipped_tests": [],
        },
    })


@pytest.fixture
def mock_empty_bandit_output():
    """Mock bandit JSON output with no findings."""
    return json.dumps({
        "results": [],
        "errors": [],
        "stats": {
            "nosec": 0,
            "skipped_tests": [],
        },
    })


@pytest.fixture
def mock_grep_output():
    """Mock grep output for secret patterns."""
    return """tests/fixtures/secrets.py:42:AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'
tests/fixtures/config.py:10:password = 'super_secret_password'"""


@pytest.fixture
def mock_tool_executor():
    """Create a mock ToolExecutor for testing."""
    executor = Mock(spec=ToolExecutor)
    return executor


@pytest.fixture
def mock_repo_root():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        secrets_dir = os.path.join(tmpdir, "tests", "fixtures")
        os.makedirs(secrets_dir, exist_ok=True)
        secrets_file = os.path.join(secrets_dir, "secrets.py")
        with open(secrets_file, "w") as f:
            f.write("password = 'super_secret_password'\n")
        config_file = os.path.join(secrets_dir, "config.py")
        with open(config_file, "w") as f:
            f.write("api_key = 'AKIAIOSFODNN7EXAMPLE'\n")
        yield tmpdir


# =============================================================================
# Test: Bandit Execution
# =============================================================================


def test_bandit_execution_with_findings(
    mock_tool_executor, mock_bandit_json_output, mock_repo_root
):
    """Test bandit execution returns normalized findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_bandit_json_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="bandit_test_id_1",
                severity="high",
                title="hardcoded_password_string (B105)",
                description="Possible hardcoded password",
                evidence="File: tests/fixtures/secrets.py\nLine: 10\nCode: password = 'super_secret_password'",
                file_path="tests/fixtures/secrets.py",
                line_number=10,
                recommendation="Possible hardcoded password",
                confidence_score=0.70,
                requires_review=True,
            ),
        ],
    )

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert isinstance(result, SubagentTask)
    assert result.agent_name == "secret_scanner"
    assert result.description == "Scan for hardcoded secrets and credentials"
    mock_tool_executor.execute_tool.assert_called_once()
    call_args = mock_tool_executor.execute_tool.call_args
    assert call_args[1]["tool_name"] == "bandit"
    assert "-t" in call_args[1]["args"]
    assert "B105" in call_args[1]["args"]
    assert result.result is not None
    assert "findings" in result.result
    assert "summary" in result.result
    assert len(result.result["findings"]) >= 1


def test_bandit_execution_no_findings(
    mock_tool_executor, mock_empty_bandit_output, mock_repo_root
):
    """Test bandit execution with no findings triggers grep fallback."""
    bandit_result = ToolResult(
        success=True,
        stdout=mock_empty_bandit_output,
        stderr="",
        exit_code=0,
        findings=[],
    )

    grep_result = ToolResult(
        success=True,
        stdout="tests/fixtures/secrets.py:10:password = 'secret'",
        stderr="",
        exit_code=0,
        findings=[
            SecurityFinding(
                id="grep_1",
                severity="medium",
                title="Pattern matched in tests/fixtures/secrets.py",
                description="Grep pattern matched at line 10",
                evidence="File: tests/fixtures/secrets.py\nLine: 10\nMatch: password = 'secret'",
                file_path="tests/fixtures/secrets.py",
                line_number=10,
                recommendation="Review the matched pattern for security implications",
                confidence_score=0.60,
                requires_review=True,
            ),
        ],
    )

    empty_grep_result = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    side_effects = [bandit_result] + [empty_grep_result] * (len(SECRET_PATTERNS) - 1) + [grep_result]
    mock_tool_executor.execute_tool.side_effect = side_effects

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert mock_tool_executor.execute_tool.call_count >= 2
    first_call = mock_tool_executor.execute_tool.call_args_list[0]
    assert first_call[1]["tool_name"] == "bandit"
    grep_calls = [call for call in mock_tool_executor.execute_tool.call_args_list if call[1]["tool_name"] == "grep"]
    assert len(grep_calls) >= 1
    assert result.result is not None
    assert len(result.result["findings"]) >= 1


def test_bandit_execution_failure(
    mock_tool_executor, mock_repo_root
):
    """Test bandit execution failure returns empty findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=False,
        stdout="",
        stderr="bandit: command not found",
        exit_code=-1,
        error_message="Tool 'bandit' is not installed. Please install it first.",
        findings=[],
    )

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    assert len(result.result["findings"]) == 0
    assert "Secret scan completed. Found 0 potential secrets" in result.result["summary"]


# =============================================================================
# Test: Grep Fallback
# =============================================================================


def test_grep_fallback_pattern_matching(
    mock_tool_executor, mock_grep_output, mock_repo_root
):
    """Test grep fallback finds secret patterns."""
    bandit_result = ToolResult(
        success=True,
        stdout='{"results": [], "errors": [], "stats": {"nosec": 0, "skipped_tests": []}}',
        stderr="",
        exit_code=0,
        findings=[],
    )

    grep_result = ToolResult(
        success=True,
        stdout=mock_grep_output,
        stderr="",
        exit_code=0,
        findings=[
            SecurityFinding(
                id="grep_1",
                severity="medium",
                title="Pattern matched in tests/fixtures/secrets.py",
                description="Grep pattern matched at line 42",
                evidence="File: tests/fixtures/secrets.py\nLine: 42\nMatch: AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'",
                file_path="tests/fixtures/secrets.py",
                line_number=42,
                recommendation="Review the matched pattern for security implications",
                confidence_score=0.60,
                requires_review=True,
            ),
        ],
    )

    empty_grep_result = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    side_effects = [bandit_result] + [empty_grep_result] * (len(SECRET_PATTERNS) - 1) + [grep_result]
    mock_tool_executor.execute_tool.side_effect = side_effects

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert mock_tool_executor.execute_tool.call_count >= 2
    grep_calls = [call for call in mock_tool_executor.execute_tool.call_args_list if call[1]["tool_name"] == "grep"]
    assert len(grep_calls) >= 1
    grep_args = grep_calls[0][1]["args"]
    assert "-E" in grep_args
    assert result.result is not None
    assert len(result.result["findings"]) >= 1


def test_grep_fallback_specific_files(
    mock_tool_executor, mock_repo_root
):
    """Test grep fallback with specific file list."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    specific_files = ["tests/fixtures/secrets.py", "tests/fixtures/config.py"]
    result = agent.execute(repo_root=mock_repo_root, files=specific_files)

    grep_calls = [call for call in mock_tool_executor.execute_tool.call_args_list if call[1]["tool_name"] == "grep"]
    if grep_calls:
        grep_args = grep_calls[0][1]["args"]
        assert "tests/fixtures/secrets.py" in grep_args
        assert "tests/fixtures/config.py" in grep_args


# =============================================================================
# Test: Output Normalization
# =============================================================================


def test_bandit_output_normalization_to_security_finding(
    mock_tool_executor, mock_bandit_json_output, mock_repo_root
):
    """Test bandit output is normalized to SecurityFinding format."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_bandit_json_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="bandit_test_id_1",
                severity="high",
                title="hardcoded_password_string (B105)",
                description="Possible hardcoded password",
                evidence="File: tests/fixtures/secrets.py\nLine: 10\nCode: password = 'super_secret_password'",
                file_path="tests/fixtures/secrets.py",
                line_number=10,
                recommendation="Possible hardcoded password",
                confidence_score=0.70,
                requires_review=True,
            ),
        ],
    )

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    findings = result.result["findings"]
    assert len(findings) >= 1
    finding = findings[0]
    assert "id" in finding
    assert "severity" in finding
    assert "title" in finding
    assert "description" in finding
    assert "evidence" in finding
    assert "file_path" in finding
    assert "line_number" in finding
    assert "recommendation" in finding
    assert "requires_review" in finding


def test_secret_patterns_defined():
    """Test that secret patterns are defined for grep fallback."""
    assert len(SECRET_PATTERNS) > 0
    assert any("AKIA" in pattern for pattern in SECRET_PATTERNS)
    assert any("password" in pattern.lower() for pattern in SECRET_PATTERNS)


def test_agent_initialization():
    """Test agent can be initialized with or without ToolExecutor."""
    mock_executor = Mock(spec=ToolExecutor)
    agent_with_executor = SecretsScannerAgent(tool_executor=mock_executor)
    assert agent_with_executor.tool_executor == mock_executor

    agent_without_executor = SecretsScannerAgent()
    assert agent_without_executor.tool_executor is not None
    assert isinstance(agent_without_executor.tool_executor, ToolExecutor)


def test_subagent_task_result_structure(
    mock_tool_executor, mock_bandit_json_output, mock_repo_root
):
    """Test SubagentTask result has required structure."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_bandit_json_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="bandit_test_id_1",
                severity="high",
                title="hardcoded_password_string (B105)",
                description="Possible hardcoded password",
                evidence="File: tests/fixtures/secrets.py\nLine: 10\nCode: password = 'super_secret_password'",
                file_path="tests/fixtures/secrets.py",
                line_number=10,
                recommendation="Possible hardcoded password",
                confidence_score=0.70,
                requires_review=True,
            ),
        ],
    )

    agent = SecretsScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.task_id == "secret_scanner_task"
    assert result.todo_id == "todo_secret_scanner"
    assert result.agent_name == "secret_scanner"
    assert "bandit" in result.tools
    assert "grep" in result.tools
    assert result.result is not None
    assert "findings" in result.result
    assert "summary" in result.result
    assert isinstance(result.result["findings"], list)
    assert isinstance(result.result["summary"], str)
