"""Episodic brain → stable: embeddings are computed once at save and reused at recall.

Before: _vector_search re-encoded every candidate on every query (O(n) embed calls
per recall). Now each episode is embedded once at save_episode and the vector is
persisted; recall encodes only the query and loads stored vectors.
"""

from __future__ import annotations

import numpy as np

from orka.brain.episode import Episode
from orka.brain.episode_store import EpisodeStore


class CountingEmbedder:
    """Deterministic embedder that counts how many times encode() is called."""

    def __init__(self) -> None:
        self.calls = 0

    def encode(self, text: str):
        self.calls += 1
        t = (text or "").lower()
        if "alpha" in t:
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in t:
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)


def _ep(text: str) -> Episode:
    return Episode(task_input=text, task_domain="general", outcome_summary=text)


def test_embedding_computed_once_per_save_and_not_per_candidate(fake_memory):
    emb = CountingEmbedder()
    store = EpisodeStore(memory=fake_memory, embedder=emb)

    store.save_episode(_ep("alpha topic one"))
    store.save_episode(_ep("beta topic two"))
    store.save_episode(_ep("gamma topic three"))
    assert emb.calls == 3, "save should embed each episode exactly once"

    # A recall must encode ONLY the query, reusing the 3 stored vectors.
    store.semantic_search("alpha query", top_k=3)
    assert emb.calls == 4, f"recall re-embedded candidates (calls={emb.calls}, expected 4)"

    # A second recall: again only +1 (the query), never the candidates.
    store.semantic_search("alpha again", top_k=3)
    assert emb.calls == 5, f"second recall re-embedded candidates (calls={emb.calls}, expected 5)"


def test_vector_ranking_uses_stored_vectors(fake_memory):
    emb = CountingEmbedder()
    store = EpisodeStore(memory=fake_memory, embedder=emb)
    store.save_episode(_ep("alpha document"))
    store.save_episode(_ep("beta document"))

    results = store.semantic_search("alpha query", top_k=2)
    top_text = results[0][0].outcome_summary
    assert "alpha" in top_text, f"expected alpha episode first, got {top_text!r}"
    assert results[0][1] > results[1][1]


def test_lazy_backfill_for_episodes_saved_without_embedder(fake_memory):
    # Save with NO embedder (no vector persisted)...
    EpisodeStore(memory=fake_memory).save_episode(_ep("alpha legacy"))
    # ...then search WITH an embedder: it must backfill, not crash or skip.
    emb = CountingEmbedder()
    store = EpisodeStore(memory=fake_memory, embedder=emb)
    results = store.semantic_search("alpha query", top_k=1)
    assert results and "alpha" in results[0][0].outcome_summary


def test_delete_removes_cached_vector(fake_memory):
    emb = CountingEmbedder()
    store = EpisodeStore(memory=fake_memory, embedder=emb)
    eid = store.save_episode(_ep("alpha doc"))
    assert store._load_embedding(eid) is not None
    store.delete_episode(eid)
    assert store._load_embedding(eid) is None
