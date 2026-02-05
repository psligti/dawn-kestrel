"""OpenCode Python - LLM Client

Simple client for calling LLM providers (z.ai, OpenAI, Anthropic, etc.).
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import json
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM client for making API calls to different providers"""

    def __init__(
        self,
        provider_id: str = "z.ai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "glm-4.7",
    ):
        """Initialize LLM client

        Args:
            provider_id: Provider identifier (z.ai, zai-coding-plan, openai, anthropic)
                       Note: zai-coding-plan is FREE for coding tools
            api_key: API key for provider
            base_url: Custom base URL (overrides default)
            model: Model identifier to use

        Note on z.ai providers:
            - z.ai: Regular provider (requires balance)
            - zai-coding-plan: FREE coding-specific provider (no balance required)
        """
        self.provider_id = provider_id
        self.api_key = api_key
        self.model = model

        # Configure base URL based on provider
        if base_url:
            self.base_url = base_url.rstrip("/")
            logger.info(f"Using custom base URL: {self.base_url}")
        elif provider_id == "z.ai":
            self.base_url = "https://api.z.ai/api/paas/v4"
            logger.info(f"Using z.ai URL: {self.base_url}")
        elif provider_id == "zai-coding-plan":
            self.base_url = "https://api.z.ai/api/coding/paas/v4"
            logger.info(f"Using z.ai-coding-plan URL: {self.base_url} (FREE)")
        elif provider_id == "openai":
            self.base_url = "https://api.openai.com/v1"
        elif provider_id == "anthropic":
            self.base_url = "https://api.anthropic.com/v1"
        else:
            self.base_url = "https://api.openai.com/v1"

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Make a chat completion API call

        Args:
            system_prompt: System prompt for LLM
            user_message: User message to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            response_format: Optional format specification (e.g., {"type": "json_object"})

        Returns:
            Response text from LLM

        Raises:
            ValueError: If API key not configured
            httpx.HTTPError: If API call fails
        """
        if not self.api_key:
            raise ValueError(
                f"API key not configured for provider '{self.provider_id}'. "
                f"Set {self.provider_id.upper().replace('.', '_')}_API_KEY environment variable or pass api_key parameter."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if response_format:
            body["response_format"] = response_format

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()

                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from {self.provider_id}: {e}")
                logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'No response text'}")
                raise
            except httpx.HTTPError as e:
                logger.error(f"HTTP error calling {self.provider_id}: {e}")
                raise

    def chat_completion_sync(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Synchronous version of chat_completion

        Args:
            system_prompt: System prompt for LLM
            user_message: User message to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            response_format: Optional format specification (e.g., {"type": "json_object"})

        Returns:
            Response text from LLM
        """
        return asyncio.run(
            self.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
            )
        )

    def chat_completion_sync(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Synchronous version of chat_completion

        Args:
            system_prompt: System prompt for the LLM
            user_message: User message to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            response_format: Optional format specification (e.g., {"type": "json_object"})

        Returns:
            Response text from the LLM
        """
        import asyncio

        return asyncio.run(
            self.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
            )
        )
