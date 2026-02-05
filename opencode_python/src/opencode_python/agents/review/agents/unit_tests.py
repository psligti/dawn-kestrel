"""Unit Tests Reviewer agent for checking test quality and adequacy."""
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


class UnitTestsReviewer(BaseReviewerAgent):
    """Reviewer agent specialized in unit test quality and adequacy.

    Checks for:
    - Test adequacy (cover changed behavior)
    - Test correctness (assertions, mocking)
    - Edge case coverage (boundary values, error conditions)
    - Determinism (randomness, time dependencies, state leakage)
    """

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer agent."""
        return f"""You are the Unit Test Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to unit tests.
- Propose minimal targeted test selection first; escalate if risk is high.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pytest, nox/tox, uv run, test layout).

You specialize in:
- adequacy of tests for changed behavior
- correctness of tests (assertions, determinism, fixtures)
- edge case and failure mode coverage
- avoiding brittle tests (time, randomness, network)
- selecting minimal test runs to validate change

Relevant changes:
- behavior changes in code
- new modules/functions/classes
- bug fixes (prefer regression tests)
- changes to test/fixture utilities, CI test steps

Checks you may request:
- pytest -q <test_file>
- pytest -q -k "<keyword>"
- pytest -q tests/unit/...
- coverage on changed modules only (if available)

Severity:
- warning: tests exist but miss an edge case
- critical: behavior changed with no tests and moderate risk
- blocking: high-risk change with no tests; broken/flaky tests introduced

{get_review_output_schema()}

Your agent name is "unit_tests"."""

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "unit_tests"

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return ["**/*.py"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform unit test review on the given context using LLM.

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

        default_account = settings.get_default_account()
        if not default_account:
            raise ValueError("No default account configured. Please configure an account with is_default=True.")

        provider_id = default_account.provider_id
        model = default_account.model
        api_key_value = default_account.api_key.get_secret_value()

        session = Session(
            id=str(uuid.uuid4()),
            slug="unit-tests-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Unit Tests Review",
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

Please analyze the above changes for unit test quality and provide your review in the specified JSON format."""

        max_retries = 2
        response_message = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[unit_tests] Calling LLM (attempt {attempt + 1}/{max_retries})...")
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
                        logger.warning(f"[unit_tests] Empty response from LLM, retrying ({attempt + 1}/{max_retries})...")
                        continue
                    else:
                        raise ValueError("Empty response from LLM after retries")

                logger.info(f"[unit_tests] Got response: {len(response_message.text)} chars")
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[unit_tests] LLM request failed, retrying ({attempt + 1}/{max_retries}): {e}")
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

        except (TimeoutError, Exception) as e:
            if isinstance(e, (TimeoutError, ValueError)):
                raise
            raise Exception(f"LLM API error: {str(e)}") from e

        return output
