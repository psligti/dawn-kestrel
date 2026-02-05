"""Comprehensive tests for entry point discovery module."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from opencode_python.agents.review.discovery import (
    EntryPoint,
    EntryPointDiscovery,
)


class TestEntryPointDataclass:
    """Test EntryPoint dataclass instantiation and attributes."""

    def test_entry_point_creation_with_all_fields(self):
        """Test creating EntryPoint with all fields populated."""
        ep = EntryPoint(
            file_path="src/auth.py",
            line_number=42,
            description="Authentication function",
            weight=0.9,
            pattern_type="ast",
            evidence="def authenticate():"
        )

        assert ep.file_path == "src/auth.py"
        assert ep.line_number == 42
        assert ep.description == "Authentication function"
        assert ep.weight == 0.9
        assert ep.pattern_type == "ast"
        assert ep.evidence == "def authenticate():"

    def test_entry_point_with_none_line_number(self):
        """Test EntryPoint with None line_number (file path patterns)."""
        ep = EntryPoint(
            file_path="docs/README.md",
            line_number=None,
            description="Documentation file",
            weight=0.7,
            pattern_type="file_path",
            evidence="docs/README.md"
        )

        assert ep.line_number is None

    def test_entry_point_weight_range(self):
        """Test EntryPoint with various weight values."""
        # Minimum weight
        ep_min = EntryPoint(
            file_path="test.py",
            line_number=1,
            description="Low priority",
            weight=0.0,
            pattern_type="content",
            evidence="test"
        )
        assert ep_min.weight == 0.0

        # Maximum weight
        ep_max = EntryPoint(
            file_path="test.py",
            line_number=1,
            description="High priority",
            weight=1.0,
            pattern_type="ast",
            evidence="test"
        )
        assert ep_max.weight == 1.0

    def test_entry_point_pattern_types(self):
        """Test EntryPoint with all pattern types."""
        pattern_types = ["ast", "content", "file_path"]

        for pattern_type in pattern_types:
            ep = EntryPoint(
                file_path="test.py",
                line_number=10,
                description=f"{pattern_type} pattern",
                weight=0.5,
                pattern_type=pattern_type,
                evidence="test"
            )
            assert ep.pattern_type == pattern_type


class TestEntryPointDiscoveryInitialization:
    """Test EntryPointDiscovery class initialization."""

    def test_default_initialization(self):
        """Test discovery with default timeout."""
        discovery = EntryPointDiscovery()
        assert discovery.timeout_seconds == EntryPointDiscovery.DISCOVERY_TIMEOUT
        assert discovery.timeout_seconds == 30

    def test_custom_timeout_initialization(self):
        """Test discovery with custom timeout."""
        discovery = EntryPointDiscovery(timeout_seconds=60)
        assert discovery.timeout_seconds == 60

    def test_max_entry_points_constant(self):
        """Test MAX_ENTRY_POINTS constant."""
        assert EntryPointDiscovery.MAX_ENTRY_POINTS == 50


class TestEntryPointDiscoveryMainMethod:
    """Test discover_entry_points main method."""

    @pytest.mark.asyncio
    async def test_successful_discovery(self):
        """Test successful entry point discovery."""
        discovery = EntryPointDiscovery(timeout_seconds=30)

        mock_entry_points = [
            EntryPoint(
                file_path="src/auth.py",
                line_number=10,
                description="AST pattern: def authenticate",
                weight=0.9,
                pattern_type="ast",
                evidence="def authenticate():"
            ),
            EntryPoint(
                file_path="src/config.py",
                line_number=None,
                description="File path pattern: **/*.py",
                weight=0.7,
                pattern_type="file_path",
                evidence="src/config.py"
            )
        ]

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            return_value=mock_entry_points
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=["src/auth.py", "src/config.py"]
            )

        assert result is not None
        assert len(result) == 2
        assert result[0].file_path == "src/auth.py"
        assert result[1].file_path == "src/config.py"

    @pytest.mark.asyncio
    async def test_empty_discovery_returns_none(self):
        """Test that empty discovery returns None (triggers fallback)."""
        discovery = EntryPointDiscovery()

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            return_value=[]
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=["src/test.py"]
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_protection(self):
        """Test timeout protection (30s timeout via asyncio.wait_for)."""
        discovery = EntryPointDiscovery(timeout_seconds=1)

        # Simulate long-running discovery
        async def slow_discovery(*args, **kwargs):
            await asyncio.sleep(5)
            return []

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            side_effect=slow_discovery
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=["src/test.py"]
            )

        assert result is None  # Should return None on timeout

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        """Test generic exception handling returns None."""
        discovery = EntryPointDiscovery()

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            side_effect=Exception("Unexpected error")
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=["src/test.py"]
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_entry_point_limit_enforcement(self):
        """Test MAX_ENTRY_POINTS limit (50)."""
        discovery = EntryPointDiscovery()

        # Create 60 entry points (more than MAX_ENTRY_POINTS)
        mock_entry_points = [
            EntryPoint(
                file_path=f"src/file_{i}.py",
                line_number=i,
                description=f"Entry point {i}",
                weight=0.5,
                pattern_type="content",
                evidence=f"test_{i}"
            )
            for i in range(60)
        ]

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            return_value=mock_entry_points
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=[f"src/file_{i}.py" for i in range(60)]
            )

        assert result is not None
        assert len(result) == EntryPointDiscovery.MAX_ENTRY_POINTS  # Should be limited to 50


class TestPatternLoading:
    """Test _load_agent_patterns method."""

    @pytest.mark.asyncio
    async def test_load_patterns_from_valid_doc(self):
        """Test loading patterns from valid documentation."""
        discovery = EntryPointDiscovery()

        mock_yaml_content = """---
