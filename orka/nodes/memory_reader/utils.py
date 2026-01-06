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
Utility Functions for Memory Reader
====================================

Common utility functions for memory search and scoring.
"""

import logging

try:
    import numpy as np
except Exception:
    np = None  # type: ignore

logger = logging.getLogger(__name__)


def calculate_overlap(text1: str, text2: str) -> float:
    """
    Calculate text overlap score between two strings.

    Args:
        text1: First text (typically the query)
        text2: Second text (typically the memory content)

    Returns:
        Overlap score between 0.0 and 1.0 (can be boosted to 2.0 for perfect matches)
    """
    try:
        if not text1 or not text2:
            return 0.0

        # Tokenize and normalize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Calculate overlap
        overlap = len(words1.intersection(words2))
        total = len(words1)  # Only consider query words

        # Calculate overlap score
        overlap_score = overlap / total if total > 0 else 0.0

        # Boost score if all query words are found
        if overlap == total:
            overlap_score *= 2

        return overlap_score

    except Exception as e:
        logger.error(f"Error calculating text overlap: {e}")
        return 0.0


def cosine_similarity(vec1, vec2) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector (numpy array or list)
        vec2: Second vector (numpy array or list)

    Returns:
        Cosine similarity between -1.0 and 1.0
    """
    try:
        if np is None:
            logger.error("NumPy not available for cosine similarity")
            return 0.0

        # Ensure vectors are numpy arrays
        if not isinstance(vec1, np.ndarray):
            vec1 = np.array(vec1)
        if not isinstance(vec2, np.ndarray):
            vec2 = np.array(vec2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)
        return float(similarity)

    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e!s}")
        return 0.0

