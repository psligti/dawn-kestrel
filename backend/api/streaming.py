"""SSE (Server-Sent Events) streaming endpoint for task execution."""

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from opencode_python.sdk import OpenCodeAsyncClient


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


# Global storage for active stream tasks
_active_streams: dict[str, asyncio.Task] = {}


async def get_sdk_client() -> OpenCodeAsyncClient:
    """Get SDK client instance with shared storage.

    Returns:
        OpenCodeAsyncClient: Initialized SDK client.

    Raises:
        HTTPException: If client initialization fails.
    """
    from api.sessions import get_sdk_client as get_api_client

    client = await get_api_client()
    # Ensure client is consistent by using default config
    # This makes sure the client behaves the same way regardless of how it's created
    return client


async def stream_task_events(task_id: str, request: Request) -> AsyncGenerator[str, None]:
    """Generate SSE events for a task execution.

    Args:
        task_id: The task/session ID to stream events for.
        request: The FastAPI request object for cancellation detection.

    Yields:
        str: SSE-formatted event strings.
    """
    client = await get_sdk_client()

    # Verify session exists and get messages
    session = None
    messages_list = []

    try:
        session = await client.get_session(task_id)
        if session is None:
            # Session not found - this will be handled by the endpoint
            return

        # Try to get messages - method might not exist in all SDK versions
        if hasattr(client, 'get_messages'):
            try:
                messages = await client.get_messages(task_id)
                messages_list = messages.messages if messages else []
            except Exception:
                # If get_messages fails, use empty list
                messages_list = []
        else:
            # No get_messages method, use empty list
            messages_list = []

        # Yield initial connection established event even with no messages
        yield f"event: connected\n"
        yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id, 'message_count': len(messages_list)})}\n\n"

    except Exception as e:
        # Convert any exception to a string to yield as an event
        error_msg = str(e)
        yield f"event: error\n"
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        return

    # Yield initial connection established event
    yield f"event: connected\n"
    yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id, 'message_count': len(messages_list)})}\n\n"

    # Yield all existing messages
    for i, msg in enumerate(messages_list):
        yield f"event: message\n"
        yield f"data: {json.dumps({'type': 'message', 'index': i, 'role': msg.role, 'content': msg.content})}\n\n"
        await asyncio.sleep(0.1)  # Small delay to show streaming effect

    # Track disconnect
    try:
        # Wait for client disconnect or keep-alive timeout
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                yield f"event: disconnect\n"
                yield f"data: {json.dumps({'type': 'disconnect', 'task_id': task_id})}\n\n"
                break

            # Send keep-alive comment every 25 seconds to maintain connection
            current_time = time.time()
            if current_time % 25 < 1:  # Approximately every 25 seconds
                yield ": keep-alive\n\n"

            # Small delay before next check
            await asyncio.sleep(1)

    except Exception:
        # Connection error or cleanup
        yield f"event: error\n"
        yield f"data: {json.dumps({'type': 'error', 'task_id': task_id, 'message': 'Stream ended'})}\n\n"


@router.get("/{task_id}/stream")
async def stream_task_events_endpoint(task_id: str, request: Request):
    """Stream task execution events as Server-Sent Events (SSE).

    This endpoint provides real-time updates for a task session using
    Server-Sent Events (SSE), which is a unidirectional server-to-client
    streaming protocol.

    Args:
        task_id: The task/session ID to stream events for.
        request: The FastAPI request object for handling disconnects.

    Returns:
        StreamingResponse: Server-Sent Events stream with real-time updates.

    SSE Format:
        - event: connected
          data: {"type": "connected", "task_id": "...", "message_count": N}

        - event: message
          data: {"type": "message", "index": N, "role": "user|assistant", "content": "..."}

        - event: disconnect
          data: {"type": "disconnect", "task_id": "..."}

        - event: error
          data: {"type": "error", "message": "..."}

        - comment: : keep-alive

    Raises:
        HTTPException: 404 if task_id not found, 500 if streaming fails.
    """
    try:
        # Check if already streaming
        if task_id in _active_streams:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task {task_id} is already being streamed",
            )

        # Verify session exists before creating generator
        client = await get_sdk_client()
        session = await client.get_session(task_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_id}",
            )

        # Define async generator inline
        async def _stream_generator():
            async for event in stream_task_events(task_id, request):
                yield event

        # Create generator instance
        gen = _stream_generator()

        # Return StreamingResponse with the generator
        return StreamingResponse(
            gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start streaming: {str(e)}",
        )
