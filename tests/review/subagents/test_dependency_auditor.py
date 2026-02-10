"""
Tests for DependencyAuditorAgent.

This module tests the DependencyAuditorAgent functionality:
- Safety tool execution and normalization
- pip-audit fallback tool execution
- SubagentTask result structure
- Error handling for missing tools
"""

from unittest.mock import Mock, MagicMock, patch

import pytest

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.subagents.dependency_auditor import (
    DependencyAuditorAgent,
)
from dawn_kestrel.agents.review.tools import ToolResult


# Mock safety JSON output with vulnerable packages
MOCK_SAFETY_OUTPUT = """
[
  {
    "name": "requests",
    "installed_version": "2.25.1",
    "affected_versions": ["<2.26.0"],
    "advisory": "Requests library is vulnerable to CRLF injection via redirect headers.",
    "id": "PYSEC-2021-299",
    "cve": "CVE-2021-33503"
  },
  {
    "name": "urllib3",
    "installed_version": "1.26.4",
    "affected_versions": ["<1.26.5"],
    "advisory": "urllib3 is vulnerable to CRLF injection via special crafted requests.",
    "id": "PYSEC-2021-142",
    "cve": "CVE-2021-28363"
  }
]
"""


# Mock pip-audit JSON output with vulnerable packages
MOCK_PIP_AUDIT_OUTPUT = """
[
  {
    "name": "requests",
    "installed_version": "2.25.1",
    "vulns": [
      {
        "id": "PYSEC-2021-299",
        "aliases": ["CVE-2021-33503"],
        "details": "Requests library is vulnerable to CRLF injection via redirect headers.",
        "fix_versions": ["2.26.0"]
      }
    ]
  },
  {
    "name": "urllib3",
    "installed_version": "1.26.4",
    "vulns": [
      {
        "id": "PYSEC-2021-142",
        "aliases": ["CVE-2021-28363"],
        "details": "urllib3 is vulnerable to CRLF injection via special crafted requests.",
        "fix_versions": ["1.26.5"]
      }
    ]
  }
]
"""


