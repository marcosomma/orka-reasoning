import asyncio
import os
import sys
import tempfile
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Disable memory decay scheduler BEFORE any orka imports to prevent thread accumulation.
# This must be set early, before OrchestratorBase is imported, as it reads this env var
# during module initialization.
os.environ["ORKA_MEMORY_DECAY_ENABLED"] = "false"

import importlib.util
import types as _types

import pytest
import sys
import yaml

# Optional/conditional test-time modules
try:
    import orka.memory_logger as memory_logger_mod
except Exception:
    memory_logger_mod = None

try:
    import orka.utils.embedder as embedder_mod
except Exception:
    embedder_mod = None

try:
    import orka.memory.redisstack_logger as rs_mod
except Exception:
    rs_mod = None

try:
    import litellm.llms.custom_httpx.async_client_cleanup as _litellm_async_cleanup
except Exception:
    _litellm_async_cleanup = None


# Minimal test-time shim for redis to avoid network/ConnectionPool side-effects.
def _ensure_redis_shim():
    # Prefer the real redis package if it's installed.
    try:
        if importlib.util.find_spec("redis") is not None:
            return
    except Exception:
        # If introspection fails, fall back to shim logic below.
        pass

    if "redis" in sys.modules:
        return
    redis_mod = ModuleType("redis")
    # Provide classes/attrs used in production imports
    class RedisShim:
        def __init__(self, *args, **kwargs):
            pass

        def ping(self):
            return True

        def hset(self, *args, **kwargs):
            return None

        def expire(self, *args, **kwargs):
            return None

        def disconnect(self):
            return None

    class ConnectionPoolShim:
        def __init__(self, *args, **kwargs):
            # mimic attributes checked by tests
            self.max_connections = kwargs.get("max_connections", 100)
            self._created_connections = 0
            self._available_connections = []
            self._in_use_connections = []

        @classmethod
        def from_url(cls, *args, **kwargs):
            return cls(*args, **kwargs)

    redis_mod.Redis = RedisShim
    redis_mod.ConnectionPool = ConnectionPoolShim

    def from_url(*args, **kwargs):
        return RedisShim(*args, **kwargs)

    redis_mod.from_url = from_url
    # Common exceptions referenced
    class RedisError(Exception):
        pass

    redis_mod.TimeoutError = RedisError
    redis_mod.ConnectionError = RedisError
    # Provide a minimal `redis.asyncio` module used by some fixtures
    try:
        import types as _types

        asyncio_mod = ModuleType("redis.asyncio")

        class AsyncRedisShim(RedisShim):
            async def ping(self):
                return True

        asyncio_mod.Redis = AsyncRedisShim
        asyncio_mod.ConnectionPool = ConnectionPoolShim

        async def async_from_url(*args, **kwargs):
            return AsyncRedisShim(*args, **kwargs)

        asyncio_mod.from_url = async_from_url
        sys.modules["redis.asyncio"] = asyncio_mod
        redis_mod.asyncio = asyncio_mod
    except Exception:
        # best-effort; not critical
        pass

    # Also provide submodules expected by production imports (e.g. redis.client)
    client_mod = ModuleType("redis.client")
    client_mod.Redis = RedisShim
    sys.modules["redis.client"] = client_mod
    redis_mod.client = client_mod

    connection_mod = ModuleType("redis.connection")
    connection_mod.ConnectionPool = ConnectionPoolShim
    sys.modules["redis.connection"] = connection_mod
    redis_mod.connection = connection_mod

    sys.modules["redis"] = redis_mod


_ensure_redis_shim()


