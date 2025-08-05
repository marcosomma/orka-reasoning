"""
Comprehensive tests for RAG node module to improve coverage.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.contracts import Context, Registry
from orka.nodes.rag_node import RAGNode


class TestRAGNodeInitialization:
    """Test RAG node initialization."""

    def test_init_with_all_parameters(self):
        """Test RAG node initialization with all parameters."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            prompt="Test prompt",
            queue="test_queue",
            timeout=60.0,
            max_concurrency=5,
            top_k=10,
            score_threshold=0.8,
        )

        assert node.node_id == "test_rag"
        assert node.registry is registry
        assert node.prompt == "Test prompt"
        assert node.queue == "test_queue"
        assert node.top_k == 10
        assert node.score_threshold == 0.8
        assert node._memory is None
        assert node._embedder is None
        assert node._llm is None
        assert node._initialized is False

    def test_init_with_minimal_parameters(self):
        """Test RAG node initialization with minimal parameters."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="minimal_rag",
            registry=registry,
        )

        assert node.node_id == "minimal_rag"
        assert node.registry is registry
        assert node.prompt == ""
        assert node.queue == "default"
        assert node.top_k == 5
        assert node.score_threshold == 0.7
        assert node._memory is None
        assert node._embedder is None
        assert node._llm is None
        assert node._initialized is False

    def test_init_with_custom_parameters(self):
        """Test RAG node initialization with custom parameters."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="custom_rag",
            registry=registry,
            prompt="Custom prompt",
            top_k=15,
            score_threshold=0.9,
        )

        assert node.node_id == "custom_rag"
        assert node.prompt == "Custom prompt"
        assert node.top_k == 15
        assert node.score_threshold == 0.9

    def test_init_inherits_from_base_node(self):
        """Test that RAG node inherits from BaseNode."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Check that BaseNode methods are available
        assert hasattr(node, "node_id")
        assert hasattr(node, "prompt")
        assert hasattr(node, "queue")
        assert hasattr(node, "params")
        assert hasattr(node, "type")
        assert hasattr(node, "initialize")
        assert hasattr(node, "run")


class TestRAGNodeInitialize:
    """Test RAG node initialization method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization."""
        registry = Mock(spec=Registry)
        mock_memory = Mock()
        mock_embedder = Mock()
        mock_llm = Mock()

        registry.get.side_effect = lambda key: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": mock_llm,
        }[key]

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        await node.initialize()

        assert node._memory is mock_memory
        assert node._embedder is mock_embedder
        assert node._llm is mock_llm
        assert node._initialized is True

        # Check that registry.get was called for each component
        assert registry.get.call_count == 3
        registry.get.assert_any_call("memory")
        registry.get.assert_any_call("embedder")
        registry.get.assert_any_call("llm")

    @pytest.mark.asyncio
    async def test_initialize_with_none_components(self):
        """Test initialization when registry returns None for components."""
        registry = Mock(spec=Registry)
        registry.get.return_value = None

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        await node.initialize()

        assert node._memory is None
        assert node._embedder is None
        assert node._llm is None
        assert node._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_multiple_calls(self):
        """Test that initialize can be called multiple times."""
        registry = Mock(spec=Registry)
        mock_memory = Mock()
        registry.get.return_value = mock_memory

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Initialize twice
        await node.initialize()
        await node.initialize()

        assert node._initialized is True
        # Registry should be called multiple times
        assert registry.get.call_count >= 3


class TestRAGNodeRun:
    """Test RAG node run method."""

    @pytest.mark.asyncio
    async def test_run_success_with_initialization(self):
        """Test successful run with automatic initialization."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        registry.get.side_effect = lambda key: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": mock_llm,
        }[key]

        # Mock the search results
        mock_memory.search.return_value = [
            {"content": "Test content 1", "score": 0.8},
            {"content": "Test content 2", "score": 0.9},
        ]

        # Mock embedder
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]

        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test answer"
        mock_llm.chat.completions.create.return_value = mock_response

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "success"
        assert result["error"] is None
        assert result["metadata"]["node_id"] == "test_rag"
        assert "result" in result
        assert result["result"]["answer"] == "Test answer"
        assert len(result["result"]["sources"]) == 2

        # Verify initialization happened
        assert node._initialized is True

    @pytest.mark.asyncio
    async def test_run_already_initialized(self):
        """Test run when node is already initialized."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock the search results
        mock_memory.search.return_value = [
            {"content": "Test content", "score": 0.8},
        ]

        # Mock embedder
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]

        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test answer"
        mock_llm.chat.completions.create.return_value = mock_response

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "success"
        # Registry should not be called since already initialized
        registry.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_with_exception(self):
        """Test run when an exception occurs."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Mock _run_impl to raise exception (after initialization)
        with patch.object(node, "_run_impl", side_effect=Exception("Run failed")):
            context = Mock(spec=Context)

            result = await node.run(context)

            assert result["status"] == "error"
            assert result["error"] == "Run failed"
            assert result["result"] is None
            assert result["metadata"]["node_id"] == "test_rag"

    @pytest.mark.asyncio
    async def test_run_with_missing_query(self):
        """Test run when query is missing from context."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        context = Mock(spec=Context)
        context.get.return_value = None  # No query

        result = await node.run(context)

        assert result["status"] == "error"
        assert "Query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_run_with_empty_search_results(self):
        """Test run when search returns no results."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock empty search results
        mock_memory.search.return_value = []
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "success"
        assert "couldn't find any relevant information" in result["result"]["answer"]
        assert result["result"]["sources"] == []

    @pytest.mark.asyncio
    async def test_run_with_custom_parameters(self):
        """Test run with custom top_k and score_threshold."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            top_k=3,
            score_threshold=0.9,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock search results
        mock_memory.search.return_value = [
            {"content": "Test content", "score": 0.95},
        ]
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]

        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test answer"
        mock_llm.chat.completions.create.return_value = mock_response

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        # Verify search was called with custom parameters
        mock_memory.search.assert_called_once_with(
            [0.1, 0.2, 0.3],
            limit=3,
            score_threshold=0.9,
        )

        assert result["status"] == "success"


class TestRAGNodePrivateMethods:
    """Test RAG node private methods."""

    @pytest.mark.asyncio
    async def test_get_embedding(self):
        """Test _get_embedding method."""
        registry = Mock(spec=Registry)
        mock_embedder = AsyncMock()
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3, 0.4]

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )
        node._embedder = mock_embedder

        result = await node._get_embedding("test text")

        assert result == [0.1, 0.2, 0.3, 0.4]
        mock_embedder.encode.assert_called_once_with("test text")

    def test_format_context_single_result(self):
        """Test _format_context with single result."""
        registry = Mock(spec=Registry)
        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        results = [
            {"content": "First piece of content", "score": 0.8},
        ]

        context = node._format_context(results)

        expected = "Source 1:\nFirst piece of content\n"
        assert context == expected

    def test_format_context_multiple_results(self):
        """Test _format_context with multiple results."""
        registry = Mock(spec=Registry)
        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        results = [
            {"content": "First content", "score": 0.9},
            {"content": "Second content", "score": 0.8},
            {"content": "Third content", "score": 0.7},
        ]

        context = node._format_context(results)

        expected = (
            "Source 1:\nFirst content\n\nSource 2:\nSecond content\n\nSource 3:\nThird content\n"
        )
        assert context == expected

    def test_format_context_empty_results(self):
        """Test _format_context with empty results."""
        registry = Mock(spec=Registry)
        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        results = []

        context = node._format_context(results)

        assert context == ""

    @pytest.mark.asyncio
    async def test_generate_answer(self):
        """Test _generate_answer method."""
        registry = Mock(spec=Registry)
        mock_llm = AsyncMock()

        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated answer"
        mock_llm.chat.completions.create.return_value = mock_response

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )
        node._llm = mock_llm

        result = await node._generate_answer("test query", "test context")

        assert result == "Generated answer"

        # Verify LLM was called with correct parameters
        mock_llm.chat.completions.create.assert_called_once()
        call_args = mock_llm.chat.completions.create.call_args

        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["messages"][1]["role"] == "user"
        assert "test query" in call_args[1]["messages"][1]["content"]
        assert "test context" in call_args[1]["messages"][1]["content"]

    @pytest.mark.asyncio
    async def test_generate_answer_with_custom_prompt(self):
        """Test _generate_answer with custom prompt formatting."""
        registry = Mock(spec=Registry)
        mock_llm = AsyncMock()

        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Custom answer"
        mock_llm.chat.completions.create.return_value = mock_response

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )
        node._llm = mock_llm

        query = "What is the capital of France?"
        context = "France is a country in Europe. Paris is the capital."

        result = await node._generate_answer(query, context)

        assert result == "Custom answer"

        # Verify the prompt contains the expected elements
        call_args = mock_llm.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]

        assert "Context:" in user_message
        assert "Question:" in user_message
        assert "Answer:" in user_message
        assert query in user_message
        assert context in user_message


class TestRAGNodeIntegration:
    """Test RAG node integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self):
        """Test complete RAG pipeline from query to answer."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        registry.get.side_effect = lambda key: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": mock_llm,
        }[key]

        # Mock pipeline components
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.return_value = [
            {"content": "Paris is the capital of France", "score": 0.9},
            {"content": "France is in Europe", "score": 0.8},
        ]

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Paris is the capital of France."
        mock_llm.chat.completions.create.return_value = mock_response

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            top_k=2,
            score_threshold=0.7,
        )

        context = Mock(spec=Context)
        context.get.return_value = "What is the capital of France?"

        result = await node.run(context)

        # Verify the complete pipeline
        assert result["status"] == "success"
        assert result["result"]["answer"] == "Paris is the capital of France."
        assert len(result["result"]["sources"]) == 2

        # Verify each component was called
        mock_embedder.encode.assert_called_once_with("What is the capital of France?")
        mock_memory.search.assert_called_once_with(
            [0.1, 0.2, 0.3],
            limit=2,
            score_threshold=0.7,
        )
        mock_llm.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_with_logging(self):
        """Test RAG node with logging."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Mock _run_impl to raise exception to trigger logging
        with patch.object(node, "_run_impl", side_effect=Exception("Test error")):
            with patch("orka.nodes.rag_node.logger") as mock_logger:
                context = Mock(spec=Context)

                result = await node.run(context)

                assert result["status"] == "error"
                mock_logger.error.assert_called_once()
                assert "RAGNode test_rag failed" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_rag_with_different_context_types(self):
        """Test RAG node with different context query types."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Test with empty string query
        context = Mock(spec=Context)
        context.get.return_value = ""

        result = await node.run(context)
        assert result["status"] == "error"
        assert "Query is required" in result["error"]

        # Test with None query
        context.get.return_value = None

        result = await node.run(context)
        assert result["status"] == "error"
        assert "Query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_rag_with_memory_search_exception(self):
        """Test RAG node when memory search raises exception."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock embedder and memory search exception
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.side_effect = Exception("Memory search failed")

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "error"
        assert "Memory search failed" in result["error"]

    @pytest.mark.asyncio
    async def test_rag_with_embedder_exception(self):
        """Test RAG node when embedder raises exception."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock embedder exception
        mock_embedder.encode.side_effect = Exception("Embedder failed")

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "error"
        assert "Embedder failed" in result["error"]

    @pytest.mark.asyncio
    async def test_rag_with_llm_exception(self):
        """Test RAG node when LLM raises exception."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock successful embedding and search
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.return_value = [
            {"content": "Test content", "score": 0.8},
        ]

        # Mock LLM exception
        mock_llm.chat.completions.create.side_effect = Exception("LLM failed")

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "error"
        assert "LLM failed" in result["error"]


