"""Performance & Reliability Review Subagent."""
from __future__ import annotations
from typing import List

import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Finding,
    MergeGate,
)
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings
import uuid

PERFORMANCE_SYSTEM_PROMPT = """You are the Performance & Reliability Review Subagent.

Use this shared behavior:
- If changed_files or diff are missing, request them.
- Focus on hot paths, IO amplification, retries, timeouts, concurrency hazards.
- Propose minimal checks first; escalate if core systems changed.

Specialize in:
- complexity regressions (O(n^2), unbounded loops)
- IO amplification (extra queries/reads)
- retry/backoff/timeouts correctness
- concurrency hazards (async misuse, shared mutable state)
- memory/cpu hot paths, caching correctness
- failure modes and graceful degradation

Relevant changes:
- loops, batching, pagination, retries
- network clients, DB access, file IO
- orchestration changes, parallelism, caching

Checks you may request:
- targeted benchmarks (if repo has them)
- profiling hooks or smoke run command
- unit tests for retry/timeout behavior

Blocking:
- infinite/unbounded retry risk
- missing timeouts on network calls in critical paths
- concurrency bugs with shared mutable state

Return JSON with agent="performance" using the standard schema.
Return JSON only."""


class PerformanceReliabilityReviewer(BaseReviewerAgent):
    """Reviewer agent for performance and reliability checks.

    Checks for:
    - Code complexity (nested loops, deep nesting, cyclomatic complexity)
    - IO amplification (N+1 database queries, excessive API calls in loops)
    - Retry logic (exponential backoff, proper retry policies)
    - Concurrency issues (race conditions, missing locks, shared state)
    """

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "performance"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer."""
        return PERFORMANCE_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return [
            "**/*.py",
            "**/*.rs",
            "**/*.go",
            "**/*.js",
            "**/*.ts",
            "**/*.tsx",
            "**/config/**",
            "**/database/**",
            "**/db/**",
            "**/network/**",
            "**/api/**",
            "**/services/**",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform performance and reliability review on the given context using LLM.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with performance findings, severity, and merge gate decision

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
            slug="performance-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Performance Review",
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

Please analyze the above changes for performance and reliability issues and provide your review in the specified JSON format."""

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

