"""Performance & Reliability Review Subagent."""
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
        return f"""You are the Performance & Reliability Review Subagent.

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

{get_review_output_schema()}

Your agent name is "performance"."""

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
        """Perform performance review on given context using SimpleReviewAgentRunner.

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

Please analyze the above changes for performance and reliability issues and provide your review in the specified JSON format."""

        logger.info(f"[performance] Prompt construction complete:")
        logger.info(f"[performance]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[performance]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[performance]   Full user_message: {len(user_message)} chars")
        logger.info(f"[performance]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="performance")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[performance] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[performance] JSON validation successful!")
            logger.info(f"[performance]   agent: {output.agent}")
            logger.info(f"[performance]   severity: {output.severity}")
            logger.info(f"[performance]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[performance] JSON validation error: {e}")
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

