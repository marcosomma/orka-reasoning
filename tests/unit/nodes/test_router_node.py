"""Unit tests for orka.nodes.router_node."""

from unittest.mock import Mock

import pytest

from orka.nodes.router_node import RouterNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestRouterNode:
    """Test suite for RouterNode class."""

    def test_init(self):
        """Test RouterNode initialization."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1"],
                "false": ["agent2"],
            }
        }
        
        node = RouterNode(node_id="router", params=params)
        
        assert node.node_id == "router"
        assert node.params == params

    def test_init_missing_params(self):
        """Test RouterNode initialization without params raises ValueError."""
        with pytest.raises(ValueError, match="RouterAgent requires 'params'"):
            RouterNode(node_id="router", params=None)

    @pytest.mark.asyncio
    async def test_run_impl_string_match(self):
        """Test _run_impl with string decision value."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1"],
                "false": ["agent2"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        input_data = {
            "previous_outputs": {
                "classifier": "true"
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent1"]

    @pytest.mark.asyncio
    async def test_run_impl_boolean_match(self):
        """Test _run_impl with boolean decision value."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                True: ["agent1"],
                False: ["agent2"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        input_data = {
            "previous_outputs": {
                "classifier": True
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent1"]

    @pytest.mark.asyncio
    async def test_run_impl_dict_decision_value(self):
        """Test _run_impl with dict decision value."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        input_data = {
            "previous_outputs": {
                "classifier": {"response": "true"}
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent1"]

    @pytest.mark.asyncio
    async def test_run_impl_no_match(self):
        """Test _run_impl when no route matches."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        input_data = {
            "previous_outputs": {
                "classifier": "unknown"
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == []

    def test_bool_key_true(self):
        """Test _bool_key with true values."""
        node = RouterNode(node_id="router", params={"decision_key": "test", "routing_map": {}})
        
        assert node._bool_key("true") is True
        assert node._bool_key("yes") is True
        assert node._bool_key("1") is True

    def test_bool_key_false(self):
        """Test _bool_key with false values."""
        node = RouterNode(node_id="router", params={"decision_key": "test", "routing_map": {}})
        
        assert node._bool_key("false") is False
        assert node._bool_key("no") is False
        assert node._bool_key("0") is False

    def test_bool_key_other(self):
        """Test _bool_key with other values."""
        node = RouterNode(node_id="router", params={"decision_key": "test", "routing_map": {}})
        
        assert node._bool_key("maybe") == "maybe"
        assert node._bool_key("unknown") == "unknown"

