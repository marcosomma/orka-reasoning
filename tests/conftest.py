"""Test configuration and fixtures for OrKa test suite."""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Generator, List
import tempfile
import yaml
import asyncio
from pathlib import Path

# Set test environment
os.environ["PYTEST_RUNNING"] = "true"
os.environ["ORKA_ENV"] = "test"

# Mock external services that should not run in unit tests
MOCK_EXTERNAL_SERVICES = [
    'redis.Redis',
    'redis.asyncio.Redis', 
    'sentence_transformers.SentenceTransformer',
    'ddgs.DDGS',
    'openai.OpenAI',
    'litellm.completion',
    'httpx.AsyncClient',
]


@pytest.fixture(autouse=True)
def mock_external_services(request):
    """Auto-mock external services for unit tests, but allow opt-out."""
    # Skip auto-mocking if test is marked with no_auto_mock
    if hasattr(request, 'node') and request.node.get_closest_marker('no_auto_mock'):
        yield
        return
    
    # Mock Redis
    redis_mock = Mock()
    redis_mock.ping.return_value = True
    redis_mock.set.return_value = True
    redis_mock.get.return_value = '{"test": "data"}'
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = True
    redis_mock.scan_iter.return_value = iter(['test:key1', 'test:key2'])
    redis_mock.hset.return_value = True
    redis_mock.hget.return_value = '{"vector": [0.1, 0.2, 0.3]}'
    redis_mock.ft.return_value = Mock()
    
    # Mock SentenceTransformer
    embedder_mock = Mock()
    embedder_mock.encode.return_value = [[0.1, 0.2, 0.3] * 128]  # 384-dim vector
    
    # Mock DDGS
    ddgs_mock = Mock()
    ddgs_mock.text.return_value = [
        {"title": "Test Result", "body": "Test content", "href": "https://test.com"}
    ]
    
    # Mock LiteLLM
    litellm_mock = Mock()
    litellm_mock.completion.return_value = Mock(
        choices=[Mock(message=Mock(content="Test LLM response"))]
    )
    
    with patch('redis.Redis', return_value=redis_mock), \
         patch('redis.asyncio.Redis', return_value=redis_mock), \
         patch('sentence_transformers.SentenceTransformer', return_value=embedder_mock), \
         patch('ddgs.DDGS', return_value=ddgs_mock), \
         patch('litellm.completion', return_value=litellm_mock), \
         patch('httpx.AsyncClient'):
        yield


