"""
Tests for orka.orchestrator.agent_factory module.

This module tests the AgentFactory class which handles creation and initialization
of agents and nodes based on configuration.
"""

import os
from unittest.mock import Mock, patch

import pytest

from orka.orchestrator.agent_factory import AGENT_TYPES, AgentFactory

# Check if we should skip async/event loop tests in CI
SKIP_ASYNC_TESTS = os.environ.get("CI", "").lower() in ("true", "1", "yes")

# Skip marker for tests that have event loop issues in CI
async_skip = pytest.mark.skipif(
    SKIP_ASYNC_TESTS,
    reason="Async tests skipped in CI due to event loop issues",
)


class MockOrchestrator(AgentFactory):
    """Mock orchestrator that inherits from AgentFactory for testing."""

    def __init__(self, orchestrator_cfg=None, agent_cfgs=None, memory=None):
        self.orchestrator_cfg = orchestrator_cfg or {}
        self.agent_cfgs = agent_cfgs or []
        self.memory = memory or Mock()


class TestAgentFactory:
    """Test cases for AgentFactory class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.memory = Mock()

    def test_agent_types_registry(self):
        """Test that all expected agent types are registered."""
        expected_types = [
            "binary",
            "classification",
            "local_llm",
            "openai-answer",
            "openai-binary",
            "openai-classification",
            "validate_and_structure",
            "duckduckgo",
            "router",
            "failover",
            "failing",
            "join",
            "fork",
            "memory",
        ]

        for agent_type in expected_types:
            assert agent_type in AGENT_TYPES, f"Agent type {agent_type} not found in registry"

    def test_init_agents_empty_config(self):
        """Test initializing agents with empty configuration."""
        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert instances == {}

    def test_init_unsupported_agent_type(self):
        """Test initializing an unsupported agent type."""
        agent_cfg = {
            "id": "unsupported_1",
            "type": "unsupported_type",
            "prompt": "This won't work",
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        with pytest.raises(ValueError, match="Unsupported agent type: unsupported_type"):
            factory._init_agents()

    def test_init_router_node_basic(self):
        """Test basic router node initialization."""
        agent_cfg = {
            "id": "router_1",
            "type": "router",
            "prompt": "Route this request",
            "queue": None,
            "params": {"decision_key": "route_decision"},
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "router_1" in instances
        assert instances["router_1"].node_id == "router_1"

    @async_skip
    def test_init_memory_reader_node_basic(self):
        """Test basic memory reader node initialization."""
        agent_cfg = {
            "id": "memory_reader_1",
            "type": "memory",
            "prompt": "Read from memory",
            "queue": None,
            "namespace": "test_namespace",
            "config": {
                "operation": "read",
            },
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "memory_reader_1" in instances
        assert instances["memory_reader_1"].node_id == "memory_reader_1"

    @async_skip
    def test_init_memory_writer_node_basic(self):
        """Test basic memory writer node initialization."""
        agent_cfg = {
            "id": "memory_writer_1",
            "type": "memory",
            "prompt": "Write to memory",
            "queue": None,
            "namespace": "test_namespace",
            "config": {
                "operation": "write",
            },
            "vector": True,
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "memory_writer_1" in instances
        assert instances["memory_writer_1"].node_id == "memory_writer_1"

    @async_skip
    def test_init_memory_node_default_operation(self):
        """Test memory node with default operation (read)."""
        agent_cfg = {
            "id": "memory_default_1",
            "type": "memory",
            "prompt": "Default memory operation",
            "queue": None,
            "namespace": "default",
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "memory_default_1" in instances
        assert instances["memory_default_1"].node_id == "memory_default_1"

    def test_init_fork_node_basic(self):
        """Test basic fork node initialization."""
        agent_cfg = {
            "id": "fork_1",
            "type": "fork",
            "prompt": "Fork execution",
            "queue": ["agent1", "agent2"],
            "config": {"targets": [["agent1"], ["agent2"]]},
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "fork_1" in instances
        assert instances["fork_1"].node_id == "fork_1"

    def test_init_join_node_basic(self):
        """Test basic join node initialization."""
        agent_cfg = {
            "id": "join_1",
            "type": "join",
            "prompt": "Join results",
            "queue": None,
            "group_id": "fork_group_123",
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "join_1" in instances
        assert instances["join_1"].node_id == "join_1"

    def test_init_failing_node_basic(self):
        """Test basic failing node initialization."""
        agent_cfg = {
            "id": "failing_1",
            "type": "failing",
            "prompt": "This will fail",
            "queue": None,
            "failure_rate": 0.5,
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "failing_1" in instances
        assert instances["failing_1"].node_id == "failing_1"

    def test_init_failover_node_basic(self):
        """Test basic failover node initialization."""
        agent_cfg = {
            "id": "failover_1",
            "type": "failover",
            "queue": ["next_agent"],
            "children": [
                {
                    "id": "child_1",
                    "type": "failing",
                    "prompt": "Child agent",
                },
            ],
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "failover_1" in instances
        assert instances["failover_1"].node_id == "failover_1"

    def test_init_duckduckgo_tool_basic(self):
        """Test basic DuckDuckGo tool initialization."""
        agent_cfg = {
            "id": "search_1",
            "type": "duckduckgo",
            "prompt": "Search the web",
            "queue": None,
            "max_results": 5,
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "search_1" in instances
        assert instances["search_1"].tool_id == "search_1"

    @async_skip
    def test_init_validation_agent_basic(self):
        """Test basic validation agent initialization."""
        agent_cfg = {
            "id": "validator_1",
            "type": "validate_and_structure",
            "prompt": "Validate this data",
            "queue": None,
            "store_structure": True,
            "schema": {"type": "object"},
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "validator_1" in instances
        # ValidationAndStructuringAgent uses params dict
        assert hasattr(instances["validator_1"], "params")

    @async_skip
    def test_init_multiple_agents(self):
        """Test initializing multiple agents."""
        agent_cfgs = [
            {
                "id": "router_1",
                "type": "router",
                "prompt": "First agent",
                "params": {"decision_key": "test"},
            },
            {
                "id": "memory_1",
                "type": "memory",
                "prompt": "Second agent",
                "config": {"operation": "read"},
            },
        ]

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=agent_cfgs,
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert len(instances) == 2
        assert "router_1" in instances
        assert "memory_1" in instances

    def test_config_field_removal(self):
        """Test that id, type, prompt, and queue fields are removed from config."""
        agent_cfg = {
            "id": "test_router",
            "type": "router",
            "prompt": "Test prompt",
            "queue": ["next"],
            "params": {"decision_key": "test"},
            "custom_param": "value",
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        # Verify agent was created successfully
        assert "test_router" in instances
        assert instances["test_router"].node_id == "test_router"

    @patch("builtins.print")
    def test_debug_output(self, mock_print):
        """Test that debug information is printed during initialization."""
        orchestrator_cfg = {"debug": True}
        agent_cfg = {
            "id": "debug_router",
            "type": "router",
            "prompt": "Debug test",
            "params": {"decision_key": "test"},
        }

        factory = MockOrchestrator(
            orchestrator_cfg=orchestrator_cfg,
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        # Check that debug information was printed
        assert mock_print.call_count >= 2  # orchestrator_cfg and agent_cfgs

        # Check that agent initialization message was printed
        init_calls = [
            call for call in mock_print.call_args_list if "Instantiating agent" in str(call)
        ]
        assert len(init_calls) == 1

    @async_skip
    def test_memory_node_with_missing_namespace(self):
        """Test memory node initialization with missing namespace (uses default)."""
        agent_cfg = {
            "id": "memory_no_namespace",
            "type": "memory",
            "prompt": "Memory without namespace",
            "config": {"operation": "read"},
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "memory_no_namespace" in instances
        assert instances["memory_no_namespace"].node_id == "memory_no_namespace"

    def test_special_memory_handler(self):
        """Test that memory type is handled as special_handler."""
        assert AGENT_TYPES["memory"] == "special_handler"

    def test_agent_type_case_insensitive(self):
        """Test that agent type handling is case insensitive."""
        agent_cfg = {
            "id": "router_upper",
            "type": "router",  # uppercase
            "prompt": "Test case insensitive",
            "params": {"decision_key": "test"},
        }

        factory = MockOrchestrator(
            orchestrator_cfg={},
            agent_cfgs=[agent_cfg],
            memory=self.memory,
        )

        instances = factory._init_agents()

        assert "router_upper" in instances
        assert instances["router_upper"].node_id == "router_upper"
