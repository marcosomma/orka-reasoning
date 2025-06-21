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

import json
import time
from unittest.mock import patch

import numpy as np
import pytest

from orka.nodes.memory_reader_node import MemoryReaderNode


class MockEmbedder:
    """Mock embedder for testing."""

    async def encode(self, text):
        """Return a simple vector based on text hash for consistency."""
        # Create a deterministic vector based on text
        text_hash = hash(text) % 1000
        return np.array(
            [float(text_hash % 10), float((text_hash // 10) % 10), float((text_hash // 100) % 10)],
        )


class MockRedisClient:
    """Mock Redis client that supports enhanced memory operations."""

    def __init__(self):
        self.data = {}
        self.streams = {}
        self.vectors = {}

    async def keys(self, pattern):
        """Return keys matching pattern."""
        if pattern == "*":
            return list(self.data.keys())
        prefix = pattern.replace("*", "")
        return [k for k in self.data.keys() if k.startswith(prefix)]

    async def hget(self, key, field):
        """Get hash field value."""
        if key not in self.data:
            return None
        return self.data[key].get(field)

    async def hset(self, key, field, value):
        """Set hash field value."""
        if key not in self.data:
            self.data[key] = {}
        self.data[key][field] = value
        return 1

    async def xadd(self, stream_key, entry):
        """Add entry to stream."""
        if stream_key not in self.streams:
            self.streams[stream_key] = []
        entry_id = f"{int(time.time() * 1000)}-0"
        self.streams[stream_key].append((entry_id, entry))
        return entry_id

    async def xrange(self, stream_key):
        """Get stream entries."""
        return self.streams.get(stream_key, [])

    def add_memory(self, key, content, metadata=None, vector=None, namespace="default"):
        """Helper to add test memories."""
        self.data[key] = {
            "content": content.encode() if isinstance(content, str) else content,
            "namespace": namespace.encode() if isinstance(namespace, str) else namespace,
            "metadata": json.dumps(metadata or {}).encode(),
        }
        if vector is not None:
            self.data[key]["vector"] = vector

    def add_stream_memory(self, stream_key, content, metadata=None, timestamp=None):
        """Helper to add stream memories."""
        payload = {
            "content": content,
            "metadata": metadata or {},
        }
        entry = {
            "payload": json.dumps(payload).encode(),
            "ts": str(int((timestamp or time.time()) * 1000)).encode(),
        }
        if stream_key not in self.streams:
            self.streams[stream_key] = []
        entry_id = f"{int(time.time() * 1000)}-0"
        self.streams[stream_key].append((entry_id, entry))


def to_bytes(vector):
    """Convert vector to bytes (mock implementation)."""
    return np.array(vector).tobytes()


def from_bytes(vector_bytes):
    """Convert bytes back to vector (mock implementation)."""
    return np.frombuffer(vector_bytes, dtype=np.float64)


@pytest.fixture
def mock_redis():
    """Fixture providing mock Redis client."""
    return MockRedisClient()


@pytest.fixture
def memory_reader():
    """Fixture providing enhanced memory reader node."""
    with patch("orka.nodes.memory_reader_node.get_embedder") as mock_get_embedder:
        mock_get_embedder.return_value = MockEmbedder()
        with patch("orka.nodes.memory_reader_node.redis.from_url") as mock_redis_url:
            mock_redis = MockRedisClient()
            mock_redis_url.return_value = mock_redis

            reader = MemoryReaderNode(
                node_id="test_reader",
                namespace="test_namespace",
                context_weight=0.3,
                temporal_weight=0.2,
                enable_context_search=True,
                enable_temporal_ranking=True,
                context_window_size=5,
                temporal_decay_hours=24,
            )
            reader.redis = mock_redis

            # Pre-populate the mock with some test data to avoid warnings
            mock_redis.add_memory(
                "mem:test1",
                "test content",
                metadata={"test": "data"},
                vector=np.array([0.1, 0.2, 0.3]),
                namespace="test_namespace",
            )

            return reader


@pytest.fixture
def sample_context():
    """Fixture providing sample conversation context."""
    return [
        {
            "content": "We were discussing machine learning algorithms yesterday",
            "timestamp": time.time() - 3600,  # 1 hour ago
            "role": "user",
        },
        {
            "content": "Neural networks are a type of machine learning model",
            "timestamp": time.time() - 3000,  # 50 minutes ago
            "role": "assistant",
        },
        {
            "content": "What about deep learning applications?",
            "timestamp": time.time() - 1800,  # 30 minutes ago
            "role": "user",
        },
    ]


class TestContextExtraction:
    """Test context extraction functionality."""

    def test_extract_conversation_context_from_history(self, memory_reader):
        """Test extracting context from conversation history."""
        context = {
            "history": [
                {"content": "Hello", "role": "user", "timestamp": time.time() - 300},
                {"content": "Hi there", "role": "assistant", "timestamp": time.time() - 200},
                {"content": "How are you?", "role": "user", "timestamp": time.time() - 100},
            ],
        }

        conversation_context = memory_reader._extract_conversation_context(context)

        assert len(conversation_context) == 3
        assert conversation_context[0]["content"] == "Hello"
        assert conversation_context[0]["role"] == "user"
        assert conversation_context[2]["content"] == "How are you?"

    def test_extract_conversation_context_from_outputs(self, memory_reader):
        """Test extracting context from previous outputs."""
        context = {
            "outputs": {
                "previous_node": {
                    "memories": [
                        {"content": "Previous memory 1", "ts": time.time() - 600},
                        {"content": "Previous memory 2", "ts": time.time() - 300},
                    ],
                },
            },
        }

        conversation_context = memory_reader._extract_conversation_context(context)

        assert len(conversation_context) == 2
        assert conversation_context[0]["content"] == "Previous memory 1"
        assert conversation_context[0]["role"] == "memory"

    def test_extract_conversation_context_window_size_limit(self, memory_reader):
        """Test that context window size is respected."""
        # Set a smaller window size
        memory_reader.context_window_size = 2

        context = {
            "history": [
                {"content": f"Message {i}", "role": "user", "timestamp": time.time() - i * 100}
                for i in range(5)
            ],
        }

        conversation_context = memory_reader._extract_conversation_context(context)

        # Should only keep the last 2 items
        assert len(conversation_context) == 2
        assert conversation_context[0]["content"] == "Message 3"
        assert conversation_context[1]["content"] == "Message 4"


class TestEnhancedQueryVariations:
    """Test enhanced query variation generation."""

    def test_generate_enhanced_query_variations_basic(self, memory_reader):
        """Test basic query variation generation."""
        query = "What is machine learning?"
        context = []

        variations = memory_reader._generate_enhanced_query_variations(query, context)

        assert query in variations
        assert "machine learning" in variations  # Entity extraction
        assert "machine learning definition" in variations
        assert len(variations) <= 10  # Limit check

    def test_generate_enhanced_query_variations_with_context(self, memory_reader, sample_context):
        """Test query variations with conversation context."""
        query = "Tell me about AI"

        variations = memory_reader._generate_enhanced_query_variations(query, sample_context)

        # Should include original query
        assert query in variations

        # Should include context-enhanced variations
        context_enhanced = [v for v in variations if "algorithms" in v or "neural" in v]
        assert len(context_enhanced) > 0

    def test_generate_enhanced_query_variations_when_questions(self, memory_reader):
        """Test variations for 'when' questions."""
        query = "when did neural networks become popular?"
        context = []

        variations = memory_reader._generate_enhanced_query_variations(query, context)

        # Should include temporal variations
        assert any("history" in v for v in variations)
        assert any("timeline" in v for v in variations)

    def test_generate_enhanced_query_variations_limit(self, memory_reader):
        """Test that variations are limited to prevent too many API calls."""
        query = "test query"
        # Create a large context
        context = [
            {
                "content": f"Context item {i} with many words",
                "timestamp": time.time(),
                "role": "user",
            }
            for i in range(20)
        ]

        variations = memory_reader._generate_enhanced_query_variations(query, context)

        assert len(variations) <= 10


class TestContextAwareVectorSearch:
    """Test context-aware vector search functionality."""

    @pytest.mark.asyncio
    async def test_context_aware_vector_search_basic(self, memory_reader):
        """Test basic context-aware vector search."""
        # Setup test data
        memory_reader.redis.add_memory(
            "mem:1",
            "Machine learning is a subset of AI",
            {"confidence": 0.9},
            to_bytes([1.0, 2.0, 3.0]),
            namespace="test_namespace",
        )

        query_embedding = np.array([1.1, 2.1, 3.1])
        namespace = "test_namespace"
        context = []

        with patch("orka.nodes.memory_reader_node.from_bytes", side_effect=from_bytes):
            results = await memory_reader._context_aware_vector_search(
                query_embedding,
                namespace,
                context,
            )

        assert len(results) > 0
        assert results[0]["content"] == "Machine learning is a subset of AI"
        assert "primary_similarity" in results[0]
        assert "context_similarity" in results[0]

    @pytest.mark.asyncio
    async def test_context_aware_vector_search_with_context(self, memory_reader, sample_context):
        """Test vector search with conversation context."""
        # Setup test data
        memory_reader.redis.add_memory(
            "mem:1",
            "Deep learning uses neural networks with multiple layers",
            {"confidence": 0.9},
            to_bytes([1.0, 2.0, 3.0]),
            namespace="test_namespace",
        )

        query_embedding = np.array([1.1, 2.1, 3.1])
        namespace = "test_namespace"

        with patch("orka.nodes.memory_reader_node.from_bytes", side_effect=from_bytes):
            results = await memory_reader._context_aware_vector_search(
                query_embedding,
                namespace,
                sample_context,
            )

        assert len(results) > 0
        result = results[0]
        assert "similarity" in result
        assert "primary_similarity" in result
        assert "context_similarity" in result
        assert result["match_type"] == "context_aware_vector"

    @pytest.mark.asyncio
    async def test_generate_context_vector(self, memory_reader, sample_context):
        """Test context vector generation."""
        context_vector = await memory_reader._generate_context_vector(sample_context)

        assert context_vector is not None
        assert isinstance(context_vector, np.ndarray)
        assert len(context_vector) == 3  # Based on our mock embedder

    @pytest.mark.asyncio
    async def test_generate_context_vector_empty_context(self, memory_reader):
        """Test context vector generation with empty context."""
        context_vector = await memory_reader._generate_context_vector([])

        assert context_vector is None


class TestEnhancedKeywordSearch:
    """Test enhanced keyword search functionality."""

    @pytest.mark.asyncio
    async def test_enhanced_keyword_search_basic(self, memory_reader):
        """Test basic enhanced keyword search."""
        # Setup test data
        memory_reader.redis.add_memory(
            "mem:1",
            "Machine learning algorithms are powerful tools",
            {"source": "test"},
            namespace="test_namespace",
        )

        namespace = "test_namespace"
        query = "machine learning"
        context = []

        results = await memory_reader._enhanced_keyword_search(namespace, query, context)

        assert len(results) > 0
        assert results[0]["content"] == "Machine learning algorithms are powerful tools"
        assert results[0]["match_type"] == "enhanced_keyword"
        assert "query_overlap" in results[0]
        assert "context_overlap" in results[0]

    @pytest.mark.asyncio
    async def test_enhanced_keyword_search_with_context(self, memory_reader, sample_context):
        """Test keyword search with conversation context."""
        # Setup test data that matches context keywords
        memory_reader.redis.add_memory(
            "mem:1",
            "Neural networks are used in deep learning applications",
            {"source": "test"},
            namespace="test_namespace",
        )

        namespace = "test_namespace"
        query = "artificial intelligence"  # Different from content but context should help

        results = await memory_reader._enhanced_keyword_search(namespace, query, sample_context)

        # Should find the memory due to context overlap (neural, learning)
        assert len(results) > 0
        result = results[0]
        assert result["context_overlap"] > 0

    @pytest.mark.asyncio
    async def test_enhanced_keyword_search_similarity_calculation(self, memory_reader):
        """Test enhanced similarity calculation."""
        memory_reader.redis.add_memory(
            "mem:1",
            "Machine learning and artificial intelligence",
            {"source": "test"},
            namespace="test_namespace",
        )

        namespace = "test_namespace"
        query = "machine learning"
        context = [{"content": "artificial intelligence", "timestamp": time.time(), "role": "user"}]

        results = await memory_reader._enhanced_keyword_search(namespace, query, context)

        assert len(results) > 0
        result = results[0]
        # Should have both query and context overlap
        assert result["query_overlap"] > 0
        assert result["context_overlap"] > 0
        # Similarity should be enhanced by context
        assert result["similarity"] > result["query_overlap"] / 2  # Basic query similarity


class TestContextAwareStreamSearch:
    """Test context-aware stream search functionality."""

    @pytest.mark.asyncio
    async def test_context_aware_stream_search_basic(self, memory_reader):
        """Test basic context-aware stream search."""
        # Setup stream data
        stream_key = "test_stream"
        memory_reader.redis.add_stream_memory(
            stream_key,
            "Machine learning is transforming technology",
            {"source": "conversation"},
        )

        query = "machine learning"
        query_embedding = np.array([1.0, 2.0, 3.0])
        context = []

        results = await memory_reader._context_aware_stream_search(
            stream_key,
            query,
            query_embedding,
            context,
        )

        assert len(results) > 0
        result = results[0]
        assert result["content"] == "Machine learning is transforming technology"
        assert result["match_type"] == "context_aware_stream"
        assert "primary_similarity" in result
        assert "context_similarity" in result

    @pytest.mark.asyncio
    async def test_context_aware_stream_search_exact_match(self, memory_reader):
        """Test stream search with exact keyword match."""
        stream_key = "test_stream"
        content = "Machine learning is powerful"
        memory_reader.redis.add_stream_memory(stream_key, content)

        query = "machine learning"
        query_embedding = np.array([1.0, 2.0, 3.0])
        context = []

        results = await memory_reader._context_aware_stream_search(
            stream_key,
            query,
            query_embedding,
            context,
        )

        assert len(results) > 0
        result = results[0]
        assert result["primary_similarity"] == 1.0  # Exact match

    @pytest.mark.asyncio
    async def test_context_aware_stream_search_with_context(self, memory_reader, sample_context):
        """Test stream search with conversation context."""
        stream_key = "test_stream"
        memory_reader.redis.add_stream_memory(
            stream_key,
            "Deep neural networks have many applications",
            {"source": "conversation"},
        )

        query = "AI applications"
        query_embedding = np.array([1.0, 2.0, 3.0])

        results = await memory_reader._context_aware_stream_search(
            stream_key,
            query,
            query_embedding,
            sample_context,
        )

        assert len(results) > 0
        result = results[0]
        # Should have context similarity due to "neural networks" in context
        assert result["context_similarity"] >= 0


class TestHybridScoring:
    """Test hybrid scoring functionality."""

    def test_apply_hybrid_scoring_basic(self, memory_reader):
        """Test basic hybrid scoring."""
        memories = [
            {
                "content": "Machine learning content",
                "similarity": 0.8,
                "ts": int(time.time() * 1000),  # Current time in milliseconds
                "context_similarity": 0.3,
            },
            {
                "content": "Older content",
                "similarity": 0.7,
                "ts": int((time.time() - 3600) * 1000),  # 1 hour ago
                "context_similarity": 0.2,
            },
        ]

        query = "machine learning"
        context = []

        scored_memories = memory_reader._apply_hybrid_scoring(memories, query, context)

        assert len(scored_memories) == 2
        # Check that hybrid scores are calculated
        for memory in scored_memories:
            assert "hybrid_score" in memory
            assert "temporal_score" in memory
            assert "keyword_bonus" in memory

        # Should be sorted by hybrid score
        assert scored_memories[0]["hybrid_score"] >= scored_memories[1]["hybrid_score"]

    def test_apply_hybrid_scoring_temporal_decay(self, memory_reader):
        """Test temporal decay in hybrid scoring."""
        current_time = time.time()
        memories = [
            {
                "content": "Recent content",
                "similarity": 0.6,
                "ts": current_time * 1000,  # Current time in milliseconds
                "context_similarity": 0.1,
            },
            {
                "content": "Old content",
                "similarity": 0.6,
                "ts": (current_time - 3600) * 1000,  # 1 hour ago in milliseconds
                "context_similarity": 0.1,
            },
        ]

        query = "test"
        context = []

        scored_memories = memory_reader._apply_hybrid_scoring(memories, query, context)

        # Recent memory should have higher temporal score
        recent_memory = next(m for m in scored_memories if "Recent" in m["content"])
        old_memory = next(m for m in scored_memories if "Old" in m["content"])

        assert recent_memory["temporal_score"] > old_memory["temporal_score"]

    def test_apply_hybrid_scoring_keyword_bonus(self, memory_reader):
        """Test keyword bonus in hybrid scoring."""
        memories = [
            {
                "content": "This contains the exact query machine learning",
                "similarity": 0.5,
                "ts": int(time.time() * 1000),
                "context_similarity": 0.1,
            },
            {
                "content": "This does not contain the query",
                "similarity": 0.5,
                "ts": int(time.time() * 1000),
                "context_similarity": 0.1,
            },
        ]

        query = "machine learning"
        context = []

        scored_memories = memory_reader._apply_hybrid_scoring(memories, query, context)

        # Memory with exact query match should have keyword bonus
        exact_match = next(m for m in scored_memories if "exact query" in m["content"])
        no_match = next(m for m in scored_memories if "does not contain" in m["content"])

        assert exact_match["keyword_bonus"] > no_match["keyword_bonus"]
        assert exact_match["hybrid_score"] > no_match["hybrid_score"]


class TestEnhancedFiltering:
    """Test enhanced memory filtering functionality."""

    def test_filter_enhanced_relevant_memories_hybrid_score(self, memory_reader):
        """Test filtering based on hybrid scores."""
        memories = [
            {
                "content": "High quality content",
                "hybrid_score": 0.8,
                "similarity": 0.6,
            },
            {
                "content": "Medium quality content",
                "hybrid_score": 0.3,
                "similarity": 0.5,
            },
            {
                "content": "Low quality content",
                "hybrid_score": 0.1,
                "similarity": 0.2,
            },
        ]

        query = "test query"
        context = []

        filtered = memory_reader._filter_enhanced_relevant_memories(memories, query, context)

        # Should keep high hybrid score (>= 0.4) and medium similarity (>= 0.3)
        assert len(filtered) == 2
        assert filtered[0]["hybrid_score"] == 0.8
        assert filtered[1]["similarity"] == 0.5

    def test_filter_enhanced_relevant_memories_context_keywords(self, memory_reader):
        """Test filtering based on context keywords."""
        memories = [
            {
                "content": "neural networks are powerful",
                "hybrid_score": 0.2,
                "similarity": 0.2,
            },
            {
                "content": "completely unrelated content",
                "hybrid_score": 0.2,
                "similarity": 0.2,
            },
        ]

        query = "test query"
        context = [
            {
                "content": "We discussed neural networks yesterday",
                "timestamp": time.time(),
                "role": "user",
            },
        ]

        filtered = memory_reader._filter_enhanced_relevant_memories(memories, query, context)

        # Should keep memory with context keyword match
        assert len(filtered) == 1
        assert "neural networks" in filtered[0]["content"]

    def test_filter_enhanced_relevant_memories_query_keywords(self, memory_reader):
        """Test filtering based on query keywords."""
        memories = [
            {
                "content": "machine learning algorithms",
                "hybrid_score": 0.2,
                "similarity": 0.2,
            },
            {
                "content": "unrelated content",
                "hybrid_score": 0.2,
                "similarity": 0.2,
            },
        ]

        query = "machine learning applications"
        context = []

        filtered = memory_reader._filter_enhanced_relevant_memories(memories, query, context)

        # Should keep memory with query keyword overlap
        assert len(filtered) == 1
        assert "machine learning" in filtered[0]["content"]


class TestMemoryReaderIntegration:
    """Integration tests for the enhanced memory reader."""

    @pytest.mark.asyncio
    async def test_run_with_context_awareness(self, memory_reader):
        """Test the main run method with context awareness."""
        # Mock the enhanced search methods to return test data
        test_memories = [
            {
                "content": "Machine learning uses neural networks",
                "similarity": 0.8,
                "metadata": {"confidence": 0.9},
                "match_type": "vector",
                "hybrid_score": 0.8,
                "temporal_score": 0.9,
                "keyword_bonus": 0.1,
            },
        ]

        with patch.object(
            memory_reader,
            "_context_aware_vector_search",
            return_value=test_memories,
        ):
            with patch.object(memory_reader, "_enhanced_keyword_search", return_value=[]):
                with patch.object(memory_reader, "_context_aware_stream_search", return_value=[]):
                    context = {
                        "input": "What is machine learning?",
                        "session_id": "test_session",
                        "history": [
                            {
                                "content": "We talked about AI yesterday",
                                "role": "user",
                                "timestamp": time.time() - 3600,
                            },
                        ],
                    }

                    result = await memory_reader.run(context)

        assert result["status"] == "success"
        assert "memories" in result
        assert result["memories"] != "NONE"
        assert len(result["memories"]) > 0
        assert "Machine learning" in result["memories"][0]["content"]

    @pytest.mark.asyncio
    async def test_run_no_memories_found(self, memory_reader):
        """Test run method when no memories are found."""
        context = {
            "input": "Random query with no matches",
            "session_id": "test_session",
        }

        with patch("orka.nodes.memory_reader_node.retry", side_effect=lambda x: x):
            result = await memory_reader.run(context)

        assert result["status"] == "success"
        assert result["memories"] == "NONE"

    def test_backward_compatibility_methods(self, memory_reader):
        """Test that backward compatibility methods exist and delegate properly."""
        # Test that old method signatures still work
        assert hasattr(memory_reader, "_keyword_search")
        assert hasattr(memory_reader, "_vector_search")
        assert hasattr(memory_reader, "_stream_search")
        assert hasattr(memory_reader, "_filter_relevant_memories")


class TestConfigurationOptions:
    """Test configuration options for enhanced memory reader."""

    def test_configuration_initialization(self):
        """Test that configuration options are properly initialized."""
        with patch("orka.nodes.memory_reader_node.get_embedder") as mock_get_embedder:
            mock_get_embedder.return_value = MockEmbedder()
            with patch("orka.nodes.memory_reader_node.redis.from_url"):
                reader = MemoryReaderNode(
                    node_id="test",
                    context_weight=0.4,
                    temporal_weight=0.3,
                    enable_context_search=False,
                    enable_temporal_ranking=False,
                    context_window_size=10,
                    temporal_decay_hours=48,
                )

                assert reader.context_weight == 0.4
                assert reader.temporal_weight == 0.3
                assert reader.enable_context_search is False
                assert reader.enable_temporal_ranking is False
                assert reader.context_window_size == 10
                assert reader.temporal_decay_hours == 48

    def test_default_configuration(self):
        """Test default configuration values."""
        with patch("orka.nodes.memory_reader_node.get_embedder") as mock_get_embedder:
            mock_get_embedder.return_value = MockEmbedder()
            with patch("orka.nodes.memory_reader_node.redis.from_url"):
                reader = MemoryReaderNode(node_id="test")

                assert reader.context_weight == 0.3
                assert reader.temporal_weight == 0.2
                assert reader.enable_context_search is True
                assert reader.enable_temporal_ranking is True
                assert reader.context_window_size == 5
                assert reader.temporal_decay_hours == 24


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_cosine_similarity_identical_vectors(self, memory_reader):
        """Test cosine similarity with identical vectors."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0, 3.0])

        similarity = memory_reader._cosine_similarity(vec1, vec2)

        assert abs(similarity - 1.0) < 1e-6  # Should be very close to 1.0

    def test_cosine_similarity_orthogonal_vectors(self, memory_reader):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])

        similarity = memory_reader._cosine_similarity(vec1, vec2)

        assert abs(similarity - 0.0) < 1e-6  # Should be very close to 0.0

    def test_cosine_similarity_different_shapes(self, memory_reader):
        """Test cosine similarity with different vector shapes."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0])

        similarity = memory_reader._cosine_similarity(vec1, vec2)

        assert similarity == 0  # Should return 0 for different shapes

    def test_cosine_similarity_zero_vectors(self, memory_reader):
        """Test cosine similarity with zero vectors."""
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 2.0, 3.0])

        similarity = memory_reader._cosine_similarity(vec1, vec2)

        assert similarity == 0  # Should return 0 for zero vectors


if __name__ == "__main__":
    pytest.main([__file__])
