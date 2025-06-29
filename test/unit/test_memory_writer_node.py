from unittest.mock import Mock, patch

import pytest

from orka.nodes.memory_writer_node import MemoryWriterNode


class TestMemoryWriterNodeInitialization:
    """Test MemoryWriterNode initialization scenarios."""

    @patch("orka.nodes.memory_writer_node.create_memory_logger")
    def test_initialization_default_params(self, mock_create_logger):
        """Test initialization with default parameters."""
        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger

        node = MemoryWriterNode(node_id="test_writer", prompt="test", queue=[])

        assert node.node_id == "test_writer"
        assert node.type == "memorywriternode"
        assert node.memory_logger == mock_logger
        assert node.namespace == "default"
        assert node.session_id == "default"
        assert node.decay_config == {}

        mock_create_logger.assert_called_once_with(
            backend="redisstack",
            enable_hnsw=True,
            vector_params={"M": 16, "ef_construction": 200},
            decay_config={},
        )

    @patch("orka.nodes.memory_writer_node.create_memory_logger")
    def test_initialization_with_custom_params(self, mock_create_logger):
        """Test initialization with custom parameters."""
        mock_logger = Mock()
        mock_create_logger.return_value = mock_logger

        custom_vector_params = {"M": 32, "ef_construction": 400}
        custom_decay_config = {"short_term_hours": 2.0, "long_term_hours": 48.0}

        node = MemoryWriterNode(
            node_id="custom_writer",
            prompt="test",
            queue=[],
            namespace="custom_ns",
            session_id="custom_session",
            use_hnsw=False,
            vector_params=custom_vector_params,
            decay_config=custom_decay_config,
        )

        assert node.namespace == "custom_ns"
        assert node.session_id == "custom_session"
        assert node.decay_config == custom_decay_config

        mock_create_logger.assert_called_once_with(
            backend="redisstack",
            enable_hnsw=False,
            vector_params=custom_vector_params,
            decay_config=custom_decay_config,
        )

    def test_initialization_with_custom_memory_logger(self):
        """Test initialization with pre-existing memory logger."""
        custom_logger = Mock()

        node = MemoryWriterNode(
            node_id="test_writer",
            prompt="test",
            queue=[],
            memory_logger=custom_logger,
            namespace="test_ns",
        )

        assert node.memory_logger == custom_logger
        assert node.namespace == "test_ns"


