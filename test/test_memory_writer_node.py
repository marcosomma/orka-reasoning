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
Test cases for memory writer node functionality
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from orka.nodes.memory_writer_node import MemoryWriterNode


class TestMemoryWriterNode:
    """Test suite for memory writer node functionality"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(return_value=b"1234567890-0")
        redis_mock.xrevrange = AsyncMock(
            return_value=[
                (b"1234567890-0", {b"payload": b'{"content": "test content"}'}),
            ],
        )
        redis_mock.hset = AsyncMock(return_value=True)
        redis_mock.hget = AsyncMock()
        return redis_mock

    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder"""
        embedder = AsyncMock()
        embedder.encode = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
        return embedder

    @pytest.fixture
    def memory_writer_node(self, mock_redis):
        """Create a memory writer node for testing"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch("orka.nodes.memory_writer_node.get_embedder") as mock_get_embedder:
                mock_get_embedder.return_value = AsyncMock()
                mock_get_embedder.return_value.encode = AsyncMock(return_value=[0.1, 0.2, 0.3])

                node = MemoryWriterNode(
                    node_id="test_memory_writer",
                    prompt="Test prompt",
                    queue=["test_queue"],
                    vector=True,
                    namespace="test_namespace",
                    metadata={"test_key": "test_value"},
                )
                return node

    @pytest.fixture
    def memory_writer_node_no_vector(self, mock_redis):
        """Create a memory writer node with vector disabled"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            node = MemoryWriterNode(
                node_id="test_memory_writer_no_vector",
                prompt="Test prompt",
                queue=["test_queue"],
                vector=False,
                namespace="test_namespace",
            )
            return node

    def test_initialization_with_vector(self, mock_redis):
        """Test memory writer node initialization with vector enabled"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch("orka.nodes.memory_writer_node.get_embedder") as mock_get_embedder:
                mock_embedder = AsyncMock()
                mock_get_embedder.return_value = mock_embedder

                node = MemoryWriterNode(
                    node_id="test_node",
                    prompt="Test prompt",
                    queue=["test_queue"],
                    vector=True,
                    namespace="custom_namespace",
                    key_template="key_{{session_id}}",
                    metadata={"source": "test"},
                )

                assert node.node_id == "test_node"
                assert node.vector_enabled == True
                assert node.namespace == "custom_namespace"
                assert node.key_template == "key_{{session_id}}"
                assert node.metadata == {"source": "test"}
                assert node.embedder is mock_embedder
                assert node.type == "memorywriternode"

    def test_initialization_without_vector(self, mock_redis):
        """Test memory writer node initialization with vector disabled"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            node = MemoryWriterNode(
                node_id="test_node",
                prompt="Test prompt",
                queue=["test_queue"],
                vector=False,
            )

            assert node.node_id == "test_node"
            assert node.vector_enabled == False
            assert node.namespace == "default"
            assert node.key_template == ""
            assert node.metadata == {}
            assert node.embedder is None

    def test_initialization_embedder_failure_with_fallback(self, mock_redis):
        """Test initialization when primary embedder fails but fallback succeeds"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch("orka.nodes.memory_writer_node.get_embedder") as mock_get_embedder:
                # First call fails, second call (fallback) succeeds
                mock_embedder = AsyncMock()
                mock_get_embedder.side_effect = [Exception("Primary failed"), mock_embedder]

                with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
                    node = MemoryWriterNode(
                        node_id="test_node",
                        vector=True,
                        embedding_model="custom_model",
                    )

                    assert node.vector_enabled == True
                    assert node.embedder is mock_embedder
                    mock_logger.error.assert_called()
                    mock_logger.info.assert_called_with(
                        "Initialized fallback embedder after primary embedder failed",
                    )

    def test_initialization_embedder_complete_failure(self, mock_redis):
        """Test initialization when both primary and fallback embedder fail"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch("orka.nodes.memory_writer_node.get_embedder") as mock_get_embedder:
                # Both calls fail
                mock_get_embedder.side_effect = Exception("Both failed")

                with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
                    node = MemoryWriterNode(
                        node_id="test_node",
                        vector=True,
                    )

                    assert node.vector_enabled == False
                    assert node.embedder is None
                    mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_run_with_input_text(self, memory_writer_node):
        """Test running memory writer with input text"""
        context = {
            "input": "Test content to store",
            "session_id": "test_session",
            "namespace": "custom_namespace",
        }

        with patch("time.time_ns", return_value=1234567890):
            with patch("time.time", return_value=1234567.89):
                result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        assert result["session"] == "test_session"
        assert result["namespace"] == "custom_namespace"
        assert "entry_id" in result
        assert "vector_id" in result

        # Verify Redis stream write was called
        memory_writer_node.redis.xadd.assert_called_once()
        stream_key = "orka:memory:custom_namespace:test_session"
        call_args = memory_writer_node.redis.xadd.call_args
        assert call_args[0][0] == stream_key

        # Verify payload structure
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        assert payload["content"] == "Test content to store"
        assert payload["metadata"]["test_key"] == "test_value"

    @pytest.mark.asyncio
    async def test_run_without_vector_storage(self, memory_writer_node_no_vector):
        """Test running memory writer without vector storage"""
        context = {
            "input": "Test content to store",
            "session_id": "test_session",
        }

        result = await memory_writer_node_no_vector.run(context)

        assert result["status"] == "success"
        assert "vector_id" not in result

        # Verify only stream write was called, no vector operations
        memory_writer_node_no_vector.redis.xadd.assert_called_once()
        memory_writer_node_no_vector.redis.hset.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_with_prompt_template(self, memory_writer_node):
        """Test running memory writer with prompt template when input is empty"""
        memory_writer_node.prompt = "Content: {{answer}}"

        context = {
            "input": "",  # Empty input
            "answer": "Generated answer from template",
            "session_id": "test_session",
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Verify the template was rendered
        call_args = memory_writer_node.redis.xadd.call_args
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        assert payload["content"] == "Content: Generated answer from template"

    @pytest.mark.asyncio
    async def test_run_with_previous_outputs_fallback(self, memory_writer_node):
        """Test running memory writer using previous_outputs as fallback"""
        context = {
            "input": "",  # Empty input
            "session_id": "test_session",
            "previous_outputs": {
                "synthesize_timeline_answer": "Answer from previous output",
                "other_field": "Other content",
            },
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Verify it used the first available field
        call_args = memory_writer_node.redis.xadd.call_args
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        assert payload["content"] == "Answer from previous output"

    @pytest.mark.asyncio
    async def test_run_no_content_available(self, memory_writer_node):
        """Test running memory writer when no content is available"""
        context = {
            "input": "",  # Empty input
            "session_id": "test_session",
            # No previous_outputs
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "error"
        assert "No content available to store in memory" in result["error"]

    @pytest.mark.asyncio
    async def test_run_with_key_template(self, memory_writer_node):
        """Test running memory writer with key template"""
        memory_writer_node.key_template = "session_{{session_id}}_{{timestamp}}"

        context = {
            "input": "Test content",
            "session_id": "test_session",
            "timestamp": "12345",
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Verify the key template was used
        call_args = memory_writer_node.redis.xadd.call_args
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        assert payload["key"] == "session_test_session_12345"

    @pytest.mark.asyncio
    async def test_run_key_template_error(self, memory_writer_node):
        """Test running memory writer when key template fails"""
        memory_writer_node.key_template = "invalid_{{missing_var}}"

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        with patch("time.time_ns", return_value=9876543210):
            result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Template resolves to "invalid_" (missing variables become empty strings)
        call_args = memory_writer_node.redis.xadd.call_args
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        assert payload["key"] == "invalid_"

    @pytest.mark.asyncio
    async def test_run_with_metadata_template(self, memory_writer_node):
        """Test running memory writer with metadata template"""
        memory_writer_node.metadata = {
            "static_key": "static_value",
            "dynamic_key": "{{answer}}",
            "fallback_key": "{{previous_outputs.result}}",
        }

        context = {
            "input": "Test content",
            "session_id": "test_session",
            "answer": "Dynamic answer",
            "previous_outputs": {
                "result": "Fallback result",
            },
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Verify metadata templates were resolved
        call_args = memory_writer_node.redis.xadd.call_args
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        metadata = payload["metadata"]

        assert metadata["static_key"] == "static_value"
        assert metadata["dynamic_key"] == "Dynamic answer"
        assert metadata["fallback_key"] == "Fallback result"

    @pytest.mark.asyncio
    async def test_run_metadata_template_error_with_fallback(self, memory_writer_node):
        """Test metadata template error with fallback mechanism"""
        memory_writer_node.metadata = {
            "fallback_key": "{{previous_outputs.result}}",
        }

        context = {
            "input": "Test content",
            "session_id": "test_session",
            "previous_outputs": {
                "result": "Fallback value",
            },
        }

        # Mock jinja2 Template to fail
        with patch("jinja2.Template") as mock_template:
            mock_template.side_effect = Exception("Template error")

            result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Should use fallback mechanism
        call_args = memory_writer_node.redis.xadd.call_args
        entry = call_args[0][1]
        payload = json.loads(entry["payload"])
        metadata = payload["metadata"]
        assert metadata["fallback_key"] == "Fallback value"

    @pytest.mark.asyncio
    async def test_run_stream_verification_failure(self, memory_writer_node):
        """Test when stream verification fails"""
        memory_writer_node.redis.xrevrange.return_value = []  # No entries

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
            result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        mock_logger.warning.assert_called_with(
            "Could not verify stream write - no entries in orka:memory:test_namespace:test_session",
        )

    @pytest.mark.asyncio
    async def test_run_stream_verification_exception(self, memory_writer_node):
        """Test when stream verification raises exception"""
        memory_writer_node.redis.xrevrange.side_effect = Exception("Verification failed")

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
            result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        mock_logger.error.assert_called_with("Error verifying stream write: Verification failed")

    @pytest.mark.asyncio
    async def test_run_vector_encoding_failure_with_fallback(self, memory_writer_node):
        """Test vector encoding failure with fallback embedder"""
        # Make primary embedder fail
        memory_writer_node.embedder.encode.side_effect = Exception("Primary encoding failed")

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        # Mock fallback embedder
        mock_fallback = AsyncMock()
        mock_fallback.encode.return_value = [0.5, 0.6, 0.7]

        with patch("orka.utils.embedder.AsyncEmbedder", return_value=mock_fallback):
            result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        assert "vector_id" in result

        # Verify fallback embedder was used
        mock_fallback.encode.assert_called_once_with("Test content")

    @pytest.mark.asyncio
    async def test_run_vector_encoding_complete_failure(self, memory_writer_node):
        """Test when both primary and fallback vector encoding fail"""
        # Make primary embedder fail
        memory_writer_node.embedder.encode.side_effect = Exception("Primary encoding failed")

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        # Make fallback embedder also fail
        mock_fallback = AsyncMock()
        mock_fallback.encode.side_effect = Exception("Fallback encoding failed")

        with patch("orka.utils.embedder.AsyncEmbedder", return_value=mock_fallback):
            with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
                result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        assert "vector_id" not in result  # Vector storage should have failed

        mock_logger.error.assert_any_call(
            "Failed to store vector embedding: Fallback encoding failed",
        )

    @pytest.mark.asyncio
    async def test_run_vector_storage_verification(self, memory_writer_node):
        """Test vector storage verification"""
        memory_writer_node.redis.hget.side_effect = [
            b"vector_data",  # vector field
            b"stored_content",  # content field
        ]

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
            result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        assert "vector_id" in result

        # Verify logging for successful storage
        mock_logger.info.assert_any_call("Vector successfully stored with length 11 bytes")
        mock_logger.info.assert_any_call("Content successfully stored: stored_content...")

    @pytest.mark.asyncio
    async def test_run_vector_storage_verification_failure(self, memory_writer_node):
        """Test vector storage verification when data is missing"""
        memory_writer_node.redis.hget.side_effect = [
            None,  # vector field missing
            None,  # content field missing
        ]

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        with patch("orka.nodes.memory_writer_node.logger") as mock_logger:
            result = await memory_writer_node.run(context)

        assert result["status"] == "success"

        # Verify warning logs for missing data
        mock_logger.warning.assert_any_call("Vector was not stored correctly")
        mock_logger.warning.assert_any_call("Content was not stored correctly")

    @pytest.mark.asyncio
    async def test_run_redis_stream_exception(self, memory_writer_node):
        """Test when Redis stream operations fail"""
        memory_writer_node.redis.xadd.side_effect = Exception("Redis connection failed")

        context = {
            "input": "Test content",
            "session_id": "test_session",
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "error"
        assert "Redis connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_context_outputs_update(self, memory_writer_node):
        """Test that context outputs are properly updated"""
        context = {
            "input": "Test content",
            "session_id": "test_session",
            "outputs": {},
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        assert context["outputs"]["test_memory_writer"] == result

    @pytest.mark.asyncio
    async def test_run_context_outputs_creation(self, memory_writer_node):
        """Test that context outputs dict is created if missing"""
        context = {
            "input": "Test content",
            "session_id": "test_session",
            # No outputs dict
        }

        result = await memory_writer_node.run(context)

        assert result["status"] == "success"
        assert "outputs" in context
        assert context["outputs"]["test_memory_writer"] == result

    def test_redis_url_from_environment(self):
        """Test Redis URL configuration from environment"""
        with patch.dict("os.environ", {"REDIS_URL": "redis://custom:6380"}):
            with patch("redis.asyncio.from_url") as mock_from_url:
                with patch("orka.nodes.memory_writer_node.get_embedder"):
                    node = MemoryWriterNode(node_id="test", vector=False)
                    mock_from_url.assert_called_once_with(
                        "redis://custom:6380",
                        decode_responses=False,
                    )

    def test_redis_url_default(self):
        """Test default Redis URL when environment variable is not set"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("redis.asyncio.from_url") as mock_from_url:
                with patch("orka.nodes.memory_writer_node.get_embedder"):
                    node = MemoryWriterNode(node_id="test", vector=False)
                    mock_from_url.assert_called_once_with(
                        "redis://localhost:6379",
                        decode_responses=False,
                    )
