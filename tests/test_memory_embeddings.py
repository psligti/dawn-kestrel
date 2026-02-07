"""Tests for MemoryEmbedder and MemorySummarizer"""
from __future__ import annotations

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

from dawn_kestrel.agents.memory_embedder import MemoryEmbedder, create_memory_embedder
from dawn_kestrel.agents.memory_summarizer import (
    MemorySummarizer,
    create_memory_summarizer,
    MemorySummary as MemorySummaryClass,
)
from dawn_kestrel.core.models import Message, MemorySummary


@pytest.fixture
def sample_messages():
    """Create sample messages for testing"""
    return [
        Message(
            id="msg1",
            session_id="session123",
            role="user",
            text="Hello, I need help with my Python project",
            time={"created": 1704067200.0},
        ),
        Message(
            id="msg2",
            session_id="session123",
            role="assistant",
            text="I'd be happy to help with your Python project. What do you need?",
            time={"created": 1704067260.0},
        ),
        Message(
            id="msg3",
            session_id="session123",
            role="user",
            text="I'm working on a memory system for an AI agent. It needs embeddings and summarization.",
            time={"created": 1704067320.0},
        ),
        Message(
            id="msg4",
            session_id="session123",
            role="assistant",
            text="That sounds like a great project! I can help you implement memory embeddings and summarization.",
            time={"created": 1704067380.0},
        ),
    ]


