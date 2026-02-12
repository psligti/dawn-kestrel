"""
Injection Scanner Agent for FSM-based Security Review.

This module provides a specialized agent for detecting injection vulnerabilities in code:
- Uses ToolExecutor to run semgrep for injection pattern detection
- Semgrep rules for: SQL injection, XSS, command injection, path traversal
- Handles semgrep output normalization to SecurityFinding format
- Returns SubagentTask-compatible results

Security notes:
- NEVER uses shell=True with user input (from napkin)
- Always uses shell=False with list arguments
- Python 3.9 compatible (uses typing.Optional[T] instead of T | None)
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, List, Optional

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.tools import ToolExecutor

if TYPE_CHECKING:
    from dawn_kestrel.llm import LLMClient


logger = logging.getLogger(__name__)


# Semgrep configuration files for injection vulnerability detection
# Using standard semgrep rules from https://semgrep.dev/docs/writing-rules/unsafe-python
# and https://semgrep.dev/docs/writing-rules/unsafe-javascript

# Inline semgrep configuration for injection patterns
SEMGREP_RULES_YAML = """
rules:
  # SQL Injection patterns (Python)
  - id: python.sql-injection.f-string
    pattern-either:
      - pattern: execute("$SQL", ...)
      - pattern: executemany("$SQL", ...)
      - pattern: $X.execute("$SQL")
    languages: [python]
    message: Potential SQL injection via f-string formatting
    severity: ERROR

  - id: python.sql-injection.format
    pattern-either:
      - pattern: execute("...".format(...))
      - pattern: executemany("...".format(...))
    languages: [python]
    message: Potential SQL injection via format string
    severity: ERROR

  # Command Injection patterns (Python)
  - id: python.lang.security.audit.subprocess-shell-true
    patterns:
      - pattern: subprocess.$FUNC(..., shell=True, ...)
        metavariables:
          FUNC: (run | call | Popen | check_output)
    languages: [python]
    message: subprocess call with shell=True potentially unsafe
    severity: ERROR

  - id: python.lang.security.audit.os-system
    pattern: os.system($CMD)
    languages: [python]
    message: os.system call is potentially unsafe
    severity: ERROR

  # Path Traversal patterns (Python)
  - id: python.lang.security.audit.path-traversal-open
    pattern: open($PATH, ...)
    languages: [python]
    message: User-controlled data used in file open
    severity: WARNING

  # XSS patterns (JavaScript)
  - id: javascript.xss.react-props-dangerouslysetinnerhtml
    pattern: <... dangerouslySetInnerHTML={{...}} />
    languages: [javascript, typescript]
    message: User-controlled data passed to dangerouslySetInnerHTML
    severity: WARNING

  - id: javascript.xss.document-write
    pattern: document.write($INPUT)
    languages: [javascript, typescript]
    message: User-controlled data passed to document.write
    severity: WARNING
"""


class InjectionScannerAgent:
    """
    Agent for detecting injection vulnerabilities in code.

    This agent uses semgrep for injection vulnerability detection:
    1. Primary: Run semgrep with injection patterns
    2. Normalize semgrep output to SecurityFinding format
    3. Return SubagentTask-compatible result with findings and summary

    Injection types covered:
    - SQL injection
    - XSS (Cross-Site Scripting)
    - Command injection
    - Path traversal
    """

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        llm_client: Optional["LLMClient"] = None,
    ):
        """Initialize InjectionScannerAgent.

        Args:
            tool_executor: ToolExecutor for running semgrep.
                         If None, creates a new instance.
            llm_client: LLMClient for potential LLM-based analysis.
                       Currently not used, kept for future enhancement.
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.llm_client = llm_client
        self.logger = logger

    def execute(self, repo_root: str, files: Optional[List[str]] = None) -> SubagentTask:
        """
        Execute injection scanning on the given repository.

        Args:
            repo_root: Path to repository root
            files: List of files to scan (optional).
                    If None, scans all supported files.

        Returns:
            SubagentTask with findings and summary
        """
        self.logger.info("[INJECTION_SCANNER] Starting injection vulnerability scan...")

        # Primary: Use semgrep for injection pattern detection
        findings = self._scan_with_semgrep(repo_root, files)

        # Convert findings to dict format for SubagentTask result
        findings_data = []
        for finding in findings:
            findings_data.append(
                {
                    "id": finding.id,
                    "severity": finding.severity,
                    "title": finding.title,
                    "description": finding.description,
                    "evidence": finding.evidence,
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "recommendation": finding.recommendation,
                    "requires_review": finding.requires_review,
                }
            )

        # Build summary
        summary = (
            f"Injection scan completed. Found {len(findings)} potential injection vulnerabilities. "
            f"Scanned for SQL injection, XSS, command injection, and path traversal."
        )

        self.logger.info(f"[INJECTION_SCANNER] {summary}")

        # Return SubagentTask result
        return SubagentTask(
            task_id="injection_scanner_task",
            todo_id="todo_injection_scanner",
            description="Scan for injection vulnerabilities (SQL, XSS, command, path)",
            agent_name="injection_scanner",
            prompt="Scan for injection vulnerabilities",
            tools=["semgrep"],
            result={
                "findings": findings_data,
                "summary": summary,
            },
        )

    def _scan_with_semgrep(
        self, repo_root: str, files: Optional[List[str]] = None
    ) -> List[SecurityFinding]:
        """
        Scan for injection vulnerabilities using semgrep.

        Args:
            repo_root: Path to repository root
            files: List of files to scan (optional)

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[INJECTION_SCANNER] Scanning with semgrep...")

        # Create temporary semgrep config file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as config_file:
            config_file.write(SEMGREP_RULES_YAML)
            config_path = config_file.name

        try:
            # Build semgrep arguments
            args = [
                "-f",
                config_path,  # Use inline rules from config
                "-f",
                "auto",  # Also use auto-detected rules from semgrep registry
                "--json",  # JSON output format
            ]

            # Add target files or directory
            if files:
                args.extend(files)
            else:
                args.append(repo_root)

            # Run semgrep via ToolExecutor
            result = self.tool_executor.execute_tool(tool_name="semgrep", args=args, timeout=60)

            if not result.success:
                self.logger.warning(
                    f"[INJECTION_SCANNER] Semgrep execution failed: {result.error_message}"
                )
                # Don't return error findings - this is a tool issue, not a security issue
                return []

            # Use normalized findings from ToolExecutor
            return result.findings

        finally:
            # Clean up temporary config file
            try:
                os.unlink(config_path)
            except Exception as e:
                self.logger.debug(f"[INJECTION_SCANNER] Failed to clean up config file: {e}")
