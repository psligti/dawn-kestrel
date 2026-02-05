"""Security Review Subagent - checks for security vulnerabilities."""
from __future__ import annotations
from typing import List
import pydantic as pd
import logging

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    MergeGate,
    get_review_output_schema,
)
from opencode_python.core.harness import SimpleReviewAgentRunner

logger = logging.getLogger(__name__)


class SecurityReviewer(BaseReviewerAgent):
    """Security reviewer agent that checks for security vulnerabilities.

    This agent specializes in detecting:
    - Secrets handling (API keys, passwords, tokens)
    - Authentication/authorization issues
    - Injection risks (SQL, XSS, command)
    - CI/CD exposures
    - Unsafe code execution patterns
    """

    def get_agent_name(self) -> str:
        """Return agent identifier."""
        return "security"

    def get_system_prompt(self) -> str:
        """Get system prompt for security reviewer."""
        return f"""You are Security Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to security.
- Propose minimal targeted checks first; escalate if risk is high.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pyproject.toml, CI workflows, audit tools) to propose correct commands.

You specialize in:
- secrets handling (keys/tokens/passwords), logging of sensitive data
- authn/authz, permission checks, RBAC
- injection risks: SQL injection, command injection, template injection, prompt injection
- SSRF, unsafe network calls, insecure defaults
- dependency/supply chain risk signals (new deps, loosened pins)
- cryptography misuse
- file/path handling, deserialization, eval/exec usage
- CI/CD exposures (tokens, permissions, workflow changes)

High-signal file patterns:
- auth/**, security/**, iam/**, permissions/**, middleware/**
- network clients, webhook handlers, request parsers
- subprocess usage, shell commands
- config files: *.yml, *.yaml (CI), Dockerfile, terraform, deploy scripts
- dependency files: pyproject.toml, requirements*.txt, poetry.lock, uv.lock

Checks you may request (when available and relevant):
- bandit (Python SAST)
- dependency audit (pip-audit / poetry audit / uv audit)
- semgrep ruleset
- grep checks: "password", "token", "secret", "AWS_", "PRIVATE_KEY"

Security review must answer:
1) Did we introduce a new trust boundary or input surface?
2) Are inputs validated and outputs encoded appropriately?
3) Are secrets handled safely (not logged, not committed, not exposed)?
4) Are permissions least-privilege and explicit?

Blocking conditions:
- plaintext secrets committed or leaked into logs
- authz bypass risk or missing permission checks
- code execution risk (eval/exec) without strong sandboxing
- command injection risk via subprocess with untrusted input
- unsafe deserialization of untrusted input

{get_review_output_schema()}

Your agent name is "security"."""

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns relevant to security review."""
        return [
            "**/*.py",
            "**/*.yml",
            "**/*.yaml",
            "**/auth*/**",
            "**/security*/**",
            "**/iam/**",
            "**/permissions/**",
            "**/middleware/**",
            "**/requirements*.txt",
            "**/pyproject.toml",
            "**/poetry.lock",
            "**/uv.lock",
            "**/Dockerfile*",
            "**/*.tf",
            "**/.github/workflows/**",
            "**/.gitlab-ci.yml",
        ]

    def get_allowed_tools(self) -> List[str]:
        """Get allowed tools for security review checks."""
        return [
            "git",
            "grep",
            "ast-grep",
            "python",
            "bandit",
            "semgrep",
            "pip-audit",
            "uv",
            "poetry",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform security review on given context using SimpleReviewAgentRunner.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with security findings, severity, and merge gate decision

        Raises:
            ValueError: If API key is missing or invalid
            TimeoutError: If LLM request times out
            Exception: For other API-related errors
        """
        logger.info(f"[security] >>> review() called")
        logger.info(f"[security]     repo_root: {context.repo_root}")
        logger.info(f"[security]     base_ref: {context.base_ref}")
        logger.info(f"[security]     head_ref: {context.head_ref}")
        logger.info(f"[security]     changed_files: {len(context.changed_files)}")
        logger.info(f"[security]     diff_size: {len(context.diff)} chars")
        logger.info(f"[security]     pr_title: {context.pr_title}")
        logger.info(f"[security]     pr_description: {len(context.pr_description) if context.pr_description else 0} chars")

        output = await self._execute_review_with_runner(
            context,
            early_return_on_no_relevance=True,
            no_relevance_summary="No security-relevant files changed. Security review not applicable.",
        )

        logger.info(f"[security] Parsed ReviewOutput:")
        logger.info(f"[security]   agent: {output.agent}")
        logger.info(f"[security]   summary: {output.summary[:100]}{'...' if len(output.summary) > 100 else ''}")
        logger.info(f"[security]   severity: {output.severity}")
        logger.info(f"[security]   findings: {len(output.findings)}")
        logger.info(f"[security]   checks: {len(output.checks)}")
        logger.info(f"[security]   skips: {len(output.skips)}")
        logger.info(f"[security]   merge_gate.decision: {output.merge_gate.decision}")

        for i, finding in enumerate(output.findings, 1):
            logger.info(f"[security]   Finding #{i}: {finding.title}")
            logger.info(f"[security]     id: {finding.id}")
            logger.info(f"[security]     severity: {finding.severity}")
            logger.info(f"[security]     confidence: {finding.confidence}")
            logger.info(f"[security]     owner: {finding.owner}")
            logger.info(f"[security]     estimate: {finding.estimate}")
            logger.debug(f"[security]     evidence: {finding.evidence[:150]}{'...' if len(finding.evidence) > 150 else ''}")
            logger.debug(f"[security]     recommendation: {finding.recommendation[:150]}{'...' if len(finding.recommendation) > 150 else ''}")

        logger.info(f"[security] <<< review() returning")
        return output
