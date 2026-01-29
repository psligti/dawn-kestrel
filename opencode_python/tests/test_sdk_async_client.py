"""Tests for async SDK client.

Placeholder tests for OpenCodeAsyncClient SDK client.
All tests are skipped because the SDK client is not yet implemented.

These tests will be unskipped when the SDK client is implemented in future tasks.
"""

import pytest


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeAsyncClientInitialization:
    """Tests for OpenCodeAsyncClient initialization."""

    def test_async_client_initialization_default(self) -> None:
        """Test OpenCodeAsyncClient initialization with default config."""
        # TODO: Implement when OpenCodeAsyncClient is available
        # from opencode_python.sdk.client import OpenCodeAsyncClient
        # client = OpenCodeAsyncClient()
        # assert client is not None
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_initialization_with_sdk_config(self) -> None:
        """Test OpenCodeAsyncClient initialization with SDKConfig."""
        # TODO: Implement when OpenCodeAsyncClient is available
        # from opencode_python.sdk.client import OpenCodeAsyncClient
        # from opencode_python.core.config import SDKConfig
        # config = SDKConfig()
        # client = OpenCodeAsyncClient(config=config)
        # assert client is not None
        pytest.skip("OpenCodeAsyncClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeAsyncClientSessionMethods:
    """Tests for OpenCodeAsyncClient session management methods."""

    def test_async_client_create_session(self) -> None:
        """Test OpenCodeAsyncClient.create_session() method."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_get_session(self) -> None:
        """Test OpenCodeAsyncClient.get_session() method."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_list_sessions(self) -> None:
        """Test OpenCodeAsyncClient.list_sessions() method."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_delete_session(self) -> None:
        """Test OpenCodeAsyncClient.delete_session() method."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeAsyncClientMessaging:
    """Tests for OpenCodeAsyncClient messaging methods."""

    def test_async_client_add_message(self) -> None:
        """Test OpenCodeAsyncClient.add_message() method."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeAsyncClientHandlerIntegration:
    """Tests for OpenCodeAsyncClient handler integration."""

    def test_async_client_io_handler_integration(self) -> None:
        """Test OpenCodeAsyncClient handler integration (io_handler)."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_progress_handler_integration(self) -> None:
        """Test OpenCodeAsyncClient handler integration (progress_handler)."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_notification_handler_integration(self) -> None:
        """Test OpenCodeAsyncClient handler integration (notification_handler)."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeAsyncClientCallbacks:
    """Tests for OpenCodeAsyncClient callback methods."""

    def test_async_client_on_progress_callback(self) -> None:
        """Test OpenCodeAsyncClient on_progress callback."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")

    def test_async_client_on_notification_callback(self) -> None:
        """Test OpenCodeAsyncClient on_notification callback."""
        # TODO: Implement when OpenCodeAsyncClient is available
        pytest.skip("OpenCodeAsyncClient not yet implemented")
