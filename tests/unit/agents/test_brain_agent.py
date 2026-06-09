# OrKa: Orchestrator Kit Agents — BrainAgent Tests

"""Tests for the BrainAgent (orchestrator-compatible Brain wrapper)."""

import json

import pytest
import pytest_asyncio

from orka.agents.brain_agent import BrainAgent


class FakeMemory:
    """In-memory fake for testing (no Redis needed)."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> bool:
        self._store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        return sum(1 for k in keys if self._store.pop(k, None) is not None)

    def hset(self, name: str, key: str, value: str) -> int:
        self._hashes.setdefault(name, {})[key] = value
        return 1

    def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    def hkeys(self, name: str) -> list[str]:
        return list(self._hashes.get(name, {}).keys())

    def hdel(self, name: str, *keys: str) -> int:
        h = self._hashes.get(name, {})
        return sum(1 for k in keys if h.pop(k, None) is not None)

    def sadd(self, name: str, *values: str) -> int:
        s = self._sets.setdefault(name, set())
        before = len(s)
        s.update(values)
        return len(s) - before

    def srem(self, name: str, *values: str) -> int:
        s = self._sets.get(name, set())
        return sum(1 for v in values if v in s and not s.discard(v) and True)

    def smembers(self, name: str) -> list[str]:
        return list(self._sets.get(name, set()))

    def zadd(self, name: str, mapping: dict[str, float]) -> int:
        if name not in self._sorted_sets:
            self._sorted_sets[name] = {}
        count = 0
        for member, score in mapping.items():
            if member not in self._sorted_sets[name]:
                count += 1
            self._sorted_sets[name][member] = score
        return count

    def zrem(self, name: str, *members: str) -> int:
        zs = self._sorted_sets.get(name, {})
        return sum(1 for m in members if zs.pop(m, None) is not None)

    def zcard(self, name: str) -> int:
        return len(self._sorted_sets.get(name, {}))

    def zrevrange(self, name: str, start: int, stop: int) -> list[str]:
        zs = self._sorted_sets.get(name, {})
        sorted_members = sorted(zs.keys(), key=lambda m: zs[m], reverse=True)
        end = len(sorted_members) + stop + 1 if stop < 0 else stop + 1
        return sorted_members[start:end]

    def zrange(self, name: str, start: int, stop: int) -> list[str]:
        zs = self._sorted_sets.get(name, {})
        sorted_members = sorted(zs.keys(), key=lambda m: zs[m])
        end = len(sorted_members) + stop + 1 if stop < 0 else stop + 1
        return sorted_members[start:end]

    def log(self, agent_id, event_type, payload, **kwargs):
        pass


@pytest.fixture
def memory():
    return FakeMemory()


def _make_learn_payload() -> dict:
    """Build a realistic LLM output that the brain_learn agent would receive."""
    return {
        "domain": "medical_diagnosis",
        "task": "Diagnose a patient with recurring headaches and fatigue",
        "response": "Systematic diagnostic analysis of patient symptoms",
        "steps": [
            {"action": "gather and categorize all symptoms", "result": "success"},
            {"action": "form differential diagnosis list", "result": "success"},
            {"action": "rank diagnoses by likelihood", "result": "success"},
            {"action": "propose prioritized diagnostic tests", "result": "success"},
        ],
        "confidence": "0.85",
        "internal_reasoning": "Used systematic decomposition to analyze symptoms",
    }


def _make_recall_payload() -> dict:
    """Build a context for a different domain (software debugging)."""
    return {
        "domain": "software_debugging",
        "task": "Debug intermittent failures in a microservice system",
        "response": "Need to analyze system components and find root cause",
        "confidence": "0.7",
        "internal_reasoning": "The system needs systematic investigation",
    }


# ═══════════════════════════════════════════════════════════════════════
# Learn operation tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_learn_returns_skill(memory):
    agent = BrainAgent(agent_id="test_learn", operation="learn", memory_logger=memory)
    ctx = {
        "formatted_prompt": json.dumps(_make_learn_payload()),
        "input": "test",
    }
    result = await agent._run_impl(ctx)

    assert "skill_id" in result
    assert "skill_name" in result
    assert result["skill_name"]
    assert isinstance(result["skill_steps"], list)
    assert len(result["skill_steps"]) > 0


@pytest.mark.asyncio(loop_scope="function")
async def test_learn_with_dict_payload(memory):
    agent = BrainAgent(agent_id="test_learn_dict", operation="learn", memory_logger=memory)
    ctx = {
        "formatted_prompt": _make_learn_payload(),  # dict, not JSON string
        "input": "test",
    }
    result = await agent._run_impl(ctx)

    assert "skill_id" in result
    assert result["skill_name"]


@pytest.mark.asyncio(loop_scope="function")
async def test_learn_minimal_payload(memory):
    """Even a minimal payload should produce *something* (the Brain is forgiving)."""
    agent = BrainAgent(agent_id="test_minimal", operation="learn", memory_logger=memory)
    ctx = {"input": "test", "formatted_prompt": json.dumps({"response": "simple idea"})}
    result = await agent._run_impl(ctx)

    # The Brain always tries to learn something;
    # with a trivial payload it still extracts a skill from the response text.
    assert "skill_id" in result or result["confidence"] == "0.0"


# ═══════════════════════════════════════════════════════════════════════
# Recall operation tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_recall_no_skills_yet(memory):
    agent = BrainAgent(agent_id="test_recall", operation="recall", memory_logger=memory)
    ctx = {
        "formatted_prompt": json.dumps(_make_recall_payload()),
        "input": "test",
    }
    result = await agent._run_impl(ctx)

    assert "No applicable skills" in result["response"]
    assert result["confidence"] == "0.0"


@pytest.mark.asyncio(loop_scope="function")
async def test_recall_finds_learned_skill(memory):
    """Learn a skill, then recall it from a related domain context."""
    agent = BrainAgent(agent_id="brain", operation="learn", memory_logger=memory)

    # Step 1: Learn — use task descriptions the ContextAnalyzer can extract patterns from
    learn_payload = {
        "domain": "data_analysis",
        "task": "Analyze and decompose the dataset, validate each section and aggregate results",
        "response": "Systematic analysis with decomposition and aggregation",
        "steps": [
            {"action": "decompose input into sections", "result": "success"},
            {"action": "analyze each section independently", "result": "success"},
            {"action": "validate section results", "result": "success"},
            {"action": "aggregate validated results", "result": "success"},
        ],
        "confidence": "0.85",
    }
    learn_ctx = {
        "formatted_prompt": json.dumps(learn_payload),
        "input": "test",
    }
    learn_result = await agent._run_impl(learn_ctx)
    assert "skill_id" in learn_result

    # Step 2: Recall from different domain but with similar cognitive patterns
    agent.operation = "recall"
    recall_payload = {
        "domain": "code_review",
        "task": "Analyze and decompose the PR into files, validate each change and aggregate findings",
        "response": "Need to break down and analyze code changes",
        "confidence": "0.7",
        "min_score": "0.0",
    }
    recall_ctx = {
        "formatted_prompt": json.dumps(recall_payload),
        "input": "test",
    }
    recall_result = await agent._run_impl(recall_ctx)

    assert "skill_id" in recall_result
    assert recall_result["skill_name"]
    assert float(recall_result["confidence"]) > 0
    assert isinstance(recall_result["all_candidates"], list)
    assert len(recall_result["all_candidates"]) >= 1


# ═══════════════════════════════════════════════════════════════════════
# Full learn → recall lifecycle
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_learn_recall_lifecycle(memory):
    """Full lifecycle: learn in medical, recall for software debugging."""
    brain_agent = BrainAgent(agent_id="brain", operation="learn", memory_logger=memory)

    # Learn medical diagnosis pattern
    learn_ctx = {
        "formatted_prompt": json.dumps(_make_learn_payload()),
        "input": "diagnose patient",
    }
    learn_result = await brain_agent._run_impl(learn_ctx)
    skill_name = learn_result["skill_name"]
    skill_steps = learn_result["skill_steps"]

    assert skill_name
    assert len(skill_steps) >= 3

    # Switch to recall mode and query from software domain (explicit min_score=0.0)
    brain_agent.operation = "recall"
    recall_payload = _make_recall_payload()
    recall_payload["min_score"] = "0.0"
    recall_ctx = {
        "formatted_prompt": json.dumps(recall_payload),
        "input": "debug system",
    }
    recall_result = await brain_agent._run_impl(recall_ctx)

    assert recall_result["skill_name"] == skill_name
    assert isinstance(recall_result["adaptations"], dict)


# ═══════════════════════════════════════════════════════════════════════
# Operation dispatch
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_operation_from_context_overrides_default(memory):
    """Operation in ctx should override the constructor default."""
    agent = BrainAgent(agent_id="test_op", operation="learn", memory_logger=memory)

    # First learn a skill
    learn_ctx = {
        "formatted_prompt": json.dumps(_make_learn_payload()),
        "input": "test",
    }
    await agent._run_impl(learn_ctx)

    # Now use recall via context override
    recall_ctx = {
        "operation": "recall",
        "formatted_prompt": json.dumps(_make_recall_payload()),
        "input": "test",
    }
    result = await agent._run_impl(recall_ctx)

    # Should have attempted recall (not learn)
    assert "candidates" in result.get("response", "").lower() or "skill" in result.get("response", "").lower()


# ═══════════════════════════════════════════════════════════════════════
# Feedback operation tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_feedback_records_transfer(memory):
    """Learn → recall → feedback should increment transfer_history."""
    agent = BrainAgent(agent_id="brain", operation="learn", memory_logger=memory)

    # Step 1: Learn
    learn_ctx = {
        "formatted_prompt": json.dumps(_make_learn_payload()),
        "input": "test",
    }
    learn_result = await agent._run_impl(learn_ctx)
    skill_id = learn_result["skill_id"]

    # Step 2: Recall (explicit min_score=0.0 for lifecycle test)
    agent.operation = "recall"
    recall_payload = _make_recall_payload()
    recall_payload["min_score"] = "0.0"
    recall_ctx = {
        "formatted_prompt": json.dumps(recall_payload),
        "input": "test",
    }
    recall_result = await agent._run_impl(recall_ctx)
    assert recall_result["skill_id"] == skill_id

    # Step 3: Feedback
    agent.operation = "feedback"
    feedback_ctx = {
        "formatted_prompt": json.dumps(recall_result),
        "input": "test",
    }
    fb_result = await agent._run_impl(feedback_ctx)

    assert fb_result["skill_id"] == skill_id
    assert fb_result["transfer_count"] == 1
    assert fb_result["transfer_success"] is True
    assert "successful" in fb_result["response"].lower()


@pytest.mark.asyncio(loop_scope="function")
async def test_feedback_without_skill_id(memory):
    """Feedback with no skill_id returns an error response."""
    agent = BrainAgent(agent_id="brain", operation="feedback", memory_logger=memory)
    ctx = {
        "formatted_prompt": json.dumps({"domain": "test"}),
        "input": "test",
    }
    result = await agent._run_impl(ctx)
    assert result["confidence"] == "0.0"
    assert "skill_id" in result["response"].lower()


@pytest.mark.asyncio(loop_scope="function")
async def test_feedback_failed_transfer(memory):
    """Feedback with success=False records a failed transfer."""
    agent = BrainAgent(agent_id="brain", operation="learn", memory_logger=memory)

    # Learn
    learn_ctx = {
        "formatted_prompt": json.dumps(_make_learn_payload()),
        "input": "test",
    }
    learn_result = await agent._run_impl(learn_ctx)
    skill_id = learn_result["skill_id"]

    # Feedback with failure
    agent.operation = "feedback"
    feedback_ctx = {
        "formatted_prompt": json.dumps({"skill_id": skill_id, "success": False, "domain": "test"}),
        "input": "test",
    }
    fb_result = await agent._run_impl(feedback_ctx)

    assert fb_result["transfer_count"] == 1
    assert fb_result["transfer_success"] is False
    assert "failed" in fb_result["response"].lower()


@pytest.mark.asyncio(loop_scope="function")
async def test_full_learn_recall_feedback_lifecycle(memory):
    """Complete lifecycle: learn → recall → feedback → verify transfer count."""
    agent = BrainAgent(agent_id="brain", operation="learn", memory_logger=memory)

    # Learn
    learn_ctx = {
        "formatted_prompt": json.dumps(_make_learn_payload()),
        "input": "medical diagnosis",
    }
    learn_result = await agent._run_impl(learn_ctx)
    skill_id = learn_result["skill_id"]

    # Recall (explicit min_score=0.0 for lifecycle test)
    agent.operation = "recall"
    recall_payload = _make_recall_payload()
    recall_payload["min_score"] = "0.0"
    recall_ctx = {
        "formatted_prompt": json.dumps(recall_payload),
        "input": "software debugging",
    }
    recall_result = await agent._run_impl(recall_ctx)
    assert recall_result["skill_id"] == skill_id

    # Feedback (using recall output directly, like the workflow does)
    agent.operation = "feedback"
    feedback_ctx = {
        "formatted_prompt": json.dumps(recall_result),
        "input": "record transfer",
    }
    fb_result = await agent._run_impl(feedback_ctx)
    assert fb_result["transfer_count"] == 1

    # Second recall + feedback cycle (reuse same recall_ctx with min_score=0.0)
    agent.operation = "recall"
    recall_result2 = await agent._run_impl(recall_ctx)

    agent.operation = "feedback"
    feedback_ctx2 = {
        "formatted_prompt": json.dumps(recall_result2),
        "input": "record transfer 2",
    }
    fb_result2 = await agent._run_impl(feedback_ctx2)
    assert fb_result2["transfer_count"] == 2


# ═══════════════════════════════════════════════════════════════════════
# Error handling
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_no_memory_raises():
    """BrainAgent without memory_logger should raise RuntimeError."""
    agent = BrainAgent(agent_id="no_mem", operation="learn", memory_logger=None)
    with pytest.raises(RuntimeError, match="requires a memory_logger"):
        await agent._run_impl({"input": "test"})


@pytest.mark.asyncio(loop_scope="function")
async def test_parse_json_field_handles_bad_input():
    """Static helper should handle garbage gracefully."""
    assert BrainAgent._parse_json_field(None) == {}
    assert BrainAgent._parse_json_field(42) == {}
    assert BrainAgent._parse_json_field("not json") == {}
    assert BrainAgent._parse_json_field('{"key": "val"}') == {"key": "val"}
    assert BrainAgent._parse_json_field({"key": "val"}) == {"key": "val"}


# ═══════════════════════════════════════════════════════════════════════
# _abstract_procedure tests
# ═══════════════════════════════════════════════════════════════════════


class TestAbstractProcedure:
    def _make_agent(self, memory):
        return BrainAgent(agent_id="test_abs", operation="learn", memory_logger=memory)

    def test_extracts_leading_verb(self, memory):
        agent = self._make_agent(memory)
        text = "Analyze the system logs for anomalies and report findings."
        steps = agent._abstract_procedure(text)
        assert len(steps) >= 1
        assert steps[0]["action"].startswith("analyze ")

    def test_extracts_embedded_verb(self, memory):
        """Verbs appearing inside a sentence are detected."""
        agent = self._make_agent(memory)
        text = "The system should validate the incoming data carefully."
        steps = agent._abstract_procedure(text)
        assert len(steps) >= 1
        assert any("validate" in s["action"] for s in steps)

    def test_max_eight_steps(self, memory):
        """No more than 8 steps should be returned."""
        agent = self._make_agent(memory)
        sentences = [f"Analyze part {i} of the input data for correctness." for i in range(20)]
        text = ". ".join(sentences)
        steps = agent._abstract_procedure(text)
        assert len(steps) <= 8

    def test_no_actionable_text_returns_empty(self, memory):
        """Text without action verbs returns empty list."""
        agent = self._make_agent(memory)
        text = "This is just a long sentence about nothing particularly special or interesting really."
        steps = agent._abstract_procedure(text)
        assert steps == []

    def test_short_sentences_skipped(self, memory):
        """Sentences shorter than 20 chars are ignored."""
        agent = self._make_agent(memory)
        text = "Analyze it. Done."
        steps = agent._abstract_procedure(text)
        assert steps == []

    def test_steps_have_required_keys(self, memory):
        agent = self._make_agent(memory)
        text = "Validate the entire configuration for compliance with the standards."
        steps = agent._abstract_procedure(text)
        assert len(steps) >= 1
        for step in steps:
            assert "action" in step
            assert "result" in step
            assert "description" in step


# ═══════════════════════════════════════════════════════════════════════
# min_score default validation
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_recall_default_min_score_filters_low_matches(memory):
    """The default min_score=0.5 should filter out very weak matches."""
    agent = BrainAgent(agent_id="brain", operation="learn", memory_logger=memory)

    # Learn a very specific skill
    learn_ctx = {
        "formatted_prompt": json.dumps(
            {
                "domain": "cooking",
                "task": "Prepare a three-course dinner with appetizer, main, dessert",
                "response": "Analyze ingredients and prepare each course systematically",
                "steps": [
                    {"action": "gather ingredients", "result": "success"},
                    {"action": "prepare appetizer", "result": "success"},
                    {"action": "cook main course", "result": "success"},
                ],
                "confidence": "0.8",
            }
        ),
        "input": "cook dinner",
    }
    await agent._run_impl(learn_ctx)

    # Recall from completely unrelated domain — default min_score=0.5
    # should filter this out (no explicit min_score in payload)
    agent.operation = "recall"
    recall_ctx = {
        "formatted_prompt": json.dumps(
            {
                "domain": "quantum_physics",
                "task": "Solve the Schrödinger equation for a hydrogen atom",
            }
        ),
        "input": "physics",
    }
    result = await agent._run_impl(recall_ctx)

    # With default min_score=0.5, unrelated domains should be filtered
    assert result["confidence"] == "0.0" or float(result.get("combined_score", 0.0)) >= 0.5


# ═══════════════════════════════════════════════════════════════════════
# Episode operations: record_episode
# ═══════════════════════════════════════════════════════════════════════


def _make_record_episode_payload() -> dict:
    """Build a payload for the record_episode operation."""
    return {
        "task_input": "Analyze customer churn data and build prediction model",
        "domain": "data_science",
        "task": "churn_prediction",
        "model": "gpt-4",
        "success": True,
        "quality": 0.85,
        "outcome_summary": "Built churn model with 85% accuracy",
        "what_worked": ["Feature engineering", "XGBoost model"],
        "what_failed": [],
        "lessons": ["Use SMOTE for imbalanced data", "Validate with time-based splits"],
        "agents": ["data_prep", "model_trainer", "evaluator"],
        "strategy": "sequential",
        "tokens_used": 3000,
        "latency_ms": 1500,
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_record_episode_returns_episode_id(memory):
    agent = BrainAgent(agent_id="test_ep", operation="record_episode", memory_logger=memory)
    ctx = {
        "formatted_prompt": json.dumps(_make_record_episode_payload()),
        "input": "test",
    }
    result = await agent._run_impl(ctx)

    assert "episode_id" in result
    assert result["episode_domain"] == "data_science"
    assert result["episode_success"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_record_episode_failure(memory):
    agent = BrainAgent(agent_id="test_ep_fail", operation="record_episode", memory_logger=memory)
    payload = _make_record_episode_payload()
    payload["success"] = False
    payload["quality"] = 0.2
    payload["outcome_summary"] = "Model training diverged"
    payload["what_failed"] = ["Gradient explosion"]
    payload["failure_analysis"] = "Learning rate too high"
    payload["lessons"] = ["Use learning rate warmup"]

    ctx = {
        "formatted_prompt": json.dumps(payload),
        "input": "test",
    }
    result = await agent._run_impl(ctx)

    assert result["episode_success"] is False
    assert "episode_id" in result


@pytest.mark.asyncio(loop_scope="function")
async def test_record_episode_minimal_payload(memory):
    agent = BrainAgent(agent_id="test_ep_min", operation="record_episode", memory_logger=memory)
    ctx = {
        "formatted_prompt": json.dumps({"response": "Did something"}),
        "input": "test",
    }
    result = await agent._run_impl(ctx)
    assert "episode_id" in result


@pytest.mark.asyncio(loop_scope="function")
async def test_record_episode_coerces_string_lists(memory):
    agent = BrainAgent(agent_id="test_ep_str", operation="record_episode", memory_logger=memory)
    payload = _make_record_episode_payload()
    payload["lessons"] = "lesson A, lesson B, lesson C"
    payload["what_worked"] = "thing 1, thing 2"

    ctx = {
        "formatted_prompt": json.dumps(payload),
        "input": "test",
    }
    result = await agent._run_impl(ctx)
    assert "episode_id" in result


# ═══════════════════════════════════════════════════════════════════════
# Episode operations: recall_episodes
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_recall_episodes_empty(memory):
    agent = BrainAgent(agent_id="test_recall_ep", operation="recall_episodes", memory_logger=memory)
    ctx = {
        "formatted_prompt": json.dumps(
            {
                "task_input": "Find similar tasks",
                "domain": "test",
            }
        ),
        "input": "test",
    }
    result = await agent._run_impl(ctx)
    assert result["episode_count"] == 0
    assert "No relevant" in result["response"]


@pytest.mark.asyncio(loop_scope="function")
async def test_record_then_recall_episodes(memory):
    """Record an episode, then recall it from a similar context."""
    agent = BrainAgent(agent_id="brain", operation="record_episode", memory_logger=memory)

    # Record
    record_ctx = {
        "formatted_prompt": json.dumps(_make_record_episode_payload()),
        "input": "test",
    }
    record_result = await agent._run_impl(record_ctx)
    assert "episode_id" in record_result

    # Recall
    agent.operation = "recall_episodes"
    recall_ctx = {
        "formatted_prompt": json.dumps(
            {
                "task_input": "Build a prediction model for customer churn",
                "domain": "data_science",
                "min_score": "0.0",
            }
        ),
        "input": "test",
    }
    recall_result = await agent._run_impl(recall_ctx)

    assert recall_result["episode_count"] >= 1
    assert "RELEVANT PAST EXPERIENCE" in recall_result["response"]
    assert isinstance(recall_result["episodes"], list)


@pytest.mark.asyncio(loop_scope="function")
async def test_recall_episodes_with_domain_filter(memory):
    """Recall with domain_filter restricts results."""
    agent = BrainAgent(agent_id="brain", operation="record_episode", memory_logger=memory)

    # Record in two different domains
    payload_ds = _make_record_episode_payload()
    payload_ds["domain"] = "data_science"
    await agent._run_impl(
        {
            "formatted_prompt": json.dumps(payload_ds),
            "input": "test",
        }
    )

    payload_eng = _make_record_episode_payload()
    payload_eng["domain"] = "engineering"
    payload_eng["task_input"] = "Build REST API"
    await agent._run_impl(
        {
            "formatted_prompt": json.dumps(payload_eng),
            "input": "test",
        }
    )

    # Recall only engineering
    agent.operation = "recall_episodes"
    recall_ctx = {
        "formatted_prompt": json.dumps(
            {
                "task_input": "Build API",
                "domain_filter": "engineering",
                "min_score": "0.0",
            }
        ),
        "input": "test",
    }
    result = await agent._run_impl(recall_ctx)
    assert result["episode_count"] >= 1


@pytest.mark.asyncio(loop_scope="function")
async def test_dispatch_routes_to_record_episode(memory):
    """Operation dispatch routes 'record_episode' correctly."""
    agent = BrainAgent(agent_id="test", operation="learn", memory_logger=memory)
    ctx = {
        "operation": "record_episode",
        "formatted_prompt": json.dumps(_make_record_episode_payload()),
        "input": "test",
    }
    result = await agent._run_impl(ctx)
    assert "episode_id" in result


@pytest.mark.asyncio(loop_scope="function")
async def test_dispatch_routes_to_recall_episodes(memory):
    """Operation dispatch routes 'recall_episodes' correctly."""
    agent = BrainAgent(agent_id="test", operation="learn", memory_logger=memory)
    ctx = {
        "operation": "recall_episodes",
        "formatted_prompt": json.dumps({"task_input": "something", "domain": "test"}),
        "input": "test",
    }
    result = await agent._run_impl(ctx)
    assert "episode_count" in result
