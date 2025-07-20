"""
Unit tests for the fork_group_manager.py module.
Tests both ForkGroupManager (Redis-based) and SimpleForkGroupManager (in-memory).
"""

from unittest.mock import Mock, patch

from typing import Any, Dict, List, Tuple

from orka.fork_group_manager import ForkGroupManager, SimpleForkGroupManager


class TestForkGroupManager:
    """Test suite for the Redis-based ForkGroupManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = Mock()
        self.fork_manager = ForkGroupManager(self.mock_redis)
        self.test_group_id = "test_group_123"
        self.test_agent_ids = ["agent1", "agent2", "agent3"]

    def test_initialization(self):
        """Test ForkGroupManager initialization."""
        redis_client = Mock()
        manager = ForkGroupManager(redis_client)

        assert manager.redis == redis_client

    def test_create_group_flat_ids(self):
        """Test creating a group with simple agent IDs."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.sadd.assert_called_once_with(
            expected_key,
            "agent1",
            "agent2",
            "agent3",
        )

    def test_create_group_nested_ids(self):
        """Test creating a group with nested agent ID lists."""
        nested_ids = [["agent1", "agent2"], "agent3", ["agent4"]]

        self.fork_manager.create_group(self.test_group_id, nested_ids)

        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.sadd.assert_called_once_with(
            expected_key,
            "agent1",
            "agent2",
            "agent3",
            "agent4",
        )

    def test_create_group_mixed_nested_ids(self):
        """Test creating a group with complex nested structures."""
        complex_ids = ["single", ["branch1", "branch2"], ["seq1", "seq2", "seq3"]]

        self.fork_manager.create_group(self.test_group_id, complex_ids)

        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.sadd.assert_called_once_with(
            expected_key,
            "single",
            "branch1",
            "branch2",
            "seq1",
            "seq2",
            "seq3",
        )

    def test_mark_agent_done(self):
        """Test marking an agent as done."""
        agent_id = "agent1"

        self.fork_manager.mark_agent_done(self.test_group_id, agent_id)

        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.srem.assert_called_once_with(expected_key, agent_id)

    def test_is_group_done_true(self):
        """Test checking if group is done when all agents completed."""
        self.mock_redis.scard.return_value = 0

        result = self.fork_manager.is_group_done(self.test_group_id)

        assert result is True
        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.scard.assert_called_once_with(expected_key)

    def test_is_group_done_false(self):
        """Test checking if group is done when agents still pending."""
        self.mock_redis.scard.return_value = 2

        result = self.fork_manager.is_group_done(self.test_group_id)

        assert result is False
        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.scard.assert_called_once_with(expected_key)

    def test_list_pending_agents_bytes(self):
        """Test listing pending agents when Redis returns bytes."""
        self.mock_redis.smembers.return_value = {b"agent1", b"agent2"}

        result = self.fork_manager.list_pending_agents(self.test_group_id)

        assert set(result) == {"agent1", "agent2"}
        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.smembers.assert_called_once_with(expected_key)

    def test_list_pending_agents_strings(self):
        """Test listing pending agents when Redis returns strings."""
        self.mock_redis.smembers.return_value = {"agent1", "agent2"}

        result = self.fork_manager.list_pending_agents(self.test_group_id)

        assert set(result) == {"agent1", "agent2"}
        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.smembers.assert_called_once_with(expected_key)

    def test_list_pending_agents_empty(self):
        """Test listing pending agents when no agents are pending."""
        self.mock_redis.smembers.return_value = set()

        result = self.fork_manager.list_pending_agents(self.test_group_id)

        assert result == []

    def test_delete_group(self):
        """Test deleting a fork group."""
        self.fork_manager.delete_group(self.test_group_id)

        expected_key = f"fork_group:{self.test_group_id}"
        self.mock_redis.delete.assert_called_once_with(expected_key)

    @patch("time.time")
    def test_generate_group_id(self, mock_time):
        """Test generating a unique group ID."""
        mock_time.return_value = 1234567890
        base_id = "workflow"

        result = self.fork_manager.generate_group_id(base_id)

        assert result == "workflow_1234567890"

    def test_group_key(self):
        """Test generating Redis key for group."""
        result = self.fork_manager._group_key(self.test_group_id)

        assert result == f"fork_group:{self.test_group_id}"

    def test_branch_seq_key(self):
        """Test generating Redis key for branch sequence."""
        result = self.fork_manager._branch_seq_key(self.test_group_id)

        assert result == f"fork_branch:{self.test_group_id}"

    def test_track_branch_sequence(self):
        """Test tracking branch sequence."""
        agent_sequence = ["agent1", "agent2", "agent3"]

        self.fork_manager.track_branch_sequence(self.test_group_id, agent_sequence)

        expected_key = f"fork_branch:{self.test_group_id}"
        expected_calls: List[Tuple[Tuple[str, str, str], Dict[Any, Any]]] = [
            ((expected_key, "agent1", "agent2"), {}),
            ((expected_key, "agent2", "agent3"), {}),
        ]

        assert self.mock_redis.hset.call_count == 2
        for expected_call in expected_calls:
            assert expected_call in self.mock_redis.hset.call_args_list

    def test_track_branch_sequence_single_agent(self):
        """Test tracking branch sequence with single agent."""
        agent_sequence = ["agent1"]

        self.fork_manager.track_branch_sequence(self.test_group_id, agent_sequence)

        # Should not call hset for single agent
        self.mock_redis.hset.assert_not_called()

    def test_next_in_sequence_bytes(self):
        """Test getting next agent in sequence when Redis returns bytes."""
        self.mock_redis.hget.return_value = b"agent2"

        result = self.fork_manager.next_in_sequence(self.test_group_id, "agent1")

        assert result == "agent2"
        expected_key = f"fork_branch:{self.test_group_id}"
        self.mock_redis.hget.assert_called_once_with(expected_key, "agent1")

    def test_next_in_sequence_string(self):
        """Test getting next agent in sequence when Redis returns string."""
        self.mock_redis.hget.return_value = "agent2"

        result = self.fork_manager.next_in_sequence(self.test_group_id, "agent1")

        assert result == "agent2"

    def test_next_in_sequence_none(self):
        """Test getting next agent in sequence when no next agent exists."""
        self.mock_redis.hget.return_value = None

        result = self.fork_manager.next_in_sequence(self.test_group_id, "agent1")

        assert result is None


