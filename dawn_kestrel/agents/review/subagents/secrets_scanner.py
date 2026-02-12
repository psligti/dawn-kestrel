"""
Secrets Scanner Agent for FSM-based Security Review.

This module provides a specialized agent for detecting hardcoded secrets in code:
- Uses ToolExecutor to run bandit for secret detection
- Implements pattern matching via grep as fallback
- Handles bandit output normalization to SecurityFinding format
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


# Common secret patterns for grep fallback
SECRET_PATTERNS = [
    # API Keys
    r"AKIA[0-9A-Z]{16}",  # AWS Access Key ID
    r"[A-Za-z0-9/+=]{40}",  # AWS Secret Access Key (approximate)
    r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API key
    r"AIza[0-9A-Za-z\-_]{35}",  # Google API key
    # Tokens
    r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*",  # Bearer tokens
    r"(?i)github_token[\s:=]+[a-zA-Z0-9]{20,}",  # GitHub tokens
    # Passwords
    r"(?i)password\s*[:=]\s*[\"']?[^\s\"']+",
    r"(?i)passwd\s*[:=]\s*[\"']?[^\s\"']+",
    r"(?i)api[_-]?key\s*[:=]\s*[\"']?[^\s\"']+",
    # Database connection strings
    r"(?i)mongodb://[^\s\"']+",
    r"(?i)postgres://[^\s\"']+",
    r"(?i)mysql://[^\s\"']+",
    # Private keys
    r"-----BEGIN PRIVATE KEY-----",
    r"-----BEGIN RSA PRIVATE KEY-----",
    r"-----BEGIN DSA PRIVATE KEY-----",
]


class SecretsScannerAgent:
    """
    Agent for detecting hardcoded secrets in code.

    This agent uses tool-based detection only (no AI-based detection):
    1. Primary: Run bandit with hardcoded secrets checks
    2. Fallback: Use grep with secret patterns
    3. Normalize all outputs to SecurityFinding format

    Returns SubagentTask-compatible result with findings and summary.
    """

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        llm_client: Optional["LLMClient"] = None,
    ):
        """Initialize SecretsScannerAgent.

        Args:
            tool_executor: ToolExecutor for running bandit and grep.
                         If None, creates a new instance.
            llm_client: LLMClient for potential LLM-based analysis.
                       Currently not used, kept for future enhancement.
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.llm_client = llm_client
        self.logger = logger

    def execute(self, repo_root: str, files: Optional[List[str]] = None) -> SubagentTask:
        """
        Execute secret scanning on the given repository.

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional). If None, scans all Python files.

        Returns:
            SubagentTask with findings and summary
        """
        self.logger.info("[SECRET_SCANNER] Starting secret detection scan...")

        # Collect findings from all methods
        all_findings: List[SecurityFinding] = []

        # Primary: Use bandit for secret detection
        bandit_findings = self._scan_with_bandit(repo_root, files)
        all_findings.extend(bandit_findings)

        # Fallback: Use grep for pattern matching if bandit found nothing or failed
        if not bandit_findings:
            self.logger.info("[SECRET_SCANNER] No findings from bandit, using grep fallback...")
            grep_findings = self._scan_with_grep(repo_root, files)
            all_findings.extend(grep_findings)
        else:
            self.logger.info(
                f"[SECRET_SCANNER] Bandit found {len(bandit_findings)} findings, skipping grep"
            )

        # Convert findings to dict format for SubagentTask result
        findings_data = []
        for finding in all_findings:
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
            f"Secret scan completed. Found {len(all_findings)} potential secrets. "
            f"Used bandit for primary detection."
        )

        self.logger.info(f"[SECRET_SCANNER] {summary}")

        # Return SubagentTask result
        return SubagentTask(
            task_id="secret_scanner_task",
            todo_id="todo_secret_scanner",
            description="Scan for hardcoded secrets and credentials",
            agent_name="secret_scanner",
            prompt="Scan for secrets",
            tools=["bandit", "grep"],
            result={
                "findings": findings_data,
                "summary": summary,
            },
        )

    def _scan_with_bandit(
        self, repo_root: str, files: Optional[List[str]] = None
    ) -> List[SecurityFinding]:
        """
        Scan for secrets using bandit.

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional)

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[SECRET_SCANNER] Scanning with bandit...")

        # Build bandit arguments
        args = [
            "-f",
            "json",  # JSON output format
            "-r",
            repo_root,  # Recursive scan
        ]

        # Add specific files if provided
        if files:
            # Filter to Python files only (bandit only checks Python)
            python_files = [f for f in files if f.endswith(".py")]
            if python_files:
                args = python_files  # Scan only specified files
            else:
                self.logger.warning(
                    "[SECRET_SCANNER] No Python files in file list, skipping bandit"
                )
                return []

        # Run bandit via ToolExecutor
        # Focus on hardcoded secrets tests (B105: hard-coded password string)
        bandit_args = args + ["-t", "B105"]  # Only check for hardcoded secrets

        result = self.tool_executor.execute_tool(tool_name="bandit", args=bandit_args, timeout=30)

        if not result.success:
            self.logger.warning(f"[SECRET_SCANNER] Bandit execution failed: {result.error_message}")
            # Don't return error findings - this is a tool issue, not a security issue
            return []

        # Use normalized findings from ToolExecutor
        return result.findings

    def _scan_with_grep(
        self, repo_root: str, files: Optional[List[str]] = None
    ) -> List[SecurityFinding]:
        """
        Scan for secrets using grep pattern matching (fallback).

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional)

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[SECRET_SCANNER] Scanning with grep fallback...")

        all_findings: List[SecurityFinding] = []

        # Build file list for grep
        if files:
            grep_files = files
        else:
            # Scan common source file types
            grep_files = []
            for root, dirs, filenames in os.walk(repo_root):
                # Skip hidden directories and common non-code directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "__pycache__", "venv", ".venv"]
                ]
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in [".py", ".js", ".ts", ".java", ".go", ".rb", ".php"]:
                        grep_files.append(os.path.join(root, filename))

        # Scan each file for each pattern
        for pattern in SECRET_PATTERNS:
            grep_args = [
                "-n",  # Show line numbers
                "-E",  # Extended regex
                pattern,
            ] + grep_files

            result = self.tool_executor.execute_tool(tool_name="grep", args=grep_args, timeout=30)

            if result.success and result.findings:
                all_findings.extend(result.findings)

        self.logger.info(f"[SECRET_SCANNER] Grep found {len(all_findings)} findings")

        return all_findings
