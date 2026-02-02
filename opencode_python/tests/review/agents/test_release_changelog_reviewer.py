"""Tests for ReleaseChangelogReviewer."""
from __future__ import annotations

from pathlib import Path
import pytest
from unittest.mock import Mock, AsyncMock

from opencode_python.agents.review.agents.changelog import ReleaseChangelogReviewer
from opencode_python.agents.review.base import ReviewContext


@pytest.mark.asyncio
async def test_review_creates_ai_session_and_calls_process_message(tmp_path: Path):
    """Test that review() creates AISession and calls process_message."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    diff = """diff --git a/src/api.py b/src/api.py
+++ b/src/api.py
@@ -1,1 +1,1 @@
- def api_get(id: int) -> str:
+ def api_get(user_id: int) -> str:
"""
    context = ReviewContext(
        changed_files=["src/api.py"],
        diff=diff,
        repo_root=str(tmp_path),
    )

    # Mock AISession
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    # Create expected ReviewOutput JSON response
    expected_output = {
        "agent": "release_changelog",
        "summary": "Breaking changes detected but CHANGELOG not updated",
        "severity": "critical",
        "scope": {
            "relevant_files": ["src/api.py"],
            "ignored_files": [],
            "reasoning": "Analyzed 1 relevant files for release hygiene. Breaking changes found in src/api.py but no CHANGELOG file exists."
        },
        "findings": [
            {
                "id": "release-changelog-not-updated-for-breaking",
                "title": "Breaking changes detected but CHANGELOG not updated",
                "severity": "critical",
                "confidence": "high",
                "owner": "dev",
                "estimate": "M",
                "evidence": "Breaking changes found in src/api.py but CHANGELOG not in changed files",
                "risk": "Users will not be aware of breaking changes",
                "recommendation": "Update CHANGELOG.md to document breaking changes"
            }
        ],
        "merge_gate": {
            "decision": "needs_changes",
            "must_fix": ["release-changelog-not-updated-for-breaking"],
            "should_fix": [],
            "notes_for_coding_agent": ["Add CHANGELOG entry for user-visible changes"]
        }
    }

    # Mock the response from LLM
    from opencode_python.core.models import Message
    mock_response_message = Mock(spec=Message)
    mock_response_message.text = str(expected_output).replace("'", '"')
    mock_ai_session.process_message.return_value = mock_response_message

    # Mock AISession constructor to return our mock
    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review
        output = await reviewer.review(context)

    # Verify AISession.process_message was called
    assert mock_ai_session.process_message.called

    # Verify the output has the expected structure
    assert output.agent == "release_changelog"
    assert output.severity == "critical"
    assert len(output.findings) == 1


@pytest.mark.asyncio
async def test_review_handles_missing_api_key_by_raising_exception(tmp_path: Path):
    """Test that review() raises ValueError when API key is missing."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    context = ReviewContext(
        changed_files=["src/api.py"],
        diff="+ new function",
        repo_root=str(tmp_path),
    )

    # Mock AISession to raise ValueError for missing API key
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        if not api_key:
            raise ValueError("API key not provided")
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review - should raise ValueError
        with pytest.raises(ValueError, match="API key not provided"):
            await reviewer.review(context)


@pytest.mark.asyncio
async def test_review_handles_invalid_json_response(tmp_path: Path):
    """Test that review() returns error ReviewOutput for invalid JSON."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    context = ReviewContext(
        changed_files=["src/api.py"],
        diff="+ new function",
        repo_root=str(tmp_path),
    )

    # Mock AISession to return invalid JSON
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    from opencode_python.core.models import Message
    mock_response_message = Mock(spec=Message)
    mock_response_message.text = "This is not valid JSON"
    mock_ai_session.process_message.return_value = mock_response_message

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review - should handle error gracefully
        output = await reviewer.review(context)

        # Verify error handling
        assert output.agent == "release_changelog"
        assert output.severity == "critical"
        assert "Error parsing LLM response" in output.summary or "validation error" in output.scope.reasoning.lower()


@pytest.mark.asyncio
async def test_review_handles_timeout_error_by_raising_exception(tmp_path: Path):
    """Test that review() raises TimeoutError for LLM timeouts."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    context = ReviewContext(
        changed_files=["src/api.py"],
        diff="+ new function",
        repo_root=str(tmp_path),
    )

    # Mock AISession to raise TimeoutError
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()
    mock_ai_session.process_message.side_effect = TimeoutError("LLM request timed out")

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review - should raise TimeoutError
        with pytest.raises(TimeoutError, match="LLM request timed out"):
            await reviewer.review(context)


