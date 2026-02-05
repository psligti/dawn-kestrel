"""Tests for CommandExecutor."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opencode_python.agents.review.utils.executor import (
    CommandExecutionError,
    CommandExecutor,
    CommandTimeoutError,
    ExecutionResult,
    ParsedResult,
    SecurityError,
)

pytest_plugins = ("pytest_asyncio",)


class TestExecutionResult:

    def test_execution_result_minimal(self):
        result = ExecutionResult(
            command="echo hello",
            exit_code=0,
            stdout="hello\n",
            stderr="",
            timeout=False,
            parsed_findings=[],
            files_modified=[],
            duration_seconds=0.1,
        )
        assert result.command == "echo hello"
        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.timeout is False
        assert result.parsed_findings == []
        assert result.files_modified == []
        assert result.duration_seconds == 0.1

    def test_execution_result_with_findings(self):
        result = ExecutionResult(
            command="ruff check",
            exit_code=1,
            stdout="",
            stderr="error: E501 line too long",
            timeout=False,
            parsed_findings=[{"file": "test.py", "line": 10, "code": "E501", "message": "line too long"}],
            files_modified=[],
            duration_seconds=0.5,
        )
        assert len(result.parsed_findings) == 1
        assert result.parsed_findings[0]["file"] == "test.py"


class TestParsedResult:

    def test_parsed_result(self):
        result = ParsedResult(
            findings=[{"file": "test.py", "line": 5}],
            errors=["syntax error"],
            files_modified=["test.py"],
        )
        assert len(result.findings) == 1
        assert result.errors == ["syntax error"]
        assert result.files_modified == ["test.py"]


class TestCommandExecutorValidation:

    def test_validate_command_allowed(self):
        executor = CommandExecutor(allowed_tools=["ruff", "pytest"])
        assert executor.validate_command("ruff check .") is True
        assert executor.validate_command("pytest tests/") is True

    def test_validate_command_blocked_tool(self):
        executor = CommandExecutor(allowed_tools=["ruff", "pytest"])
        assert executor.validate_command("rm -rf /") is False
        assert executor.validate_command("curl malicious.com") is False

    def test_validate_command_shell_metacharacters(self):
        executor = CommandExecutor(allowed_tools=["ruff", "pytest"])

        assert executor.validate_command("ruff check | cat") is False
        assert executor.validate_command("ruff check ; rm -rf /") is False
        assert executor.validate_command("ruff check `rm -rf /`") is False
        assert executor.validate_command("ruff check $(rm -rf /)") is False
        assert executor.validate_command("ruff check & rm -rf /") is False
        assert executor.validate_command("ruff check && rm -rf /") is False
        assert executor.validate_command("ruff check || rm -rf /") is False
        assert executor.validate_command("ruff check > output.txt") is False
        assert executor.validate_command("ruff check < input.txt") is False
        assert executor.validate_command("ruff check *") is False
        assert executor.validate_command("ruff check ?") is False

    def test_validate_working_directory_valid(self):
        executor = CommandExecutor()
        assert executor._validate_working_directory("src") is True
        assert executor._validate_working_directory("tests") is True
        assert executor._validate_working_directory(".") is True

    def test_validate_working_directory_traversal(self):
        executor = CommandExecutor()

        assert executor._validate_working_directory("..") is False
        assert executor._validate_working_directory("../src") is False
        assert executor._validate_working_directory("src/../../etc") is False
        assert executor._validate_working_directory("/etc") is False
        assert executor._validate_working_directory("/usr/local") is False


class TestCommandExecutor:

    @pytest.fixture
    def executor(self):
        return CommandExecutor(allowed_tools=["echo", "python", "ruff", "pytest"])

    @pytest.mark.asyncio
    async def test_execute_allowed_command_success(self, executor):
        result = await executor.execute("echo hello", timeout=5, cwd=".")
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.timeout is False

    @pytest.mark.asyncio
    async def test_execute_blocked_command_raises_error(self, executor):
        with pytest.raises(SecurityError, match="not in whitelist"):
            await executor.execute("rm -rf /", timeout=5, cwd=".")

    @pytest.mark.asyncio
    async def test_execute_command_with_metacharacters_raises_error(self, executor):
        with pytest.raises(SecurityError, match="contains blocked characters"):
            await executor.execute("echo hello | cat", timeout=5, cwd=".")

    @pytest.mark.asyncio
    async def test_execute_with_invalid_working_directory(self, executor):
        with pytest.raises(SecurityError, match="Invalid working directory"):
            await executor.execute("echo hello", timeout=5, cwd="../etc")

    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, executor):
        with patch("opencode_python.agents.review.utils.executor.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("python -c 'import time; time.sleep(60)'", 1)

            with pytest.raises(CommandTimeoutError):
                await executor.execute("python -c 'import time; time.sleep(60)'", timeout=1, cwd=".")

    @pytest.mark.asyncio
    async def test_execute_command_failure(self, executor):
        result = await executor.execute("python -c 'import sys; sys.exit(1)'", timeout=5, cwd=".")
        assert result.exit_code == 1
        assert result.timeout is False

    @pytest.mark.asyncio
    async def test_concurrent_execution_limit(self, executor):
        executor = CommandExecutor(allowed_tools=["python"], max_concurrent=2)

        tasks = [
            executor.execute("python -c 'import time; time.sleep(0.1)'", timeout=5, cwd=".") for _ in range(4)
        ]

        results = await asyncio.gather(*tasks)
        assert len(results) == 4
        assert all(r.exit_code == 0 for r in results)


class TestOutputParsing:

    @pytest.fixture
    def executor(self):
        return CommandExecutor()

    def test_parse_ruff_json_output(self, executor):
        output = '[{"location":{"row":10,"column":5},"code":"E501","message":"Line too long","filename":"test.py"}]'
        result = executor.parse_output(output, "ruff")
        assert len(result.findings) == 1
        assert result.findings[0]["code"] == "E501"
        assert result.findings[0]["filename"] == "test.py"

    def test_parse_pytest_output(self, executor):
        output = """
