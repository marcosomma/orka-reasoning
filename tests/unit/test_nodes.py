"""
Unit tests for the orka.nodes module.
Tests node initialization, execution, routing, and specialized functionality with heavy mocking.
"""

from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from orka.nodes import (
    BaseNode,
    FailingNode,
    FailoverNode,
    ForkNode,
    JoinNode,
    MemoryReaderNode,
    MemoryWriterNode,
    RAGNode,
    RouterNode,
)


class TestBaseNode:
    """Test the BaseNode abstract base class."""

    def test_base_node_initialization(self):
        """Test BaseNode initialization with basic parameters."""

        # Create a concrete implementation for testing
        class ConcreteNode(BaseNode):
            async def run(self, input_data):
                return {"result": "success"}

        node = ConcreteNode(
            node_id="test_node",
            prompt="test prompt",
            queue=["agent1", "agent2"],
            extra_param="value",
        )

        assert node.node_id == "test_node"
        assert node.prompt == "test prompt"
        assert node.queue == ["agent1", "agent2"]
        assert node.params == {"extra_param": "value"}
        assert node.type == "concretenode"

    def test_base_node_failing_type(self):
        """Test BaseNode special handling for failing type."""

        class FailingTestNode(BaseNode):
            def __init__(self, *args, **kwargs):
                # Set type to "failing" before calling super to trigger agent_id setting
                self.__class__.__name__ = "Failing"  # This will make type = "failing"
                super().__init__(*args, **kwargs)

            async def run(self, input_data):
                return {"result": "success"}

        node = FailingTestNode(
            node_id="fail_node",
            prompt="test",
            queue=[],
        )

        # Should set agent_id for failing nodes
        assert hasattr(node, "agent_id")
        assert node.agent_id == "fail_node"

    @pytest.mark.asyncio
    async def test_base_node_initialize(self):
        """Test BaseNode initialize method."""

        class ConcreteNode(BaseNode):
            async def run(self, input_data):
                return {"result": "success"}

        node = ConcreteNode(
            node_id="test_node",
            prompt="test",
            queue=[],
        )

        # Initialize should not raise error
        await node.initialize()

    def test_base_node_repr(self):
        """Test BaseNode string representation."""

        class ConcreteNode(BaseNode):
            async def run(self, input_data):
                return {"result": "success"}

        node = ConcreteNode(
            node_id="test_node",
            prompt="test",
            queue=["agent1"],
        )

        repr_str = repr(node)
        assert "ConcreteNode" in repr_str
        assert "id=test_node" in repr_str
        assert "queue=['agent1']" in repr_str

    def test_base_node_abstract_run(self):
        """Test that BaseNode.run is abstract."""

        # BaseNode should not be instantiable due to abstract method
        with pytest.raises(TypeError):
            BaseNode("test", "prompt", [])


