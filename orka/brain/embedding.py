# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Brain Embedding Adapter
=======================

The Brain's scoring paths — :mod:`orka.brain.transfer_engine` and
:mod:`orka.brain.episode_store` — are synchronous and call
``embedder.encode(text)`` expecting a vector back immediately. The framework's
:class:`orka.utils.embedder.AsyncEmbedder` exposes its model-backed encoding
synchronously as ``encode_sync`` (``encode`` itself is a coroutine).

Passing an ``AsyncEmbedder`` directly to the Brain therefore does **not** work:
``encode`` returns a coroutine, the cosine math raises, and both consumers
silently fall back to keyword overlap. This adapter bridges the two so the
Brain receives real sentence-transformer embeddings.

Honesty guard: :func:`default_brain_embedder` returns ``None`` when no real
embedding model is loaded. That deliberately routes the Brain to its keyword
fallback rather than feeding it the deterministic *random* vectors the
``AsyncEmbedder`` produces when its model is unavailable — random vectors would
manufacture meaningless "semantic" similarity scores.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SyncBrainEmbedder:
    """Adapt an async-capable embedder to the Brain's synchronous ``encode`` API.

    Args:
        embedder: An object exposing a synchronous ``encode_sync(text) -> vector``
            method (e.g. :class:`orka.utils.embedder.AsyncEmbedder`).
    """

    def __init__(self, embedder: Any) -> None:
        self._embedder = embedder

    def encode(self, text: str) -> Any:
        """Return a vector for ``text`` synchronously."""
        return self._embedder.encode_sync(text)


def default_brain_embedder() -> SyncBrainEmbedder | None:
    """Build the default Brain embedder, or ``None`` if no real model is available.

    Returns ``None`` (so the Brain uses keyword overlap) when the embedding model
    failed to load, rather than silently scoring on random fallback vectors.
    """
    try:
        from orka.utils.embedder import get_embedder

        embedder = get_embedder()
        if not getattr(embedder, "model_loaded", False):
            logger.warning(
                "Embedding model not loaded; Brain semantic recall will use keyword fallback."
            )
            return None
        return SyncBrainEmbedder(embedder)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Brain embedder unavailable (%s); using keyword fallback.", exc)
        return None
