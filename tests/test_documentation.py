"""Tests for documentation structure and examples (TDD: RED phase).

Tests verify:
- docs/getting-started.md exists with required sections
- docs/examples/ directory exists with all required examples
- All examples have valid Python syntax
- All examples execute without errors
- README.md links to documentation
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestGettingStartedDocumentation:
    """Tests for docs/getting-started.md structure."""

    def test_getting_started_file_exists(self) -> None:
        docs_path = Path("docs/getting-started.md")
        assert docs_path.exists(), "docs/getting-started.md does not exist"

    def test_getting_started_has_required_sections(self) -> None:
        docs_path = Path("docs/getting-started.md")
        content = docs_path.read_text()

        required_sections = [
            "# Getting Started",
            "## Installation",
            "## Quick Start",
            "## Async Client Usage",
            "## Sync Client Usage",
            "## Handler Configuration",
            "## Error Handling",
            "## Migration Guide",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_getting_started_has_code_examples(self) -> None:
        docs_path = Path("docs/getting-started.md")
        content = docs_path.read_text()

        assert "```python" in content, "Missing Python code examples"
        assert "from dawn_kestrel.sdk import" in content, "Missing SDK imports in examples"

    def test_getting_started_type_hints_present(self) -> None:
        docs_path = Path("docs/getting-started.md")
        content = docs_path.read_text()

        assert ": str" in content or ": int" in content, "Missing type hints in examples"


class TestExamplesDirectory:
    """Tests for docs/examples/ directory structure."""

    def test_examples_directory_exists(self) -> None:
        examples_dir = Path("docs/examples")
        assert examples_dir.exists(), "docs/examples/ directory does not exist"
        assert examples_dir.is_dir(), "docs/examples/ is not a directory"

    def test_basic_usage_example_exists(self) -> None:
        example_path = Path("docs/examples/basic_usage.py")
        assert example_path.exists(), "docs/examples/basic_usage.py does not exist"

    def test_sync_usage_example_exists(self) -> None:
        example_path = Path("docs/examples/sync_usage.py")
        assert example_path.exists(), "docs/examples/sync_usage.py does not exist"

    def test_cli_integration_example_exists(self) -> None:
        example_path = Path("docs/examples/cli_integration.py")
        assert example_path.exists(), "docs/examples/cli_integration.py does not exist"

    def test_tui_integration_example_exists(self) -> None:
        example_path = Path("docs/examples/tui_integration.py")
        assert example_path.exists(), "docs/examples/tui_integration.py does not exist"


class TestExampleScriptsValidity:
    """Tests for example Python files validity."""

    def test_basic_usage_syntax_valid(self) -> None:
        example_path = Path("docs/examples/basic_usage.py")

        try:
            with open(example_path) as f:
                compile(f.read(), example_path, "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {example_path}: {e}")

    def test_sync_usage_syntax_valid(self) -> None:
        example_path = Path("docs/examples/sync_usage.py")

        try:
            with open(example_path) as f:
                compile(f.read(), example_path, "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {example_path}: {e}")

    def test_cli_integration_syntax_valid(self) -> None:
        example_path = Path("docs/examples/cli_integration.py")

        try:
            with open(example_path) as f:
                compile(f.read(), example_path, "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {example_path}: {e}")

    def test_tui_integration_syntax_valid(self) -> None:
        example_path = Path("docs/examples/tui_integration.py")

        try:
            with open(example_path) as f:
                compile(f.read(), example_path, "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {example_path}: {e}")

    def test_examples_import_sdk(self) -> None:
        examples = [
            Path("docs/examples/basic_usage.py"),
            Path("docs/examples/sync_usage.py"),
            Path("docs/examples/cli_integration.py"),
            Path("docs/examples/tui_integration.py"),
        ]

        for example_path in examples:
            content = example_path.read_text()
            assert "from dawn_kestrel.sdk import" in content or \
                   "import dawn_kestrel.sdk" in content, \
                f"{example_path} does not import SDK"

    def test_examples_have_docstrings(self) -> None:
        examples = [
            Path("docs/examples/basic_usage.py"),
            Path("docs/examples/sync_usage.py"),
            Path("docs/examples/cli_integration.py"),
            Path("docs/examples/tui_integration.py"),
        ]

        for example_path in examples:
            content = example_path.read_text()
            assert '"""' in content or "'''" in content, \
                f"{example_path} is missing docstring"

    def test_examples_use_type_hints(self) -> None:
        examples = [
            Path("docs/examples/basic_usage.py"),
            Path("docs/examples/sync_usage.py"),
        ]

        for example_path in examples:
            content = example_path.read_text()
            assert ":" in content and "->" in content, \
                f"{example_path} should use type hints"


class TestExampleScriptsExecution:
    """Tests for example scripts execution."""

    @pytest.mark.slow
    def test_basic_usage_executes(self) -> None:
        example_path = Path("docs/examples/basic_usage.py")

        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, \
            f"{example_path} failed with return code {result.returncode}\n" \
            f"stdout: {result.stdout}\n" \
            f"stderr: {result.stderr}"

    @pytest.mark.slow
    def test_sync_usage_executes(self) -> None:
        example_path = Path("docs/examples/sync_usage.py")

        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, \
            f"{example_path} failed with return code {result.returncode}\n" \
            f"stdout: {result.stdout}\n" \
            f"stderr: {result.stderr}"

    @pytest.mark.slow
    def test_cli_integration_executes(self) -> None:
        example_path = Path("docs/examples/cli_integration.py")

        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, \
            f"{example_path} failed with return code {result.returncode}\n" \
            f"stdout: {result.stdout}\n" \
            f"stderr: {result.stderr}"

    @pytest.mark.slow
    def test_tui_integration_executes(self) -> None:
        example_path = Path("docs/examples/tui_integration.py")

        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, \
            f"{example_path} failed with return code {result.returncode}\n" \
            f"stdout: {result.stdout}\n" \
            f"stderr: {result.stderr}"


class TestREADMEUpdates:
    """Tests for README.md updates."""

    def test_readme_exists(self) -> None:
        readme_path = Path("README.md")
        assert readme_path.exists(), "README.md does not exist"

    def test_readme_has_getting_started_link(self) -> None:
        readme_path = Path("README.md")
        content = readme_path.read_text()

        assert "docs/getting-started.md" in content or \
               "Getting Started" in content, \
            "README.md should link to getting started documentation"

    def test_readme_has_examples_link(self) -> None:
        readme_path = Path("README.md")
        content = readme_path.read_text()

        assert "docs/examples/" in content or "Examples" in content, \
            "README.md should link to examples"
