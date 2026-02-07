"""
ToolExecutionTracker - Track and persist tool executions.

Provides persistent storage for tool execution history with
query capabilities and event emission.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

from dawn_kestrel.core.event_bus import bus, Events
from dawn_kestrel.core.models import ToolState


logger = logging.getLogger(__name__)


class ToolExecutionTracker:
    """Track and persist tool executions

    Stores tool execution records in JSON files under
    storage/tool_execution/{session_id}/{execution_id}.json
    """

    def __init__(self, base_dir: Path):
        """Initialize ToolExecutionTracker

        Args:
            base_dir: Base directory for storage (typically project root)
        """
        self.base_dir = base_dir
        self.storage_dir = base_dir / "storage" / "tool_execution"
        self._lock = None

    async def log_execution(
        self,
        execution_id: str,
        session_id: str,
        message_id: str,
        tool_id: str,
        state: ToolState,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Log a tool execution record

        Args:
            execution_id: Unique identifier for this execution
            session_id: Session identifier
            message_id: Message identifier
            tool_id: Tool identifier
            state: Tool execution state (from ToolState model)
            start_time: Execution start timestamp (optional, uses time_start from state if None)
            end_time: Execution end timestamp (optional, uses time_end from state if None)

        Returns:
            Execution record dictionary
        """
        execution_record = {
            "id": execution_id,
            "session_id": session_id,
            "message_id": message_id,
            "tool_id": tool_id,
            "state": state.model_dump(mode="json"),
            "start_time": start_time or state.time_start,
            "end_time": end_time or state.time_end,
            "logged_at": datetime.now().timestamp(),
        }

        await self.persist(execution_record)

        await bus.publish(Events.TOOL_STARTED, {
            "execution_id": execution_id,
            "session_id": session_id,
            "tool_id": tool_id,
            "state": state.status,
        })

        logger.debug(
            f"Logged tool execution: {tool_id} (status: {state.status}) "
            f"in session {session_id}"
        )

        return execution_record

    async def update_execution(
        self,
        execution_id: str,
        state: ToolState,
        end_time: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing execution record

        Args:
            execution_id: Execution identifier
            state: Updated tool execution state
            end_time: New end timestamp (optional)

        Returns:
            Updated execution record or None if not found
        """
        session_id = None

        session_dirs = [d for d in self.storage_dir.iterdir() if d.is_dir()]
        for session_dir in session_dirs:
            execution_file = session_dir / f"{execution_id}.json"
            if execution_file.exists():
                session_id = session_dir.name
                break

        if not session_id:
            logger.warning(f"Execution record not found: {execution_id}")
            return None

        execution_file = self.storage_dir / session_id / f"{execution_id}.json"
        try:
            with open(execution_file, "r") as f:
                record = json.load(f)

            record["state"] = state.model_dump(mode="json")
            if end_time:
                record["end_time"] = end_time
            record["updated_at"] = datetime.now().timestamp()

            with open(execution_file, "w") as f:
                json.dump(record, f, indent=2)

            if state.status == "completed":
                await bus.publish(Events.TOOL_COMPLETED, {
                    "execution_id": execution_id,
                    "session_id": session_id,
                    "tool_id": record["tool_id"],
                    "output": state.output,
                })
            elif state.status == "error":
                await bus.publish(Events.TOOL_ERROR, {
                    "execution_id": execution_id,
                    "session_id": session_id,
                    "tool_id": record["tool_id"],
                    "error": state.error,
                })

            logger.debug(f"Updated execution record: {execution_id} (status: {state.status})")

            return record

        except Exception as e:
            logger.error(f"Failed to update execution record {execution_id}: {e}")
            return None

    async def get_execution_history(
        self,
        session_id: str,
        tool_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get execution history for a session

        Args:
            session_id: Session identifier
            tool_id: Optional filter by specific tool
            limit: Optional maximum number of records to return

        Returns:
            List of execution records sorted by timestamp (newest first)
        """
        session_dir = self.storage_dir / session_id
        if not session_dir.exists():
            return []

        executions = []
        for execution_file in session_dir.glob("*.json"):
            try:
                with open(execution_file, "r") as f:
                    record = json.load(f)

                if tool_id and record.get("tool_id") != tool_id:
                    continue

                executions.append(record)

            except Exception as e:
                logger.warning(f"Failed to read execution file {execution_file}: {e}")

        executions.sort(key=lambda x: x.get("start_time", 0), reverse=True)

        if limit:
            executions = executions[:limit]

        return executions

    async def get_execution(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific execution record

        Args:
            execution_id: Execution identifier

        Returns:
            Execution record or None if not found
        """
        session_dirs = [d for d in self.storage_dir.iterdir() if d.is_dir()]
        for session_dir in session_dirs:
            execution_file = session_dir / f"{execution_id}.json"
            if execution_file.exists():
                try:
                    with open(execution_file, "r") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read execution file {execution_file}: {e}")
                    return None

        return None

    async def persist(self, record: Dict[str, Any]) -> None:
        """Persist an execution record to disk

        Args:
            record: Execution record dictionary
        """
        session_id = record["session_id"]
        execution_id = record["id"]

        session_dir = self.storage_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        execution_file = session_dir / f"{execution_id}.json"
        with open(execution_file, "w") as f:
            json.dump(record, f, indent=2)

        logger.debug(f"Persisted execution record: {execution_file}")


def create_tool_tracker(base_dir: Path) -> ToolExecutionTracker:
    """Factory function to create ToolExecutionTracker

    Args:
        base_dir: Base directory for storage

    Returns:
        ToolExecutionTracker instance
    """
    return ToolExecutionTracker(base_dir)
