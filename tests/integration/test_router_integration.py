"""Integration tests for RouterNode in real workflow execution."""

import pytest
import yaml
from pathlib import Path
import tempfile

from orka.orchestrator import Orchestrator


# Helper to create temporary YAML config files
def create_temp_workflow(workflow_config):
    """Create a temporary YAML file for workflow config."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.safe_dump(workflow_config, temp_file)
    temp_file.close()
    return temp_file.name


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama server running - for manual testing")
async def test_router_node_basic_workflow():
    """Test RouterNode with basic true/false routing."""
    workflow_config = {
        "orchestrator": {
            "id": "test_router",
            "strategy": "sequential",
            "agents": ["classifier", "router", "final"],
        },
        "agents": [
            {
                "id": "classifier",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "temperature": 0.1,
                "prompt": "Return exactly 'true' if the input is a question, 'false' otherwise: {{ input }}",
            },
            {
                "id": "router",
                "type": "router",
                "params": {
                    "decision_key": "classifier",
                    "routing_map": {
                        "true": ["question_handler"],
                        "false": ["statement_handler"],
                    },
                },
                "depends_on": ["classifier"],
            },
            {
                "id": "question_handler",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "temperature": 0.7,
                "prompt": "Answer this question: {{ input }}",
            },
            {
                "id": "statement_handler",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "temperature": 0.3,
                "prompt": "Validate this statement: {{ input }}",
            },
            {
                "id": "final",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "temperature": 0.5,
                "prompt": "Summarize: {{ get_agent_response('question_handler') or get_agent_response('statement_handler') }}",
            },
        ],
    }

    config_file = create_temp_workflow(workflow_config)
    try:
        orchestrator = Orchestrator(config_file)
        result = await orchestrator.run("What is the capital of France?")

        assert result is not None
        assert "final" in result
        # Verify router executed correctly by checking that question_handler was called
        assert "question_handler" in result or "statement_handler" in result
    finally:
        Path(config_file).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama server running - for manual testing")
async def test_router_node_with_dict_decision_value():
    """Test RouterNode handles dict decision values correctly."""
    workflow_config = {
        "orchestrator": {
            "id": "test_router_dict",
            "strategy": "sequential",
            "agents": ["analyzer", "router", "handler"],
        },
        "agents": [
            {
                "id": "analyzer",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "temperature": 0.1,
                "prompt": "Classify sentiment as 'positive' or 'negative': {{ input }}",
            },
            {
                "id": "router",
                "type": "router",
                "params": {
                    "decision_key": "analyzer",
                    "routing_map": {
                        "positive": ["positive_handler"],
                        "negative": ["negative_handler"],
                    },
                },
                "depends_on": ["analyzer"],
            },
            {
                "id": "positive_handler",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "prompt": "Respond positively to: {{ input }}",
            },
            {
                "id": "negative_handler",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "prompt": "Respond empathetically to: {{ input }}",
            },
        ],
    }

    orchestrator = Orchestrator(workflow_config)
    result = await orchestrator.run("I love this product!")

    assert result is not None
    # Verify one of the handlers was executed
    assert "positive_handler" in result or "negative_handler" in result


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama server running - for manual testing")
async def test_router_node_empty_route():
    """Test RouterNode handles empty routing gracefully."""
    workflow_config = {
        "orchestrator": {
            "id": "test_router_empty",
            "strategy": "sequential",
            "agents": ["classifier", "router", "fallback"],
        },
        "agents": [
            {
                "id": "classifier",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "temperature": 0.1,
                "prompt": "Return 'unknown' for: {{ input }}",
            },
            {
                "id": "router",
                "type": "router",
                "params": {
                    "decision_key": "classifier",
                    "routing_map": {
                        "known": ["handler"],
                    },
                },
                "depends_on": ["classifier"],
            },
            {
                "id": "fallback",
                "type": "local_llm",
                "model": "gpt-oss:20b",
                "model_url": "http://localhost:11434/api/generate",
                "provider": "ollama",
                "prompt": "Fallback response for: {{ input }}",
            },
        ],
    }

    orchestrator = Orchestrator(workflow_config)
    result = await orchestrator.run("test input")

    assert result is not None
    # Should proceed to fallback since router has no matching route
    assert "fallback" in result


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama server running - for manual testing")
async def test_failover_search_validate_example():
    """Test the actual failover_search_and_validate.yml example workflow."""
    import yaml
    from pathlib import Path

    # Load the actual example workflow
    example_path = Path(__file__).parent.parent.parent / "examples" / "failover_search_and_validate.yml"
    if not example_path.exists():
        pytest.skip("Example file not found")

    with open(example_path) as f:
        workflow_config = yaml.safe_load(f)

    orchestrator = Orchestrator(str(example_path))
    result = await orchestrator.run("is routing working as expected?")

    assert result is not None
    # Verify router executed and routed correctly
    assert "need_answer" in result
    assert "router_answer" in result
    # Should have executed one of the paths
    assert "build_answer" in result or "validate_fact" in result
    assert "final_summary" in result