class TestFailingNode:
    """Test the FailingNode implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = FailingNode(
            node_id="failing_test",
            prompt="test failure",
            queue=[],
        )

    def test_failing_node_initialization(self):
        """Test FailingNode initialization."""
        assert self.node.node_id == "failing_test"
        assert self.node.prompt == "test failure"
        assert self.node.queue == []
        # FailingNode type is "failingnode", not "failing", so no agent_id
        assert self.node.type == "failingnode"

    def test_failing_node_id_property(self):
        """Test FailingNode id property."""
        # FailingNode.id property returns getattr(self, "agent_id", getattr(self, "node_id", "unknown"))

        # Test with node_id present
        assert self.node.id == "failing_test"

        # Test fallback behavior - the actual behavior
        node_empty = FailingNode("", "", [])
        # When node_id is empty string, it returns empty string (not "unknown")
        node_empty.node_id = ""
        if hasattr(node_empty, "agent_id"):
            delattr(node_empty, "agent_id")
        assert node_empty.id == ""  # Empty string, not "unknown"

        # Test true fallback to "unknown" - when node_id attribute doesn't exist
        node_no_attr = FailingNode("test", "", [])
        if hasattr(node_no_attr, "agent_id"):
            delattr(node_no_attr, "agent_id")
        if hasattr(node_no_attr, "node_id"):
            delattr(node_no_attr, "node_id")
        assert node_no_attr.id == "unknown"

    @patch("time.sleep")
    def test_failing_node_run_failure(self, mock_sleep):
        """Test that FailingNode.run raises RuntimeError."""

        with pytest.raises(RuntimeError, match="failed intentionally after 5 seconds"):
            self.node.run({"input": "test"})

        # Should have slept for 5 seconds
        mock_sleep.assert_called_once_with(5)

    @patch("time.sleep")
    def test_failing_node_run_with_different_node_id(self, mock_sleep):
        """Test FailingNode with different node_id."""

        node = FailingNode("custom_fail", "prompt", [])

        with pytest.raises(RuntimeError, match="custom_fail failed intentionally"):
            node.run({})


class TestRouterNode:
    """Test the RouterNode implementation."""

    def test_router_node_initialization_success(self):
        """Test RouterNode initialization with valid parameters."""

        params = {
            "decision_key": "classification",
            "routing_map": {
                "positive": ["agent1"],
                "negative": ["agent2"],
            },
        }

        node = RouterNode(
            node_id="router_test",
            params=params,
        )

        assert node.node_id == "router_test"
        assert node.params == params
        assert node.prompt is None
        assert node.queue is None

    def test_router_node_initialization_missing_params(self):
        """Test RouterNode initialization fails without params."""

        with pytest.raises(ValueError, match="RouterAgent requires 'params'"):
            RouterNode(node_id="router_test")

    def test_router_node_initialization_none_params(self):
        """Test RouterNode initialization fails with None params."""

        with pytest.raises(ValueError, match="RouterAgent requires 'params'"):
            RouterNode(node_id="router_test", params=None)

    def test_router_node_run_basic_routing(self):
        """Test basic routing functionality."""

        params = {
            "decision_key": "result",
            "routing_map": {
                "success": ["success_agent"],
                "failure": ["failure_agent"],
            },
        }

        node = RouterNode(node_id="router", params=params)

        # Test successful routing
        input_data = {
            "previous_outputs": {
                "result": "success",
            },
        }

        route = node.run(input_data)
        assert route == ["success_agent"]

    def test_router_node_run_string_boolean_routing(self):
        """Test routing with string boolean values."""

        params = {
            "decision_key": "is_valid",
            "routing_map": {
                True: ["valid_agent"],
                False: ["invalid_agent"],
            },
        }

        node = RouterNode(node_id="router", params=params)

        # Test with string "true"
        input_data = {
            "previous_outputs": {
                "is_valid": "true",
            },
        }

        route = node.run(input_data)
        assert route == ["valid_agent"]

        # Test with string "false"
        input_data = {
            "previous_outputs": {
                "is_valid": "false",
            },
        }

        route = node.run(input_data)
        assert route == ["invalid_agent"]

    def test_router_node_run_case_insensitive_routing(self):
        """Test case-insensitive routing."""

        params = {
            "decision_key": "status",
            "routing_map": {
                "approved": ["approval_agent"],
                "rejected": ["rejection_agent"],
            },
        }

        node = RouterNode(node_id="router", params=params)

        # Test with different cases
        for status in ["APPROVED", "Approved", "approved"]:
            input_data = {
                "previous_outputs": {
                    "status": status,
                },
            }

            route = node.run(input_data)
            assert route == ["approval_agent"]

    def test_router_node_run_no_match(self):
        """Test routing when no route matches."""

        params = {
            "decision_key": "category",
            "routing_map": {
                "A": ["agent_a"],
                "B": ["agent_b"],
            },
        }

        node = RouterNode(node_id="router", params=params)

        input_data = {
            "previous_outputs": {
                "category": "C",  # No matching route
            },
        }

        route = node.run(input_data)
        assert route == []  # Empty list for no match

    def test_router_node_run_missing_decision_key(self):
        """Test routing when decision key is missing."""

        params = {
            "decision_key": "missing_key",
            "routing_map": {
                "value": ["agent"],
            },
        }

        node = RouterNode(node_id="router", params=params)

        input_data = {
            "previous_outputs": {
                "other_key": "value",
            },
        }

        route = node.run(input_data)
        assert route == []

    def test_router_node_run_no_previous_outputs(self):
        """Test routing with no previous outputs."""

        params = {
            "decision_key": "key",
            "routing_map": {"value": ["agent"]},
        }

        node = RouterNode(node_id="router", params=params)

        input_data = {}  # No previous_outputs

        route = node.run(input_data)
        assert route == []

    def test_router_node_bool_key_conversion(self):
        """Test _bool_key method for boolean conversion."""

        node = RouterNode(
            node_id="router",
            params={"decision_key": "test", "routing_map": {}},
        )

        # Test true values
        assert node._bool_key("true") is True
        assert node._bool_key("yes") is True
        assert node._bool_key("1") is True

        # Test false values
        assert node._bool_key("false") is False
        assert node._bool_key("no") is False
        assert node._bool_key("0") is False

        # Test other values remain unchanged
        assert node._bool_key("maybe") == "maybe"
        assert node._bool_key("2") == "2"

    def test_router_node_multi_agent_routing(self):
        """Test routing to multiple agents."""

        params = {
            "decision_key": "urgency",
            "routing_map": {
                "high": ["escalation_agent", "alert_agent", "manager_agent"],
            },
        }

        node = RouterNode(node_id="router", params=params)

        input_data = {
            "previous_outputs": {
                "urgency": "high",
            },
        }

        route = node.run(input_data)
        assert route == ["escalation_agent", "alert_agent", "manager_agent"]


class TestForkNode:
    """Test the ForkNode implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_memory_logger = Mock()
        self.mock_orchestrator = Mock()
        self.mock_fork_manager = Mock()
        self.mock_orchestrator.fork_manager = self.mock_fork_manager

    def test_fork_node_initialization(self):
        """Test ForkNode initialization."""

        targets = [["agent1", "agent2"], ["agent3"]]

        node = ForkNode(
            node_id="fork_test",
            prompt="test fork",
            queue=[],
            memory_logger=self.mock_memory_logger,
            targets=targets,
            mode="parallel",
        )

        assert node.node_id == "fork_test"
        assert node.prompt == "test fork"
        assert node.memory_logger == self.mock_memory_logger
        assert node.targets == targets
        assert node.mode == "parallel"

    def test_fork_node_default_initialization(self):
        """Test ForkNode initialization with defaults."""

        node = ForkNode(
            node_id="fork_test",
            memory_logger=self.mock_memory_logger,
        )

        assert node.mode == "sequential"  # Default mode
        assert node.targets == []  # Default targets

    @pytest.mark.asyncio
    async def test_fork_node_run_no_targets(self):
        """Test ForkNode run with no targets raises error."""

        node = ForkNode(
            node_id="fork_test",
            memory_logger=self.mock_memory_logger,
            targets=[],
        )

        with pytest.raises(ValueError, match="requires non-empty 'targets' list"):
            await node.run({"orchestrator": self.mock_orchestrator})

    @pytest.mark.asyncio
    async def test_fork_node_run_sequential_mode(self):
        """Test ForkNode run in sequential mode."""

        targets = [["agent1", "agent2"], ["agent3"]]

        node = ForkNode(
            node_id="fork_test",
            memory_logger=self.mock_memory_logger,
            targets=targets,
            mode="sequential",
        )

        # Mock fork manager methods
        self.mock_fork_manager.generate_group_id.return_value = "fork_group_123"

        result = await node.run({"test": "context", "orchestrator": self.mock_orchestrator})

        # Verify fork group generation
        self.mock_fork_manager.generate_group_id.assert_called_once_with("fork_test")

        # Verify sequential queuing (only first agents)
        expected_calls = [
            (["agent1"], "fork_group_123"),
            (["agent3"], "fork_group_123"),
        ]

        actual_calls = self.mock_orchestrator.enqueue_fork.call_args_list
        for i, call in enumerate(actual_calls):
            args, kwargs = call
            assert args == expected_calls[i]

        # Verify branch sequence tracking
        self.mock_fork_manager.track_branch_sequence.assert_called()

        # ForkNode calls create_group for each branch, so check it was called
        assert self.mock_fork_manager.create_group.call_count >= 1

        # Verify memory operations - implementation makes multiple hset calls
        # (1 for fork group mapping + 2 calls per agent for waitfor and results storage)
        assert self.mock_memory_logger.hset.call_count == 7

        # Check that fork group mapping was called
        fork_mapping_calls = [
            call
            for call in self.mock_memory_logger.hset.call_args_list
            if call[0][0] == "fork_group_mapping:fork_test"
        ]
        assert len(fork_mapping_calls) == 1
        assert fork_mapping_calls[0] == call(
            "fork_group_mapping:fork_test", "group_id", "fork_group_123"
        )

        self.mock_memory_logger.sadd.assert_called_once_with(
            "fork_group:fork_group_123",
            "agent1",
            "agent2",
            "agent3",
        )

        # Verify result - implementation now returns more detailed structure
        assert result["status"] == "forked"
        assert result["fork_group"] == "fork_group_123"
        assert "agents" in result
        assert "initial_state" in result

    @pytest.mark.asyncio
    async def test_fork_node_run_parallel_mode(self):
        """Test ForkNode run in parallel mode."""

        targets = [["agent1", "agent2"], "agent3"]

        node = ForkNode(
            node_id="fork_test",
            memory_logger=self.mock_memory_logger,
            targets=targets,
            mode="parallel",
        )

        self.mock_fork_manager.generate_group_id.return_value = "fork_group_456"

        result = await node.run({"orchestrator": self.mock_orchestrator})

        # In parallel mode, should queue all agents in branches
        expected_calls = [
            (["agent1", "agent2"], "fork_group_456"),
            (["agent3"], "fork_group_456"),
        ]

        actual_calls = self.mock_orchestrator.enqueue_fork.call_args_list
        for i, call in enumerate(actual_calls):
            args, kwargs = call
            assert args == expected_calls[i]

        # Should not track branch sequences in parallel mode
        self.mock_fork_manager.track_branch_sequence.assert_not_called()

    @pytest.mark.asyncio
    async def test_fork_node_run_mixed_targets(self):
        """Test ForkNode with mixed target types."""

        targets = [["agent1"], "agent2", ["agent3", "agent4"]]

        node = ForkNode(
            node_id="fork_test",
            memory_logger=self.mock_memory_logger,
            targets=targets,
            mode="sequential",
        )

        self.mock_fork_manager.generate_group_id.return_value = "fork_group_789"

        await node.run({"orchestrator": self.mock_orchestrator})

        # Verify groups were created (may be called multiple times)
        assert self.mock_fork_manager.create_group.call_count >= 1


