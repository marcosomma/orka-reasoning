import hashlib
import logging
import os
import random

import numpy as np

logger = logging.getLogger(__name__)

# Global embedder instance
_embedder = None

# Default embedding dimensions for common models
DEFAULT_EMBEDDING_DIM = 384  # Common for smaller models like MiniLM-L6-v2
EMBEDDING_DIMENSIONS = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "all-distilroberta-v1": 768,
    "all-MiniLM-L12-v2": 384,
}


class AsyncEmbedder:
    """Async wrapper for SentenceTransformer with robust fallback mechanisms."""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = (
            model_name if model_name else "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.model = None
        self.model_loaded = False

        # Set embedding dimension based on model or use default
        if model_name:
            base_name = model_name.split("/")[-1]
            self.embedding_dim = EMBEDDING_DIMENSIONS.get(
                base_name, DEFAULT_EMBEDDING_DIM
            )
        else:
            self.embedding_dim = DEFAULT_EMBEDDING_DIM

        logger.info(f"Using embedding dimension: {self.embedding_dim}")

        # Try to load the model
        self._load_model()

    def _load_model(self):
        """Load the sentence transformer model with error handling."""
        try:
            # Only import if needed to reduce startup time
            from sentence_transformers import SentenceTransformer

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
            self.model = SentenceTransformer(self.model_name)
            self.model_loaded = True
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
            logger.warning(
                f"Failed to load embedding model: {str(e)}. Using fallback encoding."
            )
            self.model_loaded = False

    async def encode(self, text: str) -> np.ndarray:
        """Encode text to embedding vector with robust fallback mechanisms."""
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
                    logger.error(
                        f"Model produced invalid embedding: {embedding}. Using fallback."
                    )
            except Exception as e:
                logger.error(
                    f"Error encoding text with model: {str(e)}. Using fallback."
                )

        # If we get here, we need to use the fallback
        logger.warning("Using fallback pseudo-random encoding based on text hash")
        return self._fallback_encode(text)

    def _fallback_encode(self, text: str) -> np.ndarray:
        """Generate a deterministic pseudo-random embedding based on text hash."""
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


def get_embedder(name=None):
    """Get or create the singleton embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = AsyncEmbedder(name)
    return _embedder


def to_bytes(vec: np.ndarray) -> bytes:
    """Convert embedding vector to normalized bytes."""
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
    """Convert bytes back to a numpy array embedding vector."""
    try:
        return np.frombuffer(b, dtype=np.float32)
    except Exception as e:
        logger.error(f"Error converting bytes to vector: {str(e)}")
        # Return empty vector as fallback
        return np.zeros(DEFAULT_EMBEDDING_DIM, dtype=np.float32)
