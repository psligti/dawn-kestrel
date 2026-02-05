"""Linting and Style Review Subagent."""
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
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings
import uuid

logger = logging.getLogger(__name__)

class LintingReviewer(BaseReviewerAgent):
    """Reviewer agent for linting, formatting, and code quality checks.

    This agent uses LLM-based analysis to detect:
    - Formatting issues (indentation, line length)
    - Lint adherence (PEP8 violations, style issues)
    - Type hints coverage (missing type annotations)
    - Code quality smells (unused imports, dead code)
    """

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "linting"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer."""
        return f"""You are the Linting & Style Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to lint/style.
- Propose minimal changed-files-only lint commands first.
- If changed_files or diff are missing, request them.
- Discover repo conventions (ruff/black/flake8/isort, format settings in pyproject).

You specialize in:
- formatting and lint adherence
- import hygiene, unused vars, dead code
- type hints sanity (quality, not architecture)
- consistency with repo conventions
- correctness smells (shadowing, mutable defaults)

Relevant changes:
- any Python source changes (*.py)
- lint config changes (pyproject.toml, ruff.toml, etc.)

Checks you may request:
- ruff check <changed_files>
- ruff format <changed_files>
- formatter/linter commands used by the repo
- type check if enforced (only when relevant)

Severity:
- warning: minor style issues
- critical: new lint violations likely failing CI
- blocking: syntax errors, obvious correctness issues, format prevents CI merge

{get_review_output_schema()}

Your agent name is "linting"."""

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return [
            "**/*.py",
            "*.json",
            "*.toml",
            "*.yaml",
            "*.yml",
            "pyproject.toml",
            "ruff.toml",
            ".flake8",
            "setup.cfg",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform linting review on the given context using LLM.

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
                agent="linting",
                summary="No Python or lint config files changed. Linting review not applicable.",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    reasoning="No relevant files for linting review",
                ),
                findings=[],
                merge_gate=MergeGate(
                    decision="approve",
                    must_fix=[],
                    should_fix=[],
                    notes_for_coding_agent=[
                        "No Python or lint configuration files were changed.",
                    ],
                ),
            )

        default_account = settings.get_default_account()
        if not default_account:
            raise ValueError("No default account configured. Please configure an account with is_default=True.")

        provider_id = default_account.provider_id
        model = default_account.model
        api_key_value = default_account.api_key.get_secret_value()

        session = Session(
            id=str(uuid.uuid4()),
            slug="linting-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Linting Review",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id=provider_id,
            model=model,
            api_key=api_key_value
        )

        system_prompt = self.get_system_prompt()
        formatted_context = self.format_inputs_for_prompt(context)

        user_message = f"""{system_prompt}

{formatted_context}

Please analyze the above changes for linting and style issues and provide your review in the specified JSON format."""

        max_retries = 2
        response_message = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[linting] Calling LLM (attempt {attempt + 1}/{max_retries})...")
                response_message = await ai_session.process_message(
                    user_message,
                    options={
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "response_format": {"type": "json_object"}
                    }
                )

                if not response_message.text or not response_message.text.strip():
                    if attempt < max_retries - 1:
                        logger.warning(f"[linting] Empty response from LLM, retrying ({attempt + 1}/{max_retries})...")
                        continue
                    else:
                        raise ValueError("Empty response from LLM after retries")

                logger.info(f"[linting] Got response: {len(response_message.text)} chars")
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[linting] LLM request failed, retrying ({attempt + 1}/{max_retries}): {e}")
                    continue
                raise

        if not response_message or not response_message.text:
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
