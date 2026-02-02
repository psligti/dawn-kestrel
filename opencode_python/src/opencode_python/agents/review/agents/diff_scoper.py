"""Diff Scoper Subagent - pre-pass reviewer for diff risk classification and routing."""
from __future__ import annotations
from typing import List
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    MergeGate,
    Finding,
)
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings
import uuid


_SYSTEM_PROMPT = """You are the Diff Scoper Subagent.

Use this shared behavior:
- If changed_files or diff are missing, request them.
- Summarize change intent and classify risk.
- Route attention to which other subagents matter most.
- Propose minimal checks to run first.

Goal:
- Summarize what changed in 5–10 bullets.
- Classify risk: low/medium/high.
- Produce a routing table: which subagents are most relevant and why.
- Propose the minimal set of checks to run first.

Return JSON with agent="diff_scoper" using the standard schema.
In merge_gate.notes_for_coding_agent include:
- "routing": { "architecture": "...", "security": "...", ... }
- "risk rationale"
Return JSON only."""


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
        return _SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to.

        Diff scoper is relevant to all files since it analyzes overall change scope.
        """
        return ["**/*"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform review on the given context using LLM.

        Analyzes the git diff to classify risk and route attention to appropriate subagents.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with risk classification, routing findings, and merge gate decision

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
            slug="diff-scoper-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Diff Scoper Review",
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

Please analyze the above changes for diff scoping and provide your review in the specified JSON format."""

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
