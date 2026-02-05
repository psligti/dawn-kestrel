"""TelemetryMetricsReviewer - checks for logging quality and observability coverage."""
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
        return f"""You are the Telemetry & Metrics Review Subagent.

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

{get_review_output_schema()}

Your agent name is "telemetry"."""

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
        """Perform telemetry review on given context using SimpleReviewAgentRunner.

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

Please analyze the above changes for telemetry and logging issues and provide your review in the specified JSON format."""

        logger.info(f"[telemetry] Prompt construction complete:")
        logger.info(f"[telemetry]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[telemetry]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[telemetry]   Full user_message: {len(user_message)} chars")
        logger.info(f"[telemetry]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="telemetry")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[telemetry] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[telemetry] JSON validation successful!")
            logger.info(f"[telemetry]   agent: {output.agent}")
            logger.info(f"[telemetry]   severity: {output.severity}")
            logger.info(f"[telemetry]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[telemetry] JSON validation error: {e}")
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

