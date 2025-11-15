import pytest

from orka.nodes.loop_node import LoopNode


@pytest.mark.asyncio
async def test_extract_score_agent_key_strategy():
    node = LoopNode("test_node")

    # Configure an agent_key strategy targeting 'agent_x' and default key 'response'
    node.score_extraction_config = {
        "strategies": [
            {"type": "agent_key", "agents": ["agent_x"], "key": "response"}
        ]
    }

    payload = {"agent_x": {"response": "SCORE: 0.42 some text"}}

    score = await node._extract_score(payload)

    assert isinstance(score, float)
    assert abs(score - 0.42) < 1e-6


import asyncio


@pytest.mark.asyncio
async def test_extract_score_high_priority_present_but_no_score_returns_zero():
    node = LoopNode("test_node")

    # Force no boolean scorer
    node.score_calculator = None
    # Ensure high_priority_agents includes 'agreement_moderator'
    node.high_priority_agents = ["agreement_moderator"]

    # Provide a result with the high-priority agent but no extractable score
    payload = {"agreement_moderator": {"response": "No score here"}}

    score = await node._extract_score(payload)

    assert isinstance(score, float)
    assert score == 0.0
