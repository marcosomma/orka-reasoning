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

import asyncio

import pytest
from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_base_agent_fails():
    """Test that incomplete legacy agent implementations fail"""
    from orka.agents.base_agent import LegacyBaseAgent

    # Abstract run method is not implemented
    class Incomplete(LegacyBaseAgent):
        pass

    with pytest.raises(TypeError):
        Incomplete("id", "prompt", "queue")


def test_legacy_base_agent_implemented():
    """Test a complete legacy agent implementation"""
    from orka.agents.base_agent import LegacyBaseAgent

    class Complete(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed: {input_data}"

    # Create an event loop for this test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Should instantiate successfully
        agent = Complete("id", "prompt", "queue")

        # Should run successfully
        result = agent.run("test input")
        assert result == "Processed: test input"

        # Should have the correct string representation
        assert str(agent) == "<Complete id=id queue=queue>"
    finally:
        # Clean up the event loop
        loop.close()
