# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
import asyncio
import logging
import os
import subprocess
import sys
import time
from unittest.mock import patch

import pytest
import redis
from fake_redis import FakeRedisClient

# Set PYTEST_RUNNING environment variable at the earliest possible moment
os.environ["PYTEST_RUNNING"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Check if pytest-asyncio is available
try:
    import pytest_asyncio

    print("pytest-asyncio is installed ✓")
except ImportError:
    print("\nWARNING: pytest-asyncio not found. Async tests might be skipped.")
    print("Install with: pip install pytest-asyncio\n")

# Import required modules
try:
    from orka.nodes.fork_node import ForkGroupManager
except ImportError:
    # Create stub for testing
    class ForkGroupManager:
        def remove_group(self, group_id):
            raise KeyError(f"Group {group_id} not found")


try:
    from orka import cli as orka_cli
except ImportError:
    # Create stub module if not available
    import types

    orka_cli = types.ModuleType("orka_cli")
    sys.modules["orka_cli"] = orka_cli

# Global flag to determine if we're using real Redis
USE_REAL_REDIS = os.getenv("USE_REAL_REDIS", "false").lower() == "true"

# Define important environment variables
PYTEST_RUNNING = "true"
SKIP_LLM_TESTS = os.environ.get("SKIP_LLM_TESTS", "false").lower()

# Check for CI environment
if os.environ.get("CI", "").lower() in ("true", "1", "yes"):
    # Always skip LLM tests in CI
    SKIP_LLM_TESTS = "true"

# Set environment variables for test configuration
os.environ["PYTEST_RUNNING"] = PYTEST_RUNNING
os.environ["SKIP_LLM_TESTS"] = SKIP_LLM_TESTS
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy_key_for_testing")


def get_redis_client():
    """Get appropriate Redis client based on configuration."""
    if USE_REAL_REDIS:
        return redis.from_url("redis://localhost:6379/0")
    return FakeRedisClient()


@pytest.fixture(autouse=True, scope="session")
def patch_redis_globally():
    """Patch Redis globally unless using real Redis."""
    if not USE_REAL_REDIS:
        with patch("orka.memory.redis_logger.redis.from_url", return_value=FakeRedisClient()):
            yield
    else:
        yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_memory_after_tests():
    """
    Fixture that runs delete_memory.py script after all tests complete.
    This ensures proper cleanup of memory data.
    """
    yield  # Let all tests run first

    # Only run cleanup if using real Redis
    if USE_REAL_REDIS:
        try:
            script_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "scripts",
                "delete_memory.py",
            )
            if os.path.exists(script_path):
                print("\n🧹 Running memory cleanup after tests...")
                result = subprocess.run(
                    [sys.executable, script_path],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    print("✅ Memory cleanup completed successfully")
                else:
                    print(f"⚠️ Memory cleanup completed with warnings: {result.stderr}")
            else:
                print(f"⚠️ Memory cleanup script not found at: {script_path}")
        except subprocess.TimeoutExpired:
            print("⚠️ Memory cleanup timed out after 30 seconds")
        except Exception as e:
            print(f"⚠️ Error during memory cleanup: {e}")


def test_remove_group_keyerror():
    mgr = ForkGroupManager()
    with pytest.raises(KeyError):
        mgr.remove_group("nonexistent")


def test_main_invokes_asyncio(monkeypatch):
    called = {}

    def fake_run(coro):
        called["ran"] = True

    monkeypatch.setattr("asyncio.run", fake_run)
    sys_argv = sys.argv
    sys.argv = ["prog", "config.yml", "input"]
    try:
        monkeypatch.setattr(
            "orka.orchestrator.Orchestrator",
            lambda config_path: type(
                "DummyOrchestrator",
                (),
                {"run": lambda self, x: None},
            )(),
        )
        import importlib

        importlib.reload(orka_cli)
        assert called.get("ran")
    finally:
        sys.argv = sys_argv


def wait_for_redis(
    redis_url: str,
    max_retries: int = 5,
    retry_delay: float = 1.0,
) -> bool:
    """
    Wait for Redis to be available.

    Args:
        redis_url: Redis connection URL.
        max_retries: Maximum number of connection attempts.
        retry_delay: Delay between retries in seconds.

    Returns:
        True if Redis is available, False otherwise.
    """
    for _ in range(max_retries):
        try:
            client = redis.from_url(redis_url)
            client.ping()
            return True
        except redis.ConnectionError:
            time.sleep(retry_delay)
    return False


@pytest.fixture(scope="session", autouse=True)
def ensure_redis() -> None:
    """
    Ensure Redis is available before running tests.
    This fixture runs automatically for all tests.
    """
    if USE_REAL_REDIS:
        redis_url = "redis://localhost:6379/0"
        if not wait_for_redis(redis_url):
            pytest.skip("Redis is not available")


@pytest.fixture(scope="function")
def redis_client():
    """Create a Redis client for testing."""
    client = get_redis_client()
    yield client
    # Cleanup after tests
    if USE_REAL_REDIS:
        if hasattr(client, "flushdb"):
            client.flushdb()
    else:
        # For FakeRedisClient, we need to clear all data manually
        # Since FakeRedisClient doesn't support flushdb, we'll clear each key type
        for key in client._keys():
            client.delete(key)


@pytest.fixture
def valid_orka_yaml():
    """
    Fixture providing a valid OrKa YAML configuration for testing.
    This ensures all tests use proper YAML structure.
    """
    return """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-binary
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
"""


@pytest.fixture
def complex_orka_yaml():
    """
    Fixture providing a more complex valid OrKa YAML configuration for testing.
    """
    return """
orchestrator:
  id: complex_test_orchestrator
  strategy: parallel
  queue: orka:test
  agents:
    - classifier
    - router
    - answer_builder

agents:
  - id: classifier
    type: openai-classification
    queue: orka:classifier
    prompt: "Classify this input: {{ input }}"
    options:
      - tech
      - science
      - general

  - id: router
    type: router
    params:
      decision_key: classifier
      routing_map:
        tech: ["answer_builder"]
        science: ["answer_builder"]
        general: ["answer_builder"]
    depends_on:
      - classifier

  - id: answer_builder
    type: openai-answer
    queue: orka:answer
    prompt: "Provide an answer for: {{ input }}"
    depends_on:
      - router
"""


# Define a custom event loop policy that pytest-asyncio can use
@pytest.fixture(scope="session")
def event_loop_policy():
    """Return the event loop policy to use for tests."""
    # Use the default policy for now
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session", autouse=True)
def mock_openai_env():
    """Ensure we have an OPENAI_API_KEY set for testing."""
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "dummy_key_for_testing"},
        clear=False,
    ):
        yield
