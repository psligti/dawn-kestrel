"""OpenCode Python - Destructive action safeguards

Provides confirmation dialogs and safety checks for destructive operations
like force push, delete, and mass refactor.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Callable, Awaitable
import logging
import asyncio

from opencode_python.observability.models import (
    DestructiveAction,
    DestructiveActionRequest,
)
from opencode_python.core.event_bus import bus

logger = logging.getLogger(__name__)


class DestructiveActionGuard:
    """Guard for destructive operations requiring confirmation"""

    DEFAULT_DESTRUCTIVE_ACTIONS = [
        DestructiveAction.FORCE_PUSH,
        DestructiveAction.DELETE_BRANCH,
        DestructiveAction.DELETE_FILES,
        DestructiveAction.MASS_REFACTOR,
        DestructiveAction.RESET_HARD,
        DestructiveAction.REVERT_COMMIT,
    ]

    ACTION_DESCRIPTIONS = {
        DestructiveAction.FORCE_PUSH: "Force push will overwrite remote history and may cause data loss for collaborators",
        DestructiveAction.DELETE_BRANCH: "Deleting a branch will remove all commits unique to that branch",
        DestructiveAction.DELETE_FILES: "Deleting files cannot be easily undone without git history",
        DestructiveAction.MASS_REFACTOR: "Mass refactoring may affect many files and introduce bugs",
        DestructiveAction.RESET_HARD: "Hard reset will discard all uncommitted changes permanently",
        DestructiveAction.REVERT_COMMIT: "Reverting a commit will create a new commit that undoes the changes",
    }

    def __init__(self, destructive_actions: Optional[List[DestructiveAction]] = None):
        """Initialize destructive action guard

        Args:
            destructive_actions: List of actions requiring confirmation
        """
        self._destructive_actions = set(destructive_actions or self.DEFAULT_DESTRUCTIVE_ACTIONS)
        self._pending_requests: Dict[str, DestructiveActionRequest] = {}
        self._callbacks: Dict[str, Callable[[bool], Awaitable[None]]] = {}
        self._lock = asyncio.Lock()

    def is_destructive(self, action: DestructiveAction) -> bool:
        """Check if an action requires confirmation

        Args:
            action: Action to check

        Returns:
            True if action requires confirmation
        """
        return action in self._destructive_actions

    def get_description(self, action: DestructiveAction) -> str:
        """Get description for destructive action

        Args:
            action: Destructive action

        Returns:
            Description of the action's impact
        """
        return self.ACTION_DESCRIPTIONS.get(action, "This action may have destructive consequences")

    async def request_confirmation(
        self,
        session_id: str,
        action: DestructiveAction,
        metadata: Optional[Dict] = None,
        callback: Optional[Callable[[bool], Awaitable[None]]] = None,
    ) -> DestructiveActionRequest:
        """Request user confirmation for destructive action

        Creates a request that must be approved before the action can proceed.
        Emits destructive:request event for UI to show confirmation dialog.

        Args:
            session_id: Session identifier
            action: Destructive action being requested
            metadata: Additional context about the action
            callback: Async function to call with approval result (True=approved, False=denied)

        Returns:
            The destructive action request
        """
        async with self._lock:
            request = DestructiveActionRequest(
                session_id=session_id,
                action=action,
                description=self.get_description(action),
                impact=self._get_impact_description(action),
                metadata=metadata or {},
            )

            self._pending_requests[request.id] = request
            if callback:
                self._callbacks[request.id] = callback

            await bus.publish(
                "destructive:request",
                {
                    "request_id": request.id,
                    "session_id": session_id,
                    "action": action.value,
                    "description": request.description,
                    "impact": request.impact,
                    "default_action": "cancel",
                },
            )

            logger.warning(
                f"Destructive action requested: {action.value} for session {session_id}"
            )

            return request

    async def approve_request(self, request_id: str) -> bool:
        """Approve a destructive action request

        Args:
            request_id: Request identifier

        Returns:
            True if request was found and approved
        """
        async with self._lock:
            request = self._pending_requests.get(request_id)
            if not request:
                logger.error(f"Request not found: {request_id}")
                return False

            callback = self._callbacks.get(request_id)
            del self._pending_requests[request_id]
            if callback:
                del self._callbacks[request_id]
                await callback(True)

            logger.info(f"Approved destructive action: {request.action.value}")
            return True

    async def deny_request(self, request_id: str) -> bool:
        """Deny a destructive action request

        Args:
            request_id: Request identifier

        Returns:
            True if request was found and denied
        """
        async with self._lock:
            request = self._pending_requests.get(request_id)
            if not request:
                logger.error(f"Request not found: {request_id}")
                return False

            callback = self._callbacks.get(request_id)
            del self._pending_requests[request_id]
            if callback:
                del self._callbacks[request_id]
                await callback(False)

            logger.info(f"Denied destructive action: {request.action.value}")
            return True

    def get_pending_request(self, session_id: str) -> Optional[DestructiveActionRequest]:
        """Get pending request for a session

        Args:
            session_id: Session identifier

        Returns:
            Pending request or None
        """
        for request in self._pending_requests.values():
            if request.session_id == session_id:
                return request
        return None

    def add_destructive_action(self, action: DestructiveAction) -> None:
        """Add an action to the destructive actions list

        Args:
            action: Action to add
        """
        self._destructive_actions.add(action)

    def remove_destructive_action(self, action: DestructiveAction) -> None:
        """Remove an action from the destructive actions list

        Args:
            action: Action to remove
        """
        self._destructive_actions.discard(action)

    def _get_impact_description(self, action: DestructiveAction) -> str:
        """Get detailed impact description for an action

        Args:
            action: Destructive action

        Returns:
            Impact description
        """
        impacts = {
            DestructiveAction.FORCE_PUSH: "Remote history will be overwritten. Collaborators will need to force pull to reconcile.",
            DestructiveAction.DELETE_BRANCH: "All commits unique to this branch will be deleted and cannot be recovered.",
            DestructiveAction.DELETE_FILES: "Files will be permanently deleted. Use git restore to recover if committed.",
            DestructiveAction.MASS_REFACTOR: "Many files will be modified. Review changes carefully before committing.",
            DestructiveAction.RESET_HARD: "All uncommitted changes will be lost. Use git stash first if needed.",
            DestructiveAction.REVERT_COMMIT: "A new commit will be created to undo the changes. Original commit remains.",
        }
        return impacts.get(action, "This action cannot be easily undone.")


# Global destructive action guard instance
destructive_guard = DestructiveActionGuard()
