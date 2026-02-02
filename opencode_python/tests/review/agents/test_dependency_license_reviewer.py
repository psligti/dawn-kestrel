"""Tests for DependencyLicenseReviewer."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from opencode_python.agents.review.agents.dependencies import DependencyLicenseReviewer
from opencode_python.agents.review.agents import dependencies as dependencies_module
from opencode_python.agents.review.base import ReviewContext


@pytest.mark.asyncio
async def test_dependency_reviewer_with_llm_findings():
    """Test LLM-based review with dependency issues found."""
    reviewer = DependencyLicenseReviewer()

    mock_llm_response = """{"agent":"dependencies","summary":"Found 2 critical, 1 warning dependency issue(s) - review required","severity":"critical","scope":{"relevant_files":["pyproject.toml","requirements.txt"],"ignored_files":["src/main.py"],"reasoning":"Dependency files changed - LLM analyzed new deps and version bumps"},"findings":[{"id":"dep-new-requests","title":"New dependency added: requests","severity":"warning","confidence":"high","owner":"dev","estimate":"S","evidence":"File: pyproject.toml | Added: requests","risk":"New dependency introduces supply chain risk and increases attack surface","recommendation":"Justify the need for this dependency and review its security posture"},{"id":"dep-loose-requests","title":"Loosened version pin: requests with ^2.31.0","severity":"critical","confidence":"high","owner":"dev","estimate":"M","evidence":"File: pyproject.toml | Line: 3 | requests = \\"^2.31.0\\"","risk":"Loosened version pins may cause non-reproducible builds","recommendation":"Use exact versions or strict constraints (~=) for reproducibility"},{"id":"dep-license-gpl","title":"Potentially incompatible license detected: GPL","severity":"critical","confidence":"medium","owner":"dev","estimate":"M","evidence":"File: pyproject.toml | Line: 4 | license = \\"GPL\\"","risk":"GPL license may conflict with project license policy","recommendation":"Review GPL license compatibility and consider alternative with compatible license"}],"merge_gate":{"decision":"needs_changes","must_fix":["dep-loose-requests","dep-license-gpl"],"should_fix":["dep-new-requests"],"notes_for_coding_agent":["Critical dependency issues detected - fix before merging","Review loosened version pins and license compatibility"]}}"""

    mock_message = MagicMock()
    mock_message.text = mock_llm_response

    with patch('opencode_python.agents.review.agents.dependencies.AISession') as mock_ai_session_class:
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message.return_value = mock_message
        mock_ai_session_class.return_value = mock_ai_session

        context = ReviewContext(
            changed_files=["pyproject.toml", "src/main.py"],
            diff="diff content",
            repo_root="/repo",
        )

        output = await reviewer.review(context)

        assert output.agent == "dependencies"
        assert output.severity == "critical"
        assert output.merge_gate.decision == "needs_changes"
        assert len(output.findings) == 3
        assert any("dep-new-requests" in f.id for f in output.findings)
        assert any("dep-loose-requests" in f.id for f in output.findings)
        assert any("dep-license-gpl" in f.id for f in output.findings)

        mock_ai_session_class.assert_called_once()
        call_kwargs = mock_ai_session_class.call_args[1]
        assert 'provider_id' in call_kwargs
        assert 'model' in call_kwargs
        assert 'api_key' in call_kwargs
        assert 'session' in call_kwargs


@pytest.mark.asyncio
async def test_dependency_reviewer_no_issues():
    """Test LLM-based review with no dependency issues."""
    reviewer = DependencyLicenseReviewer()

    mock_llm_response = """{"agent":"dependencies","summary":"No dependency issues found","severity":"merge","scope":{"relevant_files":["pyproject.toml"],"ignored_files":[],"reasoning":"Safe dependency version bump detected"},"findings":[],"merge_gate":{"decision":"approve","must_fix":[],"should_fix":[],"notes_for_coding_agent":[]}}"""

    mock_message = MagicMock()
    mock_message.text = mock_llm_response

    with patch('opencode_python.agents.review.agents.dependencies.AISession') as mock_ai_session_class:
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message.return_value = mock_message
        mock_ai_session_class.return_value = mock_ai_session

        context = ReviewContext(
            changed_files=["pyproject.toml"],
            diff="diff content",
            repo_root="/repo",
        )

        output = await reviewer.review(context)

        assert output.severity == "merge"
        assert output.merge_gate.decision == "approve"
        assert len(output.findings) == 0


@pytest.mark.asyncio
async def test_dependency_reviewer_skips_when_no_dependency_files():
    """Test that review skips when no dependency files are changed."""
    reviewer = DependencyLicenseReviewer()

    with patch('opencode_python.agents.review.agents.dependencies.AISession') as mock_ai_session_class:
        context = ReviewContext(
            changed_files=["src/app.py"],
            diff="+ print('hello')",
            repo_root="/repo",
        )

        output = await reviewer.review(context)

        assert output.severity == "merge"
        assert output.merge_gate.decision == "approve"
        assert "No dependency files changed" in output.summary

        # Should NOT call AISession when no relevant files
        mock_ai_session_class.assert_not_called()


@pytest.mark.asyncio
async def test_dependency_reviewer_timeout():
    """Test that timeout errors are propagated."""
    reviewer = DependencyLicenseReviewer()

    with patch('opencode_python.agents.review.agents.dependencies.AISession') as mock_ai_session_class:
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message.side_effect = asyncio.TimeoutError("LLM request timed out")
        mock_ai_session_class.return_value = mock_ai_session

        context = ReviewContext(
            changed_files=["pyproject.toml"],
            diff="diff content",
            repo_root="/repo",
        )

        with pytest.raises(asyncio.TimeoutError):
            await reviewer.review(context)


@pytest.mark.asyncio
async def test_dependency_reviewer_invalid_json():
    """Test handling of invalid JSON response from LLM."""
    reviewer = DependencyLicenseReviewer()

    mock_message = MagicMock()
    mock_message.text = "This is not valid JSON"

    with patch('opencode_python.agents.review.agents.dependencies.AISession') as mock_ai_session_class:
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message.return_value = mock_message
        mock_ai_session_class.return_value = mock_ai_session

        context = ReviewContext(
            changed_files=["pyproject.toml"],
            diff="diff content",
            repo_root="/repo",
        )

        output = await reviewer.review(context)

        assert output.agent == "dependencies"
        assert output.severity == "critical"
        assert output.merge_gate.decision == "needs_changes"
        assert "Error parsing LLM response" in output.summary


@pytest.mark.asyncio
async def test_dependency_reviewer_empty_response():
    """Test handling of empty response from LLM."""
    reviewer = DependencyLicenseReviewer()

    mock_message = MagicMock()
    mock_message.text = ""

    with patch('opencode_python.agents.review.agents.dependencies.AISession') as mock_ai_session_class:
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message.return_value = mock_message
        mock_ai_session_class.return_value = mock_ai_session

        context = ReviewContext(
            changed_files=["pyproject.toml"],
            diff="diff content",
            repo_root="/repo",
        )

        with pytest.raises(ValueError, match="Empty response from LLM"):
            await reviewer.review(context)


def test_dependency_reviewer_metadata():
    """Test agent metadata methods."""
    reviewer = DependencyLicenseReviewer()

    assert reviewer.get_agent_name() == "dependencies"
    assert reviewer.get_system_prompt() == dependencies_module.DEPENDENCY_SYSTEM_PROMPT
    assert "pyproject.toml" in reviewer.get_relevant_file_patterns()
    assert "requirements*.txt" in reviewer.get_relevant_file_patterns()
    assert "poetry.lock" in reviewer.get_relevant_file_patterns()