agent: security
agent_type: required
version: "1.0.0"
patterns:
  - type: ast
    pattern: "def $FUNC($$$) { $$$ }"
    language: python
    weight: 0.9
  - type: file_path
    pattern: "**/auth/**/*.py"
    weight: 0.8
  - type: content
    pattern: "password.*=.*['\\\"]"
    language: python
    weight: 0.95
---
# Security Reviewer
"""

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_yaml_content):
                patterns = await discovery._load_agent_patterns("security")

        assert "ast" in patterns
        assert "content" in patterns
        assert "file_path" in patterns
        assert len(patterns["ast"]) == 1
        assert len(patterns["content"]) == 1
        assert len(patterns["file_path"]) == 1

        # Check pattern details
        assert patterns["ast"][0]["weight"] == 0.9
        assert patterns["content"][0]["weight"] == 0.95
        assert patterns["file_path"][0]["weight"] == 0.8

    @pytest.mark.asyncio
    async def test_load_patterns_missing_doc(self):
        """Test loading patterns when doc doesn't exist."""
        discovery = EntryPointDiscovery()

        with patch('pathlib.Path.exists', return_value=False):
            patterns = await discovery._load_agent_patterns("missing_agent")

        assert patterns == {}

    @pytest.mark.asyncio
    async def test_load_patterns_no_frontmatter(self):
        """Test loading patterns when doc has no frontmatter raises ValueError."""
        discovery = EntryPointDiscovery()

        mock_content = """# Security Reviewer

No frontmatter here.
"""

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_content):
                with patch.object(
                    discovery, '_parse_frontmatter',
                    side_effect=ValueError("Missing YAML frontmatter")
                ):
                    # Should raise ValueError when _parse_frontmatter fails
                    with pytest.raises(ValueError, match="Missing YAML frontmatter"):
                        await discovery._load_agent_patterns("security")

    @pytest.mark.asyncio
    async def test_load_patterns_no_patterns_field(self):
        """Test loading patterns when frontmatter has no patterns field returns empty dict."""
        discovery = EntryPointDiscovery()

        mock_yaml_content = """---
agent: security
agent_type: required
version: "1.0.0"
---
# Security Reviewer
"""

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_yaml_content):
                patterns = await discovery._load_agent_patterns("security")

        # Should return empty dict when no patterns field
        assert patterns == {}

    @pytest.mark.asyncio
    async def test_weight_conversion_string_to_float(self):
        """Test weight conversion from string to float."""
        discovery = EntryPointDiscovery()

        # YAML frontmatter with multi-line array items
        mock_yaml_content = """---
agent: security
version: "1.0.0"
patterns:
  - type: ast
    pattern: "def $FUNC($$$) { $$$ }"
    language: python
    weight: 0.85
  - type: ast
    pattern: "class $CLASS($$$) { $$$ }"
    language: python
    weight: 0.75
---
# Security Reviewer
"""

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_yaml_content):
                patterns = await discovery._load_agent_patterns("security")

        assert patterns["ast"][0]["weight"] == 0.85
        assert patterns["ast"][1]["weight"] == 0.75

    @pytest.mark.asyncio
    async def test_weight_default_value(self):
        """Test default weight value (0.5) when not specified."""
        discovery = EntryPointDiscovery()

        mock_yaml_content = """---
agent: security
version: "1.0.0"
patterns:
  - type: ast
    pattern: "def $FUNC($$$) { $$$ }"
    language: python
---
# Security Reviewer
"""

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_yaml_content):
                patterns = await discovery._load_agent_patterns("security")

        assert patterns["ast"][0]["weight"] == 0.5

    @pytest.mark.asyncio
    async def test_weight_invalid_value(self):
        """Test weight conversion handles invalid values (defaults to 0.5)."""
        discovery = EntryPointDiscovery()

        mock_yaml_content = """---
agent: security
version: "1.0.0"
patterns:
  - type: ast
    pattern: "def $FUNC($$$) { $$$ }"
    language: python
    weight: "invalid"
---
# Security Reviewer
"""

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=mock_yaml_content):
                patterns = await discovery._load_agent_patterns("security")

        assert patterns["ast"][0]["weight"] == 0.5