class TestMemoryEmbedder:
    """Test MemoryEmbedder functionality"""

    @pytest.mark.asyncio
    async def test_embed_with_mock_strategy(self):
        """Test embedding generation with mock strategy"""
        embedder = create_memory_embedder()

        text = "This is a test message"
        embedding = await embedder.embed(text)

        assert isinstance(embedding, list)
        assert len(embedding) == MemoryEmbedder.EMBEDDING_DIMENSION
        assert all(isinstance(x, float) for x in embedding)
        assert embedder.get_strategy() == "mock"

    @pytest.mark.asyncio
    async def test_embed_empty_text(self):
        """Test embedding with empty text returns zero vector"""
        embedder = create_memory_embedder()

        embedding = await embedder.embed("")

        assert isinstance(embedding, list)
        assert len(embedding) == MemoryEmbedder.EMBEDDING_DIMENSION
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_deterministic(self):
        """Test mock embeddings are deterministic for same text"""
        embedder = create_memory_embedder()

        text = "Same text"
        embedding1 = await embedder.embed(text)
        embedding2 = await embedder.embed(text)

        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_embed_different_text_different_embedding(self):
        """Test different texts produce different embeddings"""
        embedder = create_memory_embedder()

        text1 = "First text"
        text2 = "Second text"

        embedding1 = await embedder.embed(text1)
        embedding2 = await embedder.embed(text2)

        assert embedding1 != embedding2

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding generation"""
        embedder = create_memory_embedder()

        texts = ["text1", "text2", "text3"]
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(
            len(emb) == MemoryEmbedder.EMBEDDING_DIMENSION for emb in embeddings
        )

    @pytest.mark.asyncio
    async def test_openai_strategy_without_api_key_fails(self):
        """Test OpenAI strategy fails without API key"""
        import os

        # Remove API key if present
        original_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        try:
            from dawn_kestrel.core.config import SDKConfig

            config = SDKConfig()
            embedder = MemoryEmbedder(config)
            assert embedder.get_strategy() == "mock"

        finally:
            # Restore API key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key

    def test_get_strategy(self):
        """Test getting current embedding strategy"""
        embedder = create_memory_embedder()
        strategy = embedder.get_strategy()

        assert strategy in ["mock", "openai", "local"]


class TestMemorySummarizer:
    """Test MemorySummarizer functionality"""

    @pytest.mark.asyncio
    async def test_summarize_with_mock_strategy(self, sample_messages):
        """Test summarization with mock strategy"""
        summarizer = create_memory_summarizer()

        summary = await summarizer.summarize(sample_messages)

        assert isinstance(summary, MemorySummaryClass)
        assert summary.session_id == "session123"
        assert summary.summary != ""
        assert len(summary.key_points) > 0
        assert summary.original_token_count > 0
        assert summary.compressed_token_count > 0
        assert summarizer.get_strategy() == "mock"

    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self):
        """Test summarizing empty message list"""
        summarizer = create_memory_summarizer()

        summary = await summarizer.summarize([])

        assert summary.session_id == ""
        assert summary.summary == ""
        assert len(summary.key_points) == 0
        assert summary.original_token_count == 0
        assert summary.compressed_token_count == 0

    @pytest.mark.asyncio
    async def test_summarize_with_since_filter(self, sample_messages):
        """Test summarizing with timestamp filter"""
        summarizer = create_memory_summarizer()

        # Filter messages after second message
        since = 1704067260.0
        summary = await summarizer.summarize(sample_messages, since=since)

        # Should only summarize last 2 messages
        assert summary.original_token_count > 0
        assert summary.original_token_count < sum(
            len(m.text) for m in sample_messages
        ) // 4

    @pytest.mark.asyncio
    async def test_summarize_with_target_tokens(self, sample_messages):
        """Test summarization with target token count"""
        summarizer = create_memory_summarizer()

        target_tokens = 500
        summary = await summarizer.summarize(sample_messages, target_tokens=target_tokens)

        assert summary.compressed_token_count <= target_tokens * 2  # Allow some flexibility

    @pytest.mark.asyncio
    async def test_summarize_compression_ratio(self, sample_messages):
        """Test compression ratio calculation"""
        summarizer = create_memory_summarizer()

        summary = await summarizer.summarize(sample_messages)

        assert summary.compression_ratio > 0
        # In mock mode, compression ratio can be > 1.0
        assert isinstance(summary.compression_ratio, float)

    @pytest.mark.asyncio
    async def test_estimate_tokens(self, sample_messages):
        """Test token estimation from messages"""
        summarizer = create_memory_summarizer()

        token_count = summarizer._estimate_tokens(sample_messages)

        assert token_count > 0
        # Rough estimate: ~4 chars per token
        # Allow for small rounding differences due to " " join
        total_chars = sum(len(m.text) for m in sample_messages)
        assert abs(token_count - total_chars // 4) <= 2

    @pytest.mark.asyncio
    async def test_get_message_time(self, sample_messages):
        """Test extracting timestamp from message"""
        summarizer = create_memory_summarizer()

        time = summarizer._get_message_time(sample_messages[0])

        assert time == 1704067200.0

    def test_mock_summarize(self):
        """Test mock summarization logic"""
        summarizer = create_memory_summarizer()
        messages = [
            Message(
                id="msg1",
                session_id="test",
                role="user",
                text="Test message one",
                time={"created": 1704067200.0},
            ),
            Message(
                id="msg2",
                session_id="test",
                role="assistant",
                text="Test message two",
                time={"created": 1704067260.0},
            ),
        ]

        summary_text, key_points = asyncio.run(summarizer._mock_summarize(messages))

        assert "2 messages" in summary_text
        assert len(key_points) >= 1

    def test_get_strategy(self):
        """Test getting current summarization strategy"""
        summarizer = create_memory_summarizer()
        strategy = summarizer.get_strategy()

        assert strategy in ["mock", "openai"]


class TestMemorySummaryModel:
    """Test MemorySummary Pydantic model"""

    def test_memory_summary_creation(self):
        """Test creating MemorySummary from dict"""
        summary_data = {
            "session_id": "session123",
            "summary": "Test summary",
            "key_points": ["Point 1", "Point 2"],
            "original_token_count": 1000,
            "compressed_token_count": 500,
            "compression_ratio": 0.5,
            "timestamp": 1704067200.0,
        }

        summary = MemorySummary(**summary_data)

        assert summary.session_id == "session123"
        assert summary.summary == "Test summary"
        assert len(summary.key_points) == 2
        assert summary.original_token_count == 1000
        assert summary.compressed_token_count == 500
        assert summary.compression_ratio == 0.5

    def test_memory_summary_defaults(self):
        """Test MemorySummary default values"""
        summary = MemorySummary(session_id="test")

        assert summary.session_id == "test"
        assert summary.summary == ""
        assert len(summary.key_points) == 0
        assert summary.original_token_count == 0
        assert summary.compressed_token_count == 0
        assert summary.compression_ratio == 1.0
        assert summary.target_compression == 0.5

    def test_memory_summary_serialization(self):
        """Test MemorySummary serialization to dict"""
        summary = MemorySummary(
            session_id="session123",
            summary="Test",
            key_points=["Point"],
            original_token_count=1000,
            compressed_token_count=500,
        )

        data = summary.model_dump()

        assert data["session_id"] == "session123"
        assert data["summary"] == "Test"
        assert data["key_points"] == ["Point"]
        assert data["original_token_count"] == 1000
        assert data["compressed_token_count"] == 500


class TestIntegration:
    """Integration tests for embedding and summarization"""

    @pytest.mark.asyncio
    async def test_embedding_and_summarization_workflow(self, sample_messages):
        """Test complete workflow: embed messages, summarize conversation"""
        embedder = create_memory_embedder()
        summarizer = create_memory_summarizer()

        # Embed messages
        embeddings = []
        for msg in sample_messages:
            if msg.text:
                embedding = await embedder.embed(msg.text)
                embeddings.append(embedding)

        assert len(embeddings) == len([m for m in sample_messages if m.text])

        # Summarize conversation
        summary = await summarizer.summarize(sample_messages)

        assert summary.session_id == "session123"
        assert summary.summary != ""
        assert summary.compression_ratio > 0

    @pytest.mark.asyncio
    async def test_batch_embeddings_and_summary(self, sample_messages):
        """Test batch embeddings with summary generation"""
        embedder = create_memory_embedder()
        summarizer = create_memory_summarizer()

        texts = [m.text for m in sample_messages if m.text]

        # Generate batch embeddings
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == len(texts)

        # Summarize
        summary = await summarizer.summarize(sample_messages)

        assert summary.original_token_count > 0
        assert summary.compressed_token_count > 0
