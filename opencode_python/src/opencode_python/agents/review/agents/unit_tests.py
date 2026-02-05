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
from opencode_python.core.harness import SimpleReviewAgentRunner

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
        """Perform unit test review on given context using SimpleReviewAgentRunner.

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

        system_prompt = self.get_system_prompt()
        formatted_context = self.format_inputs_for_prompt(context)

        user_message = f"""{system_prompt}

{formatted_context}

Please analyze the above changes for unit test quality and provide your review in specified JSON format."""

        logger.info(f"[unit_tests] Prompt construction complete:")
        logger.info(f"[unit_tests]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[unit_tests]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[unit_tests]   Full user_message: {len(user_message)} chars")
        logger.info(f"[unit_tests]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="unit_tests")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[unit_tests] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[unit_tests] JSON validation successful!")
            logger.info(f"[unit_tests]   agent: {output.agent}")
            logger.info(f"[unit_tests]   severity: {output.severity}")
            logger.info(f"[unit_tests]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[unit_tests] JSON validation error: {e}")
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
        except (TimeoutError, ValueError):
            raise
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}") from e
