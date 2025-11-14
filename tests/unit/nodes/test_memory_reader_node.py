"""Unit tests for orka.nodes.memory_reader_node."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.nodes.memory_reader_node import MemoryReaderNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestMemoryReaderNode:
    """Test suite for MemoryReaderNode class."""

    def test_init(self):
        """Test MemoryReaderNode initialization."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            namespace="test_namespace",
            limit=5
        )
        
        assert node.node_id == "memory_reader"
        assert node.namespace == "test_namespace"
        assert node.limit == 5

    def test_init_without_memory_logger(self):
        """Test MemoryReaderNode initialization without memory logger."""
        with patch('orka.memory_logger.create_memory_logger') as mock_create:
            mock_memory = Mock()
            mock_create.return_value = mock_memory
            
            node = MemoryReaderNode(
                node_id="memory_reader",
                prompt="Test prompt",
                queue=[],
                namespace="test"
            )
            
            assert node.memory_logger == mock_memory

    @pytest.mark.asyncio
    async def test_run_impl(self):
        """Test _run_impl method."""
        mock_memory = Mock()
        mock_memory.search_memories = AsyncMock(return_value=[
            {"content": "Memory 1", "score": 0.9},
            {"content": "Memory 2", "score": 0.8},
        ])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            namespace="test"
        )
        node.embedder = mock_embedder
        
        context = {
            "input": "test query",
            "formatted_prompt": "test query"
        }
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)
        assert "memories" in result or "results" in result

    def test_update_search_metrics(self):
        """Test _update_search_metrics method."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        node._update_search_metrics(0.5, 10)
        
        assert node._search_metrics["total_results_found"] == 10

    def test_get_search_metrics(self):
        """Test get_search_metrics method."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        metrics = node.get_search_metrics()
        
        assert isinstance(metrics, dict)
        assert "hnsw_searches" in metrics

    def test_apply_temporal_ranking(self):
        """Test _apply_temporal_ranking method."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            enable_temporal_ranking=True
        )
        
        results = [
            {"content": "Old", "timestamp": "2024-01-01T00:00:00"},
            {"content": "New", "timestamp": "2024-01-02T00:00:00"},
        ]
        
        ranked = node._apply_temporal_ranking(results)
        
        assert isinstance(ranked, list)

    def test_filter_by_category(self):
        """Test _filter_by_category method."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            memory_category_filter="stored"
        )
        
        memories = [
            {"category": "stored", "content": "Memory 1"},
            {"category": "log", "content": "Memory 2"},
        ]
        
        filtered = node._filter_by_category(memories)
        
        assert isinstance(filtered, list)

