# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for loop helper functions."""

import pytest

from orka.orchestrator.prompt_rendering.loop_helpers import create_loop_helpers


class TestLoopHelpers:
    """Tests for loop helper functions."""

    def test_get_loop_number_direct(self):
        """Test get_loop_number with direct value."""
        helpers = create_loop_helpers({"loop_number": 5})
        assert helpers["get_loop_number"]() == 5

    def test_get_loop_number_nested(self):
        """Test get_loop_number with nested value."""
        helpers = create_loop_helpers({"input": {"loop_number": 3}})
        assert helpers["get_loop_number"]() == 3

    def test_get_loop_number_default(self):
        """Test get_loop_number default value."""
        helpers = create_loop_helpers({})
        assert helpers["get_loop_number"]() == 1

    def test_get_past_loops_empty(self):
        """Test get_past_loops with no loops."""
        helpers = create_loop_helpers({})
        assert helpers["get_past_loops"]() == []

    def test_get_past_loops_from_previous_outputs(self):
        """Test get_past_loops from previous_outputs."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [{"round": 1}, {"round": 2}]
            }
        })
        assert len(helpers["get_past_loops"]()) == 2

    def test_has_past_loops_true(self):
        """Test has_past_loops returns True."""
        helpers = create_loop_helpers({
            "previous_outputs": {"past_loops": [{"round": 1}]}
        })
        assert helpers["has_past_loops"]() is True

    def test_has_past_loops_false(self):
        """Test has_past_loops returns False."""
        helpers = create_loop_helpers({})
        assert helpers["has_past_loops"]() is False

    def test_get_past_insights(self):
        """Test get_past_insights."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [{"synthesis_insights": "insight text"}]
            }
        })
        assert helpers["get_past_insights"]() == "insight text"

    def test_get_past_insights_none(self):
        """Test get_past_insights with no loops."""
        helpers = create_loop_helpers({})
        assert "No synthesis" in helpers["get_past_insights"]()

    def test_get_past_loop_data_key(self):
        """Test get_past_loop_data with key."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [{"field": "value"}]
            }
        })
        assert helpers["get_past_loop_data"]("field") == "value"

    def test_get_past_loop_data_no_key(self):
        """Test get_past_loop_data without key."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [{"field": "value"}]
            }
        })
        result = helpers["get_past_loop_data"](None)
        assert "field" in result

    def test_get_round_info(self):
        """Test get_round_info."""
        helpers = create_loop_helpers({
            "loop_number": 2,
            "previous_outputs": {
                "past_loops": [{"round": "1"}]
            }
        })
        assert helpers["get_round_info"]() == "1"

    def test_get_loop_rounds(self):
        """Test get_loop_rounds."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [{"round": 1}, {"round": 2}, {"round": 3}]
            }
        })
        assert helpers["get_loop_rounds"]() == 3

    def test_get_final_score_from_past_loops(self):
        """Test get_final_score from past loops."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "past_loops": [{"agreement_score": 0.85}]
            }
        })
        assert helpers["get_final_score"]() == 0.85

    def test_get_loop_status_default(self):
        """Test get_loop_status default."""
        helpers = create_loop_helpers({})
        assert helpers["get_loop_status"]() == "completed"

    def test_get_loop_output(self):
        """Test get_loop_output."""
        helpers = create_loop_helpers({
            "previous_outputs": {
                "agent1": {"response": {"data": "value"}}
            }
        })
        result = helpers["get_loop_output"]("agent1")
        assert result == {"data": "value"}

    def test_get_loop_output_missing(self):
        """Test get_loop_output with missing agent."""
        helpers = create_loop_helpers({})
        result = helpers["get_loop_output"]("missing")
        assert result == {}

