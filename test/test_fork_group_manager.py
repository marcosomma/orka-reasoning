# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Tests for ForkGroupManager and SimpleForkGroupManager
"""

import time
from unittest.mock import MagicMock

import pytest
from fake_redis import FakeRedisClient

from orka.fork_group_manager import ForkGroupManager, SimpleForkGroupManager


class TestForkGroupManager:
    """Test cases for ForkGroupManager"""

    def test_init(self):
        """Test ForkGroupManager initialization"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)
        assert manager.redis == redis_client

    def test_create_group_flat_ids(self):
        """Test creating a group with flat agent IDs"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        manager.create_group("group1", ["agent1", "agent2", "agent3"])

        # Verify agents were added to the set
        members = redis_client.smembers("fork_group:group1")
        # Convert bytes to strings for comparison
        members_str = {m.decode() if isinstance(m, bytes) else m for m in members}
        assert "agent1" in members_str
        assert "agent2" in members_str
        assert "agent3" in members_str

    def test_create_group_nested_ids(self):
        """Test creating a group with nested agent IDs"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # Test with nested lists (branch sequences)
        manager.create_group("group1", [["agent1", "agent2"], ["agent3"]])

        # Verify all agents were flattened and added
        members = redis_client.smembers("fork_group:group1")
        # Convert bytes to strings for comparison
        members_str = {m.decode() if isinstance(m, bytes) else m for m in members}
        assert "agent1" in members_str
        assert "agent2" in members_str
        assert "agent3" in members_str

    def test_mark_agent_done(self):
        """Test marking an agent as done"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # Create group and mark agent done
        manager.create_group("group1", ["agent1", "agent2"])
        manager.mark_agent_done("group1", "agent1")

        # Verify agent was removed
        members = redis_client.smembers("fork_group:group1")
        # Convert bytes to strings for comparison
        members_str = {m.decode() if isinstance(m, bytes) else m for m in members}
        assert "agent1" not in members_str
        assert "agent2" in members_str

    def test_is_group_done(self):
        """Test checking if group is done"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # Create group
        manager.create_group("group1", ["agent1", "agent2"])
        assert not manager.is_group_done("group1")

        # Mark one agent done
        manager.mark_agent_done("group1", "agent1")
        assert not manager.is_group_done("group1")

        # Mark all agents done
        manager.mark_agent_done("group1", "agent2")
        assert manager.is_group_done("group1")

    def test_list_pending_agents(self):
        """Test listing pending agents"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # Create group
        manager.create_group("group1", ["agent1", "agent2", "agent3"])
        pending = manager.list_pending_agents("group1")
        assert set(pending) == {"agent1", "agent2", "agent3"}

        # Mark one done
        manager.mark_agent_done("group1", "agent1")
        pending = manager.list_pending_agents("group1")
        assert set(pending) == {"agent2", "agent3"}

    def test_list_pending_agents_with_bytes(self):
        """Test listing pending agents when Redis returns bytes"""
        redis_client = MagicMock()
        redis_client.smembers.return_value = [b"agent1", b"agent2", "agent3"]
        manager = ForkGroupManager(redis_client)

        pending = manager.list_pending_agents("group1")
        assert set(pending) == {"agent1", "agent2", "agent3"}

    def test_delete_group(self):
        """Test deleting a group"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # Create and delete group
        manager.create_group("group1", ["agent1", "agent2"])
        manager.delete_group("group1")

        # Verify group was deleted
        assert manager.is_group_done("group1")  # No pending agents

    def test_generate_group_id(self):
        """Test generating group IDs"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        group_id = manager.generate_group_id("base_id")
        assert group_id.startswith("base_id_")

        # Test with time - should contain timestamp
        current_time = int(time.time())
        group_id = manager.generate_group_id("test")
        assert f"test_{current_time}" in group_id or f"test_{current_time + 1}" in group_id

    def test_group_key(self):
        """Test _group_key method"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        key = manager._group_key("test_group")
        assert key == "fork_group:test_group"

    def test_branch_seq_key(self):
        """Test _branch_seq_key method"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        key = manager._branch_seq_key("test_group")
        assert key == "fork_branch:test_group"

    def test_track_branch_sequence(self):
        """Test tracking branch sequences"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        sequence = ["agent1", "agent2", "agent3"]
        manager.track_branch_sequence("group1", sequence)

        # Verify sequence was stored correctly
        next_agent = redis_client.hget("fork_branch:group1", "agent1")
        assert next_agent == b"agent2"  # FakeRedisClient returns bytes like real Redis
        next_agent = redis_client.hget("fork_branch:group1", "agent2")
        assert next_agent == b"agent3"
        next_agent = redis_client.hget("fork_branch:group1", "agent3")
        assert next_agent is None

    def test_next_in_sequence(self):
        """Test getting next agent in sequence"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # Track sequence and test next
        sequence = ["agent1", "agent2", "agent3"]
        manager.track_branch_sequence("group1", sequence)

        assert manager.next_in_sequence("group1", "agent1") == "agent2"
        assert manager.next_in_sequence("group1", "agent2") == "agent3"
        assert manager.next_in_sequence("group1", "agent3") is None

    def test_next_in_sequence_with_bytes(self):
        """Test next_in_sequence when Redis returns bytes"""
        redis_client = MagicMock()
        redis_client.hget.return_value = b"agent2"
        manager = ForkGroupManager(redis_client)

        next_agent = manager.next_in_sequence("group1", "agent1")
        assert next_agent == "agent2"

    def test_next_in_sequence_none(self):
        """Test next_in_sequence when no next agent exists"""
        redis_client = FakeRedisClient()
        manager = ForkGroupManager(redis_client)

        # No sequence tracked
        assert manager.next_in_sequence("group1", "agent1") is None


class TestSimpleForkGroupManager:
    """Test cases for SimpleForkGroupManager"""

    def test_init(self):
        """Test SimpleForkGroupManager initialization"""
        manager = SimpleForkGroupManager()
        assert manager._groups == {}
        assert manager._branch_sequences == {}

    def test_create_group_flat_ids(self):
        """Test creating a group with flat agent IDs"""
        manager = SimpleForkGroupManager()

        manager.create_group("group1", ["agent1", "agent2", "agent3"])

        assert "group1" in manager._groups
        assert manager._groups["group1"] == {"agent1", "agent2", "agent3"}

    def test_create_group_nested_ids(self):
        """Test creating a group with nested agent IDs"""
        manager = SimpleForkGroupManager()

        # Test with nested lists (branch sequences)
        manager.create_group("group1", [["agent1", "agent2"], ["agent3"]])

        assert "group1" in manager._groups
        assert manager._groups["group1"] == {"agent1", "agent2", "agent3"}

    def test_mark_agent_done(self):
        """Test marking an agent as done"""
        manager = SimpleForkGroupManager()

        # Create group and mark agent done
        manager.create_group("group1", ["agent1", "agent2"])
        manager.mark_agent_done("group1", "agent1")

        assert manager._groups["group1"] == {"agent2"}

    def test_mark_agent_done_nonexistent_group(self):
        """Test marking agent done for nonexistent group"""
        manager = SimpleForkGroupManager()

        # Should not raise error
        manager.mark_agent_done("nonexistent", "agent1")

    def test_is_group_done(self):
        """Test checking if group is done"""
        manager = SimpleForkGroupManager()

        # Nonexistent group is considered done
        assert manager.is_group_done("nonexistent")

        # Create group
        manager.create_group("group1", ["agent1", "agent2"])
        assert not manager.is_group_done("group1")

        # Mark one agent done
        manager.mark_agent_done("group1", "agent1")
        assert not manager.is_group_done("group1")

        # Mark all agents done
        manager.mark_agent_done("group1", "agent2")
        assert manager.is_group_done("group1")

    def test_list_pending_agents(self):
        """Test listing pending agents"""
        manager = SimpleForkGroupManager()

        # Nonexistent group returns empty list
        assert manager.list_pending_agents("nonexistent") == []

        # Create group
        manager.create_group("group1", ["agent1", "agent2", "agent3"])
        pending = manager.list_pending_agents("group1")
        assert set(pending) == {"agent1", "agent2", "agent3"}

        # Mark one done
        manager.mark_agent_done("group1", "agent1")
        pending = manager.list_pending_agents("group1")
        assert set(pending) == {"agent2", "agent3"}

    def test_delete_group(self):
        """Test deleting a group"""
        manager = SimpleForkGroupManager()

        # Create group with sequence
        manager.create_group("group1", ["agent1", "agent2"])
        manager.track_branch_sequence("group1", ["agent1", "agent2"])

        assert "group1" in manager._groups
        assert "group1" in manager._branch_sequences

        # Delete group
        manager.delete_group("group1")

        assert "group1" not in manager._groups
        assert "group1" not in manager._branch_sequences

    def test_delete_nonexistent_group(self):
        """Test deleting a nonexistent group"""
        manager = SimpleForkGroupManager()

        # Should not raise error
        manager.delete_group("nonexistent")

    def test_generate_group_id(self):
        """Test generating group IDs"""
        manager = SimpleForkGroupManager()

        group_id = manager.generate_group_id("base_id")
        assert group_id.startswith("base_id_")

        # Test with time - should contain timestamp
        current_time = int(time.time())
        group_id = manager.generate_group_id("test")
        assert f"test_{current_time}" in group_id or f"test_{current_time + 1}" in group_id

    def test_track_branch_sequence(self):
        """Test tracking branch sequences"""
        manager = SimpleForkGroupManager()

        sequence = ["agent1", "agent2", "agent3"]
        manager.track_branch_sequence("group1", sequence)

        # Verify sequence was stored correctly
        assert "group1" in manager._branch_sequences
        assert manager._branch_sequences["group1"]["agent1"] == "agent2"
        assert manager._branch_sequences["group1"]["agent2"] == "agent3"
        assert "agent3" not in manager._branch_sequences["group1"]

    def test_next_in_sequence(self):
        """Test getting next agent in sequence"""
        manager = SimpleForkGroupManager()

        # Track sequence and test next
        sequence = ["agent1", "agent2", "agent3"]
        manager.track_branch_sequence("group1", sequence)

        assert manager.next_in_sequence("group1", "agent1") == "agent2"
        assert manager.next_in_sequence("group1", "agent2") == "agent3"
        assert manager.next_in_sequence("group1", "agent3") is None

    def test_next_in_sequence_nonexistent_group(self):
        """Test next_in_sequence for nonexistent group"""
        manager = SimpleForkGroupManager()

        assert manager.next_in_sequence("nonexistent", "agent1") is None

    def test_remove_group_existing(self):
        """Test removing an existing group"""
        manager = SimpleForkGroupManager()

        # Create group
        manager.create_group("group1", ["agent1", "agent2"])
        assert "group1" in manager._groups

        # Remove group
        manager.remove_group("group1")
        assert "group1" not in manager._groups

    def test_remove_group_nonexistent(self):
        """Test removing a nonexistent group raises KeyError"""
        manager = SimpleForkGroupManager()

        with pytest.raises(KeyError, match="Group nonexistent not found"):
            manager.remove_group("nonexistent")

    def test_track_sequence_empty(self):
        """Test tracking empty sequence"""
        manager = SimpleForkGroupManager()

        # Empty sequence should not create any mappings
        manager.track_branch_sequence("group1", [])

        # Group should be created but empty
        assert manager._branch_sequences.get("group1", {}) == {}

    def test_track_sequence_single_agent(self):
        """Test tracking sequence with single agent"""
        manager = SimpleForkGroupManager()

        # Single agent sequence should not create any mappings
        manager.track_branch_sequence("group1", ["agent1"])

        # Group should be created but empty
        assert manager._branch_sequences.get("group1", {}) == {}
