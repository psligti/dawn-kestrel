"""Diff Scoper Subagent - pre-pass reviewer for diff risk classification and routing."""
from __future__ import annotations
from typing import List
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    MergeGate,
    get_review_output_schema,
)
from opencode_python.core.harness import SimpleReviewAgentRunner



class DiffScoperReviewer(BaseReviewerAgent):
    """Pre-pass reviewer that classifies diff risk and routes attention to appropriate subagents.

    This agent runs early in the review pipeline to:
    1. Analyze the git diff to identify scope and magnitude of changes
    2. Classify risk level (high/medium/low) based on multiple factors
    3. Route attention findings to appropriate specialized reviewers
    4. Suggest minimal checks to run first for quick feedback
    """

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "diff_scoper"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer agent."""
        return f"""You are the Diff Scoper Subagent.

Use this shared behavior:
- If changed_files or diff are missing, request them.
- Summarize change intent and classify risk.
- Route attention to which other subagents matter most.
- Propose minimal checks to run first.

Goal:
- Summarize what changed in 5-10 bullets.
- Classify risk: low/medium/high.
- Produce a routing table: which subagents are most relevant and why.
- Propose minimal set of checks to run first.

{get_review_output_schema()}

Your agent name is "diff_scoper".

IMPORTANT: In merge_gate.notes_for_coding_agent, include:
- "routing": {{"architecture": "...", "security": "...", ...}}
- "risk rationale"

These are notes for the orchestrator, not blocking issues."""

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to.

        Diff scoper is relevant to all files since it analyzes overall change scope.
        """
        return ["**/*"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform diff_scoper review on given context using SimpleReviewAgentRunner.

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

Please analyze the above changes for diff scoping issues and provide your review in the specified JSON format."""

        logger.info(f"[diff_scoper] Prompt construction complete:")
        logger.info(f"[diff_scoper]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[diff_scoper]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[diff_scoper]   Full user_message: {len(user_message)} chars")
        logger.info(f"[diff_scoper]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="diff_scoper")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[diff_scoper] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[diff_scoper] JSON validation successful!")
            logger.info(f"[diff_scoper]   agent: {output.agent}")
            logger.info(f"[diff_scoper]   severity: {output.severity}")
            logger.info(f"[diff_scoper]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[diff_scoper] JSON validation error: {e}")
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

