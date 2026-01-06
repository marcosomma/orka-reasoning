import os
import yaml
import pytest


@pytest.mark.no_auto_mock
def test_example_yaml_loads():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "examples", "structured_output_demo.yml")
    path = os.path.normpath(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "orchestrator" in data
    assert "agents" in data
    agents = data.get("agents", [])
    assert any(a.get("params", {}).get("structured_output", {}).get("enabled") for a in agents)
    # Ensure local_llm examples exist for LM Studio with three modes
    local_agents = [a for a in agents if a.get("type") == "local_llm"]
    assert len(local_agents) >= 3, "Expected three local_llm agents in the example"

    modes = {a.get("id"): a.get("params", {}).get("structured_output", {}).get("mode") for a in local_agents}
    assert "summarize_local_prompt" in modes and modes["summarize_local_prompt"] == "prompt"
    assert "summarize_local_model_json" in modes and modes["summarize_local_model_json"] == "model_json"
    assert "summarize_local_tool_call" in modes and modes["summarize_local_tool_call"] == "tool_call"

    # Verify schema presence and fields for one of them
    for agent_id in ("summarize_local_prompt", "summarize_local_model_json", "summarize_local_tool_call"):
        a = next(a for a in local_agents if a.get("id") == agent_id)
        so = a.get("params", {}).get("structured_output", {})
        schema = so.get("schema", {})
        assert schema.get("required") == ["summary"]
        assert "key_points" in schema.get("optional", {})
        assert schema.get("optional", {}).get("word_count") in ("integer", "int")
