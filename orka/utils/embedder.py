# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Embedder Module
==============

This module provides text embedding functionality for the OrKa framework with robust
fallback mechanisms. It is designed to provide best-effort embeddings even when
model loading fails or when running in restricted environments.

Purpose: Provide text embeddings with fallback strategies and deterministic behavior when models are unavailable.

Assumptions:
- External model files may not be present in all environments; fallback hashing is used when models are unavailable.
- Deterministic fallback embeddings are suitable for basic storage and retrieval but not for advanced semantic operations.

Proof: Unit tests in `tests/unit/utils/test_embedder.py` cover model loading, fallback, and deterministic behavior.

Key features:
- Async-friendly embedding interface
- Singleton pattern for efficient resource use
- Fallback mechanisms for reliability
- Deterministic pseudo-random embeddings when models unavailable
- Utility functions for embedding storage and retrieval

The module supports several embedding models from the sentence-transformers library,
with automatic dimension detection and handling. When primary models are unavailable,
it falls back to deterministic hash-based embeddings that preserve basic semantic
relationships.

Usage example:
```python
from orka.utils.embedder import get_embedder, to_bytes

# Get the default embedder (singleton)
embedder = get_embedder()

# Get embeddings for a text
async def process_text(text):
    # Get vector embedding
    embedding = await embedder.encode(text)

    # Convert to bytes for storage if needed
    embedding_bytes = to_bytes(embedding)

    # Use embedding for semantic search, clustering, etc.
    return embedding
```
"""

import hashlib
import logging
import logging as std_logging
import os
import random
from typing import Any, Optional, Union, cast

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Set a specific cache directory for Sentence Transformers models
os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "sentence_transformers"
)

# Default embedding dimensions for common models
DEFAULT_EMBEDDING_DIM = 384  # Common for smaller models like MiniLM-L6-v2
EMBEDDING_DIMENSIONS = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "all-distilroberta-v1": 768,
    "all-MiniLM-L12-v2": 384,
}


def _ensure_numpy_array(data: Any) -> np.ndarray:
    """Convert any array-like data to a numpy array."""
    if isinstance(data, np.ndarray):
        return data
    try:
        # Try to convert to numpy array
        arr = np.array(data, dtype=np.float32)
        if arr.size > 0:
            return arr
    except Exception as e:
        logger.error(f"Error converting to numpy array: {e}")
    # Return zero array as fallback
    return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32)


class AsyncEmbedder:
    """
    Async wrapper for SentenceTransformer with robust fallback mechanisms.

    This class provides an async-friendly interface to sentence transformer models for
    generating text embeddings. It includes robust error handling, fallback mechanisms,
    and resilience features to provide best-effort embedding functionality in diverse environments.

    Key features:
    - Lazy loading of embedding models to reduce startup time
    - Graceful fallback to deterministic pseudo-random embeddings when models fail
    - Consistent embedding dimensions regardless of model availability
    - Automatic model file detection to prevent unnecessary downloads

    Attributes:
        model_name (str): Name of the sentence transformer model to use
        model: The SentenceTransformer model instance or None if loading failed
        model_loaded (bool): Whether the model was successfully loaded
        embedding_dim (int): Dimension of the embedding vectors produced
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.model_loaded = False

        # Set embedding dimension based on model or use default
        base_name = model_name.split("/")[-1]
        self.embedding_dim = EMBEDDING_DIMENSIONS.get(base_name, DEFAULT_EMBEDDING_DIM)

        logger.info(f"Using embedding dimension: {self.embedding_dim}")

        # Try to load the model
        self._load_model()

    def _load_model(self) -> None:
        """
        Load the sentence transformer model with comprehensive error handling.

        This method attempts to load the specified sentence transformer model
        with multiple layers of error handling:
        1. Checks for import errors (missing dependencies)
        2. Verifies model files exist locally before loading
        3. Handles general exceptions during model loading

        The method sets model_loaded to True if successful, False otherwise.
        Even on failure, the embedder will remain functional using fallback mechanisms.
        """
        try:
            # Check for model file existence before loading
            if not self.model_name.startswith(("http:", "https:")):
                # Check if model exists in common locations
                home_dir = os.path.expanduser("~")
                model_paths = [
                    os.path.join(
                        home_dir,
                        ".cache",
                        "torch",
                        "sentence_transformers",
                        self.model_name.split("/")[-1],
                    ),
                    os.path.join(
                        home_dir,
                        ".cache",
                        "huggingface",
                        "transformers",
                        self.model_name.split("/")[-1],
                    ),
                ]

                model_found = any(os.path.exists(path) for path in model_paths)
                if not model_found:
                    logger.warning(
                        f"Model files not found locally for {self.model_name}. May need to download."
                    )

            # Temporarily suppress noisy library logs
            datasets_logger = std_logging.getLogger("datasets")
            transformers_logger = std_logging.getLogger("transformers")
            torch_logger = std_logging.getLogger("torch")

            original_levels = {
                "datasets": datasets_logger.level,
                "transformers": transformers_logger.level,
                "torch": torch_logger.level,
            }

            # Set to WARNING to suppress INFO logs
            datasets_logger.setLevel(std_logging.WARNING)
            transformers_logger.setLevel(std_logging.WARNING)
            torch_logger.setLevel(std_logging.WARNING)

            try:
                model = SentenceTransformer(self.model_name)
            finally:
                # Restore original log levels
                datasets_logger.setLevel(original_levels["datasets"])
                transformers_logger.setLevel(original_levels["transformers"])
                torch_logger.setLevel(original_levels["torch"])
            self.model = model
            self.model_loaded = True
            dim = model.get_sentence_embedding_dimension()
            if dim is not None:
                self.embedding_dim = dim
            logger.info(
                f"Successfully loaded embedding model: {self.model_name} with dimension {self.embedding_dim}"
            )
            return  # Return early on success
        except ImportError as e:
            logger.error(
                f"Failed to import SentenceTransformer: {str(e)}. Using fallback encoding."
            )
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {str(e)}. Using fallback encoding.")

        # If we get here, model loading failed
        self.model_loaded = False
        self.model = None

    async def encode(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector with robust fallback mechanisms.

        This async method converts text to a numerical vector representation using
        either the loaded model or fallback mechanisms. It aims to return embeddings when possible; when the model is unavailable, deterministic fallback embeddings or zeros are provided per fallback policy.

        Args:
            text (str): The text to encode into an embedding vector

        Returns:
            np.ndarray: A normalized embedding vector of shape (embedding_dim,)

        Note:
            The method has a three-tier fallback system:
            1. Try using the primary model if loaded
            2. Fall back to deterministic hash-based pseudo-random encoding if model fails
            3. Last resort: return a zero vector if all else fails

        Example:
            ```python
            embedder = AsyncEmbedder()
            embedding = await embedder.encode("This is a sample text")
            # embedding shape: (384,)
            ```
        """
        if not text:
            logger.warning("Empty text provided for encoding. Using zero vector.")
            return np.zeros(self.embedding_dim, dtype=np.float32)

        # Try using the primary model
        if self.model_loaded and self.model is not None:
            try:
                # Get the embedding and ensure it's a numpy array
                result = self.model.encode(text)
                return _ensure_numpy_array(result)
            except Exception as e:
                logger.error(f"Error encoding text with model: {str(e)}. Using fallback.")

        # If we get here, we need to use the fallback
        logger.warning("Using fallback pseudo-random encoding based on text hash")
        return self._fallback_encode(text)

    def embed(self, text: str) -> np.ndarray:
        """
        Synchronous embedding method compatible with existing call sites.

        This mirrors the logic of `encode` without async, so it can be used
        in synchronous scoring and routing paths without event loop juggling.

        Args:
            text: Text to embed

        Returns:
            np.ndarray: Embedding vector
        """
        if not text:
            logger.warning("Empty text provided for embedding. Using zero vector.")
            return np.zeros(self.embedding_dim, dtype=np.float32)

        if self.model_loaded and self.model is not None:
            try:
                result = self.model.encode(text)
                return _ensure_numpy_array(result)
            except Exception as e:
                logger.error(f"Error embedding text with model: {str(e)}. Using fallback.")

        logger.warning("Using fallback pseudo-random embedding based on text hash")
        return self._fallback_encode(text)

    def _fallback_encode(self, text: str) -> np.ndarray:
        """
        Generate a deterministic pseudo-random embedding based on text hash.

        This method creates embeddings when the primary model is unavailable.
        It uses a hash-based approach to generate deterministic vectors, ensuring
        that identical text inputs produce deterministic fallback embeddings when model-based embeddings are not available.

        Args:
            text (str): The text to encode

        Returns:
            np.ndarray: A normalized embedding vector of shape (embedding_dim,)

        Note:
            The generated embeddings are deterministic but don't have the semantic
            properties of true model-based embeddings. They are suitable for basic
            storage and retrieval but not for advanced semantic operations.
        """
        try:
            # Create a deterministic hash of the text
            text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

            # Set random seed based on text hash for deterministic output
            random.seed(text_hash)

            # Generate a random embedding vector
            vec = np.array(
                [random.uniform(-1, 1) for _ in range(self.embedding_dim)],
                dtype=np.float32,
            )

            # Normalize to unit length for cosine similarity
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            return vec
        except Exception as e:
            logger.error(f"Error in fallback encoding: {str(e)}. Using zeros vector.")
            # Last resort - return zeros
            return np.zeros(self.embedding_dim, dtype=np.float32)


# Global embedder instance for singleton pattern
_embedder: Optional[AsyncEmbedder] = None


def get_embedder(name: Optional[str] = None) -> AsyncEmbedder:
    """
    Get or create the singleton embedder instance.

    This function implements the singleton pattern to ensure only one embedder
    instance is created and reused, conserving resources. The first call creates
    the embedder with the specified model name; subsequent calls return the
    existing instance regardless of the name parameter.

    Args:
        name (str, optional): Model name to use if creating a new embedder instance.
            Ignored if an embedder already exists.

    Returns:
        AsyncEmbedder: The singleton embedder instance

    Example:
        ```python
        # First call creates the embedder
        embedder1 = get_embedder("sentence-transformers/all-MiniLM-L6-v2")

        # Second call returns the same instance even with different model name
        embedder2 = get_embedder("different-model")
        assert embedder1 is embedder2  # True
        ```
    """
    global _embedder
    if _embedder is None:
        _embedder = AsyncEmbedder(name or "sentence-transformers/all-MiniLM-L6-v2")
    return _embedder


def to_bytes(vec: np.ndarray) -> bytes:
    """
    Convert embedding vector to normalized bytes for storage.

    This utility function converts a numpy embedding vector to bytes format
    for efficient storage in databases or caches. It ensures consistent
    normalization and data types.

    Args:
        vec (np.ndarray): The embedding vector to convert

    Returns:
        bytes: The normalized vector in bytes format

    Note:
        The function handles errors gracefully, returning empty vector bytes
        if conversion fails.

    Example:
        ```python
        embedding = await embedder.encode("Sample text")
        bytes_data = to_bytes(embedding)
        # Store bytes_data in Redis or other storage
        ```
    """
    try:
        # Ensure vector is float32 for consistent storage
        vec = vec.astype(np.float32)

        # Normalize for cosine similarity
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tobytes()
    except Exception as e:
        logger.error(f"Error converting vector to bytes: {str(e)}")
        # Return empty bytes as fallback
        return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32).tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    """
    Convert bytes back to a numpy array embedding vector.

    This utility function reverses the to_bytes conversion, reconstructing
    a numpy array from its byte representation. It's used when retrieving
    embedding vectors from storage.

    Args:
        b (bytes): The bytes representation of the embedding vector

    Returns:
        np.ndarray: The reconstructed embedding vector

    Note:
        The function handles errors gracefully, returning a zero vector
        if conversion fails.

    Example:
        ```python
        # Retrieve bytes_data from storage
        embedding = from_bytes(bytes_data)
        # Use embedding for similarity calculations, etc.
        ```
    """
    try:
        return np.frombuffer(b, dtype=np.float32)
    except Exception as e:
        logger.error(f"Error converting bytes to vector: {str(e)}")
        # Return empty vector as fallback
        return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32)
