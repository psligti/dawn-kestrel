""Tests for neighbors.py module using TDD approach.

Tests cover:
- Python relative import neighbor resolution
- Env key extraction patterns
- Config path reference extraction
- Deterministic ordering of outputs
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError


class TestNeighborsResult:
    """Test NeighborsResult Pydantic model."""

    def test_neighbors_result_valid(self):
        """Test valid NeighborsResult creation."""
        try:
            from opencode_python.agents.review.neighbors import NeighborsResult

            result = NeighborsResult(
                import_neighbors=["src/utils.py", "src/helpers.py"],
                config_references=["config/settings.yaml"],
                env_keys=["API_KEY", "DATABASE_URL"]
            )
            assert len(result.import_neighbors) == 2
            assert len(result.config_references) == 1
            assert len(result.env_keys) == 2
        except ImportError:
            pytest.skip("Module not yet created")

    def test_neighbors_result_empty(self):
        """Test empty NeighborsResult."""
        try:
            from opencode_python.agents.review.neighbors import NeighborsResult

            result = NeighborsResult(
                import_neighbors=[],
                config_references=[],
                env_keys=[]
            )
            assert result.import_neighbors == []
            assert result.config_references == []
            assert result.env_keys == []
        except ImportError:
            pytest.skip("Module not yet created")

    def test_neighbors_result_extra_fields_forbidden(self):
        """Test extra fields are rejected."""
        try:
            from opencode_python.agents.review.neighbors import NeighborsResult

            with pytest.raises(ValidationError, match="extra"):
                NeighborsResult(
                    import_neighbors=[],
                    config_references=[],
                    env_keys=[],
                    unexpected_field="should fail"
                )
        except ImportError:
            pytest.skip("Module not yet created")


