"""
Test plugin discovery system using Python entry_points.

Tests cover:
- Loading tools from entry points
- Loading providers from entry points
- Loading agents from entry points
- Validation of plugin structure
- Graceful failure handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from importlib.metadata import EntryPoint


class TestLoadTools:
    """Test tool plugin discovery and loading."""

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_tools_from_entry_points(self, mock_entry_points):
        """Test that tools are loaded from entry_points."""
        # Setup mock entry points
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "bash"
        mock_ep.value = "dawn_kestrel.tools.builtin:BashTool"
        mock_ep.load.return_value = Mock()

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_tools

        # Test
        tools = load_tools()

        # Assert
        assert isinstance(tools, dict)
        assert "bash" in tools
        mock_eps.select.assert_called_once_with(group="dawn_kestrel.tools")

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_tools_with_no_entry_points(self, mock_entry_points):
        """Test that empty dict is returned when no tools found."""
        # Setup mock with no entry points
        mock_eps = Mock()
        mock_eps.select.return_value = []
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_tools

        # Test
        tools = load_tools()

        # Assert
        assert isinstance(tools, dict)
        assert len(tools) == 0

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_tools_handles_loading_errors(self, mock_entry_points):
        """Test that loading errors are handled gracefully."""
        # Setup mock with failing entry point
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "broken_tool"
        mock_ep.value = "invalid.module:InvalidTool"
        mock_ep.load.side_effect = ImportError("Cannot import")

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_tools

        # Test - should not raise, just log warning
        tools = load_tools()

        # Assert - broken tool should be skipped
        assert "broken_tool" not in tools


class TestLoadProviders:
    """Test provider plugin discovery and loading."""

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_providers_from_entry_points(self, mock_entry_points):
        """Test that providers are loaded from entry_points."""
        # Setup mock entry points
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "anthropic"
        mock_ep.value = "dawn_kestrel.providers:AnthropicProvider"
        mock_ep.load.return_value = Mock()

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_providers

        # Test
        providers = load_providers()

        # Assert
        assert isinstance(providers, dict)
        assert "anthropic" in providers
        mock_eps.select.assert_called_once_with(group="dawn_kestrel.providers")

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_providers_with_no_entry_points(self, mock_entry_points):
        """Test that empty dict is returned when no providers found."""
        # Setup mock with no entry points
        mock_eps = Mock()
        mock_eps.select.return_value = []
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_providers

        # Test
        providers = load_providers()

        # Assert
        assert isinstance(providers, dict)
        assert len(providers) == 0


class TestLoadAgents:
    """Test agent plugin discovery and loading."""

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_agents_from_entry_points(self, mock_entry_points):
        """Test that agents are loaded from entry_points."""
        # Setup mock entry points
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "orchestrator"
        mock_ep.value = "dawn_kestrel.agents.bolt_merlin:orchestrator"
        mock_ep.load.return_value = Mock()

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_agents

        # Test
        agents = load_agents()

        # Assert
        assert isinstance(agents, dict)
        assert "orchestrator" in agents
        mock_eps.select.assert_called_once_with(group="dawn_kestrel.agents")

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_load_agents_with_no_entry_points(self, mock_entry_points):
        """Test that empty dict is returned when no agents found."""
        # Setup mock with no entry points
        mock_eps = Mock()
        mock_eps.select.return_value = []
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_agents

        # Test
        agents = load_agents()

        # Assert
        assert isinstance(agents, dict)
        assert len(agents) == 0


class TestPluginValidation:
    """Test plugin validation logic."""

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_validate_plugin_structure(self, mock_entry_points):
        """Test that plugin structure is validated."""
        # Setup mock entry point with valid structure
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "valid_tool"
        mock_ep.value = "dawn_kestrel.tools.builtin:BashTool"

        # Mock the loaded object
        mock_tool = Mock()
        mock_tool.__class__.__name__ = "BashTool"
        mock_ep.load.return_value = mock_tool

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_tools

        # Test
        tools = load_tools()

        # Assert
        assert "valid_tool" in tools

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_invalid_plugin_rejected(self, mock_entry_points):
        """Test that invalid plugins are rejected gracefully."""
        # Setup mock entry point that returns None
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "invalid_plugin"
        mock_ep.value = "invalid.module:InvalidClass"
        mock_ep.load.return_value = None

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_tools

        # Test
        tools = load_tools()

        # Assert - invalid plugin should be skipped
        assert "invalid_plugin" not in tools


class TestVersionCompatibility:
    """Test version compatibility checks."""

    @patch("dawn_kestrel.core.plugin_discovery.entry_points")
    def test_plugin_version_check(self, mock_entry_points):
        """Test that plugin version is checked."""
        # Setup mock entry point with version metadata
        mock_ep = Mock(spec=EntryPoint)
        mock_ep.name = "versioned_tool"
        mock_ep.value = "dawn_kestrel.tools.builtin:BashTool"
        mock_ep.dist = Mock()
        mock_ep.dist.version = "1.0.0"

        mock_tool = Mock()
        mock_ep.load.return_value = mock_tool

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        # Import after mocking
        from dawn_kestrel.core.plugin_discovery import load_tools

        # Test
        tools = load_tools()

        # Assert - versioned plugin should be loaded
        assert "versioned_tool" in tools