@pytest.mark.asyncio
async def test_review_with_no_findings_returns_merge_severity(tmp_path: Path):
    """Test that review() returns merge severity when no findings."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    diff = """diff --git a/src/utils.py b/src/utils.py
+++ b/src/utils.py
@@ -1,1 +1,1 @@
- def helper():
+ def helper():
"""
    context = ReviewContext(
        changed_files=["src/utils.py"],
        diff=diff,
        repo_root=str(tmp_path),
    )

    # Mock AISession to return empty findings
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    from opencode_python.core.models import Message
    mock_response_message = Mock(spec=Message)
    mock_response_message.text = '''{
        "agent": "release_changelog",
        "summary": "Release hygiene review passed",
        "severity": "merge",
        "scope": {
            "relevant_files": ["src/utils.py"],
            "ignored_files": [],
            "reasoning": "Analyzed 1 relevant files for release hygiene. No user-visible changes detected."
        },
        "findings": [],
        "merge_gate": {
            "decision": "approve",
            "must_fix": [],
            "should_fix": [],
            "notes_for_coding_agent": []
        }
    }'''
    mock_ai_session.process_message.return_value = mock_response_message

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review
        output = await reviewer.review(context)

        # Verify merge/approve decision
        assert output.severity == "merge"
        assert output.merge_gate.decision == "approve"
        assert len(output.findings) == 0


@pytest.mark.asyncio
async def test_review_includes_system_prompt_and_context_in_message(tmp_path: Path):
    """Test that review() includes system prompt and formatted context in message."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    context = ReviewContext(
        changed_files=["src/api.py"],
        diff="+ new function",
        repo_root=str(tmp_path),
    )

    # Mock AISession
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    from opencode_python.core.models import Message
    mock_response_message = Mock(spec=Message)
    mock_response_message.text = '''{
        "agent": "release_changelog",
        "summary": "Test",
        "severity": "merge",
        "scope": {"relevant_files": ["src/api.py"], "ignored_files": [], "reasoning": "Test"},
        "findings": [],
        "merge_gate": {"decision": "approve", "must_fix": [], "should_fix": [], "notes_for_coding_agent": []}
    }'''
    mock_ai_session.process_message.return_value = mock_response_message

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review
        await reviewer.review(context)

        # Verify AISession.process_message was called
        assert mock_ai_session.process_message.called

        # Verify system prompt is in the message
        call_args = mock_ai_session.process_message.call_args
        user_message = call_args[0][0]
        assert "Release & Changelog Review Subagent" in user_message or "Release & Changelog Review" in user_message

        # Verify context is included
        assert "src/api.py" in user_message


@pytest.mark.asyncio
async def test_review_with_breaking_change_finding(tmp_path: Path):
    """Test that review() correctly returns breaking change findings."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    diff = """diff --git a/src/api.py b/src/api.py
