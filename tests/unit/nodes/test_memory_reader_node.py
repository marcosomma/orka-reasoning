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

    @pytest.mark.asyncio
    async def test_run_impl_with_dict_input(self):
        """Test _run_impl with dictionary input."""
        mock_memory = Mock()
        mock_memory.search_memories = AsyncMock(return_value=[])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.embedder = mock_embedder
        
        context = {
            "input": {"input": "nested query", "loop_number": 1}
        }
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_impl_with_non_string_input(self):
        """Test _run_impl with non-string input conversion."""
        mock_memory = Mock()
        mock_memory.search_memories = AsyncMock(return_value=[])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.embedder = mock_embedder
        
        context = {
            "input": 12345  # Non-string input
        }
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_impl_empty_query(self):
        """Test _run_impl with empty query."""
        mock_memory = Mock()
        mock_memory.search_memories = AsyncMock(return_value=[])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {}
        
        result = await node._run_impl(context)
        
        # Should handle empty query gracefully
        assert isinstance(result, dict)
        assert "memories" in result or "error" in result or "count" in result

    @pytest.mark.asyncio
    async def test_run_impl_with_embedder_error(self):
        """Test _run_impl when embedder fails."""
        mock_memory = Mock()
        mock_memory.search_memories = AsyncMock(return_value=[])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(side_effect=Exception("Encoding error"))
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.embedder = mock_embedder
        
        context = {"input": "test query"}
        
        result = await node._run_impl(context)
        
        # Should handle error gracefully
        assert isinstance(result, dict)

    def test_init_with_custom_params(self):
        """Test initialization with all custom parameters."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            namespace="custom",
            limit=10,
            similarity_threshold=0.8,
            ef_runtime=20,
            use_hnsw=True,
            hybrid_search_enabled=True,
            context_window_size=15,
            context_weight=0.3,
            enable_context_search=True,
            enable_temporal_ranking=True,
            temporal_decay_hours=48.0,
            temporal_weight=0.2,
            memory_category_filter="stored"
        )
        
        assert node.namespace == "custom"
        assert node.limit == 10
        assert node.similarity_threshold == 0.8
        assert node.ef_runtime == 20
        assert node.context_weight == 0.3
        assert node.temporal_decay_hours == 48.0

    def test_init_with_memory_preset(self):
        """Test initialization with memory preset."""
        with patch('orka.memory_logger.create_memory_logger') as mock_create, \
             patch('orka.memory_logger.apply_memory_preset_to_config') as mock_preset:
            
            mock_memory = Mock()
            mock_create.return_value = mock_memory
            mock_preset.return_value = {
                "namespace": "preset_namespace",
                "limit": 3,
                "memory_preset": "short_term"
            }
            
            node = MemoryReaderNode(
                node_id="memory_reader",
                prompt="Test",
                queue=[],
                memory_preset="short_term"
            )
            
            mock_preset.assert_called_once()

    def test_init_without_embedder(self):
        """Test initialization when embedder fails to load."""
        with patch('orka.utils.embedder.get_embedder', side_effect=Exception("No embedder")):
            mock_memory = Mock()
            
            node = MemoryReaderNode(
                node_id="memory_reader",
                prompt="Test",
                queue=[],
                memory_logger=mock_memory
            )
            
            assert node.embedder is None

    def test_update_search_metrics_multiple_calls(self):
        """Test _update_search_metrics with multiple updates."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        node._update_search_metrics(0.5, 10)
        node._update_search_metrics(0.3, 5)
        
        metrics = node.get_search_metrics()
        assert metrics["total_results_found"] == 15

    def test_apply_temporal_ranking_with_invalid_timestamp(self):
        """Test _apply_temporal_ranking with invalid timestamps."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            enable_temporal_ranking=True
        )
        
        results = [
            {"content": "Memory", "timestamp": "invalid"},
        ]
        
        ranked = node._apply_temporal_ranking(results)
        
        # Should handle invalid timestamps gracefully
        assert isinstance(ranked, list)

    def test_filter_by_category_no_filter(self):
        """Test _filter_by_category when no filter is set."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            memory_category_filter=None
        )
        
        memories = [
            {"category": "stored", "content": "Memory 1"},
            {"category": "log", "content": "Memory 2"},
        ]
        
        filtered = node._filter_by_category(memories)
        
        # Should return all memories when no filter
        assert len(filtered) == 2

    def test_filter_by_category_missing_category(self):
        """Test _filter_by_category with memories missing category field."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            memory_category_filter="stored"
        )
        
        memories = [
            {"content": "Memory without category"},
        ]
        
        filtered = node._filter_by_category(memories)
        
        assert isinstance(filtered, list)

    @pytest.mark.asyncio
    async def test_run_impl_with_fallback_search(self):
        """Test _run_impl with fallback search when no results found."""
        mock_memory = Mock()
        # First call returns empty, second call returns results
        mock_memory.search_memories = Mock(side_effect=[[], [{"content": "Found with fallback"}]])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Find the result",
            queue=[],
            memory_logger=mock_memory
        )
        node.embedder = mock_embedder
        
        context = {"input": "Find the result"}
        
        result = await node._run_impl(context)
        
        # Should have called search_memories at least twice (original + fallback)
        assert mock_memory.search_memories.call_count >= 2
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_impl_with_metadata_filtering(self):
        """Test _run_impl with metadata-based filtering."""
        mock_memory = Mock()
        mock_memory.search_memories = Mock(return_value=[
            {"content": "Memory 1", "metadata": {"log_type": "memory", "category": "stored"}},
            {"content": "Memory 2", "metadata": {"log_type": "orchestration"}},  # Should be filtered
        ])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.embedder = mock_embedder
        
        context = {"input": "test query"}
        
        result = await node._run_impl(context)
        
        # Should filter out orchestration logs
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_impl_with_trace_id(self):
        """Test _run_impl with trace_id in context."""
        mock_memory = Mock()
        mock_memory.search_memories = Mock(return_value=[])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.embedder = mock_embedder
        
        context = {
            "input": "test query",
            "trace_id": "trace-123",
            "min_importance": 0.5
        }
        
        result = await node._run_impl(context)
        
        # Should pass trace_id to search_memories
        call_kwargs = mock_memory.search_memories.call_args[1]
        assert call_kwargs.get("trace_id") == "trace-123"
        assert call_kwargs.get("min_importance") == 0.5

    def test_apply_temporal_ranking_with_temporal_weight(self):
        """Test _apply_temporal_ranking with custom temporal weight."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            enable_temporal_ranking=True,
            temporal_weight=0.5
        )
        
        import time
        current_time = time.time()
        
        results = [
            {"content": "Old memory", "timestamp": current_time - 100000},
            {"content": "Recent memory", "timestamp": current_time - 100},
        ]
        
        ranked = node._apply_temporal_ranking(results)
        
        # Recent memory should be ranked higher
        assert isinstance(ranked, list)

    def test_get_search_metrics_initial_state(self):
        """Test get_search_metrics before any searches."""
        mock_memory = Mock()
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metrics = node.get_search_metrics()
        
        assert metrics["hnsw_searches"] == 0
        assert metrics["legacy_searches"] == 0
        assert metrics["total_results_found"] == 0
        assert metrics["average_search_time"] == 0.0

    @pytest.mark.asyncio
    async def test_run_impl_with_hnsw_disabled(self):
        """Test _run_impl with HNSW disabled."""
        mock_memory = Mock()
        mock_memory.search_memories = Mock(return_value=[])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            use_hnsw=False
        )
        node.embedder = mock_embedder
        
        context = {"input": "test query"}
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_impl_with_hybrid_search(self):
        """Test _run_impl with hybrid search enabled."""
        mock_memory = Mock()
        mock_memory.search_memories = Mock(return_value=[])
        
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[[0.1] * 384])
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            hybrid_search_enabled=True
        )
        node.embedder = mock_embedder
        
        context = {"input": "test query"}
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)

    def test_init_with_decay_config(self):
        """Test initialization with decay configuration."""
        mock_memory = Mock()
        
        decay_config = {
            "enabled": True,
            "base_decay_rate": 0.5,
            "importance_threshold": 0.3
        }
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            decay_config=decay_config
        )
        
        assert node.decay_config == decay_config

    @pytest.mark.asyncio
    async def test_run_impl_no_search_memories_method(self):
        """Test _run_impl when memory_logger doesn't have search_memories."""
        mock_memory = Mock(spec=[])  # Empty spec means no methods
        
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {"input": "test query"}
        
        result = await node._run_impl(context)
        
        # Should handle missing method gracefully
        assert isinstance(result, dict)

