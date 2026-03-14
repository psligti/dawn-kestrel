"""Artifact service for run artifact emission and storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dawn_kestrel.contracts.run_artifact import RunArtifact


class ArtifactService:
    """Service for emitting and storing run artifacts.

    Provides the bridge between Dawn Kestrel execution and
    external evaluation systems like Ash Hawk.
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        hook: object | None = None,
    ) -> None:
        self._output_dir = output_dir
        self._hook = hook

    def emit(self, artifact: RunArtifact) -> Path | None:
        """Emit a run artifact to storage and notify hooks.

        Args:
            artifact: The run artifact to emit.

        Returns:
            Path to the stored artifact file, or None if no storage.
        """
        stored_path: Path | None = None

        if self._output_dir:
            stored_path = self._store_artifact(artifact)

        if self._hook and hasattr(self._hook, "submit_run_for_review"):
            self._hook.submit_run_for_review(artifact)

        return stored_path

    def _store_artifact(self, artifact: RunArtifact) -> Path:
        """Store artifact to disk as JSON.

        Args:
            artifact: The artifact to store.

        Returns:
            Path to the stored file.
        """
        import json

        self._output_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._output_dir / f"{artifact.run_id}.json"

        with open(file_path, "w") as f:
            f.write(artifact.model_dump_json(indent=2))

        return file_path

    def load(self, run_id: str) -> RunArtifact | None:
        """Load a run artifact from storage.

        Args:
            run_id: The run ID to load.

        Returns:
            The loaded artifact, or None if not found.
        """
        if not self._output_dir:
            return None

        from dawn_kestrel.contracts.run_artifact import RunArtifact

        file_path = self._output_dir / f"{run_id}.json"
        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)

        return RunArtifact.model_validate(data)


import json
