"""
Tests for AuthReviewerAgent.

Tests cover:
- LLM analysis for JWT/OAuth validation issues
- Grep pattern matching for auth patterns (JWT, OAuth, tokens)
- Combined LLM + tool-based verification
- Mock test fixtures for auth code scenarios
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, Mock

import pytest

# Import the agent and related types
from dawn_kestrel.agents.review.subagents.auth_reviewer import (
    AUTH_PATTERNS,
    AuthReviewerAgent,
)
from dawn_kestrel.agents.review.tools import ToolExecutor, ToolResult
from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.llm import LLMResponse


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_grep_output():
    """Mock grep output for auth patterns."""
    return """tests/fixtures/auth.py:15:decoded = jwt.decode(token, verify=False)
tests/fixtures/auth.py:42:access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
tests/fixtures/auth.py:58:Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"""


@pytest.fixture
def mock_tool_executor():
    """Create a mock ToolExecutor for testing."""
    executor = Mock(spec=ToolExecutor)
    return executor


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient for testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_llm_response():
    """Mock LLM response with auth findings."""
    return LLMResponse(
        text=json.dumps(
            {
                "findings": [
                    {
                        "id": "llm_auth_001",
                        "severity": "high",
                        "title": "JWT decode without expiration check",
                        "description": "JWT token is decoded without checking the exp claim",
                        "evidence": "jwt.decode(token, secret, algorithms=['HS256'])",
                        "file_path": "auth/jwt_handler.py",
                        "line_number": 25,
                        "recommendation": "Always verify exp claim after JWT decode",
                        "requires_review": True,
                    }
                ],
                "summary": "Found 1 JWT validation issue: missing exp check",
            }
        ),
        usage=Mock(prompt_tokens=100, completion_tokens=200, total_tokens=300),
    )


@pytest.fixture
def mock_repo_root():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures_dir = os.path.join(tmpdir, "tests", "fixtures")
        os.makedirs(fixtures_dir, exist_ok=True)
        auth_file = os.path.join(fixtures_dir, "auth.py")
        with open(auth_file, "w") as f:
            f.write("decoded = jwt.decode(token, verify=False)\n")
            f.write('access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."\n')
            f.write("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\n")
        yield tmpdir


# =============================================================================
# Test: Grep Pattern Matching
# =============================================================================


def test_grep_auth_pattern_detection(mock_tool_executor, mock_grep_output, mock_repo_root):
    """Test grep finds auth patterns (JWT, OAuth, tokens)."""
    # First pattern matches, others return empty
    grep_result = ToolResult(
        success=True,
        stdout=mock_grep_output,
        stderr="",
        exit_code=0,
        findings=[
            SecurityFinding(
                id="grep_1",
                severity="high",
                title="Pattern matched in tests/fixtures/auth.py",
                description="Grep pattern matched at line 15",
                evidence="File: tests/fixtures/auth.py\nLine: 15\nMatch: jwt.decode(token, verify=False)",
                file_path="tests/fixtures/auth.py",
                line_number=15,
                recommendation="Review the matched pattern for security implications",
                confidence_score=0.60,
                requires_review=True,
            ),
        ],
    )

    empty_grep_result = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    side_effects = [grep_result] + [empty_grep_result] * (len(AUTH_PATTERNS) - 1)
    mock_tool_executor.execute_tool.side_effect = side_effects

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor)
    result = asyncio.run(agent.execute(repo_root=mock_repo_root))

    assert mock_tool_executor.execute_tool.call_count >= 1
    first_call = mock_tool_executor.execute_tool.call_args_list[0]
    assert first_call[1]["tool_name"] == "grep"
    assert "-E" in first_call[1]["args"]
    assert result.result is not None
    assert len(result.result["findings"]) >= 1
    assert result.agent_name == "auth_reviewer"


def test_grep_fallback_specific_files(mock_tool_executor, mock_repo_root):
    """Test grep with specific file list."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor)
    specific_files = ["tests/fixtures/auth.py", "src/auth/jwt.py"]
    result = asyncio.run(agent.execute(repo_root=mock_repo_root, files=specific_files))

    grep_calls = [
        call
        for call in mock_tool_executor.execute_tool.call_args_list
        if call[1]["tool_name"] == "grep"
    ]
    if grep_calls:
        grep_args = grep_calls[0][1]["args"]
        assert "tests/fixtures/auth.py" in grep_args
        assert "src/auth/jwt.py" in grep_args


def test_auth_patterns_defined():
    """Test that auth patterns are defined for grep."""
    assert len(AUTH_PATTERNS) > 0
    assert any("jwt" in pattern.lower() for pattern in AUTH_PATTERNS)
    assert any("oauth" in pattern.lower() or "access_token" in pattern for pattern in AUTH_PATTERNS)
    assert any("bearer" in pattern.lower() for pattern in AUTH_PATTERNS)


# =============================================================================
# Test: LLM Analysis
# =============================================================================


