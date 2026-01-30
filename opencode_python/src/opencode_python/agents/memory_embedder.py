"""OpenCode Python - Memory Embedder for semantic search"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
import logging
import os

from opencode_python.core.config import SDKConfig


logger = logging.getLogger(__name__)


class MemoryEmbedder:
    """Memory embedder interface for generating vector embeddings

    Supports multiple embedding strategies:
    - Mock embeddings (for testing, no external API required)
    - OpenAI embeddings (requires OPENAI_API_KEY)
    - Local models (sentence-transformers, optional dependency)

    All embeddings are normalized to 1536 dimensions (OpenAI text-embedding-3-small standard).
    """

    EMBEDDING_DIMENSION = 1536

    def __init__(self, config: Optional[SDKConfig] = None):
        """Initialize memory embedder

        Args:
            config: SDK configuration with embedding settings
        """
        self.config = config or SDKConfig()
        self.embedding_strategy = self._determine_strategy()
        self._validate_strategy()

    def _determine_strategy(self) -> str:
        """Determine embedding strategy from config or environment

        Returns:
            Strategy name: "mock", "openai", or "local"
        """
        # Check config first
        strategy = getattr(self.config, "embedding_strategy", None)

        # Fall back to environment variable
        if not strategy:
            strategy = os.getenv("EMBEDDING_STRATEGY", "mock")

        # Default to mock if no API key available
        if strategy == "openai" and not os.getenv("OPENAI_API_KEY"):
            logger.warning(
                "OPENAI_API_KEY not found, falling back to mock embeddings. "
                "Set EMBEDDING_STRATEGY='mock' explicitly to suppress this warning."
            )
            strategy = "mock"

        return strategy

    def _validate_strategy(self) -> None:
        """Validate the chosen embedding strategy"""
        valid_strategies = ["mock", "openai", "local"]
        if self.embedding_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid embedding strategy: {self.embedding_strategy}. "
                f"Valid options: {', '.join(valid_strategies)}"
            )

        if self.embedding_strategy == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required for OpenAI embeddings"
                )

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        """
        if not text or not text.strip():
            logger.warning("Attempted to embed empty text, returning zero vector")
            return [0.0] * self.EMBEDDING_DIMENSION

        logger.debug(f"Generating embedding for text: {text[:100]}...")

        if self.embedding_strategy == "mock":
            return await self._mock_embed(text)
        elif self.embedding_strategy == "openai":
            return await self._openai_embed(text)
        elif self.embedding_strategy == "local":
            return await self._local_embed(text)
        else:
            raise ValueError(f"Unknown embedding strategy: {self.embedding_strategy}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        logger.debug(f"Generating batch embeddings for {len(texts)} texts")

        # Process in parallel for efficiency
        embeddings = [await self.embed(text) for text in texts]
        return embeddings

    async def _mock_embed(self, text: str) -> List[float]:
        """Generate mock embedding for testing

        Mock embeddings are deterministic based on text content,
        making them suitable for unit tests without external dependencies.

        Args:
            text: Input text

        Returns:
            Mock embedding vector (1536 dimensions)
        """
        # Create deterministic but pseudo-random-like embedding
        # based on text content hash
        import hashlib

        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Convert hex hash to normalized float values
        embedding = []
        for i in range(self.EMBEDDING_DIMENSION):
            # Use different parts of hash for each dimension
            char_index = i % len(text_hash)
            hash_char = text_hash[char_index]

            # Convert hex char to normalized float [-1, 1]
            float_val = (int(hash_char, 16) / 15.0) * 2 - 1
            embedding.append(float_val)

        logger.debug(f"Generated mock embedding (strategy={self.embedding_strategy})")
        return embedding

    async def _openai_embed(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API

        Args:
            text: Input text

        Returns:
            OpenAI embedding vector (1536 dimensions)
        """
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=self.EMBEDDING_DIMENSION,
            )

            embedding = response.data[0].embedding

            if len(embedding) != self.EMBEDDING_DIMENSION:
                logger.warning(
                    f"OpenAI returned {len(embedding)} dimensions, expected {self.EMBEDDING_DIMENSION}"
                )

            logger.debug(f"Generated OpenAI embedding (strategy={self.embedding_strategy})")
            return embedding

        except ImportError:
            raise ImportError(
                "OpenAI package is required for OpenAI embeddings. "
                "Install with: pip install openai"
            )
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

    async def _local_embed(self, text: str) -> List[float]:
        """Generate embedding using local model (sentence-transformers)

        Args:
            text: Input text

        Returns:
            Local model embedding vector (normalized to 1536 dimensions)
        """
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np

            # Load model (cached after first load)
            if not hasattr(self, "_local_model"):
                model_name = getattr(
                    self.config, "local_embedding_model", "all-MiniLM-L6-v2"
                )
                logger.info(f"Loading local model: {model_name}")
                self._local_model = SentenceTransformer(model_name)

            # Generate embedding
            embedding = self._local_model.encode(text, convert_to_numpy=True)

            # Normalize to 1536 dimensions
            # If smaller: pad with zeros
            # If larger: truncate
            if len(embedding) < self.EMBEDDING_DIMENSION:
                padding = np.zeros(self.EMBEDDING_DIMENSION - len(embedding))
                embedding = np.concatenate([embedding, padding])
            elif len(embedding) > self.EMBEDDING_DIMENSION:
                embedding = embedding[: self.EMBEDDING_DIMENSION]

            embedding = embedding.tolist()

            logger.debug(f"Generated local embedding (strategy={self.embedding_strategy})")
            return embedding

        except ImportError:
            raise ImportError(
                "sentence-transformers package is required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise

    def get_strategy(self) -> str:
        """Get current embedding strategy

        Returns:
            Strategy name
        """
        return self.embedding_strategy


def create_memory_embedder(config: Optional[SDKConfig] = None) -> MemoryEmbedder:
    """Factory function to create memory embedder

    Args:
        config: Optional SDK configuration

    Returns:
        MemoryEmbedder instance
    """
    return MemoryEmbedder(config=config)
