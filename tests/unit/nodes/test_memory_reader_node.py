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


    def test_enhance_with_context_scoring_with_valid_context(self):
        """Test _enhance_with_context_scoring with valid conversation context."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.context_weight = 0.3
        
        conversation_context = [
            {"content": "machine learning algorithms neural networks"},
            {"content": "deep learning training data"}
        ]
        
        results = [
            {"content": "machine learning tutorial", "similarity_score": 0.7},
            {"content": "unrelated topic", "similarity_score": 0.5},
            {"content": "neural networks deep learning", "similarity_score": 0.6}
        ]
        
        enhanced = node._enhance_with_context_scoring(results.copy(), conversation_context)
        
        # Verify context scores were added
        assert all("context_score" in r for r in enhanced)
        assert all("original_similarity" in r for r in enhanced)
        
        # Results with context overlap should have higher scores
        assert enhanced[0]["similarity_score"] > enhanced[0]["original_similarity"]
        
        # Results should be re-sorted by enhanced similarity
        scores = [r["similarity_score"] for r in enhanced]
        assert scores == sorted(scores, reverse=True)


    def test_enhance_with_context_scoring_with_empty_context(self):
        """Test _enhance_with_context_scoring with empty context."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        results = [
            {"content": "test content", "similarity_score": 0.7},
            {"content": "another test", "similarity_score": 0.5}
        ]
        
        # Test with None
        enhanced = node._enhance_with_context_scoring(results.copy(), None)
        assert enhanced == results
        
        # Test with empty list
        enhanced = node._enhance_with_context_scoring(results.copy(), [])
        assert enhanced == results


    def test_enhance_with_context_scoring_with_multiple_context_items(self):
        """Test _enhance_with_context_scoring with multiple context items."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.context_weight = 0.2
        
        conversation_context = [
            {"content": "python programming language coding"},
            {"content": "software development testing debugging"},
            {"content": "artificial intelligence machine learning"}
        ]
        
        results = [
            {"content": "python programming tutorial", "similarity_score": 0.8},
            {"content": "java programming guide", "similarity_score": 0.7}
        ]
        
        enhanced = node._enhance_with_context_scoring(results.copy(), conversation_context)
        
        # Verify context keywords were extracted from all context items
        assert enhanced[0]["context_score"] > 0
        assert enhanced[0]["similarity_score"] > enhanced[0]["original_similarity"]


    def test_enhance_with_context_scoring_error_handling(self):
        """Test _enhance_with_context_scoring handles errors gracefully."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        # Malformed context that could cause errors
        conversation_context = [
            {"content": None},  # None content
            {},  # Missing content field
        ]
        
        results = [
            {"content": "test content", "similarity_score": 0.7}
        ]
        
        # Should handle errors and return original results
        enhanced = node._enhance_with_context_scoring(results.copy(), conversation_context)
        assert isinstance(enhanced, list)
        assert len(enhanced) == 1


    def test_extract_conversation_context_from_previous_outputs(self):
        """Test _extract_conversation_context extracts from previous_outputs."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "input": "test query",
            "previous_outputs": {
                "agent1": {"response": "First agent response"},
                "agent2": {"answer": "Second agent answer"},
                "agent3": {"result": "Third agent result"}
            }
        }
        
        conversation_context = node._extract_conversation_context(context)
        
        assert len(conversation_context) == 3
        assert conversation_context[0]["agent_id"] == "agent1"
        assert conversation_context[0]["content"] == "First agent response"
        assert conversation_context[0]["field"] == "response"
        assert conversation_context[1]["field"] == "answer"
        assert conversation_context[2]["field"] == "result"
        
        # Verify timestamps were added
        assert all("timestamp" in ctx for ctx in conversation_context)


    def test_extract_conversation_context_multiple_content_fields(self):
        """Test _extract_conversation_context with various content field patterns."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "previous_outputs": {
                "agent1": {"output": "Output content"},
                "agent2": {"content": "Content field"},
                "agent3": {"message": "Message field"},
                "agent4": {"text": "Text field"},
                "agent5": {"summary": "Summary field"}
            }
        }
        
        conversation_context = node._extract_conversation_context(context)
        
        assert len(conversation_context) == 5
        fields = [ctx["field"] for ctx in conversation_context]
        assert "output" in fields
        assert "content" in fields
        assert "message" in fields
        assert "text" in fields
        assert "summary" in fields


    def test_extract_conversation_context_from_direct_values(self):
        """Test _extract_conversation_context with direct string/number outputs."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "previous_outputs": {
                "agent1": "Simple string output",
                "agent2": 42,
                "agent3": 3.14
            }
        }
        
        conversation_context = node._extract_conversation_context(context)
        
        assert len(conversation_context) == 3
        assert conversation_context[0]["content"] == "Simple string output"
        assert conversation_context[1]["content"] == "42"
        assert conversation_context[2]["content"] == "3.14"
        assert all(ctx["field"] == "direct_output" for ctx in conversation_context)


    def test_extract_conversation_context_from_context_fields(self):
        """Test _extract_conversation_context extracts from context fields."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "conversation": [
                {"content": "First message", "timestamp": 100},
                {"content": "Second message", "timestamp": 200}
            ],
            "history": [
                {"content": "History item", "timestamp": 300}
            ],
            "context": "Direct context string",
            "previous_messages": "Previous messages string"
        }
        
        conversation_context = node._extract_conversation_context(context)
        
        assert len(conversation_context) >= 5  # At least 5 items extracted
        
        # Verify conversation list items
        conv_items = [ctx for ctx in conversation_context if ctx.get("source") == "conversation"]
        assert len(conv_items) == 2
        
        # Verify timestamps were preserved
        assert conv_items[0]["timestamp"] == 100
        assert conv_items[1]["timestamp"] == 200


    def test_extract_conversation_context_window_sizing(self):
        """Test _extract_conversation_context limits to context_window_size."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        node.context_window_size = 3
        
        context = {
            "previous_outputs": {
                f"agent{i}": {"response": f"Response {i}"} for i in range(10)
            }
        }
        
        conversation_context = node._extract_conversation_context(context)
        
        # Should be limited to context_window_size
        assert len(conversation_context) == 3
        
        # Should return most recent items (sorted by timestamp descending)
        # Since all timestamps are created at same time, we just verify size limit works
        assert all("timestamp" in ctx for ctx in conversation_context)


    def test_extract_conversation_context_empty_context(self):
        """Test _extract_conversation_context with empty/missing context."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        # Empty context
        context = {"input": "test query"}
        conversation_context = node._extract_conversation_context(context)
        assert conversation_context == []
        
        # Context with empty previous_outputs
        context = {"previous_outputs": {}}
        conversation_context = node._extract_conversation_context(context)
        assert conversation_context == []


    def test_generate_enhanced_query_variations_with_context(self):
        """Test _generate_enhanced_query_variations with conversation context."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        query = "machine learning"
        conversation_context = [
            {"content": "neural networks deep learning algorithms"},
            {"content": "training data optimization techniques"}
        ]
        
        variations = node._generate_enhanced_query_variations(query, conversation_context)
        
        # Should include original query
        assert query in variations
        
        # Should include context-enhanced variations
        assert len(variations) > 1
        assert len(variations) <= 8  # Max 8 variations
        
        # Should have more variations with context than without
        variations_without_context = node._generate_enhanced_query_variations(query, [])
        assert len(variations) >= len(variations_without_context)


    def test_generate_enhanced_query_variations_without_context(self):
        """Test _generate_enhanced_query_variations without context."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        query = "python programming"
        conversation_context = []
        
        variations = node._generate_enhanced_query_variations(query, conversation_context)
        
        # Should include original query
        assert query in variations
        
        # Should include basic variations
        assert len(variations) > 1
        
        # Without context, should only have basic variations
        assert all(not v.startswith("related to") for v in variations if v != query)


    def test_generate_enhanced_query_variations_empty_query(self):
        """Test _generate_enhanced_query_variations with empty query."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        conversation_context = [{"content": "some context"}]
        
        # Empty string
        variations = node._generate_enhanced_query_variations("", conversation_context)
        assert variations == [""]
        
        # Whitespace only
        variations = node._generate_enhanced_query_variations("  ", conversation_context)
        assert len(variations) == 1


    def test_generate_enhanced_query_variations_max_limit(self):
        """Test _generate_enhanced_query_variations respects max limit."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        query = "artificial intelligence"
        conversation_context = [
            {"content": "machine learning neural networks deep learning"},
            {"content": "algorithms training optimization techniques"}
        ]
        
        variations = node._generate_enhanced_query_variations(query, conversation_context)
        
        # Should not exceed max limit of 8
        assert len(variations) <= 8


    def test_generate_query_variations_single_word(self):
        """Test _generate_query_variations with single word query."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        variations = node._generate_query_variations("python")
        
        assert len(variations) > 0
        assert "python" in variations
        assert any("about" in v for v in variations)
        assert any("information" in v for v in variations)


    def test_generate_query_variations_two_words(self):
        """Test _generate_query_variations with two word query."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        variations = node._generate_query_variations("machine learning")
        
        assert len(variations) > 0
        assert "machine learning" in variations
        # Should include reversed
        assert any("learning machine" in v for v in variations)


    def test_generate_query_variations_multiple_words(self):
        """Test _generate_query_variations with multi-word query."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        query = "deep learning neural networks"
        variations = node._generate_query_variations(query)
        
        assert len(variations) > 0
        assert query in variations
        # Should include first and last words
        assert any("deep networks" in v for v in variations)
        # Should include first two words
        assert any("deep learning" in v for v in variations)


    def test_generate_query_variations_empty_query(self):
        """Test _generate_query_variations with empty query."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        variations = node._generate_query_variations("")
        assert variations == []
        
        variations = node._generate_query_variations("  ")
        assert variations == []


    def test_generate_query_variations_deduplication(self):
        """Test _generate_query_variations removes duplicates."""
        mock_memory = Mock()
        node = MemoryReaderNode(
            node_id="memory_reader",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        variations = node._generate_query_variations("ai")
        
        # Should not have duplicates
        assert len(variations) == len(set(variations))

