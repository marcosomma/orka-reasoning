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
from orka.agents.agents import BinaryAgent, ClassificationAgent
from orka.agents.llm_agents import OpenAIBinaryAgent, OpenAIClassificationAgent, OpenAIAnswerBuilder
from orka.agents.google_duck_agents import DuckDuckGoAgent

def test_binary_agent_run():
    agent = BinaryAgent(agent_id="test_bin", prompt="Is this true?", queue="test")
    output = agent.run({"input": "Cats are mammals."})
    assert isinstance(output, bool)

def test_classification_agent_run():
    agent = ClassificationAgent(agent_id="test_class", prompt="Classify:", queue="test", options=["cat", "dog"])
    output = agent.run({"input": "A domestic animal"})
    assert output in ["cat", "dog"]

def test_openai_binary_agent_run():
    agent = OpenAIBinaryAgent(agent_id="test_openai_bin", prompt="Is this real?", queue="test")
    output = agent.run({"input": "Is water wet?"})
    assert isinstance(output, bool)

def test_openai_classification_agent_run():
    agent = OpenAIClassificationAgent(agent_id="test_openai_class", prompt="Classify:", queue="test", options=["yes", "no"])
    output = agent.run({"input": "Sky is blue"})
    assert output in ["yes", "no"]

def test_openai_answer_builder_run():
    agent = OpenAIAnswerBuilder(agent_id="test_builder", prompt="Answer this:", queue="test")
    output = agent.run({"input": "What is AI?"})
    assert isinstance(output, str)
    assert len(output) > 5

def test_duckduckgo_agent_run():
    agent = DuckDuckGoAgent(agent_id="test_duck", prompt="Search:", queue="test")
    output = agent.run({"input": "OrKa project"})
    assert isinstance(output, list)
    assert len(output) > 0
