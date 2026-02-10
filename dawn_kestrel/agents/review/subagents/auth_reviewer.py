"""
Auth Reviewer Agent for FSM-based Security Review.

This module provides a specialized agent for authentication code review:
- Uses LLM for JWT/OAuth validation pattern analysis
- Uses grep/ast-grep for auth-specific patterns (missing exp check, hardcoded tokens)
- Combines LLM analysis with tool-based verification
- Returns SubagentTask-compatible results

Security notes:
- NEVER uses shell=True with user input (from napkin)
- Always uses shell=False with list arguments
- Python 3.9 compatible (uses typing.Optional[T] instead of T | None)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.tools import ToolExecutor
from dawn_kestrel.llm import LLMClient, LLMRequestOptions
from dawn_kestrel.providers.base import ProviderID


logger = logging.getLogger(__name__)


# Auth-specific patterns for grep/ast-grep
AUTH_PATTERNS = [
    # JWT decode without verify
    r"jwt\.decode\(",
    # JWT decode with verify=False
    r"jwt\.decode\([^,]*verify=False",
    # Missing exp check in JWT
    r"jwt\.decode\([^)]*\)[^)]*exp",
    # Hardcoded JWT tokens
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    # OAuth access tokens
    r"(?i)access_token\s*[:=]\s*[\"']?[A-Za-z0-9]{20,}",
    # Bearer tokens
    r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*",
    # API keys in auth code
    r"(?i)api_key\s*[:=]\s*[\"']?[A-Za-z0-9]{20,}",
    # Session tokens without validation
    r"request\.session\[.token.\]",
]


class AuthReviewerAgent:
    """
    Agent for authentication code review.

    This agent uses both LLM-based analysis and tool-based detection:
    1. LLM Analysis: Review JWT/OAuth validation patterns for security issues
    2. Tool-based: Use grep for auth-specific patterns (missing exp, hardcoded tokens)
    3. Combine both approaches for comprehensive auth code review

    Auth issues covered:
    - JWT exp check missing
    - JWT verification disabled
    - Hardcoded tokens
    - OAuth validation issues
    """

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize AuthReviewerAgent.

        Args:
            tool_executor: ToolExecutor for running grep/ast-grep.
                          If None, creates a new instance.
            llm_client: LLMClient for auth code analysis.
                       If None, creates a new instance (requires API key).
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.llm_client = llm_client
        self.logger = logger

    async def execute(
        self, repo_root: str, files: Optional[List[str]] = None, context: Optional[str] = None
    ) -> SubagentTask:
        """
        Execute authentication code review on the given repository.

        Args:
            repo_root: Path to repository root
            files: List of files to review (optional).
                    If None, reviews all supported files.
            context: Additional context (diff, changed files) for LLM analysis.

        Returns:
            SubagentTask with findings and summary
        """
        self.logger.info("[AUTH_REVIEWER] Starting authentication code review...")

        # Collect findings from all methods
        all_findings: List[SecurityFinding] = []

        # Tool-based: Use grep for auth pattern detection
        grep_findings = await self._scan_with_grep(repo_root, files)
        all_findings.extend(grep_findings)

        # LLM-based: Analyze auth code patterns for JWT/OAuth validation
        llm_findings = []
        if self.llm_client:
            llm_findings = await self._analyze_with_llm(repo_root, files, context)
            all_findings.extend(llm_findings)
        else:
            self.logger.warning(
                "[AUTH_REVIEWER] No LLM client provided, skipping LLM-based analysis"
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
            f"Auth code review completed. Found {len(all_findings)} authentication issues. "
            f"Used grep for pattern detection"
            + (", LLM for JWT/OAuth validation analysis" if self.llm_client else "")
            + "."
        )

        self.logger.info(f"[AUTH_REVIEWER] {summary}")

        # Return SubagentTask result
        return SubagentTask(
            task_id="auth_reviewer_task",
            todo_id="todo_auth_reviewer",
            description="Review authentication code for JWT/OAuth validation issues",
            agent_name="auth_reviewer",
            prompt="Review authentication code",
            tools=["grep"] + (["llm"] if self.llm_client else []),
            result={
                "findings": findings_data,
                "summary": summary,
            },
        )

    async def _scan_with_grep(
        self, repo_root: str, files: Optional[List[str]] = None
    ) -> List[SecurityFinding]:
        """
        Scan for auth patterns using grep.

        Args:
            repo_root: Path to repository root
            files: List of files to scan (optional)

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[AUTH_REVIEWER] Scanning with grep for auth patterns...")

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
                    and d not in ["node_modules", "__pycache__", "venv", ".venv", "dist", "build"]
                ]
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php"]:
                        grep_files.append(os.path.join(root, filename))

        # Scan each file for each pattern
        for pattern in AUTH_PATTERNS:
            grep_args = [
                "-n",  # Show line numbers
                "-E",  # Extended regex
                pattern,
            ] + grep_files

            result = self.tool_executor.execute_tool(tool_name="grep", args=grep_args, timeout=30)

            if result.success and result.findings:
                all_findings.extend(result.findings)

        self.logger.info(f"[AUTH_REVIEWER] Grep found {len(all_findings)} auth pattern findings")

        return all_findings

    async def _analyze_with_llm(
        self, repo_root: str, files: Optional[List[str]] = None, context: Optional[str] = None
    ) -> List[SecurityFinding]:
        """
        Analyze authentication code using LLM for JWT/OAuth validation issues.

        Args:
            repo_root: Path to repository root
            files: List of files to analyze (optional)
            context: Additional context for analysis (diff, changed files)

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info("[AUTH_REVIEWER] Analyzing with LLM for JWT/OAuth validation...")

        # Build file context for LLM
        if files:
            files_str = ", ".join(files[:20])  # Limit to first 20 files
            if len(files) > 20:
                files_str += f" ... and {len(files) - 20} more"
        else:
            files_str = "All files in repository"

        context_str = context or "No additional context provided"

        # Build prompt for LLM
        prompt = f"""You are a security code reviewer specializing in authentication and authorization.

