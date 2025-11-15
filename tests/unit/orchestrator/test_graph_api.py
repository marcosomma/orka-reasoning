"""Unit tests for orka.orchestrator.graph_api."""

from unittest.mock import Mock

import pytest

from orka.orchestrator.graph_api import (
    EdgeDescriptor,
    GraphAPI,
    GraphState,
    NodeDescriptor,
)

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestNodeDescriptor:
    """Test suite for NodeDescriptor dataclass."""

    def test_node_descriptor_creation(self):
        """Test NodeDescriptor creation."""
        node = NodeDescriptor(
            id="test_node",
            type="LocalLLMAgent",
            prompt_summary="Test prompt",
            capabilities=["text_generation"],
            contract={},
            cost_model={"base_cost": 0.001},
            safety_tags=["safe"],
            metadata={},
        )
        assert node.id == "test_node"
        assert node.type == "LocalLLMAgent"
        assert node.capabilities == ["text_generation"]


class TestEdgeDescriptor:
    """Test suite for EdgeDescriptor dataclass."""

    def test_edge_descriptor_creation(self):
        """Test EdgeDescriptor creation."""
        edge = EdgeDescriptor(
            src="node1",
            dst="node2",
            condition={"key": "value"},
            weight=0.8,
            metadata={"meta": "data"},
        )
        assert edge.src == "node1"
        assert edge.dst == "node2"
        assert edge.weight == 0.8
        assert edge.condition == {"key": "value"}

    def test_edge_descriptor_default_metadata(self):
        """Test EdgeDescriptor with default metadata."""
        edge = EdgeDescriptor(src="node1", dst="node2")
        assert edge.metadata == {}


class TestGraphState:
    """Test suite for GraphState dataclass."""

    def test_graph_state_creation(self):
        """Test GraphState creation."""
        nodes = {
            "node1": NodeDescriptor(
                id="node1",
                type="LocalLLMAgent",
                prompt_summary="Test",
                capabilities=[],
                contract={},
                cost_model={},
                safety_tags=[],
                metadata={},
            )
        }
        edges = [EdgeDescriptor(src="node1", dst="node2")]

        state = GraphState(
            nodes=nodes,
            edges=edges,
            current_node="node1",
            visited_nodes={"node1"},
            runtime_state={"run_id": "test"},
            budgets={"max_cost": 0.1},
            constraints={},
        )
        assert len(state.nodes) == 1
        assert len(state.edges) == 1
        assert state.current_node == "node1"


