"""Unit tests for orka.fork_group_manager."""

from unittest.mock import Mock

import pytest

from orka.fork_group_manager import ForkGroupManager, SimpleForkGroupManager

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestForkGroupManager:
    """Test suite for ForkGroupManager class."""

    def test_init(self):
        """Test ForkGroupManager initialization."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        assert manager.redis == mock_redis

    def test_create_group(self):
        """Test create_group method."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        manager.create_group("group1", ["agent1", "agent2"])
        
        mock_redis.sadd.assert_called_once()
        assert "fork_group:group1" in str(mock_redis.sadd.call_args)

    def test_create_group_with_nested_lists(self):
        """Test create_group with nested agent lists."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        manager.create_group("group1", [["agent1", "agent2"], "agent3"])
        
        mock_redis.sadd.assert_called_once()

    def test_mark_agent_done(self):
        """Test mark_agent_done method."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        manager.mark_agent_done("group1", "agent1")
        
        mock_redis.srem.assert_called_once()

    def test_is_group_done(self):
        """Test is_group_done method."""
        mock_redis = Mock()
        mock_redis.scard.return_value = 0
        manager = ForkGroupManager(mock_redis)
        
        result = manager.is_group_done("group1")
        
        assert result is True
        mock_redis.scard.assert_called_once()

    def test_is_group_done_not_done(self):
        """Test is_group_done when group is not done."""
        mock_redis = Mock()
        mock_redis.scard.return_value = 2
        manager = ForkGroupManager(mock_redis)
        
        result = manager.is_group_done("group1")
        
        assert result is False

    def test_list_pending_agents(self):
        """Test list_pending_agents method."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = {b"agent1", b"agent2"}
        manager = ForkGroupManager(mock_redis)
        
        result = manager.list_pending_agents("group1")
        
        assert "agent1" in result
        assert "agent2" in result

    def test_list_pending_agents_strings(self):
        """Test list_pending_agents with string values."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = {"agent1", "agent2"}
        manager = ForkGroupManager(mock_redis)
        
        result = manager.list_pending_agents("group1")
        
        assert "agent1" in result
        assert "agent2" in result

    def test_delete_group(self):
        """Test delete_group method."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        manager.delete_group("group1")
        
        mock_redis.delete.assert_called_once()

    def test_generate_group_id(self):
        """Test generate_group_id method."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        group_id = manager.generate_group_id("base")
        
        assert group_id.startswith("base_")
        assert len(group_id) > len("base_")

    def test_group_key(self):
        """Test _group_key method."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        key = manager._group_key("group1")
        
        assert key == "fork_group:group1"

    def test_track_branch_sequence(self):
        """Test track_branch_sequence method."""
        mock_redis = Mock()
        manager = ForkGroupManager(mock_redis)
        
        manager.track_branch_sequence("group1", ["agent1", "agent2", "agent3"])

        assert mock_redis.hset.call_count == 2

    def test_next_in_sequence(self):
        """Test next_in_sequence method."""
        mock_redis = Mock()
        mock_redis.hget.return_value = "agent2"
        manager = ForkGroupManager(mock_redis)
        
        result = manager.next_in_sequence("group1", "agent1")
        
        assert result == "agent2"

    def test_next_in_sequence_last(self):
        """Test next_in_sequence when agent is last."""
        mock_redis = Mock()
        mock_redis.hget.return_value = None
        manager = ForkGroupManager(mock_redis)
        
        result = manager.next_in_sequence("group1", "agent2")
        
        assert result is None


class TestSimpleForkGroupManager:
    """Test suite for SimpleForkGroupManager class."""

    def test_init(self):
        """Test SimpleForkGroupManager initialization."""
        manager = SimpleForkGroupManager()
        
        assert manager._groups == {}
        assert manager._branch_sequences == {}

    def test_create_group(self):
        """Test create_group method."""
        manager = SimpleForkGroupManager()
        
        manager.create_group("group1", ["agent1", "agent2"])
        
        assert "group1" in manager._groups
        assert "agent1" in manager._groups["group1"]
        assert "agent2" in manager._groups["group1"]

    def test_mark_agent_done(self):
        """Test mark_agent_done method."""
        manager = SimpleForkGroupManager()
        manager.create_group("group1", ["agent1", "agent2"])
        
        manager.mark_agent_done("group1", "agent1")
        
        assert "agent1" not in manager._groups["group1"]
        assert "agent2" in manager._groups["group1"]

    def test_is_group_done(self):
        """Test is_group_done method."""
        manager = SimpleForkGroupManager()
        manager.create_group("group1", ["agent1"])
        
        assert manager.is_group_done("group1") is False
        
        manager.mark_agent_done("group1", "agent1")
        
        assert manager.is_group_done("group1") is True

    def test_list_pending_agents(self):
        """Test list_pending_agents method."""
        manager = SimpleForkGroupManager()
        manager.create_group("group1", ["agent1", "agent2"])
        
        pending = manager.list_pending_agents("group1")
        
        assert "agent1" in pending
        assert "agent2" in pending

    def test_delete_group(self):
        """Test delete_group method."""
        manager = SimpleForkGroupManager()
        manager.create_group("group1", ["agent1"])
        
        manager.delete_group("group1")
        
        assert "group1" not in manager._groups

    def test_generate_group_id(self):
        """Test generate_group_id method."""
        manager = SimpleForkGroupManager()
        
        group_id = manager.generate_group_id("base")
        
        assert group_id.startswith("base_")

    def test_track_branch_sequence(self):
        """Test track_branch_sequence method."""
        manager = SimpleForkGroupManager()
        
        manager.track_branch_sequence("group1", ["agent1", "agent2"])
        
        assert "group1" in manager._branch_sequences
        assert manager._branch_sequences["group1"] == {"agent1": "agent2"}

    def test_next_in_sequence(self):
        """Test next_in_sequence method."""
        manager = SimpleForkGroupManager()
        manager.track_branch_sequence("group1", ["agent1", "agent2", "agent3"])
        
        result = manager.next_in_sequence("group1", "agent1")
        
        assert result == "agent2"

    def test_next_in_sequence_last(self):
        """Test next_in_sequence when agent is last."""
        manager = SimpleForkGroupManager()
        manager.track_branch_sequence("group1", ["agent1", "agent2"])
        
        result = manager.next_in_sequence("group1", "agent2")
        
        assert result is None

    def test_remove_group(self):
        """Test remove_group method."""
        manager = SimpleForkGroupManager()
        manager.create_group("group1", ["agent1"])
        manager.track_branch_sequence("group1", ["agent1"])
        
        manager.remove_group("group1")
        
        assert "group1" not in manager._groups
        assert "group1" not in manager._branch_sequences

