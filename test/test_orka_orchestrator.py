# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka
from unittest.mock import MagicMock, patch

import pytest
import yaml
from dotenv import load_dotenv
from fake_redis import FakeRedisClient

from orka.orchestrator import Orchestrator

load_dotenv()


class DummyAgent:
    def __init__(self, agent_id, prompt, queue, **kwargs):
        self.agent_id = agent_id
        self.prompt = prompt
        self.queue = queue
        self.type = self.__class__.__name__.lower()

    def run(self, input_data):
        return {self.agent_id: f"processed: {input_data}"}


@pytest.mark.asyncio
async def test_orchestrator_flow(monkeypatch, tmp_path):
    from orka import orchestrator
    from orka.orchestrator import Orchestrator

    file = tmp_path / "orka.yaml"
    file.write_text("""
orchestrator:
  id: test
  agents:
   - a1
   - a2
agents:
  - id: a1
    type: dummy
    prompt: test
    queue: q1
  - id: a2
    type: dummy
    prompt: test
    queue: q2
""")

    fake_redis = FakeRedisClient()

    with patch("orka.memory_logger.redis.from_url", return_value=fake_redis):
        orchestrator.AGENT_TYPES["dummy"] = DummyAgent
        o = Orchestrator(str(file))
        result = await o.run("msg")

    assert isinstance(result, list), f"Expected result to be list, got {type(result)}"
    agent_ids = {entry["agent_id"] for entry in result if "agent_id" in entry}
    assert "a1" in agent_ids, f"'a1' not found in executed agent IDs: {agent_ids}"
    assert "a2" in agent_ids, f"'a2' not found in executed agent IDs: {agent_ids}"


@pytest.fixture
def parallel_config(tmp_path):
    config = {
        "orchestrator": {
            "id": "parallel_test",
            "strategy": "parallel",
            "queue": "orka:test",
            "agents": ["initial_check", "fork_parallel", "join_parallel", "final_step"],
        },
        "agents": [
            {
                "id": "initial_check",
                "type": "openai-binary",
                "prompt": "Is this a test?",
                "queue": "orka:test",
            },
            {
                "id": "fork_parallel",
                "type": "fork",
                "targets": [
                    ["generate_before", "search_before"],
                    ["generate_after", "search_after"],
                ],
            },
            {
                "id": "generate_before",
                "type": "openai-answer",
                "prompt": "Generate query for before: {{ input }}",
                "queue": "orka:before",
            },
            {
                "id": "search_before",
                "type": "duckduckgo",
                "prompt": "{{ previous_outputs.generate_before }}",
                "queue": "orka:before_search",
            },
            {
                "id": "generate_after",
                "type": "openai-answer",
                "prompt": "Generate query for after: {{ input }}",
                "queue": "orka:after",
            },
            {
                "id": "search_after",
                "type": "duckduckgo",
                "prompt": "{{ previous_outputs.generate_after }}",
                "queue": "orka:after_search",
            },
            {"id": "join_parallel", "type": "join", "group": "fork_parallel"},
            {
                "id": "final_step",
                "type": "openai-answer",
                "prompt": "Final synthesis: {{ input }}",
                "queue": "orka:final",
            },
        ],
    }

    config_file = tmp_path / "parallel_config.yml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return str(config_file)


@pytest.mark.asyncio
async def test_parallel_execution(parallel_config):
    # Create a mock Redis client that can handle JSON serialization
    mock_redis = MagicMock()
    mock_redis.hset = MagicMock()
    mock_redis.get = MagicMock(return_value=None)
    mock_redis.set = MagicMock()

    with patch("orka.memory_logger.redis.from_url", return_value=mock_redis):
        orchestrator = Orchestrator(parallel_config)

        # Mock the agent responses
        async def mock_run(*args, **kwargs):
            return {"result": "test result"}

        for agent_id in [
            "generate_before",
            "search_before",
            "generate_after",
            "search_after",
        ]:
            orchestrator.agents[agent_id].run = mock_run

        result = await orchestrator.run("Test input")
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_parallel_execution_with_empty_branches(parallel_config):
    with patch("orka.memory_logger.redis.from_url", return_value=MagicMock()):
        orchestrator = Orchestrator(parallel_config)

        # Set empty targets
        orchestrator.agents["fork_parallel"].config["targets"] = []

        # Mock the memory logger to avoid JSON serialization issues
        mock_memory_logger = MagicMock()
        mock_memory_logger.log = MagicMock()
        orchestrator.memory = mock_memory_logger

        with pytest.raises(ValueError, match="requires non-empty 'targets'"):
            await orchestrator.run("Test input")


@pytest.mark.asyncio
async def test_parallel_execution_with_invalid_branch(parallel_config):
    with patch("orka.memory_logger.redis.from_url", return_value=MagicMock()):
        orchestrator = Orchestrator(parallel_config)

        # Set invalid target
        orchestrator.agents["fork_parallel"].targets = ["nonexistent_agent"]

        with pytest.raises(KeyError):
            await orchestrator.run("Test input")
