"""Tests for repository configuration discovery utilities."""
import tempfile
from pathlib import Path

import pytest

from dawn_kestrel.agents.review.utils.config import RepoConfigDiscovery


class TestRepoConfigDiscovery:
    """Test suite for RepoConfigDiscovery class."""

    def test_init_with_default_repo_root(self):
        discovery = RepoConfigDiscovery()
        assert discovery.repo_root == Path(".").resolve()

    def test_init_with_custom_repo_root(self):
        discovery = RepoConfigDiscovery("/tmp")
        assert discovery.repo_root == Path("/tmp").resolve()

    def test_read_pyproject_toml_existing(self, temp_repo):
        pyproject_content = """
[project]
name = "test-project"

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.read_pyproject_toml()

        assert config is not None
        assert "project" in config
        assert "tool" in config
        assert config["tool"]["ruff"]["line-length"] == 100
        assert config["tool"]["mypy"]["strict"] is True

    def test_read_pyproject_toml_missing(self, temp_repo):
        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.read_pyproject_toml()
        assert config == {}

    def test_read_pyproject_toml_malformed(self, temp_repo):
        (temp_repo / "pyproject.toml").write_text("invalid [toml content")

        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.read_pyproject_toml()
        assert config == {}

    def test_discover_lint_commands_ruff(self, temp_repo):
        pyproject_content = """
[tool.ruff]
line-length = 100
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "ruff check" in commands

    def test_discover_lint_commands_ruff_format(self, temp_repo):
        pyproject_content = """
[tool.ruff]
line-length = 100

[tool.ruff.format]
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "ruff check" in commands
        assert "ruff format --check" in commands

    def test_discover_lint_commands_black(self, temp_repo):
        pyproject_content = """
[tool.black]
line-length = 88
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "black --check ." in commands

    def test_discover_lint_commands_flake8(self, temp_repo):
        pyproject_content = """
[tool.flake8]
max-line-length = 88
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "flake8" in commands

    def test_discover_lint_commands_multiple(self, temp_repo):
        pyproject_content = """
[tool.ruff]
line-length = 100

[tool.black]
line-length = 88
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "ruff check" in commands
        assert "black --check ." in commands

    def test_discover_lint_commands_standalone_ruff_toml(self, temp_repo):
        (temp_repo / ".ruff.toml").write_text("line-length = 100")

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "ruff check" in commands

    def test_discover_lint_commands_flake8_setup_cfg(self, temp_repo):
        setup_cfg_content = """
[flake8]
max-line-length = 88
"""
        (temp_repo / "setup.cfg").write_text(setup_cfg_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert "flake8" in commands

    def test_discover_lint_commands_no_config(self, temp_repo):
        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_lint_commands()

        assert commands == []

    def test_discover_test_commands_pytest(self, temp_repo):
        pyproject_content = """
[tool.pytest.ini_options]
testpaths = ["tests"]
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_test_commands()

        assert "pytest" in commands

    def test_discover_test_commands_pytest_async_mode(self, temp_repo):
        pyproject_content = """
[tool.pytest.ini_options]
asyncio_mode = "auto"
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_test_commands()

        assert "pytest" in commands
        assert "pytest --asyncio-mode=auto" in commands

    def test_discover_test_commands_tox(self, temp_repo):
        tox_ini_content = """
[tox]
envlist = py311

[testenv]
commands = pytest
"""
        (temp_repo / "tox.ini").write_text(tox_ini_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_test_commands()

        assert "tox" in commands

    def test_discover_test_commands_nox(self, temp_repo):
        (temp_repo / "noxfile.py").write_text("import nox")

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_test_commands()

        assert "nox" in commands

    def test_discover_test_commands_pytest_setup_cfg(self, temp_repo):
        setup_cfg_content = """
[tool:pytest]
testpaths = tests
"""
        (temp_repo / "setup.cfg").write_text(setup_cfg_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_test_commands()

        assert "pytest" in commands

    def test_discover_test_commands_no_config(self, temp_repo):
        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_test_commands()

        assert commands == []

    def test_discover_type_check_commands_mypy(self, temp_repo):
        pyproject_content = """
[tool.mypy]
strict = true
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_type_check_commands()

        assert "mypy --strict" in commands

    def test_discover_type_check_commands_mypy_basic(self, temp_repo):
        pyproject_content = """
[tool.mypy]
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_type_check_commands()

        assert "mypy" in commands
        assert "mypy --strict" not in commands

    def test_discover_type_check_commands_pyright(self, temp_repo):
        pyproject_content = """
[tool.pyright]
typeCheckingMode = "strict"
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_type_check_commands()

        assert "pyright" in commands

    def test_discover_type_check_commands_mypy_ini(self, temp_repo):
        (temp_repo / ".mypy.ini").write_text("[mypy]\nstrict = true")

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_type_check_commands()

        assert "mypy" in commands

    def test_discover_type_check_commands_pyrightconfig_json(self, temp_repo):
        (temp_repo / "pyrightconfig.json").write_text('{"typeCheckingMode": "strict"}')

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_type_check_commands()

        assert "pyright" in commands

    def test_discover_type_check_commands_no_config(self, temp_repo):
        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.discover_type_check_commands()

        assert commands == []

    def test_discover_ci_config_github_actions(self, temp_repo):
        github_dir = temp_repo / ".github" / "workflows"
        github_dir.mkdir(parents=True)

        workflow_content = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
"""
        (github_dir / "test.yml").write_text(workflow_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.discover_ci_config()

        assert "github" in config["platforms"]
        assert "CI" in config["workflows"]
        assert config["workflows"]["CI"]["file"] == ".github/workflows/test.yml"

    def test_discover_ci_config_gitlab_ci(self, temp_repo):
        (temp_repo / ".gitlab-ci.yml").write_text("stages:\n  - test")

        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.discover_ci_config()

        assert "gitlab" in config["platforms"]
        assert "gitlab" in config["workflows"]

    def test_discover_ci_config_azure_pipelines(self, temp_repo):
        (temp_repo / "azure-pipelines.yml").write_text("jobs:\n  - job: test")

        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.discover_ci_config()

        assert "azure" in config["platforms"]
        assert "azure" in config["workflows"]

    def test_discover_ci_config_no_ci(self, temp_repo):
        discovery = RepoConfigDiscovery(str(temp_repo))
        config = discovery.discover_ci_config()

        assert config["platforms"] == []
        assert config["workflows"] == {}

    def test_get_all_tool_commands(self, temp_repo):
        pyproject_content = """
[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
strict = true
"""
        (temp_repo / "pyproject.toml").write_text(pyproject_content)

        discovery = RepoConfigDiscovery(str(temp_repo))
        commands = discovery.get_all_tool_commands()

        assert "lint" in commands
        assert "test" in commands
        assert "type_check" in commands
        assert "ruff check" in commands["lint"]
        assert "pytest" in commands["test"]
        assert "mypy --strict" in commands["type_check"]


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        yield repo_path
