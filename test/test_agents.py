# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
from orka.agents.agents import BinaryAgent, ClassificationAgent
from orka.agents.llm_agents import (
    OpenAIAnswerBuilder,
    OpenAIBinaryAgent,
    OpenAIClassificationAgent,
)
from orka.tools.search_tools import DuckDuckGoTool


def test_binary_agent_run():
    agent = BinaryAgent(agent_id="test_bin", prompt="Is this true?", queue="test")
    output = agent.run({"input": "Cats are mammals."})
    assert output in [True, False]


def test_classification_agent_run():
    agent = ClassificationAgent(
        agent_id="test_class",
        prompt="Classify:",
        queue="test",
        options=["cat", "dog"],
    )
    output = agent.run({"input": "A domestic animal"})
    assert output == "deprecated"


def test_openai_binary_agent_run():
    agent = OpenAIBinaryAgent(
        agent_id="test_openai_bin",
        prompt="Is this real?",
        queue="test",
    )
    output = agent.run({"input": "Is water wet?"})
    assert output in [True, False]


def test_openai_classification_agent_run():
    agent = OpenAIClassificationAgent(
        agent_id="test_openai_class",
        prompt="Classify:",
        queue="test",
        options=["cat", "dog"],
    )
    output = agent.run({"input": "Barking"})
    assert output in ["cat", "dog", "not-classified"]


def test_openai_classification_agent_run_not_classified():
    agent = OpenAIClassificationAgent(
        agent_id="test_openai_class",
        prompt="Classify:",
        queue="test",
        options=[],
    )
    output = agent.run({"input": "Sky is blue"})
    assert output == "not-classified"


def test_openai_answer_builder_run():
    agent = OpenAIAnswerBuilder(
        agent_id="test_builder",
        prompt="Answer this:",
        queue="test",
    )
    output = agent.run({"input": "What is AI?"})
    # OpenAIAnswerBuilder now returns structured response with metrics
    assert isinstance(output, dict)
    assert "response" in output
    assert "_metrics" in output
    assert len(output["response"]) > 5


def test_duckduckgo_tool_run():
    tool = DuckDuckGoTool(tool_id="test_duck", prompt="Search:", queue="test")
    output = tool.run({"input": "OrKa project"})
    assert isinstance(output, list)
    assert len(output) > 0
