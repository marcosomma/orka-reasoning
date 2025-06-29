"""
Advanced integration tests for complex workflow scenarios.
Tests memory operations, fork/join patterns, and error handling.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orka.orchestrator import Orchestrator


class TestAdvancedWorkflows:
    """Test advanced workflow patterns and edge cases."""

    @pytest.fixture(autouse=True)
    def setup_advanced_mocks(self):
        """Set up comprehensive mocks for advanced testing."""
        with patch("redis.from_url") as mock_redis, patch(
            "orka.agents.llm_agents.client",
        ) as mock_openai, patch("orka.tools.search_tools.DDGS") as mock_ddg, patch(
            "orka.memory.redisstack_logger.redis.Redis",
        ) as mock_redis_stack:
            # Mock Redis with hash operations
            redis_instance = MagicMock()
            redis_instance.hget.return_value = None
            redis_instance.hset.return_value = True
            redis_instance.hkeys.return_value = []
            redis_instance.smembers.return_value = set()
            redis_instance.hdel.return_value = True
            mock_redis.return_value = redis_instance

            # Mock RedisStack
            mock_redis_stack.return_value = redis_instance

            # Mock OpenAI with different response types
            def create_openai_response(content="Test response", model="gpt-4"):
                response = MagicMock()
                response.choices = [MagicMock()]
                response.choices[0].message.content = content
                response.usage.total_tokens = 150
                response.usage.prompt_tokens = 100
                response.usage.completion_tokens = 50
                response.model = model
                return response

            mock_openai.chat.completions.create.return_value = create_openai_response()

            # Mock DuckDuckGo with multiple results
            mock_ddg_instance = MagicMock()
            mock_ddg_instance.text.return_value = [
                MagicMock(title="Result 1", body="Search result 1", href="http://example1.com"),
                MagicMock(title="Result 2", body="Search result 2", href="http://example2.com"),
                MagicMock(title="Result 3", body="Search result 3", href="http://example3.com"),
            ]
            mock_ddg.return_value = mock_ddg_instance

            yield {
                "redis": mock_redis,
                "redis_stack": mock_redis_stack,
                "openai": mock_openai,
                "ddg": mock_ddg,
            }

    def test_fork_join_workflow(self, setup_advanced_mocks):
        """Test fork_join.yaml workflow for parallel processing."""
        fork_join_path = Path("examples/fork_join.yaml")
        if not fork_join_path.exists():
            pytest.skip("fork_join.yaml not found")

        orchestrator = Orchestrator(str(fork_join_path))

        # Verify fork and join nodes exist
        fork_nodes = [
            agent
            for agent_id, agent in orchestrator.agents.items()
            if agent.__class__.__name__ == "ForkNode"
        ]
        join_nodes = [
            agent
            for agent_id, agent in orchestrator.agents.items()
            if agent.__class__.__name__ == "JoinNode"
        ]

        assert len(fork_nodes) > 0, "No fork nodes found in fork_join workflow"
        assert len(join_nodes) > 0, "No join nodes found in fork_join workflow"

        # Verify they have proper configuration
        for fork_node in fork_nodes:
            assert hasattr(fork_node, "targets")

        for join_node in join_nodes:
            assert hasattr(join_node, "group_id")

    def test_memory_operations_workflow(self, setup_advanced_mocks):
        """Test memory read/write operations in workflows."""
        memory_path = Path("examples/basic_memory.yml")
        orchestrator = Orchestrator(str(memory_path))

        # Find memory nodes
        memory_nodes = [
            agent for agent_id, agent in orchestrator.agents.items() if "memory" in agent_id.lower()
        ]

        assert len(memory_nodes) >= 2, "Expected at least 2 memory nodes (read/write)"

        # Verify memory configuration
        for memory_node in memory_nodes:
            # Memory nodes should have either namespace or node_id
            assert hasattr(memory_node, "namespace") or hasattr(memory_node, "node_id")

    def test_enhanced_memory_validation_workflow(self, setup_advanced_mocks):
        """Test enhanced memory validation example."""
        enhanced_path = Path("examples/enhanced_memory_validation_example.yml")
        if not enhanced_path.exists():
            pytest.skip("enhanced_memory_validation_example.yml not found")

        orchestrator = Orchestrator(str(enhanced_path))

        # Should have comprehensive agent types
        agent_types = set()
        for agent in orchestrator.agents.values():
            agent_types.add(agent.__class__.__name__)

        # Should include various agent types for validation
        expected_types = ["OpenAIAnswerBuilder", "OpenAIBinaryAgent", "OpenAIClassificationAgent"]
        found_types = [t for t in expected_types if any(expected in t for expected in agent_types)]
        assert len(found_types) > 0, f"Expected validation agents, got types: {agent_types}"

    def test_routing_memory_writers_workflow(self, setup_advanced_mocks):
        """Test routing memory writers example."""
        routing_path = Path("examples/routing_memory_writers.yml")
        if not routing_path.exists():
            pytest.skip("routing_memory_writers.yml not found")

        orchestrator = Orchestrator(str(routing_path))

        # Should have router nodes
        router_nodes = [
            agent
            for agent_id, agent in orchestrator.agents.items()
            if agent.__class__.__name__ == "RouterNode"
        ]

        # Should have memory writer nodes
        memory_writers = [
            agent
            for agent_id, agent in orchestrator.agents.items()
            if "memory" in agent_id.lower() and "write" in agent_id.lower()
        ]

        assert len(router_nodes) > 0, "No router nodes found"
        assert len(memory_writers) > 0, "No memory writer nodes found"

    def test_local_llm_workflow_structure(self, setup_advanced_mocks):
        """Test local LLM workflow structure."""
        local_llm_path = Path("examples/local_llm.yml")
        if not local_llm_path.exists():
            pytest.skip("local_llm.yml not found")

        # This test just verifies the structure loads without errors
        orchestrator = Orchestrator(str(local_llm_path))

        # Should have agents configured
        assert len(orchestrator.agents) > 0

        # Should have orchestrator configuration
        assert "id" in orchestrator.orchestrator_cfg
        assert "strategy" in orchestrator.orchestrator_cfg

    def test_memory_decay_workflow(self, setup_advanced_mocks):
        """Test memory decay example workflow."""
        decay_path = Path("examples/memory_decay_example.yml")
        if not decay_path.exists():
            pytest.skip("memory_decay_example.yml not found")

        orchestrator = Orchestrator(str(decay_path))

        # Should have memory-related agents
        memory_agents = [
            agent_id for agent_id in orchestrator.agents.keys() if "memory" in agent_id.lower()
        ]

        assert len(memory_agents) > 0, "No memory agents found in decay workflow"

    def test_validation_structuring_workflow(self, setup_advanced_mocks):
        """Test validation and structuring orchestrator workflow."""
        validation_path = Path("examples/validation_and_structuring_orchestrator.yml")
        if not validation_path.exists():
            pytest.skip("validation_and_structuring_orchestrator.yml not found")

        orchestrator = Orchestrator(str(validation_path))

        # Should have validation-related agents
        validation_agents = [
            agent
            for agent_id, agent in orchestrator.agents.items()
            if "validation" in agent_id.lower()
            or agent.__class__.__name__ in ["OpenAIBinaryAgent", "OpenAIClassificationAgent"]
        ]

        assert len(validation_agents) > 0, "No validation agents found"

    def test_workflow_agent_connectivity(self, setup_advanced_mocks):
        """Test that agents in workflows are properly connected."""
        example_files = [
            "examples/example.yml",
            "examples/complex_flow.yml",
            "examples/basic_memory.yml",
        ]

        for example_file in example_files:
            if Path(example_file).exists():
                orchestrator = Orchestrator(example_file)

                # Every workflow should have at least one agent
                assert len(orchestrator.agents) > 0, f"No agents in {example_file}"

                # Agents should have proper identifiers
                for agent_id, agent in orchestrator.agents.items():
                    assert agent_id is not None, f"Agent has no ID in {example_file}"
                    # Agents have various identifier attributes depending on type
                    has_identifier = (
                        hasattr(agent, "node_id")
                        or hasattr(agent, "agent_id")
                        or hasattr(agent, "tool_id")
                        or hasattr(agent, "id")
                    )
                    assert has_identifier, f"Agent {agent_id} missing identifier in {example_file}"

    def test_workflow_error_handling(self, setup_advanced_mocks):
        """Test error handling in workflows with failover nodes."""
        failover_path = Path("examples/failover.yml")
        orchestrator = Orchestrator(str(failover_path))

        # Should have failover nodes
        failover_nodes = [
            agent
            for agent_id, agent in orchestrator.agents.items()
            if agent.__class__.__name__ == "FailoverNode"
        ]

        assert len(failover_nodes) > 0, "No failover nodes found"

        # Failover nodes should have children
        for failover_node in failover_nodes:
            assert hasattr(failover_node, "children") or hasattr(failover_node, "child_agents")

    def test_memory_category_workflow(self, setup_advanced_mocks):
        """Test memory category workflow."""
        category_path = Path("examples/memory_category_test.yml")
        if not category_path.exists():
            pytest.skip("memory_category_test.yml not found")

        orchestrator = Orchestrator(str(category_path))

        # Should have memory operations
        memory_agents = [
            agent_id for agent_id in orchestrator.agents.keys() if "memory" in agent_id.lower()
        ]

        assert len(memory_agents) > 0, "No memory agents in category test"

    def test_workflow_configuration_completeness(self, setup_advanced_mocks):
        """Test that all workflow configurations are complete."""
        example_files = [
            "examples/example.yml",
            "examples/complex_flow.yml",
            "examples/basic_memory.yml",
            "examples/failover.yml",
        ]

        for example_file in example_files:
            if Path(example_file).exists():
                orchestrator = Orchestrator(example_file)

                # Should have orchestrator configuration
                assert "id" in orchestrator.orchestrator_cfg
                assert "strategy" in orchestrator.orchestrator_cfg
                assert "agents" in orchestrator.orchestrator_cfg

                # Agents list should not be empty
                assert len(orchestrator.orchestrator_cfg["agents"]) > 0

                # All agents in the list should exist
                for agent_id in orchestrator.orchestrator_cfg["agents"]:
                    assert agent_id in orchestrator.agents, (
                        f"Agent {agent_id} listed but not found in {example_file}"
                    )

    def test_complex_agent_interactions(self, setup_advanced_mocks):
        """Test complex agent interaction patterns."""
        complex_path = Path("examples/complex_flow.yml")
        orchestrator = Orchestrator(str(complex_path))

        # Should have different types of agents working together
        agent_types = {}
        for agent_id, agent in orchestrator.agents.items():
            agent_type = agent.__class__.__name__
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1

        # Should have at least 3 different types of agents
        assert len(agent_types) >= 3, f"Expected diverse agent types, got: {agent_types}"

        # Should include both LLM and tool agents
        has_llm = any("OpenAI" in agent_type for agent_type in agent_types)
        has_tools = any("Tool" in agent_type for agent_type in agent_types)
        has_nodes = any("Node" in agent_type for agent_type in agent_types)

        assert has_llm, "No LLM agents found"
        assert has_tools or has_nodes, "No tool/node agents found"
