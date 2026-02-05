"""Dependency & License Review Subagent implementation."""
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



class DependencyLicenseReviewer(BaseReviewerAgent):
    """Reviewer agent for dependency and license compliance."""

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "dependencies"

    def get_system_prompt(self) -> str:
        """Return the system prompt for the dependency reviewer."""
        return f"""You are the Dependency & License Review Subagent.

Use this shared behavior:
- If dependency changes are present but file contents are missing, request dependency files and lockfiles.
- Evaluate reproducibility and audit readiness.

Focus:
- new deps added, version bumps, loosened pins
- supply chain risk signals (typosquatting, untrusted packages)
- license compatibility (if enforced)
- build reproducibility (lockfile consistency)

Relevant files:
- pyproject.toml, requirements*.txt, poetry.lock, uv.lock
- CI dependency steps

Checks you may request:
- pip-audit / poetry audit / uv audit
- license checker if repo uses it
- lockfile diff sanity checks

Severity:
- critical/blocking for risky dependency introduced without justification
- critical if pins loosened causing non-repro builds
- warning for safe bumps but missing notes

{get_review_output_schema()}

Your agent name is "dependencies"."""

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns relevant to dependency review."""
        return [
            "pyproject.toml",
            "requirements*.txt",
            "requirements.txt",
            "setup.py",
            "Pipfile",
            "poetry.lock",
            "uv.lock",
            "setup.cfg",
            "tox.ini",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform dependencies review on given context using SimpleReviewAgentRunner.

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

Please analyze the above changes for dependency and vulnerability issues and provide your review in the specified JSON format."""

        logger.info(f"[dependencies] Prompt construction complete:")
        logger.info(f"[dependencies]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[dependencies]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[dependencies]   Full user_message: {len(user_message)} chars")
        logger.info(f"[dependencies]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="dependencies")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[dependencies] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[dependencies] JSON validation successful!")
            logger.info(f"[dependencies]   agent: {output.agent}")
            logger.info(f"[dependencies]   severity: {output.severity}")
            logger.info(f"[dependencies]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[dependencies] JSON validation error: {e}")
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