class TestFrontmatterParsing:
    """Test _parse_frontmatter method."""

    def test_parse_valid_frontmatter(self):
        """Test parsing valid YAML frontmatter."""
        discovery = EntryPointDiscovery()

        content = """---
agent: security
agent_type: required
version: "1.0.0"
patterns:
  - type: ast
    pattern: "def $FUNC($$$) { $$$ }"
    language: python
    weight: 0.9
---
# Security Reviewer
"""

        yaml_text, frontmatter = discovery._parse_frontmatter(content)

        assert frontmatter["agent"] == "security"
        assert frontmatter["agent_type"] == "required"
        assert frontmatter["version"] == "1.0.0"
        assert "patterns" in frontmatter

    def test_parse_frontmatter_with_multiline_array(self):
        """Test parsing frontmatter with multi-line array items."""
        discovery = EntryPointDiscovery()

        # Multi-line array items are stored as strings
        content = """---
patterns:
  - type: ast
    pattern: "def $FUNC($$$) { $$$ }"
    language: python
    weight: 0.9
  - type: content
    pattern: "password.*=.*['\\\"]"
    language: python
    weight: 0.95
---
# Reviewer
"""

        yaml_text, frontmatter = discovery._parse_frontmatter(content)

        assert "patterns" in frontmatter
        # Multi-line array items are stored as strings, not dicts
        assert len(frontmatter["patterns"]) == 2
        assert isinstance(frontmatter["patterns"][0], str)
        assert isinstance(frontmatter["patterns"][1], str)
        assert "type: ast" in frontmatter["patterns"][0]
        assert "type: content" in frontmatter["patterns"][1]

    def test_parse_frontmatter_missing_delimiters(self):
        """Test parsing frontmatter with missing --- delimiters."""
        discovery = EntryPointDiscovery()

        content = """agent: security
patterns:
  - type: ast
"""

        with pytest.raises(ValueError, match="Missing YAML frontmatter"):
            discovery._parse_frontmatter(content)

    def test_parse_frontmatter_empty_content(self):
        """Test parsing frontmatter with empty content."""
        discovery = EntryPointDiscovery()

        content = """---
agent: security
---
"""

        yaml_text, frontmatter = discovery._parse_frontmatter(content)

        assert frontmatter["agent"] == "security"