Your task is to review authentication code for JWT (JSON Web Token) and OAuth validation issues.

FILES TO REVIEW:
{files_str}

ADDITIONAL CONTEXT:
{context_str}

ANALYSIS TASK:
Review the code for the following authentication security issues:

1. JWT Issues:
   - Missing exp (expiration) check in JWT validation
   - JWT decode with verify=False or algorithms=None
   - Missing signature verification
   - Using weak algorithms (none, HS256 with hardcoded secrets)

2. OAuth Issues:
   - Missing token validation before use
   - Hardcoded OAuth client secrets or tokens
   - Token reuse without revocation checks
   - Missing PKCE (Proof Key for Code Exchange) for public clients

3. General Auth Issues:
   - Hardcoded API keys or tokens
   - Session token validation bypass
   - Authorization header parsing issues

OUTPUT FORMAT:
Return findings as a JSON object with:
{{
  "findings": [
    {{
      "id": "unique_id",
      "severity": "critical|high|medium|low",
      "title": "Short descriptive title",
      "description": "Detailed description of the security issue",
      "evidence": "Code snippet or pattern matched",
      "file_path": "path/to/file",
      "line_number": 123,
      "recommendation": "How to fix the issue",
      "requires_review": true/false
    }}
  ],
  "summary": "Brief summary of auth code review"
}}

Be thorough. Report ALL potential issues, even low-severity ones.
If no issues found, return an empty findings array with an appropriate summary.
"""

        try:
            # Call LLM
            response = await self.llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                options=LLMRequestOptions(
                    temperature=0.3,  # Lower temperature for more deterministic results
                    max_tokens=2000,
                ),
            )

            # Parse LLM response
            import json

            try:
                llm_result = json.loads(response.text)
                findings_data = llm_result.get("findings", [])
                summary = llm_result.get("summary", "LLM analysis completed")

                # Convert to SecurityFinding objects
                findings = []
                for f in findings_data:
                    finding = SecurityFinding(
                        id=f.get("id", "llm_auth_001"),
                        severity=f.get("severity", "medium"),
                        title=f.get("title", "Auth code issue"),
                        description=f.get("description", ""),
                        evidence=f.get("evidence", ""),
                        file_path=f.get("file_path"),
                        line_number=f.get("line_number"),
                        recommendation=f.get("recommendation"),
                        requires_review=f.get("requires_review", True),
                        confidence_score=0.75,  # LLM-based confidence
                    )
                    findings.append(finding)

                self.logger.info(f"[AUTH_REVIEWER] LLM found {len(findings)} auth issues")
                return findings

            except json.JSONDecodeError as e:
                self.logger.warning(f"[AUTH_REVIEWER] Failed to parse LLM response as JSON: {e}")
                self.logger.debug(f"[AUTH_REVIEWER] LLM response: {response.text[:500]}")
                return []

        except Exception as e:
            self.logger.warning(f"[AUTH_REVIEWER] LLM analysis failed: {e}")
            return []
