"""Unit tests for orka.nodes.satellite_state_writer (SatelliteStateWriter)."""

import pytest

from orka.nodes.satellite_state_writer import SatelliteStateWriter

pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestSatelliteStateWriter:
    """Test suite for SatelliteStateWriter class."""

    def test_init(self):
        """Test SatelliteStateWriter initialization."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[]
        )
        
        assert node.node_id == "sat_writer"
        assert node.prompt == "Write state"
        assert node.type == "satellitestatewriter"

    def test_init_with_role_param(self):
        """Test initialization with role parameter."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="summarizer"
        )
        
        assert node.params.get("role") == "summarizer"

    def test_init_with_policy_version(self):
        """Test initialization with policy_version parameter."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            policy_version="v2"
        )
        
        assert node.params.get("policy_version") == "v2"

    @pytest.mark.asyncio
    async def test_run_impl_with_dict_input(self):
        """Test _run_impl with dictionary input."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="summarizer"
        )
        
        input_data = {
            "summary": "This is a summary",
            "intent": "User wants help"
        }
        
        result = await node._run_impl(input_data)
        
        assert result["agent_id"] == "sat_writer"
        assert result["role"] == "summarizer"
        assert result["state_patch"]["summary"] == "This is a summary"
        assert result["state_patch"]["intent"] == "User wants help"
        assert result["provenance"]["source"] == "summarizer"
        assert result["provenance"]["reason"] == "node_output"
        assert result["provenance"]["evidence_pointers"] == []
        assert result["provenance"]["policy_version"] == "v1"

    @pytest.mark.asyncio
    async def test_run_impl_with_string_input(self):
        """Test _run_impl with string input (creates summary field)."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="intent"
        )
        
        input_data = "This is a plain string input"
        
        result = await node._run_impl(input_data)
        
        assert result["agent_id"] == "sat_writer"
        assert result["role"] == "intent"
        assert result["state_patch"]["summary"] == "This is a plain string input"
        assert len(result["state_patch"]) == 1
        assert result["provenance"]["source"] == "intent"

    @pytest.mark.asyncio
    async def test_run_impl_with_numeric_input(self):
        """Test _run_impl with numeric input (converted to string)."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="generic"
        )
        
        input_data = 42
        
        result = await node._run_impl(input_data)
        
        assert result["state_patch"]["summary"] == "42"
        assert result["role"] == "generic"

    @pytest.mark.asyncio
    async def test_run_impl_with_none_input(self):
        """Test _run_impl with None input (converted to string)."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[]
        )
        
        input_data = None
        
        result = await node._run_impl(input_data)
        
        assert result["state_patch"]["summary"] == "None"
        assert result["role"] == "generic"

    @pytest.mark.asyncio
    async def test_run_impl_with_list_input(self):
        """Test _run_impl with list input (converted to string)."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="compliance"
        )
        
        input_data = ["item1", "item2", "item3"]
        
        result = await node._run_impl(input_data)
        
        assert "item1" in result["state_patch"]["summary"]
        assert "item2" in result["state_patch"]["summary"]
        assert result["role"] == "compliance"

    @pytest.mark.asyncio
    async def test_run_impl_with_empty_dict(self):
        """Test _run_impl with empty dictionary."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[]
        )
        
        input_data = {}
        
        result = await node._run_impl(input_data)
        
        assert result["state_patch"] == {}
        assert result["role"] == "generic"

    @pytest.mark.asyncio
    async def test_run_impl_with_nested_dict_values(self):
        """Test _run_impl with nested dictionary values (converted to strings)."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[]
        )
        
        input_data = {
            "field1": {"nested": "value"},
            "field2": [1, 2, 3]
        }
        
        result = await node._run_impl(input_data)
        
        assert "nested" in result["state_patch"]["field1"]
        assert "value" in result["state_patch"]["field1"]
        assert "1" in result["state_patch"]["field2"]

    @pytest.mark.asyncio
    async def test_run_impl_with_custom_policy_version(self):
        """Test _run_impl with custom policy_version parameter."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            policy_version="v3"
        )
        
        input_data = "Test input"
        
        result = await node._run_impl(input_data)
        
        assert result["provenance"]["policy_version"] == "v3"

    @pytest.mark.asyncio
    async def test_run_impl_default_role(self):
        """Test _run_impl uses 'generic' as default role."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[]
        )
        
        input_data = "Test"
        
        result = await node._run_impl(input_data)
        
        assert result["role"] == "generic"
        assert result["provenance"]["source"] == "generic"

    @pytest.mark.asyncio
    async def test_run_method_integration(self):
        """Test the full run method (not just _run_impl)."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="summarizer"
        )
        
        input_data = {"key": "value"}
        
        result = await node.run(input_data)
        
        # run() wraps _run_impl with OrkaResponse
        assert result["status"] == "success"
        assert "result" in result
        assert result["result"]["agent_id"] == "sat_writer"
        assert result["result"]["role"] == "summarizer"

    @pytest.mark.asyncio
    async def test_run_impl_multiple_keys(self):
        """Test _run_impl with multiple dictionary keys."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="multi"
        )
        
        input_data = {
            "summary": "Summary text",
            "intent": "Intent text",
            "constraints": "Constraint text",
            "risk": "Risk assessment"
        }
        
        result = await node._run_impl(input_data)
        
        assert len(result["state_patch"]) == 4
        assert result["state_patch"]["summary"] == "Summary text"
        assert result["state_patch"]["intent"] == "Intent text"
        assert result["state_patch"]["constraints"] == "Constraint text"
        assert result["state_patch"]["risk"] == "Risk assessment"

    @pytest.mark.asyncio
    async def test_run_impl_provenance_structure(self):
        """Test that provenance structure is complete."""
        node = SatelliteStateWriter(
            node_id="sat_writer",
            prompt="Write state",
            queue=[],
            role="test_role"
        )
        
        result = await node._run_impl("test")
        
        prov = result["provenance"]
        assert "source" in prov
        assert "reason" in prov
        assert "evidence_pointers" in prov
        assert "policy_version" in prov
        assert prov["source"] == "test_role"
        assert prov["reason"] == "node_output"
        assert isinstance(prov["evidence_pointers"], list)
        assert len(prov["evidence_pointers"]) == 0
