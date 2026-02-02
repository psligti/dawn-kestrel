"""TelemetryMetricsReviewer - checks for logging quality and observability coverage."""
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


TELEMETRY_SYSTEM_PROMPT = """You are the Telemetry & Metrics Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to observability.
- Propose minimal targeted checks; escalate when failure modes are introduced.
- If changed_files or diff are missing, request them.
- Discover repo conventions (logging frameworks, metrics libs, tracing setup).

You specialize in:
- logging quality (structured logs, levels, correlation IDs)
- tracing spans / propagation (if applicable)
- metrics: counters/gauges/histograms, cardinality control
- error reporting: meaningful errors, no sensitive data
- observability coverage of new workflows and failure modes
- performance signals: timing, retries, rate limits, backoff

Relevant changes:
- new workflows, background jobs, pipelines, orchestration
- network calls, IO boundaries, retry logic, timeouts
- error handling changes, exception mapping

Checks you may request:
- log format checks (if repo has them)
- smoke run command to ensure logs/metrics emitted (if available)
- grep for logger usage & secrets leakage

Blocking:
- secrets/PII likely logged
- critical path introduced with no error logging/metrics
- retry loops without visibility or limits (runaway risk)
- high-cardinality metric labels introduced

Output MUST be valid JSON only with agent="telemetry_metrics" and the standard schema.
Return JSON only."""


class TelemetryMetricsReviewer(BaseReviewerAgent):
    """Telemetry reviewer agent that checks for logging quality and observability coverage.

    This agent specializes in detecting:
    - Logging quality (proper log levels, structured logging)
    - Error reporting (exceptions raised with context)
    - Observability coverage (metrics, traces, distributed tracing)
    - Silent failures (swallowed exceptions)
    """

    def get_agent_name(self) -> str:
        """Return the agent identifier."""
        return "telemetry"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the telemetry reviewer."""
        return TELEMETRY_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns relevant to telemetry review."""
        return [
            "**/*.py",
            "**/logging/**",
            "**/observability/**",
            "**/metrics/**",
            "**/tracing/**",
            "**/monitoring/**",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform telemetry review on the given context using LLM.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with telemetry findings, severity, and merge gate decision

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
            slug="telemetry-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Telemetry Review",
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

Please analyze the above changes for telemetry and observability issues and provide your review in the specified JSON format."""

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