class TestMemoryWriterNodeRun:
    """Test the main run method of MemoryWriterNode."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.mock_memory_logger = Mock()
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=self.mock_memory_logger,
                namespace="test_ns",
                session_id="test_session",
            )

    @pytest.mark.asyncio
    async def test_run_successful_with_structured_memory(self):
        """Test successful run with structured memory object."""
        self.mock_memory_logger.log_memory.return_value = "memory_key_123"

        context = {
            "input": "Original input",
            "previous_outputs": {
                "false_validation_guardian": {
                    "result": {
                        "memory_object": {
                            "number": "7",
                            "result": "true",
                            "condition": "greater than 5",
                            "analysis_type": "numerical_comparison",
                            "confidence": 0.95,
                            "validation_status": "validated",
                        },
                    },
                },
            },
            "namespace": "custom_ns",
            "session_id": "custom_session",
            "metadata": {"source": "test", "category": "stored"},
        }

        result = await self.node.run(context)

        assert result["status"] == "success"
        assert result["memory_key"] == "memory_key_123"
        assert result["session"] == "custom_session"
        assert result["namespace"] == "custom_ns"
        assert result["backend"] == "redisstack"
        assert result["vector_enabled"] == True
        assert "content_length" in result

        # Verify log_memory was called with correct parameters
        self.mock_memory_logger.log_memory.assert_called_once()
        call_args = self.mock_memory_logger.log_memory.call_args
        assert call_args[1]["node_id"] == "test_writer"
        assert call_args[1]["trace_id"] == "custom_session"
        assert call_args[1]["metadata"]["namespace"] == "custom_ns"
        assert call_args[1]["metadata"]["category"] == "stored"

    @pytest.mark.asyncio
    async def test_run_with_true_validation_guardian(self):
        """Test run with true validation guardian output."""
        self.mock_memory_logger.log_memory.return_value = "memory_key_456"

        context = {
            "input": "Test input",
            "previous_outputs": {
                "true_validation_guardian": {
                    "result": {
                        "memory_object": {
                            "number": "3",
                            "result": "false",
                            "condition": "greater than 5",
                            "analysis_type": "numerical_comparison",
                            "confidence": 0.85,
                        },
                    },
                },
            },
        }

        result = await self.node.run(context)

        assert result["status"] == "success"
        assert result["memory_key"] == "memory_key_456"

    @pytest.mark.asyncio
    async def test_run_fallback_to_input(self):
        """Test run falls back to input when no structured memory found."""
        self.mock_memory_logger.log_memory.return_value = "memory_key_789"

        context = {
            "input": "Direct input content",
            "previous_outputs": {},
        }

        result = await self.node.run(context)

        assert result["status"] == "success"
        assert result["memory_key"] == "memory_key_789"

        # Verify the content was the direct input
        call_args = self.mock_memory_logger.log_memory.call_args
        assert "Direct input content" in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_run_no_memory_content(self):
        """Test run with no extractable memory content."""
        context = {
            "previous_outputs": {},
            # No input field
        }

        result = await self.node.run(context)

        assert result["status"] == "error"
        assert result["error"] == "No memory content to store"

    @pytest.mark.asyncio
    async def test_run_memory_logger_exception(self):
        """Test run when memory logger throws exception."""
        self.mock_memory_logger.log_memory.side_effect = Exception("Redis connection failed")

        context = {
            "input": "Test content",
        }

        result = await self.node.run(context)

        assert result["status"] == "error"
        assert "Redis connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_uses_default_namespace_and_session(self):
        """Test run uses default namespace and session when not provided."""
        self.mock_memory_logger.log_memory.return_value = "memory_key_default"

        context = {
            "input": "Test content",
        }

        result = await self.node.run(context)

        assert result["status"] == "success"
        assert result["session"] == "test_session"  # From node initialization
        assert result["namespace"] == "test_ns"  # From node initialization


class TestMemoryWriterNodeContentExtraction:
    """Test memory content extraction methods."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=Mock(),
            )

    def test_extract_memory_content_false_guardian(self):
        """Test extracting content from false validation guardian."""
        context = {
            "input": "Original input",
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
        }

        content = self.node._extract_memory_content(context)

        assert "Number: 7" in content
        assert "Greater than 5: true" in content
        assert "Condition: greater than 5" in content
        assert "Analysis: numerical_comparison" in content
        assert "Confidence: 0.95" in content

    def test_extract_memory_content_true_guardian(self):
        """Test extracting content from true validation guardian."""
        context = {
            "input": "Original input",
            "previous_outputs": {
                "true_validation_guardian": {
                    "result": {
                        "memory_object": {
                            "number": "3",
                            "result": "false",
                            "analysis_type": "comparison",
                        },
                    },
                },
            },
        }

        content = self.node._extract_memory_content(context)

        assert "Number: 3" in content
        assert "Greater than 5: false" in content
        assert "Analysis: comparison" in content

    def test_extract_memory_content_no_guardian_output(self):
        """Test extracting content when no guardian output exists."""
        context = {
            "input": "Direct input content",
            "previous_outputs": {},
        }

        content = self.node._extract_memory_content(context)

        assert content == "Direct input content"

    def test_extract_memory_content_invalid_guardian_structure(self):
        """Test extracting content with invalid guardian structure."""
        context = {
            "input": "Fallback input",
            "previous_outputs": {
                "false_validation_guardian": {
                    # Missing result field
                    "invalid": "structure",
                },
            },
        }

        content = self.node._extract_memory_content(context)

        assert content == "Fallback input"

    def test_extract_memory_content_guardian_not_dict(self):
        """Test extracting content when guardian output is not a dict."""
        context = {
            "input": "Fallback input",
            "previous_outputs": {
                "false_validation_guardian": "not a dict",
            },
        }

        content = self.node._extract_memory_content(context)

        assert content == "Fallback input"

    def test_extract_memory_content_exception_handling(self):
        """Test exception handling during content extraction."""
        with patch.object(
            self.node,
            "_memory_object_to_text",
            side_effect=Exception("Conversion error"),
        ):
            context = {
                "input": "Fallback input",
                "previous_outputs": {
                    "false_validation_guardian": {
                        "result": {
                            "memory_object": {"test": "data"},
                        },
                    },
                },
            }

            content = self.node._extract_memory_content(context)

            assert content == "Fallback input"


