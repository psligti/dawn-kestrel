"""Tests for theme command palette integration."""

import pytest
from unittest.mock import Mock

from opencode_python.themes.registry import ThemeRegistry, get_theme_registry as get_registry
from opencode_python.themes.models import Theme, ThemeMetadata, ThemeSettings
from opencode_python.tui.dialogs.command_palette_dialog import CommandPaletteDialog
from opencode_python.tui.palette.command_palette import CommandPalette


@pytest.fixture
def app_mock():
    """Create a mock Textual app for testing."""
    app = Mock()
    return app


class TestThemeCommandPaletteIntegration:
    """Test theme commands in command palette."""

    @pytest.fixture
    def theme_registry(self):
        """Create a ThemeRegistry instance."""
        return get_registry()

    @pytest.fixture
    def sample_theme(self):
        """Create a sample theme for testing."""
        return Theme(
            metadata=ThemeMetadata(
                name="Test Theme",
                slug="test",
                description="Test theme",
                author="OpenCode",
                version="1.0.0",
            ),
            primary="#10b981",
            secondary="#5c9cf5",
            accent="#d946ef",
            error="#ef4444",
            warning="#f59e0b",
            success="#10b981",
            info="#10b981",
            text="#f3f4f6",
            text_muted="#9ca3af",
            text_selection="#2968c3",
            background="#1a1d2e",
            background_panel="#242838",
            background_element="#242838",
            background_menu="#242838",
            border="#6b7280",
            border_active="#a855f7",
            border_subtle="#6b7280",
            font_family="monospace",
            font_size=14,
            line_height=1.4,
            animations_enabled=True,
            reduced_motion=False,
        )

    def test_theme_commands_exist(self, theme_registry):
        """Test that theme-related commands are available."""
        palette = CommandPaletteDialog(app=app_mock())

        theme_registry.register_theme(self.sample_theme())

        palette._render_content()

        command_values = [cmd.get("value") for cmd in palette.filtered_commands]

        assert "switch_theme" in command_values
        assert "list_themes" in command_values
        assert "preview_theme" in command_values
        assert "theme_settings" in command_values

    def test_switch_theme_command_valid(self, theme_registry, sample_theme):
        """Test switch_theme command with valid theme."""
        palette = CommandPaletteDialog(app=app_mock())
        theme_registry.register_theme(self.sample_theme())

        palette._render_content()

        command_values = [cmd.get("value") for cmd in palette.filtered_commands]

        async def execute():
            # Find switch_theme command
            for idx, cmd in enumerate(palette.filtered_commands):
                if cmd.get("value") == "switch_theme":
                    palette._selected_index = idx
                    break

            await palette.action_enter()

            assert palette.get_result() == "test"

    def test_list_themes_command(self, theme_registry):
        """Test list_themes command shows theme list."""
        palette = CommandPaletteDialog(app=app_mock())
        theme_registry.register_theme(self.sample_theme())

        palette._render_content()

        command_values = [cmd.get("value") for cmd in palette.filtered_commands]

        async def execute():
            for idx, cmd in enumerate(palette.filtered_commands):
                if cmd.get("value") == "list_themes":
                    palette._selected_index = idx
                    break

            await palette.action_enter()

            result = palette.get_result()
            assert result is not None

    def test_preview_theme_command(self, theme_registry):
        """Test preview_theme command shows theme preview."""
        palette = CommandPaletteDialog(app=app_mock())
        theme_registry.register_theme(self.sample_theme())

        palette._render_content()

        command_values = [cmd.get("value") for cmd in palette.filtered_commands]

        async def execute():
            for idx, cmd in enumerate(palette.filtered_commands):
                if cmd.get("value") == "preview_theme":
                    palette._selected_index = idx
                    break

            await palette.action_enter()

            result = palette.get_result()
            assert result is not None