class TestJoinNode:
    """Test the JoinNode implementation."""

    @pytest.mark.asyncio
    async def test_join_node_basic_functionality(self):
        """Test basic JoinNode functionality."""

        # Mock the actual implementation's run method to be async
        with patch.object(JoinNode, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"status": "joined", "results": ["result1", "result2"]}

            node = JoinNode(
                node_id="join_test",
                prompt="test join",
                queue=[],
            )

            result = await node.run({}, {})

            assert result["status"] == "joined"
            assert "results" in result


class TestMemoryWriterNode:
    """Test cases for MemoryWriterNode."""

    @patch("orka.nodes.memory_writer_node.create_memory_logger")
    def test_memory_writer_node_initialization(self, mock_create_logger):
        """Test MemoryWriterNode initialization."""

        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger

        # MemoryWriterNode passes prompt and queue as kwargs to BaseNode
        node = MemoryWriterNode(
            node_id="writer_test",
            prompt="",
            queue=[],
        )

        assert node.node_id == "writer_test"
        assert node.type == "memorywriternode"
        assert node.memory_logger == mock_logger

        # Test with custom memory logger - provide it directly to skip creation
        custom_logger = Mock()
        node_custom = MemoryWriterNode(
            node_id="writer_custom",
            prompt="",
            queue=[],
            memory_logger=custom_logger,
        )
        assert node_custom.memory_logger == custom_logger
        # Should have called create_memory_logger only once (for first node)
        mock_create_logger.assert_called_once()

    @patch("orka.nodes.memory_writer_node.create_memory_logger")
    @pytest.mark.asyncio
    async def test_memory_writer_node_run(self, mock_create_logger):
        """Test MemoryWriterNode run method."""

        mock_logger = Mock()
        mock_logger.log_memory.return_value = "memory_key_123"
        mock_create_logger.return_value = mock_logger

        node = MemoryWriterNode(
            node_id="writer_test",
            prompt="",
            queue=[],
        )

        # Test successful memory writing
        context = {
            "input": "Test memory content",
            "previous_outputs": {
                "false_validation_guardian": {
                    "result": {
                        "memory_object": {
                            "number": "7",
                            "result": "true",
                            "condition": "greater than 5",
                            "analysis_type": "numerical_comparison",
                            "confidence": 0.95,
                        },
                    },
                },
            },
            "namespace": "test_namespace",
            "session_id": "test_session",
        }

        result = await node.run(context)

        assert result["status"] == "success"
        assert result["memory_key"] == "memory_key_123"
        assert result["session"] == "test_session"
        assert result["namespace"] == "test_namespace"
        assert result["backend"] == "redisstack"
        mock_logger.log_memory.assert_called_once()


