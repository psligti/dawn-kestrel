"""Agent runner protocol for ash-hawk evaluation integration.

This module provides the protocol and utilities for running agents
in a way that's compatible with ash-hawk's evaluation framework.
The runner captures transcripts, tool calls, and other metrics
needed for evaluation.

Usage:
    from dawn_kestrel.evaluation.runner import AgentRunner, RunnerConfig

    runner = AgentRunner(config=RunnerConfig(
        agent_name="build",
        capture_transcripts=True,
        capture_tool_calls=True,
    ))

    result = await runner.run(
        prompt="Implement a feature",
        hooks=my_evaluation_hooks,
    )
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import pydantic as pd

if TYPE_CHECKING:
    from dawn_kestrel.agents.registry import AgentRegistry
    from dawn_kestrel.core.agent_types import AgentResult
    from dawn_kestrel.evaluation.hooks import EvaluationHooks
    from dawn_kestrel.evaluation.models import Transcript
    from dawn_kestrel.tools.framework import ToolRegistry


@runtime_checkable
class AgentRunnerProtocol(Protocol):
    """Protocol for agent runners compatible with ash-hawk.

    Any runner implementing this protocol can be used with ash-hawk's
    evaluation framework to run agents and capture results.

    The runner is responsible for:
    - Executing the agent with the given prompt
    - Capturing tool calls and outputs
    - Generating transcripts
    - Reporting to evaluation hooks
    """

    async def run(
        self,
        prompt: str,
        hooks: EvaluationHooks | None = None,
        context: dict[str, Any] | None = None,
    ) -> RunnerResult:
        """Run the agent with the given prompt.

        Args:
            prompt: The user prompt to process
            hooks: Optional evaluation hooks to report events
            context: Optional context (session_id, working_dir, etc.)

        Returns:
            RunnerResult with agent output and captured metrics
        """
        ...


@dataclass
class RunnerConfig:
    """Configuration for agent runner.

    Attributes:
        agent_name: Name of the agent to run
        capture_transcripts: Whether to capture full transcripts
        capture_tool_calls: Whether to capture tool call details
        capture_tokens: Whether to capture token usage
        max_iterations: Maximum iterations for the agent
        timeout_seconds: Timeout for agent execution
        working_dir: Working directory for the agent
        model: Optional model override
        provider: Optional provider override
        tools: Optional tool registry to use
    """

    agent_name: str = "build"
    capture_transcripts: bool = True
    capture_tool_calls: bool = True
    capture_tokens: bool = True
    max_iterations: int = 10
    timeout_seconds: float = 300.0
    working_dir: str = "."
    model: str | None = None
    provider: str | None = None
    tools: ToolRegistry | None = None


class RunnerResult(pd.BaseModel):
    """Result from running an agent.

    Attributes:
        run_id: Unique identifier for this run
        agent_name: Name of the agent that was run
        prompt: The original prompt
        response: The agent's response text
        success: Whether the run completed successfully
        error: Error message if run failed
        duration_seconds: Total execution time
        tokens_used: Token usage breakdown
        tools_called: List of tools that were called
        tool_call_count: Number of tool calls made
        transcript: Captured transcript (if capture_transcripts=True)
        metadata: Additional metadata about the run
    """

    run_id: str = pd.Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str = ""
    prompt: str = ""
    response: str = ""
    success: bool = True
    error: str | None = None
    duration_seconds: float = 0.0
    tokens_used: dict[str, int] = pd.Field(default_factory=lambda: {"input": 0, "output": 0})
    tools_called: list[str] = pd.Field(default_factory=list)
    tool_call_count: int = 0
    transcript: Any | None = None
    metadata: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")


class AgentRunner:
    """Runner for executing agents with evaluation hooks.

    This is the primary interface for running agents in a way
    that's compatible with ash-hawk evaluation. It:
    - Manages agent execution lifecycle
    - Reports events to evaluation hooks
    - Captures transcripts and metrics
    - Handles errors gracefully

    Example:
        from dawn_kestrel.evaluation.runner import AgentRunner, RunnerConfig
        from dawn_kestrel.evaluation.hooks import EvaluationHooks

        hooks = EvaluationHooks()
        hooks.on_tool_call = lambda t, i, o: print(f"Tool: {t}")

        runner = AgentRunner(config=RunnerConfig(agent_name="build"))
        result = await runner.run(prompt="Hello", hooks=hooks)

        print(f"Response: {result.response}")
        print(f"Tools used: {result.tools_called}")
    """

    def __init__(
        self,
        config: RunnerConfig,
        agent_registry: AgentRegistry | None = None,
    ) -> None:
        """Initialize the agent runner.

        Args:
            config: Runner configuration
            agent_registry: Optional agent registry (for dependency injection)
        """
        self.config = config
        self._agent_registry = agent_registry
        self._run_count = 0

    async def run(
        self,
        prompt: str,
        hooks: EvaluationHooks | None = None,
        context: dict[str, Any] | None = None,
    ) -> RunnerResult:
        """Run the agent with the given prompt.

        Args:
            prompt: The user prompt to process
            hooks: Optional evaluation hooks to report events
            context: Optional context (session_id, working_dir, etc.)

        Returns:
            RunnerResult with agent output and captured metrics
        """
        start_time = time.time()
        context = context or {}
        run_id = str(uuid.uuid4())[:8]

        result = RunnerResult(
            run_id=run_id,
            agent_name=self.config.agent_name,
            prompt=prompt,
        )

        try:
            # Emit phase event for evaluation
            if hooks:
                hooks.emit_phase(
                    "runner_start",
                    {
                        "run_id": run_id,
                        "agent_name": self.config.agent_name,
                        "prompt_length": len(prompt),
                    },
                )

            # Execute the agent
            agent_result = await self._execute_agent(prompt, context, hooks)

            # Populate result from agent execution
            result.response = agent_result.response
            result.success = agent_result.error is None
            result.error = agent_result.error
            result.tools_called = agent_result.tools_used or []
            result.tool_call_count = len(result.tools_called)

            if agent_result.tokens_used:
                result.tokens_used = {
                    "input": agent_result.tokens_used.input,
                    "output": agent_result.tokens_used.output,
                    "reasoning": getattr(agent_result.tokens_used, "reasoning", 0),
                }

            if agent_result.metadata:
                result.metadata.update(agent_result.metadata)

            # Capture transcript if configured
            if self.config.capture_transcripts and hooks:
                transcript = self._create_transcript(result, agent_result)
                result.transcript = transcript
                hooks.emit_transcript(transcript)

            # Emit completion phase
            if hooks:
                hooks.emit_phase(
                    "runner_complete",
                    {
                        "run_id": run_id,
                        "success": result.success,
                        "duration_seconds": result.duration_seconds,
                        "tool_call_count": result.tool_call_count,
                    },
                )

        except Exception as e:
            result.success = False
            result.error = str(e)

            if hooks:
                hooks.emit_phase(
                    "runner_error",
                    {
                        "run_id": run_id,
                        "error": str(e),
                    },
                )

        finally:
            result.duration_seconds = time.time() - start_time
            self._run_count += 1

        return result

    async def _execute_agent(
        self,
        prompt: str,
        context: dict[str, Any],
        hooks: EvaluationHooks | None,
    ) -> AgentResult:
        """Execute the agent and return the result.

        This is a placeholder that should be overridden by actual
        implementations that integrate with AgentRuntime.

        Args:
            prompt: The user prompt
            context: Execution context
            hooks: Evaluation hooks

        Returns:
            AgentResult from execution
        """
        # Import here to avoid circular imports
        from dawn_kestrel.core.agent_types import AgentResult
        from dawn_kestrel.core.models import TokenUsage

        # Placeholder implementation
        # Real implementation would use AgentRuntime.execute_agent()
        return AgentResult(
            agent_name=self.config.agent_name,
            response=f"Agent {self.config.agent_name} executed: {prompt[:50]}...",
            parts=[],
            metadata={},
            tools_used=[],
            tokens_used=TokenUsage(input=100, output=50, reasoning=0, cache_read=0, cache_write=0),
            duration=0.5,
            error=None,
            task_id=None,
        )

    def _create_transcript(
        self,
        result: RunnerResult,
        agent_result: AgentResult,
    ) -> Transcript:
        from dawn_kestrel.core.models import Message
        from dawn_kestrel.evaluation.models import Transcript

        messages = [
            Message(
                id=f"{result.run_id}_user",
                session_id=result.run_id,
                role="user",
                text=result.prompt,
            ),
            Message(
                id=f"{result.run_id}_assistant",
                session_id=result.run_id,
                role="assistant",
                text=result.response,
            ),
        ]

        return Transcript(
            id=result.run_id,
            session_id=result.run_id,
            messages=messages,
            timing={
                "duration_seconds": result.duration_seconds,
                "tool_call_count": float(result.tool_call_count),
            },
        )

    async def run_batch(
        self,
        prompts: list[str],
        hooks: EvaluationHooks | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[RunnerResult]:
        """Run multiple prompts in sequence.

        Args:
            prompts: List of prompts to process
            hooks: Optional evaluation hooks
            context: Optional context for all runs

        Returns:
            List of RunnerResults
        """
        results = []
        for prompt in prompts:
            result = await self.run(prompt, hooks, context)
            results.append(result)
        return results


__all__ = [
    "AgentRunnerProtocol",
    "RunnerConfig",
    "RunnerResult",
    "AgentRunner",
]
