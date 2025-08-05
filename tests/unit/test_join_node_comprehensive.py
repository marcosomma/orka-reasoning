"""Test Join Node Comprehensive."""

import json
from unittest.mock import MagicMock

from orka.nodes.join_node import JoinNode


class TestJoinNode:
    """Test cases for JoinNode."""

    def test_init_default_values(self):
        """Test JoinNode initialization with default values."""
        mock_queue = MagicMock()
        mock_memory = MagicMock()

        node = JoinNode(
            node_id="join1",
            prompt="Join results",
            queue=mock_queue,
            memory_logger=mock_memory,
        )

        assert node.node_id == "join1"
        assert node.prompt == "Join results"
        assert node.queue == mock_queue
        assert node.memory_logger == mock_memory
        assert node.group_id is None
        assert node.max_retries == 30
        assert node.output_key == "join1:output"
        assert node._retry_key == "join1:join_retry_count"

    def test_init_custom_values(self):
        """Test JoinNode initialization with custom values."""
        mock_queue = MagicMock()
        mock_memory = MagicMock()

        node = JoinNode(
            node_id="join2",
            prompt="Custom join",
            queue=mock_queue,
            memory_logger=mock_memory,
            group="group123",
            max_retries=50,
        )

        assert node.node_id == "join2"
        assert node.group_id == "group123"
        assert node.max_retries == 50
        assert node.output_key == "join2:output"
        assert node._retry_key == "join2:join_retry_count"

    def test_run_all_agents_completed(self):
        """Test run when all expected agents have completed."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
            group="group1",
        )

        # Mock memory operations for completed scenario
        mock_memory.hget.side_effect = [
            None,  # retry count (first call)
            '{"result": "agent1"}',  # agent1 result
            '{"result": "agent2"}',  # agent2 result
        ]
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]

        input_data = {"fork_group_id": "group1"}
        result = node.run(input_data)

        assert result["status"] == "done"
        assert "merged" in result
        assert result["merged"]["agent1"] == "agent1"
        assert result["merged"]["agent2"] == "agent2"

        # Verify cleanup calls
        mock_memory.hdel.assert_any_call("join_retry_counts", "join1:join_retry_count")
        mock_memory.hset.assert_any_call(
            "join_outputs",
            "join1:output",
            json.dumps(result["merged"]),
        )

    def test_run_agents_pending_first_attempt(self):
        """Test run when some agents are still pending (first attempt)."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
            group="group1",
            max_retries=10,
        )

        # Mock memory operations for pending scenario
        mock_memory.hget.return_value = None  # No retry count yet
        mock_memory.hkeys.return_value = ["agent1"]  # Only agent1 completed
        mock_memory.smembers.return_value = ["agent1", "agent2", "agent3"]  # Expected agents

        input_data = {"fork_group_id": "group1"}
        result = node.run(input_data)

        assert result["status"] == "waiting"
        assert result["pending"] == ["agent2", "agent3"]
        assert result["received"] == ["agent1"]
        assert result["retry_count"] == 3
        assert result["max_retries"] == 10

        # Verify retry count was set
        mock_memory.hset.assert_called_with("join_retry_counts", "join1:join_retry_count", "3")

    def test_run_agents_pending_with_retries(self):
        """Test run when agents are pending and retries are happening."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
            max_retries=10,
        )

        # Mock memory operations for retry scenario
        mock_memory.hget.return_value = "5"  # Current retry count
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        mock_memory.smembers.return_value = ["agent1", "agent2", "agent3"]

        input_data = {"fork_group_id": "test_group"}
        result = node.run(input_data)

        assert result["status"] == "waiting"
        assert result["pending"] == ["agent3"]
        assert result["received"] == ["agent1", "agent2"]
        assert result["retry_count"] == 6
        assert result["max_retries"] == 10

        # Verify retry count was incremented
        mock_memory.hset.assert_called_with("join_retry_counts", "join1:join_retry_count", "6")

    def test_run_max_retries_exceeded(self):
        """Test run when max retries are exceeded."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
            max_retries=5,
        )

        # Mock memory operations for timeout scenario
        mock_memory.hget.return_value = "5"  # At max retries
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]

        input_data = {"fork_group_id": "test_group"}
        result = node.run(input_data)

        assert result["status"] == "timeout"
        assert result["pending"] == ["agent2"]
        assert result["received"] == ["agent1"]
        assert result["max_retries"] == 5

        # Verify retry count was cleaned up
        mock_memory.hdel.assert_called_with("join_retry_counts", "join1:join_retry_count")

    def test_run_use_default_group_id(self):
        """Test run using default group_id when not provided in input."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
            group="default_group",
        )

        # Mock memory operations
        mock_memory.hget.return_value = None
        mock_memory.hkeys.return_value = []
        mock_memory.smembers.return_value = ["agent1"]

        input_data = {}  # No fork_group_id provided
        result = node.run(input_data)

        # Should use default group_id
        mock_memory.smembers.assert_called_with("fork_group:default_group")
        assert result["status"] == "waiting"

    def test_run_handle_byte_strings(self):
        """Test run handles byte strings from Redis correctly."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
        )

        # Mock memory operations returning byte strings (like Redis)
        mock_memory.hget.return_value = None
        mock_memory.hkeys.return_value = [b"agent1", b"agent2"]  # Byte strings
        mock_memory.smembers.return_value = [b"agent1", b"agent2", b"agent3"]  # Byte strings

        input_data = {"fork_group_id": "test_group"}
        result = node.run(input_data)

        assert result["status"] == "waiting"
        assert result["pending"] == ["agent3"]  # Should be decoded
        assert result["received"] == ["agent1", "agent2"]  # Should be decoded

    def test_complete_method(self):
        """Test _complete method functionality."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
        )

        # Mock data retrieval
        mock_memory.hget.side_effect = [
            '{"result": "data1", "status": "success"}',
            '{"result": "data2", "status": "success"}',
        ]

        fork_targets = ["agent1", "agent2"]
        state_key = "test:state:key"

        result = node._complete(fork_targets, state_key)

        assert result["status"] == "done"
        assert "merged" in result
        assert result["merged"]["agent1"] == "data1"
        assert result["merged"]["agent2"] == "data2"

        # Verify storage and cleanup
        expected_merged = {
            "agent1": "data1",
            "agent2": "data2",
        }
        mock_memory.hset.assert_any_call(
            "join_outputs",
            "join1:output",
            json.dumps(expected_merged),
        )
        mock_memory.hdel.assert_called_with(state_key, "agent1", "agent2")

    def test_complete_method_empty_targets(self):
        """Test _complete method with empty fork targets."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
        )

        fork_targets = []
        state_key = "test:state:key"

        result = node._complete(fork_targets, state_key)

        assert result["status"] == "done"
        assert result["merged"] == {}

        # Should not call hdel with empty targets
        mock_memory.hdel.assert_not_called()

        # Should still store empty result
        mock_memory.hset.assert_called_with(
            "join_results:join1",
            "result",
            json.dumps({"status": "done", "merged": {}}),
        )

    def test_run_json_parsing_in_complete(self):
        """Test that JSON parsing works correctly in _complete method."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
        )

        # Mock for completed scenario that triggers _complete
        mock_memory.hget.side_effect = [
            None,  # retry count
            '{"complex": {"nested": "data"}, "list": [1, 2, 3]}',  # agent1 result
        ]
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = ["agent1"]

        input_data = {"fork_group_id": "test_group"}
        result = node.run(input_data)

        assert result["status"] == "done"
        assert result["merged"]["agent1"]["complex"]["nested"] == "data"
        assert result["merged"]["agent1"]["list"] == [1, 2, 3]

    def test_run_state_key_formation(self):
        """Test that the correct state key is used."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
        )

        mock_memory.hget.return_value = None
        mock_memory.hkeys.return_value = []
        mock_memory.smembers.return_value = ["agent1"]

        input_data = {"fork_group_id": "test_group"}
        node.run(input_data)

        # Verify correct state key is used
        expected_state_key = "waitfor:join_parallel_checks:inputs"
        mock_memory.hkeys.assert_called_with(expected_state_key)

    def test_run_retry_count_edge_cases(self):
        """Test retry count edge cases."""
        mock_memory = MagicMock()
        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=MagicMock(),
            memory_logger=mock_memory,
            max_retries=5,
        )

        # Test exactly at max retries
        mock_memory.hget.return_value = "5"  # At max retries
        mock_memory.hkeys.return_value = []
        mock_memory.smembers.return_value = ["agent1"]

        input_data = {"fork_group_id": "test_group"}
        result = node.run(input_data)

        # Should timeout since retry_count (6) >= max_retries (5)
        assert result["status"] == "timeout"

        # Test just under max retries
        mock_memory.hget.return_value = "3"
        result = node.run(input_data)

        # Should still be waiting since retry_count (4) < max_retries (5)
        assert result["status"] == "waiting"

    def test_inheritance_from_base_node(self):
        """Test that JoinNode properly inherits from BaseNode."""
        mock_queue = MagicMock()
        mock_memory = MagicMock()

        node = JoinNode(
            node_id="join1",
            prompt="Join test",
            queue=mock_queue,
            memory_logger=mock_memory,
        )

        # Should have BaseNode attributes
        assert hasattr(node, "node_id")
        assert hasattr(node, "prompt")
        assert hasattr(node, "queue")

        # Should be instance of BaseNode
        from orka.nodes.base_node import BaseNode

        assert isinstance(node, BaseNode)
