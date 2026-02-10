"""
Tests for InjectionScannerAgent.

Tests cover:
- Semgrep execution with injection pattern detection
- Output normalization to SecurityFinding format
- Mock test fixtures for semgrep JSON output
"""

import json
import os
import tempfile
from unittest.mock import Mock

import pytest

# Import agent and related types
from dawn_kestrel.agents.review.subagents.injection_scanner import InjectionScannerAgent
from dawn_kestrel.agents.review.tools import ToolExecutor, ToolResult
from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask

# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_semgrep_sql_injection_output():
    """Mock semgrep JSON output with SQL injection findings."""
    return json.dumps(
        {
            "results": [
                {
                    "check_id": "python.sql-injection.sqlalchemy-compositional",
                    "path": "tests/fixtures/injection.py",
                    "start": {"line": 15, "col": 1},
                    "end": {"line": 15, "col": 50},
                    "extra": {
                        "message": "User-controlled data used in SQL query.",
                        "severity": "ERROR",
                        "metadata": {},
                        "lines": '    query = f"SELECT * FROM users WHERE id={user_input}"\n',
                    },
                },
            ],
            "errors": [],
        }
    )


@pytest.fixture
def mock_semgrep_xss_output():
    """Mock semgrep JSON output with XSS findings."""
    return json.dumps(
        {
            "results": [
                {
                    "check_id": "javascript.xss.react-props-dangerouslysetinnerhtml",
                    "path": "tests/fixtures/xss.js",
                    "start": {"line": 8, "col": 1},
                    "end": {"line": 8, "col": 40},
                    "extra": {
                        "message": "User-controlled data passed to dangerouslySetInnerHTML.",
                        "severity": "WARNING",
                        "metadata": {},
                        "lines": "    <div dangerouslySetInnerHTML={{__html: userContent}} />\n",
                    },
                },
            ],
            "errors": [],
        }
    )


@pytest.fixture
def mock_semgrep_command_injection_output():
    """Mock semgrep JSON output with command injection findings."""
    return json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.subprocess-shell-true",
                    "path": "tests/fixtures/injection.py",
                    "start": {"line": 25, "col": 1},
                    "end": {"line": 25, "col": 60},
                    "extra": {
                        "message": "subprocess call with shell=True potentially unsafe.",
                        "severity": "ERROR",
                        "metadata": {},
                        "lines": "    subprocess.run(command, shell=True)\n",
                    },
                },
            ],
            "errors": [],
        }
    )


@pytest.fixture
def mock_semgrep_path_traversal_output():
    """Mock semgrep JSON output with path traversal findings."""
    return json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.path-traversal-open",
                    "path": "tests/fixtures/path.py",
                    "start": {"line": 12, "col": 1},
                    "end": {"line": 12, "col": 40},
                    "extra": {
                        "message": "User-controlled data used in file open.",
                        "severity": "WARNING",
                        "metadata": {},
                        "lines": "    with open(user_path, 'r') as f:\n",
                    },
                },
            ],
            "errors": [],
        }
    )


@pytest.fixture
def mock_semgrep_empty_output():
    """Mock semgrep JSON output with no findings."""
    return json.dumps(
        {
            "results": [],
            "errors": [],
        }
    )


@pytest.fixture
def mock_tool_executor():
    """Create a mock ToolExecutor for testing."""
    executor = Mock(spec=ToolExecutor)
    return executor


@pytest.fixture
def mock_repo_root():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures_dir = os.path.join(tmpdir, "tests", "fixtures")
        os.makedirs(fixtures_dir, exist_ok=True)
        injection_file = os.path.join(fixtures_dir, "injection.py")
        with open(injection_file, "w") as f:
            f.write('query = f"SELECT * FROM users WHERE id={user_input}"\n')
        xss_file = os.path.join(fixtures_dir, "xss.js")
        with open(xss_file, "w") as f:
            f.write("<div dangerouslySetInnerHTML={{__html: userContent}} />\n")
        yield tmpdir


# =============================================================================
# Test: Semgrep Execution
# =============================================================================


