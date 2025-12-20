# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for MemoryProcessingMixin."""

import pytest

from orka.memory.base_logger_mixins.memory_processing_mixin import MemoryProcessingMixin


class ConcreteMemoryProcessing(MemoryProcessingMixin):
    """Concrete implementation for testing."""

    def __init__(self, debug_keep_previous_outputs=False):
        self.debug_keep_previous_outputs = debug_keep_previous_outputs
        self._redis_data = {}

    def hkeys(self, name):
        return list(self._redis_data.get(name, {}).keys())

    def hget(self, name, key):
        return self._redis_data.get(name, {}).get(key)

    def hset(self, name, key, value):
        if name not in self._redis_data:
            self._redis_data[name] = {}
        self._redis_data[name][key] = value
        return 1

    def set(self, key, value):
        self._redis_data[key] = value
        return True


class TestMemoryProcessingMixin:
    """Tests for MemoryProcessingMixin.
    
    Note: _process_memory_for_saving and _sanitize_for_json are provided by
    SerializationMixin and tested there.
    """

    @pytest.fixture
    def processor(self):
        return ConcreteMemoryProcessing()

    def test_build_previous_outputs_from_logs(self, processor):
        """Test building outputs from logs."""
        logs = [
            {"agent_id": "agent1", "payload": {"result": "output1"}},
            {"agent_id": "agent2", "payload": {"response": "answer"}},
        ]
        result = processor._build_previous_outputs(logs)

        assert "agent1" in result
        assert "agent2" in result

    def test_build_previous_outputs_merged_dict(self, processor):
        """Test merged dict handling."""
        logs = [
            {
                "agent_id": "join_node",
                "payload": {"result": {"merged": {"a": 1, "b": 2}}},
            }
        ]
        result = processor._build_previous_outputs(logs)

        assert "a" in result
        assert "b" in result

    def test_build_previous_outputs_memories(self, processor):
        """Test memories handling."""
        logs = [
            {
                "agent_id": "memory_reader",
                "payload": {"memories": [{"content": "test"}], "query": "search"},
            }
        ]
        result = processor._build_previous_outputs(logs)

        assert "memories" in result["memory_reader"]
        assert result["memory_reader"]["query"] == "search"

    def test_build_previous_outputs_response_format(self, processor):
        """Test response format extraction."""
        logs = [
            {
                "agent_id": "llm_agent",
                "payload": {
                    "response": "LLM answer",
                    "confidence": "0.9",
                    "_metrics": {"tokens": 100},
                },
            }
        ]
        result = processor._build_previous_outputs(logs)

        assert result["llm_agent"]["response"] == "LLM answer"
        assert result["llm_agent"]["confidence"] == "0.9"
        assert result["llm_agent"]["_metrics"]["tokens"] == 100

    def test_build_previous_outputs_empty_logs(self, processor):
        """Test with empty logs."""
        result = processor._build_previous_outputs([])
        assert result == {}

    def test_build_previous_outputs_stores_in_redis(self, processor):
        """Test that results are stored in Redis."""
        logs = [{"agent_id": "test_agent", "payload": {"result": "test_output"}}]
        processor._build_previous_outputs(logs)

        # Check that result was stored
        assert "agent_result:test_agent" in processor._redis_data
        assert "agent_results" in processor._redis_data
        assert "test_agent" in processor._redis_data["agent_results"]
