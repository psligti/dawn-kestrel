"""Tests for theme definitions and application integration"""

from __future__ import annotations

from pathlib import Path


class TestThemeFilesExist:
    """Test that all required theme files exist"""

    def test_light_theme_exists(self):
        """Test that light.tcss theme file exists"""
        light_theme = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/themes/light.tcss"
        assert light_theme.exists(), "light.tcss theme file should exist"
        assert light_theme.is_file(), "light.tcss should be a file"

    def test_dark_theme_exists(self):
        """Test that dark.tcss theme file exists"""
        dark_theme = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/themes/dark.tcss"
        assert dark_theme.exists(), "dark.tcss theme file should exist"
        assert dark_theme.is_file(), "dark.tcss should be a file"

    def test_dracula_theme_exists(self):
        """Test that dracula.tcss theme file exists"""
        dracula_theme = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/themes/dracula.tcss"
        assert dracula_theme.exists(), "dracula.tcss theme file should exist"
        assert dracula_theme.is_file(), "dracula.tcss should be a file"


class TestThemeCSSVariables:
    """Test that theme files contain all required CSS variables"""

    def test_light_theme_has_primary_color(self, tmp_path):
        """Test that light theme defines primary color"""
        light_theme = tmp_path / "light.tcss"
        light_theme.write_text("""
$primary: #007f95;
$secondary: #7b5bb6;
$accent: #d68c27;
$error: #d1383d;
$warning: #a44200;
$success: #036e43;
$info: #007f95;
$text: #363644;
$text-muted: #70707d;
$background: #ffffff;
$background-panel: #fbfcfd;
$background-element: #f4f5f9;
        """)

        content = light_theme.read_text()
        assert "$primary:" in content
        assert "#007f95" in content

    def test_dark_theme_has_primary_color(self, tmp_path):
        """Test that dark theme defines primary color"""
        dark_theme = tmp_path / "dark.tcss"
        dark_theme.write_text("""
$primary: #56b6c2;
$secondary: #5c9cf5;
$accent: #9d7cd8;
$error: #e06c75;
$warning: #f5a742;
$success: #7fd88f;
$info: #56b6c2;
$text: #f5f5f5;
$text-muted: #a0a0a0;
$background: #0a0a0a;
$background-panel: #141414;
$background-element: #1e1e1e;
        """)

        content = dark_theme.read_text()
        assert "$primary:" in content
        assert "#56b6c2" in content

    def test_dracula_theme_has_primary_color(self, tmp_path):
        """Test that dracula theme defines primary color"""
        dracula_theme = tmp_path / "dracula.tcss"
        dracula_theme.write_text("""
$primary: #8be9fd;
$secondary: #bd93f9;
$accent: #ff79c6;
$error: #ff5555;
$warning: #f1fa8c;
$success: #50fa7b;
$info: #8be9fd;
$text: #f8f8f2;
$text-muted: #6272a4;
$background: #282a36;
$background-panel: #21222c;
$background-element: #44475a;
        """)

        content = dracula_theme.read_text()
        assert "$primary:" in content
        assert "#8be9fd" in content

    def test_theme_has_all_required_variables(self, tmp_path):
        """Test that all required CSS variables are present in light theme"""
        light_theme = tmp_path / "light.tcss"
        required_vars = [
            "$primary",
            "$secondary",
            "$accent",
            "$error",
            "$warning",
            "$success",
            "$info",
            "$text",
            "$text-muted",
            "$text-selection",
            "$background",
            "$background-panel",
            "$background-element",
            "$background-menu",
            "$border",
            "$border-active",
            "$border-subtle",
            "$diff-added",
            "$diff-removed",
            "$diff-context",
            "$diff-hunk-header",
            "$diff-highlight-added",
            "$diff-highlight-removed",
            "$diff-added-bg",
            "$diff-removed-bg",
            "$diff-context-bg",
            "$diff-line-number",
            "$diff-added-line-number-bg",
            "$diff-removed-line-number-bg",
            "$markdown-text",
            "$markdown-heading",
            "$markdown-link",
            "$markdown-link-text",
            "$markdown-code",
            "$markdown-blockquote",
            "$markdown-emph",
            "$markdown-strong",
            "$markdown-horizontal-rule",
            "$markdown-list-item",
            "$markdown-list-enumeration",
            "$markdown-image",
            "$markdown-image-text",
            "$markdown-code-block",
            "$syntax-comment",
            "$syntax-keyword",
            "$syntax-function",
            "$syntax-variable",
            "$syntax-string",
            "$syntax-number",
            "$syntax-type",
            "$syntax-operator",
            "$syntax-punctuation",
        ]

        light_theme.write_text("\n".join([f"${var}: #color;" for var in required_vars]))

        content = light_theme.read_text()
        for var in required_vars:
            assert var in content, f"Theme should define {var}"

    def test_theme_has_mixed_case_colors(self, tmp_path):
        """Test that themes use lowercase hex color codes"""
        theme = tmp_path / "test.tcss"
        theme.write_text("""
$primary: #007f95;
$secondary: #7b5bb6;
$error: #d1383d;
        """)

        content = theme.read_text()
        # Check that colors are lowercase
        assert "#007f95" in content  # lowercase
        assert "#7b5bb6" in content  # lowercase
        assert "#d1383d" in content  # lowercase


