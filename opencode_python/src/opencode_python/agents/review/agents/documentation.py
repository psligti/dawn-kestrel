"""Documentation Review Subagent.

Reviews code changes for documentation coverage including:
- Docstrings for public functions/classes
- README updates for new features
- Configuration documentation
- Usage examples
"""

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

class DocumentationReviewer(BaseReviewerAgent):
    """Documentation reviewer agent that checks for documentation coverage.

    This agent specializes in detecting:
    - Missing docstrings for public functions/classes
    - Outdated or missing README documentation
    - Missing configuration documentation
    - Missing usage examples
    """

    def get_agent_name(self) -> str:
        """Return the agent identifier."""
        return "documentation"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the documentation reviewer."""
        return f"""You are the Documentation Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to documentation.
- Propose minimal checks; request doc build checks only if relevant.
- If changed_files or diff are missing, request them.
- Discover repo conventions (README, docs toolchain) to propose correct commands.

You specialize in:
- docstrings for public functions/classes
- module-level docs explaining purpose and contracts
- README / usage updates when behavior changes
- configuration documentation (env vars, settings, CLI flags)
- examples and edge case documentation

Relevant changes:
- new public APIs, new commands/tools/skills/agents
- changes to behavior, defaults, outputs, error handling
- renamed modules, moved files, breaking interface changes

Checks you may request:
- docs build/check (mkdocs/sphinx) if repo has it
- docstring linting if configured
- ensure examples match CLI/help output if changed

Documentation review must answer:
1) Would a new engineer understand how to use the changed parts?
2) Are contracts described (inputs/outputs/errors)?
3) Are sharp edges warned?
4) Is terminology consistent?

Severity guidance:
- warning: missing docstring or minor README mismatch
- critical: behavior changed but docs claim old behavior; config/env changes undocumented
- blocking: public interface changed with no documentation and high risk of misuse

{get_review_output_schema()}

Your agent name is "documentation"."""

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns relevant to documentation review."""
        return [
            "**/*.py",
            "README*",
            "docs/**",
            "*.md",
            "pyproject.toml",
            "setup.cfg",
            ".env.example",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform documentation review on given context using SimpleReviewAgentRunner.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with documentation findings, severity, and merge gate decision

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

Please analyze the above changes for documentation coverage and provide your review in the specified JSON format."""

        logger.info(f"[documentation] Prompt construction complete:")
        logger.info(f"[documentation]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[documentation]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[documentation]   Full user_message: {len(user_message)} chars")
        logger.info(f"[documentation]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(agent_name="documentation")

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[documentation] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[documentation] JSON validation successful!")
            logger.info(f"[documentation]   agent: {output.agent}")
            logger.info(f"[documentation]   severity: {output.severity}")
            logger.info(f"[documentation]   findings: {len(output.findings)}")

            return output
        except pd.ValidationError as e:
            logger.error(f"[documentation] JSON validation error: {e}")
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