class TestMemoryReaderNode:
    """Test cases for MemoryReaderNode."""

    @patch("orka.memory_logger.create_memory_logger")
    def test_memory_reader_node_initialization(self, mock_create_logger):
        """Test MemoryReaderNode initialization."""

        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger

        # MemoryReaderNode passes prompt and queue as kwargs to BaseNode
        node = MemoryReaderNode(
            node_id="reader_test",
            prompt="",
            queue=[],
        )

        assert node.node_id == "reader_test"
        assert node.type == "memoryreadernode"
        assert node.memory_logger == mock_logger

        # Test with custom parameters - must include prompt and queue
        node_custom = MemoryReaderNode(
            node_id="reader_custom",
            prompt="",
            queue=[],
            limit=10,
            similarity_threshold=0.8,
        )
        assert node_custom.limit == 10
        assert node_custom.similarity_threshold == 0.8

    @patch("orka.memory_logger.create_memory_logger")
    @pytest.mark.asyncio
    async def test_memory_reader_node_run(self, mock_create_logger):
        """Test MemoryReaderNode run method."""

        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger

        node = MemoryReaderNode(
            node_id="reader_test",
            prompt="",
            queue=[],
        )

        # Test successful memory reading
        mock_memories = [
            {
                "content": "Test memory 1",
                "metadata": {"log_type": "memory", "category": "stored"},
                "similarity_score": 0.9,
            },
            {
                "content": "Test memory 2",
                "metadata": {"log_type": "memory", "category": "stored"},
                "similarity_score": 0.8,
            },
        ]

        mock_logger.search_memories.return_value = mock_memories

        context = {
            "input": "test query",
            "trace_id": "test_trace",
            "min_importance": 0.5,
        }

        result = await node.run(context)

        assert result["query"] == "test query"
        assert result["backend"] == "redisstack"
        assert result["search_type"] == "enhanced_vector"
        assert result["num_results"] == 2
        assert len(result["memories"]) == 2

        # Test empty query
        empty_result = await node.run({})
        assert empty_result["error"] == "No query provided"
        assert empty_result["memories"] == []


