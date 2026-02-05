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
from opencode_python.core.harness import SimpleReviewAgentRunner

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
        """Perform linting review on given context using SimpleReviewAgentRunner.

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

        system_prompt = self.get_system_prompt()
        formatted_context = self.format_inputs_for_prompt(context)

        user_message = f"""{system_prompt}

{formatted_context}

Please analyze the above changes for linting and style issues and provide your review in specified JSON format."""

        logger.info(f"[linting] Prompt construction complete:")
        logger.info(f"[linting]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[linting]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[linting]   Full user_message: {len(user_message)} chars")
        logger.info(f"[linting]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="linting")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[linting] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[linting] JSON validation successful!")
            logger.info(f"[linting]   agent: {output.agent}")
            logger.info(f"[linting]   severity: {output.severity}")
            logger.info(f"[linting]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[linting] JSON validation error: {e}")
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
