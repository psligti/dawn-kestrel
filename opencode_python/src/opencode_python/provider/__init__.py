"""OpenCode Python - AI Provider Abstraction"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import json
import logging


logger = logging.getLogger(__name__)


@dataclass
class UsageInfo:
    """Usage information from AI provider"""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_5m_tokens: Optional[int] = None
    cache_write_1h_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass
class CommonChunk:
    """Common chunk structure from streaming responses"""
    id: str
    object: str = "chat.completion.chunk"
    created: int = 0
    model: str = ""
    choices: Optional[list] = None
    usage: Optional[UsageInfo] = None
    finish_reason: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for all LLM providers"""

    @abstractmethod
    def modify_url(self, provider_api: str, is_stream: bool = False) -> str:
        """Modify API URL for requests"""
        pass

    @abstractmethod
    def modify_headers(
        self,
        headers: Dict[str, str],
        body: Dict[str, Any],
        api_key: str
    ) -> Dict[str, str]:
        """Add provider-specific headers"""
        pass

    @abstractmethod
    def modify_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request body to provider format"""
        pass

    @abstractmethod
    def get_stream_separator(self) -> str:
        """Return separator for streaming chunks"""
        pass

    @abstractmethod
    def parse_usage(self, chunk: str) -> Optional[UsageInfo]:
        """Parse usage from a chunk, return None if not complete"""
        pass

    def create_binary_stream_decoder(self) -> Optional[Callable[[bytes], Optional[bytes]]]:
        """Return decoder for binary streams (e.g., AWS Bedrock)"""
        return None


class AnthropicProvider(BaseProvider):
    """Anthropic API provider implementation"""

    def __init__(self, req_model: str, provider_model: str):
        self.req_model = req_model
        self.provider_model = provider_model
        self.is_bedrock = provider_model.startswith("arn:aws:bedrock:")
        self.is_sonnet = "sonnet" in req_model

    def modify_url(self, provider_api: str, is_stream: bool = False) -> str:
        if self.is_bedrock:
            action = "invoke-with-response-stream" if is_stream else "invoke"
            return f"{provider_api}/model/{self.provider_model}/{action}"
        return f"{provider_api}/messages"

    def modify_headers(
        self,
        headers: Dict[str, str],
        body: Dict[str, Any],
        api_key: str
    ) -> Dict[str, str]:
        if self.is_bedrock:
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = headers.get("anthropic-version", "2023-06-01")
            if self.req_model.startswith("claude-sonnet-"):
                headers["anthropic-beta"] = "context-1m-2025-08-07"
        return headers

    def modify_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request body to Anthropic format"""
        body = body.copy()

        if self.is_sonnet:
            body["anthropic-beta"] = "context-1m-2025-08-07"

        return body

    def get_stream_separator(self) -> str:
        return "\n\n"

    def parse_usage(self, chunk: str) -> Optional[UsageInfo]:
        """Parse Anthropic usage from SSE chunk"""
        lines = chunk.split("\n")
        data_line = next((line for line in lines if line.startswith("data: ")), None)

        if not data_line:
            return None

        try:
            json_data = json.loads(data_line[6:])
            usage = json_data.get("usage") or json_data.get("message", {}).get("usage")
            if usage:
                return UsageInfo(
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cache_read_tokens=usage.get("cache_read_input_tokens"),
                    cache_write_5m_tokens=usage.get("cache_creation", {}).get("ephemeral_5m_input_tokens"),
                    cache_write_1h_tokens=usage.get("cache_creation", {}).get("ephemeral_1h_input_tokens"),
                )
        except json.JSONDecodeError:
            pass

        return None


class OpenAIProvider(BaseProvider):
    """OpenAI API provider implementation"""

    def modify_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request body to OpenAI format"""
        body = body.copy()
        return body