class TestSimpleForkGroupManager:
    """Test suite for the in-memory SimpleForkGroupManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.fork_manager = SimpleForkGroupManager()
        self.test_group_id = "test_group_123"
        self.test_agent_ids = ["agent1", "agent2", "agent3"]

    def test_initialization(self):
        """Test SimpleForkGroupManager initialization."""
        manager = SimpleForkGroupManager()

        assert hasattr(manager, "_groups")
        assert hasattr(manager, "_branch_sequences")
        assert isinstance(manager._groups, dict)
        assert isinstance(manager._branch_sequences, dict)

    def test_create_group_flat_ids(self):
        """Test creating a group with simple agent IDs."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        assert self.test_group_id in self.fork_manager._groups
        assert self.fork_manager._groups[self.test_group_id] == set(self.test_agent_ids)

    def test_create_group_nested_ids(self):
        """Test creating a group with nested agent ID lists."""
        nested_ids = [["agent1", "agent2"], "agent3", ["agent4"]]

        self.fork_manager.create_group(self.test_group_id, nested_ids)

        expected_flat = {"agent1", "agent2", "agent3", "agent4"}
        assert self.fork_manager._groups[self.test_group_id] == expected_flat

    def test_mark_agent_done(self):
        """Test marking an agent as done."""
        # Set up group first
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        # Mark agent as done
        self.fork_manager.mark_agent_done(self.test_group_id, "agent1")

        # Verify agent was removed
        assert "agent1" not in self.fork_manager._groups[self.test_group_id]
        assert "agent2" in self.fork_manager._groups[self.test_group_id]
        assert "agent3" in self.fork_manager._groups[self.test_group_id]

    def test_mark_agent_done_nonexistent_group(self):
        """Test marking agent done in non-existent group."""
        # Should not raise exception
        self.fork_manager.mark_agent_done("nonexistent", "agent1")

    def test_is_group_done_true(self):
        """Test checking if group is done when all agents completed."""
        # Create empty group
        self.fork_manager._groups[self.test_group_id] = set()

        result = self.fork_manager.is_group_done(self.test_group_id)

        assert result is True

    def test_is_group_done_false(self):
        """Test checking if group is done when agents still pending."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        result = self.fork_manager.is_group_done(self.test_group_id)

        assert result is False

    def test_is_group_done_nonexistent(self):
        """Test checking non-existent group."""
        result = self.fork_manager.is_group_done("nonexistent")

        assert result is True  # Non-existent group is considered done

    def test_list_pending_agents(self):
        """Test listing pending agents."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        result = self.fork_manager.list_pending_agents(self.test_group_id)

        assert set(result) == set(self.test_agent_ids)

    def test_list_pending_agents_after_completion(self):
        """Test listing pending agents after some complete."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)
        self.fork_manager.mark_agent_done(self.test_group_id, "agent1")

        result = self.fork_manager.list_pending_agents(self.test_group_id)

        assert set(result) == {"agent2", "agent3"}

    def test_list_pending_agents_nonexistent(self):
        """Test listing pending agents for non-existent group."""
        result = self.fork_manager.list_pending_agents("nonexistent")

        assert result == []

    def test_delete_group(self):
        """Test deleting a fork group."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        self.fork_manager.delete_group(self.test_group_id)

        assert self.test_group_id not in self.fork_manager._groups

    def test_delete_nonexistent_group(self):
        """Test deleting non-existent group."""
        # Should not raise exception
        self.fork_manager.delete_group("nonexistent")

    @patch("time.time")
    def test_generate_group_id(self, mock_time):
        """Test generating a unique group ID."""
        mock_time.return_value = 1234567890
        base_id = "workflow"

        result = self.fork_manager.generate_group_id(base_id)

        assert result == "workflow_1234567890"

    def test_track_branch_sequence(self):
        """Test tracking branch sequence."""
        agent_sequence = ["agent1", "agent2", "agent3"]

        self.fork_manager.track_branch_sequence(self.test_group_id, agent_sequence)

        assert self.test_group_id in self.fork_manager._branch_sequences
        expected_mapping = {"agent1": "agent2", "agent2": "agent3"}
        assert self.fork_manager._branch_sequences[self.test_group_id] == expected_mapping

    def test_track_branch_sequence_single_agent(self):
        """Test tracking branch sequence with single agent."""
        agent_sequence = ["agent1"]

        self.fork_manager.track_branch_sequence(self.test_group_id, agent_sequence)

        assert self.test_group_id in self.fork_manager._branch_sequences
        assert self.fork_manager._branch_sequences[self.test_group_id] == {}

    def test_next_in_sequence(self):
        """Test getting next agent in sequence."""
        agent_sequence = ["agent1", "agent2", "agent3"]
        self.fork_manager.track_branch_sequence(self.test_group_id, agent_sequence)

        result = self.fork_manager.next_in_sequence(self.test_group_id, "agent1")

        assert result == "agent2"

    def test_next_in_sequence_last_agent(self):
        """Test getting next agent when current is last."""
        agent_sequence = ["agent1", "agent2", "agent3"]
        self.fork_manager.track_branch_sequence(self.test_group_id, agent_sequence)

        result = self.fork_manager.next_in_sequence(self.test_group_id, "agent3")

        assert result is None

    def test_next_in_sequence_nonexistent_group(self):
        """Test getting next agent for non-existent group."""
        result = self.fork_manager.next_in_sequence("nonexistent", "agent1")

        assert result is None

    def test_remove_group(self):
        """Test removing a group (alias for delete_group)."""
        self.fork_manager.create_group(self.test_group_id, self.test_agent_ids)

        self.fork_manager.remove_group(self.test_group_id)

        assert self.test_group_id not in self.fork_manager._groups

    def test_complete_workflow_simulation(self):
        """Test a complete fork group workflow simulation."""
        # Create group with nested structure
        workflow_agents = [["prep1", "prep2"], "main", ["cleanup1", "cleanup2"]]

        # Create and track group
        self.fork_manager.create_group(self.test_group_id, workflow_agents)

        # Verify all agents are pending
        pending = self.fork_manager.list_pending_agents(self.test_group_id)
        assert set(pending) == {"prep1", "prep2", "main", "cleanup1", "cleanup2"}
        assert not self.fork_manager.is_group_done(self.test_group_id)

        # Complete agents one by one
        for agent in ["prep1", "prep2", "main", "cleanup1"]:
            self.fork_manager.mark_agent_done(self.test_group_id, agent)
            assert not self.fork_manager.is_group_done(self.test_group_id)

        # Complete last agent
        self.fork_manager.mark_agent_done(self.test_group_id, "cleanup2")
        assert self.fork_manager.is_group_done(self.test_group_id)

        # Cleanup
        self.fork_manager.delete_group(self.test_group_id)
