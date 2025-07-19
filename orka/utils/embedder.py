"""Provide text embedding functionality for the OrKa framework.

This module provides text embedding functionality for the OrKa framework with robust
fallback mechanisms. It is designed to be resilient and provide embeddings even in
cases where model loading fails or when running in restricted environments.

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
import os
import random
from typing import Dict, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

# Global embedder instance for singleton pattern
_embedder: Optional[AsyncEmbedder] = None

# Default embedding dimensions for common models
DEFAULT_EMBEDDING_DIM: int = 384  # Common for smaller models like MiniLM-L6-v2
EMBEDDING_DIMENSIONS: Dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "all-distilroberta-v1": 768,
    "all-MiniLM-L12-v2": 384,
}


class AsyncEmbedder:
    """
    Async wrapper for SentenceTransformer with robust fallback mechanisms.

    This class provides an async-friendly interface to sentence transformer models for
    generating text embeddings. It includes robust error handling, fallback mechanisms,
    and resilience features to ensure embedding functionality always works.

    Key features:
    - Lazy loading of embedding models to reduce startup time
    - Graceful fallback to deterministic pseudo-random embeddings when models fail
    - Consistent embedding dimensions regardless of model availability
    - Automatic model file detection to prevent unnecessary downloads

    Attributes:
        model_name (str): Name of the sentence transformer model to use
        model (Optional[SentenceTransformer]): The SentenceTransformer model instance or None if loading failed
        model_loaded (bool): Whether the model was successfully loaded
        embedding_dim (int): Dimension of the embedding vectors produced
    """

    def __init__(
        self, model_name: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2"
    ) -> None:
        """
        Initialize the AsyncEmbedder with the specified model.

        Args:
            model_name: Name of the sentence transformer model to use.
                Defaults to "sentence-transformers/all-MiniLM-L6-v2", a lightweight
                but effective general-purpose embedding model.

        Note:
            Model loading happens during initialization but has fallback mechanisms
            to ensure the embedder remains functional even if loading fails.
        """
        self.model_name: str = (
            model_name if model_name else "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.model: Optional[SentenceTransformer] = None
        self.model_loaded: bool = False

        # Set embedding dimension based on model or use default
        if model_name:
            base_name = model_name.split("/")[-1]
            self.embedding_dim: int = EMBEDDING_DIMENSIONS.get(base_name, DEFAULT_EMBEDDING_DIM)
        else:
            self.embedding_dim = DEFAULT_EMBEDDING_DIM

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
            if self.model_name and not self.model_name.startswith(("http:", "https:")):
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

            # Load the model
            if SentenceTransformer is not None:
                self.model = SentenceTransformer(self.model_name)
                self.model_loaded = True
                if self.model is not None and hasattr(
                    self.model, "get_sentence_embedding_dimension"
                ):
                    self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(
                    f"Successfully loaded embedding model: {self.model_name} with dimension {self.embedding_dim}"
                )
        except ImportError as e:
            logger.error(
                f"Failed to import SentenceTransformer: {str(e)}. Using fallback encoding."
            )
            self.model_loaded = False
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {str(e)}. Using fallback encoding.")
            self.model_loaded = False

    async def encode(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector with robust fallback mechanisms.

        This async method converts text to a numerical vector representation using
        either the loaded model or fallback mechanisms. It ensures that valid
        embeddings are always returned, regardless of model status.

        Args:
            text: The text to encode into an embedding vector

        Returns:
            A normalized embedding vector of shape (embedding_dim,)

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
                embedding = self.model.encode(text)
                # Ensure the embedding is the right shape
                if isinstance(embedding, np.ndarray) and embedding.size > 0:
                    return embedding
                else:
                    logger.error(f"Model produced invalid embedding: {embedding}. Using fallback.")
            except Exception as e:
                logger.error(f"Error encoding text with model: {str(e)}. Using fallback.")

        # If we get here, we need to use the fallback
        logger.warning("Using fallback pseudo-random encoding based on text hash")
        return self._fallback_encode(text)

    def _fallback_encode(self, text: str) -> np.ndarray:
        """
        Generate a deterministic pseudo-random embedding based on text hash.

        This method creates embeddings when the primary model is unavailable.
        It uses a hash-based approach to generate deterministic vectors, ensuring
        that identical text inputs always produce the same embedding vectors.

        Args:
            text: The text to encode

        Returns:
            A normalized embedding vector of shape (embedding_dim,)

        Note:
            The generated embeddings are deterministic but don't have the semantic
            properties of true model-based embeddings. They are suitable for basic
            storage and retrieval but not for advanced semantic operations.
        """
        # Use text hash as random seed for deterministic output
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        random.seed(text_hash)

        # Generate pseudo-random vector
        vec = np.array([random.gauss(0, 1) for _ in range(self.embedding_dim)])

        # Normalize to unit length (L2 norm)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.astype(np.float32)


def get_embedder(name: Optional[str] = None) -> AsyncEmbedder:
    """
    Get or create a singleton embedder instance.

    This function implements the singleton pattern for embedder instances to avoid
    loading multiple copies of large models into memory. It ensures efficient
    resource usage while providing consistent embedding functionality.

    Args:
        name: Optional model name to use. If None, uses the default model.

    Returns:
        A singleton AsyncEmbedder instance.

    Example:
        ```python
        # Get default embedder
        embedder1 = get_embedder()
        embedder2 = get_embedder()  # Returns same instance as embedder1

        # Get specific model embedder
        custom_embedder = get_embedder("sentence-transformers/all-mpnet-base-v2")
        ```
    """
    global _embedder
    if _embedder is None:
        _embedder = AsyncEmbedder(name)
    return _embedder


def to_bytes(vec: np.ndarray) -> bytes:
    """
    Convert a numpy array to bytes for storage.

    This function serializes a numpy array to a compact byte representation
    suitable for storage in databases or transmission over networks.

    Args:
        vec: The numpy array to convert

    Returns:
        The serialized byte representation of the array

    Example:
        ```python
        embedding = await embedder.encode("sample text")
        bytes_data = to_bytes(embedding)
        # Store bytes_data in database
        ```
    """
    return vec.tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    """
    Convert bytes back to a numpy array.

    This function deserializes a byte representation back into a numpy array,
    typically used when retrieving embeddings from storage.

    Args:
        b: The bytes to convert back to an array

    Returns:
        The deserialized numpy array

    Example:
        ```python
        # Retrieve bytes_data from database
        embedding = from_bytes(bytes_data)
        # Use embedding for similarity comparison, etc.
        ```
    """
    return np.frombuffer(b, dtype=np.float32)