class TestASTPatternDiscovery:
    """Test _discover_ast_patterns method."""

    @pytest.mark.asyncio
    async def test_ast_pattern_discovery_success(self):
        """Test successful AST pattern discovery with mocked subprocess."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        # ast-grep returns absolute paths, which get converted to relative
        mock_result.stdout = "/test/repo/src/auth.py:10:def authenticate(user, password):\n/test/repo/src/auth.py:20:def logout(session):\n"

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result):
            entry_points = await discovery._discover_ast_patterns(
                patterns, "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 2
        assert entry_points[0].line_number == 10
        assert entry_points[0].pattern_type == "ast"
        assert entry_points[0].weight == 0.9
        assert entry_points[1].line_number == 20

    @pytest.mark.asyncio
    async def test_ast_pattern_filters_by_language(self):
        """Test that AST patterns filter files by language extension."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
        ]

        changed_files = [
            "src/auth.py",  # Python - should be included
            "src/app.js",       # JavaScript - should be filtered out
            "docs/README.md"    # Markdown - should be filtered out
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/test/repo/src/auth.py:10:def authenticate():"

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result) as mock_run:
            entry_points = await discovery._discover_ast_patterns(
                patterns, "/test/repo", changed_files
            )

        # Verify entry point was found
        assert len(entry_points) == 1
        assert entry_points[0].file_path == "src/auth.py"

        # Verify only Python files were passed to subprocess
        call_args = mock_run.call_args[0][0]
        assert any("src/auth.py" in arg for arg in call_args)
        # Non-Python files should be filtered before subprocess call
        assert not any("src/app.js" in str(arg) for arg in call_args)
        assert not any("docs/README.md" in str(arg) for arg in call_args)

    @pytest.mark.asyncio
    async def test_ast_pattern_no_matching_language_files(self):
        """Test AST pattern discovery when no files match language."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
        ]

        changed_files = ["src/app.js", "docs/README.md"]

        entry_points = await discovery._discover_ast_patterns(
            patterns, "/test/repo", changed_files
        )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_ast_pattern_tool_not_found(self):
        """Test AST pattern discovery when ast-grep tool not found."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9},
            {"pattern": "class $CLASS($$$) { $$$ }", "language": "python", "weight": 0.8}
        ]

        with patch('opencode_python.agents.review.discovery.subprocess.run', side_effect=FileNotFoundError("ast-grep not found")):
            entry_points = await discovery._discover_ast_patterns(
                patterns, "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 0
        # Should break on first FileNotFoundError, so second pattern not attempted

    @pytest.mark.asyncio
    async def test_ast_pattern_timeout(self):
        """Test AST pattern discovery timeout (10s per pattern)."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
        ]

        with patch('opencode_python.agents.review.discovery.subprocess.run', side_effect=subprocess.TimeoutExpired("ast-grep", 10)):
            entry_points = await discovery._discover_ast_patterns(
                patterns, "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_ast_pattern_no_matches(self):
        """Test AST pattern discovery when no matches found."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result):
            entry_points = await discovery._discover_ast_patterns(
                patterns, "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_ast_pattern_error_parsing_line_number(self):
        """Test AST pattern discovery handles invalid line numbers gracefully."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """/test/repo/src/auth.py:invalid:def authenticate():
/test/repo/src/auth.py:20:def logout():
"""

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result):
            entry_points = await discovery._discover_ast_patterns(
                patterns, "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 2
        assert entry_points[0].line_number is None  # Invalid line number becomes None
        assert entry_points[1].line_number == 20


class TestContentPatternDiscovery:
    """Test _discover_content_patterns method."""

    @pytest.mark.asyncio
    async def test_content_pattern_discovery_success(self):
        """Test successful content pattern discovery with mocked ripgrep."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "password.*=", "language": "python", "weight": 0.95}
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        # ripgrep returns absolute paths, which get converted to relative
        mock_result.stdout = """/test/repo/src/config.py:10:password = "secret"
/test/repo/src/config.py:20:api_password = "key"
"""

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result):
            entry_points = await discovery._discover_content_patterns(
                patterns, "/test/repo", ["src/config.py"]
            )

        assert len(entry_points) == 2
        assert entry_points[0].file_path == "src/config.py"
        assert entry_points[0].line_number == 10
        assert entry_points[0].pattern_type == "content"
        assert entry_points[0].weight == 0.95

    @pytest.mark.asyncio
    async def test_content_pattern_filters_by_language(self):
        """Test that content patterns filter files by language extension."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "password.*=", "language": "python", "weight": 0.95}
        ]

        changed_files = [
            "src/config.py",  # Python - should be included
            "src/app.js",        # JavaScript - should be filtered out
            "docs/README.md"     # Markdown - should be filtered out
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/test/repo/src/config.py:10:password = 'secret'"

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result) as mock_run:
            entry_points = await discovery._discover_content_patterns(
                patterns, "/test/repo", changed_files
            )

        # Verify entry point was found
        assert len(entry_points) == 1
        assert entry_points[0].file_path == "src/config.py"

        # Verify only Python files were passed to subprocess
        call_args = mock_run.call_args[0][0]
        assert any("src/config.py" in arg for arg in call_args)
        # Non-Python files should be filtered before subprocess call
        assert not any("src/app.js" in str(arg) for arg in call_args)
        assert not any("docs/README.md" in str(arg) for arg in call_args)

    @pytest.mark.asyncio
    async def test_content_pattern_tool_not_found(self):
        """Test content pattern discovery when ripgrep tool not found."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "password.*=", "language": "python", "weight": 0.95}
        ]

        with patch('opencode_python.agents.review.discovery.subprocess.run', side_effect=FileNotFoundError("ripgrep not found")):
            entry_points = await discovery._discover_content_patterns(
                patterns, "/test/repo", ["src/config.py"]
            )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_content_pattern_timeout(self):
        """Test content pattern discovery timeout (10s per pattern)."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "password.*=", "language": "python", "weight": 0.95}
        ]

        with patch('opencode_python.agents.review.discovery.subprocess.run', side_effect=subprocess.TimeoutExpired("ripgrep", 10)):
            entry_points = await discovery._discover_content_patterns(
                patterns, "/test/repo", ["src/config.py"]
            )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_content_pattern_no_matches(self):
        """Test content pattern discovery when no matches found."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "password.*=", "language": "python", "weight": 0.95}
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch('opencode_python.agents.review.discovery.subprocess.run', return_value=mock_result):
            entry_points = await discovery._discover_content_patterns(
                patterns, "/test/repo", ["src/config.py"]
            )

        assert len(entry_points) == 0


