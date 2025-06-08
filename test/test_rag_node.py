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
Test cases for RAG node functionality
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.contracts import Context, Registry
from orka.nodes.rag_node import RAGNode


class TestRAGNode:
    """Test suite for RAG node functionality"""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry with required components"""
        registry = MagicMock(spec=Registry)

        # Mock memory component
        mock_memory = AsyncMock()
        mock_memory.search = AsyncMock()

        # Mock embedder component
        mock_embedder = AsyncMock()
        mock_embedder.encode = AsyncMock()

        # Mock LLM component
        mock_llm = AsyncMock()
        mock_chat = AsyncMock()
        mock_completions = AsyncMock()
        mock_llm.chat = mock_chat
        mock_chat.completions = mock_completions

        # Mock response structure
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Generated answer based on context"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_completions.create = AsyncMock(return_value=mock_response)

        registry.get.side_effect = lambda key: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": mock_llm,
        }.get(key)

        return registry

    @pytest.fixture
    def rag_node(self, mock_registry):
        """Create a RAG node for testing"""
        return RAGNode(
            node_id="test_rag",
            registry=mock_registry,
            prompt="Test prompt",
            queue="test_queue",
            timeout=30.0,
            max_concurrency=5,
            top_k=3,
            score_threshold=0.8,
        )

    def test_initialization(self, mock_registry):
        """Test RAG node initialization"""
        node = RAGNode(
            node_id="test_rag",
            registry=mock_registry,
            prompt="Test prompt",
            queue="test_queue",
            timeout=45.0,
            max_concurrency=8,
            top_k=7,
            score_threshold=0.6,
        )

        assert node.node_id == "test_rag"
        assert node.registry is mock_registry
        assert node.top_k == 7
        assert node.score_threshold == 0.6
        assert node._memory is None
        assert node._embedder is None
        assert node._llm is None
        assert not node._initialized

    @pytest.mark.asyncio
    async def test_initialize_components(self, rag_node, mock_registry):
        """Test initialization of RAG node components"""
        await rag_node.initialize()

        assert rag_node._initialized
        assert rag_node._memory is not None
        assert rag_node._embedder is not None
        assert rag_node._llm is not None

        # Check that registry.get was called for each component
        expected_calls = ["memory", "embedder", "llm"]
        actual_calls = [call[0][0] for call in mock_registry.get.call_args_list]
        assert set(actual_calls) == set(expected_calls)

    @pytest.mark.asyncio
    async def test_run_success_with_results(self, rag_node, mock_registry):
        """Test successful RAG node execution with search results"""
        # Setup test data
        test_context = Context({"query": "What is machine learning?"})

        # Mock search results
        search_results = [
            {"content": "Machine learning is a subset of AI", "score": 0.9},
            {"content": "ML algorithms learn from data", "score": 0.85},
        ]

        # Configure mocks
        mock_memory = mock_registry.get("memory")
        mock_embedder = mock_registry.get("embedder")
        mock_llm = mock_registry.get("llm")

        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.return_value = search_results

        # Run the node
        result = await rag_node.run(test_context)

        # Verify result structure
        assert result["status"] == "success"
        assert result["error"] is None
        assert result["metadata"]["node_id"] == "test_rag"
        assert "result" in result

        # Verify the inner result
        inner_result = result["result"]
        assert "answer" in inner_result
        assert "sources" in inner_result
        assert inner_result["sources"] == search_results
        assert inner_result["answer"] == "Generated answer based on context"

        # Verify component interactions
        mock_embedder.encode.assert_called_once_with("What is machine learning?")
        mock_memory.search.assert_called_once_with(
            [0.1, 0.2, 0.3],
            limit=3,
            score_threshold=0.8,
        )
        mock_llm.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_no_results_found(self, rag_node, mock_registry):
        """Test RAG node execution when no relevant results are found"""
        test_context = Context({"query": "Very specific query with no matches"})

        # Configure mocks to return no results
        mock_memory = mock_registry.get("memory")
        mock_embedder = mock_registry.get("embedder")

        mock_embedder.encode.return_value = [0.5, 0.6, 0.7]
        mock_memory.search.return_value = []  # No results

        result = await rag_node.run(test_context)

        # Verify result
        assert result["status"] == "success"
        assert result["error"] is None

        inner_result = result["result"]
        assert (
            inner_result["answer"]
            == "I couldn't find any relevant information to answer your question."
        )
        assert inner_result["sources"] == []

        # Verify that LLM was not called since no results found
        mock_llm = mock_registry.get("llm")
        mock_llm.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_missing_query(self, rag_node):
        """Test RAG node execution with missing query"""
        test_context = Context({})  # No query provided

        result = await rag_node.run(test_context)

        assert result["status"] == "error"
        assert result["error"] == "Query is required for RAG operation"
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_run_empty_query(self, rag_node):
        """Test RAG node execution with empty query"""
        test_context = Context({"query": ""})  # Empty query

        result = await rag_node.run(test_context)

        assert result["status"] == "error"
        assert result["error"] == "Query is required for RAG operation"
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_run_embedder_error(self, rag_node, mock_registry):
        """Test RAG node execution when embedder fails"""
        test_context = Context({"query": "Test query"})

        # Make embedder fail
        mock_embedder = mock_registry.get("embedder")
        mock_embedder.encode.side_effect = Exception("Embedder failed")

        result = await rag_node.run(test_context)

        assert result["status"] == "error"
        assert "Embedder failed" in result["error"]
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_run_memory_search_error(self, rag_node, mock_registry):
        """Test RAG node execution when memory search fails"""
        test_context = Context({"query": "Test query"})

        # Configure embedder to succeed but memory search to fail
        mock_embedder = mock_registry.get("embedder")
        mock_memory = mock_registry.get("memory")

        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.side_effect = Exception("Memory search failed")

        result = await rag_node.run(test_context)

        assert result["status"] == "error"
        assert "Memory search failed" in result["error"]
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_run_llm_error(self, rag_node, mock_registry):
        """Test RAG node execution when LLM generation fails"""
        test_context = Context({"query": "Test query"})

        # Configure components to succeed up to LLM
        mock_embedder = mock_registry.get("embedder")
        mock_memory = mock_registry.get("memory")
        mock_llm = mock_registry.get("llm")

        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.return_value = [{"content": "Test content", "score": 0.9}]
        mock_llm.chat.completions.create.side_effect = Exception("LLM generation failed")

        result = await rag_node.run(test_context)

        assert result["status"] == "error"
        assert "LLM generation failed" in result["error"]
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_get_embedding(self, rag_node, mock_registry):
        """Test the _get_embedding method"""
        await rag_node.initialize()

        mock_embedder = mock_registry.get("embedder")
        mock_embedder.encode.return_value = [0.1, 0.2, 0.3, 0.4]

        result = await rag_node._get_embedding("test text")

        assert result == [0.1, 0.2, 0.3, 0.4]
        mock_embedder.encode.assert_called_once_with("test text")

    def test_format_context_single_result(self, rag_node):
        """Test context formatting with single result"""
        results = [{"content": "Single piece of content", "score": 0.9}]

        context = rag_node._format_context(results)

        expected = "Source 1:\nSingle piece of content\n"
        assert context == expected

    def test_format_context_multiple_results(self, rag_node):
        """Test context formatting with multiple results"""
        results = [
            {"content": "First piece of content", "score": 0.9},
            {"content": "Second piece of content", "score": 0.8},
            {"content": "Third piece of content", "score": 0.7},
        ]

        context = rag_node._format_context(results)

        expected = (
            "Source 1:\nFirst piece of content\n\n"
            "Source 2:\nSecond piece of content\n\n"
            "Source 3:\nThird piece of content\n"
        )
        assert context == expected

    def test_format_context_empty_results(self, rag_node):
        """Test context formatting with empty results"""
        results = []

        context = rag_node._format_context(results)

        assert context == ""

    @pytest.mark.asyncio
    async def test_generate_answer(self, rag_node, mock_registry):
        """Test the _generate_answer method"""
        await rag_node.initialize()

        mock_llm = mock_registry.get("llm")

        # Test the method
        answer = await rag_node._generate_answer("What is AI?", "AI is artificial intelligence")

        assert answer == "Generated answer based on context"

        # Verify the LLM was called with correct parameters
        call_args = mock_llm.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["messages"][1]["role"] == "user"
        assert "What is AI?" in call_args[1]["messages"][1]["content"]
        assert "AI is artificial intelligence" in call_args[1]["messages"][1]["content"]

    @pytest.mark.asyncio
    async def test_run_auto_initialization(self, rag_node, mock_registry):
        """Test that run() automatically initializes if not already initialized"""
        # Ensure node is not initialized
        assert not rag_node._initialized

        test_context = Context({"query": "Test query"})

        # Configure mocks for a successful run
        mock_embedder = mock_registry.get("embedder")
        mock_memory = mock_registry.get("memory")

        mock_embedder.encode.return_value = [0.1, 0.2, 0.3]
        mock_memory.search.return_value = [{"content": "Test content", "score": 0.9}]

        result = await rag_node.run(test_context)

        # Should be initialized now
        assert rag_node._initialized
        assert result["status"] == "success"

    def test_rag_node_default_parameters(self, mock_registry):
        """Test RAG node with default parameters"""
        node = RAGNode(node_id="test", registry=mock_registry)

        assert node.top_k == 5
        assert node.score_threshold == 0.7
        assert node.prompt == ""
        assert node.queue == "default"