class TestRAGNodeEdgeCases:
    """Test RAG node edge cases."""

    def test_rag_node_with_zero_top_k(self):
        """Test RAG node with zero top_k."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            top_k=0,
        )

        assert node.top_k == 0

    def test_rag_node_with_negative_score_threshold(self):
        """Test RAG node with negative score threshold."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            score_threshold=-0.5,
        )

        assert node.score_threshold == -0.5

    def test_rag_node_with_very_high_score_threshold(self):
        """Test RAG node with very high score threshold."""
        registry = Mock(spec=Registry)

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            score_threshold=1.5,
        )

        assert node.score_threshold == 1.5

    @pytest.mark.asyncio
    async def test_rag_with_very_large_context(self):
        """Test RAG node with very large context."""
        registry = Mock(spec=Registry)
        mock_memory = AsyncMock()
        mock_embedder = AsyncMock()
        mock_llm = AsyncMock()

        node = RAGNode(
            node_id="test_rag",
            registry=registry,
            top_k=100,  # Large number of results
        )

        # Pre-initialize
        node._memory = mock_memory
        node._embedder = mock_embedder
        node._llm = mock_llm
        node._initialized = True

        # Mock large search results
        large_results = [{"content": f"Content {i}", "score": 0.9 - i * 0.01} for i in range(50)]

        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.return_value = large_results

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Large context answer"
        mock_llm.chat.completions.create.return_value = mock_response

        context = Mock(spec=Context)
        context.get.return_value = "Test query"

        result = await node.run(context)

        assert result["status"] == "success"
        assert len(result["result"]["sources"]) == 50
        assert result["result"]["answer"] == "Large context answer"

    def test_format_context_with_special_characters(self):
        """Test _format_context with special characters in content."""
        registry = Mock(spec=Registry)
        node = RAGNode(
            node_id="test_rag",
            registry=registry,
        )

        results = [
            {"content": "Content with\nnewlines\tand\ttabs", "score": 0.8},
            {"content": "Content with unicode: 🎉 émojis", "score": 0.9},
        ]

        context = node._format_context(results)

        assert "Content with\nnewlines\tand\ttabs" in context
        assert "Content with unicode: 🎉 émojis" in context
        assert "Source 1:" in context
        assert "Source 2:" in context
