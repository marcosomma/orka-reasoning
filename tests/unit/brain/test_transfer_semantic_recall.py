"""POC ④: the skill-transfer semantic path actually uses embeddings.

The existing transfer tests run with no embedder (semantic falls back to keyword).
P1 wired a real embedder into the Brain; this test proves _compute_semantic_similarity
discriminates a semantically-related skill from an unrelated one for a query that shares
MEANING but not WORDS — the cross-domain transfer the engine is meant to enable.
"""

from __future__ import annotations

import pytest

from orka.brain.context_analyzer import ContextAnalyzer
from orka.brain.embedding import default_brain_embedder
from orka.brain.skill import Skill, SkillStep
from orka.brain.skill_graph import SkillGraph
from orka.brain.transfer_engine import SkillTransferEngine


class _FakeMemory:
    def __init__(self):
        self._h, self._s, self._kv = {}, {}, {}

    def get(self, k): return self._kv.get(k)
    def set(self, k, v): self._kv[k] = v; return True
    def delete(self, *ks): return 0
    def hset(self, n, k, v): self._h.setdefault(n, {})[k] = v; return 1
    def hget(self, n, k): return self._h.get(n, {}).get(k)
    def hkeys(self, n): return list(self._h.get(n, {}).keys())
    def hdel(self, n, *ks): return 0
    def sadd(self, n, *vs): self._s.setdefault(n, set()).update(vs); return len(vs)
    def srem(self, n, *vs): return 0
    def smembers(self, n): return list(self._s.get(n, set()))


def _skill(name, description):
    # Identical structure so STRUCTURAL score is equal; only the description differs,
    # isolating the SEMANTIC contribution.
    return Skill(
        name=name,
        description=description,
        procedure=[SkillStep(action="do it", order=0)],
        source_context={
            "task_structures": ["transformation"],
            "cognitive_patterns": ["generation"],
            "input_shape": "single_text",
            "output_shape": "text",
        },
        tags=["transformation", "generation"],
        confidence=0.6,
    )


def test_semantic_similarity_discriminates_related_skill():
    embedder = default_brain_embedder()
    if embedder is None:
        pytest.skip("No real embedding model available; semantic behavior cannot be observed.")

    graph = SkillGraph(memory=_FakeMemory())
    graph.save_skill(_skill("Polite Decline", "Draft a courteous email declining a request"))
    graph.save_skill(_skill("Turkey Fry", "Steps to deep-fry a turkey safely outdoors"))

    engine = SkillTransferEngine(skill_graph=graph, context_analyzer=ContextAnalyzer(), embedder=embedder)
    candidates = engine.find_transferable_skills(
        {"task": "write a respectful message rejecting a proposal", "domain": "comms"},
        min_score=0.0,
    )
    by_name = {c.skill.name: c for c in candidates}
    assert "Polite Decline" in by_name and "Turkey Fry" in by_name
    # The semantically-related skill must score higher on the SEMANTIC axis...
    assert by_name["Polite Decline"].semantic_score > by_name["Turkey Fry"].semantic_score
    # ...and rank first overall.
    assert candidates[0].skill.name == "Polite Decline"