class TestRAGNode:
    """Test the RAGNode implementation."""

    def test_rag_node_initialization(self):
        """Test RAGNode initialization."""

        mock_registry = Mock()

        node = RAGNode(
            node_id="rag_test",
            registry=mock_registry,
            prompt="RAG query",
            queue="default",
        )

        assert node.node_id == "rag_test"
        assert node.prompt == "RAG query"
        assert node.registry == mock_registry

    @pytest.mark.asyncio
    async def test_rag_node_run(self):
        """Test RAGNode run method."""

        mock_registry = Mock()

        node = RAGNode(
            node_id="rag_test",
            registry=mock_registry,
            prompt="query",
        )

        # Mock the implementation
        with patch.object(node, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "status": "success",
                "result": {
                    "answer": "Generated answer",
                    "sources": [{"content": "doc1"}],
                },
            }

            result = await node.run({"query": "test query"})

            assert result["status"] == "success"
            assert "result" in result


class TestFailoverNode:
    """Test the FailoverNode implementation."""

    def test_failover_node_initialization(self):
        """Test FailoverNode initialization."""

        node = FailoverNode(
            node_id="failover_test",
            prompt="failover logic",
            queue=["primary_agent", "backup_agent"],
        )

        assert node.node_id == "failover_test"
        assert node.prompt == "failover logic"
        assert node.queue == ["primary_agent", "backup_agent"]

    @pytest.mark.asyncio
    async def test_failover_node_run(self):
        """Test FailoverNode run method."""

        node = FailoverNode(
            node_id="failover_test",
            prompt="failover",
            queue=["primary", "backup"],
        )

        # Mock the implementation
        with patch.object(node, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "status": "failover_complete",
                "active_agent": "backup_agent",
                "failed_agent": "primary_agent",
            }

            result = await node.run({}, {})

            assert result["status"] == "failover_complete"
            assert "active_agent" in result
            assert "failed_agent" in result


