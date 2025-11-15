"""Unit tests for orka.orchestrator.graph_introspection."""

from unittest.mock import Mock, AsyncMock

import pytest

from orka.orchestrator.graph_introspection import GraphIntrospector
from orka.orchestrator.graph_api import GraphState, NodeDescriptor, EdgeDescriptor

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestGraphIntrospector:
    """Test suite for GraphIntrospector class."""

    def create_mock_config(self):
        """Helper to create mock config."""
        config = Mock()
        config.max_depth = 4
        config.k_beam = 3
        return config

    def create_mock_graph_state(self):
        """Helper to create mock graph state."""
        nodes = {
            "agent1": NodeDescriptor(
                id="agent1",
                type="LocalLLMAgent",
                prompt_summary="Agent 1",
                capabilities=["text_generation"],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            ),
            "agent2": NodeDescriptor(
                id="agent2",
                type="SearchAgent",
                prompt_summary="Agent 2",
                capabilities=["web_search"],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            ),
        }
        edges = [
            EdgeDescriptor(src="agent1", dst="agent2", weight=1.0),
        ]
        return GraphState(
            nodes=nodes,
            edges=edges,
            current_node="agent1",
            visited_nodes=set(),
            runtime_state={},
            budgets={},
            constraints={},
        )

    def test_init(self):
        """Test GraphIntrospector initialization."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        assert introspector.config == config
        assert introspector.max_depth == 4
        assert introspector.k_beam == 3

    def test_init_default_max_depth(self):
        """Test GraphIntrospector initialization with default max_depth."""
        config = Mock()
        config.k_beam = 3
        del config.max_depth  # Remove max_depth attribute
        
        introspector = GraphIntrospector(config)
        
        assert introspector.max_depth == 4  # Default value

    def test_filter_memory_agents_from_candidates(self):
        """Test _filter_memory_agents_from_candidates method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        # Add memory agent to graph state
        graph_state.nodes["memory_reader"] = NodeDescriptor(
            id="memory_reader",
            type="MemoryReaderNode",
            prompt_summary="Memory reader",
            capabilities=["memory_read"],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = ["agent2", "memory_reader"]
        
        filtered = introspector._filter_memory_agents_from_candidates(neighbors, graph_state)
        
        assert "memory_reader" not in filtered
        assert "agent2" in filtered

    def test_filter_control_flow_agents_from_candidates(self):
        """Test _filter_control_flow_agents_from_candidates method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        # Add control flow agent
        graph_state.nodes["validator"] = NodeDescriptor(
            id="validator",
            type="PlanValidatorAgent",
            prompt_summary="Validator",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = ["agent2", "validator"]
        
        filtered = introspector._filter_control_flow_agents_from_candidates(neighbors, graph_state)
        
        assert "validator" not in filtered
        assert "agent2" in filtered

    def test_is_memory_agent(self):
        """Test _is_memory_agent method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["memory_reader"] = NodeDescriptor(
            id="memory_reader",
            type="MemoryReaderNode",
            prompt_summary="Memory reader",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        assert introspector._is_memory_agent("memory_reader", graph_state) is True
        assert introspector._is_memory_agent("agent1", graph_state) is False

    def test_get_memory_operation(self):
        """Test _get_memory_operation method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["memory_reader"] = NodeDescriptor(
            id="memory_reader",
            type="MemoryReaderNode",
            prompt_summary="Memory reader",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        operation = introspector._get_memory_operation("memory_reader", graph_state)
        
        assert operation == "read"

    @pytest.mark.asyncio
    async def test_discover_paths(self):
        """Test discover_paths method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        question = "Test question"
        context = {}
        
        paths = await introspector.discover_paths(graph_state, question, context)
        
        assert isinstance(paths, list)

    def test_get_eligible_neighbors(self):
        """Test _get_eligible_neighbors method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        neighbors = introspector._get_eligible_neighbors("agent1", graph_state, set())
        
        assert isinstance(neighbors, list)

    def test_check_edge_condition(self):
        """Test _check_edge_condition method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        edge = EdgeDescriptor(src="agent1", dst="agent2", condition=None)
        
        result = introspector._check_edge_condition(edge, graph_state)
        
        assert result is True  # No condition means always pass

    @pytest.mark.asyncio
    async def test_explore_from_node(self):
        """Test _explore_from_node method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        paths = await introspector._explore_from_node(graph_state, "agent1", set(), ["agent1"], 1)
        
        assert isinstance(paths, list)

    def test_get_graph_neighbors(self):
        """Test _get_graph_neighbors method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        neighbors = introspector._get_graph_neighbors(graph_state, "agent1", set())
        
        assert isinstance(neighbors, list)
        assert "agent2" in neighbors

    def test_is_graphscout_node(self):
        """Test _is_graphscout_node method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["graphscout"] = NodeDescriptor(
            id="graphscout",
            type="GraphScoutAgent",
            prompt_summary="GraphScout",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        assert introspector._is_graphscout_node(graph_state, "graphscout") is True
        assert introspector._is_graphscout_node(graph_state, "agent1") is False

    def test_is_response_builder_node(self):
        """Test _is_response_builder_node method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["response_builder"] = NodeDescriptor(
            id="response_builder",
            type="LocalLLMAgent",
            prompt_summary="Response builder",
            capabilities=["text_generation", "response_generation"],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        assert introspector._is_response_builder_node(graph_state, "response_builder") is True
        assert introspector._is_response_builder_node(graph_state, "agent1") is False

    def test_check_path_feasibility(self):
        """Test _check_path_feasibility method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        candidate = {
            "path": ["agent1", "agent2"],
            "node_id": "agent2",
        }
        
        result = introspector._check_path_feasibility(candidate, graph_state)
        
        assert isinstance(result, bool)

    def test_check_join_feasibility(self):
        """Test _check_join_feasibility method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        candidate = {
            "path": ["agent1", "agent2"],
        }
        
        result = introspector._check_join_feasibility(candidate, graph_state)
        
        assert isinstance(result, bool)

    def test_check_resource_constraints(self):
        """Test _check_resource_constraints method."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.budgets = {"max_cost": 0.1}
        candidate = {
            "estimated_cost": 0.05,
        }
        
        result = introspector._check_resource_constraints(candidate, graph_state)
        
        assert isinstance(result, bool)

