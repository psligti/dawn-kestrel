"""Tests for sync SDK client.

Placeholder tests for OpenCodeClient SDK client.
All tests are skipped because the SDK client is not yet implemented.

These tests will be unskipped when the SDK client is implemented in future tasks.
"""

import pytest


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeClientInitialization:
    """Tests for OpenCodeClient initialization."""

    def test_sync_client_initialization_default(self) -> None:
        """Test OpenCodeClient initialization with default config."""
        # TODO: Implement when OpenCodeClient is available
        # from opencode_python.sdk.client import OpenCodeClient
        # client = OpenCodeClient()
        # assert client is not None
        pytest.skip("OpenCodeClient not yet implemented")

    def test_sync_client_initialization_with_sdk_config(self) -> None:
        """Test OpenCodeClient initialization with SDKConfig."""
        # TODO: Implement when OpenCodeClient is available
        # from opencode_python.sdk.client import OpenCodeClient
        # from opencode_python.core.config import SDKConfig
        # config = SDKConfig()
        # client = OpenCodeClient(config=config)
        # assert client is not None
        pytest.skip("OpenCodeClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeClientSessionMethods:
    """Tests for OpenCodeClient session management methods."""

    def test_sync_client_create_session(self) -> None:
        """Test OpenCodeClient.create_session() method."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")

    def test_sync_client_get_session(self) -> None:
        """Test OpenCodeClient.get_session() method."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")

    def test_sync_client_list_sessions(self) -> None:
        """Test OpenCodeClient.list_sessions() method."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")

    def test_sync_client_delete_session(self) -> None:
        """Test OpenCodeClient.delete_session() method."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeClientMessaging:
    """Tests for OpenCodeClient messaging methods."""

    def test_sync_client_add_message(self) -> None:
        """Test OpenCodeClient.add_message() method."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")


@pytest.mark.skip(reason="SDK client not yet implemented")
class TestOpenCodeClientAsyncIntegration:
    """Tests for OpenCodeClient async integration."""

    def test_sync_client_uses_asyncio_run(self) -> None:
        """Test OpenCodeClient uses asyncio.run() internally."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")

    def test_sync_client_handler_integration(self) -> None:
        """Test OpenCodeClient handler integration."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")

    def test_sync_client_wraps_async_client_methods(self) -> None:
        """Test OpenCodeClient wraps async client methods."""
        # TODO: Implement when OpenCodeClient is available
        pytest.skip("OpenCodeClient not yet implemented")
