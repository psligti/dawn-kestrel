"""Pytest configuration and fixtures for backend tests."""
import sys
from pathlib import Path

# Add opencode_python to Python path for SDK imports (absolute path for reliable imports)
sys.path.insert(0, "/Users/parkersligting/develop/pt/agentic_coding/.worktrees/webapp/opencode_python/src")

import asyncio
import os
import shutil
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from main import app
from opencode_python.sdk import OpenCodeAsyncClient

# Singleton storage directory for tests
_test_storage_dir = None


@pytest.fixture
def event_loop() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """Create an instance of the default event loop for the test session.

    This fixture is required for pytest-asyncio to work correctly with async FastAPI tests.

    Yields:
        asyncio.AbstractEventLoop: The event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI application.

    This fixture provides a TestClient instance that can make HTTP requests
    to the FastAPI application without starting a server.

    Returns:
        TestClient: A test client instance.
    """
    return TestClient(app)


@pytest.fixture
async def test_session(client: TestClient) -> str:
    """Create a test session for message endpoint tests.

    This fixture sets up a test session that can be used by tests
    for adding and listing messages.

    Returns:
        str: The created session ID.
    """
    async def _get_session_id():
        session = await OpenCodeAsyncClient().create_session(title="Test Session")
        return session.id

    session_id = await _get_session_id()
    return session_id


@pytest.fixture
async def test_session_with_messages(client: TestClient) -> str:
    """Create a test session with sample messages.

    This fixture sets up a test session with multiple messages
    for testing list functionality.

    Returns:
        str: The created session ID.
    """
    async def _get_session_id():
        # Create session
        session = await OpenCodeAsyncClient().create_session(
            title="Test Session with Messages"
        )
        session_id = session.id

        # Add sample messages
        client = OpenCodeAsyncClient()
        await client.add_message(
            session_id=session_id,
            role="user",
            content="Hello, this is a test message",
        )
        await client.add_message(
            session_id=session_id,
            role="assistant",
            content="Hello! How can I help you?",
        )

        return session_id

    session_id = await _get_session_id()
    return session_id


@pytest.fixture
async def clean_storage():
    """Clean up test storage directory.

    This fixture clears the test storage directory before and after tests.
    """
    global _test_storage_dir
    import tempfile

    # Set up test storage directory
    _test_storage_dir = os.path.join(tempfile.gettempdir(), "test_sessions")

    # Clean up directory if it exists
    storage_path = Path(_test_storage_dir)
    if storage_path.exists():
        import shutil
        shutil.rmtree(storage_path)

    yield

    # Clean up after tests
    if storage_path.exists():
        shutil.rmtree(storage_path)
