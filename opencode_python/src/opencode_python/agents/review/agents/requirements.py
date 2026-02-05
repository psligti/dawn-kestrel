"""Requirements reviewer subagent for comparing implementation to ticket/PR description."""
from __future__ import annotations
from typing import List
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Scope, MergeGate


REQUIREMENTS_SYSTEM_PROMPT = """You are the Requirements Review Subagent.

Use this shared behavior:
- If diff is missing, request it.
- If no ticket/pr description is provided, request it OR proceed by extracting implied requirements from code changes and mark confidence lower.
- Compare stated requirements and acceptance criteria to what was implemented.

Goal:
Confirm the change matches stated requirements and acceptance criteria.

Inputs may include:
- ticket_description or pr_description
- acceptance_criteria
- changed_files
- diff

What to do:
1) Extract explicit/implied requirements from description/criteria.
2) Check the diff implements them.
3) Identify gaps, scope creep, ambiguous behavior.
4) Ensure error cases and edge cases are covered or flagged.

Severity:
- warning: minor mismatch or missing note
- critical: core requirement not met or contradicts requirement
- blocking: change does the wrong thing / breaks a requirement / unsafe default

Return JSON with agent="requirements" using the standard schema.
Return JSON only."""


class RequirementsReviewer(BaseReviewerAgent):
    """Reviewer agent that compares implementation to ticket/PR description."""

    def get_agent_name(self) -> str:
        """Return the name of this reviewer agent."""
        return "requirements"

    def get_system_prompt(self) -> str:
        """Get the system prompt for this reviewer agent."""
        return REQUIREMENTS_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns this reviewer is relevant to."""
        return ["**/*"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform requirements review on given context using SimpleReviewAgentRunner.

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

Please analyze the above changes for requirement changes and provide your review in the specified JSON format."""

        logger.info(f"[requirements] Prompt construction complete:")
        logger.info(f"[requirements]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[requirements]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[requirements]   Full user_message: {len(user_message)} chars")
        logger.info(f"[requirements]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="requirements")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[requirements] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[requirements] JSON validation successful!")
            logger.info(f"[requirements]   agent: {output.agent}")
            logger.info(f"[requirements]   severity: {output.severity}")
            logger.info(f"[requirements]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[requirements] JSON validation error: {e}")
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

