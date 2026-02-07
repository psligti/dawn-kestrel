"""Compatibility shim tests for rename migration."""

from __future__ import annotations

import importlib
import sys

import pytest


def test_import_opencode_python_warns_about_dawn_kestrel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing opencode_python should emit a deprecation warning."""
    monkeypatch.delenv("PYTHONWARNINGS", raising=False)
    sys.modules.pop("opencode_python", None)

    with pytest.warns(DeprecationWarning, match="dawn_kestrel"):
        importlib.import_module("opencode_python")


def test_opencode_review_help_alias_warns_and_shows_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Legacy opencode-review alias should warn and forward to review help."""
    from dawn_kestrel.cli.legacy import opencode_review

    monkeypatch.setattr(sys, "argv", ["opencode-review", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        opencode_review()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "dawn-kestrel review" in captured.err


def test_parkcode_alias_warns_and_shows_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Legacy parkcode alias should warn and show main help."""
    from dawn_kestrel.cli.legacy import parkcode

    monkeypatch.setattr(sys, "argv", ["parkcode", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        parkcode()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "dawn-kestrel" in captured.err


def test_opencode_review_generate_docs_alias_warns_and_shows_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Legacy opencode-review-generate-docs alias should warn and forward to docs help."""
    from dawn_kestrel.cli.legacy import opencode_review_generate_docs

    monkeypatch.setattr(sys, "argv", ["opencode-review-generate-docs", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        opencode_review_generate_docs()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "dawn-kestrel docs" in captured.err
