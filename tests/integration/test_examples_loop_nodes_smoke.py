"""Smoke/integration tests for LoopNode configs in `examples/`.

We load real example YAML files, extract the LoopNode agent configs, and execute the
LoopNode in-process while stubbing the nested Orchestrator used by LoopNode's
internal_workflow execution.

This gives us high-signal coverage of the complex LoopNode behaviors (internal
workflow compilation, temp-YAML runner, log/result extraction, score extraction,
and output shaping) without requiring:
- live Redis
- real LLM calls
- network access
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pytest
import yaml

from orka.nodes.loop_node import LoopNode


pytestmark = [pytest.mark.integration, pytest.mark.no_auto_mock]


def _repo_root() -> Path:
    # tests/integration/ -> tests/ -> repo root
    return Path(__file__).resolve().parents[2]


def _candidate_examples() -> list[Path]:
    root = _repo_root()
    candidates = [
        root / "examples" / "simple_boolean_loop.yml",
        root / "examples" / "boolean_scoring_loop_example.yml",
        root / "examples" / "plan_validation_loop_boolean.yml",
        root / "examples" / "graph_scout_validated_loop.yml",
        root / "examples" / "cognitive_society_minimal_loop.yml",
    ]
    return [p for p in candidates if p.exists()]


def _iter_agents(config: dict[str, Any]) -> Iterable[dict[str, Any]]:
    agents = config.get("agents", [])
    if isinstance(agents, list):
        for a in agents:
            if isinstance(a, dict):
                yield a


def _loop_agents_from_example(example_path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(example_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    return [a for a in _iter_agents(data) if a.get("type") == "loop"]


@dataclass
class _FakeMemory:
    def close(self) -> None:
        return None


@dataclass
class _FakeForkManager:
    redis: Any = None


class _FakeOrchestrator:
    """Minimal stub that matches what LoopNode expects from Orchestrator."""

    def __init__(self, config_path: str):
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        self.orchestrator_cfg = cfg.get("orchestrator", {}) if isinstance(cfg, dict) else {}
        self.memory = _FakeMemory()
        self.fork_manager = _FakeForkManager()

        # LoopNode checks for this to avoid ad-hoc renderer initialization.
        self.render_template = lambda *args, **kwargs: ""  # noqa: E731

    async def run(self, workflow_input: dict[str, Any], return_logs: bool = True):
        # Produce logs shaped like the real engine: entries with agent_id and payload.result.
        agent_seq = self.orchestrator_cfg.get("agents", [])
        if isinstance(agent_seq, list) and agent_seq and isinstance(agent_seq[0], dict):
            agent_seq = [a.get("id") for a in agent_seq]

        logs: list[dict[str, Any]] = []
        for agent_id in agent_seq or []:
            if not agent_id:
                continue
            # Preserve a MetaReport-shaped entry to cover the LoopNode extraction path
            # that skips these entries.
            logs.append({"event_type": "MetaReport", "agent_id": agent_id, "payload": {"result": {}}})
            logs.append(
                {
                    "agent_id": agent_id,
                    "payload": {
                        "result": {
                            # Ensure LoopNode's default numeric extractors can always find a score.
                            "response": "score: 1.0",
                        }
                    },
                }
            )
        return logs


@pytest.mark.asyncio
@pytest.mark.parametrize("example_path", _candidate_examples(), ids=lambda p: p.name)
async def test_examples_loop_nodes_smoke(example_path: Path, monkeypatch):
    # Patch the Orchestrator symbol imported by LoopNode's internal_workflow runner.
    import orka.orchestrator as orchestrator_module

    monkeypatch.setattr(orchestrator_module, "Orchestrator", _FakeOrchestrator)

    loop_agents = _loop_agents_from_example(example_path)
    assert loop_agents, f"No loop agents found in example: {example_path}"

    # Execute each loop agent config in isolation.
    for agent_cfg in loop_agents:
        node_id = agent_cfg["id"]
        cfg = dict(agent_cfg)
        cfg.pop("id", None)
        cfg.pop("type", None)

        # Avoid Redis persistence in these smoke tests; we focus on execution and output shape.
        cfg["persist_across_runs"] = False

        node = LoopNode(node_id=node_id, **cfg)

        out = await node._run_impl({"input": "test", "previous_outputs": {}})

        assert isinstance(out, dict)
        assert out.get("loops_completed", 0) >= 1
        assert "final_score" in out
        assert 0.0 <= float(out["final_score"]) <= 1.0
        assert "threshold_met" in out
        assert "past_loops" in out and isinstance(out["past_loops"], list)


