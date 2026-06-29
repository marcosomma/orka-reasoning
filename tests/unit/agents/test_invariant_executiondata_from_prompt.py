"""Regression: InvariantValidatorAgent must read execution data from the rendered
prompt (formatted_prompt), not the raw input.

Bug: _run_impl passed ctx["input"] (the raw user question) to process(); the
EXECUTION_DATA_JSON block only exists in ctx["formatted_prompt"], so the validator
always logged "No execution_data provided, validation will be limited" and ran on
nothing — silently hollowing out the self-assessment workflows.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from orka.agents.invariant_validator_agent import InvariantValidatorAgent

_EXEC_DATA = {
    "nodes_executed": ["fork_a", "branch_1", "branch_2", "join_a", "responder"],
    "fork_groups": {
        "fork_a": {
            "has_join": True,
            "branches": ["branch_1", "branch_2"],
            "completed_branches": ["branch_1", "branch_2"],
            "fork_group_id": "fork_a",
        }
    },
    "router_decisions": {},
    "graph_structure": {"nodes": {}, "edges": []},
    "tool_calls": [],
    "structured_outputs": {},
}


def _agent():
    return InvariantValidatorAgent(
        agent_id="invariant_collector",
        params={"max_depth": 50, "allow_reentrant_nodes": [], "strict_tool_errors": False},
    )


def test_reads_execution_data_from_formatted_prompt(caplog):
    agent = _agent()
    ctx = {
        "input": "Assess whether the OrKa memory system is functioning correctly.",
        "formatted_prompt": "EXECUTION_DATA_JSON:\n" + json.dumps(_EXEC_DATA),
    }
    with caplog.at_level("WARNING"):
        result = asyncio.run(agent._run_impl(ctx))

    # The fix: data was found, so the "limited" warning must NOT fire.
    assert "No execution_data provided" not in caplog.text, "execution_data not extracted from formatted_prompt"
    # And the validator produced a real result over the provided nodes.
    assert isinstance(result, dict)
    assert "validation_summary" in result or "fork_join_integrity" in result


def test_raw_input_only_still_warns(caplog):
    """Control: with only raw input (no formatted_prompt), there's genuinely no data."""
    agent = _agent()
    ctx = {"input": "Assess the system."}  # no EXECUTION_DATA_JSON anywhere
    with caplog.at_level("WARNING"):
        asyncio.run(agent._run_impl(ctx))
    assert "No execution_data provided" in caplog.text
