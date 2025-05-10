# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import pytest
from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_base_agent_fails():
    """Test that incomplete legacy agent implementations fail"""
    from orka.agents.agent_base import BaseAgent

    # Abstract run method is not implemented
    class Incomplete(BaseAgent):
        pass

    with pytest.raises(TypeError):
        Incomplete("id", "prompt", "queue")


def test_legacy_base_agent_implemented():
    """Test a complete legacy agent implementation"""
    from orka.agents.agent_base import BaseAgent

    class Complete(BaseAgent):
        def run(self, input_data):
            return f"Processed: {input_data}"

    # Should instantiate successfully
    agent = Complete("id", "prompt", "queue")

    # Should run successfully
    result = agent.run("test input")
    assert result == "Processed: test input"

    # Should have the correct string representation
    assert str(agent) == "<Complete id=id queue=queue>"
