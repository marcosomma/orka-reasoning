"""Unit tests for orka.nodes.join_node."""

import json
from unittest.mock import Mock, AsyncMock

import pytest

from orka.nodes.join_node import JoinNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestJoinNode:
    """Test suite for JoinNode class."""

    def test_init(self):
        """Test JoinNode initialization."""
        mock_memory = Mock()
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        assert node.node_id == "join_node"
        assert node.group_id == "fork_group_123"
        assert node.max_retries == 30  # Default

    def test_init_custom_max_retries(self):
        """Test JoinNode initialization with custom max_retries."""
        mock_memory = Mock()
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            max_retries=50
        )
        
        assert node.max_retries == 50

    @pytest.mark.asyncio
    async def test_run_impl_all_complete(self):
        """Test _run_impl when all agents have completed."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "0"  # retry count
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        # Mock _complete method
        node._complete = Mock(return_value={"status": "complete", "results": {}})
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "complete"
        mock_memory.hdel.assert_called()

    @pytest.mark.asyncio
    async def test_run_impl_waiting(self):
        """Test _run_impl when agents are still pending."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "0"  # retry count
        mock_memory.hkeys.return_value = ["agent1"]  # Only one received
        mock_memory.smembers.return_value = ["agent1", "agent2"]  # Two expected
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "waiting"
        assert "pending" in result
        assert "agent2" in result["pending"]

    @pytest.mark.asyncio
    async def test_run_impl_timeout(self):
        """Test _run_impl when max retries exceeded."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "30"  # At max retries
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123",
            max_retries=30
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "timeout"
        assert "pending" in result

    def test_complete(self):
        """Test _complete method."""
        mock_memory = Mock()
        mock_memory.hget.return_value = json.dumps({
            "response": "result1",
            "status": "success"
        })
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        assert isinstance(result, dict)
        assert "agent1" in result
        assert "agent2" in result

    def test_complete_logs_memory_with_trace_id(self):
        """Regression: _complete must not reference undefined input_data and should use trace_id when logging."""
        mock_memory = Mock()

        state_key = "waitfor:join_parallel_checks:inputs"
        group_key = "join_results:join_node"

        def hget_side_effect(key, field):
            if key == state_key:
                # Simulate completed agent payload stored in join state
                return json.dumps(
                    {
                        "response": "ok",
                        "status": "done",
                        "confidence": "0.9",
                        "fork_group": "fork_group_123",
                    }
                )
            if key == group_key and field == "result":
                return json.dumps({"status": "done"})
            return None

        mock_memory.hget.side_effect = hget_side_effect
        mock_memory.set = Mock()
        mock_memory.get = Mock(return_value="{}")
        mock_memory.hset = Mock()
        mock_memory.hdel = Mock()
        mock_memory.log_memory = Mock(return_value="orka_memory:test")

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
        )

        fork_targets = ["agent1", "agent2"]

        result = node._complete(fork_targets, state_key, input_data={"trace_id": "trace_123"})

        assert isinstance(result, dict)
        mock_memory.log_memory.assert_called()
        # Ensure our trace_id is used (not join_key fallback)
        assert mock_memory.log_memory.call_args.kwargs["trace_id"] == "trace_123"

    @pytest.mark.asyncio
    async def test_run_impl_find_fork_group_by_pattern(self):
        """Test _run_impl finding fork group by pattern when not in input."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None  # First retry
        mock_memory.scan.return_value = (0, [b"fork_group:test_group_123"])
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group"
        )
        
        # Mock _complete
        node._complete = Mock(return_value={"status": "done"})
        
        result = await node._run_impl({})  # No fork_group_id in input
        
        # Verify scan was called with pattern
        mock_memory.scan.assert_called()
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_pattern_no_matches(self):
        """Test _run_impl when pattern matching finds no fork groups."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None
        mock_memory.scan.return_value = (0, [])  # No matches
        mock_memory.hkeys.return_value = []
        mock_memory.smembers.return_value = ["agent1"]
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group"
        )
        
        result = await node._run_impl({})
        
        # Should return waiting status
        assert result["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_run_impl_uses_mapping_if_scan_fails(self):
        """If scan finds no matches, use explicit mapping key set by ForkNode."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None
        mock_memory.scan.return_value = (0, [])  # No matches
        # mapping exists for join node
        # first hget call (mapping) -> mapped_group_123, second hget (retry count) -> None
        mock_memory.hget.side_effect = ["mapped_group_123", None]
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group",
        )

        node._complete = Mock(return_value={"status": "done"})

        result = await node._run_impl({})

        # Should have used mapping and completed
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_mapping_with_no_targets_waits(self):
        """If mapping recovers a group but smembers returns no targets, join should wait."""
        mock_memory = Mock()
        # retry count missing
        # first hget -> mapped_group_456 (mapping), second hget -> None (retry)
        mock_memory.hget.side_effect = ["mapped_group_456", None]
        mock_memory.scan.return_value = (0, [])
        # mapping exists, but smembers returns empty
        mock_memory.smembers.return_value = []
        mock_memory.hkeys.return_value = ["agent1"]

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group",
        )

        result = await node._run_impl({})

        assert result["status"] == "waiting"
        assert result["message"] == "No expected fork targets yet; waiting for Fork to register targets"

    @pytest.mark.asyncio
    async def test_run_impl_mapping_used_but_state_has_completed_payload_merges(self):
        """If mapping recovers a group but smembers returns no targets, but join state shows a completed payload, join should merge using received."""
        mock_memory = Mock()
        # first hget -> mapped_group_456 (mapping), second hget -> None (retry)
        def hget_side(*args):
            if args == (f"fork_group_mapping:test_group", "group_id"):
                return "mapped_group_456"
            # state entry for agent1 contains a completed payload
            if args == ("waitfor:join_parallel_checks:inputs", "agent1"):
                return json.dumps({"response": "done", "confidence": "0.9", "status": "done", "fork_group": "mapped_group_456"})
            # retry count
            if args == ("join_retry_counts", "join_node:output"):
                return None
            return None

        mock_memory.hget.side_effect = hget_side
        mock_memory.scan.return_value = (0, [])
        mock_memory.smembers.return_value = []
        mock_memory.hkeys.return_value = ["agent1"]

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group",
        )

        node._complete = Mock(return_value={"status": "done"})

        result = await node._run_impl({})

        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_recovers_group_from_state_and_merges(self):
        """When fork_group is missing, derive it from stored agent state and proceed to merge."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None
        mock_memory.scan.return_value = (0, [])
        # state has received keys for 2 agents
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        # first agent's state contains fork_group info
        state_key = "waitfor:join_parallel_checks:inputs"
        mock_memory.hget.side_effect = lambda *args: json.dumps({"fork_group": "fork_from_state"}) if args == (state_key, "agent1") else None

        # smembers for inferred group returns targets
        def smembers_side(key):
            if key == "fork_group:fork_from_state":
                return ["agent1", "agent2"]
            return []

        mock_memory.smembers.side_effect = smembers_side

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group",
        )

        node._complete = Mock(return_value={"status": "done"})

        result = await node._run_impl({})

        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_mapping_used_but_state_points_elsewhere_and_merges(self):
        """If mapping recovers a group but it has no targets, and a received entry points to another group, use that group."""
        mock_memory = Mock()
        # Simulate mapping found first
        def hget_side(*args):
            # mapping lookup
            if args == (f"fork_group_mapping:test_group", "group_id"):
                return "mapped_group_456"
            # retry count
            if args == ("join_retry_counts", "join_node:output"):
                return None
            # state entry for agent1
            if args == ("waitfor:join_parallel_checks:inputs", "agent1"):
                return json.dumps({"fork_group": "actual_group_789"})
            return None

        mock_memory.hget.side_effect = hget_side
        mock_memory.scan.return_value = (0, [])
        mock_memory.hkeys.return_value = ["agent1"]

        # smembers returns empty for mapped_group_456 but returns targets for actual_group_789
        def smembers_side(key):
            if key == "fork_group:mapped_group_456":
                return []
            if key == "fork_group:actual_group_789":
                return ["agent1", "agent2"]
            return []

        mock_memory.smembers.side_effect = smembers_side

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group",
        )

        node._complete = Mock(return_value={"status": "done"})

        result = await node._run_impl({})

        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_falls_back_to_received_when_targets_missing(self):
        """When fork group set is empty, use received inputs as targets to allow merging."""
        mock_memory = Mock()
        # retry count missing
        mock_memory.hget.return_value = None
        mock_memory.scan.return_value = (0, [])
        # no mapping
        # smembers for fork group returns empty
        mock_memory.smembers.return_value = []
        # state has received keys for 2 agents
        mock_memory.hkeys.return_value = ["agent1", "agent2"]

        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group",
        )

        node._complete = Mock(return_value={"status": "done"})

        result = await node._run_impl({})

        # Should have merged using received inputs as targets
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_scan_error(self):
        """Test _run_impl handling scan errors gracefully."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None
        mock_memory.scan.side_effect = Exception("Scan error")
        mock_memory.hkeys.return_value = []
        mock_memory.smembers.return_value = ["agent1"]
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test_group"
        )
        
        result = await node._run_impl({})
        
        # Should handle error and continue
        assert result["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_run_impl_multiple_scan_iterations(self):
        """Test _run_impl with multiple scan iterations."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None
        # Simulate multiple scan calls
        mock_memory.scan.side_effect = [
            (123, [b"fork_group:test_1"]),
            (0, [b"fork_group:test_2"])  # cursor 0 means done
        ]
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = ["agent1"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="test"
        )
        
        node._complete = Mock(return_value={"status": "done"})
        
        result = await node._run_impl({})
        
        # Verify scan was called multiple times
        assert mock_memory.scan.call_count == 2

    def test_complete_with_result_field(self):
        """Test _complete when results have 'result' field."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            json.dumps({"result": "extracted_result", "other": "data"}),
            json.dumps({"result": "another_result"})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        assert result["merged"]["agent1"] == "extracted_result"
        assert result["merged"]["agent2"] == "another_result"

    def test_complete_with_response_field(self):
        """Test _complete when results have 'response' field."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            json.dumps({
                "response": "llm_response",
                "confidence": "0.9",
                "internal_reasoning": "thinking",
                "_metrics": {"tokens": 100},
                "formatted_prompt": "prompt text"
            }),
            json.dumps({"response": "another_response", "confidence": "0.8"})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        assert result["merged"]["agent1"]["response"] == "llm_response"
        assert result["merged"]["agent1"]["confidence"] == "0.9"
        assert result["merged"]["agent2"]["response"] == "another_response"

    def test_complete_with_plain_dict(self):
        """Test _complete when results are plain dicts without standard fields."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            json.dumps({"custom": "data1", "value": 42}),
            json.dumps({"custom": "data2", "value": 43})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        assert result["merged"]["agent1"]["custom"] == "data1"
        assert result["merged"]["agent1"]["value"] == 42

    def test_complete_with_non_dict_result(self):
        """Test _complete when result is not a dict (error handling)."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            "plain_string_result",  # String causes AttributeError
            "42"
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        # Non-dict results trigger error handling
        assert "error" in result["merged"]["agent1"]
        assert result["merged"]["agent1"]["error_type"] == "AttributeError"
        assert "error" in result["merged"]["agent2"]

    def test_complete_with_json_decode_error(self):
        """Test _complete handling JSON decode errors."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            "invalid{json",  # Invalid JSON string causes AttributeError when accessing .get()
            json.dumps({"valid": "json"})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        # Invalid JSON triggers error handling
        assert "error" in result["merged"]["agent1"]
        assert result["merged"]["agent1"]["error_type"] == "AttributeError"
        assert result["merged"]["agent2"]["valid"] == "json"

    def test_complete_with_none_result(self):
        """Test _complete when hget returns None."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            None,  # No result for agent1
            json.dumps({"result": "agent2_result"})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        # agent1 should not be in merged (no result)
        assert "agent1" not in result["merged"]
        assert result["merged"]["agent2"] == "agent2_result"

    def test_complete_with_exception_during_processing(self):
        """Test _complete handling exceptions during result processing."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            Exception("Redis error"),
            json.dumps({"result": "agent2_result"})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        # agent1 should have error result
        assert "agent1" in result["merged"]
        assert "error" in result["merged"]["agent1"]
        assert result["merged"]["agent1"]["error_type"] == "Exception"
        assert result["merged"]["agent2"] == "agent2_result"

    def test_complete_stores_results_correctly(self):
        """Test _complete stores results in Redis with correct keys."""
        mock_memory = Mock()
        mock_memory.hget.side_effect = [
            json.dumps({"response": "result1", "fork_group": "group_123"}),
            json.dumps({"response": "result2", "fork_group": "group_123"})
        ]
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        # Verify Redis operations
        assert mock_memory.set.call_count >= 2  # At least 2 agent results + final
        assert mock_memory.hset.call_count >= 3  # join_outputs + 2 group results + final group
        mock_memory.hdel.assert_called_once_with(state_key, *fork_targets)

    def test_complete_empty_fork_targets(self):
        """Test _complete with empty fork_targets list."""
        mock_memory = Mock()
        mock_memory.hdel = Mock()
        mock_memory.set = Mock()
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = []
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        assert result["status"] == "done"
        assert result["merged"] == {}
        # hdel should not be called with empty list
        mock_memory.hdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_impl_retry_count_none_defaults_to_3(self):
        """Test _run_impl when retry count is None (first run)."""
        mock_memory = Mock()
        mock_memory.hget.return_value = None  # First time, no retry count
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        result = await node._run_impl(input_data)
        
        # Should set retry count to 3 (starting value when None)
        mock_memory.hset.assert_called_with(
            "join_retry_counts",
            node._retry_key,
            "3"
        )

    @pytest.mark.asyncio
    async def test_run_impl_bytes_in_inputs_received(self):
        """Test _run_impl properly handles bytes in inputs_received."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "0"
        mock_memory.hkeys.return_value = [b"agent1", b"agent2"]  # Bytes
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        node._complete = Mock(return_value={"status": "done"})
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_run_impl_bytes_in_fork_targets(self):
        """Test _run_impl properly handles bytes in fork_targets."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "0"
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = [b"agent1", b"agent2"]  # Bytes
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        result = await node._run_impl(input_data)
        
        # Should properly decode bytes and find pending agent2
        assert result["status"] == "waiting"
        assert "agent2" in result["pending"]

