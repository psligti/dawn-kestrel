"""Review agent base classes and types.

Defines the foundational types for review agents, including ReviewContext
and the abstract BaseReviewerAgent class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReviewContext:
    """Context information for a code review.

    Bundles all the information needed to perform a review,
    including changed files, diff content, and repository metadata.
    """

    changed_files: list[str]
    """List of files that changed in the PR"""

    diff: str
    """Git diff content"""

    repo_root: str
    """Absolute path to the repository root"""

    base_ref: str | None = None
    """Base git reference (e.g., 'main')"""

    head_ref: str | None = None
    """Head git reference (e.g., 'feature-branch')"""

    pr_title: str | None = None
    """Pull request title"""

    pr_description: str | None = None
    """Pull request description"""


class BaseReviewerAgent(ABC):
    """Abstract base class for review agents.

    All review agents should inherit from this class and implement
    the required abstract methods.
    """

    @abstractmethod
    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform a review on the given context.

        Args:
            context: ReviewContext with changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
        """
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.

        Returns:
            System prompt string
        """
        ...

    @abstractmethod
    def get_relevant_file_patterns(self) -> list[str]:
        """Get file patterns relevant to this agent's review focus.

        Returns:
            List of glob patterns for relevant files (e.g., ['**/*.py', '**/auth/**'])
        """
        ...

    def is_relevant_to_changes(self, changed_files: list[str]) -> bool:
        """Check if the agent is relevant to the changed files.

        Args:
            changed_files: List of files that changed in the PR

        Returns:
            True if any file matches the agent's relevant patterns
        """
        patterns = self.get_relevant_file_patterns()
        if not patterns:
            return False

        from fnmatch import fnmatch

        for file_path in changed_files:
            for pattern in patterns:
                if fnmatch.fnmatch(file_path, pattern.replace("**", "*")):
                    return True
        return False

    def format_inputs_for_prompt(self, context: ReviewContext) -> str:
        """Format the review context as a prompt for the agent.

        Args:
            context: ReviewContext to format

        Returns:
            Formatted string suitable for use as user prompt
        """
        parts = [
            "## Review Context",
            "",
            f"**Repository Root**: {context.repo_root}",
            "",
            "### Changed Files",
        ]

        for file_path in context.changed_files:
            parts.append(f"- {file_path}")

        if context.base_ref and context.head_ref:
            parts.append("")
            parts.append("### Git Diff")
            parts.append(f"**Base Ref**: {context.base_ref}")
            parts.append(f"**Head Ref**: {context.head_ref}")

        parts.append("")
        parts.append("### Diff Content")
        parts.append("```diff")
        parts.append(context.diff)
        parts.append("```")

        if context.pr_title:
            parts.append("")
            parts.append("### Pull Request")
            parts.append(f"**Title**: {context.pr_title}")
            if context.pr_description:
                parts.append(f"**Description**:\n{context.pr_description}")

        return "\n".join(parts)


# Import contracts for type hints
from dawn_kestrel.agents.review.contracts import ReviewOutput