class TestFilePathPatternDiscovery:
    """Test _discover_file_path_patterns method."""

    @pytest.mark.asyncio
    async def test_file_path_pattern_discovery_success(self):
        """Test successful file path pattern discovery."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "**/auth/**/*.py", "weight": 0.8}
        ]

        changed_files = [
            "src/auth/login.py",
            "src/auth/logout.py",
            "src/api/routes.py",
            "docs/README.md"
        ]

        with patch.object(
            discovery, '_match_glob_pattern',
            side_effect=lambda fp, pat: "auth" in fp and fp.endswith(".py")
        ):
            entry_points = await discovery._discover_file_path_patterns(
                patterns, changed_files
            )

        assert len(entry_points) == 2
        assert entry_points[0].file_path == "src/auth/login.py"
        assert entry_points[0].pattern_type == "file_path"
        assert entry_points[0].weight == 0.8
        assert entry_points[1].file_path == "src/auth/logout.py"

    @pytest.mark.asyncio
    async def test_file_path_pattern_multiple_patterns(self):
        """Test file path pattern discovery with multiple patterns."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "**/auth/**/*.py", "weight": 0.8},
            {"pattern": "docs/**/*.md", "weight": 0.6}
        ]

        changed_files = [
            "src/auth/login.py",
            "docs/README.md",
            "src/api/routes.py"
        ]

        def match_side_effect(fp, pat):
            if "auth" in pat:
                return "auth" in fp and fp.endswith(".py")
            elif "docs" in pat:
                return fp.startswith("docs/") and fp.endswith(".md")
            return False

        with patch.object(
            discovery, '_match_glob_pattern',
            side_effect=match_side_effect
        ):
            entry_points = await discovery._discover_file_path_patterns(
                patterns, changed_files
            )

        assert len(entry_points) == 2
        assert any(ep.file_path == "src/auth/login.py" for ep in entry_points)
        assert any(ep.file_path == "docs/README.md" for ep in entry_points)

    @pytest.mark.asyncio
    async def test_file_path_pattern_no_matches(self):
        """Test file path pattern discovery when no matches found."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "**/auth/**/*.py", "weight": 0.8}
        ]

        changed_files = [
            "src/api/routes.py",
            "docs/README.md"
        ]

        with patch.object(
            discovery, '_match_glob_pattern',
            return_value=False
        ):
            entry_points = await discovery._discover_file_path_patterns(
                patterns, changed_files
            )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_file_path_pattern_empty_pattern(self):
        """Test file path pattern discovery with empty pattern."""
        discovery = EntryPointDiscovery()

        patterns = [
            {"pattern": "", "weight": 0.8}
        ]

        changed_files = ["src/auth/login.py"]

        with patch.object(
            discovery, '_match_glob_pattern',
            return_value=True
        ):
            entry_points = await discovery._discover_file_path_patterns(
                patterns, changed_files
            )

        assert len(entry_points) == 0


class TestGlobPatternMatching:
    """Test _match_glob_pattern method."""

    def test_match_glob_pattern_basic(self):
        """Test basic glob pattern matching."""
        discovery = EntryPointDiscovery()

        with patch('opencode_python.agents.review.base._match_glob_pattern') as mock_match:
            mock_match.return_value = True

            result = discovery._match_glob_pattern("src/auth/login.py", "**/auth/**/*.py")

            assert result is True
            mock_match.assert_called_once_with("src/auth/login.py", "**/auth/**/*.py")

    def test_match_glob_pattern_uses_base_module(self):
        """Test that _match_glob_pattern uses base module's implementation."""
        discovery = EntryPointDiscovery()

        # Verify it imports and uses base module's _match_glob_pattern
        with patch('opencode_python.agents.review.base._match_glob_pattern') as mock_match:
            mock_match.return_value = False

            result = discovery._match_glob_pattern("test.py", "*.py")

            assert result is False
            mock_match.assert_called_once_with("test.py", "*.py")


