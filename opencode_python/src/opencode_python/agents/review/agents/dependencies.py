"""Dependency & License Review Subagent implementation."""
from __future__ import annotations

from typing import List
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    MergeGate,
)
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings
import uuid


DEPENDENCY_SYSTEM_PROMPT = """You are the Dependency & License Review Subagent.

Use this shared behavior:
- If dependency changes are present but file contents are missing, request dependency files and lockfiles.
- Evaluate reproducibility and audit readiness.

Focus:
- new deps added, version bumps, loosened pins
- supply chain risk signals (typosquatting, untrusted packages)
- license compatibility (if enforced)
- build reproducibility (lockfile consistency)

Relevant files:
- pyproject.toml, requirements*.txt, poetry.lock, uv.lock
- CI dependency steps

Checks you may request:
- pip-audit / poetry audit / uv audit
- license checker if repo uses it
- lockfile diff sanity checks

Severity:
- critical/blocking for risky dependency introduced without justification
- critical if pins loosened causing non-repro builds
- warning for safe bumps but missing notes

Return JSON with agent="dependency_license" using the standard schema.
Return JSON only."""


class DependencyLicenseReviewer(BaseReviewerAgent):
    """Reviewer agent for dependency and license compliance."""

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "dependencies"

    def get_system_prompt(self) -> str:
        """Return the system prompt for the dependency reviewer."""
        return DEPENDENCY_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns relevant to dependency review."""
        return [
            "pyproject.toml",
            "requirements*.txt",
            "requirements.txt",
            "setup.py",
            "Pipfile",
            "poetry.lock",
            "uv.lock",
            "setup.cfg",
            "tox.ini",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform dependency and license review using LLM.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision

        Raises:
            ValueError: If API key is missing or invalid
            TimeoutError: If LLM request times out
            Exception: For other API-related errors
        """
        relevant_files = []
        for file_path in context.changed_files:
            if self.is_relevant_to_changes([file_path]):
                relevant_files.append(file_path)

        if not relevant_files:
            return ReviewOutput(
                agent=self.get_agent_name(),
                summary="No dependency files changed - review not applicable",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    reasoning="No dependency configuration files in changes",
                ),
                merge_gate=MergeGate(decision="approve"),
            )

        provider_id = settings.provider_default
        model = settings.model_default
        api_key = settings.api_key.get_secret_value() if settings.api_key else None

        session = Session(
            id=str(uuid.uuid4()),
            slug="dependency-license-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Dependency & License Review",
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

Please analyze the above changes for dependency and license issues and provide your review in the specified JSON format."""

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