def test_llm_analysis_jwt_validation(
    mock_tool_executor, mock_llm_client, mock_llm_response, mock_repo_root
):
    """Test LLM analyzes JWT validation issues."""
    # Mock grep to return nothing (only test LLM)
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )
    mock_llm_client.complete.return_value = mock_llm_response

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor, llm_client=mock_llm_client)
    result = asyncio.run(agent.execute(repo_root=mock_repo_root))

    assert mock_llm_client.complete.called
    assert result.result is not None
    assert len(result.result["findings"]) >= 1
    assert "llm" in result.tools


def test_llm_analysis_no_llm_client(mock_tool_executor, mock_repo_root):
    """Test agent works without LLM client (tool-based only)."""
    # Only grep results
    grep_result = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    mock_tool_executor.execute_tool.return_value = grep_result

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor, llm_client=None)
    result = asyncio.run(agent.execute(repo_root=mock_repo_root))

    assert "llm" not in result.tools
    assert result.result is not None
    assert "grep" in result.tools


def test_llm_response_parsing_error(mock_llm_client, mock_repo_root):
    """Test LLM response parsing error is handled gracefully."""
    # Invalid JSON response
    mock_llm_client.complete.return_value = LLMResponse(
        text="This is not valid JSON",
        usage=Mock(prompt_tokens=100, completion_tokens=100, total_tokens=200),
    )

    agent = AuthReviewerAgent(llm_client=mock_llm_client)
    result = asyncio.run(agent.execute(repo_root=mock_repo_root))

    # Should not crash, but log warning and return only grep results
    assert result.result is not None


# =============================================================================
# Test: Combined LLM + Tool-based
# =============================================================================


def test_combined_llm_and_grep_analysis(
    mock_tool_executor, mock_llm_client, mock_llm_response, mock_grep_output, mock_repo_root
):
    """Test combined LLM and grep analysis."""
    # Grep results
    grep_result = ToolResult(
        success=True,
        stdout=mock_grep_output,
        stderr="",
        exit_code=0,
        findings=[
            SecurityFinding(
                id="grep_1",
                severity="high",
                title="Pattern matched in tests/fixtures/auth.py",
                description="Grep pattern matched at line 15",
                evidence="File: tests/fixtures/auth.py\nLine: 15\nMatch: jwt.decode(token, verify=False)",
                file_path="tests/fixtures/auth.py",
                line_number=15,
                recommendation="Review the matched pattern for security implications",
                confidence_score=0.60,
                requires_review=True,
            ),
        ],
    )

    empty_grep_result = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    mock_tool_executor.execute_tool.side_effect = [grep_result] + [empty_grep_result] * (
        len(AUTH_PATTERNS) - 1
    )
    mock_llm_client.complete.return_value = mock_llm_response

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor, llm_client=mock_llm_client)
    result = asyncio.run(agent.execute(repo_root=mock_repo_root))

    assert mock_tool_executor.execute_tool.called
    assert mock_llm_client.complete.called
    assert result.result is not None
    assert "grep" in result.tools
    assert "llm" in result.tools
    # Should have findings from both sources
    assert len(result.result["findings"]) >= 1


# =============================================================================
# Test: Agent Initialization and Structure
# =============================================================================


def test_agent_initialization_with_all_dependencies(mock_tool_executor, mock_llm_client):
    """Test agent can be initialized with ToolExecutor and LLMClient."""
    agent = AuthReviewerAgent(
        tool_executor=mock_tool_executor,
        llm_client=mock_llm_client,
    )
    assert agent.tool_executor == mock_tool_executor
    assert agent.llm_client == mock_llm_client


def test_agent_initialization_without_dependencies():
    """Test agent can be initialized without dependencies."""
    agent = AuthReviewerAgent()
    assert agent.tool_executor is not None
    assert isinstance(agent.tool_executor, ToolExecutor)
    assert agent.llm_client is None


def test_subagent_task_result_structure(
    mock_tool_executor, mock_llm_client, mock_llm_response, mock_repo_root
):
    """Test SubagentTask result has required structure."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )
    mock_llm_client.complete.return_value = mock_llm_response

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor, llm_client=mock_llm_client)
    result = asyncio.run(agent.execute(repo_root=mock_repo_root))

    assert result.task_id == "auth_reviewer_task"
    assert result.todo_id == "todo_auth_reviewer"
    assert result.agent_name == "auth_reviewer"
    assert "grep" in result.tools
    assert "llm" in result.tools
    assert result.result is not None
    assert "findings" in result.result
    assert "summary" in result.result
    assert isinstance(result.result["findings"], list)
    assert isinstance(result.result["summary"], str)
    assert "Auth code review completed" in result.result["summary"]


def test_execute_with_context_parameter(mock_tool_executor, mock_repo_root):
    """Test execute() accepts context parameter for LLM analysis."""
    mock_tool_executor.execute_tool.return_value = ToolResult(
        success=True,
        stdout="",
        stderr="",
        exit_code=0,
        findings=[],
    )

    agent = AuthReviewerAgent(tool_executor=mock_tool_executor)
    context = "Recent changes in authentication module"
    result = asyncio.run(agent.execute(repo_root=mock_repo_root, context=context))

    assert result.result is not None
    # Context is passed to LLM (not grep)
    assert result.agent_name == "auth_reviewer"
