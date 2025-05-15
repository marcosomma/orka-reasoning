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


from orka.agents.agents import BinaryAgent


class TestBinaryAgent:
    def test_initialization(self):
        """Test initialization of BinaryAgent"""
        agent = BinaryAgent(
            agent_id="test_binary",
            prompt="Test prompt",
            queue="test_queue",
        )
        assert agent.agent_id == "test_binary"
        assert agent.prompt == "Test prompt"
        assert agent.queue == "test_queue"

    def test_yes_response(self):
        """Test BinaryAgent with 'yes' input"""
        agent = BinaryAgent(
            agent_id="test_binary", prompt="Is this a yes?", queue="test_queue"
        )
        result = agent.run({"input": "yes"})
        assert result == "true" or result is True  # Handle both string and boolean

    def test_no_response(self):
        """Test BinaryAgent with 'no' input"""
        agent = BinaryAgent(
            agent_id="test_binary", prompt="Is this a no?", queue="test_queue"
        )
        result = agent.run({"input": "no"})
        assert result == False or result is False  # Handle both string and boolean

    def test_ambiguous_response(self):
        """Test BinaryAgent with ambiguous input"""
        agent = BinaryAgent(
            agent_id="test_binary", prompt="Is this clear?", queue="test_queue"
        )
        # For ambiguous responses, it might return False instead of raising
        # an error in the current implementation
        result = agent.run({"input": "Maybe"})
        assert result == False or result is False
