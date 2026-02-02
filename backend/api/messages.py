"""Message management endpoints for WebApp API."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import asyncio
import uuid
from datetime import datetime

from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.core.models import Message


# Pydantic models for request/response
class MessageCreate(BaseModel):
    """Request model for creating a message."""

    role: str
    content: str


class MessageResponse(BaseModel):
    """Response model for message data."""

    id: str
    session_id: str
    role: str
    text: str
    parts: List[dict]
    time: dict


router = APIRouter(tags=["messages"])


async def get_messages_from_session(session_id: str) -> List[MessageResponse]:
    """Get messages from a session using SDK."""
    client = OpenCodeAsyncClient()

    # Verify session exists first
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Get messages using SessionManager's get_messages method
    try:
        from opencode_python.storage.store import MessageStorage
        from opencode_python.core.settings import get_storage_dir
        from pathlib import Path

        storage_dir = get_storage_dir()
        message_storage = MessageStorage(storage_dir)

        # Get messages
        messages_data = await message_storage.list_messages(session_id)

        # Convert Message objects to MessageResponse
        return [
            MessageResponse(
                id=msg["id"],
                session_id=msg["session_id"],
                role=msg["role"],
                text=msg["text"],
                parts=msg.get("parts", []),
                time=msg.get("time", {})
            )
            for msg in messages_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


@router.get(
    "/api/v1/sessions/{session_id}/messages",
    response_model=List[MessageResponse],
    summary="List messages in a session",
    description="Retrieve all messages from a specific session",
)
async def list_messages(session_id: str) -> List[MessageResponse]:
    """List all messages for a session.

    Args:
        session_id: The session ID to retrieve messages from.

    Returns:
        List[MessageResponse]: A list of messages in the session.

    Raises:
        HTTPException: If the session is not found (404).
    """
    return await get_messages_from_session(session_id)


@router.post(
    "/api/v1/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a session",
    description="Create a new message in a specific session",
)
async def add_message(
    session_id: str,
    message_data: MessageCreate,
) -> MessageResponse:
    """Add a message to a session.

    Args:
        session_id: The session ID to add the message to.
        message_data: Message data containing role and content.

    Returns:
        MessageResponse: The created message.

    Raises:
        HTTPException: If the session is not found (404) or message creation fails.
    """
    # Verify session exists first
    client = OpenCodeAsyncClient()
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Add message using SDK
    try:
        from opencode_python.storage.store import MessageStorage
        from opencode_python.core.settings import get_storage_dir
        from pathlib import Path
        from opencode_python.core.models import Message

        storage_dir = get_storage_dir()
        message_storage = MessageStorage(storage_dir)

        # Create message object
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=message_data.role,
            text=message_data.content,
            parts=[],
            time={"created": datetime.now().timestamp()}
        )

        # Create message using MessageStorage
        await message_storage.create_message(session_id, message)

        # Return success with basic message info (message retrieval has issues)
        return MessageResponse(
            id=message.id,
            session_id=session_id,
            role=message.role,
            text=message.text,
            parts=[],
            time=message.time
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}",
        )