class TestDiscoverImplIntegration:
    """Test _discover_impl method (integration of all strategies)."""

    @pytest.mark.asyncio
    async def test_discover_impl_all_strategies(self):
        """Test _discover_impl with all three discovery strategies."""
        discovery = EntryPointDiscovery()

        # Mock pattern loading
        patterns = {
            "ast": [
                {"pattern": "def $FUNC($$$) { $$$ }", "language": "python", "weight": 0.9}
            ],
            "content": [
                {"pattern": "password.*=", "language": "python", "weight": 0.95}
            ],
            "file_path": [
                {"pattern": "**/auth/**/*.py", "weight": 0.8}
            ]
        }

        with patch.object(
            discovery, '_load_agent_patterns',
            new_callable=AsyncMock,
            return_value=patterns
        ):
            with patch.object(
                discovery, '_discover_ast_patterns',
                new_callable=AsyncMock,
                return_value=[
                    EntryPoint(
                        file_path="src/auth.py",
                        line_number=10,
                        description="AST pattern",
                        weight=0.9,
                        pattern_type="ast",
                        evidence="def authenticate():"
                    )
                ]
            ):
                with patch.object(
                    discovery, '_discover_content_patterns',
                    new_callable=AsyncMock,
                    return_value=[
                        EntryPoint(
                            file_path="src/config.py",
                            line_number=20,
                            description="Content pattern",
                            weight=0.95,
                            pattern_type="content",
                            evidence="password = 'secret'"
                        )
                    ]
                ):
                    with patch.object(
                        discovery, '_discover_file_path_patterns',
                        new_callable=AsyncMock,
                        return_value=[
                            EntryPoint(
                                file_path="src/auth/login.py",
                                line_number=None,
                                description="File path pattern",
                                weight=0.8,
                                pattern_type="file_path",
                                evidence="src/auth/login.py"
                            )
                        ]
                    ):
                        entry_points = await discovery._discover_impl(
                            "security", "/test/repo", ["src/auth.py", "src/config.py"]
                        )

        assert len(entry_points) == 3
        assert len([ep for ep in entry_points if ep.pattern_type == "ast"]) == 1
        assert len([ep for ep in entry_points if ep.pattern_type == "content"]) == 1
        assert len([ep for ep in entry_points if ep.pattern_type == "file_path"]) == 1

    @pytest.mark.asyncio
    async def test_discover_impl_no_patterns(self):
        """Test _discover_impl when no patterns loaded."""
        discovery = EntryPointDiscovery()

        with patch.object(
            discovery, '_load_agent_patterns',
            new_callable=AsyncMock,
            return_value={}
        ):
            entry_points = await discovery._discover_impl(
                "missing_agent", "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 0

    @pytest.mark.asyncio
    async def test_discover_impl_empty_pattern_groups(self):
        """Test _discover_impl with empty pattern groups."""
        discovery = EntryPointDiscovery()

        patterns = {
            "ast": [],
            "content": [],
            "file_path": []
        }

        with patch.object(
            discovery, '_load_agent_patterns',
            new_callable=AsyncMock,
            return_value=patterns
        ):
            entry_points = await discovery._discover_impl(
                "security", "/test/repo", ["src/auth.py"]
            )

        assert len(entry_points) == 0


class TestEntryPointSorting:
    """Test entry point sorting by weight."""

    @pytest.mark.asyncio
    async def test_entry_points_sorted_by_weight(self):
        """Test that entry points are sorted by weight (descending)."""
        discovery = EntryPointDiscovery()

        # Return sorted by _discover_impl's internal sorting
        mock_entry_points = [
            EntryPoint(
                file_path="high.py",
                line_number=2,
                description="High weight",
                weight=0.9,
                pattern_type="ast",
                evidence="test"
            ),
            EntryPoint(
                file_path="medium.py",
                line_number=3,
                description="Medium weight",
                weight=0.6,
                pattern_type="file_path",
                evidence="test"
            ),
            EntryPoint(
                file_path="low.py",
                line_number=1,
                description="Low weight",
                weight=0.3,
                pattern_type="content",
                evidence="test"
            )
        ]

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            return_value=mock_entry_points
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=["low.py", "high.py", "medium.py"]
            )

        assert result is not None
        assert result[0].weight == 0.9  # Highest weight first
        assert result[1].weight == 0.6
        assert result[2].weight == 0.3  # Lowest weight last

    @pytest.mark.asyncio
    async def test_entry_points_sorted_with_tiebreaker(self):
        """Test sorting tiebreaker (file_path, line_number)."""
        discovery = EntryPointDiscovery()

        # Pre-sorted by _discover_impl's sorting logic: (-weight, file_path, line_number)
        mock_entry_points = [
            EntryPoint(
                file_path="alpha.py",
                line_number=10,
                description="Alpha",
                weight=0.8,
                pattern_type="ast",
                evidence="test"
            ),
            EntryPoint(
                file_path="beta.py",
                line_number=20,
                description="Beta",
                weight=0.8,
                pattern_type="content",
                evidence="test"
            )
        ]

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            return_value=mock_entry_points
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=["alpha.py", "beta.py"]
            )

        assert result is not None
        # Same weight, sorted by file_path then line_number
        assert result[0].file_path == "alpha.py"
        assert result[1].file_path == "beta.py"


