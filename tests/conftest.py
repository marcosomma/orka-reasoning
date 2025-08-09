# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

import asyncio
import logging
import os
import pathlib
import subprocess
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# Set PYTEST_RUNNING environment variable at the earliest possible moment
os.environ["PYTEST_RUNNING"] = "true"

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Environment detection
IS_CI = os.environ.get("CI", "").lower() in ("true", "1", "yes")
IS_GITHUB_ACTIONS = "false"
PYTEST_RUNNING = os.environ.get("PYTEST_RUNNING", "").lower() == "true"
USE_REAL_REDIS = os.environ.get("USE_REAL_REDIS", "false").lower() == "true"

# Test execution configuration
SKIP_LLM_TESTS = os.environ.get("SKIP_LLM_TESTS", "true" if IS_CI else "false").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Set environment variables
os.environ["PYTEST_RUNNING"] = "true"
os.environ["SKIP_LLM_TESTS"] = str(SKIP_LLM_TESTS).lower()


# Load .env early so real keys are available for integration tests (non-CI)
def _load_env_file(env_path: pathlib.Path) -> None:
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Do not override already-set environment vars
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


_root = pathlib.Path(__file__).resolve().parent.parent
_env = _root / ".env"
if _env.exists():
    _load_env_file(_env)

# Ensure OPENAI_API_KEY always present to avoid crashes; tests can still mock LLMs
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy_key_for_testing")

# Configure logging for CI
if IS_CI:
    logging.basicConfig(
        level=logging.WARNING,  # Less verbose in CI
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# Import fake Redis if needed
try:
    from fake_redis import FakeRedisClient
except ImportError:
    # Create a minimal fake Redis client if the module doesn't exist
    class FakeRedisClient:
        def __init__(self):
            self._data = {}
            self._sets = {}

        def ping(self):
            return True

        def get(self, key):
            return self._data.get(key)

        def set(self, key, value):
            self._data[key] = value
            return True

        def delete(self, *keys):
            count = 0
            for key in keys:
                if key in self._data:
                    del self._data[key]
                    count += 1
            return count

        def flushdb(self):
            self._data.clear()
            self._sets.clear()
            return True

        def sadd(self, key, *members):
            if key not in self._sets:
                self._sets[key] = set()
            self._sets[key].update(members)
            return len(members)

        def smembers(self, key):
            return self._sets.get(key, set())


try:
    import redis
except ImportError:
    redis = None


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for different environments."""
    if IS_CI:
        # Add CI-specific markers
        config.addinivalue_line("markers", "ci_only: mark test to run only in CI")
        config.addinivalue_line("markers", "local_only: mark test to run only locally")

    # Skip slow tests in CI by default
    if IS_CI and not config.getoption("--run-slow", default=False):
        config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment."""
    if IS_CI:
        # Skip local-only tests in CI
        skip_local = pytest.mark.skip(reason="Skipped in CI environment")
        for item in items:
            if "local_only" in item.keywords:
                item.add_marker(skip_local)

        # Skip slow tests if not explicitly requested
        if not config.getoption("--run-slow", default=False):
            skip_slow = pytest.mark.skip(reason="Slow tests skipped (use --run-slow)")
            for item in items:
                if "slow" in item.keywords:
                    item.add_marker(skip_slow)
    else:
        # Skip CI-only tests locally
        skip_ci = pytest.mark.skip(reason="CI-only test")
        for item in items:
            if "ci_only" in item.keywords:
                item.add_marker(skip_ci)


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )
    parser.addoption(
        "--use-real-services",
        action="store_true",
        default=USE_REAL_REDIS,
        help="Use real Redis/Kafka services",
    )


# Core fixtures
@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure the test environment."""
    # Set test-specific environment variables
    os.environ["ORKA_ENV"] = "test"
    os.environ["ORKA_LOG_LEVEL"] = "WARNING" if IS_CI else "INFO"

    yield

    # Cleanup after all tests
    if not IS_CI:  # Only cleanup locally
        cleanup_test_data()


@pytest.fixture(scope="session")
def redis_client():
    """Provide Redis client based on configuration."""
    if USE_REAL_REDIS and redis and wait_for_redis(REDIS_URL):
        client = redis.from_url(REDIS_URL)
        yield client
        try:
            client.flushdb()  # Clean up after tests
        except Exception:
            pass
    else:
        yield FakeRedisClient()


@pytest.fixture(scope="function", autouse=True)
def isolate_tests():
    """Ensure test isolation."""
    # Clear any global state
    import gc

    gc.collect()

    yield

    # Post-test cleanup
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    """Mock external services in CI environment."""
    if IS_CI or SKIP_LLM_TESTS:
        with patch("openai.OpenAI") as mock_openai:
            # Configure OpenAI mock
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Mocked response"
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            yield mock_openai
    else:
        yield None


# Configuration fixtures
@pytest.fixture(scope="session")
def basic_config():
    """Basic configuration for testing."""
    return {
        "orchestrator": {
            "id": "test_orchestrator",
            "strategy": "sequential",
            "queue": "orka:test",
        },
    }


@pytest.fixture(scope="session")
def agent_config():
    """Basic agent configuration."""
    return {
        "id": "test_agent",
        "type": "openai-answer",
        "queue": "orka:test_queue",
        "prompt": "Test prompt: {{ input }}",
    }


@pytest.fixture(scope="function")
def mock_memory_logger():
    """Mock memory logger for testing."""
    mock_logger = MagicMock()
    mock_logger.log_event.return_value = None
    mock_logger.get_events.return_value = []
    mock_logger.clear_events.return_value = None
    return mock_logger


@pytest.fixture(scope="function")
def temp_yaml_config(tmp_path):
    """Create a temporary YAML config file."""
    config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-answer
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
"""
    config_file = tmp_path / "test_config.yml"
    config_file.write_text(config_content)
    return str(config_file)


# Utility functions
def wait_for_redis(redis_url: str, max_retries: int = 5, retry_delay: float = 1.0) -> bool:
    """Wait for Redis to be available."""
    if not redis:
        return False

    for attempt in range(max_retries):
        try:
            client = redis.from_url(redis_url)
            client.ping()
            return True
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    return False


def cleanup_test_data():
    """Clean up test data after test session."""
    try:
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "delete_memory.py")
        if os.path.exists(script_path):
            subprocess.run([sys.executable, script_path], check=False, timeout=30)
    except Exception as e:
        logging.warning(f"Failed to cleanup test data: {e}")