class TestMemoryWriterNodeObjectToText:
    """Test memory object to text conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=Mock(),
            )

    def test_memory_object_to_text_complete_object(self):
        """Test converting complete memory object to text."""
        memory_obj = {
            "number": "7",
            "result": "true",
            "condition": "greater than 5",
            "analysis_type": "numerical_comparison",
            "confidence": 0.95,
            "validation_status": "validated",
        }

        text = self.node._memory_object_to_text(memory_obj, "original input")

        assert "Number: 7" in text
        assert "Greater than 5: true" in text
        assert "Condition: greater than 5" in text
        assert "Analysis: numerical_comparison" in text
        assert "Confidence: 0.95" in text
        assert "Validated: validated" in text
        assert "JSON:" in text

    def test_memory_object_to_text_partial_object(self):
        """Test converting partial memory object to text."""
        memory_obj = {
            "number": "3",
            "result": "false",
        }

        text = self.node._memory_object_to_text(memory_obj, "original input")

        assert "Number: 3" in text
        assert "Greater than 5: false" in text
        assert "Condition: " in text  # Empty condition
        assert "Analysis: " in text  # Empty analysis
        assert "Confidence: 1.0" in text  # Default confidence

    def test_memory_object_to_text_missing_number(self):
        """Test converting memory object without number field."""
        memory_obj = {
            "result": "true",
            "analysis_type": "test",
        }

        text = self.node._memory_object_to_text(memory_obj, "original input")

        assert "Number: original input" in text  # Uses original input as fallback
        assert "Greater than 5: true" in text

    def test_memory_object_to_text_exception_handling(self):
        """Test exception handling during object to text conversion."""
        # Create a problematic memory object that causes an exception
        memory_obj = Mock()
        memory_obj.get.side_effect = Exception("Mock exception")

        with patch("logging.Logger.warning") as mock_warning:
            text = self.node._memory_object_to_text(memory_obj, "original")

            # Should return string representation of the object
            assert str(memory_obj) in text
            mock_warning.assert_called_once()


class TestMemoryWriterNodeImportanceScore:
    """Test importance score calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=Mock(),
            )

    def test_calculate_importance_score_base_score(self):
        """Test base importance score calculation."""
        score = self.node._calculate_importance_score("Short content", {})

        assert score == 0.5  # Base score

    def test_calculate_importance_score_long_content(self):
        """Test importance score with long content."""
        long_content = "x" * 600  # Over 500 characters
        score = self.node._calculate_importance_score(long_content, {})

        assert score == 0.7  # Base + 0.2 for long content

    def test_calculate_importance_score_medium_content(self):
        """Test importance score with medium content."""
        medium_content = "x" * 200  # Over 100 characters
        score = self.node._calculate_importance_score(medium_content, {})

        assert score == 0.6  # Base + 0.1 for medium content

    def test_calculate_importance_score_stored_category(self):
        """Test importance score with stored category."""
        metadata = {"category": "stored"}
        score = self.node._calculate_importance_score("Content", metadata)

        assert score == 0.8  # Base + 0.3 for stored category

    def test_calculate_importance_score_with_query(self):
        """Test importance score with query metadata."""
        metadata = {"query": "test query"}
        score = self.node._calculate_importance_score("Content", metadata)

        assert score == 0.6  # Base + 0.1 for query

    def test_calculate_importance_score_maximum(self):
        """Test importance score calculation with all bonuses."""
        long_content = "x" * 600
        metadata = {"category": "stored", "query": "test query"}
        score = self.node._calculate_importance_score(long_content, metadata)

        assert score == 1.0  # Clamped to maximum 1.0

    def test_calculate_importance_score_clamping(self):
        """Test that importance score is properly clamped."""
        # Test that score doesn't go below 0.0
        negative_bonus_content = ""
        score = self.node._calculate_importance_score(negative_bonus_content, {})
        assert score >= 0.0

        # Test that score doesn't go above 1.0 (already tested in maximum test)
        assert score <= 1.0


