"""Security Review Subagent - checks for security vulnerabilities."""
from __future__ import annotations
from typing import List
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Finding,
    MergeGate,
)
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings
import uuid


SECURITY_SYSTEM_PROMPT = """You are the Security Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to security.
- Propose minimal targeted checks first; escalate if risk is high.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pyproject.toml, CI workflows, audit tools) to propose correct commands.

You specialize in:
- secrets handling (keys/tokens/passwords), logging of sensitive data
- authn/authz, permission checks, RBAC
- injection risks: SQL injection, command injection, template injection
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

Output MUST be valid JSON only with agent="security" and the standard schema.
Return JSON only."""


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
        """Return the agent identifier."""
        return "security"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the security reviewer."""
        return SECURITY_SYSTEM_PROMPT

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

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform security review on the given context using LLM.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with security findings, severity, and merge gate decision

        Raises:
            ValueError: If API key is missing or invalid
            TimeoutError: If LLM request times out
            Exception: For other API-related errors
        """
        relevant_files = []
        for file_path in context.changed_files:
            if self.is_relevant_to_changes([file_path]):
                relevant_files.append(file_path)

        provider_id = settings.provider_default
        model = settings.model_default
        api_key = settings.api_key.get_secret_value() if settings.api_key else None

        session = Session(
            id=str(uuid.uuid4()),
            slug="security-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Security Review",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id=provider_id,
            model=model,
            api_key=api_key
        )

        system_prompt = self.get_system_prompt()
        formatted_context = self.format_inputs_for_prompt(context)

        user_message = f"""{system_prompt}

{formatted_context}

Please analyze the above changes for security vulnerabilities and provide your review in the specified JSON format."""

        try:
            response_message = await ai_session.process_message(
                user_message,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            )

            if not response_message.text:
                raise ValueError("Empty response from LLM")

            try:
                output = ReviewOutput.model_validate_json(response_message.text)
            except pd.ValidationError as e:
                return ReviewOutput(
                    agent=self.get_agent_name(),
                    summary=f"Error parsing LLM response: {str(e)}",
                    severity="critical",
                    scope=Scope(
                        relevant_files=relevant_files,
                        ignored_files=[],
                        reasoning="Failed to parse LLM JSON response due to validation error."
                    ),
                    findings=[],
                    merge_gate=MergeGate(
                        decision="needs_changes",
                        must_fix=[],
                        should_fix=[],
                        notes_for_coding_agent=[
                            "Review LLM response format and ensure it matches expected schema."
                        ]
                    )
                )

            return output

        except (TimeoutError, Exception) as e:
            if isinstance(e, (TimeoutError, ValueError)):
                raise
            raise Exception(f"LLM API error: {str(e)}") from e

