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

    @pytest.mark.asyncio
    async def test_run_returns_orka_response(self):
        """Test that run() returns OrkaResponse with list in result field."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1", "agent2"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        input_data = {
            "previous_outputs": {
                "classifier": "true"
            }
        }
        
        # Call run() instead of _run_impl() to test the full response wrapping
        response = await node.run(input_data)
        
        # Verify OrkaResponse structure
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert response["component_id"] == "router"
        assert response["component_type"] == "node"
        assert "timestamp" in response
        
        # Verify the result contains the routed agents
        assert isinstance(response["result"], list)
        assert response["result"] == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_run_with_dict_decision_returns_orka_response(self):
        """Test run() with dict decision value returns proper OrkaResponse."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        input_data = {
            "previous_outputs": {
                "classifier": {"response": "true", "confidence": "0.95"}
            }
        }
        
        response = await node.run(input_data)
        
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert response["result"] == ["agent1"]

    @pytest.mark.asyncio
    async def test_run_no_match_returns_empty_list_in_orka_response(self):
        """Test run() with no matching route returns OrkaResponse with empty list."""
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
        
        response = await node.run(input_data)
        
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert response["result"] == []

    @pytest.mark.asyncio
    async def test_run_impl_verbose_response_with_true(self):
        """Test _run_impl extracts 'true' from verbose LLM response."""
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
                "classifier": "Based on the analysis, the answer is true because the data is coherent."
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent1"]

    @pytest.mark.asyncio
    async def test_run_impl_verbose_response_with_false(self):
        """Test _run_impl extracts 'false' from verbose LLM response."""
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
                "classifier": "The provided information is not coherent and complete.\n\nHere's why:\n1. Missing context\n2. Incomplete data\n\nTherefore, the answer is false."
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent2"]

    @pytest.mark.asyncio
    async def test_run_impl_verbose_response_with_yes(self):
        """Test _run_impl extracts 'yes' from verbose response and maps to true."""
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
                "classifier": "After careful consideration, yes, this is correct."
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent1"]

    @pytest.mark.asyncio
    async def test_run_impl_verbose_response_with_no(self):
        """Test _run_impl extracts 'no' from verbose response and maps to false."""
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
                "classifier": "Upon review, no, this doesn't meet the criteria."
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent2"]

    @pytest.mark.asyncio
    async def test_run_impl_verbose_response_with_both_keywords(self):
        """Test _run_impl returns empty list when both true and false appear in response."""
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
                "classifier": "It's true that we have data, but false that it's complete."
            }
        }
        
        result = await node._run_impl(input_data)
        
        # When both keywords present, should not match either route
        assert result == []

    @pytest.mark.asyncio
    async def test_run_impl_case_insensitive_keyword_extraction(self):
        """Test _run_impl keyword extraction is case-insensitive."""
        params = {
            "decision_key": "classifier",
            "routing_map": {
                "true": ["agent1"],
                "false": ["agent2"],
            }
        }
        node = RouterNode(node_id="router", params=params)
        
        # Test various case combinations
        test_cases = [
            ("The answer is TRUE", ["agent1"]),
            ("Response: FALSE", ["agent2"]),
            ("Yes, that's correct", ["agent1"]),
            ("No way!", ["agent2"]),
        ]
        
        for response_text, expected_route in test_cases:
            input_data = {
                "previous_outputs": {
                    "classifier": response_text
                }
            }
            result = await node._run_impl(input_data)
            assert result == expected_route, f"Failed for: {response_text}"

    @pytest.mark.asyncio
    async def test_run_impl_dict_with_verbose_response(self):
        """Test _run_impl extracts keyword from dict response field."""
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
                "classifier": {
                    "response": "After analysis, the result is true.",
                    "confidence": "0.9"
                }
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result == ["agent1"]


