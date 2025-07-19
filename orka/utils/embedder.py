"""Provide text embedding functionality for the OrKa framework."""

import hashlib
import logging
import random
from typing import Dict, Optional, cast, Union, Type, Any

import numpy as np
from numpy.typing import NDArray

# Define a type alias for SentenceTransformer to handle the import case
SentenceTransformerType: Optional[Type[Any]] = None

try:
    from sentence_transformers import SentenceTransformer

    SentenceTransformerType = SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

# Default embedding dimensions for common models
DEFAULT_EMBEDDING_DIM: int = 384  # Common for smaller models like MiniLM-L6-v2
EMBEDDING_DIMENSIONS: Dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "all-distilroberta-v1": 768,
    "all-MiniLM-L12-v2": 384,
}


class AsyncEmbedder:
    """Async wrapper for SentenceTransformer with robust fallback mechanisms."""

    def __init__(
        self, model_name: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2"
    ) -> None:
        """Initialize the AsyncEmbedder."""
        self.model_name = model_name if model_name else "sentence-transformers/all-MiniLM-L6-v2"
        self.model = None
        self.model_loaded = False

        # Set embedding dimension based on model or use default
        if model_name:
            base_name = model_name.split("/")[-1]
            self.embedding_dim = EMBEDDING_DIMENSIONS.get(base_name, DEFAULT_EMBEDDING_DIM)
        else:
            self.embedding_dim = DEFAULT_EMBEDDING_DIM

        logger.info(f"Using embedding dimension: {self.embedding_dim}")
        self._load_model()

    def _load_model(self) -> None:
        """Load the sentence transformer model."""
        try:
            # Get the SentenceTransformer class from the module or the global scope
            transformer_class = SentenceTransformerType
            if transformer_class is None:
                logger.error("SentenceTransformer not available. Using fallback encoding.")
                return

            self.model = transformer_class(self.model_name)
            if self.model is not None and hasattr(self.model, "get_sentence_embedding_dimension"):
                self.embedding_dim = cast(int, self.model.get_sentence_embedding_dimension())
            self.model_loaded = True
            logger.info(f"Successfully loaded embedding model: {self.model_name}")
        except ImportError as e:
            logger.error(
                f"Failed to import SentenceTransformer: {str(e)}. Using fallback encoding."
            )
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}. Using fallback encoding.")

    def _fallback_encode(self, text: str) -> NDArray[np.float32]:
        """Generate deterministic pseudo-random embeddings when model is unavailable."""
        if not text:
            return np.zeros(self.embedding_dim, dtype=np.float32)

        try:
            # Use text hash as random seed for deterministic output
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            random.seed(text_hash)

            # Generate random vector
            vec = np.array(
                [random.gauss(0, 1) for _ in range(self.embedding_dim)], dtype=np.float32
            )

            # Handle zero norm case
            norm = float(np.linalg.norm(vec))
            if not norm or norm < 1e-10:  # Avoid division by zero
                vec = np.ones(self.embedding_dim, dtype=np.float32) / np.sqrt(
                    float(self.embedding_dim)
                )
            else:
                vec = vec / norm

            return vec
        except Exception as e:
            logger.error(f"Error in fallback encoding: {e}. Using zero vector.")
            return np.zeros(self.embedding_dim, dtype=np.float32)

    async def encode(self, text: str) -> NDArray[np.float32]:
        """Encode text to embedding vector."""
        if not text:
            logger.warning("Empty text provided for encoding. Using zero vector.")
            return np.zeros(self.embedding_dim, dtype=np.float32)

        if self.model_loaded and self.model is not None:
            try:
                embedding = self.model.encode(text)
                # Convert to numpy array first if needed
                if not isinstance(embedding, np.ndarray):
                    try:
                        embedding = np.array(embedding, dtype=np.float32)
                    except Exception as e:
                        logger.error(
                            f"Failed to convert model output to numpy array: {e}. Using fallback."
                        )
                        return self._fallback_encode(text)

                # Check if the converted embedding is valid
                embedding = cast(NDArray[np.float32], embedding)
                if embedding.shape[0] > 0:  # Check first dimension is non-zero
                    # Normalize the vector
                    norm = float(np.linalg.norm(embedding))
                    if not norm or norm < 1e-10:  # Avoid division by zero
                        return np.zeros(self.embedding_dim, dtype=np.float32)

                    normalized = embedding / norm
                    return cast(NDArray[np.float32], normalized.astype(np.float32))
                else:
                    logger.error("Model produced empty embedding. Using fallback.")
            except Exception as e:
                logger.error(f"Error encoding text with model: {str(e)}. Using fallback.")

        logger.warning("Using fallback pseudo-random encoding based on text hash")
        return self._fallback_encode(text)


def to_bytes(vec: Union[NDArray[np.float32], None]) -> bytes:
    """Convert a numpy array to bytes for storage."""
    if vec is None or not isinstance(vec, np.ndarray):
        return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32).tobytes()

    # Ensure float32 type and normalize
    vec = vec.astype(np.float32)
    norm = float(np.linalg.norm(vec))
    if not norm or norm < 1e-10:  # Avoid division by zero
        vec = np.zeros_like(vec)
    else:
        vec = vec / norm

    return vec.tobytes()


def from_bytes(b: bytes) -> NDArray[np.float32]:
    """Convert bytes back to a numpy array."""
    try:
        if not b:
            return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32)
        return np.frombuffer(b, dtype=np.float32)
    except ValueError as e:
        logger.error(f"Failed to convert bytes to array: {e}")
        return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32)


# Global embedder instance for singleton pattern
_embedder: Optional[AsyncEmbedder] = None


def get_embedder(name: Optional[str] = None) -> AsyncEmbedder:
    """Get or create a singleton embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = AsyncEmbedder(name)
    return _embedder
