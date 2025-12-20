# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for agent helper functions."""

import pytest

from orka.orchestrator.prompt_rendering.agent_helpers import create_agent_helpers


class TestAgentHelpers:
    """Tests for agent helper functions."""

    def test_get_agent_response_result(self):
        """Test get_agent_response with result field."""
        helpers = create_agent_helpers({
            "previous_outputs": {"agent1": {"result": "test result"}}
        })
        assert helpers["get_agent_response"]("agent1") == "test result"

    def test_get_agent_response_response(self):
        """Test get_agent_response with response field."""
        helpers = create_agent_helpers({
            "previous_outputs": {"agent1": {"response": "test response"}}
        })
        assert helpers["get_agent_response"]("agent1") == "test response"

    def test_get_agent_response_missing(self):
        """Test get_agent_response with missing agent."""
        helpers = create_agent_helpers({})
        result = helpers["get_agent_response"]("missing")
        assert "No response found" in result

    def test_safe_get_response_success(self):
        """Test safe_get_response with valid response."""
        helpers = create_agent_helpers({
            "previous_outputs": {"agent1": {"result": "test"}}
        })
        assert helpers["safe_get_response"]("agent1") == "test"

    def test_safe_get_response_fallback(self):
        """Test safe_get_response with fallback."""
        helpers = create_agent_helpers({})
        result = helpers["safe_get_response"]("missing", "fallback value")
        assert result == "fallback value"

    def test_safe_get_response_with_prev_outputs(self):
        """Test safe_get_response with explicit prev_outputs."""
        helpers = create_agent_helpers({})
        prev_outputs = {"agent1": {"result": "explicit"}}
        result = helpers["safe_get_response"]("agent1", "fallback", prev_outputs)
        assert result == "explicit"

    def test_get_progressive_response(self):
        """Test get_progressive_response."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "progressive_refinement": {"result": "progressive result"}
            }
        })
        assert helpers["get_progressive_response"]() == "progressive result"

    def test_get_conservative_response(self):
        """Test get_conservative_response."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "conservative_refinement": {"result": "conservative result"}
            }
        })
        assert helpers["get_conservative_response"]() == "conservative result"

    def test_get_realist_response(self):
        """Test get_realist_response."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "realist_refinement": {"result": "realist result"}
            }
        })
        assert helpers["get_realist_response"]() == "realist result"

    def test_get_purist_response(self):
        """Test get_purist_response."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "purist_refinement": {"result": "purist result"}
            }
        })
        assert helpers["get_purist_response"]() == "purist result"

    def test_get_collaborative_responses(self):
        """Test get_collaborative_responses."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "progressive_refinement": {"result": "prog"},
                "conservative_refinement": {"result": "cons"},
            }
        })
        result = helpers["get_collaborative_responses"]()
        assert "Progressive: prog" in result
        assert "Conservative: cons" in result

    def test_get_collaborative_responses_empty(self):
        """Test get_collaborative_responses with no responses."""
        helpers = create_agent_helpers({})
        result = helpers["get_collaborative_responses"]()
        assert "No collaborative responses" in result

    def test_get_fork_responses_named(self):
        """Test get_fork_responses with named fork group."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "fork_group": {
                    "agent1": {"response": "resp1"},
                    "agent2": {"response": "resp2"},
                }
            }
        })
        result = helpers["get_fork_responses"]("fork_group")
        assert result == {"agent1": "resp1", "agent2": "resp2"}

    def test_get_fork_responses_no_name(self):
        """Test get_fork_responses without name."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "group1": {"agent1": {"response": "resp1"}},
            }
        })
        result = helpers["get_fork_responses"]()
        assert "group1" in result

    def test_joined_results(self):
        """Test joined_results."""
        helpers = create_agent_helpers({
            "previous_outputs": {
                "join_node": {"joined_results": [1, 2, 3]}
            }
        })
        assert helpers["joined_results"]() == [1, 2, 3]

    def test_joined_results_empty(self):
        """Test joined_results with no results."""
        helpers = create_agent_helpers({})
        assert helpers["joined_results"]() == []

