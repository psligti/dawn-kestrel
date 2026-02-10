"""
Dependency Auditor Agent for FSM-based Security Review.

This module provides a specialized agent for checking dependency vulnerabilities:
- Uses ToolExecutor to run safety or pip-audit
- Handles dependency vulnerability checking
- Normalizes safety/pip-audit output to SecurityFinding format
- Returns SubagentTask-compatible results

Security notes:
- NEVER uses shell=True with user input (from napkin)
- Always uses shell=False with list arguments
- Python 3.9 compatible (uses typing.Optional[T] instead of T | None)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.tools import ToolExecutor


logger = logging.getLogger(__name__)


class DependencyAuditorAgent:
    """
    Agent for checking dependency vulnerabilities in Python packages.

    This agent uses tool-based detection only (no AI-based detection):
    1. Primary: Run safety for vulnerability scanning
    2. Fallback: Use pip-audit if safety is not available
    3. Normalize all outputs to SecurityFinding format

    Returns SubagentTask-compatible result with findings and summary.
    """

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        """Initialize DependencyAuditorAgent.

        Args:
            tool_executor: ToolExecutor for running safety and pip-audit.
                         If None, creates a new instance.
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.logger = logger

    def execute(self, repo_root: str, files: Optional[List[str]] = None) -> SubagentTask:
        """
        Execute dependency vulnerability checking on given repository.

        Args:
            repo_root: Path to repository root
            files: List of files to check (optional). Not used for dependency checks
                    since dependencies are in requirements.txt or pyproject.toml.

        Returns:
            SubagentTask with findings and summary
        """
        self.logger.info("[DEPENDENCY_AUDITOR] Starting dependency vulnerability scan...")

        # Collect findings from all methods
        all_findings: List[SecurityFinding] = []

        # Primary: Use safety for vulnerability scanning
        safety_findings = self._scan_with_safety(repo_root)
        all_findings.extend(safety_findings)

        # Fallback: Use pip-audit if safety found nothing or failed
        if not safety_findings:
            self.logger.info("[DEPENDENCY_AUDITOR] No findings from safety, trying pip-audit...")
            pip_audit_findings = self._scan_with_pip_audit(repo_root)
            all_findings.extend(pip_audit_findings)
        else:
            self.logger.info(
                f"[DEPENDENCY_AUDITOR] Safety found {len(safety_findings)} findings, skipping pip-audit"
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
            f"Dependency vulnerability scan completed. Found {len(all_findings)} "
            f"vulnerable dependencies. Used safety for primary detection."
        )

        self.logger.info(f"[DEPENDENCY_AUDITOR] {summary}")

        # Return SubagentTask result
        return SubagentTask(
            task_id="dependency_auditor_task",
            todo_id="todo_dependency_auditor",
            description="Check for dependency vulnerabilities",
            agent_name="dependency_auditor",
            prompt="Check for dependency vulnerabilities",
            tools=["safety", "pip-audit"],
            result={
                "findings": findings_data,
                "summary": summary,
            },
        )

    def _scan_with_safety(self, repo_root: str) -> List[SecurityFinding]:
        """
        Scan for dependency vulnerabilities using safety.

        Args:
            repo_root: Path to repository root

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[DEPENDENCY_AUDITOR] Scanning with safety...")

        # Build safety arguments
        # Check requirements.txt, pyproject.toml, setup.py
        args = [
            "check",
            "--json",  # JSON output format for normalization
        ]

        # Run safety via ToolExecutor
        result = self.tool_executor.execute_tool(tool_name="safety", args=args, timeout=30)

        if not result.success:
            self.logger.warning(
                f"[DEPENDENCY_AUDITOR] Safety execution failed: {result.error_message}"
            )
            # Don't return error findings - this is a tool issue, not a security issue
            return []

        # Use normalized findings from ToolExecutor
        return result.findings

    def _scan_with_pip_audit(self, repo_root: str) -> List[SecurityFinding]:
        """
        Scan for dependency vulnerabilities using pip-audit (fallback).

        Args:
            repo_root: Path to repository root

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[DEPENDENCY_AUDITOR] Scanning with pip-audit fallback...")

        # Build pip-audit arguments
        args = [
            "--format",
            "json",  # JSON output format for normalization
        ]

        # Run pip-audit via ToolExecutor
        result = self.tool_executor.execute_tool(tool_name="pip-audit", args=args, timeout=30)

        if not result.success:
            self.logger.warning(
                f"[DEPENDENCY_AUDITOR] pip-audit execution failed: {result.error_message}"
            )
            return []

        # Use normalized findings from ToolExecutor
        return result.findings
