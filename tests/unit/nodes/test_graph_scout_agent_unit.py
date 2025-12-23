# Unit tests to increase branch coverage of GraphScoutAgent

import asyncio
from typing import Any, Dict, List

import pytest

from orka.nodes.graph_scout_agent import GraphScoutAgent


class OrchestratorStub:
    pass


class FakeGraphAPI:
    async def get_graph_state(self, orchestrator, run_id):
        return {"nodes": [], "edges": []}


class FakeIntrospector:
    def __init__(self, candidates: List[Dict[str, Any]]):
        self._cands = candidates

    async def discover_paths(self, graph_state, question, context, executing_node=""):
        return list(self._cands)


class FakeBudget:
    def __init__(self, keep: bool):
        self.keep = keep

    async def filter_candidates(self, cands, context):
        return list(cands) if self.keep else []


class FakeEvaluator:
    def __init__(self, capture: Dict[str, Any]):
        self.capture = capture

    async def simulate_candidates(self, cands, question, evaluation_context, orchestrator):
        # Ensure current_agent_id is propagated
        self.capture["current_agent_id"] = evaluation_context.get("current_agent_id")
        return list(cands)


class FakeSafety:
    def __init__(self, keep: bool):
        self.keep = keep

    async def assess_candidates(self, cands, context):
        return list(cands) if self.keep else []


class FakeScorer:
    def __init__(self, score: float = 0.9):
        self.score = score

    async def score_candidates(self, cands, question, context):
        return [
            {
                "node_id": c.get("node_id", "n"),
                "score": self.score,
                "components": {"h": 0.5},
            }
            for c in cands
        ]


class FakeDecision:
    def __init__(self, decision_type="commit_next", target="next", conf=0.8):
        self.decision = {
            "decision_type": decision_type,
            "target": target,
            "confidence": conf,
            "reasoning": "ok",
        }

    async def make_decision(self, scored, context):
        return dict(self.decision)


@pytest.mark.asyncio
async def test_extract_question_variants():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    # direct string
    assert a._extract_question({"input": "q"}) == "q"
    # dict with nested input
    assert a._extract_question({"input": {"input": "q2"}}) == "q2"
    # non-string input coerced
    assert a._extract_question({"input": 123}) == "123"


@pytest.mark.asyncio
async def test_run_impl_error_without_orchestrator():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    res = await a._run_impl({"input": "test"})
    assert res["status"] == "error"
    assert res["decision"] == "fallback"


@pytest.mark.asyncio
async def test_run_impl_no_candidates_path():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    a.graph_api = FakeGraphAPI()
    a.introspector = FakeIntrospector([])
    ctx = {"input": "question", "orchestrator": OrchestratorStub(), "run_id": "r1"}
    out = await a._run_impl(ctx)
    assert out["status"] == "no_candidates"


@pytest.mark.asyncio
async def test_run_impl_budget_exceeded():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    a.graph_api = FakeGraphAPI()
    a.introspector = FakeIntrospector([{"node_id": "a"}])
    a.budget_controller = FakeBudget(keep=False)
    # other components unused due to early return but set for safety
    a.smart_evaluator = FakeEvaluator({})
    a.safety_controller = FakeSafety(True)
    a.scorer = FakeScorer()
    a.decision_engine = FakeDecision().__class__()
    ctx = {"input": "question", "orchestrator": OrchestratorStub(), "run_id": "r2"}
    out = await a._run_impl(ctx)
    assert out["status"] == "budget_exceeded"


@pytest.mark.asyncio
async def test_run_impl_safety_violation():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    a.graph_api = FakeGraphAPI()
    a.introspector = FakeIntrospector([{"node_id": "a"}])
    a.budget_controller = FakeBudget(keep=True)
    capture = {}
    a.smart_evaluator = FakeEvaluator(capture)
    a.safety_controller = FakeSafety(False)
    ctx = {"input": "question", "orchestrator": OrchestratorStub(), "run_id": "r3"}
    out = await a._run_impl(ctx)
    assert out["status"] == "safety_violation"
    # evaluator captured current agent id
    assert capture.get("current_agent_id") == "gs"


@pytest.mark.asyncio
async def test_run_impl_success_and_trace():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    a.graph_api = FakeGraphAPI()
    a.introspector = FakeIntrospector([{"node_id": "a"}, {"node_id": "b"}])
    a.budget_controller = FakeBudget(keep=True)
    capture = {}
    a.smart_evaluator = FakeEvaluator(capture)
    a.safety_controller = FakeSafety(True)
    a.scorer = FakeScorer(score=0.77)
    a.decision_engine = FakeDecision(decision_type="commit_next", target="a", conf=0.66)

    ctx = {"input": "choose", "previous_outputs": {"x": 1}, "orchestrator": OrchestratorStub(), "run_id": "r4", "step_index": 1}

    out = await a._run_impl(ctx)
    assert out["status"] == "success"
    assert out["decision"] == "commit_next"
    assert out["target"] == "a"
    assert isinstance(out.get("trace"), dict)
    # nested result should contain top_score
    assert "result" in out and isinstance(out["result"], dict)
    assert out["result"]["top_score"] >= 0


def test_build_trace_dict_structure():
    a = GraphScoutAgent("gs", prompt="", queue=[])
    trace = a._build_trace_dict(
        question="q",
        candidates=[{"node_id": "x"}],
        scored_candidates=[{"node_id": "x", "score": 0.5, "components": {}}],
        decision_result={"decision_type": "commit_next", "target": "x", "confidence": 0.5, "reasoning": "r"},
        context={"run_id": "r", "step_index": 2},
    )
    assert trace["decision"]["type"] == "commit_next"
    assert trace["scoring"]["scored_candidates"] == 1