@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    redis_mock = Mock()
    redis_mock.ping.return_value = True
    redis_mock.set.return_value = True
    redis_mock.get.return_value = '{"test": "data"}'
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = True
    redis_mock.scan_iter.return_value = iter(['test:key1', 'test:key2'])
    redis_mock.hset.return_value = True
    redis_mock.hget.return_value = '{"vector": [0.1, 0.2, 0.3]}'
    redis_mock.ft.return_value = Mock()
    return redis_mock


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for unit tests."""
    return {
        "response": "Test LLM response",
        "tokens": 100,
        "cost": 0.001,
        "latency": 1.5,
        "model": "test-model"
    }


@pytest.fixture
def mock_embedder():
    """Mock sentence transformer embedder."""
    embedder_mock = Mock()
    embedder_mock.encode.return_value = [[0.1, 0.2, 0.3] * 128]  # 384-dim vector
    embedder_mock.get_sentence_embedding_dimension.return_value = 384
    return embedder_mock


@pytest.fixture
def mock_search_results():
    """Mock search results for DuckDuckGo."""
    return [
        {
            "title": "Test Search Result 1",
            "body": "This is test content for search result 1",
            "href": "https://example.com/result1"
        },
        {
            "title": "Test Search Result 2", 
            "body": "This is test content for search result 2",
            "href": "https://example.com/result2"
        }
    ]


@pytest.fixture
def temp_config_file():
    """Create temporary YAML config file."""
    config_data = {
        'orchestrator': {
            'id': 'test_workflow',
            'strategy': 'sequential',
            'queue': 'test_queue',
            'agents': ['test_agent']
        },
        'agents': [{
            'id': 'test_agent',
            'type': 'local_llm',
            'prompt': 'Test prompt: {{ input }}',
            'provider': 'ollama',
            'model': 'test-model'
        }]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        yield f.name
    
    os.unlink(f.name)


@pytest.fixture
def sample_context():
    """Sample execution context for tests."""
    return {
        'run_id': 'test_run_123',
        'input': 'Test input query',
        'previous_outputs': {},
        'orchestrator': Mock(),
        'step_index': 0,
        'queue': ['test_agent']
    }


@pytest.fixture
def sample_graph_state():
    """Sample graph state for GraphScout tests."""
    from orka.orchestrator.graph_api import GraphState, NodeDescriptor, EdgeDescriptor
    
    nodes = {
        "test_agent": NodeDescriptor(
            id="test_agent",
            type="LocalLLMAgent",
            prompt_summary="Test agent for unit tests",
            capabilities=["text_generation"],
            contract={},
            cost_model={"base_cost": 0.001},
            safety_tags=["safe"],
            metadata={}
        ),
        "search_agent": NodeDescriptor(
            id="search_agent",
            type="SearchAgent",
            prompt_summary="Search agent for testing",
            capabilities=["web_search"],
            contract={},
            cost_model={"base_cost": 0.002},
            safety_tags=["safe"],
            metadata={}
        )
    }
    
    edges = [EdgeDescriptor(src="test_agent", dst="search_agent", weight=1.0)]
    
    return GraphState(
        nodes=nodes,
        edges=edges,
        current_node="test_agent",
        visited_nodes=set(),
        runtime_state={"run_id": "test_run_123"},
        budgets={"max_tokens": 1000, "max_cost": 0.10},
        constraints={}
    )


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for unit tests."""
    orchestrator = Mock()
    orchestrator.agents = {
        "test_agent": Mock(
            __class__=Mock(__name__="LocalLLMAgent"),
            required_inputs=[],
            capabilities=["text_generation"],
            safety_tags=["safe"]
        ),
        "search_agent": Mock(
            __class__=Mock(__name__="SearchAgent"),
            required_inputs=["query"],
            capabilities=["web_search"],
            safety_tags=["safe"]
        )
    }
    orchestrator.orchestrator_cfg = {
        "agents": ["test_agent", "search_agent"],
        "strategy": "sequential"
    }
    orchestrator.queue = ["test_agent"]
    orchestrator.step_index = 0
    orchestrator.memory_manager = Mock()
    return orchestrator


@pytest.fixture
def sample_candidates():
    """Sample candidates for GraphScout path evaluation."""
    return [
        {
            "node_id": "test_agent",
            "path": ["test_agent"],
            "estimated_cost": 0.001,
            "estimated_latency": 500,
            "confidence": 0.8
        },
        {
            "node_id": "search_agent", 
            "path": ["test_agent", "search_agent"],
            "estimated_cost": 0.003,
            "estimated_latency": 1500,
            "confidence": 0.9
        }
    ]


@pytest.fixture
def temp_memory_file():
    """Create temporary memory file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"test_memory": {"content": "test data", "timestamp": "2024-01-01T00:00:00Z"}}')
        yield f.name
    
    os.unlink(f.name)


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for different environments."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests with mocked external services")
    config.addinivalue_line("markers", "integration: Integration tests with real services")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "no_auto_mock: Skip automatic mocking of external services")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    for item in items:
        # Auto-mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Auto-mark integration tests  
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# Helper functions for tests
def create_test_config(agents_config: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create test configuration dictionary."""
    if agents_config is None:
        agents_config = [{
            'id': 'test_agent',
            'type': 'local_llm',
            'prompt': 'Test: {{ input }}',
            'provider': 'test',
            'model': 'test-model'
        }]
    
    return {
        'orchestrator': {
            'id': 'test_workflow',
            'strategy': 'sequential',
            'queue': 'test_queue',
            'agents': [agent['id'] for agent in agents_config]
        },
        'agents': agents_config
    }


def assert_mock_called_with_pattern(mock_obj, pattern: str):
    """Assert that mock was called with argument containing pattern."""
    for call in mock_obj.call_args_list:
        args, kwargs = call
        for arg in args:
            if isinstance(arg, str) and pattern in arg:
                return True
        for value in kwargs.values():
            if isinstance(value, str) and pattern in value:
                return True
    raise AssertionError(f"Mock was not called with argument containing '{pattern}'")
