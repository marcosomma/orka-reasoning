import json

import pytest

from orka.nodes.path_executor_node import PathExecutorNode


def test_extract_from_nested_response_dict():
    node = PathExecutorNode("execute_path", path_source="path_proposal")

    previous_outputs = {
        "path_proposal": {
            "response": {
                "result": {
                    "target": [{"node_id": "a"}, {"node_id": "b"}]
                },
                "decision": "shortlist",
            }
        }
    }

    agent_path, err = node._extract_agent_path({"previous_outputs": previous_outputs})
    assert err is None
    assert agent_path == ["a", "b"]


def test_extract_from_serialized_response_json():
    node = PathExecutorNode("execute_path", path_source="path_proposal")

    payload = {"result": {"target": [{"node_id": "x"}]}, "decision": "shortlist"}
    serialized = json.dumps(payload)

    previous_outputs = {"path_proposal": {"response": serialized}}

    agent_path, err = node._extract_agent_path({"previous_outputs": previous_outputs})
    assert err is None
    assert agent_path == ["x"]


def test_extract_from_response_with_path_list_strings():
    node = PathExecutorNode("execute_path", path_source="path_proposal")

    previous_outputs = {"path_proposal": {"response": {"result": {"target": ["web_search", "analyzer"]}}}}

    agent_path, err = node._extract_agent_path({"previous_outputs": previous_outputs})
    assert err is None
    assert agent_path == ["web_search", "analyzer"]


def test_extract_from_direct_path_field():
    # If path_source points directly into nested keys it should still work
    node = PathExecutorNode("execute_path", path_source="path_proposal.response.result")

    previous_outputs = {"path_proposal": {"response": {"result": {"target": [{"node_id": "alpha"}]}}}}

    agent_path, err = node._extract_agent_path({"previous_outputs": previous_outputs})
    assert err is None
    assert agent_path == ["alpha"]


def test_extract_from_commit_path_list():
    node = PathExecutorNode("execute_path", path_source="path_proposal")

    previous_outputs = {"path_proposal": {"result": {"target": ["analysis_agent", "response_builder"]}, "decision": "commit_path"}}

    agent_path, err = node._extract_agent_path({"previous_outputs": previous_outputs})
    assert err is None
    assert agent_path == ["analysis_agent", "response_builder"]