class TestDependencyAuditorAgent:
    """Tests for DependencyAuditorAgent initialization and execution."""

    def test_initialization_default_executor(self):
        """Test that agent initializes with default ToolExecutor."""
        agent = DependencyAuditorAgent()
        assert agent.tool_executor is not None
        assert agent.logger is not None

    def test_initialization_custom_executor(self):
        """Test that agent accepts custom ToolExecutor."""
        mock_executor = Mock(spec=DependencyAuditorAgent.__init__)
        agent = DependencyAuditorAgent(tool_executor=mock_executor)
        assert agent.tool_executor is not None

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_execute_with_safety_success(self, mock_popen, mock_run):
        """Test execute() with successful safety scan."""
        # Mock subprocess.run for tool installation check (returns success)
        mock_run_result = Mock()
        mock_run_result.returncode = 0
        mock_run.return_value = mock_run_result

        # Mock subprocess.Popen for safety execution
        mock_process = MagicMock()
        mock_process.returncode = 1  # Exit code 1 means findings found
        mock_process.communicate.return_value = (MOCK_SAFETY_OUTPUT, "")
        mock_process.__enter__ = Mock(return_value=mock_process)
        mock_process.__exit__ = Mock(return_value=False)
        mock_popen.return_value = mock_process

        # Create agent and execute
        agent = DependencyAuditorAgent()
        result = agent.execute(repo_root="/fake/repo")

        # Verify SubagentTask structure
        assert isinstance(result, SubagentTask)
        assert result.task_id == "dependency_auditor_task"
        assert result.todo_id == "todo_dependency_auditor"
        assert result.agent_name == "dependency_auditor"
        assert "safety" in result.tools
        assert "pip-audit" in result.tools

        # Verify result structure
        assert result.result is not None
        assert "findings" in result.result
        assert "summary" in result.result

        # Verify findings were captured
        findings = result.result["findings"]
        assert len(findings) == 2
        assert findings[0]["title"] == "Vulnerable dependency: requests 2.25.1"
        assert findings[0]["severity"] == "high"

        # Verify summary
        summary = result.result["summary"]
        assert "Dependency vulnerability scan completed" in summary
        assert "Found 2 vulnerable dependencies" in summary

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_execute_with_pip_audit_fallback(self, mock_popen, mock_run):
        """Test execute() falls back to pip-audit when safety returns no findings."""
        # Mock subprocess.run for tool installation check (returns success)
        mock_run_result = Mock()
        mock_run_result.returncode = 0
        mock_run.return_value = mock_run_result

        # Mock subprocess calls: first call is safety (no findings), second is pip-audit
        mock_process_safety = MagicMock()
        mock_process_safety.returncode = 0  # Exit code 0 means no findings
        mock_process_safety.communicate.return_value = ("[]", "")
        mock_process_safety.__enter__ = Mock(return_value=mock_process_safety)
        mock_process_safety.__exit__ = Mock(return_value=False)

        mock_process_pip_audit = MagicMock()
        mock_process_pip_audit.returncode = 1  # Exit code 1 means findings found
        mock_process_pip_audit.communicate.return_value = (MOCK_PIP_AUDIT_OUTPUT, "")
        mock_process_pip_audit.__enter__ = Mock(return_value=mock_process_pip_audit)
        mock_process_pip_audit.__exit__ = Mock(return_value=False)

        # Safety first, then pip-audit
        mock_popen.side_effect = [mock_process_safety, mock_process_pip_audit]

        # Create agent and execute
        agent = DependencyAuditorAgent()
        result = agent.execute(repo_root="/fake/repo")

        # Verify findings from pip-audit fallback
        findings = result.result["findings"]
        assert len(findings) == 2
        assert findings[0]["title"] == "Vulnerable dependency: requests 2.25.1"

        # Verify summary mentions both tools
        summary = result.result["summary"]
        assert "Found 2 vulnerable dependencies" in summary

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_execute_with_no_vulnerabilities(self, mock_popen, mock_run):
        """Test execute() with no vulnerabilities found."""
        # Mock subprocess.run for tool installation check (returns success)
        mock_run_result = Mock()
        mock_run_result.returncode = 0
        mock_run.return_value = mock_run_result

        # Mock subprocess for safety (no findings)
        mock_process = MagicMock()
        mock_process.returncode = 0  # Exit code 0 means no findings
        mock_process.communicate.return_value = ("[]", "")
        mock_process.__enter__ = Mock(return_value=mock_process)
        mock_process.__exit__ = Mock(return_value=False)
        mock_popen.return_value = mock_process

        # Create agent and execute
        agent = DependencyAuditorAgent()
        result = agent.execute(repo_root="/fake/repo")

        # Verify no findings
        findings = result.result["findings"]
        assert len(findings) == 0

        # Verify summary mentions 0 findings
        summary = result.result["summary"]
        assert "Found 0 vulnerable dependencies" in summary

    @patch("subprocess.Popen")
    def test_execute_with_safety_tool_missing(self, mock_popen):
        """Test execute() handles missing safety tool gracefully."""
        # Mock FileNotFoundError for safety
        mock_popen.side_effect = FileNotFoundError("safety not found")

        # Create agent and execute
        agent = DependencyAuditorAgent()
        result = agent.execute(repo_root="/fake/repo")

        # Verify empty findings when tool is missing
        findings = result.result["findings"]
        assert len(findings) == 0

        # Verify summary mentions 0 findings
        summary = result.result["summary"]
        assert "Found 0 vulnerable dependencies" in summary

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_scan_with_safety_logging(self, mock_popen, mock_run, caplog):
        """Test that safety scan logs appropriate messages."""
        # Mock subprocess.run for tool installation check (returns success)
        mock_run_result = Mock()
        mock_run_result.returncode = 0
        mock_run.return_value = mock_run_result

        # Mock subprocess for safety
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (MOCK_SAFETY_OUTPUT, "")
        mock_process.__enter__ = Mock(return_value=mock_process)
        mock_process.__exit__ = Mock(return_value=False)
        mock_popen.return_value = mock_process

        # Create agent and execute with logging
        with caplog.at_level("INFO"):
            agent = DependencyAuditorAgent()
            agent.execute(repo_root="/fake/repo")

        # Verify log messages
        log_messages = [record.message for record in caplog.records]
        assert any(
            "[DEPENDENCY_AUDITOR] Starting dependency vulnerability scan" in m for m in log_messages
        )
        assert any("[DEPENDENCY_AUDITOR] Scanning with safety" in m for m in log_messages)
        assert any(
            "[DEPENDENCY_AUDITOR] Dependency vulnerability scan completed" in m
            for m in log_messages
        )

    def test_finding_structure_compliance(self):
        """Test that findings conform to SecurityFinding structure."""
        # Mock tool result with findings
        mock_findings = [
            SecurityFinding(
                id="test-id-1",
                severity="high",
                title="Test Vulnerability",
                description="Test description",
                evidence="Test evidence",
                file_path=None,
                line_number=None,
                recommendation="Upgrade to safe version",
                confidence_score=0.90,
                requires_review=True,
            )
        ]

        # Verify finding fields
        finding = mock_findings[0]
        assert finding.id == "test-id-1"
        assert finding.severity == "high"
        assert finding.title == "Test Vulnerability"
        assert finding.description == "Test description"
        assert finding.evidence == "Test evidence"
        assert finding.file_path is None  # No file path for dependency issues
        assert finding.line_number is None  # No line number for dependency issues
        assert finding.recommendation == "Upgrade to safe version"
        assert finding.confidence_score == 0.90
        assert finding.requires_review is True
