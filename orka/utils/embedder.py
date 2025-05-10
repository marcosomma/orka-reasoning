import numpy as np
from sentence_transformers import SentenceTransformer

_embedder = None


class AsyncEmbedder:
    """Async wrapper for SentenceTransformer."""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    async def encode(self, text: str) -> np.ndarray:
        """Encode text to embedding vector."""
        return self.model.encode(text)


def get_embedder(name="sentence-transformers/all-MiniLM-L6-v2"):
    """Get or create the singleton embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = AsyncEmbedder(name)
    return _embedder


def to_bytes(vec: np.ndarray) -> bytes:
    """Convert embedding vector to normalized bytes."""
    vec = vec.astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-9  # cosine works on unit vectors
    return vec.tobytes()
