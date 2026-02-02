"""Tests for the message management endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_list_messages_success(client: TestClient, test_session: str):
    """Test that listing messages returns 200 OK with message data.

    This test verifies the GET /api/v1/sessions/{session_id}/messages endpoint
    returns a successful response with message data for an existing session.
    """
    response = client.get(f"/api/v1/sessions/{test_session}/messages")
    assert response.status_code == 200


def test_add_message_success(client: TestClient, test_session: str):
    """Test that adding a message returns 201 Created.

    This test verifies the POST /api/v1/sessions/{session_id}/messages endpoint
    creates a message successfully with correct status code and returns the message data.
    """
    message_data = {
        "role": "user",
        "content": "Hello, this is a test message",
    }
    response = client.post(
        f"/api/v1/sessions/{test_session}/messages",
        json=message_data,
    )
    if response.status_code != 201:
        print(f"ERROR: {response.json()}")
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    assert response.json()["text"] == "Hello, this is a test message"
    assert "id" in response.json()


def test_list_messages_not_found(client: TestClient):
    """Test that listing messages for non-existent session returns 404.

    This test verifies the GET /api/v1/sessions/{session_id}/messages endpoint
    returns 404 when the session does not exist.
    """
    session_id = "non-existent-session"
    response = client.get(f"/api/v1/sessions/{session_id}/messages")
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


def test_add_message_not_found(client: TestClient):
    """Test that adding a message to non-existent session returns 404.

    This test verifies the POST /api/v1/sessions/{session_id}/messages endpoint
    returns 404 when the session does not exist.
    """
    session_id = "non-existent-session"
    message_data = {
        "role": "user",
        "content": "Test message",
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json=message_data,
    )
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


def test_add_message_with_assistant_role(client: TestClient, test_session: str):
    """Test that adding an assistant message works correctly.

    This test verifies the POST endpoint handles different message roles properly.
    """
    message_data = {
        "role": "assistant",
        "content": "This is an assistant response",
    }
    response = client.post(
        f"/api/v1/sessions/{test_session}/messages",
        json=message_data,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "assistant"


def test_add_message_with_system_role(client: TestClient, test_session: str):
    """Test that adding a system message works correctly.

    This test verifies the POST endpoint handles system role properly.
    """
    message_data = {
        "role": "system",
        "content": "System initialization message",
    }
    response = client.post(
        f"/api/v1/sessions/{test_session}/messages",
        json=message_data,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "system"


def test_add_message_missing_content(client: TestClient):
    """Test that adding a message without content returns 400 or 422.

    This test verifies the POST endpoint validates request data.
    """
    session_id = "test-session-789"
    message_data = {
        "role": "user",
        # Missing content field
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json=message_data,
    )
    # Should be 422 (validation error) or 400 (bad request)
    assert response.status_code in [400, 422]


def test_add_message_missing_role(client: TestClient):
    """Test that adding a message without role returns 400 or 422.

    This test verifies the POST endpoint validates request data.
    """
    session_id = "test-session-role"
    message_data = {
        # Missing role field
        "content": "Test message without role",
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json=message_data,
    )
    # Should be 422 (validation error) or 400 (bad request)
    assert response.status_code in [400, 422]


def test_list_messages_returns_array(client: TestClient, test_session: str):
    """Test that listing messages returns a proper array.

    This test verifies the GET endpoint returns the correct response format.
    """
    response = client.get(f"/api/v1/sessions/{test_session}/messages")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