class TestGraphAPI:
    """Test suite for GraphAPI class."""

    def test_init(self):
        """Test GraphAPI initialization."""
        api = GraphAPI()
        assert api.cache == {}

    @pytest.mark.asyncio
    async def test_get_graph_state(self):
        """Test get_graph_state method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {
            "agent1": Mock(
                type="local_llm",
                __class__=Mock(__name__="LocalLLMAgent"),
                prompt="Test prompt",
                capabilities=["text_generation"],
                contract={},
                cost_model={"base_cost": 0.001},
                safety_tags=["safe"],
            )
        }
        mock_orchestrator.orchestrator_cfg = {
            "agents": ["agent1", "agent2"],
            "budget": {"max_cost": 0.1},
        }
        mock_orchestrator.step_index = 0
        mock_orchestrator.queue = ["agent1"]

        state = await api.get_graph_state(mock_orchestrator, "test_run_id")

        assert isinstance(state, GraphState)
        assert "agent1" in state.nodes

    @pytest.mark.asyncio
    async def test_extract_nodes(self):
        """Test _extract_nodes method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {
            "agent1": Mock(
                type="local_llm",
                __class__=Mock(__name__="LocalLLMAgent"),
                prompt="Test prompt",
                capabilities=["text_generation"],
                contract={},
                cost_model={},
                safety_tags=[],
            )
        }

        nodes = await api._extract_nodes(mock_orchestrator)

        assert "agent1" in nodes
        assert isinstance(nodes["agent1"], NodeDescriptor)

    @pytest.mark.asyncio
    async def test_extract_nodes_no_agents(self):
        """Test _extract_nodes when orchestrator has no agents."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        del mock_orchestrator.agents  # Remove agents attribute

        nodes = await api._extract_nodes(mock_orchestrator)

        assert nodes == {}

    @pytest.mark.asyncio
    async def test_build_edges(self):
        """Test _build_edges method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.orchestrator_cfg = {
            "agents": ["agent1", "agent2", "agent3"],
        }

        edges = await api._build_edges(mock_orchestrator)

        assert isinstance(edges, list)
        # Should create edges between consecutive agents
        assert len(edges) >= 2

    @pytest.mark.asyncio
    async def test_get_current_node(self):
        """Test _get_current_node method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.queue = ["agent1", "agent2"]
        mock_orchestrator.step_index = 0

        current = await api._get_current_node(mock_orchestrator, "test_run_id")

        assert current == "agent1"

    @pytest.mark.asyncio
    async def test_get_current_node_empty_queue(self):
        """Test _get_current_node with empty queue."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.queue = []

        current = await api._get_current_node(mock_orchestrator, "test_run_id")

        assert current == "unknown"

    @pytest.mark.asyncio
    async def test_get_visited_nodes(self):
        """Test _get_visited_nodes method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.step_index = 2
        mock_orchestrator.orchestrator_cfg = {
            "agents": ["agent1", "agent2", "agent3"],
        }

        visited = await api._get_visited_nodes(mock_orchestrator, "test_run_id")

        assert isinstance(visited, set)
        assert len(visited) >= 0

    @pytest.mark.asyncio
    async def test_get_runtime_state(self):
        """Test _get_runtime_state method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.step_index = 5
        mock_orchestrator.queue = []
        mock_orchestrator.run_id = "test_run_id"

        state = await api._get_runtime_state(mock_orchestrator, "test_run_id")

        assert isinstance(state, dict)
        assert state["run_id"] == "test_run_id"
        assert state["step_index"] == 5

    @pytest.mark.asyncio
    async def test_get_budgets(self):
        """Test _get_budgets method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.orchestrator_cfg = {
            "budgets": {"max_cost_usd": 0.1, "max_tokens": 1000},
        }

        budgets = await api._get_budgets(mock_orchestrator)

        assert isinstance(budgets, dict)
        assert budgets["max_cost_usd"] == 0.1

    @pytest.mark.asyncio
    async def test_get_budgets_no_budget_config(self):
        """Test _get_budgets when no budget config exists."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.orchestrator_cfg = {}

        budgets = await api._get_budgets(mock_orchestrator)

        assert isinstance(budgets, dict)

    @pytest.mark.asyncio
    async def test_get_constraints(self):
        """Test _get_constraints method."""
        api = GraphAPI()

        mock_orchestrator = Mock()
        mock_orchestrator.orchestrator_cfg = {
            "constraints": {"max_depth": 5},
        }

        constraints = await api._get_constraints(mock_orchestrator)

        assert isinstance(constraints, dict)
        assert constraints["max_depth"] == 5

    def test_extract_prompt_summary(self):
        """Test _extract_prompt_summary method."""
        api = GraphAPI()

        mock_agent = Mock()
        mock_agent.prompt = "This is a test prompt for an agent"

        summary = api._extract_prompt_summary(mock_agent)

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_extract_capabilities(self):
        """Test _extract_capabilities method."""
        api = GraphAPI()

        mock_agent = Mock()
        mock_agent.capabilities = ["text_generation", "reasoning"]

        capabilities = api._extract_capabilities(mock_agent)

        assert capabilities == ["text_generation", "reasoning"]

    def test_extract_capabilities_no_attribute(self):
        """Test _extract_capabilities when agent has no capabilities."""
        api = GraphAPI()

        mock_agent = Mock()
        del mock_agent.capabilities  # Remove attribute

        capabilities = api._extract_capabilities(mock_agent)

        assert capabilities == []

    def test_extract_contract(self):
        """Test _extract_contract method."""
        api = GraphAPI()

        mock_agent = Mock()
        mock_agent.contract = {"input": "str", "output": "str"}

        contract = api._extract_contract(mock_agent)

        assert contract == {"input": "str", "output": "str"}

    def test_extract_cost_model(self):
        """Test _extract_cost_model method."""
        api = GraphAPI()

        mock_agent = Mock()
        mock_agent.cost_model = {"base_cost": 0.001, "per_token": 0.0001}

        cost_model = api._extract_cost_model(mock_agent)

        assert cost_model == {"base_cost": 0.001, "per_token": 0.0001}

    def test_extract_safety_tags(self):
        """Test _extract_safety_tags method."""
        api = GraphAPI()

        mock_agent = Mock()
        mock_agent.safety_tags = ["safe", "verified"]

        tags = api._extract_safety_tags(mock_agent)

        assert tags == ["safe", "verified"]

    def test_extract_metadata(self):
        """Test _extract_metadata method."""
        api = GraphAPI()

        mock_agent = Mock()
        mock_agent.metadata = {"version": "1.0", "author": "test"}

        mock_agent.node_id = "test_node_id"

        metadata = api._extract_metadata(mock_agent)

        assert metadata == {
            "class_name": "Mock",
            "module": "unittest.mock",
            "node_id": "test_node_id",
        }
