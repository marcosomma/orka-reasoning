"""Proof test for P1: episodic semantic recall actually uses embeddings.

Before this fix, no embedder was ever passed to the Brain (both `Brain(...)`
construction sites omitted it), so `EpisodeStore.semantic_search` always fell
back to keyword (Jaccard) overlap and the documented "Semantic similarity (50%)"
weight contributed nothing.

This test demonstrates the before/after on two lexically-disjoint but
semantically-similar phrases:
    "draft a polite refusal email"  vs  "compose a courteous rejection message"

- BEFORE (no embedder -> keyword fallback): near-zero similarity, and the
  unrelated episode is not meaningfully separated.
- AFTER (real embedder wired): the semantically-related episode is ranked far
  above the unrelated one.

The test skips when no real sentence-transformer model is available, so it
asserts genuine semantic behavior only when it can actually be observed.
"""

from __future__ import annotations

import pytest

from orka.brain.embedding import default_brain_embedder
from orka.brain.episode import Episode
from orka.brain.episode_store import EpisodeStore

QUERY = "draft a polite refusal email"
RELATED = "compose a courteous rejection message"
UNRELATED = "how to deep fry a turkey safely"


def _make_episode(text: str) -> Episode:
    # Put the phrase in outcome_summary so to_embedding_text() carries it,
    # and use a neutral shared domain so domain scoring doesn't dominate.
    return Episode(task_input=text, task_domain="general", outcome_summary=text)


def _real_embedder():
    emb = default_brain_embedder()
    if emb is None:
        pytest.skip("No real embedding model available; semantic behavior cannot be observed.")
    return emb


def test_keyword_fallback_barely_matches(fake_memory) -> None:
    """BEFORE: with no embedder, keyword overlap barely connects the phrases."""
    store = EpisodeStore(memory=fake_memory)  # embedder=None -> keyword fallback
    store.save_episode(_make_episode(RELATED))
    store.save_episode(_make_episode(UNRELATED))

    results = store.semantic_search(QUERY, top_k=2)
    scores = {ep.outcome_summary: score for ep, score in results}

    # Jaccard of {draft,a,polite,refusal,email} vs {compose,a,courteous,rejection,message}
    # shares only "a" -> ~0.11; with the domain prefix it stays very low.
    assert scores[RELATED] < 0.25, f"keyword sim unexpectedly high: {scores[RELATED]}"


def test_embedder_recovers_semantic_match(fake_memory) -> None:
    """AFTER: with the embedder wired, the related episode is ranked first and high."""
    embedder = _real_embedder()
    store = EpisodeStore(memory=fake_memory, embedder=embedder)
    store.save_episode(_make_episode(RELATED))
    store.save_episode(_make_episode(UNRELATED))

    results = store.semantic_search(QUERY, top_k=2)
    assert results, "semantic_search returned no results"

    top_ep, top_score = results[0]
    scored = {ep.outcome_summary: score for ep, score in results}

    # The semantically related episode must rank first...
    assert top_ep.outcome_summary == RELATED, f"top match was {top_ep.outcome_summary!r}"
    # ...with a clearly semantic score (cosine of the example pair ~0.66 -> ~0.83 in [0,1])...
    assert top_score > 0.6, f"related score too low: {top_score}"
    # ...and clearly separated from the unrelated episode.
    # NOTE: _vector_search normalizes cosine via (cos+1)/2, so an *orthogonal*
    # (unrelated) pair floors at ~0.5, not 0. Observed: related~0.78, unrelated~0.49.
    # The separation is therefore bounded by that floor; >0.25 is a real, clear gap.
    assert scored[RELATED] - scored[UNRELATED] > 0.25, f"insufficient separation: {scored}"


def test_embedder_beats_keyword_on_same_data(fake_memory) -> None:
    """Direct before/after on identical data: embedding sim >> keyword sim."""
    related_ep = _make_episode(RELATED)

    kw_store = EpisodeStore(memory=fake_memory)  # keyword
    kw_store.save_episode(related_ep)
    kw_sim = dict((ep.outcome_summary, s) for ep, s in kw_store.semantic_search(QUERY, top_k=1))[RELATED]

    embedder = _real_embedder()
    vec_store = EpisodeStore(memory=fake_memory, embedder=embedder)
    vec_sim = vec_store._vector_search(QUERY, [related_ep], top_k=1)[0][1]

    assert vec_sim > kw_sim + 0.4, f"embedding ({vec_sim:.3f}) did not beat keyword ({kw_sim:.3f})"
