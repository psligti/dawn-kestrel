"""Post-run review hook for external evaluation systems."""

from __future__ import annotations

from typing import Protocol

from dawn_kestrel.contracts.run_artifact import RunArtifact


class PostRunReviewHook(Protocol):
    """Protocol for hooks that receive completed run artifacts.

    Implementations can submit runs to external evaluation systems
    like Ash Hawk for improvement proposal generation.

    The hook is called after a run completes, regardless of outcome.
    Implementations should handle errors gracefully and not block
    the execution pipeline.
    """

    def submit_run_for_review(self, artifact: RunArtifact) -> None:
        """Submit a completed run artifact for external review.

        Args:
            artifact: The complete run artifact to submit.
        """
        ...

    def on_review_complete(self, artifact: RunArtifact, review_id: str) -> None:
        """Called when external review completes.

        Args:
            artifact: The original run artifact.
            review_id: Identifier for the completed review.
        """
        ...
