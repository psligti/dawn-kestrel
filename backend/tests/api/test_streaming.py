"""Tests for SSE streaming endpoint."""

import sys
from pathlib import Path

# Add backend root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_stream_endpoint_exists():
    """Test that SSE streaming endpoint exists and returns 404 for non-existent task."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tasks/nonexistent-session/stream")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_invalid_task_id():
    """Test that streaming endpoint returns 404 for invalid task_id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tasks/nonexistent-session/stream")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_returns_sse_format():
    """Test that streaming endpoint returns SSE format with valid task."""
    from api.sessions import get_sdk_client

    # Create session and test using the same client as the endpoint
    client = await get_sdk_client()
    session = await client.create_session(title="Test SSE Session")

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/tasks/{session.id}/stream")
            assert response.status_code == 200
            # Verify content-type is text/event-stream
            assert "text/event-stream" in response.headers.get("content-type", "")
            # Read at least one byte to ensure stream is not empty
            content = await response.aread()
            assert len(content) > 0
    finally:
        await client.delete_session(session.id)


@pytest.mark.asyncio
async def test_stream_keep_alive_headers():
    """Test that SSE stream has correct headers."""
    from api.sessions import get_sdk_client

    client = await get_sdk_client()
    session = await client.create_session(title="Test SSE Keep-Alive")

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/tasks/{session.id}/stream")
            assert response.status_code == 200
            # Verify content-type is text/event-stream
            assert "text/event-stream" in response.headers.get("content-type", "")
            # Verify no-cache is set
            assert "no-cache" in response.headers.get("Cache-Control", "")
            # Verify keep-alive is set
            assert response.headers.get("Connection") == "keep-alive"
    finally:
        await client.delete_session(session.id)
