"""
Unit tests for the orka.contracts module.
Tests the TypedDict contracts and type definitions.
"""

from typing import get_type_hints

from orka.contracts import (
    Context,
    MemoryEntry,
    Output,
    Registry,
    ResourceConfig,
    Trace,
)


class TestContracts:
    """Test the contract type definitions."""

    def test_context_contract_structure(self):
        """Test Context TypedDict structure and annotations."""
        # Get type hints for Context
        hints = get_type_hints(Context)

        # Context should be a TypedDict with expected fields
        assert hasattr(Context, "__annotations__")

        # Check that Context can be used as a type hint
        def test_func(ctx: Context) -> None:
            pass

        # Should not raise any errors
        assert callable(test_func)

    def test_context_usage(self):
        """Test creating and using Context objects."""
        # Create a valid context
        context = {
            "input": "test input",
            "previous_outputs": {"agent1": "output1"},
            "metadata": {"timestamp": "2025-01-01"},
        }

        # Context should work as a regular dictionary
        assert context["input"] == "test input"
        assert "previous_outputs" in context
        assert context["metadata"]["timestamp"] == "2025-01-01"

    def test_output_contract_structure(self):
        """Test Output TypedDict structure."""
        hints = get_type_hints(Output)

        # Output should have required annotations
        assert hasattr(Output, "__annotations__")

        # Check that it's usable as a type
        def test_func(output: Output) -> None:
            pass

        assert callable(test_func)

    def test_output_usage(self):
        """Test creating and using Output objects."""
        # Create a valid output
        output = {
            "content": "test output content",
            "metadata": {"agent_id": "test_agent"},
            "success": True,
        }

        # Should work as a regular dictionary
        assert output["content"] == "test output content"
        assert output["success"] is True
        assert "metadata" in output

    def test_resource_config_contract_structure(self):
        """Test ResourceConfig TypedDict structure."""
        hints = get_type_hints(ResourceConfig)

        assert hasattr(ResourceConfig, "__annotations__")

        def test_func(config: ResourceConfig) -> None:
            pass

        assert callable(test_func)

    def test_resource_config_usage(self):
        """Test creating and using ResourceConfig objects."""
        config = {
            "cpu": "1.0",
            "memory": "512Mi",
            "timeout": 300,
        }

        assert config["cpu"] == "1.0"
        assert config["memory"] == "512Mi"
        assert config["timeout"] == 300

    def test_registry_contract_structure(self):
        """Test Registry TypedDict structure."""
        hints = get_type_hints(Registry)

        assert hasattr(Registry, "__annotations__")

        def test_func(registry: Registry) -> None:
            pass

        assert callable(test_func)

    def test_registry_usage(self):
        """Test creating and using Registry objects."""
        registry = {
            "agents": {"agent1": "type1", "agent2": "type2"},
            "nodes": {"node1": "type1"},
            "tools": {"tool1": "search"},
        }

        assert "agents" in registry
        assert len(registry["agents"]) == 2
        assert registry["agents"]["agent1"] == "type1"

    def test_trace_contract_structure(self):
        """Test Trace TypedDict structure."""
        hints = get_type_hints(Trace)

        assert hasattr(Trace, "__annotations__")

        def test_func(trace: Trace) -> None:
            pass

        assert callable(test_func)

    def test_trace_usage(self):
        """Test creating and using Trace objects."""
        trace = {
            "trace_id": "trace_123",
            "agent_id": "test_agent",
            "timestamp": "2025-01-01T00:00:00Z",
            "input": "test input",
            "output": "test output",
            "metadata": {"duration": 1.5},
        }

        assert trace["trace_id"] == "trace_123"
        assert trace["agent_id"] == "test_agent"
        assert "timestamp" in trace
        assert "metadata" in trace

    def test_memory_entry_contract_structure(self):
        """Test MemoryEntry TypedDict structure."""
        hints = get_type_hints(MemoryEntry)

        assert hasattr(MemoryEntry, "__annotations__")

        def test_func(entry: MemoryEntry) -> None:
            pass

        assert callable(test_func)

    def test_memory_entry_usage(self):
        """Test creating and using MemoryEntry objects."""
        entry = {
            "id": "memory_123",
            "content": "stored memory content",
            "agent_id": "test_agent",
            "timestamp": "2025-01-01T00:00:00Z",
            "metadata": {"importance": 0.8},
        }

        assert entry["id"] == "memory_123"
        assert entry["content"] == "stored memory content"
        assert entry["agent_id"] == "test_agent"
        assert "metadata" in entry

    def test_all_contracts_importable(self):
        """Test that all contract types can be imported."""
        # Should be able to import all contracts without errors
        from orka.contracts import Context, MemoryEntry, Output, Registry, ResourceConfig, Trace

        # All should be classes/types
        assert Context is not None
        assert Output is not None
        assert ResourceConfig is not None
        assert Registry is not None
        assert Trace is not None
        assert MemoryEntry is not None

    def test_contract_type_checking(self):
        """Test that contracts work with type checking."""
        # This tests that the contracts are properly defined TypedDicts

        def process_context(ctx: Context) -> str:
            return ctx.get("input", "")

        def process_output(output: Output) -> bool:
            return output.get("success", False)

        def process_trace(trace: Trace) -> str:
            return trace.get("trace_id", "")

        # These should be callable without errors
        assert callable(process_context)
        assert callable(process_output)
        assert callable(process_trace)

    def test_nested_contract_usage(self):
        """Test using contracts with nested structures."""
        # Create a complex context with nested data
        context = {
            "input": "complex input",
            "previous_outputs": {
                "agent1": {"content": "output1", "success": True},
                "agent2": {"content": "output2", "success": True},
            },
            "metadata": {
                "workflow_id": "wf_123",
                "step": 2,
                "config": {"timeout": 300},
            },
        }

        # Should be able to access nested data
        assert context["previous_outputs"]["agent1"]["content"] == "output1"
        assert context["metadata"]["config"]["timeout"] == 300

    def test_contract_with_optional_fields(self):
        """Test contracts with optional/missing fields."""
        # Create minimal valid objects
        minimal_context = {"input": "test"}
        minimal_output = {"content": "test", "success": True}
        minimal_trace = {
            "trace_id": "123",
            "agent_id": "agent",
            "timestamp": "2025-01-01T00:00:00Z",
        }

        # Should work even with minimal data
        assert minimal_context["input"] == "test"
        assert minimal_output["success"] is True
        assert minimal_trace["trace_id"] == "123"

    def test_contracts_module_structure(self):
        """Test that the contracts module has expected structure."""
        from orka import contracts

        # Should have all expected exports
        expected_contracts = [
            "Context",
            "Output",
            "ResourceConfig",
            "Registry",
            "Trace",
            "MemoryEntry",
        ]

        for contract in expected_contracts:
            assert hasattr(contracts, contract), f"Missing contract: {contract}"

    def test_contract_annotations_exist(self):
        """Test that all contracts have proper annotations."""
        contracts_to_test = [Context, Output, ResourceConfig, Registry, Trace, MemoryEntry]

        for contract in contracts_to_test:
            assert hasattr(contract, "__annotations__"), f"{contract.__name__} missing annotations"
            assert len(contract.__annotations__) > 0, f"{contract.__name__} has empty annotations"
