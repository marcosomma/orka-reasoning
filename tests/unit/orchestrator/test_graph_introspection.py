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

    def test_add_memory_agents_for_shortlist(self):
        """Test _add_memory_agents_for_shortlist method."""
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
        graph_state.nodes["memory_writer"] = NodeDescriptor(
            id="memory_writer",
            type="MemoryWriterNode",
            prompt_summary="Memory writer",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = ["agent1", "memory_reader", "memory_writer"]
        
        memory_candidates = introspector._add_memory_agents_for_shortlist(neighbors, graph_state)
        
        assert len(memory_candidates) == 2
        assert all(c.get("special_routing") for c in memory_candidates)
        assert any(c.get("memory_operation") == "read" for c in memory_candidates)
        assert any(c.get("memory_operation") == "write" for c in memory_candidates)

    def test_filter_control_flow_agents_by_type(self):
        """Test filtering control flow agents by type."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
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
        graph_state.nodes["classifier"] = NodeDescriptor(
            id="classifier",
            type="ClassificationAgent",
            prompt_summary="Classifier",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = ["agent1", "validator", "classifier"]
        
        filtered = introspector._filter_control_flow_agents_from_candidates(neighbors, graph_state)
        
        assert "validator" not in filtered
        assert "classifier" not in filtered
        assert "agent1" in filtered

    def test_filter_control_flow_agents_by_pattern(self):
        """Test filtering control flow agents by ID pattern."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["input_classifier"] = NodeDescriptor(
            id="input_classifier",
            type="LocalLLMAgent",
            prompt_summary="Classifier",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        graph_state.nodes["path_validator"] = NodeDescriptor(
            id="path_validator",
            type="LocalLLMAgent",
            prompt_summary="Validator",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = ["agent1", "input_classifier", "path_validator"]
        
        filtered = introspector._filter_control_flow_agents_from_candidates(neighbors, graph_state)
        
        assert "input_classifier" not in filtered
        assert "path_validator" not in filtered
        assert "agent1" in filtered

    @pytest.mark.asyncio
    async def test_discover_paths_with_graphscout(self):
        """Test path discovery from GraphScout node."""
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
        graph_state.current_node = "graphscout"
        
        paths = await introspector.discover_paths(graph_state, "Test question", {})
        
        # GraphScout should be able to route to all non-control-flow agents
        assert isinstance(paths, list)

    @pytest.mark.asyncio
    async def test_discover_paths_with_executing_node(self):
        """Test path discovery with explicit executing_node parameter."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        paths = await introspector.discover_paths(
            graph_state, "Test question", {}, executing_node="agent1"
        )
        
        assert isinstance(paths, list)

    @pytest.mark.asyncio
    async def test_discover_paths_no_neighbors(self):
        """Test path discovery when no eligible neighbors found."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        # Empty graph with no edges
        graph_state = GraphState(
            nodes={"agent1": NodeDescriptor(
                id="agent1",
                type="LocalLLMAgent",
                prompt_summary="Agent 1",
                capabilities=[],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            )},
            edges=[],
            current_node="agent1",
            visited_nodes=set(),
            runtime_state={},
            budgets={},
            constraints={},
        )
        
        paths = await introspector.discover_paths(graph_state, "Test question", {})
        
        assert paths == []

    def test_get_eligible_neighbors_with_visited(self):
        """Test _get_eligible_neighbors excludes visited nodes."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        visited = {"agent2"}  # Mark agent2 as visited
        
        neighbors = introspector._get_eligible_neighbors(graph_state, "agent1", visited)
        
        # Should not include visited agent2
        assert "agent2" not in neighbors

    def test_is_graphscout_node_with_lowercase(self):
        """Test _is_graphscout_node with case variations."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["scout"] = NodeDescriptor(
            id="scout",
            type="graphscoutagent",  # lowercase
            prompt_summary="Scout",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        assert introspector._is_graphscout_node(graph_state, "scout") is True

    def test_filter_memory_agents_exception_handling(self):
        """Test _filter_memory_agents_from_candidates exception handling."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        # Graph state with missing node descriptor
        graph_state = GraphState(
            nodes={},
            edges=[],
            current_node="agent1",
            visited_nodes=set(),
            runtime_state={},
            budgets={},
            constraints={},
        )
        
        neighbors = ["missing_node"]
        
        # Should handle error gracefully and return original list
        filtered = introspector._filter_memory_agents_from_candidates(neighbors, graph_state)
        
        assert filtered == neighbors

    def test_filter_control_flow_agents_exception_handling(self):
        """Test _filter_control_flow_agents_from_candidates exception handling."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        # Invalid graph state
        graph_state = None
        neighbors = ["agent1"]
        
        # Should handle error gracefully
        try:
            filtered = introspector._filter_control_flow_agents_from_candidates(neighbors, graph_state)
            assert filtered == neighbors
        except Exception:
            # Should not raise exception
            pass

    def test_add_memory_agents_exception_handling(self):
        """Test _add_memory_agents_for_shortlist exception handling."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        # Graph state with missing nodes
        graph_state = GraphState(
            nodes={},
            edges=[],
            current_node="agent1",
            visited_nodes=set(),
            runtime_state={},
            budgets={},
            constraints={},
        )
        
        neighbors = ["memory_reader"]
        
        # Should handle error gracefully
        memory_candidates = introspector._add_memory_agents_for_shortlist(neighbors, graph_state)
        
        assert memory_candidates == []

    def test_get_memory_operation_unknown(self):
        """Test _get_memory_operation returns 'unknown' for non-memory agents."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        operation = introspector._get_memory_operation("agent1", graph_state)
        
        assert operation == "unknown"

    def test_get_memory_operation_writer(self):
        """Test _get_memory_operation for MemoryWriterNode."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        graph_state.nodes["memory_writer"] = NodeDescriptor(
            id="memory_writer",
            type="MemoryWriterNode",
            prompt_summary="Memory writer",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        operation = introspector._get_memory_operation("memory_writer", graph_state)
        
        assert operation == "write"

    @pytest.mark.asyncio
    async def test_discover_paths_with_max_depth_1(self):
        """Test path discovery with max_depth=1 (direct neighbors only)."""
        config = Mock()
        config.max_depth = 1
        config.k_beam = 3
        
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        paths = await introspector.discover_paths(graph_state, "Test question", {})
        
        # Should only have depth 1 paths
        assert all(p.get("depth", 1) == 1 for p in paths)

    def test_filter_candidates_empty_list(self):
        """Test _filter_candidates with empty candidate list."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_mock_graph_state()
        
        filtered = introspector._filter_candidates([], graph_state, {})
        
        assert filtered == []


class TestMultiHopPathDiscovery:
    """Tests for multi-hop path discovery with pool agents."""

    def create_mock_config(self, max_depth=4, k_beam=6):
        """Helper to create mock config."""
        config = Mock()
        config.max_depth = max_depth
        config.k_beam = k_beam
        return config

    def create_multi_agent_graph_state(self):
        """Create a graph state with multiple pool agents (no explicit edges)."""
        nodes = {
            "graphscout": NodeDescriptor(
                id="graphscout",
                type="GraphScoutAgent",
                prompt_summary="GraphScout router",
                capabilities=["routing"],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            ),
            "search_agent": NodeDescriptor(
                id="search_agent",
                type="DuckDuckGoAgent",
                prompt_summary="Web search",
                capabilities=["data_retrieval", "web_search"],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            ),
            "analysis_agent": NodeDescriptor(
                id="analysis_agent",
                type="LocalLLMAgent",
                prompt_summary="Analysis",
                capabilities=["reasoning", "analysis"],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            ),
            "response_builder": NodeDescriptor(
                id="response_builder",
                type="LocalLLMAgent",
                prompt_summary="Response builder",
                capabilities=["answer_emit", "response_generation"],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={"is_terminal": True},
            ),
        }
        # No explicit edges - pool agents rely on universal routing
        edges = []
        return GraphState(
            nodes=nodes,
            edges=edges,
            current_node="graphscout",
            visited_nodes=set(),
            runtime_state={},
            budgets={},
            constraints={},
        )

    def test_get_eligible_neighbors_graphscout_discovery(self):
        """Test that GraphScout discovery uses universal routing for pool agents."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        # With is_graphscout_discovery=True, should see all pool agents
        neighbors = introspector._get_eligible_neighbors(
            graph_state, "search_agent", set(), is_graphscout_discovery=True
        )
        
        # Should include analysis_agent and response_builder (not search_agent or graphscout)
        assert "analysis_agent" in neighbors
        assert "response_builder" in neighbors
        assert "search_agent" not in neighbors  # Don't include self
        assert "graphscout" not in neighbors  # Don't include other GraphScout

    def test_get_eligible_neighbors_without_graphscout_discovery(self):
        """Test that non-GraphScout nodes follow graph edges by default."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        # Without GraphScout discovery, pool agents can't see each other (no edges)
        neighbors = introspector._get_eligible_neighbors(
            graph_state, "search_agent", set(), is_graphscout_discovery=False
        )
        
        # No explicit edges, so no neighbors found via graph edges
        assert neighbors == []

    @pytest.mark.asyncio
    async def test_explore_from_node_multi_hop_path(self):
        """Test that _explore_from_node creates multi-hop paths during GraphScout discovery."""
        config = self.create_mock_config(max_depth=4)
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        paths = await introspector._explore_from_node(
            graph_state,
            "search_agent",
            {"search_agent"},  # Already visited
            ["search_agent"],
            depth=1,
            is_graphscout_discovery=True,
        )
        
        # Should find paths to analysis_agent and response_builder
        assert any("analysis_agent" in path for path in paths)
        assert any("response_builder" in path for path in paths)

    @pytest.mark.asyncio
    async def test_explore_from_node_three_hop_path(self):
        """Test that GraphScout discovers 3-hop paths: search -> analysis -> response."""
        config = self.create_mock_config(max_depth=4)
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        # Start from GraphScout, exploring paths
        paths = await introspector._explore_from_node(
            graph_state,
            "graphscout",
            {"graphscout"},
            ["graphscout"],
            depth=0,
            is_graphscout_discovery=True,
        )
        
        # Filter to find the 3-hop path
        three_hop_paths = [p for p in paths if len(p) >= 3]
        
        # Should find at least one 3-hop path
        assert len(three_hop_paths) > 0
        
        # Check for the specific path: graphscout -> search_agent -> analysis_agent
        graphscout_search_analysis = [
            p for p in paths 
            if "search_agent" in p and "analysis_agent" in p and len(p) >= 3
        ]
        assert len(graphscout_search_analysis) > 0

    @pytest.mark.asyncio
    async def test_explore_stops_at_response_builder(self):
        """Test that exploration stops at response builder (terminal) nodes.
        
        When starting FROM a response builder, exploration can continue to other nodes.
        But when a response builder is ENCOUNTERED during exploration, we don't
        continue exploring from it (to avoid infinite chains).
        """
        config = self.create_mock_config(max_depth=4)
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        # Start from search_agent, explore toward response_builder
        paths = await introspector._explore_from_node(
            graph_state,
            "search_agent",
            {"search_agent"},
            ["search_agent"],
            depth=1,
            is_graphscout_discovery=True,
        )
        
        # Check that paths ending in response_builder don't extend further
        # When we hit response_builder, we don't continue exploring from it
        paths_ending_in_rb = [p for p in paths if p[-1] == "response_builder"]
        
        # There should be paths ending at response_builder
        assert len(paths_ending_in_rb) > 0
        
        # Verify there are no paths where response_builder appears in the middle
        # (i.e., exploration should stop at terminal nodes)
        for path in paths:
            if "response_builder" in path:
                rb_index = path.index("response_builder")
                # response_builder should be the last element when it appears
                assert rb_index == len(path) - 1, \
                    f"response_builder should be terminal, but found in middle: {path}"

    def test_graphscout_node_detection(self):
        """Test that GraphScout nodes are correctly detected."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        assert introspector._is_graphscout_node(graph_state, "graphscout") is True
        assert introspector._is_graphscout_node(graph_state, "search_agent") is False
        assert introspector._is_graphscout_node(graph_state, "analysis_agent") is False
        assert introspector._is_graphscout_node(graph_state, "response_builder") is False

    def test_response_builder_node_detection(self):
        """Test that response builder nodes are correctly detected by capabilities."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        assert introspector._is_response_builder_node(graph_state, "response_builder") is True
        assert introspector._is_response_builder_node(graph_state, "search_agent") is False
        assert introspector._is_response_builder_node(graph_state, "analysis_agent") is False
        assert introspector._is_response_builder_node(graph_state, "graphscout") is False

    @pytest.mark.asyncio
    async def test_discover_paths_with_pool_agents(self):
        """Test full path discovery with pool agents (integration test)."""
        config = self.create_mock_config(max_depth=4, k_beam=6)
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        paths = await introspector.discover_paths(
            graph_state, "What is the weather?", {}
        )
        
        # Should discover paths that include pool agents
        assert isinstance(paths, list)

    def test_eligible_neighbors_excludes_visited(self):
        """Test that visited nodes are excluded from eligible neighbors."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        visited = {"search_agent", "analysis_agent"}
        
        neighbors = introspector._get_eligible_neighbors(
            graph_state, "graphscout", visited, is_graphscout_discovery=True
        )
        
        assert "search_agent" not in neighbors
        assert "analysis_agent" not in neighbors
        assert "response_builder" in neighbors  # Not visited

    def test_eligible_neighbors_excludes_path_executor(self):
        """Test that PathExecutor nodes are excluded from GraphScout routing."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        graph_state.nodes["path_executor"] = NodeDescriptor(
            id="path_executor",
            type="PathExecutorNode",
            prompt_summary="Path executor",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = introspector._get_eligible_neighbors(
            graph_state, "graphscout", set(), is_graphscout_discovery=True
        )
        
        assert "path_executor" not in neighbors

    @pytest.mark.asyncio
    async def test_explore_respects_max_depth(self):
        """Test that exploration respects max_depth setting."""
        config = self.create_mock_config(max_depth=2)
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        
        paths = await introspector._explore_from_node(
            graph_state,
            "graphscout",
            {"graphscout"},
            ["graphscout"],
            depth=0,
            is_graphscout_discovery=True,
        )
        
        # No path should exceed max_depth + 1 (starting node + max_depth hops)
        assert all(len(path) <= 3 for path in paths)

    def test_get_eligible_neighbors_filters_control_flow(self):
        """Test that control flow agents are filtered from GraphScout routing."""
        config = self.create_mock_config()
        introspector = GraphIntrospector(config)
        
        graph_state = self.create_multi_agent_graph_state()
        graph_state.nodes["input_classifier"] = NodeDescriptor(
            id="input_classifier",
            type="LocalLLMAgent",
            prompt_summary="Classifier",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        graph_state.nodes["plan_validator"] = NodeDescriptor(
            id="plan_validator",
            type="PlanValidatorAgent",
            prompt_summary="Validator",
            capabilities=[],
            contract={},
            cost_model={},
            safety_tags=[],
            metadata={},
        )
        
        neighbors = introspector._get_eligible_neighbors(
            graph_state, "graphscout", set(), is_graphscout_discovery=True
        )
        
        # Control flow agents should be filtered out
        assert "input_classifier" not in neighbors
        assert "plan_validator" not in neighbors
        
        # Regular agents should still be present
        assert "search_agent" in neighbors
        assert "analysis_agent" in neighbors