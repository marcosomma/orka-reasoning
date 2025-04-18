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

# Load environment
load_dotenv()

class DummyAgent:
    def __init__(self, agent_id, prompt, queue, **kwargs):
        self.agent_id = agent_id
        self.prompt = prompt
        self.queue = queue
        self.type = self.__class__.__name__.lower()
    def run(self, input_data): return f"processed: {input_data}"

def test_orchestrator_flow(monkeypatch, tmp_path):
    from orka.orchestrator import Orchestrator
    file = tmp_path / "orka.yaml"
    file.write_text("""
orchestrator:
  id: test
  agents: [a1, a2]
agents:
  - id: a1
    type: openai-binary
    prompt: test
    queue: q1
  - id: a2
    type: openai-binary
    prompt: test
    queue: q2
""")
    from orka import orchestrator
    orchestrator.AGENT_TYPES["dummy"] = DummyAgent
    o = Orchestrator(str(file))
    result = o.run("msg")
    assert "a1" in result and "a2" in result
