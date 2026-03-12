from __future__ import annotations

import pytest

from dawn_kestrel.core.security.input_validation import SecurityError, validate_command


def test_validate_command_blocks_shell_metacharacters_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DK_ALLOW_SHELL_METACHARACTERS", "0")

    with pytest.raises(SecurityError):
        validate_command("ls | wc -l", allowed_commands={"ls", "wc"})


def test_validate_command_allows_shell_metacharacters_with_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DK_ALLOW_SHELL_METACHARACTERS", "1")

    tokens = validate_command("ls | wc -l", allowed_commands={"ls", "wc"})

    assert tokens[0] == "ls"
    assert "|" in tokens
