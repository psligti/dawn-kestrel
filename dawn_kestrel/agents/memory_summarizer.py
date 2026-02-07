"""OpenCode Python - Memory Summarizer for conversation compression"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import os

from dawn_kestrel.core.models import Message
from dawn_kestrel.core.config import SDKConfig


logger = logging.getLogger(__name__)


class MemorySummary:
    """Memory summary model

    Compressed representation of conversation history
    with key points and metadata.
    """

    def __init__(
        self,
        session_id: str,
        summary: str,
        key_points: List[str],
        original_token_count: int,
        compressed_token_count: int,
        timestamp: float,
    ):
        self.session_id = session_id
        self.summary = summary
        self.key_points = key_points
        self.original_token_count = original_token_count
        self.compressed_token_count = compressed_token_count
        self.timestamp = timestamp

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio

        Returns:
            Ratio of original to compressed token count
        """
        if self.original_token_count == 0:
            return 1.0
        return self.compressed_token_count / self.original_token_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary

        Returns:
            Dictionary representation
        """
        return {
            "session_id": self.session_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "original_token_count": self.original_token_count,
            "compressed_token_count": self.compressed_token_count,
            "compression_ratio": self.compression_ratio,
            "timestamp": self.timestamp,
        }


class MemorySummarizer:
    """Memory summarizer for conversation compression

    Compresses conversation history by:
    1. Extracting key points and decisions
    2. Summarizing content while preserving context
    3. Reducing token count to target percentage

    Supports multiple strategies:
    - Mock summarization (for testing)
    - OpenAI-based summarization
    """

    DEFAULT_TARGET_TOKENS = 1000
    DEFAULT_TARGET_RATIO = 0.5  # 50% token reduction

    def __init__(self, config: Optional[SDKConfig] = None):
        """Initialize memory summarizer

        Args:
            config: SDK configuration with summarization settings
        """
        self.config = config or SDKConfig()
        self.summarization_strategy = self._determine_strategy()
        self._validate_strategy()

    def _determine_strategy(self) -> str:
        """Determine summarization strategy from config or environment

        Returns:
            Strategy name: "mock" or "openai"
        """
        strategy = getattr(self.config, "summarization_strategy", None)

        if not strategy:
            strategy = os.getenv("SUMMARIZATION_STRATEGY", "mock")

        # Default to mock if no API key
        if strategy == "openai" and not os.getenv("OPENAI_API_KEY"):
            logger.warning(
                "OPENAI_API_KEY not found, falling back to mock summarization. "
                "Set SUMMARIZATION_STRATEGY='mock' explicitly to suppress this warning."
            )
            strategy = "mock"

        return strategy

    def _validate_strategy(self) -> None:
        """Validate chosen summarization strategy"""
        valid_strategies = ["mock", "openai"]
        if self.summarization_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid summarization strategy: {self.summarization_strategy}. "
                f"Valid options: {', '.join(valid_strategies)}"
            )

        if self.summarization_strategy == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required for OpenAI summarization"
                )

    async def summarize(
        self,
        messages: List[Message],
        since: Optional[float] = None,
        target_tokens: Optional[int] = None,
        target_ratio: Optional[float] = None,
    ) -> MemorySummary:
        """Summarize a list of messages

        Args:
            messages: List of messages to summarize
            since: Only summarize messages after this timestamp
            target_tokens: Target token count for summary
            target_ratio: Target compression ratio (default: 0.5 for 50% reduction)

        Returns:
            MemorySummary with compressed representation
        """
        if not messages:
            logger.warning("No messages provided for summarization")
            return MemorySummary(
                session_id="",
                summary="",
                key_points=[],
                original_token_count=0,
                compressed_token_count=0,
                timestamp=datetime.now().timestamp(),
            )

        session_id = messages[0].session_id if messages else ""

        # Filter messages by timestamp if 'since' is provided
        if since is not None:
            messages = [m for m in messages if self._get_message_time(m) >= since]

        if not messages:
            logger.info(f"No messages after timestamp {since} for session {session_id}")
            return MemorySummary(
                session_id=session_id,
                summary="No messages in this time range",
                key_points=[],
                original_token_count=0,
                compressed_token_count=0,
                timestamp=datetime.now().timestamp(),
            )

        # Calculate original token count
        original_token_count = self._estimate_tokens(messages)

        # Set target based on parameters
        if target_tokens is None:
            target_tokens = self.DEFAULT_TARGET_TOKENS

        if target_ratio is None:
            target_ratio = self.DEFAULT_TARGET_RATIO

        logger.debug(
            f"Summarizing {len(messages)} messages ({original_token_count} tokens) "
            f"for session {session_id}"
        )

        # Generate summary based on strategy
        if self.summarization_strategy == "mock":
            summary, key_points = await self._mock_summarize(messages)
        elif self.summarization_strategy == "openai":
            summary, key_points = await self._openai_summarize(
                messages, target_tokens, target_ratio
            )
        else:
            raise ValueError(f"Unknown summarization strategy: {self.summarization_strategy}")

        # Calculate compressed token count
        compressed_token_count = self._estimate_tokens_from_text(
            summary + " ".join(key_points)
        )

        memory_summary = MemorySummary(
            session_id=session_id,
            summary=summary,
            key_points=key_points,
            original_token_count=original_token_count,
            compressed_token_count=compressed_token_count,
            timestamp=datetime.now().timestamp(),
        )

        logger.debug(
            f"Generated summary for session {session_id}: "
            f"{original_token_count} -> {compressed_token_count} tokens "
            f"({memory_summary.compression_ratio:.1%} compression)"
        )

        return memory_summary

    def _get_message_time(self, message: Message) -> float:
        """Get message timestamp

        Args:
            message: Message to get time from

        Returns:
            Timestamp as float
        """
        if message.time and "created" in message.time:
            return message.time["created"]
        return 0.0

    def _estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages

        Args:
            messages: List of messages

        Returns:
            Estimated token count
        """
        total_text = " ".join(m.text for m in messages if m.text)
        return self._estimate_tokens_from_text(total_text)

    def _estimate_tokens_from_text(self, text: str) -> int:
        """Estimate token count from text

        Args:
            text: Input text

        Returns:
            Estimated token count (roughly 4 chars per token)
        """
        return max(1, len(text) // 4)

    async def _mock_summarize(self, messages: List[Message]) -> tuple[str, List[str]]:
        """Generate mock summary for testing

        Args:
            messages: List of messages to summarize

        Returns:
            Tuple of (summary_text, key_points)
        """
        message_count = len(messages)

        # Simple mock summary
        summary = f"Conversation contains {message_count} messages exchanged between user and assistant. Key topics were discussed and actions were taken."

        # Extract key points from message text
        key_points = []
        for i, msg in enumerate(messages):
            if msg.text and i < 5:  # Limit to first 5 messages
                point = msg.text[:100].strip()
                if point and len(key_points) < 5:
                    key_points.append(point)

        if not key_points:
            key_points.append("No specific key points identified in mock mode")

        return summary, key_points

    async def _openai_summarize(
        self,
        messages: List[Message],
        target_tokens: int,
        target_ratio: float,
    ) -> tuple[str, List[str]]:
        """Generate summary using OpenAI API

        Args:
            messages: List of messages to summarize
            target_tokens: Target token count
            target_ratio: Target compression ratio

        Returns:
            Tuple of (summary_text, key_points)
        """
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Format messages for summarization
            messages_text = "\n".join(
                f"{m.role}: {m.text}" for m in messages if m.text
            )

            prompt = f"""Summarize the following conversation concisely.

Target length: Around {int(target_tokens * target_ratio)} tokens
Compression goal: {int(target_ratio * 100)}% reduction from original

Conversation:
{messages_text}

Provide:
1. A concise summary (2-3 sentences)
2. 3-5 key points as bullet points

Format your response as:
Summary: [your summary here]
Key Points:
- [point 1]
- [point 2]
- [point 3]
"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=target_tokens,
                temperature=0.3,
            )

            summary_text = response.choices[0].message.content or ""

            # Parse summary and key points
            summary = ""
            key_points = []

            lines = summary_text.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()
                if line.lower().startswith("summary:"):
                    current_section = "summary"
                    summary = line.replace("Summary:", "").strip()
                elif line.lower().startswith("key points:"):
                    current_section = "key_points"
                elif line.startswith("-") and current_section == "key_points":
                    point = line.lstrip("-").strip()
                    if point:
                        key_points.append(point)
                elif current_section == "summary":
                    summary += " " + line

            summary = summary.strip()

            if not key_points:
                key_points.append("No specific key points identified")

            logger.debug("Generated OpenAI summary")
            return summary, key_points

        except ImportError:
            raise ImportError(
                "OpenAI package is required for OpenAI summarization. "
                "Install with: pip install openai"
            )
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            raise

    def get_strategy(self) -> str:
        """Get current summarization strategy

        Returns:
            Strategy name
        """
        return self.summarization_strategy


def create_memory_summarizer(config: Optional[SDKConfig] = None) -> MemorySummarizer:
    """Factory function to create memory summarizer

    Args:
        config: Optional SDK configuration

    Returns:
        MemorySummarizer instance
    """
    return MemorySummarizer(config=config)
