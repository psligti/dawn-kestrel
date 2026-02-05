"""Unit tests for AgentRunner using Template Method pattern."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json

from opencode_python.core.harness.runner import (
    AgentRunner,
    ReviewAgentRunner,
    create_review_agent_runner,
)
from opencode_python.llm.client import LLMClient, LLMResponse
from opencode_python.context.builder import ContextBuilder
from opencode_python.tools.framework import ToolRegistry
from opencode_python.providers.base import TokenUsage, ModelInfo


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    """Fixture providing temporary base directory."""
    return tmp_path / "test_repo"


@pytest.fixture
def mock_llm_client():
    """Fixture providing mocked LLM client."""
    client = AsyncMock(spec=LLMClient)
    return client


@pytest.fixture
def context_builder(base_dir: Path) -> ContextBuilder:
    """Fixture providing context builder."""
    return ContextBuilder(base_dir=base_dir)


@pytest.fixture
def sample_agent_config():
    """Fixture providing sample agent configuration."""
    return {
        "name": "test-agent",
        "prompt": "You are a test agent.",
        "user_message": "Test input",
        "temperature": 0.7,
    }


@pytest.fixture
def sample_context_data():
    """Fixture providing sample review context data."""
    return {
        "repo_root": "/test/repo",
        "changed_files": ["file1.py", "file2.py"],
        "diff": "--- a/file1.py\n+++ b/file1.py\n@@ -1,1 +1,1 @@",
        "base_ref": "main",
        "head_ref": "feature",
        "pr_title": "Test PR",
        "pr_description": "Test PR description",
    }


@pytest.fixture
def sample_review_output():
    """Fixture providing sample review output JSON."""
    return {
        "agent": "test-reviewer",
        "summary": "No issues found",
        "severity": "merge",
        "scope": {
            "relevant_files": ["file1.py"],
            "ignored_files": [],
            "reasoning": "Reviewed all files",
        },
        "merge_gate": {
            "decision": "approve",
            "must_fix": [],
            "should_fix": [],
            "notes_for_coding_agent": [],
        },
    }


class TestAgentRunner:
    """Tests for base AgentRunner class."""

    @pytest.mark.asyncio
    async def test_run_executes_template_method(
        self,
        mock_llm_client: AsyncMock,
        context_builder: ContextBuilder,
        base_dir: Path,
        sample_agent_config: dict,
    ):
        """Test that run() executes all template method steps in order."""
        mock_llm_client.complete = AsyncMock(
            return_value=LLMResponse(
                text="Test response",
                usage=TokenUsage(input=10, output=20),
                model_info=None,
            )
        )

        class ConcreteRunner(AgentRunner[str]):
            def _parse_response(self, response: str, context) -> str:
                return response

        runner = ConcreteRunner(
            llm_client=mock_llm_client,
            context_builder=context_builder,
            base_dir=base_dir,
        )

        result = await runner.run(sample_agent_config)

        assert result == "Test response"
        assert mock_llm_client.complete.called

    @pytest.mark.asyncio
    async def test_build_context_default_implementation(
        self,
        mock_llm_client: AsyncMock,
        context_builder: ContextBuilder,
        base_dir: Path,
        sample_agent_config: dict,
    ):
        """Test default _build_context implementation."""
        class ConcreteRunner(AgentRunner[str]):
            def _parse_response(self, response: str, context) -> str:
                return response

        runner = ConcreteRunner(
            llm_client=mock_llm_client,
            context_builder=context_builder,
            base_dir=base_dir,
        )

        context = await runner._build_context(
            agent_config=sample_agent_config,
            tools=None,
            skills=[],
        )

        assert context is not None
        assert context.system_prompt == sample_agent_config.get("prompt")

    def test_prepare_messages_default_implementation(
        self,
        mock_llm_client: AsyncMock,
        context_builder: ContextBuilder,
        base_dir: Path,
    ):
        """Test default _prepare_messages implementation."""
        class ConcreteRunner(AgentRunner[str]):
            def _parse_response(self, response: str, context) -> str:
                return response

        runner = ConcreteRunner(
            llm_client=mock_llm_client,
            context_builder=context_builder,
            base_dir=base_dir,
        )

        agent_config = {"user_message": "Test message"}
        messages = runner._prepare_messages(None, agent_config)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_call_llm_default_implementation(
        self,
        mock_llm_client: AsyncMock,
        context_builder: ContextBuilder,
        base_dir: Path,
    ):
        """Test default _call_llm implementation."""
        mock_llm_client.complete = AsyncMock(
            return_value=LLMResponse(
                text="LLM response",
                usage=TokenUsage(input=5, output=10),
                model_info=None,
            )
        )

        class ConcreteRunner(AgentRunner[str]):
            def _parse_response(self, response: str, context) -> str:
                return response

        runner = ConcreteRunner(
            llm_client=mock_llm_client,
            context_builder=context_builder,
            base_dir=base_dir,
        )

        messages = [{"role": "user", "content": "Test"}]
        response = await runner._call_llm(messages, {})

        assert response == "LLM response"
        mock_llm_client.complete.assert_called_once()

    def test_parse_response_raises_not_implemented(
        self,
        mock_llm_client: AsyncMock,
        context_builder: ContextBuilder,
        base_dir: Path,
    ):
        """Test that _parse_response raises NotImplementedError if not overridden."""
        runner = AgentRunner(
            llm_client=mock_llm_client,
            context_builder=context_builder,
            base_dir=base_dir,
        )

        with pytest.raises(NotImplementedError, match="Subclasses must implement _parse_response"):
            runner._parse_response("test", None)


class TestReviewAgentRunner:
    """Tests for ReviewAgentRunner class."""

    @pytest.mark.asyncio
    async def test_run_review_formats_context_and_calls_llm(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
        sample_context_data: dict,
        sample_review_output: dict,
    ):
        """Test that run_review formats context and returns parsed output."""
        mock_llm_client.complete = AsyncMock(
            return_value=LLMResponse(
                text=json.dumps(sample_review_output),
                usage=TokenUsage(input=10, output=20),
                model_info=None,
            )
        )

        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        system_prompt = "You are a reviewer."
        result = await runner.run_review(
            system_prompt=system_prompt,
            context_data=sample_context_data,
        )

        assert result == sample_review_output
        assert result["agent"] == "test-reviewer"
        assert result["summary"] == "No issues found"
        mock_llm_client.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_review_handles_invalid_json(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
        sample_context_data: dict,
    ):
        """Test that run_review raises ValueError for invalid JSON response."""
        mock_llm_client.complete = AsyncMock(
            return_value=LLMResponse(
                text="Not valid JSON {{{",
                usage=TokenUsage(input=10, output=20),
                model_info=None,
            )
        )

        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        with pytest.raises(ValueError, match="invalid JSON"):
            await runner.run_review(
                system_prompt="You are a reviewer.",
                context_data=sample_context_data,
            )

    def test_prepare_messages_includes_system_prompt(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
    ):
        """Test that _prepare_messages includes system prompt."""
        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        from opencode_python.core.agent_types import AgentContext
        from opencode_python.core.models import Session

        session = Session(
            id="test",
            slug="test",
            project_id="test",
            directory="/test",
            title="Test",
            version="1.0",
        )

        context = AgentContext(
            system_prompt="Test system prompt",
            tools=ToolRegistry(),
            messages=[],
            memories=[],
            session=session,
            agent={},
            model="gpt-4",
        )

        agent_config = {"user_message": "User input"}
        messages = runner._prepare_messages(context, agent_config)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Test system prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User input"

    def test_parse_response_valid_json(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
        sample_review_output: dict,
    ):
        """Test _parse_response with valid JSON."""
        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        json_str = json.dumps(sample_review_output)
        result = runner._parse_response(json_str, None)

        assert result == sample_review_output
        assert result["agent"] == "test-reviewer"

    def test_parse_response_invalid_json(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
    ):
        """Test _parse_response with invalid JSON."""
        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        with pytest.raises(ValueError, match="invalid JSON"):
            runner._parse_response("Not JSON", None)

    def test_format_review_context_full_context(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
        sample_context_data: dict,
    ):
        """Test _format_review_context with full context data."""
        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        formatted = runner._format_review_context(sample_context_data)

        assert "## Review Context" in formatted
        assert "/test/repo" in formatted
        assert "### Changed Files" in formatted
        assert "- file1.py" in formatted
        assert "- file2.py" in formatted
        assert "### Git Diff" in formatted
        assert "Base Ref**: main" in formatted
        assert "Head Ref**: feature" in formatted
        assert "### Diff Content" in formatted
        assert "### Pull Request" in formatted
        assert "Title**: Test PR" in formatted

    def test_format_review_context_minimal(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
    ):
        """Test _format_review_context with minimal context data."""
        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        minimal_context = {
            "repo_root": "/test",
            "changed_files": ["test.py"],
            "diff": "+ test line",
        }

        formatted = runner._format_review_context(minimal_context)

        assert "## Review Context" in formatted
        assert "- test.py" in formatted
        assert "### Diff Content" in formatted
        assert "### Pull Request" not in formatted

    @pytest.mark.asyncio
    async def test_run_with_tools(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
        sample_context_data: dict,
        sample_review_output: dict,
    ):
        """Test that tools are passed through to context builder."""
        mock_llm_client.complete = AsyncMock(
            return_value=LLMResponse(
                text=json.dumps(sample_review_output),
                usage=TokenUsage(input=10, output=20),
                model_info=None,
            )
        )

        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        tools = ToolRegistry()
        result = await runner.run_review(
            system_prompt="You are a reviewer.",
            context_data=sample_context_data,
            tools=tools,
        )

        assert result == sample_review_output

    @pytest.mark.asyncio
    async def test_run_with_options(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
        sample_context_data: dict,
        sample_review_output: dict,
    ):
        """Test that options are passed through to LLM client."""
        mock_llm_client.complete = AsyncMock(
            return_value=LLMResponse(
                text=json.dumps(sample_review_output),
                usage=TokenUsage(input=10, output=20),
                model_info=None,
            )
        )

        runner = ReviewAgentRunner(
            llm_client=mock_llm_client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        options = {"temperature": 0.5, "max_tokens": 1000}
        result = await runner.run_review(
            system_prompt="You are a reviewer.",
            context_data=sample_context_data,
            options=options,
        )

        assert result == sample_review_output
        call_args = mock_llm_client.complete.call_args
        assert call_args is not None


class TestCreateReviewAgentRunner:
    """Tests for create_review_agent_runner factory function."""

    def test_factory_creates_runner(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
    ):
        """Test that factory creates properly configured ReviewAgentRunner."""
        runner = create_review_agent_runner(
            llm_client=mock_llm_client,
            base_dir=base_dir,
        )

        assert isinstance(runner, ReviewAgentRunner)
        assert runner.llm_client == mock_llm_client
        assert runner.base_dir == base_dir
        assert isinstance(runner.context_builder, ContextBuilder)

    def test_factory_with_skill_budget(
        self,
        mock_llm_client: AsyncMock,
        base_dir: Path,
    ):
        """Test that factory passes skill budget to context builder."""
        runner = create_review_agent_runner(
            llm_client=mock_llm_client,
            base_dir=base_dir,
            skill_max_char_budget=5000,
        )

        assert runner.context_builder.skill_injector.max_char_budget == 5000


class TestIntegration:
    """Integration tests for complete runner workflows."""

    @pytest.mark.asyncio
    async def test_complete_review_workflow(
        self,
        base_dir: Path,
        sample_context_data: dict,
    ):
        """Test complete workflow from context to parsed output."""
        from opencode_python.llm.client import LLMClient

        client = LLMClient(
            provider_id="z.ai",
            model="glm-4.7",
            api_key="test-key",
        )

        runner = ReviewAgentRunner(
            llm_client=client,
            context_builder=ContextBuilder(base_dir=base_dir),
            base_dir=base_dir,
        )

        formatted_context = runner._format_review_context(sample_context_data)

        assert "## Review Context" in formatted_context
        assert "- file1.py" in formatted_context
        assert "- file2.py" in formatted_context