@pytest.fixture(autouse=True)
def global_test_mocks(request, monkeypatch):
    """
    Global test fixtures to mock heavy external dependencies so unit tests
    run deterministically in CI (no Redis, no model downloads, no network).

    This fixture is autouse and applies to all tests.
    """
    # Allow opting out (for "strict" runs that validate real wiring)
    if os.environ.get("ORKA_TEST_DISABLE_GLOBAL_MOCKS", "").strip().lower() in {"1", "true", "yes"}:
        yield
        return

    if hasattr(request, "node") and request.node.get_closest_marker("no_global_mocks"):
        yield
        return

    # Mock the memory logger factory to return a lightweight mock object
    # without decay scheduler threads that can accumulate and hang tests
    try:
        import orka.memory_logger as memory_logger_mod

        def fake_create_memory_logger(*args, **kwargs):
            m = MagicMock()
            # minimal attributes used across the codebase
            m.redis = MagicMock()
            m.index_name = kwargs.get("memory_preset", "orka_enhanced_memory")
            m.store = MagicMock()
            m.query = MagicMock(return_value=[])
            # Ensure close() and stop_decay_scheduler() are no-ops
            m.close = MagicMock()
            m.stop_decay_scheduler = MagicMock()
            return m

        monkeypatch.setattr(memory_logger_mod, "create_memory_logger", fake_create_memory_logger)
        
        # Also patch in base.py where create_memory_logger is imported directly
        try:
            import orka.orchestrator.base as base_mod
            monkeypatch.setattr(base_mod, "create_memory_logger", fake_create_memory_logger)
        except Exception:
            pass
    except Exception:
        # If module not importable during some targeted tests, skip patch
        pass

    # Prevent embedder/model download attempts
    try:
        import orka.utils.embedder as embedder_mod

        monkeypatch.setattr(embedder_mod, "download_model_if_missing", lambda *a, **k: None)
        monkeypatch.setattr(embedder_mod, "load_local_model", lambda *a, **k: MagicMock())
    except Exception:
        pass

    # Ensure environment variables that trigger network or longer flows are disabled
    os.environ.setdefault("ORKA_MEMORY_BACKEND", "redisstack")
    os.environ.setdefault("ORKA_DEBUG_KEEP_PREVIOUS_OUTPUTS", "false")

    # Patch any known Redis client factories to avoid actual network calls
    try:
        import orka.memory.redisstack_logger as rs_mod

        monkeypatch.setattr(rs_mod, "Redis", MagicMock())
    except Exception:
        pass

    yield

# Set test environment
os.environ["PYTEST_RUNNING"] = "true"
os.environ["ORKA_ENV"] = "test"

# LiteLLM registers an async-client cleanup that can emit a
# "coroutine ... was never awaited" RuntimeWarning at interpreter shutdown
# (after pytest has already finished).
# We neutralize that cleanup in tests to keep warning policy strict for OrKa code.
try:
    import litellm.llms.custom_httpx.async_client_cleanup as _litellm_async_cleanup

    def _orka__noop_close_litellm_async_clients(*args, **kwargs):
        return None

    _litellm_async_cleanup.close_litellm_async_clients = _orka__noop_close_litellm_async_clients
except Exception:
    pass

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
    
    # ddgs is an optional dependency; patching ddgs.DDGS requires the module to exist.
    # In minimal CI environments it may be absent, so we stub it in sys.modules first.
    if "ddgs" not in sys.modules:
        stub_ddgs = Mock()
        stub_ddgs.DDGS = Mock()
        sys.modules["ddgs"] = stub_ddgs

    with patch('redis.Redis', return_value=redis_mock), \
         patch('redis.asyncio.Redis', return_value=redis_mock), \
         patch('sentence_transformers.SentenceTransformer', return_value=embedder_mock), \
         patch('ddgs.DDGS', return_value=ddgs_mock), \
         patch('litellm.completion', return_value=litellm_mock), \
         patch('litellm.llms.custom_httpx.async_client_cleanup.close_litellm_async_clients', lambda *a, **k: None), \
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


# Shared fixtures used by PlanValidator unit tests and integration-style node tests
@pytest.fixture
def mock_prompt_builder():
    """Fixture for a mocked prompt_builder used by PlanValidator tests."""
    with patch("orka.agents.plan_validator.prompt_builder.build_validation_prompt") as mock_build_validation_prompt:
        mock_build_validation_prompt.return_value = "Mocked validation prompt"
        yield mock_build_validation_prompt


@pytest.fixture
def mock_boolean_score_calculator_class():
    """Fixture for a mocked BooleanScoreCalculator class used by PlanValidator tests."""
    from orka.scoring import BooleanScoreCalculator

    with patch("orka.agents.plan_validator.agent.BooleanScoreCalculator") as mock_class:
        mock_instance = MagicMock(spec=BooleanScoreCalculator)
        mock_instance.calculate.return_value = {
            "score": 0.8,
            "assessment": "ACCEPTED",
            "breakdown": {"completeness": 0.9, "efficiency": 0.7},
            "passed_criteria": ["completeness_check"],
            "failed_criteria": ["efficiency_check"],
            "dimension_scores": {"completeness": 0.9, "efficiency": 0.7},
            "total_criteria": 2,
            "passed_count": 1,
        }
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def temp_config_file():
    """Create temporary YAML config file with decay disabled for tests."""
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
        }],
        # Disable memory decay scheduler for tests to prevent thread accumulation
        'memory': {
            'decay': {
                'enabled': False
            }
        }
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
    from orka.orchestrator.graph_api import EdgeDescriptor, GraphState, NodeDescriptor
    
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
    config.addinivalue_line("markers", "no_global_mocks: Skip global test-time mocks (strict wiring)")


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
