import numpy as np
from sentence_transformers import SentenceTransformer

_embedder = None


def get_embedder(name="sentence-transformers/all-MiniLM-L6-v2"):
    """Get or create the singleton embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(name)
    return _embedder


def to_bytes(vec: np.ndarray) -> bytes:
    """Convert embedding vector to normalized bytes."""
    vec = vec.astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-9  # cosine works on unit vectors
    return vec.tobytes()