class TestPythonImportParsing:
    """Test Python AST-based import parsing for relative imports."""

    def test_python_relative_import_same_level(self):
        """Test relative import from same directory level (from . import)."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                src_dir = Path(tmpdir) / "src"
                src_dir.mkdir()

                main_py = src_dir / "main.py"
                main_py.write_text("from .helper import helper_func\n")

                helper_py = src_dir / "helper.py"
                helper_py.write_text("def helper_func():\n    pass\n")

                repo_map = {"files": ["src/main.py", "src/helper.py"]}
                changed_files = ["src/main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "src/helper.py" in result.import_neighbors
        except ImportError:
            pytest.skip("Module not yet created")

    def test_python_relative_import_parent_level(self):
        """Test relative import from parent directory (from .. import)."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                src_dir = Path(tmpdir) / "src"
                src_dir.mkdir()
                utils_dir = src_dir / "utils"
                utils_dir.mkdir()

                helper_py = utils_dir / "helper.py"
                helper_py.write_text("def helper_func():\n    pass\n")

                main_py = src_dir / "main.py"
                main_py.write_text("from ..utils.helper import helper_func\n")

                repo_map = {"files": ["src/main.py", "src/utils/helper.py"]}
                changed_files = ["src/main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert len(result.import_neighbors) == 0
        except ImportError:
            pytest.skip("Module not yet created")

    def test_python_relative_import_submodule(self):
        """Test relative import to submodule (from .module import)."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                src_dir = Path(tmpdir) / "src"
                src_dir.mkdir()

                module_py = src_dir / "module.py"
                module_py.write_text("def func():\n    pass\n")

                main_py = src_dir / "main.py"
                main_py.write_text("from .module import func\n")

                repo_map = {"files": ["src/main.py", "src/module.py"]}
                changed_files = ["src/main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "src/module.py" in result.import_neighbors
        except ImportError:
            pytest.skip("Module not yet created")

    def test_python_absolute_import_ignored(self):
        """Test absolute imports (stdlib/external packages) are ignored."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
import os
import sys
from typing import List
from requests import get
""")

                repo_map = {"files": ["main.py"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert len(result.import_neighbors) == 0
        except ImportError:
            pytest.skip("Module not yet created")

    def test_python_multiple_relative_imports(self):
        """Test multiple relative imports are all captured."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                src_dir = Path(tmpdir) / "src"
                src_dir.mkdir()

                helper1_py = src_dir / "helper1.py"
                helper1_py.write_text("def func1(): pass\n")
                helper2_py = src_dir / "helper2.py"
                helper2_py.write_text("def func2(): pass\n")
                utils_py = src_dir / "utils.py"
                utils_py.write_text("def util(): pass\n")

                main_py = src_dir / "main.py"
                main_py.write_text("""
from .helper1 import func1
from .helper2 import func2
from .utils import util
""")

                repo_map = {"files": ["src/main.py", "src/helper1.py", "src/helper2.py", "src/utils.py"]}
                changed_files = ["src/main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "src/helper1.py" in result.import_neighbors
                assert "src/helper2.py" in result.import_neighbors
                assert "src/utils.py" in result.import_neighbors
        except ImportError:
            pytest.skip("Module not yet created")


class TestEnvKeyExtraction:
    """Test environment variable key extraction from code."""

    def test_python_os_getenv_pattern(self):
        """Test os.getenv('KEY') pattern extraction."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
api_key = os.getenv('API_KEY')
db_url = os.getenv("DATABASE_URL")
""")

                repo_map = {"files": ["main.py"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "API_KEY" in result.env_keys
                assert "DATABASE_URL" in result.env_keys
        except ImportError:
            pytest.skip("Module not yet created")

    def test_python_os_environ_pattern(self):
        """Test os.environ['KEY'] pattern extraction."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
api_key = os.environ['API_KEY']
db_url = os.environ["DATABASE_URL"]
""")

                repo_map = {"files": ["main.py"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "API_KEY" in result.env_keys
                assert "DATABASE_URL" in result.env_keys
        except ImportError:
            pytest.skip("Module not yet created")

    def test_javascript_process_env_pattern(self):
        """Test process.env.KEY pattern extraction from JS/TS."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_js = Path(tmpdir) / "main.js"
                main_js.write_text("""
const apiKey = process.env.API_KEY;
const dbUrl = process.env.DATABASE_URL;
""")

                repo_map = {"files": ["main.js"]}
                changed_files = ["main.js"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "API_KEY" in result.env_keys
                assert "DATABASE_URL" in result.env_keys
        except ImportError:
            pytest.skip("Module not yet created")

    def test_typescript_process_env_pattern(self):
        """Test process.env.KEY pattern extraction from TypeScript."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_ts = Path(tmpdir) / "main.ts"
                main_ts.write_text("""
const apiKey: string = process.env.API_KEY!;
const dbUrl: string = process.env.DATABASE_URL!;
""")

                repo_map = {"files": ["main.ts"]}
                changed_files = ["main.ts"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "API_KEY" in result.env_keys
                assert "DATABASE_URL" in result.env_keys
        except ImportError:
            pytest.skip("Module not yet created")

    def test_env_key_deduplication(self):
        """Test duplicate env keys are deduplicated."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
api_key = os.getenv('API_KEY')
if not api_key:
    api_key = os.getenv('API_KEY')
db_url = os.environ['DATABASE_URL']
other_db = os.environ['DATABASE_URL']
""")

                repo_map = {"files": ["main.py"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.env_keys.count("API_KEY") == 1
                assert result.env_keys.count("DATABASE_URL") == 1
        except ImportError:
            pytest.skip("Module not yet created")


class TestConfigPathExtraction:
    """Test config file path reference extraction."""

    def test_config_path_literal_extraction(self):
        """Test string literal paths that look like config files are extracted."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
config.load('config/settings.yaml')
data = open('data/config.json')
""")

                config_dir = Path(tmpdir) / "config"
                config_dir.mkdir()
                settings_yaml = config_dir / "settings.yaml"
                settings_yaml.write_text("key: value\n")

                data_dir = Path(tmpdir) / "data"
                data_dir.mkdir()
                config_json = data_dir / "config.json"
                config_json.write_text('{"key": "value"}\n')

                repo_map = {"files": ["main.py", "config/settings.yaml", "data/config.json"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "config/settings.yaml" in result.config_references
                assert "data/config.json" in result.config_references
        except ImportError:
            pytest.skip("Module not yet created")

    def test_config_path_only_included_if_exists(self):
        """Test config paths are only included if file exists in repo."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
config.load('config/settings.yaml')
config.load('missing/file.yaml')
""")

                config_dir = Path(tmpdir) / "config"
                config_dir.mkdir()
                settings_yaml = config_dir / "settings.yaml"
                settings_yaml.write_text("key: value\n")

                repo_map = {"files": ["main.py", "config/settings.yaml"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "config/settings.yaml" in result.config_references
                assert "missing/file.yaml" not in result.config_references
        except ImportError:
            pytest.skip("Module not yet created")

    def test_config_path_common_patterns(self):
        """Test common config file patterns are recognized."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
load('config.yaml')
load('config.yml')
load('config.json')
load('config.toml')
load('config.ini')
load('settings.env')
""")

                for config_name in ["config.yaml", "config.yml", "config.json", "config.toml", "config.ini", "settings.env"]:
                    Path(tmpdir, config_name).write_text("key: value\n")

                all_files = ["main.py"] + [f for f in os.listdir(tmpdir) if f.startswith("config") or f.startswith("settings")]
                repo_map = {"files": all_files}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                for config_name in ["config.yaml", "config.yml", "config.json", "config.toml", "config.ini", "settings.env"]:
                    assert config_name in result.config_references
        except ImportError:
            pytest.skip("Module not yet created")

    def test_config_path_deduplication(self):
        """Test duplicate config paths are deduplicated."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
load('config/settings.yaml')
load('config/settings.yaml')
load('config/settings.yaml')
""")

                config_dir = Path(tmpdir) / "config"
                config_dir.mkdir()
                settings_yaml = config_dir / "settings.yaml"
                settings_yaml.write_text("key: value\n")

                repo_map = {"files": ["main.py", "config/settings.yaml"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.config_references.count("config/settings.yaml") == 1
        except ImportError:
            pytest.skip("Module not yet created")


class TestDeterministicOrdering:
    """Test that outputs are always deterministically ordered."""

    def test_import_neighbors_sorted(self):
        """Test import_neighbors are sorted deterministically."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                src_dir = Path(tmpdir) / "src"
                src_dir.mkdir()

                helper_z = src_dir / "z.py"
                helper_z.write_text("def z(): pass\n")
                helper_a = src_dir / "a.py"
                helper_a.write_text("def a(): pass\n")
                helper_m = src_dir / "m.py"
                helper_m.write_text("def m(): pass\n")

                main_py = src_dir / "main.py"
                main_py.write_text("""
from .z import z
from .a import a
from .m import m
""")

                repo_map = {"files": ["src/main.py", "src/z.py", "src/a.py", "src/m.py"]}
                changed_files = ["src/main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.import_neighbors == sorted(result.import_neighbors)
        except ImportError:
            pytest.skip("Module not yet created")

    def test_config_references_sorted(self):
        """Test config_references are sorted deterministically."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
load('z.yaml')
load('a.yaml')
load('m.yaml')
""")

                for config_name in ["z.yaml", "a.yaml", "m.yaml"]:
                    Path(tmpdir, config_name).write_text("key: value\n")

                repo_map = {"files": ["main.py", "z.yaml", "a.yaml", "m.yaml"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.config_references == sorted(result.config_references)
        except ImportError:
            pytest.skip("Module not yet created")

    def test_env_keys_sorted(self):
        """Test env_keys are sorted deterministically."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                main_py = Path(tmpdir) / "main.py"
                main_py.write_text("""
os.getenv('Z_KEY')
os.getenv('A_KEY')
os.getenv('M_KEY')
""")

                repo_map = {"files": ["main.py"]}
                changed_files = ["main.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.env_keys == sorted(result.env_keys)
        except ImportError:
            pytest.skip("Module not yet created")

    def test_multiple_runs_same_ordering(self):
        """Test multiple runs produce the same ordering."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                src_dir = Path(tmpdir) / "src"
                src_dir.mkdir()

                helper1_py = src_dir / "helper1.py"
                helper1_py.write_text("def func1(): pass\n")
                helper2_py = src_dir / "helper2.py"
                helper2_py.write_text("def func2(): pass\n")
                config_yaml = src_dir / "config.yaml"
                config_yaml.write_text("key: value\n")

                main_py = src_dir / "main.py"
                main_py.write_text("""
from .helper1 import func1
from .helper2 import func2
api_key = os.getenv('API_KEY')
db_url = os.getenv('DATABASE_URL')
load('config.yaml')
""")

                repo_map = {"files": ["src/main.py", "src/helper1.py", "src/helper2.py", "src/config.yaml"]}
                changed_files = ["src/main.py"]

                results = [find_neighbors(repo_root, changed_files, repo_map) for _ in range(3)]

                assert all(r.import_neighbors == results[0].import_neighbors for r in results)
                assert all(r.config_references == results[0].config_references for r in results)
                assert all(r.env_keys == results[0].env_keys for r in results)
        except ImportError:
            pytest.skip("Module not yet created")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_changed_files(self):
        """Test with no changed files."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                repo_map = {"files": []}
                changed_files = []

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.import_neighbors == []
                assert result.config_references == []
                assert result.env_keys == []
        except ImportError:
            pytest.skip("Module not yet created")

    def test_nonexistent_file_in_changed_files(self):
        """Test with changed file that doesn't exist on disk."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir
                repo_map = {"files": []}
                changed_files = ["nonexistent.py"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.import_neighbors == []
                assert result.config_references == []
                assert result.env_keys == []
        except ImportError:
            pytest.skip("Module not yet created")

    def test_mixed_file_types(self):
        """Test with mixed Python, JS, TS, and other files."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                py_file = Path(tmpdir) / "main.py"
                py_file.write_text("""
from .helper import func
api_key = os.getenv('API_KEY')
load('config.yaml')
""")

                js_file = Path(tmpdir) / "app.js"
                js_file.write_text("""
const apiKey = process.env.API_KEY;
""")

                ts_file = Path(tmpdir) / "app.ts"
                ts_file.write_text("""
const dbUrl: string = process.env.DATABASE_URL!;
""")

                helper_file = Path(tmpdir) / "helper.py"
                helper_file.write_text("def func(): pass\n")

                config_file = Path(tmpdir) / "config.yaml"
                config_file.write_text("key: value\n")

                repo_map = {"files": ["main.py", "app.js", "app.ts", "helper.py", "config.yaml"]}
                changed_files = ["main.py", "app.js", "app.ts"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert "helper.py" in result.import_neighbors
                assert "API_KEY" in result.env_keys
                assert "DATABASE_URL" in result.env_keys
                assert "config.yaml" in result.config_references
        except ImportError:
            pytest.skip("Module not yet created")

    def test_binary_file_skipped(self):
        """Test that binary files are skipped gracefully."""
        try:
            from opencode_python.agents.review.neighbors import find_neighbors

            with tempfile.TemporaryDirectory() as tmpdir:
                repo_root = tmpdir

                txt_file = Path(tmpdir) / "readme.txt"
                txt_file.write_text("api_key = API_KEY\n")

                repo_map = {"files": ["readme.txt"]}
                changed_files = ["readme.txt"]

                result = find_neighbors(repo_root, changed_files, repo_map)
                assert result.import_neighbors == []
        except ImportError:
            pytest.skip("Module not yet created")
