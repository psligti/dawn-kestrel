"""Session management API endpoints."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, status

from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.core.config import SDKConfig
from opencode_python.core.services.session_service import DefaultSessionService
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    title: str
    version: str = "1.0.0"


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


# Singleton storage directory for API
_api_storage_dir = None


async def get_sdk_client() -> OpenCodeAsyncClient:
    """Get SDK client instance with shared storage.

    Returns:
        OpenCodeAsyncClient: Initialized SDK client.

    Raises:
        HTTPException: If client initialization fails.
    """
    global _api_storage_dir

    try:
        # Create or reuse a temporary storage directory
        if _api_storage_dir is None:
            # Use a fixed temp directory for consistency, but use test_sessions if in test mode
            if os.environ.get("PYTEST_CURRENT_TEST"):
                # Running tests - use test-specific directory
                _api_storage_dir = os.path.join(tempfile.gettempdir(), "test_sessions")
            else:
                # Production - use api_sessions directory
                _api_storage_dir = os.path.join(tempfile.gettempdir(), "api_sessions")

        # Create SDKConfig with custom project_dir and storage_path
        storage_path = Path(_api_storage_dir)
        config = SDKConfig(
            storage_path=storage_path,
            project_dir=storage_path,
        )
        # Create client with custom config
        client = OpenCodeAsyncClient(config=config)
        return client
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize SDK client: {str(e)}",
        )


@router.get("/", response_model=Dict[str, Any])
async def list_sessions() -> Dict[str, Any]:
    """List all sessions.

    Returns:
        Dictionary containing the list of sessions.

    Raises:
        HTTPException: 500 if listing sessions fails.
    """
    try:
        client = await get_sdk_client()
        sessions = await client.list_sessions()

        return {
            "sessions": [
                {
                    "id": session.id,
                    "title": session.title,
                    "version": session.version,
                    "created_at": datetime.fromtimestamp(session.time_created).isoformat(),
                    "updated_at": datetime.fromtimestamp(session.time_updated).isoformat(),
                }
                for session in sessions
            ],
            "count": len(sessions),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get a single session by ID.

    Args:
        session_id: The session ID to retrieve.

    Returns:
        Dictionary containing session details.

    Raises:
        HTTPException: 404 if session not found, 500 if retrieval fails.
    """
    try:
        client = await get_sdk_client()
        session = await client.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        return {
            "id": session.id,
            "title": session.title,
            "version": session.version,
            "created_at": datetime.fromtimestamp(session.time_created).isoformat(),
            "updated_at": datetime.fromtimestamp(session.time_updated).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}",
        )


@router.post("/", response_model=Dict[str, Any])
async def create_session(request: CreateSessionRequest = Body(...)) -> Dict[str, Any]:
    """Create a new session.

    Args:
        request: CreateSessionRequest with title and optional version.

    Returns:
        Dictionary containing the created session details.

    Raises:
        HTTPException: 400 for invalid input, 500 if creation fails.
    """
    if not request.title or not request.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session title is required and cannot be empty",
        )

    try:
        client = await get_sdk_client()
        session = await client.create_session(title=request.title, version=request.version)

        return {
            "id": session.id,
            "title": session.title,
            "version": request.version,
            "created_at": datetime.fromtimestamp(session.time_created).isoformat(),
            "updated_at": datetime.fromtimestamp(session.time_updated).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.delete("/{session_id}", response_model=Dict[str, Any])
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a session by ID.

    Args:
        session_id: The session ID to delete.

    Returns:
        Dictionary confirming deletion.

    Raises:
        HTTPException: 404 if session not found, 500 if deletion fails.
    """
    try:
        client = await get_sdk_client()
        deleted = await client.delete_session(session_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        return {
            "message": "Session deleted successfully",
            "session_id": session_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
