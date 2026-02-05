"""Release & Changelog Review Subagent.

Reviews code changes for release hygiene including:
- CHANGELOG updates for new features
- Version bumps (major, minor, patch)
- Breaking changes documentation
- Migration guides
"""

from __future__ import annotations
from typing import List

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    MergeGate,
    get_review_output_schema,
)
from opencode_python.core.harness import SimpleReviewAgentRunner

import pydantic as pd


class ReleaseChangelogReviewer(BaseReviewerAgent):
    """Reviewer agent for release hygiene and changelog compliance."""

    def __init__(self) -> None:
        self.agent_name = "release_changelog"

    def get_agent_name(self) -> str:
        return self.agent_name

    def get_system_prompt(self) -> str:
        return f"""You are the Release & Changelog Review Subagent.

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

{get_review_output_schema()}

Your agent name is "release_changelog"."""

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
        """Perform changelog review on given context using SimpleReviewAgentRunner.

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

Please analyze the above changes for changelog completeness and provide your review in the specified JSON format."""

        logger.info(f"[changelog] Prompt construction complete:")
        logger.info(f"[changelog]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[changelog]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[changelog]   Full user_message: {len(user_message)} chars")
        logger.info(f"[changelog]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="changelog")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[changelog] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[changelog] JSON validation successful!")
            logger.info(f"[changelog]   agent: {output.agent}")
            logger.info(f"[changelog]   severity: {output.severity}")
            logger.info(f"[changelog]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[changelog] JSON validation error: {e}")
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

