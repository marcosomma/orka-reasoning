# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for memory helper functions."""

import pytest

from orka.orchestrator.prompt_rendering.memory_helpers import create_memory_helpers
from orka.orchestrator.prompt_rendering.loop_helpers import create_loop_helpers


class TestMemoryHelpers:
    """Tests for memory helper functions."""

    @pytest.fixture
    def loop_helpers(self):
        """Create loop helpers for memory helpers."""
        return create_loop_helpers({
            "previous_outputs": {
                "past_loops": [
                    {"round": 1, "agent1": "decision1"},
                    {"round": 2, "agent1": "decision2"},
                ]
            }
        })

    def test_format_memory_query(self, loop_helpers):
        """Test format_memory_query."""
        helpers = create_memory_helpers({"input": "climate change"}, loop_helpers)
        result = helpers["format_memory_query"]("progressive")
        assert "Progressive perspective on: climate change" == result

    def test_format_memory_query_with_topic(self, loop_helpers):
        """Test format_memory_query with explicit topic."""
        helpers = create_memory_helpers({}, loop_helpers)
        result = helpers["format_memory_query"]("conservative", "AI ethics")
        assert "Conservative perspective on: AI ethics" == result

    def test_get_my_past_memory(self, loop_helpers):
        """Test get_my_past_memory."""
        helpers = create_memory_helpers({
            "memories": [
                {"metadata": {"agent_type": "type1"}, "content": "memory1"},
                {"metadata": {"agent_type": "type1"}, "content": "memory2"},
                {"metadata": {"agent_type": "type2"}, "content": "memory3"},
            ]
        }, loop_helpers)
        result = helpers["get_my_past_memory"]("type1")
        assert "memory1" in result
        assert "memory2" in result

    def test_get_my_past_memory_none(self, loop_helpers):
        """Test get_my_past_memory with no memories."""
        helpers = create_memory_helpers({}, loop_helpers)
        result = helpers["get_my_past_memory"]("type1")
        assert "No past memory" in result

    def test_get_my_past_memory_no_match(self, loop_helpers):
        """Test get_my_past_memory with no matching type."""
        helpers = create_memory_helpers({
            "memories": [{"metadata": {"agent_type": "other"}, "content": "test"}]
        }, loop_helpers)
        result = helpers["get_my_past_memory"]("type1")
        assert "No past memory for this agent type" in result

    def test_get_my_past_decisions(self, loop_helpers):
        """Test get_my_past_decisions."""
        helpers = create_memory_helpers({}, loop_helpers)
        result = helpers["get_my_past_decisions"]("agent1")
        assert "decision1" in result or "decision2" in result

    def test_get_my_past_decisions_none(self):
        """Test get_my_past_decisions with no loops."""
        loop_helpers = create_loop_helpers({})
        helpers = create_memory_helpers({}, loop_helpers)
        result = helpers["get_my_past_decisions"]("agent1")
        assert "No past decisions" in result

    def test_get_agent_memory_context(self, loop_helpers):
        """Test get_agent_memory_context."""
        helpers = create_memory_helpers({
            "memories": [
                {"metadata": {"agent_type": "type1"}, "content": "memory"},
            ]
        }, loop_helpers)
        result = helpers["get_agent_memory_context"]("type1", "agent1")
        assert "PAST MEMORY" in result or "PAST DECISIONS" in result

    def test_get_agent_memory_context_none(self):
        """Test get_agent_memory_context with no context."""
        loop_helpers = create_loop_helpers({})
        helpers = create_memory_helpers({}, loop_helpers)
        result = helpers["get_agent_memory_context"]("type1", "agent1")
        # When no memory exists but decisions check returns "No past decisions available"
        # the function still includes it in context
        assert "No past context" in result or "No past decisions" in result

    def test_get_debate_evolution(self, loop_helpers):
        """Test get_debate_evolution."""
        loop_helpers_with_scores = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [
                    {"agreement_score": 0.5},
                    {"agreement_score": 0.7},
                ]
            }
        })
        helpers = create_memory_helpers({}, loop_helpers_with_scores)
        result = helpers["get_debate_evolution"]()
        assert "Round 1" in result
        assert "Round 2" in result

    def test_get_debate_evolution_first_round(self):
        """Test get_debate_evolution on first round."""
        loop_helpers = create_loop_helpers({})
        helpers = create_memory_helpers({}, loop_helpers)
        result = helpers["get_debate_evolution"]()
        assert "First round" in result