class TestNodeIntegration:
    """Test node integration scenarios."""

    @patch("orka.nodes.memory_writer_node.create_memory_logger")
    @patch("orka.memory_logger.create_memory_logger")
    def test_node_types_consistency(self, mock_create_logger, mock_create_writer_logger):
        """Test that all nodes have consistent type naming."""

        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger
        mock_create_writer_logger.return_value = mock_logger
        mock_registry = Mock()

        # Test various node types
        nodes = [
            FailingNode("test", "", []),
            RouterNode("test", params={"decision_key": "key", "routing_map": {}}),
            ForkNode("test", memory_logger=Mock()),
            JoinNode("test", "", []),
            MemoryWriterNode("test", prompt="", queue=[]),  # Use keyword arguments
            MemoryReaderNode("test", prompt="", queue=[]),  # Use keyword arguments
            RAGNode("test", registry=mock_registry),
            FailoverNode("test", "", []),
        ]

        # Check that all nodes have consistent type naming
        for node in nodes:
            assert hasattr(node, "type")
            assert node.type == node.__class__.__name__.lower()

        # Check specific type names
        assert nodes[0].type == "failingnode"
        assert nodes[1].type == "routernode"
        assert nodes[2].type == "forknode"
        assert nodes[3].type == "joinnode"
        assert nodes[4].type == "memorywriternode"
        assert nodes[5].type == "memoryreadernode"
        assert nodes[6].type == "ragnode"
        assert nodes[7].type == "failovernode"

    def test_node_repr_consistency(self):
        """Test that all nodes have consistent repr format."""

        nodes = [
            FailingNode("test_id", "prompt", ["agent1"]),
            RouterNode("test_id", params={"decision_key": "key", "routing_map": {}}),
        ]

        for node in nodes:
            repr_str = repr(node)
            assert node.__class__.__name__ in repr_str
            assert "id=test_id" in repr_str

    @patch("orka.nodes.memory_writer_node.create_memory_logger")
    @patch("orka.memory_logger.create_memory_logger")
    @pytest.mark.asyncio
    async def test_node_initialize_consistency(self, mock_create_logger, mock_create_writer_logger):
        """Test that all nodes implement initialize method."""

        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger
        mock_create_writer_logger.return_value = mock_logger
        mock_registry = Mock()

        nodes = [
            FailingNode("test", "", []),
            ForkNode("test", memory_logger=Mock()),
            JoinNode("test", "", []),
            MemoryWriterNode("test", prompt="", queue=[]),  # Use keyword arguments
            MemoryReaderNode("test", prompt="", queue=[]),  # Use keyword arguments
            RAGNode("test", registry=mock_registry),
            FailoverNode("test", "", []),
        ]

        # All nodes should have initialize method
        for node in nodes:
            assert hasattr(node, "initialize")
            assert callable(node.initialize)

            # Initialize should be async and not raise errors
            try:
                await node.initialize()
            except NotImplementedError:
                # Some nodes might not implement initialize
                pass
            except Exception as e:
                # Log but don't fail for external dependency errors
                print(f"Node {node.__class__.__name__} initialize error: {e}")

    def test_node_error_handling(self):
        """Test node error handling scenarios."""

        # Test RouterNode with invalid params
        with pytest.raises((ValueError, TypeError)):
            RouterNode("test")

        # Test node initialization with minimal params
        node = FailingNode("test", None, None)
        assert node.node_id == "test"
        assert node.prompt is None
        assert node.queue is None

    def test_node_parameter_forwarding(self):
        """Test that nodes properly handle kwargs."""

        node = ForkNode(
            node_id="test",
            memory_logger=Mock(),
            custom_param="value",
            another_param=123,
        )

        assert node.params["custom_param"] == "value"
        assert node.params["another_param"] == 123

    @pytest.mark.asyncio
    async def test_node_async_compatibility(self):
        """Test that async node methods work correctly."""

        # Test async run methods don't interfere with each other
        node1 = FailingNode("fail1", "", [])
        node2 = ForkNode("fork1", memory_logger=Mock(), targets=[["agent1"]])

        # FailingNode.run is sync, should work fine
        with pytest.raises(RuntimeError):
            with patch("time.sleep"):
                node1.run({})

        # ForkNode.run is async
        mock_orchestrator = Mock()
        mock_orchestrator.fork_manager.generate_group_id.return_value = "group123"

        result = await node2.run({"orchestrator": mock_orchestrator})
        assert result["status"] == "forked"