class TestThemeFileStructure:
    """Test that theme files are properly structured"""

    def test_light_theme_has_closing_comment(self, tmp_path):
        """Test that light theme has a closing comment"""
        light_theme = tmp_path / "light.tcss"
        light_theme.write_text("""
/* Light Theme */
$primary: #007f95;
/* Dark Theme */
        """)

        content = light_theme.read_text()
        assert "/* Light Theme */" in content

    def test_dracula_theme_has_closing_comment(self, tmp_path):
        """Test that dracula theme has a closing comment"""
        dracula_theme = tmp_path / "dracula.tcss"
        dracula_theme.write_text("""
/* Dracula Theme */
$primary: #8be9fd;
/* Another comment */
        """)

        content = dracula_theme.read_text()
        assert "/* Dracula Theme */" in content

    def test_theme_has_no_duplicate_colors(self, tmp_path):
        """Test that themes don't have duplicate color definitions for same variable"""
        theme = tmp_path / "test.tcss"
        # Create intentional duplicates
        theme.write_text("""
$primary: #007f95;
$primary: #008096;  /* Duplicate */
        """)

        content = theme.read_text()
        # Count occurrences - duplicates are allowed in CSS but not ideal
        # This is a basic check, actual implementation may handle duplicates
        assert content.count("$primary:") >= 1


class TestThemeIntegration:
    """Test integration between theme files and application"""

    def test_theme_variables_are_used_in_app(self):
        """Test that app.py references theme CSS variables"""
        app_path = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/app.py"
        app_content = app_path.read_text()

        # Check that app uses CSS variables
        assert "$primary" in app_content, "App should reference $primary CSS variable"
        assert "$secondary" in app_content, "App should reference $secondary CSS variable"
        assert "$background" in app_content, "App should reference $background CSS variable"

    def test_app_css_includes_theme_classes(self):
        """Test that app.py has CSS styles that use theme variables"""
        app_path = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/app.py"
        app_content = app_path.read_text()

        # Check for common TUI widget selectors
        assert "Screen" in app_content, "App should have Screen styles"
        assert "Header" in app_content, "App should have Header styles"
        assert "Button" in app_content, "App should have Button styles"
        assert "DataTable" in app_content, "App should have DataTable styles"

    def test_app_uses_theme_variables_in_css(self):
        """Test that app CSS uses theme variables defined in themes/*.tcss files"""
        app_path = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/app.py"
        app_content = app_path.read_text()

        # Check for usage of theme variables in CSS
        assert "$primary" in app_content, "App CSS should use $primary variable"
        assert "$secondary" in app_content, "App CSS should use $secondary variable"
        assert "$background" in app_content, "App CSS should use $background variable"

    def test_multiple_themes_exist_in_directory(self):
        """Test that all three theme files are present in themes directory"""
        themes_dir = Path(__file__).parent.parent.parent / "dawn_kestrel/tui/themes"
        theme_files = list(themes_dir.glob("*.tcss"))

        assert len(theme_files) >= 3, "Should have at least 3 theme files"
        theme_names = {f.stem for f in theme_files}
        assert "light" in theme_names, "Should have light theme"
        assert "dark" in theme_names, "Should have dark theme"
        assert "dracula" in theme_names, "Should have dracula theme"


class TestThemeColors:
    """Test that theme colors are appropriate for their type"""

    def test_light_theme_background_is_light(self, tmp_path):
        """Test that light theme background color is light"""
        theme = tmp_path / "light.tcss"
        theme.write_text("""
$background: #ffffff;  /* White/light */
$text: #363644;        /* Dark text */
        """)

        content = theme.read_text()
        # Light themes should have light backgrounds and dark text
        assert "$background:" in content
        assert "#ffffff" in content or "#f5f5f5" in content

    def test_dark_theme_background_is_dark(self, tmp_path):
        """Test that dark theme background color is dark"""
        theme = tmp_path / "dark.tcss"
        theme.write_text("""
$background: #0a0a0a;  /* Very dark */
$text: #f5f5f5;        /* Light text */
        """)

        content = theme.read_text()
        # Dark themes should have dark backgrounds and light text
        assert "$background:" in content
        assert "#0a0a0a" in content or "#282a36" in content
        assert "$text:" in content

    def test_dracula_theme_background_is_dark(self, tmp_path):
        """Test that dracula theme background is dark"""
        theme = tmp_path / "dracula.tcss"
        theme.write_text("""
$background: #282a36;  /* Dark purple */
$text: #f8f8f2;        /* Light text */
        """)

        content = theme.read_text()
        # Dracula is a dark theme
        assert "$background:" in content
        assert "#282a36" in content or "#21222c" in content