def test_semgrep_sql_injection_detection(
    mock_tool_executor, mock_semgrep_sql_injection_output, mock_repo_root
):
    """Test semgrep execution returns SQL injection findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_sql_injection_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="semgrep_python.sql-injection.sqlalchemy-compositional",
                severity="critical",
                title="Semgrep Rule: python.sql-injection.sqlalchemy-compositional",
                description="User-controlled data used in SQL query.",
                evidence='File: tests/fixtures/injection.py\nLine: 15\nCode:\n    query = f"SELECT * FROM users WHERE id={user_input}"\n',
                file_path="tests/fixtures/injection.py",
                line_number=15,
                recommendation="User-controlled data used in SQL query.",
                confidence_score=0.80,
                requires_review=True,
            ),
        ],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert isinstance(result, SubagentTask)
    assert result.agent_name == "injection_scanner"
    assert result.description == "Scan for injection vulnerabilities (SQL, XSS, command, path)"
    mock_tool_executor.execute_tool.assert_called()
    call_args = mock_tool_executor.execute_tool.call_args
    assert call_args[1]["tool_name"] == "semgrep"
    assert "-f" in call_args[1]["args"]
    assert "--json" in call_args[1]["args"]
    assert result.result is not None
    assert "findings" in result.result
    assert "summary" in result.result
    assert len(result.result["findings"]) >= 1


def test_semgrep_xss_detection(mock_tool_executor, mock_semgrep_xss_output, mock_repo_root):
    """Test semgrep execution returns XSS findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_xss_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="semgrep_javascript.xss.react-props-dangerouslysetinnerhtml",
                severity="high",
                title="Semgrep Rule: javascript.xss.react-props-dangerouslysetinnerhtml",
                description="User-controlled data passed to dangerouslySetInnerHTML.",
                evidence="File: tests/fixtures/xss.js\nLine: 8\nCode:\n    <div dangerouslySetInnerHTML={{__html: userContent}} />\n",
                file_path="tests/fixtures/xss.js",
                line_number=8,
                recommendation="User-controlled data passed to dangerouslySetInnerHTML.",
                confidence_score=0.80,
                requires_review=True,
            ),
        ],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    assert len(result.result["findings"]) >= 1
    finding = result.result["findings"][0]
    assert "XSS" in finding.get("description", "") or "dangerously" in finding.get(
        "description", ""
    )


def test_semgrep_command_injection_detection(
    mock_tool_executor, mock_semgrep_command_injection_output, mock_repo_root
):
    """Test semgrep execution returns command injection findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_command_injection_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="semgrep_python.lang.security.audit.subprocess-shell-true",
                severity="critical",
                title="Semgrep Rule: python.lang.security.audit.subprocess-shell-true",
                description="subprocess call with shell=True potentially unsafe.",
                evidence="File: tests/fixtures/injection.py\nLine: 25\nCode:\n    subprocess.run(command, shell=True)\n",
                file_path="tests/fixtures/injection.py",
                line_number=25,
                recommendation="subprocess call with shell=True potentially unsafe.",
                confidence_score=0.80,
                requires_review=True,
            ),
        ],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    assert len(result.result["findings"]) >= 1
    finding = result.result["findings"][0]
    assert (
        "command" in finding.get("title", "").lower() or "shell" in finding.get("title", "").lower()
    )


def test_semgrep_path_traversal_detection(
    mock_tool_executor, mock_semgrep_path_traversal_output, mock_repo_root
):
    """Test semgrep execution returns path traversal findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_path_traversal_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="semgrep_python.lang.security.audit.path-traversal-open",
                severity="high",
                title="Semgrep Rule: python.lang.security.audit.path-traversal-open",
                description="User-controlled data used in file open.",
                evidence="File: tests/fixtures/path.py\nLine: 12\nCode:\n    with open(user_path, 'r') as f:\n",
                file_path="tests/fixtures/path.py",
                line_number=12,
                recommendation="User-controlled data used in file open.",
                confidence_score=0.80,
                requires_review=True,
            ),
        ],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    assert len(result.result["findings"]) >= 1
    finding = result.result["findings"][0]
    assert (
        "path" in finding.get("title", "").lower()
        or "traversal" in finding.get("title", "").lower()
    )


