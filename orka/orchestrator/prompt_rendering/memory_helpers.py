# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory Helper Functions
=======================

Helper functions for accessing memory data in templates.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_memory_helpers(payload: Dict[str, Any], loop_helpers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create memory-related helper functions for Jinja2 templates.

    Args:
        payload: The current execution payload
        loop_helpers: Dictionary of loop helper functions (for get_past_loops)

    Returns:
        Dictionary of memory helper functions
    """
    # Get references to loop helpers we need
    get_past_loops = loop_helpers.get("get_past_loops", lambda: [])
    get_input = lambda: payload.get("input", "")

    def format_memory_query(perspective, topic=None):
        """Format a memory query for a specific perspective."""
        if topic is None:
            input_data = payload.get("input", "")
            if isinstance(input_data, dict):
                topic = input_data.get("input", str(input_data))
            else:
                topic = str(input_data)
        return f"{perspective.title()} perspective on: {topic}"

    def get_my_past_memory(agent_type):
        """Get past memory entries for a specific agent type."""
        memories = payload.get("memories", [])
        if not memories:
            return "No past memory available"

        my_memories = []
        for memory in memories:
            if isinstance(memory, dict):
                metadata = memory.get("metadata", {})
                if metadata.get("agent_type") == agent_type:
                    my_memories.append(memory.get("content", ""))

        if my_memories:
            return "\n".join(my_memories[-3:])
        return "No past memory for this agent type"

    def get_my_past_decisions(agent_name):
        """Get past loop decisions for a specific agent."""
        past_loops = get_past_loops()
        if not past_loops:
            return "No past decisions available"

        my_decisions = []
        for loop in past_loops:
            if agent_name in loop:
                my_decisions.append(f"Loop {loop.get('round', '?')}: {loop[agent_name]}")

        if my_decisions:
            return "\n".join(my_decisions[-2:])
        return f"No past decisions for {agent_name}"

    def get_agent_memory_context(agent_type, agent_name):
        """Get comprehensive context for an agent including memory and decisions."""
        memory = get_my_past_memory(agent_type)
        decisions = get_my_past_decisions(agent_name)

        context = []
        if memory != "No past memory available":
            context.append(f"PAST MEMORY:\n{memory}")
        if decisions != f"No past decisions for {agent_name}":
            context.append(f"PAST DECISIONS:\n{decisions}")

        return "\n\n".join(context) if context else "No past context available"

    def get_debate_evolution():
        """Get how the debate has evolved across loops."""
        past_loops = get_past_loops()
        if not past_loops:
            return "First round of debate"

        evolution = []
        for i, loop in enumerate(past_loops):
            score = loop.get("agreement_score", "Unknown")
            evolution.append(f"Round {i+1}: Agreement {score}")

        return " -> ".join(evolution)

    return {
        "format_memory_query": format_memory_query,
        "get_my_past_memory": get_my_past_memory,
        "get_my_past_decisions": get_my_past_decisions,
        "get_agent_memory_context": get_agent_memory_context,
        "get_debate_evolution": get_debate_evolution,
    }