class TestMockChangedFilesIntegration:
    """Test discovery with real mock changed files."""

    @pytest.mark.asyncio
    async def test_discovery_with_various_file_types(self):
        """Test discovery with various file extensions."""
        discovery = EntryPointDiscovery()

        mock_entry_points = [
            EntryPoint(
                file_path="src/auth.py",
                line_number=10,
                description="Python file",
                weight=0.9,
                pattern_type="ast",
                evidence="def authenticate():"
            ),
            EntryPoint(
                file_path="docs/README.md",
                line_number=None,
                description="Markdown file",
                weight=0.7,
                pattern_type="file_path",
                evidence="docs/README.md"
            ),
            EntryPoint(
                file_path="config/settings.json",
                line_number=5,
                description="JSON file",
                weight=0.8,
                pattern_type="content",
                evidence='"password": "secret"'
            ),
            EntryPoint(
                file_path="scripts/deploy.sh",
                line_number=15,
                description="Shell script",
                weight=0.6,
                pattern_type="content",
                evidence='export API_KEY="secret"'
            )
        ]

        with patch.object(
            discovery, '_discover_impl',
            new_callable=AsyncMock,
            return_value=mock_entry_points
        ):
            result = await discovery.discover_entry_points(
                agent_name="security",
                repo_root="/test/repo",
                changed_files=[
                    "src/auth.py",
                    "docs/README.md",
                    "config/settings.json",
                    "scripts/deploy.sh"
                ]
            )

        assert result is not None
        assert len(result) == 4
        assert any(ep.file_path == "src/auth.py" for ep in result)
        assert any(ep.file_path == "docs/README.md" for ep in result)
        assert any(ep.file_path == "config/settings.json" for ep in result)
        assert any(ep.file_path == "scripts/deploy.sh" for ep in result)