def test_semgrep_no_findings(mock_tool_executor, mock_semgrep_empty_output, mock_repo_root):
    """Test semgrep execution with no findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_empty_output,
        stderr="",
        exit_code=0,
        findings=[],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    assert len(result.result["findings"]) == 0
    assert "0" in result.result["summary"]


def test_semgrep_execution_failure(mock_tool_executor, mock_repo_root):
    """Test semgrep execution failure returns empty findings."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=False,
        stdout="",
        stderr="semgrep: command not found",
        exit_code=-1,
        error_message="Tool 'semgrep' is not installed. Please install it first.",
        findings=[],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.result is not None
    assert len(result.result["findings"]) == 0
    assert "0" in result.result["summary"]


# =============================================================================
# Test: Output Normalization
# =============================================================================


def test_semgrep_output_normalization_to_security_finding(
    mock_tool_executor, mock_semgrep_sql_injection_output, mock_repo_root
):
    """Test semgrep output is normalized to SecurityFinding format."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_sql_injection_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="semgrep_python.sql-injection.sqlalchemy-compositional",
                severity="critical",
                title="Semgrep Rule: python.sql-injection.sqlalchemy-compositional",
                description="User-controlled data used in SQL query.",
                evidence='File: tests/fixtures/injection.py\nLine: 15\nCode:\n    query = f"SELECT * FROM users WHERE id={user_input}"\n',
                file_path="tests/fixtures/injection.py",
                line_number=15,
                recommendation="User-controlled data used in SQL query.",
                confidence_score=0.80,
                requires_review=True,
            ),
        ],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
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


# =============================================================================
# Test: Agent Structure
# =============================================================================


def test_agent_initialization():
    """Test agent can be initialized with or without ToolExecutor."""
    mock_executor = Mock(spec=ToolExecutor)
    agent_with_executor = InjectionScannerAgent(tool_executor=mock_executor)
    assert agent_with_executor.tool_executor == mock_executor

    agent_without_executor = InjectionScannerAgent()
    assert agent_without_executor.tool_executor is not None
    assert isinstance(agent_without_executor.tool_executor, ToolExecutor)


def test_subagent_task_result_structure(
    mock_tool_executor, mock_semgrep_sql_injection_output, mock_repo_root
):
    """Test SubagentTask result has required structure."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout=mock_semgrep_sql_injection_output,
        stderr="",
        exit_code=1,
        findings=[
            SecurityFinding(
                id="semgrep_python.sql-injection.sqlalchemy-compositional",
                severity="critical",
                title="Semgrep Rule: python.sql-injection.sqlalchemy-compositional",
                description="User-controlled data used in SQL query.",
                evidence='File: tests/fixtures/injection.py\nLine: 15\nCode:\n    query = f"SELECT * FROM users WHERE id={user_input}"\n',
                file_path="tests/fixtures/injection.py",
                line_number=15,
                recommendation="User-controlled data used in SQL query.",
                confidence_score=0.80,
                requires_review=True,
            ),
        ],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    result = agent.execute(repo_root=mock_repo_root)

    assert result.task_id == "injection_scanner_task"
    assert result.todo_id == "todo_injection_scanner"
    assert result.agent_name == "injection_scanner"
    assert "semgrep" in result.tools
    assert result.result is not None
    assert "findings" in result.result
    assert "summary" in result.result
    assert isinstance(result.result["findings"], list)
    assert isinstance(result.result["summary"], str)


def test_semgrep_execution_specific_files(mock_tool_executor, mock_repo_root):
    """Test semgrep execution with specific file list."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout='{"results": [], "errors": []}',
        stderr="",
        exit_code=0,
        findings=[],
    )

    agent = InjectionScannerAgent(tool_executor=mock_tool_executor)
    specific_files = ["tests/fixtures/injection.py", "tests/fixtures/xss.js"]
    result = agent.execute(repo_root=mock_repo_root, files=specific_files)

    call_args = mock_tool_executor.execute_tool.call_args
    assert call_args[1]["tool_name"] == "semgrep"
    args = call_args[1]["args"]
    assert "tests/fixtures/injection.py" in args
    assert "tests/fixtures/xss.js" in args
