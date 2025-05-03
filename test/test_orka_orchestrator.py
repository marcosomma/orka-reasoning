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
import os
import pytest
from dotenv import load_dotenv
from unittest.mock import patch
from fake_redis import FakeRedisClient

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