+++ b/src/api.py
@@ -1,1 +1,1 @@
- def api_get(id: int) -> str:
+ def api_get(user_id: int) -> str:
"""
    context = ReviewContext(
        changed_files=["src/api.py"],
        diff=diff,
        repo_root=str(tmp_path),
    )

    # Mock AISession to return breaking change finding
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    from opencode_python.core.models import Message
    mock_response_message = Mock(spec=Message)
    mock_response_message.text = '''{
        "agent": "release_changelog",
        "summary": "Breaking changes detected but no CHANGELOG found",
        "severity": "critical",
        "scope": {
            "relevant_files": ["src/api.py"],
            "ignored_files": [],
            "reasoning": "Breaking changes found but no CHANGELOG file exists."
        },
        "findings": [
            {
                "id": "release-no-changelog-for-breaking",
                "title": "Breaking changes detected but no CHANGELOG found",
                "severity": "critical",
                "confidence": "high",
                "owner": "dev",
                "estimate": "M",
                "evidence": "Breaking changes found in src/api.py:1 - function signature change",
                "risk": "Users will not be aware of breaking changes",
                "recommendation": "Create a CHANGELOG file and document all breaking changes"
            }
        ],
        "merge_gate": {
            "decision": "needs_changes",
            "must_fix": ["release-no-changelog-for-breaking"],
            "should_fix": [],
            "notes_for_coding_agent": ["Add CHANGELOG entry for user-visible changes"]
        }
    }'''
    mock_ai_session.process_message.return_value = mock_response_message

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review
        output = await reviewer.review(context)

        # Verify breaking change finding
        assert output.severity == "critical"
        assert len(output.findings) == 1
        assert output.findings[0].id == "release-no-changelog-for-breaking"
        assert output.findings[0].severity == "critical"


@pytest.mark.asyncio
async def test_review_with_version_bump_warning(tmp_path: Path):
    """Test that review() correctly returns version bump warning."""
    from opencode_python.ai_session import AISession
    from opencode_python.core.models import Session

    reviewer = ReleaseChangelogReviewer()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nversion = \"1.2.3\"\n")

    context = ReviewContext(
        changed_files=["pyproject.toml"],
        diff="+ version = \"1.2.3\"",
        repo_root=str(tmp_path),
    )

    # Mock AISession to return version bump warning
    mock_ai_session = Mock(spec=AISession)
    mock_ai_session.process_message = AsyncMock()

    from opencode_python.core.models import Message
    mock_response_message = Mock(spec=Message)
    mock_response_message.text = '''{
        "agent": "release_changelog",
        "summary": "Version bumped to 1.2.3 but no API changes detected",
        "severity": "warning",
        "scope": {
            "relevant_files": ["pyproject.toml"],
            "ignored_files": [],
            "reasoning": "Version is 1.2.3 but no API or breaking changes found in diff"
        },
        "findings": [
            {
                "id": "release-version-bump-without-changes",
                "title": "Version bumped to 1.2.3 but no API changes detected",
                "severity": "warning",
                "confidence": "medium",
                "owner": "dev",
                "estimate": "S",
                "evidence": "File: pyproject.toml:1 - Version is 1.2.3 but no API or breaking changes found in diff",
                "risk": "Unnecessary version bumps may confuse users about release significance",
                "recommendation": "Verify if version bump is justified"
            }
        ],
        "merge_gate": {
            "decision": "approve",
            "must_fix": [],
            "should_fix": ["release-version-bump-without-changes"],
            "notes_for_coding_agent": ["Verify version bump is justified"]
        }
    }'''
    mock_ai_session.process_message.return_value = mock_response_message

    def mock_ai_session_constructor(session, provider_id, model, api_key):
        return mock_ai_session

    with pytest.MonkeyPatch().context() as m:
        m.setattr("opencode_python.agents.review.agents.changelog.AISession", mock_ai_session_constructor)
        m.setattr(
            "opencode_python.agents.review.agents.changelog.Session",
            lambda **kwargs: Session(
                id="test-session-id",
                slug="security-review",
                project_id="review",
                directory="/tmp",
                title="Security Review",
                version="1.0"
            )
        )

        # Execute the review
        output = await reviewer.review(context)

        # Verify version bump warning
        assert output.severity == "warning"
        assert len(output.findings) == 1
        assert output.findings[0].id == "release-version-bump-without-changes"
        assert output.findings[0].severity == "warning"


def test_release_reviewer_metadata_helpers():
    """Test that get_agent_name(), get_system_prompt(), get_relevant_file_patterns() work."""
    reviewer = ReleaseChangelogReviewer()

    # Test get_agent_name()
    assert reviewer.get_agent_name() == "release_changelog"

    # Test get_system_prompt()
    system_prompt = reviewer.get_system_prompt()
    assert "Release & Changelog Review Subagent" in system_prompt or "Release & Changelog Review" in system_prompt

    # Test get_relevant_file_patterns()
    patterns = reviewer.get_relevant_file_patterns()
    assert "CHANGELOG*" in patterns
    assert "pyproject.toml" in patterns
    assert "**/*.py" in patterns