class TestMemoryWriterNodeMemoryTypeClassification:
    """Test memory type classification."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=Mock(),
            )

    def test_classify_memory_type_short_term_default(self):
        """Test default short-term classification."""
        memory_type = self.node._classify_memory_type({}, 0.5)

        assert memory_type == "short_term"

    def test_classify_memory_type_stored_high_importance(self):
        """Test long-term classification for stored high-importance memory."""
        metadata = {"category": "stored"}
        memory_type = self.node._classify_memory_type(metadata, 0.8)

        assert memory_type == "long_term"

    def test_classify_memory_type_stored_low_importance(self):
        """Test short-term classification for stored low-importance memory."""
        metadata = {"category": "stored"}
        memory_type = self.node._classify_memory_type(metadata, 0.6)

        assert memory_type == "short_term"

    def test_classify_memory_type_default_long_term_config(self):
        """Test long-term classification based on config."""
        self.node.decay_config = {"default_long_term": True}
        memory_type = self.node._classify_memory_type({}, 0.3)

        assert memory_type == "long_term"

    def test_classify_memory_type_stored_exactly_threshold(self):
        """Test classification at exactly the importance threshold."""
        metadata = {"category": "stored"}
        memory_type = self.node._classify_memory_type(metadata, 0.7)

        assert memory_type == "long_term"


class TestMemoryWriterNodeExpiryHours:
    """Test expiry hours calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=Mock(),
            )

    def test_get_expiry_hours_short_term_default(self):
        """Test expiry hours for short-term memory with defaults."""
        hours = self.node._get_expiry_hours("short_term", 0.5)

        # Base 1.0 hours * (1.0 + 0.5 importance) = 1.5 hours
        assert hours == 1.5

    def test_get_expiry_hours_long_term_default(self):
        """Test expiry hours for long-term memory with defaults."""
        hours = self.node._get_expiry_hours("long_term", 0.8)

        # Base 24.0 hours * (1.0 + 0.8 importance) = 43.2 hours
        assert hours == 43.2

    def test_get_expiry_hours_with_agent_config(self):
        """Test expiry hours with agent-level configuration."""
        self.node.decay_config = {
            "short_term_hours": 2.0,
            "long_term_hours": 48.0,
        }

        short_hours = self.node._get_expiry_hours("short_term", 0.5)
        long_hours = self.node._get_expiry_hours("long_term", 0.3)

        assert short_hours == 3.0  # 2.0 * (1.0 + 0.5)
        assert abs(long_hours - 62.4) < 0.01  # 48.0 * (1.0 + 0.3) with floating point tolerance

    def test_get_expiry_hours_with_global_config_fallback(self):
        """Test expiry hours with global configuration fallback."""
        self.node.decay_config = {
            "default_short_term_hours": 0.5,
            "default_long_term_hours": 12.0,
        }

        short_hours = self.node._get_expiry_hours("short_term", 0.2)
        long_hours = self.node._get_expiry_hours("long_term", 0.6)

        assert short_hours == 0.6  # 0.5 * (1.0 + 0.2)
        assert abs(long_hours - 19.2) < 0.01  # 12.0 * (1.0 + 0.6) with floating point tolerance

    def test_get_expiry_hours_agent_priority_over_global(self):
        """Test that agent-level config takes priority over global config."""
        self.node.decay_config = {
            "short_term_hours": 3.0,  # Agent-level
            "default_short_term_hours": 1.0,  # Global fallback
            "default_long_term_hours": 36.0,  # Only global available
        }

        short_hours = self.node._get_expiry_hours("short_term", 0.0)
        long_hours = self.node._get_expiry_hours("long_term", 0.0)

        assert short_hours == 3.0  # Uses agent-level config
        assert long_hours == 36.0  # Uses global fallback

    def test_get_expiry_hours_importance_multiplier(self):
        """Test importance score multiplier effect."""
        # Test with zero importance (multiplier = 1.0)
        hours_zero = self.node._get_expiry_hours("short_term", 0.0)
        assert hours_zero == 1.0

        # Test with high importance (multiplier = 2.0)
        hours_high = self.node._get_expiry_hours("short_term", 1.0)
        assert hours_high == 2.0


