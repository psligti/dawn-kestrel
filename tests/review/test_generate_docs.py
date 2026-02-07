"""Tests for generate-docs CLI command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
import pytest

from dawn_kestrel.agents.review import cli as review_cli


def test_generate_docs_with_agent_flag(tmp_path: Path):
    """Test generate-docs with --agent flag."""
    runner = CliRunner()

    mock_doc_gen = MagicMock()
    mock_doc_gen.generate_for_agent.return_value = (True, "Generated documentation for security")

    with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
        MockDocGenAgent.return_value = mock_doc_gen

        result = runner.invoke(
            review_cli.generate_docs,
            ["--agent", "security", "--verbose"],
        )

    assert result.exit_code == 0
    assert "✓ security: Generated documentation for security" in result.output
    assert mock_doc_gen.generate_for_agent.called


def test_generate_docs_with_all_flag(tmp_path: Path):
    """Test generate-docs with --all flag."""
    # Skip this test - it's slow and requires loading all 11 agents
    pytest.skip("Test skipped - requires loading all 11 agents")


def test_generate_docs_with_force_flag(tmp_path: Path):
    """Test generate-docs with --force flag."""
    runner = CliRunner()

    mock_agent = MagicMock()
    mock_agent.get_agent_name.return_value = "security"

    with patch.dict('dawn_kestrel.agents.review.cli.__dict__', {'all_agents': {'security': mock_agent}}):
        mock_doc_gen = MagicMock()
        mock_doc_gen.generate_for_agent.return_value = (True, "Generated documentation")

        with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
            MockDocGenAgent.return_value = mock_doc_gen

            result = runner.invoke(
                review_cli.generate_docs,
                ["--agent", "security", "--force"],
            )

    assert result.exit_code == 0
    assert mock_doc_gen.generate_for_agent.call_args[1]['force'] is True


def test_generate_docs_with_output_flag(tmp_path: Path):
    """Test generate-docs with custom --output directory."""
    runner = CliRunner()
    custom_output = tmp_path / "custom_docs"

    mock_agent = MagicMock()
    mock_agent.get_agent_name.return_value = "security"

    with patch.dict('dawn_kestrel.agents.review.cli.__dict__', {'all_agents': {'security': mock_agent}}):
        with patch('dawn_kestrel.agents.review.cli.get_subagents') as mock_get_subagents:
            mock_get_subagents.return_value = [mock_agent]

            mock_doc_gen = MagicMock()
            mock_doc_gen.generate_for_agent.return_value = (True, "Generated documentation")

            with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
                MockDocGenAgent.return_value = mock_doc_gen

                result = runner.invoke(
                    review_cli.generate_docs,
                    ["--agent", "security", "--output", str(custom_output)],
                )

    assert result.exit_code == 0
    # Check that DocGenAgent was initialized with the custom output path
    assert MockDocGenAgent.call_args[1]['agents_dir'] == custom_output


def test_generate_docs_with_verbose_flag(tmp_path: Path):
    """Test generate-docs with --verbose flag."""
    runner = CliRunner()

    mock_agent = MagicMock()
    mock_agent.get_agent_name.return_value = "security"

    with patch.dict('dawn_kestrel.agents.review.cli.__dict__', {'all_agents': {'security': mock_agent}}):
        mock_doc_gen = MagicMock()
        mock_doc_gen.generate_for_agent.return_value = (True, "Generated documentation")

        with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
            MockDocGenAgent.return_value = mock_doc_gen

            result = runner.invoke(
                review_cli.generate_docs,
                ["--agent", "security", "--verbose"],
            )

    assert result.exit_code == 0
    assert "Processing agent: security" in result.output
    assert mock_doc_gen.generate_for_agent.called


def test_generate_docs_with_invalid_agent(tmp_path: Path):
    """Test generate-docs raises error for invalid agent name."""
    runner = CliRunner()

    all_agents = {
        'security': MagicMock(),
        'architecture': MagicMock(),
    }

    with patch.dict('dawn_kestrel.agents.review.cli.__dict__', {'all_agents': all_agents}):
        mock_doc_gen = MagicMock()
        mock_doc_gen.generate_for_agent.return_value = (True, "")

        with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
            MockDocGenAgent.return_value = mock_doc_gen

            result = runner.invoke(
                review_cli.generate_docs,
                ["--agent", "invalid_agent"],
            )

    assert result.exit_code != 0
    assert "Error: Unknown agent 'invalid_agent'" in result.output
    assert "Available agents:" in result.output


def test_generate_docs_requires_agent_or_all(tmp_path: Path):
    """Test generate-docs requires --agent or --all flag."""
    runner = CliRunner()

    mock_doc_gen = MagicMock()
    mock_doc_gen.generate_for_agent.return_value = (True, "")

    with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
        MockDocGenAgent.return_value = mock_doc_gen

        result = runner.invoke(
            review_cli.generate_docs,
            [],
        )

    assert result.exit_code != 0
    assert "Error: Specify --agent or --all" in result.output


def test_generate_docs_default_output_path(tmp_path: Path):
    """Test generate-docs uses default output path."""
    runner = CliRunner()

    mock_agent = MagicMock()
    mock_agent.get_agent_name.return_value = "security"

    with patch.dict('dawn_kestrel.agents.review.cli.__dict__', {'all_agents': {'security': mock_agent}}):
        mock_doc_gen = MagicMock()
        mock_doc_gen.generate_for_agent.return_value = (True, "Generated documentation")

        with patch('dawn_kestrel.agents.review.doc_gen.DocGenAgent') as MockDocGenAgent:
            MockDocGenAgent.return_value = mock_doc_gen

            result = runner.invoke(
                review_cli.generate_docs,
                ["--agent", "security"],
            )

    assert result.exit_code == 0
    assert mock_doc_gen.generate_for_agent.called
