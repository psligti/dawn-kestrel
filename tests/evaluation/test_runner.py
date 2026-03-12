"""Tests for evaluation runner module.

Tests cover:
- RunnerConfig: configuration validation
- RunnerResult: result model validation
- AgentRunner: execution lifecycle
- AgentRunnerProtocol: protocol compliance
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.evaluation.runner import (
    AgentRunner,
    AgentRunnerProtocol,
    RunnerConfig,
    RunnerResult,
)
from dawn_kestrel.evaluation.hooks import EvaluationHooks


@pytest.fixture
def config() -> RunnerConfig:
    """Create a default RunnerConfig for testing."""
    return RunnerConfig(
        agent_name="test_agent",
        capture_transcripts=True,
        capture_tool_calls=True,
    )


@pytest.fixture
def runner(config: RunnerConfig) -> AgentRunner:
    """Create an AgentRunner with default config."""
    return AgentRunner(config=config)


@pytest.fixture
def hooks() -> EvaluationHooks:
    """Create EvaluationHooks for testing."""
    return EvaluationHooks()


class TestRunnerConfig:
    """Tests for RunnerConfig dataclass."""

    def test_create_with_defaults(self) -> None:
        """Creating config with no args should use defaults."""
        config = RunnerConfig()

        assert config.agent_name == "build"
        assert config.capture_transcripts is True
        assert config.capture_tool_calls is True
        assert config.capture_tokens is True
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300.0
        assert config.working_dir == "."
        assert config.model is None
        assert config.provider is None
        assert config.tools is None

    def test_create_with_custom_values(self) -> None:
        """Creating config with custom values should work."""
        config = RunnerConfig(
            agent_name="custom_agent",
            max_iterations=5,
            timeout_seconds=60.0,
        )

        assert config.agent_name == "custom_agent"
        assert config.max_iterations == 5
        assert config.timeout_seconds == 60.0

    def test_model_override(self) -> None:
        """Model can be overridden."""
        config = RunnerConfig(model="gpt-4")

        assert config.model == "gpt-4"

    def test_provider_override(self) -> None:
        """Provider can be overridden."""
        config = RunnerConfig(provider="anthropic")

        assert config.provider == "anthropic"


class TestRunnerResult:
    """Tests for RunnerResult model."""

    def test_create_with_defaults(self) -> None:
        """Creating result with no args should use defaults."""
        result = RunnerResult()

        assert result.success is True
        assert result.error is None
        assert result.duration_seconds == 0.0
        assert result.tokens_used == {"input": 0, "output": 0}
        assert result.tools_called == []
        assert result.tool_call_count == 0
        assert result.transcript is None
        assert result.metadata == {}

    def test_create_with_values(self) -> None:
        """Creating result with custom values should work."""
        result = RunnerResult(
            run_id="abc123",
            agent_name="test",
            prompt="Hello",
            response="Hi there",
            success=True,
            duration_seconds=1.5,
            tokens_used={"input": 100, "output": 50},
            tools_called=["read", "write"],
            tool_call_count=2,
        )

        assert result.run_id == "abc123"
        assert result.agent_name == "test"
        assert result.prompt == "Hello"
        assert result.response == "Hi there"
        assert result.success is True
        assert result.duration_seconds == 1.5
        assert result.tokens_used == {"input": 100, "output": 50}
        assert result.tools_called == ["read", "write"]
        assert result.tool_call_count == 2

    def test_auto_generated_run_id(self) -> None:
        """Run ID should be auto-generated if not provided."""
        result1 = RunnerResult()
        result2 = RunnerResult()

        assert result1.run_id != result2.run_id
        assert len(result1.run_id) == 8

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RunnerResult(unknown_field="value")


class TestAgentRunner:
    """Tests for AgentRunner class."""

    def test_create_with_config(self, config: RunnerConfig) -> None:
        """Creating runner with config should store it."""
        runner = AgentRunner(config=config)

        assert runner.config == config
        assert runner._run_count == 0

    def test_create_with_agent_registry(self, config: RunnerConfig) -> None:
        """Creating runner with agent registry should store it."""
        mock_registry = MagicMock()
        runner = AgentRunner(config=config, agent_registry=mock_registry)

        assert runner._agent_registry == mock_registry

    @pytest.mark.asyncio
    async def test_run_returns_result(self, runner: AgentRunner) -> None:
        """run should return a RunnerResult."""
        result = await runner.run(prompt="Hello")

        assert isinstance(result, RunnerResult)
        assert result.prompt == "Hello"

    @pytest.mark.asyncio
    async def test_run_populates_agent_name(
        self, runner: AgentRunner, config: RunnerConfig
    ) -> None:
        """run should populate agent name from config."""
        result = await runner.run(prompt="Test")

        assert result.agent_name == config.agent_name

    @pytest.mark.asyncio
    async def test_run_emits_transcript_if_configured(self, runner: AgentRunner) -> None:
        """run should emit transcript if capture_transcripts is True."""
        hooks = EvaluationHooks()
        callback = MagicMock()
        hooks.on_transcript_ready = callback

        await runner.run(prompt="Test", hooks=hooks)

        assert callback.called

    @pytest.mark.asyncio
    async def test_run_does_not_emit_transcript_if_disabled(self) -> None:
        """run should not emit transcript if capture_transcripts is False."""
        config = RunnerConfig(
            agent_name="test",
            capture_transcripts=False,
        )
        runner = AgentRunner(config=config)
        hooks = EvaluationHooks()
        callback = MagicMock()
        hooks.on_transcript_ready = callback

        await runner.run(prompt="Test", hooks=hooks)

        assert not callback.called

    @pytest.mark.asyncio
    async def test_run_handles_exception(self, runner: AgentRunner) -> None:
        """run should handle exceptions gracefully."""
        with patch.object(
            runner,
            "_execute_agent",
            side_effect=RuntimeError("Test error"),
        ):
            result = await runner.run(prompt="Test")

        assert result.success is False
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_run_updates_run_count(self, runner: AgentRunner) -> None:
        """run should increment run count."""
        assert runner._run_count == 0

        await runner.run(prompt="Test 1")
        assert runner._run_count == 1

        await runner.run(prompt="Test 2")
        assert runner._run_count == 2

    @pytest.mark.asyncio
    async def test_run_records_duration(self, runner: AgentRunner) -> None:
        """run should record duration."""
        result = await runner.run(prompt="Test")

        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_run_without_hooks(self, runner: AgentRunner) -> None:
        """run should work without hooks."""
        result = await runner.run(prompt="Test")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_with_context(self, runner: AgentRunner) -> None:
        """run should accept context dict."""
        context = {"session_id": "sess-123", "working_dir": "/tmp"}
        result = await runner.run(prompt="Test", context=context)

        assert result.success is True


class TestAgentRunnerBatch:
    """Tests for AgentRunner batch operations."""

    @pytest.mark.asyncio
    async def test_run_batch_returns_all_results(self, runner: AgentRunner) -> None:
        """run_batch should return results for all prompts."""
        prompts = ["Test 1", "Test 2", "Test 3"]
        results = await runner.run_batch(prompts)

        assert len(results) == 3
        assert all(isinstance(r, RunnerResult) for r in results)

    @pytest.mark.asyncio
    async def test_run_batch_with_hooks(self, runner: AgentRunner) -> None:
        """run_batch should pass hooks to each run."""
        hooks = EvaluationHooks()
        callback = MagicMock()
        hooks.on_transcript_ready = callback

        await runner.run_batch(["Test 1", "Test 2"], hooks=hooks)

        assert callback.call_count >= 2

    @pytest.mark.asyncio
    async def test_run_batch_with_context(self, runner: AgentRunner) -> None:
        """run_batch should pass context to each run."""
        context = {"session_id": "sess-123"}
        results = await runner.run_batch(["Test"], context=context)

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_run_batch_empty_list(self, runner: AgentRunner) -> None:
        """run_batch with empty list should return empty list."""
        results = await runner.run_batch([])

        assert results == []


class TestAgentRunnerProtocol:
    """Tests for AgentRunnerProtocol compliance."""

    def test_agent_runner_satisfies_protocol(self, runner: AgentRunner) -> None:
        """AgentRunner should satisfy AgentRunnerProtocol."""
        from typing import runtime_checkable

        assert isinstance(runner, AgentRunnerProtocol)

    @pytest.mark.asyncio
    async def test_protocol_run_signature(self, runner: AgentRunner) -> None:
        """Protocol run method should match expected signature."""
        result = await runner.run(prompt="Test")

        assert isinstance(result, RunnerResult)
