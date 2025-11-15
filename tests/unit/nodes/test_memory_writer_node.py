"""Unit tests for orka.nodes.memory_writer_node."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.nodes.memory_writer_node import MemoryWriterNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestMemoryWriterNode:
    """Test suite for MemoryWriterNode class."""

    def test_init(self):
        """Test MemoryWriterNode initialization."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            namespace="test_namespace"
        )
        
        assert node.node_id == "memory_writer"
        assert node.namespace == "test_namespace"

    def test_init_without_memory_logger(self):
        """Test MemoryWriterNode initialization without memory logger."""
        with patch('orka.nodes.memory_writer_node.create_memory_logger') as mock_create:
            mock_memory = Mock()
            mock_create.return_value = mock_memory
            
            node = MemoryWriterNode(
                node_id="memory_writer",
                prompt="Test prompt",
                queue=[],
                namespace="test"
            )
            
            # Verify create_memory_logger was called
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_impl(self):
        """Test _run_impl method."""
        mock_memory = Mock()
        mock_memory.log = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            namespace="test"
        )
        
        context = {
            "input": "Test content to store",
            "formatted_prompt": "Test content to store"
        }
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)
        assert "status" in result

    def test_merge_metadata(self):
        """Test _merge_metadata method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            metadata={"source": "test"}
        )
        
        context = {
            "metadata": {"additional": "data"}
        }
        
        merged = node._merge_metadata(context)
        
        assert isinstance(merged, dict)
        assert "source" in merged

    def test_extract_memory_content(self):
        """Test _extract_memory_content method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "input": "Test content",
            "formatted_prompt": "Test content"
        }
        
        content = node._extract_memory_content(context)
        
        assert isinstance(content, str)
        assert len(content) > 0

    def test_calculate_importance_score(self):
        """Test _calculate_importance_score method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        score = node._calculate_importance_score(
            "Test content",
            {"event_type": "write"}
        )
        
        assert 0.0 <= score <= 1.0

    def test_classify_memory_type(self):
        """Test _classify_memory_type method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        memory_type = node._classify_memory_type(
            {"event_type": "write"},
            0.8
        )
        
        assert memory_type in ["short_term", "long_term"]

    def test_get_expiry_hours(self):
        """Test _get_expiry_hours method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        hours = node._get_expiry_hours("long_term", 0.8)
        
        assert isinstance(hours, float)
        assert hours > 0

