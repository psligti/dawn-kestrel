"""Telemetry API endpoints - session effort tracking and git status."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from opencode_python.agents.tool_execution_tracker import ToolExecutionTracker
from opencode_python.core.config import SDKConfig
from opencode_python.sdk import OpenCodeAsyncClient


router = APIRouter(prefix="/api/v1/sessions", tags=["telemetry"])


def _clamp(min_val: int, max_val: int, value: float) -> int:
    return max(min_val, min(max_val, int(value)))


async def get_project_dir() -> Path:
    """Get the project directory for telemetry scope.

    Returns:
        Path to the project directory.

    Raises:
        HTTPException: If project directory cannot be determined.
    """
    try:
        return Path(os.environ.get("WEBAPP_PROJECT_DIR", Path.cwd()))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to determine project directory: {str(e)}",
        )


async def get_tool_tracker() -> ToolExecutionTracker:
    """Get ToolExecutionTracker instance.

    Returns:
        ToolExecutionTracker instance.

    Raises:
        HTTPException: If tracker initialization fails.
    """
    try:
        client = await get_sdk_client()
        return ToolExecutionTracker(base_dir=client.config.project_dir)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize tool tracker: {str(e)}",
        )


async def get_sdk_client() -> OpenCodeAsyncClient:
    """Get SDK client instance.

    Returns:
        OpenCodeAsyncClient: Initialized SDK client.

    Raises:
        HTTPException: If client initialization fails.
    """
    try:
        project_dir = Path(os.environ.get("WEBAPP_PROJECT_DIR", Path.cwd()))
        config = SDKConfig(
            storage_path=project_dir / "storage",
            project_dir=project_dir,
        )
        client = OpenCodeAsyncClient(config=config)
        return client
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize SDK client: {str(e)}",
        )


async def get_git_status(directory: Path) -> Dict[str, Any]:
    """Get git status for a directory.

    Args:
        directory: Directory to check git status for.

    Returns:
        Dictionary with git status fields.
    """
    git_info = {
        "is_repo": False,
        "branch": None,
        "dirty_count": 0,
        "staged_count": 0,
        "ahead": 0,
        "behind": 0,
        "conflict": False,
    }

    # Check if directory is a git repository
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or result.stdout.strip() != "true":
            return git_info
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return git_info

    git_info["is_repo"] = True

    # Get branch name (handle detached HEAD)
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            git_info["branch"] = branch if branch != "HEAD" else "detached"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Parse porcelain status for dirty/staged counts and conflicts
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            porcelain_output = result.stdout.strip().splitlines()
            conflict_states = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
            dirty_count = 0
            staged_count = 0

            for line in porcelain_output:
                if len(line) >= 2:
                    xy = line[:2]

                    if any(state in xy for state in conflict_states):
                        git_info["conflict"] = True

                    if xy[0] != " ":
                        dirty_count += 1
                    if xy[1] != " ":
                        staged_count += 1

            git_info["dirty_count"] = dirty_count
            git_info["staged_count"] = staged_count
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Get ahead/behind counts if upstream exists
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            counts = result.stdout.strip().split("\t")
            if len(counts) == 2:
                try:
                    git_info["behind"] = int(counts[0])
                    git_info["ahead"] = int(counts[1])
                except ValueError:
                    pass
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return git_info


async def get_tool_history(session_id: str) -> Dict[str, Any]:
    """Get tool execution history for a session.

    Args:
        session_id: Session identifier.

    Returns:
        Dictionary with tool execution info.
    """
    tool_info = {
        "running": None,
        "last": None,
        "error_count": 0,
        "recent": [],
    }

    try:
        tracker = await get_tool_tracker()
        history = await tracker.get_execution_history(session_id, limit=20)

        if not history:
            return tool_info

        # Find running tool
        for record in history:
            state = record.get("state", {})
            if state.get("status") == "running":
                tool_info["running"] = {
                    "tool_id": record.get("tool_id"),
                    "since": record.get("start_time"),
                }
                break

        # Get last tool (most recent since sorted by start_time desc)
        if history:
            last_record = history[0]
            state = last_record.get("state", {})
            start_time = last_record.get("start_time", 0)
            end_time = last_record.get("end_time") or state.get("time_end")

            tool_info["last"] = {
                "tool_id": last_record.get("tool_id"),
                "status": state.get("status"),
                "duration_ms": int((end_time - start_time) * 1000) if end_time and start_time else None,
            }

        error_count = 0
        recent: List[Dict[str, Any]] = []

        for record in history:
            state = record.get("state", {})
            if state.get("status") == "error":
                error_count += 1

            if len(recent) < 10:
                recent.append({
                    "tool_id": record.get("tool_id"),
                    "status": state.get("status"),
                })

        tool_info["error_count"] = error_count
        tool_info["recent"] = recent

    except Exception as e:
        pass

    return tool_info


def calculate_effort_score(duration_ms: float, token_total: int, tool_count: int) -> int:
    """Calculate effort score based on duration, tokens, and tool usage.

    Args:
        duration_ms: Session duration in milliseconds.
        token_total: Total tokens used (0 if unknown).
        tool_count: Number of tools used.

    Returns:
        Effort score from 0 to 5.
    """
    # Clamp helper
    def clamp(min_val: int, max_val: int, value: float) -> int:
        return max(min_val, min(max_val, int(value)))

    # Calculate component scores
    duration_pts = clamp(0, 2, duration_ms / 30000)
    token_pts = clamp(0, 2, token_total / 2000)
    tool_pts = clamp(0, 2, tool_count / 3)

    # Sum and clamp to max 5
    effort_score = min(5, duration_pts + token_pts + tool_pts)

    return effort_score


async def get_effort_metrics(session_id: str) -> Dict[str, Any]:
    """Get effort metrics for a session.

    Args:
        session_id: Session identifier.

    Returns:
        Dictionary with effort inputs and score.
    """
    effort_info = {
        "duration_ms": 0,
        "token_total": 0,
        "tool_count": 0,
        "effort_score": 0,
    }

    try:
        tracker = await get_tool_tracker()
        history = await tracker.get_execution_history(session_id, limit=100)

        if not history:
            return effort_info

        # Calculate duration (first start to last end)
        times = [(r.get("start_time", 0), r.get("end_time") or r.get("state", {}).get("time_end"))
                 for r in history]
        valid_times = [(s, e) for s, e in times if s and e]

        if valid_times:
            min_time = min(s for s, e in valid_times)
            max_time = max(e for s, e in valid_times)
            effort_info["duration_ms"] = int((max_time - min_time) * 1000)

        # Count tools
        effort_info["tool_count"] = len(history)

        # Note: token_total is not directly available from tool history
        # This would require aggregating from message history or session metadata
        # For now, set to 0 (effort score formula handles this gracefully)
        effort_info["token_total"] = 0

        # Calculate effort score
        effort_info["effort_score"] = calculate_effort_score(
            effort_info["duration_ms"],
            effort_info["token_total"],
            effort_info["tool_count"],
        )

    except Exception as e:
        # Return default values on error
        pass

    return effort_info


@router.get("/{session_id}/telemetry", response_model=Dict[str, Any])
async def get_telemetry(session_id: str) -> Dict[str, Any]:
    """Get telemetry snapshot for a session.

    Returns directory-scoped telemetry including git status, tool history,
    and effort metrics.

    Args:
        session_id: Session identifier.

    Returns:
        Dictionary containing telemetry data.

    Raises:
        HTTPException: 404 if session not found, 500 if retrieval fails.
    """
    try:
        # Verify session exists
        client = await get_sdk_client()
        session = await client.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        # Get project directory scope
        directory_scope = await get_project_dir()

        # Gather telemetry data
        git_info = await get_git_status(directory_scope)
        tool_info = await get_tool_history(session_id)
        effort_info = await get_effort_metrics(session_id)

        return {
            "type": "telemetry",
            "session_id": session_id,
            "directory_scope": str(directory_scope),
            "git": git_info,
            "tools": tool_info,
            "effort_inputs": {
                "duration_ms": effort_info["duration_ms"],
                "token_total": effort_info["token_total"],
                "tool_count": effort_info["tool_count"],
            },
            "effort_score": effort_info["effort_score"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get telemetry: {str(e)}",
        )