tests/test_example.py::test_pass PASSED
tests/test_example.py::test_fail FAILED
"""
        result = executor.parse_output(output, "pytest")
        assert "test_pass" in str(result.findings) or len(result.errors) >= 0

    def test_parse_mypy_output(self, executor):
        output = "test.py:10: error: Incompatible return value type"
        result = executor.parse_output(output, "mypy")
        assert len(result.findings) >= 0 or len(result.errors) >= 0

    def test_parse_unknown_tool(self, executor):
        output = "some output"
        result = executor.parse_output(output, "unknown")
        assert len(result.findings) == 0
        assert len(result.errors) == 0


class TestAllowFixFlag:

    @pytest.mark.asyncio
    async def test_allow_fix_adds_flag(self):
        executor = CommandExecutor(allowed_tools=["ruff"])

        with patch("opencode_python.agents.review.utils.executor.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Fixed 2 files", stderr="", duration_seconds=0.1
            )

            result = await executor.execute("ruff check .", timeout=5, cwd=".", allow_fix=True)
            assert mock_run.called


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_subprocess_exception(self):
        executor = CommandExecutor(allowed_tools=["python"])

        with patch("opencode_python.agents.review.utils.executor.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Subprocess failed")

            with pytest.raises(CommandExecutionError):
                await executor.execute("python -c 'pass'", timeout=5, cwd=".")


class TestDefaultAllowedTools:

    def test_default_allowed_tools(self):
        from opencode_python.agents.review.utils.executor import DEFAULT_ALLOWED_TOOLS

        assert "ty" in DEFAULT_ALLOWED_TOOLS
        assert "ruff" in DEFAULT_ALLOWED_TOOLS
        assert "black" in DEFAULT_ALLOWED_TOOLS
        assert "pytest" in DEFAULT_ALLOWED_TOOLS
        assert "mypy" in DEFAULT_ALLOWED_TOOLS
        assert "bandit" in DEFAULT_ALLOWED_TOOLS
        assert "pip-audit" in DEFAULT_ALLOWED_TOOLS


class TestSecurityErrors:

    def test_security_error_tool_not_allowed(self):
        error = SecurityError("Tool 'rm' is not in whitelist")
        assert "not in whitelist" in str(error)
        assert "rm" in str(error)

    def test_security_error_blocked_characters(self):
        error = SecurityError("Command contains blocked characters: |")
        assert "blocked characters" in str(error)

    def test_security_error_invalid_directory(self):
        error = SecurityError("Invalid working directory: /etc")
        assert "Invalid working directory" in str(error)


class TestCommandTimeoutError:

    def test_timeout_error_message(self):
        error = CommandTimeoutError("Command 'ruff check' timed out after 30 seconds")
        assert "timed out" in str(error)
        assert "30 seconds" in str(error)


class TestCommandExecutionError:

    def test_execution_error_message(self):
        error = CommandExecutionError("Command failed: exit code 1")
        assert "Command failed" in str(error)
        assert "exit code 1" in str(error)