class TestMemoryWriterNodeEdgeCases:
    """Test edge cases and error scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.nodes.memory_writer_node.create_memory_logger"):
            self.mock_memory_logger = Mock()
            self.node = MemoryWriterNode(
                node_id="test_writer",
                prompt="test",
                queue=[],
                memory_logger=self.mock_memory_logger,
            )

    @pytest.mark.asyncio
    async def test_run_with_empty_context(self):
        """Test run with completely empty context."""
        result = await self.node.run({})

        assert result["status"] == "error"
        assert result["error"] == "No memory content to store"

    @pytest.mark.asyncio
    async def test_run_with_empty_input(self):
        """Test run with empty input string."""
        context = {"input": ""}

        result = await self.node.run(context)

        assert result["status"] == "error"
        assert result["error"] == "No memory content to store"

    def test_extract_memory_content_with_none_input(self):
        """Test content extraction with None input."""
        context = {"input": None, "previous_outputs": {}}

        content = self.node._extract_memory_content(context)

        assert content is None  # None input returns None

    def test_memory_object_to_text_with_none_values(self):
        """Test object to text conversion with None values."""
        memory_obj = {
            "number": None,
            "result": None,
            "condition": None,
            "analysis_type": None,
            "confidence": None,
        }

        text = self.node._memory_object_to_text(memory_obj, "fallback")

        # Should handle None values gracefully
        assert "Number: None" in text  # Implementation shows None values as-is
        assert "Greater than 5: None" in text
        assert "Condition: None" in text
        assert "Analysis: None" in text
        assert "Confidence: None" in text  # None confidence is shown as None

    def test_calculate_importance_score_with_none_metadata(self):
        """Test importance score calculation with None metadata values."""
        metadata = {"category": None, "query": None}

        score = self.node._calculate_importance_score("content", metadata)

        assert score == 0.5  # Only base score, no bonuses

    def test_classify_memory_type_with_missing_metadata_keys(self):
        """Test memory type classification with missing metadata keys."""
        # Test when category key doesn't exist
        memory_type = self.node._classify_memory_type({}, 0.8)
        assert memory_type == "short_term"

        # Test when category is None
        memory_type = self.node._classify_memory_type({"category": None}, 0.8)
        assert memory_type == "short_term"

    def test_get_expiry_hours_with_missing_config_keys(self):
        """Test expiry hours calculation with missing config keys."""
        # Empty decay config should use defaults
        self.node.decay_config = {}

        short_hours = self.node._get_expiry_hours("short_term", 0.0)
        long_hours = self.node._get_expiry_hours("long_term", 0.0)

        assert short_hours == 1.0  # Default short-term
        assert long_hours == 24.0  # Default long-term

    @pytest.mark.asyncio
    async def test_run_integration_with_all_methods(self):
        """Test complete run integration calling all internal methods."""
        self.mock_memory_logger.log_memory.return_value = "integrated_memory_key"

        # Create context that exercises all code paths
        context = {
            "input": "x" * 600,  # Long content for importance bonus
            "previous_outputs": {
                "false_validation_guardian": {
                    "result": {
                        "memory_object": {
                            "number": "10",
                            "result": "true",
                            "condition": "greater than 5",
                            "analysis_type": "numerical_comparison",
                            "confidence": 0.95,
                            "validation_status": "validated",
                        },
                    },
                },
            },
            "namespace": "integration_test",
            "session_id": "integration_session",
            "metadata": {"category": "stored", "query": "test query"},
        }

        result = await self.node.run(context)

        assert result["status"] == "success"
        assert result["memory_key"] == "integrated_memory_key"

        # Verify memory logger was called with processed data
        call_args = self.mock_memory_logger.log_memory.call_args
        assert (
            abs(call_args[1]["importance_score"] - 1.0) < 0.01
        )  # Max score with floating point tolerance
        assert call_args[1]["memory_type"] == "long_term"  # High importance stored
        assert call_args[1]["expiry_hours"] == 48.0  # 24 * (1.0 + 1.0)
