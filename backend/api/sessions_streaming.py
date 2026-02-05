"""SSE (Server-Sent Events) streaming for session theme events."""

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, Set

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from api.sessions import get_sdk_client
from api.telemetry import get_telemetry as get_telemetry_data


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


_session_subscribers: dict[str, Set[asyncio.Queue]] = {}


async def _get_current_theme_id(session_id: str) -> str:
    """Get current theme_id for a session.

    Args:
        session_id: The session ID to get theme_id for.

    Returns:
        str: The current theme_id, defaulting to "aurora" if not set.
    """
    try:
        client = await get_sdk_client()
        session = await client.get_session(session_id)
        if session and session.theme_id:
            return session.theme_id
        return "aurora"
    except Exception:
        return "aurora"


async def _notify_telemetry_change(session_id: str) -> None:
    """Broadcast telemetry update to all subscribers of a session.

    Args:
        session_id: The session ID that had a telemetry change.
    """
    if session_id not in _session_subscribers:
        return

    try:
        telemetry_data = await get_telemetry_data(session_id)
        event_data = json.dumps(telemetry_data)

        for queue in _session_subscribers[session_id]:
            try:
                await queue.put(event_data)
            except Exception:
                pass
    except Exception:
        pass


async def _notify_theme_change(session_id: str, theme_id: str) -> None:
    """Broadcast theme change to all subscribers of a session.

    Args:
        session_id: The session ID that had a theme change.
        theme_id: The new theme_id value.
    """
    if session_id not in _session_subscribers:
        return

    event_data = json.dumps({
        "type": "session_theme",
        "session_id": session_id,
        "theme_id": theme_id,
    })

    for queue in _session_subscribers[session_id]:
        try:
            await queue.put(event_data)
        except Exception:
            pass


async def _stream_session_events(
    session_id: str,
    request: Request,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for session theme changes.

    Args:
        session_id: The session ID to stream events for.
        request: The FastAPI request object for cancellation detection.

    Yields:
        str: SSE-formatted event strings.
    """
    initial_theme_id = await _get_current_theme_id(session_id)

    yield f"event: connected\n"
    yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

    yield f"event: session_theme\n"
    yield f"data: {json.dumps({'type': 'session_theme', 'session_id': session_id, 'theme_id': initial_theme_id})}\n\n"

    try:
        telemetry_data = await get_telemetry_data(session_id)
        yield f"event: telemetry\n"
        yield f"data: {json.dumps(telemetry_data)}\n\n"
    except Exception:
        pass

    queue: asyncio.Queue[str] = asyncio.Queue()

    if session_id not in _session_subscribers:
        _session_subscribers[session_id] = set()
    _session_subscribers[session_id].add(queue)

    last_telemetry: Dict[str, Any] = {}
    last_ping_time = 0

    try:
        while True:
            if await request.is_disconnected():
                yield f"event: disconnect\n"
                yield f"data: {json.dumps({'type': 'disconnect', 'session_id': session_id})}\n\n"
                break

            current_time = time.time()

            if current_time - last_ping_time > 25:
                yield f"event: ping\n"
                yield f"data: {json.dumps({'type': 'ping', 'session_id': session_id})}\n\n"
                last_ping_time = current_time

            if int(current_time) % 10 == 0:
                try:
                    telemetry_data = await get_telemetry_data(session_id)
                    if telemetry_data != last_telemetry:
                        yield f"event: telemetry\n"
                        yield f"data: {json.dumps(telemetry_data)}\n\n"
                        last_telemetry = telemetry_data
                except Exception:
                    pass

            try:
                event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                event_obj = json.loads(event_data)
                event_type = event_obj.get('type', 'session_theme')
                yield f"event: {event_type}\n"
                yield f"data: {event_data}\n\n"
            except asyncio.TimeoutError:
                continue

    except Exception as e:
        yield f"event: error\n"
        yield f"data: {json.dumps({'type': 'error', 'session_id': session_id, 'message': str(e)})}\n\n"
    finally:
        if session_id in _session_subscribers:
            _session_subscribers[session_id].discard(queue)
            if not _session_subscribers[session_id]:
                del _session_subscribers[session_id]


@router.get("/{session_id}/stream")
async def stream_session_events(session_id: str, request: Request):
    """Stream session theme events as Server-Sent Events (SSE).

    This endpoint provides real-time theme updates for a session using
    Server-Sent Events (SSE), which is a unidirectional server-to-client
    streaming protocol.

    Args:
        session_id: The session ID to stream events for.
        request: The FastAPI request object for handling disconnects.

    Returns:
        StreamingResponse: Server-Sent Events stream with real-time updates.

    SSE Format:
        - event: connected
          data: {"type": "connected", "session_id": "..."}

        - event: session_theme
          data: {"type": "session_theme", "session_id": "...", "theme_id": "..."}

        - event: telemetry
          data: {"type": "telemetry", "session_id": "...", "git": {...}, "tools": {...}, "effort_inputs": {...}, "effort_score": 3}

        - event: ping
          data: {"type": "ping", "session_id": "..."}

        - event: disconnect
          data: {"type": "disconnect", "session_id": "..."}

        - event: error
          data: {"type": "error", "session_id": "...", "message": "..."}

        - comment: : keep-alive

    Raises:
        HTTPException: 404 if session_id not found, 500 if streaming fails.
    """
    try:
        client = await get_sdk_client()
        session = await client.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        return StreamingResponse(
            _stream_session_events(session_id, request),
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
