"""Release & Changelog Review Subagent.

Reviews code changes for release hygiene including:
- CHANGELOG updates for new features
- Version bumps (major, minor, patch)
- Breaking changes documentation
- Migration guides
"""

from __future__ import annotations
from typing import List, Optional

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Finding,
    Scope,
    MergeGate,
    Check,
    Skip,
)
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings
import pydantic as pd
import uuid


SYSTEM_PROMPT = """You are the Release & Changelog Review Subagent.

Use this shared behavior:
- If user-visible behavior changes, ensure release hygiene artifacts are updated.
- If no changelog/versioning policy exists, note it and adjust severity.

Goal:
Ensure user-visible changes are communicated and release hygiene is maintained.

Relevant:
- CLI flags changed
- outputs changed (schemas, logs users rely on)
- breaking changes
- version bump / changelog / migration docs

Checks you may request:
- CHANGELOG presence/update
- version bump policy checks
- help text / docs updated

Severity:
- warning for missing changelog entry
- critical for breaking change without migration note

Return JSON with agent="release_changelog" using the standard schema.
Return JSON only."""


class ReleaseChangelogReviewer(BaseReviewerAgent):
    """Reviewer agent for release hygiene and changelog compliance."""

    def __init__(self) -> None:
        self.agent_name = "release_changelog"

    def get_agent_name(self) -> str:
        return self.agent_name

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        return [
            "CHANGELOG*",
            "CHANGES*",
            "HISTORY*",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "**/__init__.py",
            "**/*.py",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform changelog/release review on the given context using LLM.

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

        provider_id = settings.provider_default
        model = settings.model_default
        api_key = settings.api_key.get_secret_value() if settings.api_key else None

        session = Session(
            id=str(uuid.uuid4()),
            slug="release-changelog-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Release & Changelog Review",
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

Please analyze the above changes for release hygiene and changelog compliance and provide your review in the specified JSON format."""

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