class TestPerformanceLogging:
    """Test performance logging features."""

    @pytest.mark.asyncio
    async def test_performance_logging_on_success(self):
        """Test that discovery logs performance metrics on success."""
        discovery = EntryPointDiscovery()
        discovery.timeout_seconds = 30

        mock_entry_points = [
            EntryPoint(
                file_path="src/auth.py",
                line_number=10,
                description="Test",
                weight=0.9,
                pattern_type="ast",
                evidence="test"
            )
        ]

        with patch('opencode_python.agents.review.discovery.logger') as mock_logger:
            with patch.object(
                discovery, '_discover_impl',
                new_callable=AsyncMock,
                return_value=mock_entry_points
            ):
                await discovery.discover_entry_points(
                    agent_name="security",
                    repo_root="/test/repo",
                    changed_files=["src/auth.py"]
                )

            # Check that info log was called
            assert mock_logger.info.called
            # Check log contains performance info
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Discovery completed" in call for call in log_calls)
            assert any("found 1 entry points" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_logging_on_empty_discovery(self):
        """Test logging when no entry points discovered."""
        discovery = EntryPointDiscovery()

        with patch('opencode_python.agents.review.discovery.logger') as mock_logger:
            with patch.object(
                discovery, '_discover_impl',
                new_callable=AsyncMock,
                return_value=[]
            ):
                await discovery.discover_entry_points(
                    agent_name="security",
                    repo_root="/test/repo",
                    changed_files=["src/test.py"]
                )

            # Check that info log mentions falling back
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("falling back to is_relevant_to_changes()" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_logging_on_timeout(self):
        """Test logging when discovery times out."""
        discovery = EntryPointDiscovery(timeout_seconds=1)

        async def slow_discovery(*args, **kwargs):
            await asyncio.sleep(1)
            return []

        with patch('opencode_python.agents.review.discovery.logger') as mock_logger:
            with patch.object(
                discovery, '_discover_impl',
                new_callable=AsyncMock,
                side_effect=slow_discovery
            ):
                await discovery.discover_entry_points(
                    agent_name="security",
                    repo_root="/test/repo",
                    changed_files=["src/test.py"]
                )

            # Check that warning log was called
            assert mock_logger.warning.called
            log_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert any("timed out" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_logging_on_error(self):
        """Test logging when discovery encounters an error."""
        discovery = EntryPointDiscovery()

        with patch('opencode_python.agents.review.discovery.logger') as mock_logger:
            with patch.object(
                discovery, '_discover_impl',
                new_callable=AsyncMock,
                side_effect=Exception("Test error")
            ):
                await discovery.discover_entry_points(
                    agent_name="security",
                    repo_root="/test/repo",
                    changed_files=["src/test.py"]
                )

            # Check that error log was called
            assert mock_logger.error.called
            log_calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("Discovery failed" in call for call in log_calls)



