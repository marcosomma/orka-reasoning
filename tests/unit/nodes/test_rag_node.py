"""Unit tests for orka.nodes.rag_node."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.nodes.rag_node import RAGNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestRAGNode:
    """Test suite for RAGNode class."""

    def test_init(self):
        """Test RAGNode initialization."""
        mock_registry = Mock()
        
        node = RAGNode(
            node_id="rag_node",
            registry=mock_registry,
            top_k=5,
            score_threshold=0.7
        )
        
        assert node.node_id == "rag_node"
        assert node.top_k == 5
        assert node.score_threshold == 0.7

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method."""
        mock_registry = Mock()
        mock_memory = Mock()
        mock_embedder = Mock()
        mock_llm = Mock()
        mock_registry.get.side_effect = lambda x: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": mock_llm
        }[x]
        
        node = RAGNode(node_id="rag_node", registry=mock_registry)
        await node.initialize()
        
        assert node._initialized is True

    @pytest.mark.asyncio
    async def test_run_impl(self):
        """Test _run_impl method."""
        mock_registry = Mock()
        mock_memory = Mock()
        mock_memory.search = AsyncMock(return_value=[
            {"content": "Doc 1", "score": 0.9},
            {"content": "Doc 2", "score": 0.8},
        ])
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[0.1] * 384)
        
        # Correctly mock the OpenAI-like LLM client
        mock_choice = Mock()
        mock_choice.message.content = "Generated answer"
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_llm = Mock()
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_completion)

        mock_registry.get.side_effect = lambda x: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": mock_llm
        }[x]
        
        node = RAGNode(node_id="rag_node", registry=mock_registry)
        await node.initialize()
        
        context = {
            "query": "test query"
        }
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_get_embedding(self):
        """Test _get_embedding method."""
        mock_registry = Mock()
        mock_embedder = Mock()
        mock_embedder.encode = AsyncMock(return_value=[0.1] * 384)
        mock_registry.get.side_effect = lambda x: {
            "memory": Mock(),
            "embedder": mock_embedder,
            "llm": Mock()
        }[x]
        
        node = RAGNode(node_id="rag_node", registry=mock_registry)
        await node.initialize()
        
        embedding = await node._get_embedding("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    def test_format_context(self):
        """Test _format_context method."""
        mock_registry = Mock()
        node = RAGNode(node_id="rag_node", registry=mock_registry)
        
        results = [
            {"content": "Document 1", "score": 0.9},
            {"content": "Document 2", "score": 0.8},
        ]
        
        formatted = node._format_context(results)
        
        assert isinstance(formatted, str)
        assert "Document 1" in formatted

    @pytest.mark.asyncio
    async def test_generate_answer(self):
        """Test _generate_answer method."""
        mock_registry = Mock()
        
        # Correctly mock the OpenAI-like LLM client
        mock_choice = Mock()
        mock_choice.message.content = "Generated answer"
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_llm = Mock()
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_completion)

        mock_registry.get.side_effect = lambda x: {
            "memory": Mock(),
            "embedder": Mock(),
            "llm": mock_llm
        }[x]
        
        node = RAGNode(node_id="rag_node", registry=mock_registry)
        await node.initialize()
        
        answer = await node._generate_answer("query", "context")
        
        assert isinstance(answer, str)
        assert len(answer) > 0

