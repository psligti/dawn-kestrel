"""AgentRunner - Template Method pattern for agent execution.

Provides a standardized execution flow that can be customized by subclasses
through hook methods. Integrates with ContextBuilder for context creation
and LLMClient for provider-agnostic LLM calls.

This module provides two runner implementations:
1. AgentRunner - Generic agent runner with ContextBuilder
2. SimpleReviewAgentRunner - Simple runner for review agents (no ContextBuilder required)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar, cast
from pathlib import Path
import json

from dawn_kestrel.context.builder import ContextBuilder
from dawn_kestrel.core.agent_types import AgentContext
from dawn_kestrel.llm.client import LLMClient, LLMRequestOptions
from dawn_kestrel.tools.framework import ToolRegistry
from dawn_kestrel.core.settings import settings


T = TypeVar("T")


logger = logging.getLogger(__name__)


class AgentRunner(ABC, Generic[T]):
    """Template Method pattern for agent execution.

    Defines a skeleton algorithm for running agents with customizable
    hooks for context building, prompt preparation, LLM calling,
    and response parsing.

    Template Method Flow:
        1. build_context() - Build agent execution context
        2. prepare_messages() - Prepare messages for LLM
        3. call_llm() - Call LLM with messages
        4. parse_response() - Parse LLM response to output type

    Subclasses should override hook methods to customize behavior.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        context_builder: ContextBuilder,
        base_dir: Path,
    ):
        """Initialize agent runner.

        Args:
            llm_client: Provider-agnostic LLM client
            context_builder: Context builder for execution context
            base_dir: Base directory for agent operations
        """
        self.llm_client = llm_client
        self.context_builder = context_builder
        self.base_dir = base_dir

    async def run(
        self,
        agent_config: Dict[str, Any],
        tools: Optional[ToolRegistry] = None,
        skills: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> T:
        """Execute agent using template method pattern.

        This is the template method that defines the execution flow.
        Subclasses should not override this method; instead override
        the hook methods to customize behavior.

        Args:
            agent_config: Agent configuration (name, prompt, permissions, etc.)
            tools: Optional tool registry
            skills: Optional list of skill names to inject
            options: Additional execution options

        Returns:
            Typed result from parse_response() hook
        """
        logger.info(f"Starting agent execution: {agent_config.get('name', 'unknown')}")

        # Step 1: Build agent context
        context = await self._build_context(
            agent_config=agent_config,
            tools=tools,
            skills=skills or [],
        )

        # Step 2: Prepare messages for LLM
        messages = self._prepare_messages(context, agent_config)

        # Step 3: Call LLM
        response = await self._call_llm(messages, options)

        # Step 4: Parse response to output type
        result = self._parse_response(response, context)

        logger.info(f"Agent execution complete: {agent_config.get('name', 'unknown')}")
        return result

    async def _build_context(
        self,
        agent_config: Dict[str, Any],
        tools: Optional[ToolRegistry],
        skills: List[str],
    ) -> AgentContext:
        """Build agent execution context.

        Hook method for building the context. Default implementation
        uses ContextBuilder to create a minimal context.

        Args:
            agent_config: Agent configuration
            tools: Tool registry
            skills: List of skill names

        Returns:
            AgentContext for execution
        """
        from dawn_kestrel.core.models import Session

        session = Session(
            id="harness-session",
            slug="harness-session",
            project_id="harness",
            title="Agent Runner Session",
            directory=str(self.base_dir),
            version="1.0",
        )

        return await self.context_builder.build_agent_context(
            session=session,
            agent=agent_config,
            tools=tools or ToolRegistry(),
            skills=skills,
        )

    def _prepare_messages(
        self,
        context: AgentContext,
        agent_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Prepare messages for LLM call.

        Hook method for preparing the message list. Default implementation
        creates a simple user message with context.

        Args:
            context: Agent execution context
            agent_config: Agent configuration

        Returns:
            List of message dictionaries for LLM
        """
        user_message = agent_config.get("user_message", "")
        return [{"role": "user", "content": user_message}]

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call LLM with prepared messages.

        Hook method for calling the LLM. Default implementation
        uses LLMClient.complete() with system prompt.

        Args:
            messages: Message list for LLM
            options: Additional LLM options

        Returns:
            Raw text response from LLM
        """
        llm_response = await self.llm_client.complete(
            messages=messages,
            options=options,
        )
        return llm_response.text

    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> T:
        """Parse LLM response to output type.

        Abstract hook method - subclasses must implement.

        Args:
            response: Raw text response from LLM
            context: Agent execution context

        Returns:
            Typed result specific to subclass
        """
        raise NotImplementedError("Subclasses must implement _parse_response()")


class ReviewAgentRunner(AgentRunner[Dict[str, Any]]):
    """Agent runner specialized for review agents.

    Extends AgentRunner to:
    - Format review context for prompts
    - Return ReviewOutput-compatible results
    - Handle JSON parsing for structured review output
    """

    async def run_review(
        self,
        system_prompt: str,
        context_data: Dict[str, Any],
        tools: Optional[ToolRegistry] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a review agent with formatted context.

        Args:
            system_prompt: System prompt for the reviewer
            context_data: Review context (changed_files, diff, etc.)
            tools: Optional tool registry
            options: Additional execution options

        Returns:
            Parsed review output as dictionary
        """
        agent_config = {
            "name": "reviewer",
            "prompt": system_prompt,
            "user_message": self._format_review_context(context_data),
        }

        return await self.run(
            agent_config=agent_config,
            tools=tools,
            skills=[],
            options=options,
        )

    def _prepare_messages(
        self,
        context: AgentContext,
        agent_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Prepare messages with system prompt and review context.

        Args:
            context: Agent execution context
            agent_config: Agent configuration

        Returns:
            List of messages with system + user messages
        """
        messages = [
            {"role": "system", "content": context.system_prompt},
            {"role": "user", "content": agent_config.get("user_message", "")},
        ]
        return messages

    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> Dict[str, Any]:
        """Parse review response from JSON.

        Args:
            response: Raw JSON response from LLM
            context: Agent execution context

        Returns:
            Parsed review output as dictionary

        Raises:
            ValueError: If response is not valid JSON
        """
        try:
            parsed = json.loads(response.strip())
            logger.debug(f"Parsed review response: {list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review response as JSON: {e}")
            logger.debug(f"Response content: {response[:500]}")
            raise ValueError(f"Review agent returned invalid JSON: {e}")

    def _format_review_context(self, context_data: Dict[str, Any]) -> str:
        """Format review context for prompt.

        Extracted from BaseReviewerAgent.format_inputs_for_prompt()
        to prepare for moving prompt formatting into the harness.

        Args:
            context_data: Review context with changed_files, diff, etc.

        Returns:
            Formatted context string for prompt
        """
        parts = [
            "## Review Context",
            "",
            f"**Repository Root**: {context_data.get('repo_root', '.')}",
            "",
            "### Changed Files",
        ]

        for file_path in context_data.get("changed_files", []):
            parts.append(f"- {file_path}")

        if "base_ref" in context_data and "head_ref" in context_data:
            parts.append("")
            parts.append("### Git Diff")
            parts.append(f"**Base Ref**: {context_data['base_ref']}")
            parts.append(f"**Head Ref**: {context_data['head_ref']}")

        parts.append("")
        parts.append("### Diff Content")
        parts.append("```diff")
        parts.append(context_data.get("diff", ""))
        parts.append("```")

        if context_data.get("pr_title"):
            parts.append("")
            parts.append("### Pull Request")
            parts.append(f"**Title**: {context_data['pr_title']}")
            if context_data.get("pr_description"):
                parts.append(f"**Description**:\n{context_data['pr_description']}")

        return "\n".join(parts)


def create_review_agent_runner(
    llm_client: LLMClient,
    base_dir: Path,
    skill_max_char_budget: Optional[int] = None,
) -> ReviewAgentRunner:
    """Factory function to create ReviewAgentRunner.

    Args:
        llm_client: Provider-agnostic LLM client
        base_dir: Base directory for agent operations
        skill_max_char_budget: Optional max characters for injected skills

    Returns:
        Configured ReviewAgentRunner instance
    """
    context_builder = ContextBuilder(
        base_dir=base_dir,
        skill_max_char_budget=skill_max_char_budget,
    )

    return ReviewAgentRunner(
        llm_client=llm_client,
        context_builder=context_builder,
        base_dir=base_dir,
    )


class SimpleReviewAgentRunner:
    """Simplified runner for review agents without ContextBuilder dependency.

    This runner provides a bridge between existing BaseReviewerAgent implementations
    and the new LLMClient, without requiring the full harness infrastructure.

    Review agents can use this runner by:
    1. Creating an instance with agent configuration
    2. Calling run() with review context
    3. Getting ReviewOutput back

    This is a transitional design for refactoring agents to use AgentRunner
    without requiring all harness infrastructure to be in place first.
    """

    def __init__(
        self,
        agent_name: str,
        allowed_tools: Optional[List[str]] = None,
        temperature: float = 0.3,
        top_p: float = 0.9,
        max_retries: int = 2,
        timeout_seconds: float = 120.0,
    ):
        """Initialize simple review agent runner.

        Args:
            agent_name: Name of the review agent (e.g., "security", "unit_tests")
            allowed_tools: Optional explicit allowlist of tool/command prefixes
            temperature: LLM temperature
            top_p: LLM top_p parameter
            max_retries: Maximum number of retry attempts
            timeout_seconds: Request timeout in seconds
        """
        self.agent_name = agent_name
        self.allowed_tools = allowed_tools or []
        self.temperature = temperature
        self.top_p = top_p
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._llm_client: Optional[LLMClient] = None

    def _build_system_prompt(self, system_prompt: str) -> str:
        """Inject per-agent tool policy into the system prompt."""
        if not self.allowed_tools:
            return system_prompt

        allowed = ", ".join(self.allowed_tools)
        tool_policy = (
            "\n\nTool policy:\n"
            "- Only propose checks/commands that start with one of these tool prefixes: "
            f"{allowed}.\n"
            "- If useful validation would require a different tool, add it under skips with why_safe and when_to_run.\n"
            "- Keep proposed commands deterministic and repository-local."
        )
        return f"{system_prompt.rstrip()}{tool_policy}"

    def _initialize_llm_client(self) -> LLMClient:
        """Initialize LLM client from settings."""
        if self._llm_client is None:
            default_account = settings.get_default_account()
            if not default_account:
                raise ValueError("No default account configured")

            provider_id = default_account.provider_id
            model = default_account.model
            api_key = default_account.api_key.get_secret_value()

            self._llm_client = LLMClient(
                provider_id=provider_id,
                model=model,
                api_key=api_key,
                max_retries=self.max_retries,
                timeout_seconds=self.timeout_seconds,
            )
            logger.info(
                f"[{self.agent_name}] LLM client initialized: provider={provider_id}, model={model}"
            )

        return self._llm_client

    async def run(
        self,
        system_prompt: str,
        formatted_context: str,
    ) -> str:
        """Execute LLM call with system prompt and formatted context.

        Args:
            system_prompt: System prompt for the reviewer
            formatted_context: Formatted review context from agent

        Returns:
            Raw LLM response text (JSON string)

        Raises:
            ValueError: If LLM client fails to initialize or returns empty response
            TimeoutError: If LLM call times out
        """
        llm_client = self._initialize_llm_client()

        effective_system_prompt = self._build_system_prompt(system_prompt)

        messages = [
            {"role": "system", "content": effective_system_prompt},
            {"role": "user", "content": formatted_context},
        ]

        options = LLMRequestOptions(
            temperature=self.temperature,
            top_p=self.top_p,
            response_format={"type": "json_object"},
        )

        logger.info(
            f"[{self.agent_name}] Calling LLM: "
            f"temperature={self.temperature}, top_p={self.top_p}"
        )

        response = await llm_client.complete(messages=messages, options=options)

        if not response.text or not response.text.strip():
            raise ValueError("Empty response from LLM")

        logger.info(
            f"[{self.agent_name}] LLM response received: {len(response.text)} chars"
        )

        return response.text

    async def run_with_retry(
        self,
        system_prompt: str,
        formatted_context: str,
    ) -> str:
        """Execute LLM call with retry on empty responses.

        Args:
            system_prompt: System prompt for the reviewer
            formatted_context: Formatted review context from agent

        Returns:
            Raw LLM response text (JSON string)

        Raises:
            ValueError: If LLM returns empty response after all retries
        """
        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            try:
                response_text = await self.run(system_prompt, formatted_context)
                return response_text
            except ValueError as e:
                last_error = e
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"[{self.agent_name}] Empty response, retrying ({attempt + 1}/{max_attempts})..."
                    )
                    continue
                else:
                    raise ValueError(f"Empty response from LLM after retries") from e
            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"[{self.agent_name}] LLM request failed, retrying ({attempt + 1}/{max_attempts}): {e}"
                    )
                    continue
                else:
                    raise Exception(f"LLM API error: {str(e)}") from e

        raise cast(Exception, last_error)
